"""Dashboard: the client list, sending reminders, import / export, fill Username-ID, update expiry."""

from flask import Blueprint, current_app, g, jsonify, render_template, request, send_file, session

from excel_manager import RENTAL_DEFAULT
from security import check_upload
from telegram_bot import CHUNK, group_rows
from .auth import login_required, need
from .changelog import log_changes
from .clientlist import build_data, clean_phone, filt_args, in_filter, matches, pick_rows, thresholds
from .config import CFG, clamp
from .report import parse_day
from .services import bot, excel, logs

bp = Blueprint("dashboard", __name__)


@bp.get("/")
@login_required
def index():
    return render_template("index.html", csrf=session["csrf"], max_run=CFG["MAX_PER_RUN"], username=g.user["username"],
                           phone=CFG["CONTACT_PHONE"], perms=",".join(sorted(g.perms)), rental_days=RENTAL_DEFAULT)


@bp.get("/api/data")
@login_required
def data():
    try:
        return jsonify(build_data(thresholds(), filt_args(), request.args.get("q", ""),
                                  request.args.get("page"), request.args.get("size"),
                                  request.args.get("sort"), request.args.get("dir", "asc")))
    except Exception as e:
        return jsonify(error=f"Cannot read Excel: {e}"), 400


@bp.get("/api/ids")
@login_required
def ids_matching():
    """IDs of every unit matching the current filter/search ('select all matching')."""
    f, q = filt_args(), request.args.get("q", "").strip().lower()[:80]
    return jsonify(ids=[r["id"] for r in excel.records(*thresholds()) if in_filter(r, f) and matches(r, q)][:100000])


@bp.post("/api/preview")
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


@bp.post("/api/send")
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


@bp.post("/api/stop")
@login_required
@need("send")
def stop():
    bot.stop()
    return jsonify(ok=True)


@bp.get("/api/status")
@login_required
def status():
    since = clamp(request.args.get("since"), 0, 10**9, 0)
    return jsonify(running=bot.running, progress=bot.progress, logs=logs.since(since), data_version=excel.version)


@bp.post("/api/upload")
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
        current_app.logger.exception("Upload failed")  # full traceback in the terminal
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


@bp.get("/api/names")
@login_required
@need("fill_id")
def names():
    return jsonify(names=excel.names())


@bp.post("/api/update_expiry")
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


@bp.post("/api/set_user")
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


@bp.get("/api/template")
@login_required
def template_file():
    return send_file(excel.template(), as_attachment=True, download_name="clients_template.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@bp.get("/api/export")
@login_required
@need("export")
def export():
    q, f = request.args.get("q", "").strip().lower()[:80], filt_args()
    rows = [r for r in excel.records(*thresholds()) if in_filter(r, f) and matches(r, q)]
    return send_file(excel.export(rows), as_attachment=True, download_name="gps_expiry_export.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
