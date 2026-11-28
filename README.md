# GPS Expiry Notifier (Web)

Secure, browser-based version: Flask UI + pandas/openpyxl + Telethon (background thread). Khmer/UTF-8 safe.

## Setup
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # Windows: copy
python -c "import secrets;print(secrets.token_hex(32))"   # -> SECRET_KEY
python app.py hash                                     # -> ADMIN_PASSWORD_HASH (paste into .env)
playwright install chromium                            # renders the table image (Khmer-safe)
python scripts/make_sample.py                          # optional sample Excel
python scripts/login_telegram.py                       # one-time Telegram login (app must be stopped)
python app.py                                          # open http://127.0.0.1:5000
```
Excel format: the first sheet, header in row 1, with ALL 7 columns `user, type, plate, imei, expiry_date, status, sent_at` (use the template button). Other columns are ignored; a file missing any of the 7 is rejected. Layout (like `clients_template.xlsx`): `userid` (Telegram Username/ID, may be empty), `type`, `user_type`, `plate`, `imei`, `expiry_date`, `user` (the client Name, e.g. WL112), `status`, `sent_at`. Older files with `user` = Telegram ID and a `name` column still import. Optional: `user_type` (`paid_off` or `rental`, empty = paid_off). Send rule: paid_off = Normal 7 / Company 14 days before expiry, rental = 30 days (1 month). Permissions per user are set by an admin in the Users tab; the account named by `ADMIN_USER` always has every permission.

## Project structure (where to change what)

```
app.py              starts the app only (config, register blueprints, run server)
web/
  config.py         settings from .env
  services.py       database, client list, Telegram bot, log, first-admin bootstrap
  permissions.py    permission list + who has what
  auth.py           sign in/out, CSRF, security headers, @login_required / @need
  clientlist.py     Dashboard logic: filters, units to send, rows + stats
  changelog.py      admin change log
  dashboard.py      Dashboard pages + API (send, import, fill ID, update expiry)
  report.py         Report API (master / detail / changes / export)
  users.py          Users + permissions API
static/js/          core, table, live, tools, report, users, main (loaded in this order)
static/css/         base, layout, components, login, responsive, tools, features
```

Other modules (`excel_manager.py`, `database.py`, `telegram_bot.py`, `security.py`, `timeutil.py`) are unchanged.
New Dashboard feature -> `web/dashboard.py` + `static/js/live.js`; Report -> `web/report.py` + `static/js/report.js`; Users -> `web/users.py` + `static/js/users.js`.

## Security built in
- Hashed admin password (scrypt), login throttling (5 fails -> 5 min lock), 30-min idle logout, new session on login
- CSRF token on every POST; HttpOnly + SameSite=Strict cookies (+Secure when `COOKIE_SECURE=1`)
- Strict CSP (no inline/external scripts), no-store caching, nosniff, frame denial, HSTS over HTTPS
- UI renders data with `textContent` (no XSS); Excel exports neutralise `=+-@` formula injection
- Uploads: .xlsx only, 5 MB cap, fully validated before replacing the live file; atomic writes
- Fixed Excel path from `.env` (browser can't choose server paths); `MAX_PER_RUN` is a hard server-side cap
- Message templates only substitute whitelisted placeholders; Telegram flood-wait stops the batch
- Binds to 127.0.0.1 by default. For internet access, put Caddy/Nginx with HTTPS in front and set `COOKIE_SECURE=1`
- Keep `.env` and `sessions/` private (the `.session` file = your Telegram login)

Run a single process only (one worker owns the Telegram session).

## Message format
Each client gets ONE message: a table image (Plate / IMEI / Expiration) of all their due units, with the Khmer text as caption. If Chromium is missing, a text list is sent instead. On Linux servers install a Khmer font: `sudo apt install fonts-khmeros`.

## Report
The **Report** tab keeps a permanent history in `data/history.sqlite3` (no database server needed): time, client, units, plates, status (Sent / Failed / Skipped) and a plain-language reason for every failure (e.g. username does not exist, privacy settings, flood-wait). Hover a reason to see the technical detail. If a batch stops (flood-wait or Stop button), the clients not reached are listed as Skipped with the reason. Filter by run or status and use **Export report** for an Excel copy.

## Database (Users + Report only)
The database stores exactly two things: `users` (admin logins) and `send_log` (the Report, one row per message with its day, status, reason and who sent it). The client list is not in the database; load it with **Browse file**.
- Default: SQLite file `data/app.sqlite3` (no setup). For a server use MySQL/MariaDB via `DATABASE_URL` (see `.env.example`).
- First start creates the first admin from `ADMIN_USER` / `ADMIN_PASSWORD_HASH`. Then manage users in the **Users** tab, or `python scripts/create_user.py <name> [--reset]` (also the way back in if you forget a password).
- **Report** tab: filter by day range (Today / 7 / 30 / All or any From-To) and by status (Success / Failed / Skipped); a by-day table (click a day for details), summary cards and Excel export. Days use `TIMEZONE` (default Asia/Phnom_Penh).
- `python scripts/init_db.py [--old-history]` creates tables / copies the old `data/history.sqlite3` report.
- Deploy guide in Khmer: `deploy/DEPLOY_KM.md`. Health check: `/healthz`.

## Large lists (tens of thousands of units)
Measured with 20,000 units: upload ~2 s, every page/filter/search ~10-50 ms, 'Sent' marks are instant (written to the Excel file in the background and at the end of each batch). The table is paged (50-500 rows) so the browser stays fast; use **Select all matching** to select across pages. A client with many units gets several table images (40 units each). Uploads up to 10 MB. Sending speed is limited on purpose by `MIN_DELAY`/`MAX_DELAY` and `MAX_PER_RUN` to protect the Telegram account.

## Render
See `deploy/DEPLOY_RENDER.md`, `render.yaml` and `Dockerfile`. Env vars: `DATA_DIR` (persistent disk path), `TELEGRAM_SESSION_STRING`, `DATABASE_URL` (optional Postgres), `HOST=0.0.0.0` (set by the Dockerfile).

## Interface
Sidebar layout (Dashboard / Report / Users), expiry donut, daily results chart, live sending progress, light and dark themes, phone layout. Fonts and icons are bundled (Inter - OFL, KhmerOS Siemreap - GPL, Lucide icons - ISC; licenses in `static/fonts/`) so the strict Content-Security-Policy needs no external sites.

## Updating an existing install
After copying new files run `python -m pip install -r requirements.txt` (with the virtual environment active), then `python app.py`. `psycopg2-binary` is optional (PostgreSQL only): `pip install -r requirements-postgres.txt`.
