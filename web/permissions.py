"""Who may do what. Permissions are set per user by an admin (Users tab); the account named ADMIN_USER always has all of them."""
import os


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
