"""Create an admin login user, or reset a password (also the way back in if you forget it).
   python scripts/create_user.py admin2
   python scripts/create_user.py admin --reset      (set a new password and re-enable the account)"""
import argparse, getpass, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"), interpolate=False)
from werkzeug.security import generate_password_hash
from database import UserStore, database_url, make_engine

ap = argparse.ArgumentParser()
ap.add_argument("username")
ap.add_argument("--reset", action="store_true", help="change the password of an existing user")
a = ap.parse_args()
name = a.username.strip().lower()
if not re.match(r"^[a-z0-9_.-]{3,32}$", name):
    sys.exit("Username: 3-32 characters, letters, numbers, . _ - only.")
store = UserStore(make_engine(database_url(ROOT)))
user = store.get_by_name(name)
if user and not a.reset:
    sys.exit(f"User '{name}' already exists. Use --reset to change the password.")
if not user and a.reset:
    sys.exit(f"User '{name}' does not exist.")
pw = getpass.getpass("Password (10+ characters): ")
if len(pw) < 10 or pw != getpass.getpass("Repeat password: "):
    sys.exit("Passwords must match and be at least 10 characters.")
h = generate_password_hash(pw, method="scrypt")
if user:
    store.set_password(user["id"], h)
    store.set_active(user["id"], True)
    print(f"Password changed for '{name}'.")
else:
    store.create(name, h)
    print(f"User '{name}' created.")
