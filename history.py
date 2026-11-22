"""History: permanent send report in SQLite (one small file, no server needed)."""
import os, sqlite3, threading
from contextlib import closing

SCHEMA = """CREATE TABLE IF NOT EXISTS send_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, batch TEXT, user TEXT, units INTEGER,
  plates TEXT, status TEXT, reason TEXT, detail TEXT)"""


class History:
    def __init__(self, path):
        self.path, self.lock = path, threading.Lock()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._run(SCHEMA)

    def _run(self, sql, args=(), fetch=False):
        with self.lock, closing(sqlite3.connect(self.path, timeout=10)) as c:
            c.row_factory = sqlite3.Row
            cur = c.execute(sql, args)
            out = [dict(r) for r in cur.fetchall()] if fetch else None
            c.commit()
            return out

    def add(self, ts, batch, user, units, plates, status, reason="", detail=""):
        self._run("INSERT INTO send_log(ts,batch,user,units,plates,status,reason,detail) VALUES(?,?,?,?,?,?,?,?)",
                  (ts, batch, user, units, plates, status, reason, detail[:500]))

    def batches(self, limit=30):
        return self._run("""SELECT batch, MIN(ts) AS started, COUNT(*) AS total,
            SUM(status='sent') AS sent, SUM(status='failed') AS failed, SUM(status='skipped') AS skipped
            FROM send_log GROUP BY batch ORDER BY batch DESC LIMIT ?""", (limit,), True)

    def rows(self, status="all", batch="all", limit=1000):
        where, args = [], []
        if status in ("sent", "failed", "skipped"):
            where.append("status=?"); args.append(status)
        if batch not in ("all", ""):
            where.append("batch=?"); args.append(batch)
        sql = "SELECT * FROM send_log" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id DESC LIMIT ?"
        return self._run(sql, (*args, limit), True)

    def summary(self, batch="all"):
        w, a = ("WHERE batch=?", (batch,)) if batch not in ("all", "") else ("", ())
        r = self._run(f"""SELECT COUNT(*) AS total, COALESCE(SUM(status='sent'),0) AS sent,
            COALESCE(SUM(status='failed'),0) AS failed, COALESCE(SUM(status='skipped'),0) AS skipped
            FROM send_log {w}""", a, True)[0]
        return r
