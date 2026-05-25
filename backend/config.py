import os
from datetime import timedelta, timezone
from pathlib import Path


# UI runs in Thailand, so user-facing timestamps are converted to Thai
# local time (UTC+7). Thailand has no DST, so a fixed offset stays exact
# year-round and avoids depending on the OS tzdata. DB columns stay UTC.
DISPLAY_TIMEZONE = timezone(timedelta(hours=7), name="ICT")


# Two research projects share this tool. Identifiers travel through URLs,
# DB rows, export filenames, and stored-file prefixes, so they must stay
# stable once chosen.
PROJECT_FUNDUS = "Fundus"
PROJECT_WASTE = "WasteSorting"
PROJECT_IDS: tuple[str, ...] = (PROJECT_FUNDUS, PROJECT_WASTE)

# Label sets are fixed by the spec, not env-driven, so the form choices
# always match what the researchers asked for.
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

# Each project owns a short filename prefix used when we rename uploads
# (e.g. Fundus_001.jpg, Waste_042.jpg). The counter that fills the digits
# is project-wide so files of the same project share one numbering line.
PROJECT_FILENAME_PREFIX: dict[str, str] = {
    PROJECT_FUNDUS: "Fundus",
    PROJECT_WASTE: "Waste",
}


# Casts env strings ("true", "1", "yes", "on") to a boolean.
def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Forces relative SQLite URLs to live under the project root.
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


# Normalises a folder path to be absolute, anchored at the project root.
def _anchor_folder(raw_value: str | None, default: str, project_root: Path) -> str:
    # Werkzeug's send_file rejects relative paths, so normalise to absolute.
    chosen = raw_value or default
    path = Path(chosen)
    if not path.is_absolute():
        path = (project_root / chosen).resolve()
    return str(path)


# Gathers every runtime setting in one place. Read once, applied app-wide.
class Config:
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

    # Project metadata is static (per spec) and exposed on the Flask config
    # so routes can read it via current_app.config without re-importing.
    PROJECT_IDS = PROJECT_IDS
    PROJECT_LABELS = PROJECT_LABELS
    PROJECT_FILENAME_PREFIX = PROJECT_FILENAME_PREFIX

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    DEBUG = _as_bool(os.getenv("FLASK_DEBUG") or os.getenv("FlaskDebug"), default=False)
