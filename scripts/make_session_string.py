"""Create a Telegram login as TEXT, for hosts without persistent files (e.g. Render).
Run this on YOUR computer (not on the server):   python scripts\\make_session_string.py
Copy the long text it prints into the TELEGRAM_SESSION_STRING environment variable.
WARNING: that text = full access to the Telegram account. Treat it like a password; never put it in Git."""
import os
from dotenv import load_dotenv
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

load_dotenv(interpolate=False)
api_id = int(os.getenv("API_ID") or input("API_ID: "))
api_hash = os.getenv("API_HASH") or input("API_HASH: ")
with TelegramClient(StringSession(), api_id, api_hash) as c:  # asks phone, code, 2FA password
    print("\nLogged in as:", c.get_me().first_name)
    print("\n--- TELEGRAM_SESSION_STRING (copy everything on the next line) ---")
    print(c.session.save())
