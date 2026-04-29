import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Sequence

from backend.models.database import ImageRecord


EXPORT_FIELDS_FULL = [
    "id",
    "original_filename",
    "stored_filename",
    "image_path",
    "contributor",
    "notes",
    "label",
    "status",
    "uploaded_at",
    "labeled_at",
]

EXPORT_FIELDS_AI = [
    "image_path",
    "label",
]


def build_csv_export(
    images: Sequence[ImageRecord],
    export_folder: str,
    export_format: str = "full",
) -> Path:
    normalized_format = "ai" if export_format.lower().strip() == "ai" else "full"
    selected_fields = EXPORT_FIELDS_FULL if normalized_format == "full" else EXPORT_FIELDS_AI

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    export_path = Path(export_folder) / f"dataset_{normalized_format}_{timestamp}.csv"

    # utf-8-sig writes a BOM so Excel on Windows opens accented or non-Latin text correctly.
    with export_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=selected_fields)
        writer.writeheader()
        for image in images:
            row = image.to_export_row()
            if normalized_format == "ai":
                writer.writerow({"image_path": row["image_path"], "label": row["label"]})
            else:
                writer.writerow({field: row.get(field, "") for field in selected_fields})

    return export_path


def build_json_export(
    images: Sequence[ImageRecord],
    export_folder: str,
    export_format: str = "full",
) -> Path:
    normalized_format = "ai" if export_format.lower().strip() == "ai" else "full"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    export_path = Path(export_folder) / f"dataset_{normalized_format}_{timestamp}.json"

    if normalized_format == "ai":
        payload = [
            {"image_path": image.to_export_row()["image_path"], "label": image.label or ""}
            for image in images
        ]
    else:
        payload = [image.to_export_row() for image in images]

    with export_path.open("w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, ensure_ascii=False, indent=2)

    return export_path
