"""Security helpers in one place: login throttle, password policy, upload checks, response headers."""
import hashlib, io, re, threading, time, zipfile

COMMON = {"password", "passw0rd", "12345678", "123456789", "1234567890", "qwerty123", "qwertyuiop", "iloveyou1", "admin1234",
          "administrator", "welcome123", "letmein123", "password1", "password123", "p@ssw0rd", "changeme123"}


class Throttle:
    """`limit` failures within `window` seconds lock that key for `lock` seconds. In memory (one process)."""
    def __init__(self, limit=5, window=900, lock=300, cap=20000):
        self.limit, self.window, self.lock, self.cap = limit, window, lock, cap
        self._d, self._m = {}, threading.Lock()

    def wait(self, key):
        """Seconds the key is still locked (0 = free)."""
        with self._m:
            e = self._d.get(key)
            return max(0, int(e[1] - time.time())) if e and e[1] > time.time() else 0

    def fail(self, key):
        now = time.time()
        with self._m:
            if len(self._d) > self.cap:                                   # forget old entries, never grow without limit
                self._d = {k: v for k, v in self._d.items() if v[2] > now - self.window}
            n, until, first = self._d.get(key, (0, 0, now))
            if now - first > self.window:
                n, first = 0, now
            n += 1
            self._d[key] = (n, now + self.lock if n >= self.limit else until, first)

    def ok(self, key):
        with self._m:
            self._d.pop(key, None)


def password_problem(pw, username=""):
    """None when the password is acceptable, else the reason."""
    if not (10 <= len(pw) <= 128):
        return "Password must be 10-128 characters."
    if pw.lower() == username.lower() or username.lower() and username.lower() in pw.lower():
        return "Password must not contain the username."
    if pw.lower() in COMMON or len(set(pw)) < 5 or pw.isdigit():
        return "Password is too easy to guess. Mix letters, numbers and symbols."
    return None


def pw_stamp(password_hash):
    """Changes whenever the password changes: sessions made before that are signed out."""
    return hashlib.sha256(("pw:" + str(password_hash)).encode()).hexdigest()[:16]


def check_upload(f, max_unzipped=120 * 1024 * 1024):
    """Reject a file whose CONTENT is not what its name says (the extension alone proves nothing). Returns an error text or None."""
    name, head = f.filename.lower(), f.stream.read(8192)
    f.stream.seek(0)
    if name.endswith((".xlsx", ".xlsm")):
        if not head.startswith(b"PK\x03\x04"):
            return "This is not a real Excel (.xlsx) file."
        try:
            with zipfile.ZipFile(io.BytesIO(f.stream.read())) as z:
                names = set(z.namelist())
                if "xl/workbook.xml" not in names:
                    return "This is not a real Excel (.xlsx) file."
                if sum(i.file_size for i in z.infolist()) > max_unzipped:      # zip-bomb guard
                    return "The Excel file is too large when unpacked."
        except zipfile.BadZipFile:
            return "The Excel file is damaged."
        finally:
            f.stream.seek(0)
    elif name.endswith(".csv") and (b"\x00" in head or head.startswith(b"PK\x03\x04")):
        return "This is not a real CSV text file."
    return None


def apply_headers(r, secure):
    r.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
                                            "font-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; "
                                            "base-uri 'none'; form-action 'self'")
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["Referrer-Policy"] = "no-referrer"
    r.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"
    r.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    r.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    r.headers["Cache-Control"] = "no-store"
    r.headers["X-Robots-Tag"] = "noindex, nofollow"
    if secure:
        r.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return r
