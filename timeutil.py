"""One clock for the whole app (default Asia/Phnom_Penh) so report days are right even on a UTC server."""
import os
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo(os.getenv("TIMEZONE", "Asia/Phnom_Penh"))
except Exception:  # tzdata missing (Windows) or bad name: fixed UTC+7
    TZ = timezone(timedelta(hours=7))


def now():
    return datetime.now(TZ)


def today():
    return now().date()
