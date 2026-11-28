"""Web layer. One file per area, so a change in one place does not touch the others:

    config.py       settings from .env
    services.py     database, client list, Telegram bot, log (created once)
    permissions.py  the permission list and who has what
    auth.py         sign in/out, CSRF + security headers, permission decorators
    clientlist.py   Dashboard logic: filters, which units to send, one page of rows + stats
    changelog.py    admin change log
    dashboard.py    Dashboard pages and API (list, send, import, fill ID, update expiry)
    report.py       Report API (master, detail, changes, export)
    users.py        Users + permissions API
"""


def register(app):
    from . import auth, dashboard, report, users
    for m in (auth, dashboard, report, users):
        app.register_blueprint(m.bp)
