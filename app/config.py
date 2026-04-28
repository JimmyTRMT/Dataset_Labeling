import os
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DEFAULT_SECRET_KEY = "dev-change-me-secret"
    DEFAULT_DATABASE_PATH = (PROJECT_ROOT / "dataset.db").resolve().as_posix()
    DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH}"
    DEFAULT_UPLOAD_FOLDER = str((PROJECT_ROOT / "uploads").resolve())
    DEFAULT_EXPORT_FOLDER = str((PROJECT_ROOT / "exports").resolve())

    # Both naming conventions accepted so deployments can use either.
    ENV_SECRET_KEY = os.getenv("SecretKey") or os.getenv("SECRET_KEY")
    ENV_DATABASE_URL = os.getenv("DatabaseUrl") or os.getenv("DATABASE_URL")
    ENV_UPLOAD_FOLDER = os.getenv("UploadFolder") or os.getenv("UPLOAD_FOLDER")
    ENV_EXPORT_FOLDER = os.getenv("ExportFolder") or os.getenv("EXPORT_FOLDER")
    ENV_FLASK_DEBUG = os.getenv("FlaskDebug") or os.getenv("FLASK_DEBUG")

    SECRET_KEY = ENV_SECRET_KEY or DEFAULT_SECRET_KEY
    SQLALCHEMY_DATABASE_URI = ENV_DATABASE_URL or DEFAULT_DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = ENV_UPLOAD_FOLDER or DEFAULT_UPLOAD_FOLDER
    EXPORT_FOLDER = ENV_EXPORT_FOLDER or DEFAULT_EXPORT_FOLDER

    # Cap upload size to 16 MB to prevent RAM/disk exhaustion.
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    DEBUG = _as_bool(ENV_FLASK_DEBUG, default=False)
