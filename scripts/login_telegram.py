"""One-time Telegram login. Stop the web app first (the session file can't be shared)."""
import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient

load_dotenv()
os.makedirs("sessions", exist_ok=True)
with TelegramClient("sessions/main", int(os.environ["API_ID"]), os.environ["API_HASH"]) as c:
    print("Logged in as", c.get_me().first_name)
for f in os.listdir("sessions"):
    try: os.chmod(os.path.join("sessions", f), 0o600)
    except OSError: pass
