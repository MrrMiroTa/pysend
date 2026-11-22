"""ExcelManager: all spreadsheet reading/writing. Thread-safe and crash-safe."""
import atexit, io, os, re, tempfile, threading, time
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd
from timeutil import now as now_local, today as today_local

COLUMNS = ["user", "type", "plate", "imei", "expiry_date", "status", "sent_at"]
# Header names we accept (compared lower-case, ignoring spaces / _ / - / "/"). Khmer headers too.
SYNONYMS = {
    "user": "user userid username userorid useridorusername telegram telegramid telegramuser telegramusername chatid client clientid contact",
    "type": "type clienttype customertype category ប្រភេទ",
    "plate": "plate platenumber platenum plateno licenseplate licenceplate vehicle vehicleplate ស្លាកលេខ",
    "imei": "imei imeino imeinumber deviceimei",
    "expiry_date": "expirydate expirationdate expiry expire expiredate expiration expdate enddate duedate ថ្ងៃផុតកំណត់",
    "status": "status", "sent_at": "sentat",
}
SYN = {k: canon for canon, words in SYNONYMS.items() for k in words.split()}


def _key(name):
    return re.sub(r"[^0-9a-zA-Z\u1780-\u17ff]+", "", str(name)).lower()
SOON = 15  # days: above this a unit is "safe" (green)


def _read(path):
    """Read the FIRST sheet (header in row 1). Only the 7 required columns are kept; every other column
    (notes, etc.) is ignored. If any of the 7 is missing the whole file is rejected."""
    if path.lower().endswith(".csv"):
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")  # utf-8-sig: Excel-saved CSV with Khmer
    else:
        df = pd.read_excel(path, dtype=str, engine="openpyxl").fillna("")  # str keeps IMEI & Khmer intact
    found = [str(c).strip() for c in df.columns]
    keys = [_key(c) for c in found]
    picked = {}                                    # required column -> position in the file
    for canon in COLUMNS:                          # 1st: exact names (user, type, plate, imei, expiry_date, status, sent_at)
        if _key(canon) in keys:
            picked[canon] = keys.index(_key(canon))
    for pos, k in enumerate(keys):                 # 2nd: friendly alternative names, only for what is still missing
        canon = SYN.get(k)
        if canon and canon not in picked and pos not in picked.values():
            picked[canon] = pos
    if "user" not in picked and "id" in keys:      # a bare "ID" column = last resort for user
        picked["user"] = keys.index("id")
    missing = [c for c in COLUMNS if c not in picked]
    if missing:
        raise ValueError(
            f"Missing column(s): {', '.join(missing)}. The file must contain ALL 7 columns: {', '.join(COLUMNS)} "
            f"(other columns are ignored). Columns found: {', '.join(found[:15]) or 'none'}. "
            "Use the template button to get a correct file. "
            "ឯកសារត្រូវមាន column ទាំង 7 គ្រប់គ្រាន់ ទើប import បាន (column ផ្សេងៗត្រូវបានរំលង)។")
    df = df.iloc[:, [picked[c] for c in COLUMNS]].copy()   # keep ONLY the 7, in this order
    df.columns = COLUMNS
    for col in COLUMNS:
        df[col] = df[col].astype(str).str.strip()
    blank = (df[["user", "type", "plate", "imei", "expiry_date"]] == "").all(axis=1)  # empty/formatted-only rows
    df = df[~blank]
    rows_xl = (df.index + 2).tolist()              # row numbers as Excel shows them (row 1 = header)
    df = df.reset_index(drop=True)
    raw = df["expiry_date"]
    d = pd.to_datetime(raw, format="ISO8601", errors="coerce")        # 2026-11-10 / Excel date cells
    rest = d.isna() & (raw != "")
    if rest.any():                                                     # 10-11-2026 or 10/11/2026 = day first
        d[rest] = pd.to_datetime(raw[rest], dayfirst=True, errors="coerce", format="mixed")
    df["expiry_date"] = d.dt.strftime("%Y-%m-%d").fillna("")
    df["type"] = df["type"].replace("", "Normal")
    df["status"] = df["status"].map(lambda v: "Sent" if v.lower() == "sent" else "")
    warns = []
    for label, mask in (("have no user", df["user"] == ""), ("have no valid expiry date", df["expiry_date"] == "")):
        idx = [rows_xl[k] for k in mask[mask].index]
        if idx:
            warns.append(f"{len(idx)} row(s) {label} (Excel rows {', '.join(map(str, idx[:8]))}{'…' if len(idx) > 8 else ''})")
    df.attrs["warnings"] = warns
    return df


def safe_cell(v):
    """Neutralise spreadsheet formula injection (=,+,-,@) in exported cells."""
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


class ExcelManager:
    """The client list. Built for tens of thousands of units:
       * the sheet is read from disk ONCE and kept in memory (no re-reading Excel on every click),
       * 'Sent' marks are applied in memory instantly and written to the file in the background
         (at most every few seconds, and always at the end of a batch / on shutdown),
       * the computed list is cached until something changes."""
    FLUSH_DELAY = 3.0

    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        self._save_lock = threading.Lock()
        self._name_file = os.path.join(os.path.dirname(os.path.abspath(path)), "source_name.txt")
        self._df, self._version, self._dirty, self._timer = None, 0, False, None
        self._cache = {}
        self.save_error = ""
        self.last_warnings = []
        atexit.register(self._flush_quiet)

    @property
    def source_name(self):
        try:
            return open(self._name_file, encoding="utf-8").read().strip() or os.path.basename(self.path)
        except OSError:
            return os.path.basename(self.path)

    # ---- disk ----
    def _save(self, df):
        path = self.path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        fd, tmp = tempfile.mkstemp(suffix=".xlsx", dir=os.path.dirname(os.path.abspath(path)))
        os.close(fd)
        df.to_excel(tmp, index=False, engine="openpyxl")
        for attempt in range(6):  # Windows: antivirus/Excel can hold the file for a moment
            try:
                os.replace(tmp, path)  # atomic: never leaves a half-written file
                return
            except PermissionError:
                if attempt == 5:
                    try: os.remove(tmp)
                    except OSError: pass
                    raise PermissionError(f"Cannot write {path}. Close it in Excel / check folder permissions.")
                time.sleep(1)

    def _load(self):  # lock held
        if self._df is None:
            self._df = _read(self.path) if os.path.exists(self.path) else pd.DataFrame(columns=COLUMNS)
        return self._df

    def _changed(self):  # lock held
        self._version += 1
        self._cache.clear()
        self._dirty = True
        if self._timer is None:
            self._timer = threading.Timer(self.FLUSH_DELAY, self._flush_quiet)
            self._timer.daemon = True
            self._timer.start()

    def flush(self, raise_errors=False):
        """Write pending changes to the Excel file now."""
        with self.lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            if not self._dirty or self._df is None:
                return
            snap, self._dirty = self._df.copy(), False
        try:
            with self._save_lock:
                self._save(snap)
            self.save_error = ""
        except Exception as e:
            self.save_error = f"{type(e).__name__}: {e}"
            with self.lock:
                self._dirty = True
                if self._timer is None:  # try again in 10 s
                    self._timer = threading.Timer(10, self._flush_quiet)
                    self._timer.daemon = True
                    self._timer.start()
            if raise_errors:
                raise

    def _flush_quiet(self):
        try:
            self.flush()
        except Exception:
            pass

    # ---- data ----
    def records(self, normal_days, company_days, today=None):
        today = today or today_local()
        key = (normal_days, company_days, today)
        with self.lock:
            hit = self._cache.get(key)
            if hit is not None:
                return hit
            df = self._load()
            exp = pd.to_datetime(df["expiry_date"], errors="coerce")
            days = (exp - pd.Timestamp(today)).dt.days
            thr = np.where(df["type"].str.lower().str.startswith("comp"), company_days, normal_days)
            sent = (df["status"].str.lower() == "sent").to_numpy()
            d = days.to_numpy(dtype="float64", na_value=np.nan)
            state = np.select([sent, np.isnan(d), d < 0, d <= thr, d <= np.maximum(SOON, thr)],
                              ["sent", "invalid", "expired", "due", "approaching"], default="safe")
            out = [dict(id=i, user=u, type=t or "Normal", plate=p, imei=m, expiry=e,
                        days=(None if x != x else int(x)), state=s, sent_at=a)
                   for i, u, t, p, m, e, x, s, a in zip(range(len(df)), df["user"], df["type"], df["plate"], df["imei"],
                                                        df["expiry_date"], d.tolist(), state.tolist(), df["sent_at"])]
            self._cache = {key: out}
            return out

    def mark_sent(self, ids):
        """Instant (in memory). The file is written in the background, or by flush()."""
        with self.lock:
            df = self._load()
            ok = [int(i) for i in ids if 0 <= int(i) < len(df)]
            if ok:
                df.loc[ok, "status"] = "Sent"
                df.loc[ok, "sent_at"] = now_local().strftime("%Y-%m-%d %H:%M")
                self._changed()

    def replace_from_upload(self, file_storage):
        """Validate an uploaded workbook fully before it replaces the current list."""
        ext = ".csv" if file_storage.filename.lower().endswith(".csv") else ".xlsx"
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        fd, tmp = tempfile.mkstemp(suffix=ext, dir=os.path.dirname(os.path.abspath(self.path)))
        os.close(fd)
        try:
            file_storage.save(tmp)
            df = _read(tmp)  # raises on bad format / missing columns
            self.last_warnings = list(df.attrs.get("warnings", []))
            with self.lock:
                self._df = df
                self._changed()
                open(self._name_file, "w", encoding="utf-8").write(
                    os.path.basename(file_storage.filename.replace("\\", "/"))[:80])
            self.flush(raise_errors=True)
            return len(df)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    @staticmethod
    def export(rows):
        """Same 7 columns the importer needs (so the file can be imported again) + info columns that import ignores."""
        df = pd.DataFrame([{"user": safe_cell(r["user"]), "type": safe_cell(r["type"]), "plate": safe_cell(r["plate"]),
                            "imei": safe_cell(r["imei"]), "expiry_date": r["expiry"],
                            "status": "Sent" if r["state"] == "sent" else "", "sent_at": safe_cell(r["sent_at"]),
                            "days_remaining": r["days"], "state": r["state"]} for r in rows],
                          columns=COLUMNS + ["days_remaining", "state"])
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return buf

    @staticmethod
    def template():
        nxt = (today_local() + timedelta(days=10)).isoformat()
        df = pd.DataFrame([["@username", "Normal", "ភ្នំពេញ 2A-1234", "862012345678901", nxt, "", ""],
                           ["123456789", "Company", "សៀមរាប 1C-4321", "862012345678902", nxt, "", ""]], columns=COLUMNS)
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        return buf
