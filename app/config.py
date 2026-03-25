import os
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'dataset.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(PROJECT_ROOT / "uploads"))
    EXPORT_FOLDER = os.getenv("EXPORT_FOLDER", str(PROJECT_ROOT / "exports"))

    DEBUG = _as_bool(os.getenv("FLASK_DEBUG"), default=False)
