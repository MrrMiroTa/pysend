"""GPS Expiry Notifier - secure Flask web app.  Run: python app.py   (hash password: python app.py hash)

This file only starts the app. The code lives in the web/ package (one file per area - see web/__init__.py).
"""
import getpass
import os
import sys
from datetime import timedelta

from werkzeug.security import generate_password_hash

if len(sys.argv) > 1 and sys.argv[1] == "hash":
    print(generate_password_hash(getpass.getpass("New admin password: "), method="scrypt"))
    sys.exit(0)

from flask import Flask  # noqa: E402

import web  # noqa: E402
from web.config import env_int  # noqa: E402
from web.services import accounts, bot, engine, excel, history, logs  # noqa: E402,F401  (re-exported for tests/tools)

app = Flask(__name__)
if os.getenv("TRUST_PROXY") == "1":  # behind Nginx/Caddy: use the real client IP/scheme
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config.update(
    SECRET_KEY=os.environ["SECRET_KEY"],
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,                # reject uploads > 10 MB
    SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE") == "1",
    SESSION_COOKIE_NAME="__Host-session" if os.getenv("COOKIE_SECURE") == "1" else "session",   # __Host-: https only, no Domain, path /
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),   # idle logout
)
web.register(app)


def port_in_use(host, port):
    """True if another program (e.g. an old copy of this app) already listens on the port.
    Windows lets two programs share a port, which would split your data between them."""
    import socket
    s = socket.socket()
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        return False
    except OSError:
        return True
    finally:
        s.close()


if __name__ == "__main__":
    import signal
    from waitress import serve
    _host, _port = os.getenv("HOST", "127.0.0.1"), env_int("PORT", 5000)
    if port_in_use(_host, _port):
        sys.exit(f"\nPort {_port} is already in use - probably an old copy of this app is still running.\n"
                 f"Close it first (Task Manager > python.exe, or: netstat -ano | findstr :{_port}  then  taskkill /PID <number> /F),\n"
                 f"or set a different PORT in .env.")

    def _on_term(*_):  # Render/Docker stop the app with SIGTERM: save pending "Sent" marks first
        excel.flush()
        sys.exit(0)
    signal.signal(signal.SIGTERM, _on_term)
    logs.add("info", "System ready.")
    serve(app, host=_host, port=_port, threads=4)
