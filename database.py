"""Database layer (SQLAlchemy 2.x). It stores ONLY two things:
   users     - admin login accounts
   send_log  - the Report (one row per client message attempt, with the day)
SQLite by default (zero setup). MySQL/MariaDB/PostgreSQL via DATABASE_URL."""
import calendar, os, re
from datetime import date

from sqlalchemy import (Boolean, Column, Integer, MetaData, String, Table, case, create_engine, delete,
                        event, func, inspect, insert, select, text, update)
from sqlalchemy.engine import make_url

from timeutil import now

md = MetaData()
users = Table(
    "users", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(64), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("created_at", String(19), default=""),
    Column("last_login", String(19), default=""),
)
send_log = Table(
    "send_log", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ts", String(19), index=True),                       # 2026-11-09 14:24:20
    Column("day", String(10), index=True),                      # 2026-11-09  (report by day)
    Column("batch", String(20)),
    Column("user", String(190)),                                # client @username / ID
    Column("units", Integer),
    Column("plates", String(400)),
    Column("status", String(10), index=True),                   # sent / failed / skipped
    Column("reason", String(300)),
    Column("detail", String(500)),
    Column("sent_by", String(64)),                              # which admin pressed Send
)


send_unit_log = Table(                                          # the Report, one row per plate (for the Excel export)
    "send_unit_log", md,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ts", String(19), index=True),                       # date + time sent
    Column("day", String(10), index=True),
    Column("batch", String(20)),
    Column("user", String(190)),
    Column("name", String(190)),                                # e.g. WL112
    Column("plate", String(190)),
    Column("imei", String(64)),
    Column("expiry", String(32)),
    Column("status", String(10), index=True),                   # sent / failed / skipped
)

RETENTION_MONTHS = 3                                            # the Report keeps only the last 3 months


def months_before(d, n=RETENTION_MONTHS):
    """Same calendar day n months earlier (clamped to the month's length)."""
    y, m = d.year, d.month - n
    while m < 1:
        m, y = m + 12, y - 1
    return d.replace(year=y, month=m, day=min(d.day, calendar.monthrange(y, m)[1]))


def data_dir(base):
    """Where files live. Default ./data ; on Render set DATA_DIR to the persistent disk mount (e.g. /var/data)."""
    return os.path.abspath(os.getenv("DATA_DIR") or os.path.join(base, "data"))


def database_url(base):
    url = (os.getenv("DATABASE_URL") or "").strip()
    for prefix in ("postgres://", "postgresql://"):  # Render/Heroku style -> the psycopg2 driver we ship
        if url.startswith(prefix):
            url = "postgresql+psycopg2://" + url[len(prefix):]
    if not url:
        return "sqlite:///" + os.path.join(data_dir(base), "app.sqlite3").replace("\\", "/")
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////") and not re.match(r"sqlite:///[A-Za-z]:", url):
        return "sqlite:///" + os.path.join(base, url[len("sqlite:///"):]).replace("\\", "/")
    return url


def make_engine(url):
    kw = dict(pool_pre_ping=True)
    sqlite = url.startswith("sqlite")
    if sqlite:
        kw["connect_args"] = {"check_same_thread": False, "timeout": 30}
        db = make_url(url).database
        if db:
            os.makedirs(os.path.dirname(os.path.abspath(db)), exist_ok=True)
    else:
        kw["pool_recycle"] = 1800
    eng = create_engine(url, **kw)
    if sqlite:
        @event.listens_for(eng, "connect")
        def _pragma(dbapi, _):  # WAL: readers don't block the sender thread
            cur = dbapi.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()
    md.create_all(eng)
    cols = {c["name"] for c in inspect(eng).get_columns("send_log")}  # upgrade tables from older versions
    with eng.begin() as c:
        if "day" not in cols:
            c.execute(text("ALTER TABLE send_log ADD COLUMN day VARCHAR(10)"))
            c.execute(text("UPDATE send_log SET day=SUBSTR(ts,1,10)"))
        if "sent_by" not in cols:
            c.execute(text("ALTER TABLE send_log ADD COLUMN sent_by VARCHAR(64)"))
    return eng


def _stamp():
    return now().strftime("%Y-%m-%d %H:%M:%S")


class UserStore:
    """Admin login accounts."""
    def __init__(self, engine):
        self.e = engine

    def _one(self, where):
        with self.e.connect() as c:
            r = c.execute(select(users).where(where)).mappings().first()
            return dict(r) if r else None

    def get(self, uid):
        return self._one(users.c.id == uid)

    def get_by_name(self, name):
        return self._one(users.c.username == name)

    def count(self):
        with self.e.connect() as c:
            return c.execute(select(func.count()).select_from(users)).scalar()

    def list(self):
        with self.e.connect() as c:
            return [dict(r) for r in c.execute(select(users).order_by(users.c.id)).mappings()]

    def create(self, username, pw_hash):
        with self.e.begin() as c:
            return c.execute(insert(users).values(username=username, password_hash=pw_hash, is_active=True,
                                                  created_at=_stamp(), last_login="")).inserted_primary_key[0]

    def _set(self, uid, **vals):
        with self.e.begin() as c:
            c.execute(update(users).where(users.c.id == uid).values(**vals))

    def set_password(self, uid, pw_hash): self._set(uid, password_hash=pw_hash)
    def set_active(self, uid, active): self._set(uid, is_active=bool(active))
    def touch_login(self, uid): self._set(uid, last_login=_stamp())

    def delete(self, uid):
        with self.e.begin() as c:
            c.execute(delete(users).where(users.c.id == uid))


class History:
    """The Report. Every filter takes an optional day range (YYYY-MM-DD strings, inclusive)."""
    def __init__(self, engine):
        self.e = engine

    def add(self, ts, batch, user, units, plates, status, reason="", detail="", sent_by="", unit_rows=()):
        with self.e.begin() as c:
            c.execute(insert(send_log).values(
                ts=ts, day=ts[:10], batch=batch, user=user[:190], units=units, plates=plates[:400], status=status,
                reason=(reason or "")[:300], detail=(detail or "")[:500], sent_by=(sent_by or "")[:64]))
            if unit_rows:
                c.execute(insert(send_unit_log), [dict(
                    ts=ts, day=ts[:10], batch=batch, user=user[:190], name=(u.get("name") or "")[:190],
                    plate=(u.get("plate") or "")[:190], imei=(u.get("imei") or "")[:64],
                    expiry=(u.get("expiry") or "")[:32], status=status) for u in unit_rows])
        try:
            self.purge(date.fromisoformat(ts[:10]))                 # every new day pushes the oldest day out
        except Exception:
            pass                                                    # never lose a report row because cleanup failed

    @staticmethod
    def keep_from(today):
        """First day that is still kept: today minus 3 months (on 02-04 the data of 01-01 is gone)."""
        return months_before(today).isoformat()

    def purge(self, today):
        cut = self.keep_from(today)
        with self.e.begin() as c:
            n = c.execute(delete(send_log).where(send_log.c.day < cut)).rowcount or 0
            n += c.execute(delete(send_unit_log).where(send_unit_log.c.day < cut)).rowcount or 0
        return n

    def unit_rows(self, status="all", d_from=None, d_to=None, limit=100000):
        q = select(send_unit_log).order_by(send_unit_log.c.id.desc()).limit(limit)
        if status in ("sent", "failed", "skipped"):
            q = q.where(send_unit_log.c.status == status)
        if d_from:
            q = q.where(send_unit_log.c.day >= d_from)
        if d_to:
            q = q.where(send_unit_log.c.day <= d_to)
        with self.e.connect() as c:
            return [dict(r) for r in c.execute(q).mappings()]

    @staticmethod
    def _count(status):
        return func.coalesce(func.sum(case((send_log.c.status == status, 1), else_=0)), 0)

    @staticmethod
    def _range(q, d_from, d_to):
        if d_from:
            q = q.where(send_log.c.day >= d_from)
        if d_to:
            q = q.where(send_log.c.day <= d_to)
        return q

    def days(self, d_from=None, d_to=None, limit=400):
        q = select(send_log.c.day, func.count().label("total"), self._count("sent").label("sent"),
                   self._count("failed").label("failed"), self._count("skipped").label("skipped"))
        q = self._range(q, d_from, d_to).group_by(send_log.c.day).order_by(send_log.c.day.desc()).limit(limit)
        with self.e.connect() as c:
            return [{k: (v if k == "day" else int(v)) for k, v in r.items()} for r in c.execute(q).mappings()]

    def rows(self, status="all", d_from=None, d_to=None, limit=1000):
        q = select(send_log).order_by(send_log.c.id.desc()).limit(limit)
        if status in ("sent", "failed", "skipped"):
            q = q.where(send_log.c.status == status)
        with self.e.connect() as c:
            return [dict(r) for r in c.execute(self._range(q, d_from, d_to)).mappings()]

    def summary(self, d_from=None, d_to=None):
        q = select(func.count().label("total"), self._count("sent").label("sent"),
                   self._count("failed").label("failed"), self._count("skipped").label("skipped"),
                   func.count(func.distinct(case((send_log.c.status == "sent", send_log.c.user)))).label("clients_sent"))
        with self.e.connect() as c:
            return {k: int(v) for k, v in c.execute(self._range(q, d_from, d_to)).mappings().one().items()}
