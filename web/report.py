"""Report: master / detail of every send, daily results, admin changes, Excel export."""
import io
from datetime import date, timedelta

from flask import Blueprint, jsonify, request, send_file

from excel_manager import safe_cell
from timeutil import today as today_local
from .auth import login_required, need
from .changelog import CHANGE_LABEL
from .services import history

bp = Blueprint("report", __name__)


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


@bp.get("/api/report")
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


@bp.get("/api/report/detail")
@login_required
@need("report")
def report_detail():
    """Report master -> Detail: the plates of one send run, split into Paid Off and Rental."""
    day, batch = parse_day(request.args.get("day")), str(request.args.get("batch", ""))[:20]
    if not day or not batch:
        return jsonify(error="Missing day / batch."), 400
    units = [unit_view(u) for u in history.batch_units(day, batch, request.args.get("imei", ""), request.args.get("ruser", ""))]

    def section(items):                                  # Client (Count) = how many different user accounts got a message
        return dict(rows=items, clients=len({u["user"] for u in items if u["status"] == "sent"}))
    return jsonify(paid_off=section([u for u in units if u["user_type"] != "rental"]),
                   rental=section([u for u in units if u["user_type"] == "rental"]))


@bp.get("/api/report/change_detail")
@login_required
@need("report")
def change_detail():
    ts, actor, action = str(request.args.get("ts", ""))[:19], str(request.args.get("actor", ""))[:64], str(request.args.get("action", ""))[:12]
    return jsonify(rows=history.change_detail(ts, actor, action))


@bp.get("/api/report/export")
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
