import logging
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from sqlalchemy import inspect, text
load_dotenv()
from .blueprints.api import api_bp
from .blueprints.main import main_bp
from .config import Config
from .error_handlers import register_error_handlers
from .models import db

# Application factory and setup
def create_app() -> Flask:
    project_root = Path(Config.PROJECT_ROOT)
    flask_app = Flask(
        __name__,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
    )
    flask_app.config.from_object(Config)

    upload_dir = Path(flask_app.config["UPLOAD_FOLDER"])
    export_dir = Path(flask_app.config["EXPORT_FOLDER"])
    upload_dir.mkdir(exist_ok=True, parents=True)
    export_dir.mkdir(exist_ok=True, parents=True)

    db.init_app(flask_app)
    # Create database tables and ensure compatibility with older schemas
    with flask_app.app_context():
        db.create_all()
        ensure_schema_compatibility()

    if not flask_app.debug:
        logging.basicConfig(level=logging.INFO)
        if flask_app.config["SECRET_KEY"] == Config.DefaultSecretKey:
            logging.warning("Default secret key is active while debug mode is disabled. Set SecretKey in your environment before production use.")

    flask_app.register_blueprint(main_bp)
    flask_app.register_blueprint(api_bp)
    register_error_handlers(flask_app)

    return flask_app


def ensure_schema_compatibility() -> None:
    # Keep older local SQLite databases compatible with the current schema
    if db.engine.dialect.name != "sqlite":
        return

    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    if "images" not in table_names:
        return
    # Check for missing columns and add them if necessary
    existing_columns = {column["name"] for column in inspector.get_columns("images")}
    if "session_name" not in existing_columns:
        db.session.execute(text("ALTER TABLE images ADD COLUMN session_name VARCHAR(255) DEFAULT 'Default Session'"))
    if "label_option_1" not in existing_columns:
        db.session.execute(text("ALTER TABLE images ADD COLUMN label_option_1 VARCHAR(100) DEFAULT 'labelOne'"))
    if "label_option_2" not in existing_columns:
        db.session.execute(text("ALTER TABLE images ADD COLUMN label_option_2 VARCHAR(100) DEFAULT 'labelTwo'"))
    if "last_viewed_at" not in existing_columns:
        db.session.execute(text("ALTER TABLE images ADD COLUMN last_viewed_at DATETIME"))
    if "labeling_duration_seconds" not in existing_columns:
        db.session.execute(text("ALTER TABLE images ADD COLUMN labeling_duration_seconds FLOAT"))
    if "custom_labels" not in existing_columns:
        db.session.execute(text("ALTER TABLE images ADD COLUMN custom_labels TEXT"))
    db.session.commit()
