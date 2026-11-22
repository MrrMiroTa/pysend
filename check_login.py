import getpass
from dotenv import dotenv_values
from werkzeug.security import check_password_hash

v = dotenv_values(".env", interpolate=False)
h = v.get("ADMIN_PASSWORD_HASH") or ""
print("ADMIN_USER      :", repr(v.get("ADMIN_USER")))
print("hash starts with:", h[:18], "| length:", len(h), "(expect ~160+)")
try:
    print("PASSWORD MATCH  :", check_password_hash(h, getpass.getpass("Password: ")))
except Exception as e:
    print("HASH IS INVALID :", e)