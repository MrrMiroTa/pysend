"""TelegramBot: Telethon sender on its own background thread + asyncio loop.
One message per client: a table image (plate / IMEI / expiry) with the Khmer text as caption."""
import asyncio, base64, html, io, os, random, re, threading, time
from collections import deque
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from timeutil import now as now_local


class LogBuffer:
    """Thread-safe ring buffer; the web console polls it with ?since=<last id>."""
    def __init__(self, size=500):
        self.items, self.n, self.lock = deque(maxlen=size), 0, threading.Lock()

    def add(self, level, msg):
        with self.lock:
            self.n += 1
            self.items.append(dict(id=self.n, t=now_local().strftime("%H:%M:%S"), level=level, msg=msg))

    def since(self, n):
        with self.lock:
            return [x for x in self.items if x["id"] > n]


def fmt_date(iso):
    """2026-11-10 -> 10-11-2026"""
    p = (iso or "").split("-")
    return f"{p[2]}-{p[1]}-{p[0]}" if len(p) == 3 else (iso or "")


def group_rows(rows):
    """Group units by client so each client gets ONE message listing all their units."""
    groups = {}
    for r in rows:
        groups.setdefault(r["user"], []).append(r)
    return list(groups.values())


def caption(template, units, cfg, phone=None):
    """Fill only {user} {count} {expiry_date} {phone}. expiry_date = earliest date in the group."""
    first = min((u["expiry"] for u in units if u["expiry"]), default="")
    vals = dict(user=units[0]["user"], count=len(units), expiry_date=fmt_date(first),
                phone=phone or cfg.get("CONTACT_PHONE", ""))
    return re.sub(r"\{(\w+)\}", lambda m: str(vals.get(m.group(1), m.group(0))), template)


REASONS = {
    "UsernameNotOccupiedError": "Telegram username does not exist",
    "UsernameInvalidError": "Telegram username is not valid",
    "PeerFloodError": "Telegram limited this account from contacting new people (PeerFlood). Wait and send fewer messages",
    "UserPrivacyRestrictedError": "User's privacy settings do not allow messages from you",
    "UserIsBlockedError": "User has blocked this account",
    "InputUserDeactivatedError": "Telegram account was deleted or deactivated",
    "UserDeactivatedError": "Your Telegram account is deactivated",
    "UserDeactivatedBanError": "Your Telegram account is banned",
    "ChatWriteForbiddenError": "Not allowed to write to this chat",
    "AuthKeyUnregisteredError": "Telegram session expired. Run scripts/login_telegram.py again",
    "SessionRevokedError": "Telegram session was revoked. Run scripts/login_telegram.py again",
    "PermissionError": "Cannot save file (is it open in Excel?)",
    "TimeoutError": "Network timeout while contacting Telegram",
    "ConnectionError": "Network problem while contacting Telegram",
}


def explain(e):
    """Turn an exception into (plain reason for the report, technical detail)."""
    name, msg = type(e).__name__, str(e)
    if name == "FloodWaitError":
        return f"Telegram flood-wait: must wait {getattr(e, 'seconds', '?')} seconds", f"{name}: {msg}"
    if isinstance(e, ValueError) and "No user has" in msg:
        return "Telegram username does not exist", f"{name}: {msg}"
    if isinstance(e, ValueError) and "Could not find the input entity" in msg:
        return "Numeric ID not known to this account. Use the @username or save the user as a contact", f"{name}: {msg}"
    if isinstance(e, ValueError) and not msg.strip():
        return "Empty or invalid user value in Excel", name
    return REASONS.get(name, f"{name}: {msg}"[:200]), f"{name}: {msg}"


def text_table(units):  # fallback when the image cannot be rendered
    return "\n".join(f"{u['plate']} | {u['imei']} | {fmt_date(u['expiry'])}" for u in units)


CHUNK = 40  # max units per table image

CARD_CSS = """
body{margin:0;padding:16px;background:#fff;font-family:KhmerSiemreap,'Khmer UI','Leelawadee UI','Noto Sans Khmer','Khmer OS','Segoe UI',Arial,sans-serif}
#card{display:inline-block;min-width:520px;border:1px solid #d5dde5;border-radius:14px;overflow:hidden;background:#fff}
table{width:100%;border-collapse:collapse;font-size:17px;color:#1b2733}
th{background:#1f4a73;color:#fff;text-align:left;padding:14px 16px;font-size:17px}
td{padding:13px 16px}th,td{white-space:nowrap}tr:nth-child(even) td{background:#eaf0f8}
.p{font-weight:700}.b{display:inline-block;background:#fde2e2;color:#c0262d;font-weight:700;padding:5px 14px;border-radius:8px}
"""


_FONT_CSS = None


def font_css():
    """Embed the bundled KhmerOS Siemreap so the image looks identical on any server."""
    global _FONT_CSS
    if _FONT_CSS is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "fonts", "KhmerOSsiemreap.ttf")
        try:
            b64 = base64.b64encode(open(path, "rb").read()).decode()
            _FONT_CSS = ("@font-face{font-family:KhmerSiemreap;src:url(data:font/ttf;base64,%s);"
                         "unicode-range:U+1780-17FF,U+19E0-19FF,U+200B-200D}" % b64)
        except OSError:
            _FONT_CSS = ""
    return _FONT_CSS


def card_html(units):
    rows = "".join(
        f"<tr><td class=p>{html.escape(u['plate'])}</td><td>{html.escape(u['imei'])}</td>"
        f"<td><span class=b>{fmt_date(u['expiry'])}</span></td></tr>" for u in units)
    return (f"<meta charset=utf-8><style>{font_css()}{CARD_CSS}</style><div id=card><table>"
            f"<tr><th>Plate Number</th><th>IMEI</th><th>Expiration Date</th></tr>{rows}</table></div>")


class TelegramBot:
    def __init__(self, cfg, excel, logs, history):
        self.cfg, self.excel, self.log, self.history = cfg, excel, logs, history
        self.progress = dict(sent=0, failed=0, total=0)
        self.pending = []  # row ids delivered on Telegram but not yet saved to Excel
        # --- ASYNC <-> THREAD BRIDGE -------------------------------------------------
        # Flask/waitress threads are synchronous. Telethon (and Playwright) need an asyncio
        # loop, so we start ONE loop in a daemon thread. Web threads never await anything:
        # they hand a coroutine to that loop with run_coroutine_threadsafe(), which is
        # thread-safe and returns immediately. State flows back via thread-safe objects only
        # (LogBuffer, the progress dict, threading.Event) and the UI polls /api/status.
        self.loop, self._thread, self._loop_lock = None, None, threading.Lock()
        self._ensure_loop()
        self._busy = threading.Lock()      # allows one batch at a time
        self._stop = threading.Event()     # set by the Stop button, read inside the coroutine

    def _ensure_loop(self):
        """(Re)start the asyncio thread if it is not alive. gunicorn with --preload forks the process
        after import, and threads do not survive a fork: the loop would exist but never run."""
        with self._loop_lock:
            if self._thread is None or not self._thread.is_alive():
                self.loop = asyncio.new_event_loop()
                self._thread = threading.Thread(target=self.loop.run_forever, daemon=True, name="telethon-loop")
                self._thread.start()

    @property
    def running(self):
        return self._busy.locked()

    def start(self, groups, template, limit, actor="", phone=None):
        if not self._busy.acquire(blocking=False):
            return False
        self._stop.clear()
        self.actor = actor
        self.phone = phone  # contact number typed in the UI (overrides CONTACT_PHONE)
        self.pending = []
        self.progress = dict(sent=0, failed=0, total=min(len(groups), limit))
        self._ensure_loop()
        self.log.add("info", f"Batch accepted: {self.progress['total']} client(s).")
        asyncio.run_coroutine_threadsafe(self._job(groups[:limit], template), self.loop)
        return True

    def stop(self):
        self._stop.set()
        self.log.add("warn", "Stop requested - finishing the current message.")

    async def _nap(self, seconds):  # interruptible sleep so Stop reacts within ~0.5s
        end = time.monotonic() + seconds
        while time.monotonic() < end and not self._stop.is_set():
            await asyncio.sleep(0.5)

    # ---- table image (headless Chromium renders HTML, so Khmer is shaped correctly) ----
    async def _open_browser(self):
        if os.getenv("DISABLE_IMAGE") == "1":  # small/free hosts: skip Chromium, send the text list
            self.log.add("info", "Table image is turned off (DISABLE_IMAGE=1); sending text list.")
            return None, None
        try:
            from playwright.async_api import async_playwright
            pw = await async_playwright().start()
            try:
                args = ["--disable-dev-shm-usage", "--disable-gpu", "--disable-extensions", "--no-zygote",
                        "--disable-background-networking", "--mute-audio"]  # Docker's /dev/shm is tiny; keep RAM low
                if (hasattr(os, "geteuid") and os.geteuid() == 0) or os.getenv("CHROMIUM_NO_SANDBOX") == "1":
                    args.append("--no-sandbox")  # Chromium refuses to start as root otherwise (containers)
                return pw, await pw.chromium.launch(args=args, timeout=45000)
            except Exception:
                await pw.stop()
                raise
        except Exception as e:
            self.log.add("warn", f"Table image unavailable ({type(e).__name__}); using text list. "
                                 "Fix: pip install playwright  then  playwright install chromium")
            return None, None

    async def _close_browser(self, pw, browser):
        try:
            if browser: await browser.close()
            if pw: await pw.stop()
        except Exception:
            pass

    async def _png(self, browser, units):
        page = await browser.new_page(device_scale_factor=2, viewport={"width": 600, "height": 400})
        try:
            await page.set_content(card_html(units), timeout=30000)
            return await page.locator("#card").screenshot(type="png", timeout=30000)
        finally:
            await page.close()

    def preview(self, units, template, phone=None):
        """Called from a web thread: bridge into the loop and wait (max 60s) for the PNG."""
        async def go():
            pw, browser = await self._open_browser()
            if not browser:
                return None
            try:
                return await self._png(browser, units)
            finally:
                await self._close_browser(pw, browser)
        try:
            self._ensure_loop()
            png = asyncio.run_coroutine_threadsafe(go(), self.loop).result(timeout=60)
        except Exception:
            png = None
        return caption(template, units, self.cfg, phone), (base64.b64encode(png).decode() if png else None)

    async def _deliver(self, client, entity, browser, units, text):
        """One client = one message. A big fleet is split into several table images
        (CHUNK units each) because Telegram rejects very tall images."""
        chunks = [units[k:k + CHUNK] for k in range(0, len(units), CHUNK)]
        pngs = None
        if browser:
            try:
                pngs = [await self._png(browser, c) for c in chunks]
            except Exception as e:
                self.log.add("warn", f"Image render failed ({type(e).__name__}); using text list.")
        if pngs:
            long_text = len(text) > 1024  # Telegram caption limit
            for k, png in enumerate(pngs):
                bio = io.BytesIO(png)
                bio.name = f"units_{k + 1}.png"
                last = k == len(pngs) - 1  # the message text goes with the LAST image
                cap = text if (last and not long_text) else (f"({k + 1}/{len(pngs)})" if len(pngs) > 1 else None)
                await client.send_file(entity, bio, caption=cap)
                if k < len(pngs) - 1:
                    await asyncio.sleep(1)
            if long_text:
                await client.send_message(entity, text, parse_mode=None)
            return
        parts, cur = [], ""  # text fallback, split under Telegram's 4096-character limit
        for line in text_table(units).split("\n"):
            if len(cur) + len(line) + 1 > 3500:
                parts.append(cur)
                cur = ""
            cur += line + "\n"
        parts.append(cur.rstrip())
        for p in parts:
            await client.send_message(entity, p, parse_mode=None)
        await client.send_message(entity, text, parse_mode=None)

    def _record(self, batch, units, status, reason="", detail=""):
        plates = [u["plate"] for u in units if u["plate"]]
        shown = ", ".join(plates[:3]) + (f" +{len(plates) - 3} more" if len(plates) > 3 else "")
        try:
            self.history.add(now_local().strftime("%Y-%m-%d %H:%M:%S"), batch, units[0]["user"], len(units),
                             shown, status, reason, detail, getattr(self, "actor", ""))
        except Exception as e:
            self.log.add("error", f"Could not write report entry: {type(e).__name__}")

    async def _job(self, groups, template):
        client = pw = browser = None
        batch = now_local().strftime("%Y%m%d-%H%M%S")
        stopped = None  # (reason, index of first group that was NOT attempted)
        try:
            sess = self.cfg.get("SESSION_STRING")  # cloud hosting: session kept in an environment variable
            client = TelegramClient(StringSession(sess) if sess else self.cfg["SESSION"], self.cfg["API_ID"], self.cfg["API_HASH"],
                                    connection_retries=2, retry_delay=1, timeout=15)
            self.log.add("info", "Connecting to Telegram...")
            await asyncio.wait_for(client.connect(), 40)   # never hang forever (raises TimeoutError)
            if not await asyncio.wait_for(client.is_user_authorized(), 30):
                self.log.add("error", "Telegram session not logged in. Run: python scripts/login_telegram.py (or set TELEGRAM_SESSION_STRING)")
                stopped = ("Telegram session not logged in. Run scripts/login_telegram.py", 0)
                return
            self.log.add("info", "Telegram connected.")
            try:
                pw, browser = await asyncio.wait_for(self._open_browser(), 60)
            except asyncio.TimeoutError:
                pw = browser = None
                self.log.add("warn", "Table-image browser did not start in 60s; using text list instead.")
            self.log.add("info", f"Sending to {len(groups)} client(s)...")
            for n, units in enumerate(groups, 1):
                if self._stop.is_set():
                    self.log.add("warn", "Halted by user.")
                    stopped = ("Stopped by user", n - 1)
                    break
                who = units[0]["user"]
                target = who.lstrip("@")
                try:
                    entity = await asyncio.wait_for(client.get_entity(int(target) if target.lstrip("-").isdigit() else target), 30)
                    await asyncio.wait_for(self._deliver(client, entity, browser, units, caption(template, units, self.cfg, getattr(self, "phone", None))), 180)
                    self.progress["sent"] += 1
                    self._record(batch, units, "sent", "Force resend (was already sent before)" if any(u["state"] == "sent" for u in units) else "")
                    self.log.add("ok", f"[{n}/{len(groups)}] Sent to {who} ({len(units)} unit(s))")
                    ids = [u["id"] for u in units]
                    try:
                        self.excel.mark_sent(ids)
                    except Exception:
                        self.pending += ids
                        self.log.add("warn", "Delivered, but saving the Sent status failed; will retry at the end.")
                except FloodWaitError as e:
                    reason, detail = explain(e)
                    self.progress["failed"] += 1
                    self._record(batch, units, "failed", reason, detail)
                    self.log.add("error", f"[{n}/{len(groups)}] {who}: {reason} - stopping to protect the account.")
                    stopped = ("Batch stopped: " + reason, n)
                    break
                except Exception as e:
                    reason, detail = explain(e)
                    self.progress["failed"] += 1
                    self._record(batch, units, "failed", reason, detail)
                    self.log.add("error", f"[{n}/{len(groups)}] {who}: {reason}")
                if n < len(groups):
                    await self._nap(random.uniform(self.cfg["MIN_DELAY"], self.cfg["MAX_DELAY"]))
            if self.pending:
                try:
                    self.excel.mark_sent(self.pending)
                    self.log.add("ok", f"Saved {len(self.pending)} pending 'Sent' status(es) to Excel.")
                except Exception:
                    self.log.add("error", f"Could not save status for row ids {self.pending}. Mark them Sent manually!")
            try:
                self.excel.flush(raise_errors=True)  # write all 'Sent' marks to the Excel file
            except Exception as e:
                self.log.add("warn", f"Sent marks are kept in memory but the Excel file could not be saved yet ({type(e).__name__}). Close it in Excel; it retries automatically.")
            self.log.add("info", f"Done. Sent {self.progress['sent']}, failed {self.progress['failed']}. See the Report tab.")
        except Exception as e:
            reason, detail = explain(e)
            self.log.add("error", f"Job crashed: {reason}")
            if stopped is None:
                stopped = ("Batch crashed: " + reason, self.progress["sent"] + self.progress["failed"])
        finally:
            if stopped:  # everything not attempted is listed in the report as skipped, with the reason
                for units in groups[stopped[1]:]:
                    self._record(batch, units, "skipped", stopped[0])
            await self._close_browser(pw, browser)
            if client:
                await client.disconnect()
            self._busy.release()
