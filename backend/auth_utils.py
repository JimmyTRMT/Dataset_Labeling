"""Shared auth helpers. Lives outside routes/ to dodge circular imports."""

from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def admin_required(view):
    """login_required + role == admin. Non-admins (and anon) get a 403."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped
