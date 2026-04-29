import os
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _split_labels(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    items = [piece.strip() for piece in value.split(",")]
    return [item for item in items if item] or default


def _anchor_sqlite_url(raw_url: str, project_root: Path) -> str:
    # Flask-SQLAlchemy resolves relative SQLite paths against app.instance_path,
    # not the project root. Pin them to the project root for predictable behavior.
    if not raw_url.startswith("sqlite:///"):
        return raw_url
    path_part = raw_url[len("sqlite:///"):]
    is_absolute = path_part.startswith("/") or (len(path_part) >= 2 and path_part[1] == ":")
    if is_absolute:
        return raw_url
    absolute_path = (project_root / path_part).resolve().as_posix()
    return f"sqlite:///{absolute_path}"


def _anchor_folder(raw_value: str | None, default: str, project_root: Path) -> str:
    # Werkzeug's send_file rejects relative paths, so normalise to absolute.
    chosen = raw_value or default
    path = Path(chosen)
    if not path.is_absolute():
        path = (project_root / chosen).resolve()
    return str(path)


class Config:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DEFAULT_SECRET_KEY = "dev-change-me-secret"
    DEFAULT_DATABASE_PATH = (PROJECT_ROOT / "database" / "dataset.db").resolve().as_posix()
    DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH}"
    DEFAULT_UPLOAD_FOLDER = str((PROJECT_ROOT / "data" / "images").resolve())
    DEFAULT_EXPORT_FOLDER = str((PROJECT_ROOT / "data" / "exports").resolve())
    DEFAULT_LABELS = ["No DR", "Mild", "Moderate", "Severe"]

    SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("SecretKey") or DEFAULT_SECRET_KEY
    SQLALCHEMY_DATABASE_URI = _anchor_sqlite_url(
        os.getenv("DATABASE_URL") or os.getenv("DatabaseUrl") or DEFAULT_DATABASE_URL,
        PROJECT_ROOT,
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = _anchor_folder(
        os.getenv("UPLOAD_FOLDER") or os.getenv("UploadFolder"),
        DEFAULT_UPLOAD_FOLDER,
        PROJECT_ROOT,
    )
    EXPORT_FOLDER = _anchor_folder(
        os.getenv("EXPORT_FOLDER") or os.getenv("ExportFolder"),
        DEFAULT_EXPORT_FOLDER,
        PROJECT_ROOT,
    )

    AVAILABLE_LABELS = _split_labels(os.getenv("AVAILABLE_LABELS"), DEFAULT_LABELS)

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    DEBUG = _as_bool(os.getenv("FLASK_DEBUG") or os.getenv("FlaskDebug"), default=False)
