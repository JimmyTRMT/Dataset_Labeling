"""Admin blueprint: list / promote / demote / delete users.

Guarded by @admin_required at the blueprint level. Self-protection:
last-admin cannot demote or be deleted, no self-delete from the panel.
"""

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from backend.auth_utils import admin_required
from backend.models.database import ROLE_ADMIN, ROLE_ANNOTATOR, User, db


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# Blueprint-level guard - no endpoint can accidentally stay public.
@admin_bp.before_request
@admin_required
def _require_admin():
    pass


@admin_bp.get("/users")
def users_list():
    users = User.query.order_by(User.created_at.asc()).all()
    admin_count = sum(1 for user in users if user.is_admin)
    return render_template(
        "admin/users.html",
        users=users,
        admin_count=admin_count,
    )


@admin_bp.post("/users/<int:user_id>/role")
def change_role(user_id: int):
    target = db.session.get(User, user_id)
    if target is None:
        flash("User not found.", "warning")
        return redirect(url_for("admin.users_list"))

    new_role = request.form.get("role", "").strip()
    if new_role not in (ROLE_ADMIN, ROLE_ANNOTATOR):
        flash("Invalid role.", "warning")
        return redirect(url_for("admin.users_list"))

    # Refuse self-demotion if it would leave zero admins.
    if target.id == current_user.id and new_role == ROLE_ANNOTATOR:
        remaining_admins = User.query.filter_by(role=ROLE_ADMIN).count()
        if remaining_admins <= 1:
            flash("You are the only admin - promote someone else first.", "warning")
            return redirect(url_for("admin.users_list"))

    target.role = new_role
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to update role for user %s", user_id)
        flash("Could not update the role. Please try again.", "warning")
        return redirect(url_for("admin.users_list"))

    flash(f"{target.username} is now {new_role}.", "success")
    return redirect(url_for("admin.users_list"))


@admin_bp.post("/users/<int:user_id>/delete")
def delete_user(user_id: int):
    target = db.session.get(User, user_id)
    if target is None:
        flash("User not found.", "warning")
        return redirect(url_for("admin.users_list"))

    if target.id == current_user.id:
        flash("You cannot delete your own account from here.", "warning")
        return redirect(url_for("admin.users_list"))

    if target.is_admin:
        remaining_admins = User.query.filter_by(role=ROLE_ADMIN).count()
        if remaining_admins <= 1:
            flash("Cannot delete the last admin.", "warning")
            return redirect(url_for("admin.users_list"))

    username = target.username
    try:
        db.session.delete(target)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to delete user %s", user_id)
        flash("Could not delete the user. Please try again.", "warning")
        return redirect(url_for("admin.users_list"))

    flash(f"User '{username}' deleted.", "success")
    return redirect(url_for("admin.users_list"))
