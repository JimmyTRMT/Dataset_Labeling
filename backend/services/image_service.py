import re
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from backend.models.database import ImageRecord, db


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "gif", "tif", "tiff", "webp"}

# Holding pen for unlabeled uploads. Lives inside data/images/.
PENDING_FOLDER = "_pending"

# Captures the integer in "Fundus_007.jpg" or "Severity_0/Fundus_007.jpg".
_SEQUENCE_RE = re.compile(r"(?:^|/)[A-Za-z]+_(\d+)\.[A-Za-z0-9]+$")


def is_allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def label_to_folder_name(label: str) -> str:
    """Filesystem-safe folder name: "Severity 0" -> "Severity_0"."""
    return re.sub(r"\s+", "_", label.strip())


def next_sequence_number(project_id: str) -> int:
    """Next free counter for a project. Survives deletions; folder-agnostic."""
    prefix = _project_prefix(project_id)
    pattern = f"%{prefix}_%"
    candidates = (
        db.session.query(ImageRecord.stored_filename)
        .filter(ImageRecord.project == project_id)
        .filter(ImageRecord.stored_filename.like(pattern))
        .all()
    )
    highest = 0
    for (stored_filename,) in candidates:
        match = _SEQUENCE_RE.search(stored_filename or "")
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


# Stage 1: save one upload to _pending/ under its sequential name,
# return an unlabeled ImageRecord. Caller commits.
def persist_pending_image(
    file: FileStorage,
    upload_folder: str,
    project: str,
    author: str,
    description: str,
) -> ImageRecord:
    if not file or not file.filename:
        raise ValueError("Please choose an image file before submitting.")
    if not is_allowed_file(file.filename):
        raise ValueError(
            "Unsupported file type. Allowed formats: png, jpg, jpeg, bmp, gif, tif, tiff, webp."
        )

    original_name = secure_filename(file.filename)
    extension = original_name.rsplit(".", 1)[1].lower()

    prefix = _project_prefix(project)
    sequence = next_sequence_number(project)
    base_filename = f"{prefix}_{sequence:03d}.{extension}"

    pending_dir = Path(upload_folder) / PENDING_FOLDER
    pending_dir.mkdir(parents=True, exist_ok=True)

    target_path = pending_dir / base_filename
    # Bump if a stale file with the same name is still on disk.
    while target_path.exists():
        sequence += 1
        base_filename = f"{prefix}_{sequence:03d}.{extension}"
        target_path = pending_dir / base_filename

    file.save(target_path)

    return ImageRecord(
        original_filename=original_name,
        stored_filename=f"{PENDING_FOLDER}/{base_filename}",
        project=project,
        status="unlabeled",
        contributor=author or None,
        notes=description or None,
    )


# Stage 2: move _pending/ -> <Label>/, update record. Caller commits.
# Raises OSError on rename failure; caller flashes a warning.
def finalize_with_label(image: ImageRecord, label: str, upload_folder: str) -> None:
    upload_root = Path(upload_folder)
    source = upload_root / image.stored_filename
    base_filename = Path(image.stored_filename).name

    label_folder = label_to_folder_name(label)
    target_dir = upload_root / label_folder
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / base_filename
    # Names are unique per project, but double-check before clobbering.
    if target_path.exists() and target_path.resolve() != source.resolve():
        raise OSError(f"Destination already exists: {target_path}")

    if source.exists():
        source.replace(target_path)

    image.label = label
    image.status = "labeled"
    image.stored_filename = f"{label_folder}/{base_filename}"


# Best-effort delete: swallow OSError so the DB row can still be dropped.
def delete_image_file(image: ImageRecord, upload_folder: str) -> None:
    target = Path(upload_folder) / image.stored_filename
    try:
        if target.exists():
            target.unlink()
    except OSError:
        pass


# Looks up the filename prefix. Fails loudly on unknown project.
def _project_prefix(project_id: str) -> str:
    from flask import current_app

    prefixes = current_app.config["PROJECT_FILENAME_PREFIX"]
    if project_id not in prefixes:
        raise ValueError(f"Unknown project '{project_id}'.")
    return prefixes[project_id]
