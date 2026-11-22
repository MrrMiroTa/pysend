# Deploy on Render

Needs a **paid** web service with a **persistent disk** (Starter is enough to start). The Free plan sleeps after 15 minutes
without visits and wipes all files on every restart, so it is only good for a quick look.

## 1. Prepare on your own computer
```bash
python app.py hash                        # -> ADMIN_PASSWORD_HASH (type your admin password)
python scripts/make_session_string.py     # -> TELEGRAM_SESSION_STRING (phone, code, 2FA password)
```
The session string is **full access to that Telegram account**: keep it secret, never commit it. It is a separate login from
your local `sessions/main`, so you can keep using the app locally.

## 2. Put the project on GitHub (PRIVATE repo)
`.gitignore` already excludes `.env`, `sessions/`, `data/`. Check `git status` shows none of them.

## 3. Create the service
Render Dashboard -> **New -> Blueprint** -> choose the repo. Render reads `render.yaml` and asks for:
`ADMIN_PASSWORD_HASH`, `API_ID`, `API_HASH`, `TELEGRAM_SESSION_STRING`, `CONTACT_PHONE`. Paste them (no quotes needed).
`SECRET_KEY` is generated for you. The first build takes several minutes (it downloads Chromium).

## 4. Use it
Open `https://<name>.onrender.com`, sign in as `admin`, add staff in the **Users** tab, then **Browse file**.
Check **Report** after the first small test send (try 1-2 of your own accounts first).

## Things to know
- Keep **one instance** (no scaling out): the Telegram session and the running batch live in that one process.
- A deploy/restart during a batch stops the batch. Sent marks are saved first, and unsent clients stay Due, so just press Send again.
- Persistent disk = no zero-downtime deploys (a few seconds of downtime on each deploy).
- Table image needs memory. If the log says "Table image unavailable", move to a larger instance; until then the app sends a text list.
- Without a disk (Free plan) you could use Render Postgres for users/report (`DATABASE_URL`), but the Excel working copy and Sent marks
  would still be lost at every restart. Not recommended for real use.
- If Telegram logs the account out (Settings -> Devices -> terminated): run `make_session_string.py` again, update the env var, redeploy.
- Back up: use **Export report** and **Export to Excel** regularly.
