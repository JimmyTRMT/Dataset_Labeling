import logging
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# load_dotenv must run before backend.config is imported, since Config
# reads os.getenv() at class-definition time.
load_dotenv()

from flask import Flask, flash, redirect, render_template, url_for
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from backend.config import Config, DISPLAY_TIMEZONE
from backend.models.database import db, ImageRecord
from backend.routes.export import export_bp
from backend.routes.label import label_bp
from backend.routes.upload import upload_bp


csrf = CSRFProtect()


# Renders a naive UTC datetime (the way SQLAlchemy returns DB columns) as
# a string in Thai local time. Templates call it via `{{ dt | local_time }}`.
def local_time(value: datetime | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(DISPLAY_TIMEZONE).strftime(fmt)


# Application factory. Builds the Flask app, wires the database, runs the
# SQLite migration, registers blueprints + filters, and refuses to start
# in production with the default secret key.
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

    flask_app.register_blueprint(upload_bp)
    flask_app.register_blueprint(label_bp)
    flask_app.register_blueprint(export_bp)

    flask_app.jinja_env.filters["local_time"] = local_time

    register_core_routes(flask_app)
    register_error_handlers(flask_app)

    return flask_app


# The home page is small enough to live in the factory rather than its
# own blueprint. It just shows three counts and the navigation buttons.
def register_core_routes(flask_app: Flask) -> None:
    @flask_app.get("/")
    def home():
        total_count = ImageRecord.query.count()
        labeled_count = ImageRecord.query.filter_by(status="labeled").count()
        return render_template(
            "index.html",
            total_count=total_count,
            labeled_count=labeled_count,
            unlabeled_count=total_count - labeled_count,
        )


# Adds new SQLite columns to legacy databases on startup. New deployments
# are no-ops (db.create_all already created the table with all columns).
# Wrapped in try/except so a partially upgraded DB does not block the app:
# the failure is logged, and routes will surface clear errors when they
# touch the missing column.
def ensure_schema_compatibility() -> None:
    if db.engine.dialect.name != "sqlite":
        return
    try:
        inspector = inspect(db.engine)
        if "images" not in inspector.get_table_names():
            return
        existing_columns = {column["name"] for column in inspector.get_columns("images")}
        if "project" not in existing_columns:
            # Default existing rows to DR; reviewers can re-label or wipe
            # the DB if they want a clean slate.
            db.session.execute(
                text("ALTER TABLE images ADD COLUMN project VARCHAR(50) NOT NULL DEFAULT 'DR'")
            )
            db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        logging.exception("Schema migration failed; check the database manually")


# Handles 404, 413 (upload too large), and 500 with branded pages and a
# helpful flash message for the size limit.
def register_error_handlers(flask_app: Flask) -> None:
    @flask_app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @flask_app.errorhandler(413)
    def payload_too_large(_error):
        flash(
            "Upload too large. Each request is limited to 16 MB. "
            "Please upload smaller batches or compress the images.",
            "warning",
        )
        return redirect(url_for("upload.upload_page"))

    @flask_app.errorhandler(500)
    def server_error(_error):
        return render_template("errors/500.html"), 500


app = create_app()


if __name__ == "__main__":
    app.run()
