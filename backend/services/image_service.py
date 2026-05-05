from datetime import datetime
from pathlib import Path
from typing import Iterable
import uuid

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from backend.models.database import ImageRecord


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "gif", "tif", "tiff", "webp"}

# is_allowed_file checks if the uploaded file has an allowed image extension
def is_allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# persist_uploaded_images saves each upload to disk with a unique name and
# builds the matching ImageRecord. The project tag travels with every row so
# downstream code can filter cleanly by project.
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

        # timestamp + uuid prefix avoids collisions when several users upload the same filename.
        original_name = secure_filename(file.filename)
        extension = original_name.rsplit(".", 1)[1].lower()
        unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.{extension}"
        target_path = upload_path / unique_name
        file.save(target_path)

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

# delete_image_file removes the image file from disk based on the stored filename in the ImageRecord.
def delete_image_file(image: ImageRecord, upload_folder: str) -> None:
    target = Path(upload_folder) / image.stored_filename
    try:
        if target.exists():
            target.unlink()
    except OSError:
        pass
