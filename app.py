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
if len(os.getenv("SECRET_KEY", "")) < 32 or len(set(os.getenv("SECRET_KEY", ""))) < 8:
    sys.exit("Set a random SECRET_KEY of 32+ characters in .env (see .env.example). Make one with: python -c \"import secrets;print(secrets.token_hex(32))\"")

from excel_manager import RENTAL_DEFAULT, ExcelManager, norm_utype, safe_cell  # noqa: E402
from database import FileStore, History, UserStore, data_dir, database_url, make_engine  # noqa: E402
from security import Throttle, apply_headers, check_upload, password_problem, pw_stamp  # noqa: E402
from telegram_bot import CHUNK, LogBuffer, TelegramBot, group_rows  # noqa: E402
from timeutil import now as now_local, today as today_local  # noqa: E402

app = Flask(__name__)
if os.getenv("TRUST_PROXY") == "1":  # behind Nginx/Caddy: use the real client IP/scheme
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config.update(
    SECRET_KEY=os.environ["SECRET_KEY"],
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,                # reject uploads > 10 MB
    SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE") == "1",
    SESSION_COOKIE_NAME="__Host-session" if os.getenv("COOKIE_SECURE") == "1" else "session",   # __Host-: https only, no Domain, path /
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
IP_THROTTLE = Throttle(limit=5, window=900, lock=300)       # 5 wrong passwords from one address -> 5 min lock
USER_THROTTLE = Throttle(limit=12, window=900, lock=300)    # slow guessing spread over many addresses
DUMMY_HASH = generate_password_hash("not-a-real-password", method="scrypt")  # keeps login timing equal for unknown users
USER_RE = re.compile(r"^[a-z0-9_.-]{3,32}$")

# ---------- permissions (set per user by an admin in the Users tab) ----------
PERMS = ["report", "import", "send", "expiry", "fill_id", "export", "users"]
DEFAULT_PERMS = ["report", "import", "send", "expiry", "fill_id", "export"]          # "users" = manage users & permissions
ADMIN_USER = os.getenv("ADMIN_USER", "admin").strip().lower()[:64]                     # this account always has every permission


def is_main_admin(u):
    return u["username"] == ADMIN_USER


def perms_of(u):
    if is_main_admin(u):
        return set(PERMS)
    raw = u.get("permissions")
    return {p for p in (DEFAULT_PERMS if raw is None else raw.split(",")) if p in PERMS}


def clean_perms(v):
    return sorted({str(p) for p in (v or []) if str(p) in PERMS}, key=PERMS.index)

# First start only: create the first admin from .env. After that, manage users in the "Users" tab.
if accounts.count() == 0:
    _h = os.getenv("ADMIN_PASSWORD_HASH", "")
    if not _h.startswith(("scrypt:", "pbkdf2:")):
        sys.exit("No admin user exists yet. Run:  python scripts/create_user.py   "
                 "(or set ADMIN_USER and ADMIN_PASSWORD_HASH in .env)")
    accounts.create(os.getenv("ADMIN_USER", "admin").strip().lower()[:64], _h, ",".join(PERMS))

# Accounts made before permissions existed keep what they could do (everything except managing users).
for _u in accounts.list():
    if _u.get("permissions") is None:
        accounts.set_permissions(_u["id"], ",".join(DEFAULT_PERMS))
if not any(is_main_admin(_u) or "users" in perms_of(_u) for _u in accounts.list()):   # never lock everybody out
    _first = accounts.list()[0]
    accounts.set_permissions(_first["id"], ",".join(sorted(perms_of(_first) | {"users"})))


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
    return apply_headers(r, app.config["SESSION_COOKIE_SECURE"])


def login_required(f):
    @wraps(f)
    def wrap(*a, **k):
        u = accounts.get(session["uid"]) if session.get("uid") else None
        if not u or not u["is_active"]:  # a disabled/deleted user is signed out immediately
            session.clear()
            return (jsonify(error="Not signed in"), 401) if request.path.startswith("/api/") \
                else redirect(url_for("login"))
        if session.get("pw") != pw_stamp(u["password_hash"]):   # password was changed since this sign-in -> sign in again
            session.clear()
            return (jsonify(error="Signed out: the password changed. Sign in again."), 401) if request.path.startswith("/api/") \
                else redirect(url_for("login"))
        g.user, g.perms = u, perms_of(u)
        return f(*a, **k)
    return wrap


def need(perm):
    """Use under @login_required: the signed-in user must have this permission (checked on the server, not only hidden in the page)."""
    def deco(f):
        @wraps(f)
        def wrap(*a, **k):
            if perm not in g.perms:
                return jsonify(error="You do not have permission for this. Ask an admin. / អ្នកគ្មានសិទ្ធិធ្វើសកម្មភាពនេះទេ។"), 403
            return f(*a, **k)
        return wrap
    return deco


@app.get("/healthz")
def healthz():  # for uptime monitors / deployment checks
    from sqlalchemy import text
    with engine.connect() as c:
        c.execute(text("SELECT 1"))
    return "ok"


@app.route("/login", methods=["GET", "POST"])
def login():
    err, ip = None, request.remote_addr or "?"
    if request.method == "POST":
        name = request.form.get("username", "").strip().lower()[:64]
        wait = max(IP_THROTTLE.wait(ip), USER_THROTTLE.wait(name))
        if wait:
            err = f"Too many attempts. Try again in {max(1, wait // 60 + (1 if wait % 60 else 0))} minute(s)."
        else:
            u = accounts.get_by_name(name)
            try:
                pass_ok = check_password_hash(u["password_hash"] if u else DUMMY_HASH,
                                              request.form.get("password", ""))  # always run
            except ValueError:
                pass_ok = False
                logs.add("error", "A stored password hash is invalid. Reset it: python scripts/create_user.py <name> --reset")
            if u and u["is_active"] and pass_ok:
                IP_THROTTLE.ok(ip)
                USER_THROTTLE.ok(name)
                keep = secrets.token_hex(16)
                session.clear()                       # new session id after login
                session.update(uid=u["id"], csrf=keep, pw=pw_stamp(u["password_hash"]))
                accounts.touch_login(u["id"])
                logs.add("info", f"{u['username']} signed in.")
                return redirect(url_for("index"))
            IP_THROTTLE.fail(ip)
            USER_THROTTLE.fail(name)
            logs.add("warn", f"Failed sign-in attempt for '{re.sub(r'[^a-z0-9_.-]', '?', name)[:32]}'.")
            time.sleep(1)                             # slow down guessing
            err = "Wrong username or password."
    return render_template("login.html", csrf=session["csrf"], error=err)


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.errorhandler(500)
def server_error(e):
    app.logger.exception("Unhandled error")           # details stay in the server log, never in the response
    if request.path.startswith("/api/"):
        return jsonify(error="Server error. Try again; if it repeats check the server log."), 500
    return "Server error", 500


@app.errorhandler(400)
@app.errorhandler(413)
def api_errors(e):
    if request.path.startswith("/api/"):
        msg = "File too large (maximum 10 MB)." if e.code == 413 else "Request rejected. Refresh the page (Ctrl+F5) and try again."
        return jsonify(error=msg), e.code
    return e


# ---------- helpers ----------
def thresholds():
    """(Normal days, Company days, Rental days): when the message is sent (paid_off: Normal/Company, rental: 1 month)."""
    return (clamp(request.values.get("normal"), 1, 365, 7), clamp(request.values.get("company"), 1, 365, 14),
            clamp(request.values.get("rental"), 1, 365, RENTAL_DEFAULT))


def opt_int(v):
    try:
        return max(-9999, min(9999, int(str(v).strip())))
    except (TypeError, ValueError):
        return None


def filt_args(src=None):
    """The dashboard filter: pill (all/safe/approaching/due/expired/sent/ready/no_user), user_type, days-left range."""
    src = src or request.values
    lo, hi = opt_int(src.get("dmin")), opt_int(src.get("dmax"))
    if lo is not None and hi is not None and lo > hi:
        lo, hi = hi, lo
    ut = src.get("utype", "all")
    return dict(flt=src.get("filter", "all"), utype=ut if ut in ("paid_off", "rental") else "all", dmin=lo, dmax=hi)


def in_filter(r, f):
    d = r["days"]
    if f["utype"] != "all" and r["user_type"] != f["utype"]:
        return False
    if f["dmin"] is not None or f["dmax"] is not None:
        if d is None or (f["dmin"] is not None and d < f["dmin"]) or (f["dmax"] is not None and d > f["dmax"]):
            return False
    flt = f["flt"]
    if flt in ("safe", "approaching", "due", "expired", "sent"):
        return r["state"] == flt
    if flt == "ready":
        return r["eligible"]
    if flt == "no_user":
        return not (r["user"] or "").strip()
    return True


def matches(r, q):
    return not q or q in f"{r['user']} {r.get('name', '')} {r['plate']} {r['imei']}".lower()


def pick_rows(payload, th):
    """Which units to send. Units already marked Sent are skipped unless force=true.
    'Send all due' = units whose days left are within their own limit: paid_off Normal 7 / Company 14, rental 30."""
    rows = excel.records(*th)
    force = bool(payload.get("force"))
    if payload.get("mode") == "selected":
        ids = {int(i) for i in payload.get("ids", []) if str(i).isdigit()}
        chosen = [r for r in rows if r["id"] in ids]
        return chosen if force else [r for r in chosen if r["state"] != "sent"]
    return [r for r in rows if r["eligible"] or
            (force and r["state"] == "sent" and r["days"] is not None and 0 <= r["days"] <= r["thr"])]


def clean_phone(v):
    """Contact number typed in the page; only digits, + - ( ) and spaces. Anything else is ignored."""
    v = str(v or "").strip()
    return v if re.fullmatch(r"[0-9+\-()\s]{3,30}", v) else None


def check_password(pw, username=""):
    return password_problem(pw, username)


# ---------- pages & API ----------
@app.get("/")
@login_required
def index():
    return render_template("index.html", csrf=session["csrf"], max_run=CFG["MAX_PER_RUN"], username=g.user["username"],
                           phone=CFG["CONTACT_PHONE"], perms=",".join(sorted(g.perms)), rental_days=RENTAL_DEFAULT)


CHANGE_LABEL = {"expiry": "Expiry date updated", "user": "Username/ID filled", "import": "File imported"}


def log_changes(rows):
    """Record what an admin changed (shown in the Report). Never blocks the change itself."""
    try:
        history.add_changes(now_local().strftime("%Y-%m-%d %H:%M:%S"), g.user["username"], rows)
    except Exception as e:
        app.logger.warning("change log failed: %s", e)


STATE_RANK = {"expired": 0, "due": 1, "approaching": 2, "safe": 3, "sent": 4, "invalid": 5}


def natural(s):
    """WL2 before WL10: text and numbers compared the way a person reads them."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s or "")]


SORT_KEYS = {
    "user": lambda r: (not r["user"], natural(r["user"])),
    "name": lambda r: (not r.get("name"), natural(r.get("name"))),
    "type": lambda r: natural(r["type"]),
    "user_type": lambda r: r["user_type"],
    "plate": lambda r: natural(r["plate"]),
    "imei": lambda r: natural(r["imei"]),
    "expiry": lambda r: (not r["expiry"], r["expiry"]),
    "days": lambda r: (r["days"] is None, r["days"] or 0),
    "state": lambda r: STATE_RANK.get(r["state"], 9),
}


def build_data(th, f, q, page_arg, size_arg, sort=None, direction="asc"):
    """One page of the client list + stats. Used by /api/data and returned by /api/upload."""
    rows = excel.records(*th)
    cnt = Counter(r["state"] for r in rows)
    stats = {k: cnt.get(k, 0) for k in ("due", "approaching", "expired", "safe", "sent")}
    stats.update(units=len(rows), users=len({r["user"] for r in rows if r["user"]}), no_user=sum(1 for r in rows if not r["user"]),
                 ready=0, ready_resend=0, rental=0, paid_off=0)
    for r in rows:  # one pass over all units
        stats["rental" if r["user_type"] == "rental" else "paid_off"] += 1
        d = r["days"]
        if r["eligible"]:
            stats["ready"] += 1
        elif r["state"] == "sent" and d is not None and 0 <= d <= r["thr"]:
            stats["ready_resend"] += 1
    q = (q or "").strip().lower()[:80]
    shown = [r for r in rows if in_filter(r, f) and matches(r, q)]
    if sort in SORT_KEYS:
        shown = sorted(shown, key=SORT_KEYS[sort], reverse=(direction == "desc"))
    size = clamp(size_arg, 10, 500, 100)
    pages = max(1, -(-len(shown) // size))
    page = clamp(page_arg, 1, pages, 1)  # paging keeps the browser fast with 10,000+ units
    return dict(rows=shown[(page - 1) * size: page * size], total=len(shown), page=page, pages=pages, size=size,
                stats=stats, file=excel.source_name if os.path.exists(excel.path) else "")


@app.get("/api/data")
@login_required
def data():
    try:
        return jsonify(build_data(thresholds(), filt_args(), request.args.get("q", ""),
                                  request.args.get("page"), request.args.get("size"),
                                  request.args.get("sort"), request.args.get("dir", "asc")))
    except Exception as e:
        return jsonify(error=f"Cannot read Excel: {e}"), 400


@app.get("/api/ids")
@login_required
def ids_matching():
    """IDs of every unit matching the current filter/search ('select all matching')."""
    f, q = filt_args(), request.args.get("q", "").strip().lower()[:80]
    return jsonify(ids=[r["id"] for r in excel.records(*thresholds()) if in_filter(r, f) and matches(r, q)][:100000])


@app.post("/api/preview")
@login_required
@need("send")
def preview():
    p = request.get_json(silent=True) or {}
    rows = pick_rows(p, thresholds())
    if not rows:
        return jsonify(error="No matching rows to preview."), 400
    groups = group_rows(rows)
    if not groups:
        return jsonify(error="These units have no Username/ID yet. Use 'Fill Username/ID' first."), 400
    units = groups[0]
    text, image = bot.preview(units, str(p.get("template", ""))[:2000], clean_phone(p.get("phone")))
    return jsonify(user=units[0]["user"], units=len(units), images=-(-len(units) // CHUNK), text=text, image=image)


@app.post("/api/send")
@login_required
@need("send")
def send():
    p = request.get_json(silent=True) or {}
    rows = pick_rows(p, thresholds())
    tpl = str(p.get("template", "")).strip()[:2000]
    if not tpl:
        return jsonify(error="The message template is empty."), 400
    if not rows:
        return jsonify(error="Nothing to send. These units are already marked Sent - turn on Force resend to send again."
                       if p.get("mode") == "selected" else "No clients are due. Turn on Force resend to include units already sent."), 400
    limit = clamp(p.get("limit"), 1, CFG["MAX_PER_RUN"], CFG["MAX_PER_RUN"])  # env value is a hard cap
    missing = [r for r in rows if not (r["user"] or "").strip()]      # plates without a Username/ID cannot be sent
    names = sorted({r.get("name") or r["plate"] for r in missing})
    shown = ", ".join(names[:8]) + ("…" if len(names) > 8 else "")
    groups = group_rows(rows)  # one message per client
    if not groups:
        return jsonify(error=f"Cannot send: {len(missing)} plate(s) have no Username/ID ({shown}). Use 'Fill Username/ID' first."), 400
    if not bot.start(groups, tpl, limit, g.user["username"], clean_phone(p.get("phone"))):
        return jsonify(error="A batch is already running."), 409
    if missing:
        logs.add("warn", f"Skipped {len(missing)} plate(s) without Username/ID: {shown}")
    return jsonify(started=min(len(groups), limit), skipped=len(missing), skipped_names=shown)


@app.post("/api/stop")
@login_required
@need("send")
def stop():
    bot.stop()
    return jsonify(ok=True)


@app.get("/api/status")
@login_required
def status():
    since = clamp(request.args.get("since"), 0, 10**9, 0)
    return jsonify(running=bot.running, progress=bot.progress, logs=logs.since(since), data_version=excel.version)


@app.post("/api/upload")
@login_required
@need("import")
def upload():
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith((".xlsx", ".xlsm", ".csv")):
        return jsonify(error="Please choose an Excel (.xlsx, .xlsm) or .csv file."), 400
    if (bad := check_upload(f)):
        return jsonify(error=bad), 400
    if bot.running:
        return jsonify(error="Wait for the running batch to finish."), 409
    merge = request.args.get("mode", "merge") != "replace"       # default: ADD to the current list, skip duplicate IMEI
    stats = {}
    try:
        if merge:
            stats = excel.merge_from_upload(f)
            n = stats["added"]
        else:
            n = excel.replace_from_upload(f)
    except ValueError as e:
        return jsonify(error=f"Invalid file: {e}"), 400
    except Exception as e:
        app.logger.exception("Upload failed")  # full traceback in the terminal
        return jsonify(error=f"Could not import ({type(e).__name__}): {e}"), 500
    if merge:
        note = f"{f.filename}: +{n} new, {stats['duplicates']} duplicate IMEI skipped" + (f", {stats['no_imei']} without IMEI skipped" if stats["no_imei"] else "")
        logs.add("info", f"{g.user['username']} added {n} new row(s) from upload ({stats['duplicates']} duplicate IMEI skipped).")
    else:
        note = f"{f.filename}: {n} rows (list replaced)"
        logs.add("info", f"{g.user['username']} imported {n} row(s) from upload (list replaced).")
    log_changes([dict(action="import", new_value=note)])
    th = thresholds()  # the page asks for the new list in this same response (no second request needed)
    return jsonify(rows=n, file=excel.source_name, warnings=excel.last_warnings, mode="merge" if merge else "replace",
                   added=n, duplicates=stats.get("duplicates", 0), no_imei=stats.get("no_imei", 0),
                   dup_imeis=stats.get("dup_imeis", []), total=stats.get("total", n),
                   data=build_data(th, filt_args(dict(filter="all")), "", 1, request.args.get("size")))


@app.get("/api/names")
@login_required
@need("fill_id")
def names():
    return jsonify(names=excel.names())


@app.post("/api/update_expiry")
@login_required
@need("expiry")
def update_expiry():
    """The customer renewed the service: new expiry date for the selected plates (Sent is cleared)."""
    p = request.get_json(silent=True) or {}
    day = parse_day(p.get("expiry_date"))
    if not day:
        return jsonify(error="Choose a valid expiry date."), 400
    ids = [int(i) for i in p.get("ids", []) if str(i).isdigit()]
    if not ids:
        return jsonify(error="Select at least one plate first."), 400
    if bot.running:
        return jsonify(error="Wait for the running batch to finish."), 409
    try:
        changes = excel.update_expiry(ids, day, g.user["username"])
    except Exception as e:
        return jsonify(error=f"Could not save ({type(e).__name__}): {e}"), 500
    n = len(changes)
    log_changes([dict(action="expiry", **c) for c in changes])
    logs.add("info", f"{g.user['username']} set a new expiry date {day} on {n} plate(s).")
    return jsonify(updated=n, expiry_date=day)


@app.post("/api/set_user")
@login_required
@need("fill_id")
def set_user():
    """Apply one Username/ID to every plate with this Name."""
    p = request.get_json(silent=True) or {}
    if bot.running:
        return jsonify(error="Wait for the running batch to finish."), 409
    try:
        changes = excel.set_user(p.get("name"), p.get("user"))
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        return jsonify(error=f"Could not save ({type(e).__name__}): {e}"), 500
    n = len(changes)
    if not n:
        return jsonify(error=f"No plate has the Name '{str(p.get('name') or '').strip()}'."), 404
    log_changes([dict(action="user", **c) for c in changes])
    logs.add("info", f"{g.user['username']} set Username/ID on {n} plate(s) named {str(p.get('name')).strip()}.")
    return jsonify(updated=n)


@app.get("/api/template")
@login_required
def template_file():
    return send_file(excel.template(), as_attachment=True, download_name="clients_template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/api/export")
@login_required
@need("export")
def export():
    q, f = request.args.get("q", "").strip().lower()[:80], filt_args()
    rows = [r for r in excel.records(*thresholds()) if in_filter(r, f) and matches(r, q)]
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


def master_rows(d_from, d_to):
    """Report master: one line per send run, filtered by date, IMEI and user."""
    out = []
    for b in history.batches(d_from, d_to, request.args.get("imei", ""), request.args.get("ruser", "")):
        b["period"] = "" if b["lo"] is None else (f"{b['lo']}" if b["lo"] == b["hi"] else f"{b['lo']}–{b['hi']}")
        out.append(b)
    return out


def change_groups(d_from, d_to):
    """Admin changes master: rows done by the same admin, same action, same moment are ONE line."""
    groups = {}
    for r in history.changes(request.args.get("ctype", "all"), d_from, d_to, request.args.get("cq", "")):
        k = (r["ts"], r["actor"], r["action"])
        g_ = groups.setdefault(k, dict(ts=r["ts"], actor=r["actor"], action=r["action"], count=0, names=[], note="", old=None, new=None))
        g_["count"] += 1
        if r["name"] and r["name"] not in g_["names"] and len(g_["names"]) < 4:
            g_["names"].append(r["name"])
        if r["action"] == "import":
            g_["note"] = r["new_value"]
        else:                                    # one value for the whole group (e.g. the new expiry date)? show it in the master
            g_["old"] = r["old_value"] if g_["old"] in (None, r["old_value"]) else ""
            g_["new"] = r["new_value"] if g_["new"] in (None, r["new_value"]) else ""
    return list(groups.values())


@app.get("/api/report")
@login_required
@need("report")
def report():
    status, d_from, d_to = report_args()
    return jsonify(summary=history.summary(d_from, d_to), days=history.days(d_from, d_to),
                   rows=history.rows(status, d_from, d_to), range=[d_from, d_to],
                   keep_from=history.keep_from(today_local()), master=master_rows(d_from, d_to),
                   change_groups=change_groups(d_from, d_to))


def unit_view(u):
    return dict(name=u["name"], user=u["user"], plate=u["plate"], imei=u["imei"], expiry=u["expiry"], status=u["status"],
                user_type=u.get("user_type") or "paid_off")


@app.get("/api/report/detail")
@login_required
@need("report")
def report_detail():
    """Report master -> Detail: the plates of one send run, split into Paid Off and Rental."""
    day, batch = parse_day(request.args.get("day")), str(request.args.get("batch", ""))[:20]
    if not day or not batch:
        return jsonify(error="Missing day / batch."), 400
    units = [unit_view(u) for u in history.batch_units(day, batch, request.args.get("imei", ""), request.args.get("ruser", ""))]

    def section(items):                                  # Client (Count) = how many plates this client got in this section
        per = Counter(u["user"] for u in items)
        for u in items:
            u["client_count"] = per[u["user"]]
        return dict(rows=items, clients=len(per))
    return jsonify(paid_off=section([u for u in units if u["user_type"] != "rental"]),
                   rental=section([u for u in units if u["user_type"] == "rental"]))


@app.get("/api/report/change_detail")
@login_required
@need("report")
def change_detail():
    ts, actor, action = str(request.args.get("ts", ""))[:19], str(request.args.get("actor", ""))[:64], str(request.args.get("action", ""))[:12]
    return jsonify(rows=history.change_detail(ts, actor, action))


@app.get("/api/report/export")
@login_required
@need("export")
def report_export():
    import io
    import pandas as pd
    status, d_from, d_to = report_args()
    ucols = ("name", "user_type", "plate", "imei", "expiry", "ts", "status")          # the plate list the person asked for
    units = pd.DataFrame([{k: safe_cell(r.get(k)) for k in ucols} for r in history.unit_rows(status, d_from, d_to)], columns=ucols)
    units.columns = ["name", "user_type", "plate", "imei", "expiry_date", "date_sent", "status"]
    master = pd.DataFrame([{"date": b["ts"], "type": b["kind"].title(), "period_days_left": b["period"], "plates_sent": b["sent"],
                            "plates_failed": b["failed"], "plates_skipped": b["skipped"], "paid_off_sent": b["paid_off"],
                            "rental_sent": b["rental"], "clients": b["clients"]} for b in master_rows(d_from, d_to)],
                          columns=("date", "type", "period_days_left", "plates_sent", "plates_failed", "plates_skipped",
                                   "paid_off_sent", "rental_sent", "clients"))
    chg = pd.DataFrame([{"date_time": safe_cell(r["ts"]), "admin": safe_cell(r["actor"]), "action": CHANGE_LABEL.get(r["action"], r["action"]),
                         "name": safe_cell(r["name"]), "plate": safe_cell(r["plate"]), "old": safe_cell(r["old_value"]),
                         "new": safe_cell(r["new_value"])}
                        for r in history.changes(request.args.get("ctype", "all"), d_from, d_to, request.args.get("cq", ""), 100000)],
                       columns=("date_time", "admin", "action", "name", "plate", "old", "new"))
    cols = ("ts", "user", "units", "plates", "status", "reason", "detail", "sent_by")
    detail = pd.DataFrame([{k: safe_cell(r[k]) for k in cols} for r in history.rows(status, d_from, d_to, 100000)], columns=cols)
    by_day = pd.DataFrame(history.days(d_from, d_to), columns=("day", "total", "sent", "failed", "skipped"))
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        master.to_excel(w, sheet_name="Master", index=False)
        units.to_excel(w, sheet_name="Plates", index=False)
        chg.to_excel(w, sheet_name="Changes", index=False)
        by_day.to_excel(w, sheet_name="By day", index=False)
        detail.to_excel(w, sheet_name="Report", index=False)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="gps_send_report.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ---------- admin users ----------
def protected(u):
    """Stops privilege escalation: only the main admin may touch the main admin or another user-manager."""
    if not is_main_admin(g.user) and u["id"] != g.user["id"] and (is_main_admin(u) or "users" in perms_of(u)):
        return jsonify(error="Only the main admin can change this account."), 403
    return None


def public_user(u):
    return dict(id=u["id"], username=u["username"], active=bool(u["is_active"]), created_at=u["created_at"],
                last_login=u["last_login"] or "", me=u["id"] == g.user["id"], main=is_main_admin(u),
                permissions=[p for p in PERMS if p in perms_of(u)])


@app.get("/api/users")
@login_required
@need("users")
def users_list():
    return jsonify(users=[public_user(u) for u in accounts.list()])


@app.post("/api/users")
@login_required
@need("users")
def users_add():
    p = request.get_json(silent=True) or {}
    name, pw = str(p.get("username", "")).strip().lower(), str(p.get("password", ""))
    if not USER_RE.match(name):
        return jsonify(error="Username: 3-32 characters, letters, numbers, . _ - only."), 400
    if (msg := check_password(pw, name)):
        return jsonify(error=msg), 400
    if accounts.get_by_name(name):
        return jsonify(error="That username already exists."), 409
    perms = clean_perms(p.get("permissions")) if "permissions" in p else DEFAULT_PERMS
    if "users" in perms and not is_main_admin(g.user):
        return jsonify(error="Only the main admin can create another Admin."), 403
    accounts.create(name, generate_password_hash(pw, method="scrypt"), ",".join(perms))
    logs.add("info", f"{g.user['username']} created user {name} (permissions: {', '.join(perms) or 'none'}).")
    return jsonify(ok=True)


@app.post("/api/users/<int:uid>/password")
@login_required
@need("users")
def users_password(uid):
    u = accounts.get(uid)
    pw = str((request.get_json(silent=True) or {}).get("password", ""))
    if not u:
        return jsonify(error="User not found."), 404
    if (deny := protected(u)):
        return deny
    if (msg := check_password(pw, u["username"])):
        return jsonify(error=msg), 400
    new_hash = generate_password_hash(pw, method="scrypt")
    accounts.set_password(uid, new_hash)
    if uid == g.user["id"]:
        session["pw"] = pw_stamp(new_hash)             # keep MY session; every other session of this user is signed out
    logs.add("info", f"{g.user['username']} changed the password of {u['username']}.")
    return jsonify(ok=True)


@app.post("/api/users/<int:uid>/permissions")
@login_required
@need("users")
def users_permissions(uid):
    u = accounts.get(uid)
    if not u:
        return jsonify(error="User not found."), 404
    if is_main_admin(u):
        return jsonify(error=f"'{u['username']}' is the main admin and always has every permission."), 400
    perms = clean_perms((request.get_json(silent=True) or {}).get("permissions"))
    if (deny := protected(u)):
        return deny
    if "users" in perms and "users" not in perms_of(u) and not is_main_admin(g.user):
        return jsonify(error="Only the main admin can make someone an Admin."), 403
    if uid == g.user["id"] and "users" not in perms:
        return jsonify(error="You cannot remove your own 'manage users' permission."), 400
    accounts.set_permissions(uid, ",".join(perms))
    logs.add("info", f"{g.user['username']} set permissions of {u['username']}: {', '.join(perms) or 'none'}.")
    return jsonify(ok=True, permissions=perms)


@app.post("/api/users/<int:uid>/active")
@login_required
@need("users")
def users_active(uid):
    u = accounts.get(uid)
    if not u:
        return jsonify(error="User not found."), 404
    if uid == g.user["id"]:
        return jsonify(error="You cannot disable your own account."), 400
    if (deny := protected(u)):
        return deny
    active = bool((request.get_json(silent=True) or {}).get("active"))
    accounts.set_active(uid, active)
    logs.add("info", f"{g.user['username']} {'enabled' if active else 'disabled'} {u['username']}.")
    return jsonify(ok=True)


@app.post("/api/users/<int:uid>/delete")
@login_required
@need("users")
def users_delete(uid):
    u = accounts.get(uid)
    if not u:
        return jsonify(error="User not found."), 404
    if uid == g.user["id"]:
        return jsonify(error="You cannot delete your own account."), 400
    if (deny := protected(u)):
        return deny
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
