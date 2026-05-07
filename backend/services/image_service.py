import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from backend.models.database import ImageRecord


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "gif", "tif", "tiff", "webp"}


# Returns True only if the filename ends with one of our whitelisted
# image extensions.
def is_allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Saves each uploaded file to disk under a collision-resistant name and
# builds the matching ImageRecord (not committed; the route commits).
# A failed write on one file does not block the others: the corrupt file
# is skipped and reported via `invalid_detected`.
def persist_uploaded_images(
    files: Iterable[FileStorage],
    upload_folder: str,
    project: str,
    contributor: str | None = None,
    notes: str | None = None,
) -> tuple[list[ImageRecord], bool]:
    upload_path = Path(upload_folder)
    saved_records: list[ImageRecord] = []
    invalid_detected = False

    for file in files:
        if not file or not file.filename:
            continue
        if not is_allowed_file(file.filename):
            invalid_detected = True
            continue

        # Stored name = "<UTC timestamp>_<8 hex chars>.<ext>". Avoids
        # collisions when several users upload the same filename.
        original_name = secure_filename(file.filename)
        extension = original_name.rsplit(".", 1)[1].lower()
        unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.{extension}"
        target_path = upload_path / unique_name

        try:
            file.save(target_path)
        except OSError:
            # Disk full, permission denied, etc. Skip this file and keep
            # going so partial uploads still succeed.
            invalid_detected = True
            continue

        saved_records.append(
            ImageRecord(
                original_filename=original_name,
                stored_filename=unique_name,
                project=project,
                contributor=(contributor or None),
                notes=(notes or None),
                status="unlabeled",
            )
        )

    return saved_records, invalid_detected


# Best-effort deletion: unlinks the file if it exists, swallows OSError
# so the caller can still drop the DB row even when the file is gone.
def delete_image_file(image: ImageRecord, upload_folder: str) -> None:
    target = Path(upload_folder) / image.stored_filename
    try:
        if target.exists():
            target.unlink()
    except OSError:
        pass
