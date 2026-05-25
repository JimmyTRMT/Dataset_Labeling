"""Shared auth helpers: decorators and small predicates.

Lives outside `routes/` so any blueprint (or future module) can import
without circular dependencies via `backend.routes.auth`.
"""

from functools import wraps

from flask import abort
from flask_login import current_user, login_required


# Like @login_required but also enforces role == "admin". Any other role
# (or anonymous) gets a 403 - rendered as our branded errors/403 page.
def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped
