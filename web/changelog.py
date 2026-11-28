"""Admin change log: what an admin changed is recorded here and shown in the Report."""
from flask import current_app, g

from timeutil import now as now_local
from .services import history


CHANGE_LABEL = {"expiry": "Expiry date updated", "user": "Username/ID filled", "import": "File imported"}


def log_changes(rows):
    """Record what an admin changed (shown in the Report). Never blocks the change itself."""
    try:
        history.add_changes(now_local().strftime("%Y-%m-%d %H:%M:%S"), g.user["username"], rows)
    except Exception as e:
        current_app.logger.warning("change log failed: %s", e)
