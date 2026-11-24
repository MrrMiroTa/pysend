"""GPS Expiry Notifier - secure Flask web app.  Run: python app.py   (hash password: python app.py hash)"""
import getpass, os, re, secrets, sys, time
from collections import Counter
from datetime import date, timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, abort, g, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

if len(sys.argv) > 1 and sys.argv[1] == "hash":
    print(generate_password_hash(getpass.getpass("New admin password: "), method="scrypt"))
    sys.exit(0)

load_dotenv(interpolate=False)
BASE = os.path.dirname(os.path.abspath(__file__))


def env_int(key, default):
    try:
        return int(os.getenv(key, default))
    except ValueError:
        return default


def clamp(v, lo, hi, default):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


CFG = dict(
    API_ID=env_int("API_ID", 0), API_HASH=os.getenv("API_HASH", ""),
    BOT_TOKEN=os.getenv("BOT_TOKEN", ""), ADMIN_IDS=os.getenv("ADMIN_IDS", ""),
    MIN_DELAY=env_int("MIN_DELAY", 8), MAX_DELAY=max(env_int("MAX_DELAY", 20), env_int("MIN_DELAY", 8)),
    MAX_PER_RUN=env_int("MAX_PER_RUN", 80), CONTACT_PHONE=os.getenv("CONTACT_PHONE") or "087500502",
    SESSION=os.path.join(os.path.abspath(os.getenv("DATA_DIR")) if os.getenv("DATA_DIR") else BASE, "sessions", "main"),
    SESSION_STRING=os.getenv("TELEGRAM_SESSION_STRING", "").strip(),  # alternative to the .session file (cloud hosting)
)
os.makedirs(os.path.dirname(CFG["SESSION"]), exist_ok=True)
if len(os.getenv("SECRET_KEY", "")) < 32:
    sys.exit("Set a 32+ char SECRET_KEY in .env (see .env.example).")

from excel_manager import ExcelManager, safe_cell  # noqa: E402
from database import FileStore, History, UserStore, data_dir, database_url, make_engine  # noqa: E402
from telegram_bot import CHUNK, LogBuffer, TelegramBot, group_rows  # noqa: E402
from timeutil import today as today_local  # noqa: E402

app = Flask(__name__)
if os.getenv("TRUST_PROXY") == "1":  # behind Nginx/Caddy: use the real client IP/scheme
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config.update(
    SECRET_KEY=os.environ["SECRET_KEY"],
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,                # reject uploads > 10 MB
    SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),   # idle logout
)
DB_URL = database_url(BASE)
engine = make_engine(DB_URL)                  # creates the tables on first start
accounts = UserStore(engine)                  # admin login users  (database)
history = History(engine)                     # report             (database)
try:
    history.purge(today_local())               # keep only the last 3 months (rolling), also after a restart
except Exception as _e:
    print("report cleanup skipped:", type(_e).__name__)
# The client list is an Excel file. With an external database (DATABASE_URL, e.g. Neon) a copy is kept there too,
# so a redeploy on a host without a disk (Render Free) does not lose the list and the 'Sent' marks.
_use_db_copy = bool(os.getenv("DATABASE_URL", "").strip()) and not DB_URL.startswith("sqlite") and os.getenv("DB_FILE_COPY", "1") != "0"
excel = ExcelManager(os.path.join(data_dir(BASE), "clients_working.xlsx"),
                     store=FileStore(engine) if _use_db_copy else None)  # client list = Excel, loaded with Browse file
if excel.restore_if_missing():
    print("client list restored from the database")
logs = LogBuffer()
bot = TelegramBot(CFG, excel, logs, history)
FAILS = {}  # ip -> [count, locked_until]  (login brute-force throttle)
DUMMY_HASH = generate_password_hash("not-a-real-password", method="scrypt")  # keeps login timing equal for unknown users
USER_RE = re.compile(r"^[a-z0-9_.-]{3,32}$")

# First start only: create the first admin from .env. After that, manage users in the "Users" tab.
if accounts.count() == 0:
    _h = os.getenv("ADMIN_PASSWORD_HASH", "")
    if not _h.startswith(("scrypt:", "pbkdf2:")):
        sys.exit("No admin user exists yet. Run:  python scripts/create_user.py   "
                 "(or set ADMIN_USER and ADMIN_PASSWORD_HASH in .env)")
    accounts.create(os.getenv("ADMIN_USER", "admin").strip().lower()[:64], _h)


# ---------- security plumbing ----------
@app.before_request
def guard():
    session.permanent = True
    session.setdefault("csrf", secrets.token_hex(16))
    if request.method not in ("GET", "HEAD", "OPTIONS"):  # CSRF: every state-changing request needs the token
        sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
        if not secrets.compare_digest(sent, session["csrf"]):
            abort(400, "Bad CSRF token")


@app.after_request
def headers(r):
    r.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["Referrer-Policy"] = "no-referrer"
    r.headers["Cache-Control"] = "no-store"
    if app.config["SESSION_COOKIE_SECURE"]:
        r.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return r


def login_required(f):
    @wraps(f)
    def wrap(*a, **k):
        u = accounts.get(session["uid"]) if session.get("uid") else None
        if not u or not u["is_active"]:  # a disabled/deleted user is signed out immediately
            session.clear()
            return (jsonify(error="Not signed in"), 401) if request.path.startswith("/api/") \
                else redirect(url_for("login"))
        g.user = u
        return f(*a, **k)
    return wrap


@app.get("/healthz")
def healthz():  # for uptime monitors / deployment checks
    from sqlalchemy import text
    with engine.connect() as c:
        c.execute(text("SELECT 1"))
    return "ok"


@app.route("/login", methods=["GET", "POST"])
def login():
    err, ip = None, request.remote_addr
    if request.method == "POST":
        count, until = FAILS.get(ip, [0, 0])
        if time.time() < until:
            err = "Too many attempts. Try again in a few minutes."
        else:
            u = accounts.get_by_name(request.form.get("username", "").strip().lower()[:64])
            try:
                pass_ok = check_password_hash(u["password_hash"] if u else DUMMY_HASH,
                                              request.form.get("password", ""))  # always run
            except ValueError:
                pass_ok = False
                logs.add("error", "A stored password hash is invalid. Reset it: python scripts/create_user.py <name> --reset")
            if u and u["is_active"] and pass_ok:
                FAILS.pop(ip, None)
                keep = secrets.token_hex(16)
                session.clear()                       # new session id after login
                session.update(uid=u["id"], csrf=keep)
                accounts.touch_login(u["id"])
                return redirect(url_for("index"))
            count += 1
            FAILS[ip] = [count, time.time() + 300 if count >= 5 else 0]
            time.sleep(1)                             # slow down guessing
            err = "Wrong username or password."
    return render_template("login.html", csrf=session["csrf"], error=err)


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.errorhandler(400)
@app.errorhandler(413)
def api_errors(e):
    if request.path.startswith("/api/"):
        msg = "File too large (maximum 10 MB)." if e.code == 413 else "Request rejected. Refresh the page (Ctrl+F5) and try again."
        return jsonify(error=msg), e.code
    return e


# ---------- helpers ----------
def thresholds():
    return clamp(request.values.get("normal"), 1, 365, 7), clamp(request.values.get("company"), 1, 365, 14)


def in_filter(r, f, n, c):
    d = r["days"]
    live = r["state"] != "sent" and d is not None
    return {"all": True,
            "due_normal": live and 0 <= d <= n, "due_company": live and 0 <= d <= c,
            "expired": r["state"] == "expired", "sent": r["state"] == "sent"}.get(f, True)


def matches(r, q):
    return not q or q in f"{r['user']} {r.get('name', '')} {r['plate']} {r['imei']}".lower()


def thr_of(r, n, c):
    return c if r["type"].lower().startswith("comp") else n


def pick_rows(payload, n, c):
    """Which units to send. Units already marked Sent are skipped unless force=true."""
    rows = excel.records(n, c)
    force = bool(payload.get("force"))
    if payload.get("mode") == "selected":
        ids = {int(i) for i in payload.get("ids", []) if str(i).isdigit()}
        chosen = [r for r in rows if r["id"] in ids]
        return chosen if force else [r for r in chosen if r["state"] != "sent"]
    return [r for r in rows if r["state"] == "due" or
            (force and r["state"] == "sent" and r["days"] is not None and 0 <= r["days"] <= thr_of(r, n, c))]


def clean_phone(v):
    """Contact number typed in the page; only digits, + - ( ) and spaces. Anything else is ignored."""
    v = str(v or "").strip()
    return v if re.fullmatch(r"[0-9+\-()\s]{3,30}", v) else None


def check_password(pw, username=""):
    if not (8 <= len(pw) <= 128):
        return "Password must be 8-128 characters."
    if pw.lower() == username.lower():
        return "Password must not be the same as the username."
    return None


# ---------- pages & API ----------
@app.get("/")
@login_required
def index():
    return render_template("index.html", csrf=session["csrf"], max_run=CFG["MAX_PER_RUN"], username=g.user["username"],
                           phone=CFG["CONTACT_PHONE"])


def build_data(n, c, flt, q, page_arg, size_arg):
    """One page of the client list + stats. Used by /api/data and returned by /api/upload."""
    rows = excel.records(n, c)
    cnt = Counter(r["state"] for r in rows)
    stats = {k: cnt.get(k, 0) for k in ("due", "approaching", "expired", "safe", "sent")}
    stats.update(units=len(rows), users=len({r["user"] for r in rows}), due_normal=0, due_company=0, due_resend=0)
    for r in rows:  # one pass over all units
        d = r["days"]
        if d is None:
            continue
        if r["state"] != "sent":
            stats["due_normal"] += 0 <= d <= n
            stats["due_company"] += 0 <= d <= c
        elif 0 <= d <= thr_of(r, n, c):
            stats["due_resend"] += 1
    q = (q or "").strip().lower()[:80]
    shown = [r for r in rows if in_filter(r, flt, n, c) and matches(r, q)]
    size = clamp(size_arg, 10, 500, 100)
    pages = max(1, -(-len(shown) // size))
    page = clamp(page_arg, 1, pages, 1)  # paging keeps the browser fast with 10,000+ units
    return dict(rows=shown[(page - 1) * size: page * size], total=len(shown), page=page, pages=pages, size=size,
                stats=stats, file=excel.source_name if os.path.exists(excel.path) else "")


@app.get("/api/data")
@login_required
def data():
    n, c = thresholds()
    try:
        return jsonify(build_data(n, c, request.args.get("filter", "all"), request.args.get("q", ""),
                                  request.args.get("page"), request.args.get("size")))
    except Exception as e:
        return jsonify(error=f"Cannot read Excel: {e}"), 400


@app.get("/api/ids")
@login_required
def ids_matching():
    """IDs of every unit matching the current filter/search ('select all matching')."""
    n, c = thresholds()
    flt, q = request.args.get("filter", "all"), request.args.get("q", "").strip().lower()[:80]
    return jsonify(ids=[r["id"] for r in excel.records(n, c) if in_filter(r, flt, n, c) and matches(r, q)][:100000])


@app.post("/api/preview")
@login_required
def preview():
    p = request.get_json(silent=True) or {}
    rows = pick_rows(p, *thresholds())
    if not rows:
        return jsonify(error="No matching rows to preview."), 400
    units = group_rows(rows)[0]
    text, image = bot.preview(units, str(p.get("template", ""))[:2000], clean_phone(p.get("phone")))
    return jsonify(user=units[0]["user"], units=len(units), images=-(-len(units) // CHUNK), text=text, image=image)


@app.post("/api/send")
@login_required
def send():
    p = request.get_json(silent=True) or {}
    rows = pick_rows(p, *thresholds())
    tpl = str(p.get("template", "")).strip()[:2000]
    if not tpl:
        return jsonify(error="The message template is empty."), 400
    if not rows:
        return jsonify(error="Nothing to send. These units are already marked Sent - turn on Force resend to send again."
                       if p.get("mode") == "selected" else "No clients are due. Turn on Force resend to include units already sent."), 400
    limit = clamp(p.get("limit"), 1, CFG["MAX_PER_RUN"], CFG["MAX_PER_RUN"])  # env value is a hard cap
    groups = group_rows(rows)  # one message per client
    if not bot.start(groups, tpl, limit, g.user["username"], clean_phone(p.get("phone"))):
        return jsonify(error="A batch is already running."), 409
    return jsonify(started=min(len(groups), limit))


@app.post("/api/stop")
@login_required
def stop():
    bot.stop()
    return jsonify(ok=True)


@app.get("/api/status")
@login_required
def status():
    since = clamp(request.args.get("since"), 0, 10**9, 0)
    return jsonify(running=bot.running, progress=bot.progress, logs=logs.since(since))


@app.post("/api/upload")
@login_required
def upload():
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith((".xlsx", ".xlsm", ".csv")):
        return jsonify(error="Please choose an Excel (.xlsx, .xlsm) or .csv file."), 400
    if bot.running:
        return jsonify(error="Wait for the running batch to finish."), 409
    try:
        n = excel.replace_from_upload(f)
    except ValueError as e:
        return jsonify(error=f"Invalid file: {e}"), 400
    except Exception as e:
        app.logger.exception("Upload failed")  # full traceback in the terminal
        return jsonify(error=f"Could not import ({type(e).__name__}): {e}"), 500
    logs.add("info", f"{g.user['username']} imported {n} row(s) from upload.")
    n_days, c_days = thresholds()  # the page asks for the new list in this same response (no second request needed)
    return jsonify(rows=n, file=excel.source_name, warnings=excel.last_warnings,
                   data=build_data(n_days, c_days, "all", "", 1, request.args.get("size")))


@app.get("/api/template")
@login_required
def template_file():
    return send_file(excel.template(), as_attachment=True, download_name="clients_template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/api/export")
@login_required
def export():
    n, c = thresholds()
    q = request.args.get("q", "").strip().lower()[:80]
    rows = [r for r in excel.records(n, c) if in_filter(r, request.args.get("filter", "all"), n, c) and matches(r, q)]
    return send_file(excel.export(rows), as_attachment=True, download_name="gps_expiry_export.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ---------- report (by day + status) ----------
def parse_day(v):
    try:
        return date.fromisoformat(str(v)[:10]).isoformat()
    except ValueError:
        return None


def report_args():
    status = request.args.get("status", "all")
    status = status if status in ("sent", "failed", "skipped") else "all"
    if request.args.get("all") == "1":
        return status, None, None
    d_to = parse_day(request.args.get("to")) or today_local().isoformat()
    d_from = parse_day(request.args.get("from")) or (date.fromisoformat(d_to) - timedelta(days=6)).isoformat()
    d_from, d_to = min(d_from, d_to), max(d_from, d_to)
    return status, max(d_from, history.keep_from(today_local())), d_to     # older than 3 months no longer exists


@app.get("/api/report")
@login_required
def report():
    status, d_from, d_to = report_args()
    return jsonify(summary=history.summary(d_from, d_to), days=history.days(d_from, d_to),
                   rows=history.rows(status, d_from, d_to), range=[d_from, d_to],
                   keep_from=history.keep_from(today_local()))


@app.get("/api/report/export")
@login_required
def report_export():
    import io
    import pandas as pd
    status, d_from, d_to = report_args()
    ucols = ("name", "plate", "imei", "expiry", "ts", "status")          # the plate list the person asked for
    units = pd.DataFrame([{k: safe_cell(r[k]) for k in ucols} for r in history.unit_rows(status, d_from, d_to)], columns=ucols)
    units.columns = ["name", "plate", "imei", "expiry_date", "date_sent", "status"]
    cols = ("ts", "user", "units", "plates", "status", "reason", "detail", "sent_by")
    detail = pd.DataFrame([{k: safe_cell(r[k]) for k in cols} for r in history.rows(status, d_from, d_to, 100000)], columns=cols)
    by_day = pd.DataFrame(history.days(d_from, d_to), columns=("day", "total", "sent", "failed", "skipped"))
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        units.to_excel(w, sheet_name="Plates", index=False)
        by_day.to_excel(w, sheet_name="By day", index=False)
        detail.to_excel(w, sheet_name="Report", index=False)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="gps_send_report.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ---------- admin users ----------
def public_user(u):
    return dict(id=u["id"], username=u["username"], active=bool(u["is_active"]), created_at=u["created_at"],
                last_login=u["last_login"] or "", me=u["id"] == g.user["id"])


@app.get("/api/users")
@login_required
def users_list():
    return jsonify(users=[public_user(u) for u in accounts.list()])


@app.post("/api/users")
@login_required
def users_add():
    p = request.get_json(silent=True) or {}
    name, pw = str(p.get("username", "")).strip().lower(), str(p.get("password", ""))
    if not USER_RE.match(name):
        return jsonify(error="Username: 3-32 characters, letters, numbers, . _ - only."), 400
    if (msg := check_password(pw, name)):
        return jsonify(error=msg), 400
    if accounts.get_by_name(name):
        return jsonify(error="That username already exists."), 409
    accounts.create(name, generate_password_hash(pw, method="scrypt"))
    logs.add("info", f"{g.user['username']} created user {name}.")
    return jsonify(ok=True)


@app.post("/api/users/<int:uid>/password")
@login_required
def users_password(uid):
    u = accounts.get(uid)
    pw = str((request.get_json(silent=True) or {}).get("password", ""))
    if not u:
        return jsonify(error="User not found."), 404
    if (msg := check_password(pw, u["username"])):
        return jsonify(error=msg), 400
    accounts.set_password(uid, generate_password_hash(pw, method="scrypt"))
    logs.add("info", f"{g.user['username']} changed the password of {u['username']}.")
    return jsonify(ok=True)


@app.post("/api/users/<int:uid>/active")
@login_required
def users_active(uid):
    u = accounts.get(uid)
    if not u:
        return jsonify(error="User not found."), 404
    if uid == g.user["id"]:
        return jsonify(error="You cannot disable your own account."), 400
    active = bool((request.get_json(silent=True) or {}).get("active"))
    accounts.set_active(uid, active)
    logs.add("info", f"{g.user['username']} {'enabled' if active else 'disabled'} {u['username']}.")
    return jsonify(ok=True)


@app.post("/api/users/<int:uid>/delete")
@login_required
def users_delete(uid):
    u = accounts.get(uid)
    if not u:
        return jsonify(error="User not found."), 404
    if uid == g.user["id"]:
        return jsonify(error="You cannot delete your own account."), 400
    accounts.delete(uid)
    logs.add("info", f"{g.user['username']} deleted user {u['username']}.")
    return jsonify(ok=True)


def port_in_use(host, port):
    """True if another program (e.g. an old copy of this app) already listens on the port.
    Windows lets two programs share a port, which would split your data between them."""
    import socket
    s = socket.socket()
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        return False
    except OSError:
        return True
    finally:
        s.close()


if __name__ == "__main__":
    import signal
    from waitress import serve
    _host, _port = os.getenv("HOST", "127.0.0.1"), env_int("PORT", 5000)
    if port_in_use(_host, _port):
        sys.exit(f"\nPort {_port} is already in use - probably an old copy of this app is still running.\n"
                 f"Close it first (Task Manager > python.exe, or: netstat -ano | findstr :{_port}  then  taskkill /PID <number> /F),\n"
                 f"or set a different PORT in .env.")

    def _on_term(*_):  # Render/Docker stop the app with SIGTERM: save pending "Sent" marks first
        excel.flush()
        sys.exit(0)
    signal.signal(signal.SIGTERM, _on_term)
    logs.add("info", "System ready.")
    serve(app, host=_host, port=_port, threads=4)
