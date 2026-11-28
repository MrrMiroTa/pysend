"""The shared objects of the app (database, client list, Telegram bot, log, login throttle), created once at start-up."""
import os
import re
import sys

from werkzeug.security import generate_password_hash

from database import FileStore, History, UserStore, data_dir, database_url, make_engine
from excel_manager import ExcelManager
from security import Throttle
from telegram_bot import LogBuffer, TelegramBot
from timeutil import today as today_local
from .config import BASE, CFG
from .permissions import DEFAULT_PERMS, PERMS, is_main_admin, perms_of

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
