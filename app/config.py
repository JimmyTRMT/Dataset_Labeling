import os
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DefaultSecretKey = "dev-change-me-secret"
    DefaultDatabasePath = (PROJECT_ROOT / "dataset.db").resolve().as_posix()
    DefaultDatabaseUrl = f"sqlite:///{DefaultDatabasePath}"
    DefaultUploadFolder = str((PROJECT_ROOT / "uploads").resolve())
    DefaultExportFolder = str((PROJECT_ROOT / "exports").resolve())
    EnvSecretKey = os.getenv("SecretKey") or os.getenv("SECRET_KEY")
    EnvDatabaseUrl = os.getenv("DatabaseUrl") or os.getenv("DATABASE_URL")
    EnvUploadFolder = os.getenv("UploadFolder") or os.getenv("UPLOAD_FOLDER")
    EnvExportFolder = os.getenv("ExportFolder") or os.getenv("EXPORT_FOLDER")
    EnvFlaskDebug = os.getenv("FlaskDebug") or os.getenv("FLASK_DEBUG")

    SECRET_KEY = EnvSecretKey or DefaultSecretKey
    SQLALCHEMY_DATABASE_URI = EnvDatabaseUrl or DefaultDatabaseUrl
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = EnvUploadFolder or DefaultUploadFolder
    EXPORT_FOLDER = EnvExportFolder or DefaultExportFolder

    DEBUG = _as_bool(EnvFlaskDebug, default=False)
