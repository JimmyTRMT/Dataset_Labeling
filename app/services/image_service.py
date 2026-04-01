from datetime import datetime
from pathlib import Path
from typing import Iterable
import uuid
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from ..models import ImageRecord

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "gif", "tif", "tiff", "webp"}


def is_allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def persist_uploaded_images(
    files: Iterable[FileStorage],
    upload_folder: str,
    session_name: str,
    label_option_1: str,
    label_option_2: str,
    custom_labels: str | None = None,
) -> tuple[list[ImageRecord], bool]:
    
    # Save uploaded images to disk and create records.

    upload_path = Path(upload_folder)
    saved_records: list[ImageRecord] = []
    invalid_detected = False

    for file in files:
        # Skip empty files
        if not file or not file.filename:
            continue
        # Skip files with unsupported extensions
        if not is_allowed_file(file.filename):
            invalid_detected = True
            continue

        # Generate unique filename with timestamp and UUID
        original_name = secure_filename(file.filename)
        extension = original_name.rsplit(".", 1)[1].lower()
        unique_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.{extension}"
        target_path = upload_path / unique_name
        file.save(target_path)

        # Create image record
        saved_records.append(
            ImageRecord(
                original_filename=original_name,
                stored_filename=unique_name,
                file_path=str(target_path),
                session_name=session_name,
                label_option_1=label_option_1,
                label_option_2=label_option_2,
                custom_labels=custom_labels,
                status="unlabeled",
            )
        )

    return saved_records, invalid_detected
