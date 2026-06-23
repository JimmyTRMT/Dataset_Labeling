import os
from datetime import timedelta, timezone
from pathlib import Path


# Thailand has no DST, fixed UTC+7 stays accurate year-round. DB stays UTC.
DISPLAY_TIMEZONE = timezone(timedelta(hours=7), name="ICT")


# Project IDs end up in URLs, DB rows, filenames - never rename in place.
PROJECT_FUNDUS = "Fundus"
PROJECT_WASTE = "WasteSorting"
PROJECT_IDS: tuple[str, ...] = (PROJECT_FUNDUS, PROJECT_WASTE)

# Label sets are spec-fixed (not env-driven) to keep export schemas stable.
PROJECT_LABELS: dict[str, list[str]] = {
    PROJECT_FUNDUS: [
        "Severity 0",
        "Severity 1",
        "Severity 2",
        "Severity 3",
        "Severity 4",
    ],
    PROJECT_WASTE: ["PET", "Can", "Plastic"],
}

# Per-project filename prefix. Counter is project-wide (Fundus_001, ...).
PROJECT_FILENAME_PREFIX: dict[str, str] = {
    PROJECT_FUNDUS: "Fundus",
    PROJECT_WASTE: "Waste",
}


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _anchor_sqlite_url(raw_url: str, project_root: Path) -> str:
    """Resolve relative SQLite URLs against the project root, not instance_path."""
    if not raw_url.startswith("sqlite:///"):
        return raw_url
    path_part = raw_url[len("sqlite:///"):]
    is_absolute = path_part.startswith("/") or (len(path_part) >= 2 and path_part[1] == ":")
    if is_absolute:
        return raw_url
    absolute_path = (project_root / path_part).resolve().as_posix()
    return f"sqlite:///{absolute_path}"


def _anchor_folder(raw_value: str | None, default: str, project_root: Path) -> str:
    """Force a folder path to absolute. send_file rejects relative ones."""
    chosen = raw_value or default
    path = Path(chosen)
    if not path.is_absolute():
        path = (project_root / chosen).resolve()
    return str(path)


class Config:
    """All runtime settings. Read once at import, applied app-wide."""

    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DEFAULT_SECRET_KEY = "dev-change-me-secret"
    DEFAULT_DATABASE_PATH = (PROJECT_ROOT / "database" / "dataset.db").resolve().as_posix()
    DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_DATABASE_PATH}"
    DEFAULT_UPLOAD_FOLDER = str((PROJECT_ROOT / "data" / "images").resolve())
    DEFAULT_EXPORT_FOLDER = str((PROJECT_ROOT / "data" / "exports").resolve())

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

    # Exposed on Flask config so routes can read via current_app.
    PROJECT_IDS = PROJECT_IDS
    PROJECT_LABELS = PROJECT_LABELS
    PROJECT_FILENAME_PREFIX = PROJECT_FILENAME_PREFIX

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    DEBUG = _as_bool(os.getenv("FLASK_DEBUG") or os.getenv("FlaskDebug"), default=False)
