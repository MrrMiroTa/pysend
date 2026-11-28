"""Admin users and their permissions (Users tab)."""

from flask import Blueprint, g, jsonify, request, session
from werkzeug.security import generate_password_hash

from security import password_problem, pw_stamp
from .auth import login_required, need
from .permissions import DEFAULT_PERMS, PERMS, clean_perms, is_main_admin, perms_of
from .services import USER_RE, accounts, logs

bp = Blueprint("users", __name__)


def check_password(pw, username=""):
    return password_problem(pw, username)


def protected(u):
    """Stops privilege escalation: only the main admin may touch the main admin or another user-manager."""
    if not is_main_admin(g.user) and u["id"] != g.user["id"] and (is_main_admin(u) or "users" in perms_of(u)):
        return jsonify(error="Only the main admin can change this account."), 403
    return None


def public_user(u):
    return dict(id=u["id"], username=u["username"], active=bool(u["is_active"]), created_at=u["created_at"],
                last_login=u["last_login"] or "", me=u["id"] == g.user["id"], main=is_main_admin(u),
                permissions=[p for p in PERMS if p in perms_of(u)])


@bp.get("/api/users")
@login_required
@need("users")
def users_list():
    return jsonify(users=[public_user(u) for u in accounts.list()])


@bp.post("/api/users")
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


@bp.post("/api/users/<int:uid>/password")
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


@bp.post("/api/users/<int:uid>/permissions")
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


@bp.post("/api/users/<int:uid>/active")
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


@bp.post("/api/users/<int:uid>/delete")
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
