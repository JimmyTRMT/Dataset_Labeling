import logging
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# load_dotenv must run before backend.config is imported, since Config
# reads os.getenv() at class-definition time.
load_dotenv()

from flask import Flask, flash, redirect, render_template, url_for
from flask_login import LoginManager, current_user, login_required
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from backend.config import Config, DISPLAY_TIMEZONE
from backend.models.database import ImageRecord, ROLE_ADMIN, User, db
from backend.routes.admin import admin_bp
from backend.routes.annotation import annotation_bp
from backend.routes.auth import auth_bp
from backend.routes.dashboard import dashboard_bp
from backend.routes.export import export_bp


csrf = CSRFProtect()
login_manager = LoginManager()
# Public endpoint that unauthenticated users are redirected to.
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "warning"


# Flask-Login loads the current user from the session via this callback.
@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


# Renders a naive UTC datetime (the way SQLAlchemy returns DB columns) as
# a string in Thai local time. Templates use it via `{{ dt | local_time }}`.
def local_time(value: datetime | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(DISPLAY_TIMEZONE).strftime(fmt)


# Application factory. Builds the Flask app, wires the database and auth,
# runs the SQLite migration, registers blueprints + filters, and refuses
# to start in production with the default secret key.
def create_app() -> Flask:
    project_root = Config.PROJECT_ROOT
    flask_app = Flask(
        __name__,
        template_folder=str(project_root / "frontend" / "templates"),
        static_folder=str(project_root / "frontend" / "static"),
    )
    flask_app.config.from_object(Config)

    Path(flask_app.config["UPLOAD_FOLDER"]).mkdir(exist_ok=True, parents=True)
    Path(flask_app.config["EXPORT_FOLDER"]).mkdir(exist_ok=True, parents=True)
    Path(project_root / "database").mkdir(exist_ok=True, parents=True)

    db.init_app(flask_app)
    csrf.init_app(flask_app)
    login_manager.init_app(flask_app)

    with flask_app.app_context():
        db.create_all()
        ensure_schema_compatibility()

    if not flask_app.debug:
        logging.basicConfig(level=logging.INFO)
        if flask_app.config["SECRET_KEY"] == Config.DEFAULT_SECRET_KEY:
            raise RuntimeError(
                "Refusing to start with the default SecretKey while debug is disabled. "
                "Set a strong SecretKey in your .env before running in production."
            )

    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(admin_bp)
    flask_app.register_blueprint(annotation_bp)
    flask_app.register_blueprint(dashboard_bp)
    flask_app.register_blueprint(export_bp)

    flask_app.jinja_env.filters["local_time"] = local_time

    register_core_routes(flask_app)
    register_error_handlers(flask_app)
    register_cli_commands(flask_app)

    return flask_app


# Home + utility routes that don't deserve their own blueprint. Home is
# behind @login_required so an anonymous visitor is bounced to /login.
def register_core_routes(flask_app: Flask) -> None:
    @flask_app.get("/")
    @login_required
    def home():
        total_count = ImageRecord.query.count()
        per_project = {
            project_id: ImageRecord.query.filter_by(project=project_id).count()
            for project_id in flask_app.config["PROJECT_IDS"]
        }
        return render_template(
            "index.html",
            total_count=total_count,
            per_project=per_project,
        )


# Adds new columns and migrates renamed values on legacy SQLite databases.
# New deployments are no-ops. Wrapped in try/except so a partially upgraded
# DB does not block the app; failures are logged for manual inspection.
def ensure_schema_compatibility() -> None:
    if db.engine.dialect.name != "sqlite":
        return
    try:
        inspector = inspect(db.engine)
        if "images" in inspector.get_table_names():
            existing_columns = {column["name"] for column in inspector.get_columns("images")}
            if "project" not in existing_columns:
                db.session.execute(
                    text("ALTER TABLE images ADD COLUMN project VARCHAR(50) NOT NULL DEFAULT 'Fundus'")
                )
                db.session.commit()

            # Project rename pass: the project identifiers used to be DR
            # and SmartBin. Migrate legacy rows in-place so existing test
            # data keeps working under the new names.
            db.session.execute(text("UPDATE images SET project='Fundus' WHERE project='DR'"))
            db.session.execute(
                text("UPDATE images SET project='WasteSorting' WHERE project='SmartBin'")
            )
            # Label rename pass: lowercase "severity X" -> "Severity X".
            for old, new in (
                ("severity 0", "Severity 0"),
                ("severity 1", "Severity 1"),
                ("severity 2", "Severity 2"),
                ("severity 3", "Severity 3"),
                ("severity 4", "Severity 4"),
            ):
                db.session.execute(
                    text("UPDATE images SET label=:new WHERE label=:old"),
                    {"old": old, "new": new},
                )
            db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        logging.exception("Schema migration failed; check the database manually")


# Branded 403 / 404 / 413 / 500 pages.
def register_error_handlers(flask_app: Flask) -> None:
    @flask_app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @flask_app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @flask_app.errorhandler(413)
    def payload_too_large(_error):
        flash(
            "Upload too large. Each request is limited to 16 MB. "
            "Please upload a smaller image.",
            "warning",
        )
        # 413 might fire for anonymous attempts too - send them to login.
        target = "annotation.annotation_page" if current_user.is_authenticated else "auth.login"
        return redirect(url_for(target))

    @flask_app.errorhandler(500)
    def server_error(_error):
        return render_template("errors/500.html"), 500


# CLI commands for off-line maintenance. The promote-admin command is the
# safety net when nobody is admin (e.g. you wiped the DB or the only
# admin demoted themselves through direct SQL).
def register_cli_commands(flask_app: Flask) -> None:
    import click
    from sqlalchemy.exc import SQLAlchemyError

    @flask_app.cli.command("promote-admin")
    @click.argument("username")
    def promote_admin(username: str) -> None:
        """Make USERNAME an admin. Creates nothing - the user must exist."""
        user = User.query.filter_by(username=username).first()
        if user is None:
            click.echo(f"No user found with username '{username}'.")
            return
        user.role = ROLE_ADMIN
        try:
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            click.echo(f"Failed to promote {username}: {exc}")
            return
        click.echo(f"{username} is now admin.")

    @flask_app.cli.command("list-users")
    def list_users() -> None:
        """Print every registered user with their role."""
        users = User.query.order_by(User.created_at.asc()).all()
        if not users:
            click.echo("No users yet.")
            return
        click.echo(f"{'username':30s}  {'role':12s}  created_at (UTC)")
        click.echo("-" * 70)
        for user in users:
            created = user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "-"
            click.echo(f"{user.username:30s}  {user.role:12s}  {created}")


app = create_app()


if __name__ == "__main__":
    app.run()
