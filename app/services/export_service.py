import csv
from datetime import datetime
from pathlib import Path
import re
from typing import Sequence
from ..models import ImageRecord


EXPORT_FIELDS = [
    "id",
    "original_filename",
    "stored_filename",
    "session_name",
    "label_option_1",
    "label_option_2",
    "custom_labels",
    "uploaded_at",
    "labeled_at",
    "label",
    "status",
]

EXPORT_FIELDS_AI = [
    "image_path",
    "label",
]


def _sanitize_filename_part(raw_value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw_value.strip())
    return safe.strip("_") or "session"


def build_export_csv(
    images: Sequence[ImageRecord],
    export_folder: str,
    filename_prefix: str = "dataset_labels",
    export_format: str = "full",
) -> Path:
    # Legacy aliases kept for backward compatibility with old links.
    raw_format = export_format.lower().strip()
    format_aliases = {
        "complet": "full",
        "full": "full",
        "ia": "ai",
        "ai": "ai",
    }
    normalized_format = format_aliases.get(raw_format, "full")

    safe_prefix = _sanitize_filename_part(filename_prefix)
    export_name = f"{safe_prefix}_{normalized_format}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    export_path = Path(export_folder) / export_name

    selected_fields = EXPORT_FIELDS if normalized_format == "full" else EXPORT_FIELDS_AI

    # utf-8-sig writes a BOM so Excel on Windows opens Thai/accented text correctly.
    with export_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=selected_fields)
        writer.writeheader()
        for image in images:
            if normalized_format == "ai":
                # Forward slash path is portable across OS and matches what PIL/torchvision expect.
                writer.writerow(
                    {
                        "image_path": f"uploads/{image.stored_filename}",
                        "label": image.label or "",
                    }
                )
            else:
                writer.writerow(image.to_export_row())

    return export_path
