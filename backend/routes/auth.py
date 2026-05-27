"""Authentication blueprint: login, logout, register, forgot, reset.

Kept in one file because every route lives in the same lifecycle (account
creation, session management, password recovery). All POST endpoints are
WTForms-backed, so CSRF protection is enforced out of the box by Flask-WTF.
"""

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError

from backend.forms import (
    ForgotPasswordForm,
    LoginForm,
    RegisterForm,
    ResetPasswordForm,
)
from backend.models.database import ROLE_ADMIN, ROLE_ANNOTATOR, User, db


auth_bp = Blueprint("auth", __name__)


# Helper: send the user back to the page they came from if it is a safe
# in-app path, otherwise to the home page. Used after login.
def _safe_redirect_target(default_endpoint: str = "home") -> str:
    next_url = request.args.get("next") or request.form.get("next")
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return url_for(default_endpoint)


# ---------------------------------------------------------------------------
# Login / logout
# ---------------------------------------------------------------------------

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Already authenticated users skip the form straight to the home page.
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        # Defense-in-depth: same response time and message whether the user
        # does not exist or the password is wrong - avoids enumeration.
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password.", "warning")
            return redirect(url_for("auth.login"))

        login_user(user, remember=False)
        flash(f"Welcome back, {user.username}.", "success")
        return redirect(_safe_redirect_target())

    return render_template("auth/login.html", form=form)


# POST-only so the form CSRF token guards against drive-by logout links.
@auth_bp.post("/logout")
@login_required
def logout():
    username = current_user.username
    logout_user()
    flash(f"Goodbye, {username}.", "success")
    return redirect(url_for("auth.login"))


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    form = RegisterForm()
    if form.validate_on_submit():
        # First registered user becomes admin so the app is usable out of
        # the box. Everyone after that is a plain annotator.
        is_first_user = User.query.count() == 0
        role = ROLE_ADMIN if is_first_user else ROLE_ANNOTATOR

        user = User(
            username=form.username.data.strip(),
            role=role,
            security_question=form.security_question.data.strip(),
        )
        user.set_password(form.password.data)
        user.set_security_answer(form.security_answer.data)

        try:
            db.session.add(user)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Failed to create user account")
            flash("Could not create the account. Please try again.", "warning")
            return redirect(url_for("auth.register"))

        login_user(user, remember=False)
        flash(
            f"Account created. You are signed in as {user.username}"
            f"{' (admin)' if user.is_admin else ''}.",
            "success",
        )
        return redirect(url_for("home"))

    return render_template("auth/register.html", form=form)


# ---------------------------------------------------------------------------
# Forgot password : 2-step recovery via security question
# ---------------------------------------------------------------------------

# Session key holding the username under recovery between steps 1 and 2.
RESET_SESSION_KEY = "reset_username"


@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user is None:
            # Same wording as a successful step to avoid leaking which
            # usernames exist via the recovery flow.
            flash("If that account exists, the security question is shown below.", "secondary")
            return redirect(url_for("auth.forgot_password"))

        session[RESET_SESSION_KEY] = user.username
        return redirect(url_for("auth.reset_password"))

    return render_template("auth/forgot.html", form=form)


@auth_bp.route("/reset", methods=["GET", "POST"])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    username = session.get(RESET_SESSION_KEY)
    if not username:
        # No /forgot step recorded -> bounce back to step 1.
        return redirect(url_for("auth.forgot_password"))

    user = User.query.filter_by(username=username).first()
    if user is None:
        session.pop(RESET_SESSION_KEY, None)
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        if not user.check_security_answer(form.security_answer.data):
            flash("Wrong answer to the security question.", "warning")
            return redirect(url_for("auth.reset_password"))

        user.set_password(form.new_password.data)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Failed to update password during recovery")
            flash("Could not update the password. Please try again.", "warning")
            return redirect(url_for("auth.reset_password"))

        session.pop(RESET_SESSION_KEY, None)
        login_user(user, remember=False)
        flash("Password updated. You are now signed in.", "success")
        return redirect(url_for("home"))

    return render_template(
        "auth/reset.html",
        form=form,
        username=user.username,
        security_question=user.security_question,
    )
