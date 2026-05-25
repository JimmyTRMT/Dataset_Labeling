import re
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from backend.models.database import ImageRecord, db


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "gif", "tif", "tiff", "webp"}

# Holding pen for images that have been uploaded but not labeled yet.
# Sits inside data/images/ so serving and cleanup share one root.
PENDING_FOLDER = "_pending"

# Matches "Fundus_007.jpg" or "Severity_0/Fundus_007.jpg" and captures the
# integer counter. Used to compute the next sequence number per project.
_SEQUENCE_RE = re.compile(r"(?:^|/)[A-Za-z]+_(\d+)\.[A-Za-z0-9]+$")


# True iff the upload's filename ends with a whitelisted image extension.
def is_allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Builds a filesystem-safe folder name from a label. Spaces become
# underscores so "Severity 0" lands in data/images/Severity_0/.
def label_to_folder_name(label: str) -> str:
    return re.sub(r"\s+", "_", label.strip())


# Returns the next integer counter for a project. We scan the DB for all
# stored filenames matching the project's prefix and return max + 1.
# Stays correct after deletions and works regardless of which folder the
# file currently lives in (pending or final).
def next_sequence_number(project_id: str) -> int:
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


# Stage 1 of the annotation workflow: saves one uploaded image into the
# `_pending/` folder under its sequential project name (Fundus_007.jpg)
# and returns an unlabeled ImageRecord. The caller commits the row.
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
    # Defensive bump in case a stale file with the same name lingers on disk.
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


# Stage 2 of the annotation workflow: moves the file from `_pending/` into
# its label folder, then updates the record (label + status + stored
# filename). The caller commits the row. Raises OSError if the rename
# fails (callers should catch and surface a flash).
def finalize_with_label(image: ImageRecord, label: str, upload_folder: str) -> None:
    upload_root = Path(upload_folder)
    source = upload_root / image.stored_filename
    base_filename = Path(image.stored_filename).name

    label_folder = label_to_folder_name(label)
    target_dir = upload_root / label_folder
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / base_filename
    # Should not happen since names are unique per project, but stay safe.
    if target_path.exists() and target_path.resolve() != source.resolve():
        raise OSError(f"Destination already exists: {target_path}")

    if source.exists():
        source.replace(target_path)

    image.label = label
    image.status = "labeled"
    image.stored_filename = f"{label_folder}/{base_filename}"


# Best-effort deletion: unlinks the file if present, swallows OSError so
# the caller can still drop the DB row even when the file is gone.
def delete_image_file(image: ImageRecord, upload_folder: str) -> None:
    target = Path(upload_folder) / image.stored_filename
    try:
        if target.exists():
            target.unlink()
    except OSError:
        pass


# Returns the filename prefix for a project ("Fundus" or "Waste"). Raises
# ValueError on unknown project so misconfigured callers fail loudly.
def _project_prefix(project_id: str) -> str:
    from flask import current_app

    prefixes = current_app.config["PROJECT_FILENAME_PREFIX"]
    if project_id not in prefixes:
        raise ValueError(f"Unknown project '{project_id}'.")
    return prefixes[project_id]
