"""Create the database tables (users, send_log).
   python scripts/init_db.py                 create tables
   python scripts/init_db.py --old-history   copy the old data/history.sqlite3 report into the database"""
import argparse, os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"), interpolate=False)
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from database import History, database_url, make_engine, send_log, users

ap = argparse.ArgumentParser()
ap.add_argument("--old-history", action="store_true", help="import data/history.sqlite3 from older versions")
a = ap.parse_args()

url = database_url(ROOT)
try:
    engine = make_engine(url)  # creates tables if missing
except Exception as e:
    sys.exit(f"Cannot connect to the database: {type(e).__name__}. Check DATABASE_URL in .env "
             f"(host, user, password, database name) and that MariaDB/MySQL is running.\n{str(e)[:300]}")
print("Database:", make_url(url).render_as_string(hide_password=True))
print("Tables ready: users, send_log")

if a.old_history:
    old = os.path.join(ROOT, "data", "history.sqlite3")
    if not os.path.exists(old):
        sys.exit("No old history file found.")
    h, con = History(engine), sqlite3.connect(old)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM send_log ORDER BY id").fetchall()
    for r in rows:
        h.add(r["ts"], r["batch"], r["user"], r["units"], r["plates"] or "", r["status"], r["reason"] or "", r["detail"] or "")
    print(f"Copied {len(rows)} old report row(s)")

with engine.connect() as c:
    print("users:", c.execute(select(func.count()).select_from(users)).scalar(),
          "| send_log rows:", c.execute(select(func.count()).select_from(send_log)).scalar())
