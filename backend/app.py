import logging
from pathlib import Path

from dotenv import load_dotenv

# Must run before Config is imported, since Config reads os.getenv() at class definition time.
load_dotenv()

from flask import Flask, flash, redirect, render_template, url_for
from flask_wtf.csrf import CSRFProtect

from backend.config import Config
from backend.models.database import db, ImageRecord
from backend.routes.upload import upload_bp
from backend.routes.label import label_bp
from backend.routes.export import export_bp


csrf = CSRFProtect()

# create_app initializes the Flask application, configures it, sets up the database and CSRF protection, registers routes and error handlers, and returns the app instance.
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

    register_core_routes(flask_app)
    register_error_handlers(flask_app)

    return flask_app

# register_core_routes defines the main page route that shows dataset statistics and links to other pages.
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

# register_error_handlers sets up custom error pages for common HTTP errors and handles large upload attempts gracefully.
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
