"""Client-list logic for the Dashboard: threshold / filter parsing, which units to send, one page of rows + stats."""
import os
import re
from collections import Counter

from flask import request

from excel_manager import RENTAL_DEFAULT
from .config import clamp
from .services import excel


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
