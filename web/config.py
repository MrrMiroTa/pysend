"""Settings read from the environment (.env). Nothing secret is stored in code."""
import os
import sys

from dotenv import load_dotenv

load_dotenv(interpolate=False)
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # project folder


def env_int(key, default):
    try:
        return int(os.getenv(key, default))
    except ValueError:
        return default


def clamp(v, lo, hi, default):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


CFG = dict(
    API_ID=env_int("API_ID", 0), API_HASH=os.getenv("API_HASH", ""),
    BOT_TOKEN=os.getenv("BOT_TOKEN", ""), ADMIN_IDS=os.getenv("ADMIN_IDS", ""),
    MIN_DELAY=env_int("MIN_DELAY", 8), MAX_DELAY=max(env_int("MAX_DELAY", 20), env_int("MIN_DELAY", 8)),
    MAX_PER_RUN=env_int("MAX_PER_RUN", 80), CONTACT_PHONE=os.getenv("CONTACT_PHONE") or "087500502",
    SESSION=os.path.join(os.path.abspath(os.getenv("DATA_DIR")) if os.getenv("DATA_DIR") else BASE, "sessions", "main"),
    SESSION_STRING=os.getenv("TELEGRAM_SESSION_STRING", "").strip(),  # alternative to the .session file (cloud hosting)
)
os.makedirs(os.path.dirname(CFG["SESSION"]), exist_ok=True)
if len(os.getenv("SECRET_KEY", "")) < 32 or len(set(os.getenv("SECRET_KEY", ""))) < 8:
    sys.exit("Set a random SECRET_KEY of 32+ characters in .env (see .env.example). Make one with: python -c \"import secrets;print(secrets.token_hex(32))\"")
