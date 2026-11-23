"""Check that TELEGRAM_SESSION_STRING really works (run on YOUR computer, same values as in Render).

    Windows (PowerShell):
        $env:API_ID="123456"; $env:API_HASH="abc..."; $env:TELEGRAM_SESSION_STRING="1BVts..."
        python scripts\\check_session_string.py
    Or put the 3 values in .env and just run:  python scripts/check_session_string.py

Prints "OK - logged in as <name>" when the session is valid. The string is never printed."""
import asyncio, os, sys
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

load_dotenv(interpolate=False)
api_id, api_hash = os.getenv("API_ID", "").strip(), os.getenv("API_HASH", "").strip()
sess = os.getenv("TELEGRAM_SESSION_STRING", "").strip()

if not api_id.isdigit():
    sys.exit("FAIL - API_ID is missing or not digits only.")
if not api_hash:
    sys.exit("FAIL - API_HASH is missing.")
if not sess:
    sys.exit("FAIL - TELEGRAM_SESSION_STRING is missing. Create it with: python scripts/make_session_string.py")
print(f"API_ID ok ({len(api_id)} digits) | API_HASH length {len(api_hash)} (expect 32) | session length {len(sess)}")


async def main():
    client = TelegramClient(StringSession(sess), int(api_id), api_hash, connection_retries=2, timeout=15)
    try:
        await asyncio.wait_for(client.connect(), 40)
        if not await asyncio.wait_for(client.is_user_authorized(), 30):
            sys.exit("FAIL - Telegram connected but this session is NOT logged in (expired/revoked). Run make_session_string.py again.")
        me = await asyncio.wait_for(client.get_me(), 30)
        print(f"OK - logged in as {me.first_name or ''} (@{me.username or 'no username'}, id {me.id})")
    except asyncio.TimeoutError:
        sys.exit("FAIL - timed out talking to Telegram (network blocked or very slow).")
    except Exception as e:
        sys.exit(f"FAIL - {type(e).__name__}: {e}")
    finally:
        await client.disconnect()


asyncio.run(main())
