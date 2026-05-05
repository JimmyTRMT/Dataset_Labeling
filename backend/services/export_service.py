import base64
import csv
import html
import json
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Sequence

from backend.config import DISPLAY_TIMEZONE
from backend.models.database import ImageRecord


# Full layout keeps every column the auditor might want, including project.
EXPORT_FIELDS_FULL = [
    "id",
    "original_filename",
    "stored_filename",
    "image_path",
    "project",
    "contributor",
    "notes",
    "label",
    "status",
    "uploaded_at",
    "labeled_at",
]

# AI layout stays minimal so it drops straight into PyTorch / Keras / pandas.
# The project name is already in the filename, so we don't need a column here.
EXPORT_FIELDS_AI = [
    "image_path",
    "label",
]


# build_csv_export writes a CSV containing only the rows for one project. The
# project name is baked into the filename so reviewers can tell DR from
# SmartBin at a glance.
def build_csv_export(
    images: Sequence[ImageRecord],
    export_folder: str,
    project: str,
    export_format: str = "full",
) -> Path:
    normalized_format = "ai" if export_format.lower().strip() == "ai" else "full"
    selected_fields = EXPORT_FIELDS_FULL if normalized_format == "full" else EXPORT_FIELDS_AI

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    export_path = Path(export_folder) / f"export_{project}_{normalized_format}_{timestamp}.csv"

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


# build_json_export mirrors the CSV builder but emits JSON. UTF-8 without BOM,
# so consumers like pandas.read_json don't choke on the leading marker.
def build_json_export(
    images: Sequence[ImageRecord],
    export_folder: str,
    project: str,
    export_format: str = "full",
) -> Path:
    normalized_format = "ai" if export_format.lower().strip() == "ai" else "full"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    export_path = Path(export_folder) / f"export_{project}_{normalized_format}_{timestamp}.json"

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


# build_html_export writes a single self-contained HTML file: a 2-column
# table with the image on the left and its label on the right. Images are
# embedded as base64 so the file works offline, with no companion folder.
def build_html_export(
    images: Sequence[ImageRecord],
    export_folder: str,
    upload_folder: str,
    project: str,
) -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    export_path = Path(export_folder) / f"export_{project}_visual_{timestamp}.html"
    upload_path = Path(upload_folder)

    rows: list[str] = []
    for image in images:
        data_url = _encode_image_as_data_url(upload_path / image.stored_filename)
        label = html.escape(image.label or "")
        original = html.escape(image.original_filename or "")
        # If the file is missing on disk we still emit the row but show a
        # placeholder, so the export reflects the DB faithfully.
        image_cell = (
            f'<img src="{data_url}" alt="{original}">'
            if data_url
            else '<span class="missing">missing file</span>'
        )
        rows.append(
            f"""
            <tr>
                <td class="image-cell">{image_cell}</td>
                <td class="label-cell"><span class="label">{label}</span></td>
            </tr>
            """
        )

    project_safe = html.escape(project)
    generated_at = html.escape(
        datetime.now(DISPLAY_TIMEZONE).strftime("%Y-%m-%d %H:%M %Z")
    )
    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{project_safe} dataset preview</title>
    <style>
        body {{ font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
                margin: 2rem; background: #f5f5f5; color: #222; }}
        h1 {{ margin: 0 0 0.25rem; }}
        .meta {{ color: #666; margin-bottom: 1.5rem; }}
        table {{ width: 100%; border-collapse: collapse; background: #fff;
                 border: 1px solid #ddd; border-radius: 8px; overflow: hidden;
                 box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05); }}
        th, td {{ padding: 0.75rem 1rem; text-align: left;
                  border-bottom: 1px solid #eee; vertical-align: middle; }}
        th {{ background: #fafafa; font-size: 0.85rem;
              text-transform: uppercase; letter-spacing: 0.04em; color: #555; }}
        tr:last-child td {{ border-bottom: none; }}
        .image-cell {{ width: 280px; }}
        .image-cell img {{ display: block; max-width: 240px; max-height: 180px;
                           border-radius: 4px; }}
        .label-cell {{ font-size: 1.05rem; }}
        .label {{ display: inline-block; background: #198754; color: #fff;
                  padding: 0.25rem 0.65rem; border-radius: 4px;
                  font-weight: 600; }}
        .missing {{ color: #b00; font-style: italic; }}
    </style>
</head>
<body>
    <h1>{project_safe} dataset preview</h1>
    <p class="meta">{len(images)} labeled image(s) &middot; generated {generated_at}</p>
    <table>
        <thead>
            <tr><th>Image</th><th>Label</th></tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
</body>
</html>
"""

    export_path.write_text(document, encoding="utf-8")
    return export_path


# _encode_image_as_data_url reads an image file and returns it as a base64
# data URL ready to drop into an <img src="...">. Returns "" when the file
# is missing or unreadable so the caller can render a placeholder cell.
def _encode_image_as_data_url(image_path: Path) -> str:
    if not image_path.exists():
        return ""
    mime_type, _ = mimetypes.guess_type(image_path.name)
    if mime_type is None:
        mime_type = "application/octet-stream"
    try:
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    except OSError:
        return ""
    return f"data:{mime_type};base64,{encoded}"
