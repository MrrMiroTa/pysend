"""Sign in / out, session + CSRF guard, security headers, permission decorators, error pages."""
import re
import secrets
import time
from functools import wraps

from flask import Blueprint, abort, current_app, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from security import apply_headers, pw_stamp
from .permissions import perms_of
from .services import DUMMY_HASH, IP_THROTTLE, USER_THROTTLE, accounts, engine, logs

bp = Blueprint("auth", __name__)


def login_required(f):
    @wraps(f)
    def wrap(*a, **k):
        u = accounts.get(session["uid"]) if session.get("uid") else None
        if not u or not u["is_active"]:  # a disabled/deleted user is signed out immediately
            session.clear()
            return (jsonify(error="Not signed in"), 401) if request.path.startswith("/api/") \
                else redirect(url_for("auth.login"))
        if session.get("pw") != pw_stamp(u["password_hash"]):   # password was changed since this sign-in -> sign in again
            session.clear()
            return (jsonify(error="Signed out: the password changed. Sign in again."), 401) if request.path.startswith("/api/") \
                else redirect(url_for("auth.login"))
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


@bp.get("/healthz")
def healthz():  # for uptime monitors / deployment checks
    from sqlalchemy import text
    with engine.connect() as c:
        c.execute(text("SELECT 1"))
    return "ok"


@bp.route("/login", methods=["GET", "POST"])
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
                return redirect(url_for("dashboard.index"))
            IP_THROTTLE.fail(ip)
            USER_THROTTLE.fail(name)
            logs.add("warn", f"Failed sign-in attempt for '{re.sub(r'[^a-z0-9_.-]', '?', name)[:32]}'.")
            time.sleep(1)                             # slow down guessing
            err = "Wrong username or password."
    return render_template("login.html", csrf=session["csrf"], error=err)


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.app_errorhandler(500)
def server_error(e):
    current_app.logger.exception("Unhandled error")           # details stay in the server log, never in the response
    if request.path.startswith("/api/"):
        return jsonify(error="Server error. Try again; if it repeats check the server log."), 500
    return "Server error", 500


@bp.app_errorhandler(400)
@bp.app_errorhandler(413)
def api_errors(e):
    if request.path.startswith("/api/"):
        msg = "File too large (maximum 10 MB)." if e.code == 413 else "Request rejected. Refresh the page (Ctrl+F5) and try again."
        return jsonify(error=msg), e.code
    return e


@bp.before_app_request
def guard():
    session.permanent = True
    session.setdefault("csrf", secrets.token_hex(16))
    if request.method not in ("GET", "HEAD", "OPTIONS"):  # CSRF: every state-changing request needs the token
        sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
        if not secrets.compare_digest(sent, session["csrf"]):
            abort(400, "Bad CSRF token")


@bp.after_app_request
def headers(r):
    return apply_headers(r, current_app.config["SESSION_COOKIE_SECURE"])
