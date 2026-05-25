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
from backend.routes.annotation import annotation_bp
from backend.routes.export import export_bp


csrf = CSRFProtect()


# Renders a naive UTC datetime (the way SQLAlchemy returns DB columns) as
# a string in Thai local time. Templates use it via `{{ dt | local_time }}`.
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

    flask_app.register_blueprint(annotation_bp)
    flask_app.register_blueprint(export_bp)

    flask_app.jinja_env.filters["local_time"] = local_time

    register_core_routes(flask_app)
    register_error_handlers(flask_app)

    return flask_app


# The home page is small enough to live in the factory. It just shows the
# headline counts and links to the rest of the app.
def register_core_routes(flask_app: Flask) -> None:
    @flask_app.get("/")
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
        if "images" not in inspector.get_table_names():
            return
        existing_columns = {column["name"] for column in inspector.get_columns("images")}
        if "project" not in existing_columns:
            db.session.execute(
                text("ALTER TABLE images ADD COLUMN project VARCHAR(50) NOT NULL DEFAULT 'Fundus'")
            )
            db.session.commit()

        # Project rename pass: the project identifiers used to be DR and
        # SmartBin. Migrate legacy rows in-place so existing test data
        # keeps working under the new names.
        db.session.execute(text("UPDATE images SET project='Fundus' WHERE project='DR'"))
        db.session.execute(
            text("UPDATE images SET project='WasteSorting' WHERE project='SmartBin'")
        )
        # Label rename pass: lowercase "severity X" → "Severity X" so old
        # rows match the new Fundus label list.
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


# Branded 404 / 413 / 500 pages.
def register_error_handlers(flask_app: Flask) -> None:
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
        return redirect(url_for("annotation.annotation_page"))

    @flask_app.errorhandler(500)
    def server_error(_error):
        return render_template("errors/500.html"), 500


app = create_app()


if __name__ == "__main__":
    app.run()
