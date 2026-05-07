import base64
import csv
import html
import json
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
from skimage.feature import graycomatrix, graycoprops

from backend.config import DISPLAY_TIMEZONE
from backend.models.database import ImageRecord


# GLCM is computed over one pixel of distance and four directions: 0, 45,
# 90, and 135 degrees. Each property therefore comes back as a list of 4
# values, one per direction.
GLCM_DISTANCES = [1]
GLCM_ANGLES = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]
# graycoprops accepts these property names verbatim. Lowercased equivalents
# are used as dict keys / column names so they read like CSV headers.
GLCM_PROPS: tuple[str, ...] = (
    "contrast",
    "dissimilarity",
    "homogeneity",
    "energy",
    "correlation",
    "ASM",
)
GLCM_FEATURE_KEYS: tuple[str, ...] = tuple(prop.lower() for prop in GLCM_PROPS)


# Full layout keeps every column the auditor might want, including project
# and one column per GLCM feature.
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
    *GLCM_FEATURE_KEYS,
]

# AI layout stays minimal but carries the GLCM features alongside the label,
# so classical ML pipelines can train on the precomputed texture descriptors.
EXPORT_FIELDS_AI = [
    "image_path",
    "label",
    *GLCM_FEATURE_KEYS,
]


# _zero_features returns the fallback dict when an image is missing or
# unreadable, so a single bad file never breaks an entire export.
def _zero_features() -> dict[str, list[float]]:
    return {key: [0.0, 0.0, 0.0, 0.0] for key in GLCM_FEATURE_KEYS}


# extract_glcm_features reads one image, converts to grayscale, and computes
# the 6 standard GLCM properties for the 4 reference angles. Output shape:
# {"contrast": [v0, v45, v90, v135], "dissimilarity": [...], ...}.
def extract_glcm_features(image_path: Path) -> dict[str, list[float]]:
    if not image_path.exists():
        return _zero_features()
    try:
        bgr_image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if bgr_image is None:
            return _zero_features()
        grayscale = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
        glcm_matrix = graycomatrix(
            grayscale,
            distances=GLCM_DISTANCES,
            angles=GLCM_ANGLES,
            symmetric=True,
            normed=True,
        )
        features: dict[str, list[float]] = {}
        for prop, key in zip(GLCM_PROPS, GLCM_FEATURE_KEYS):
            # graycoprops returns shape (len(distances), len(angles)).
            # We only have one distance, so take row 0 -> 4 floats.
            angle_values = graycoprops(glcm_matrix, prop)[0]
            features[key] = [round(float(value), 2) for value in angle_values]
        return features
    except Exception:
        # Any decoding / numpy error falls back to zeros so the rest of the
        # export still completes.
        return _zero_features()


# _format_feature_for_csv renders a 4-value list as the bracketed string the
# spec wants in CSV cells, e.g. "[20.70, 31.68, 16.28, 30.71]".
def _format_feature_for_csv(values: list[float]) -> str:
    return "[" + ", ".join(f"{value:.2f}" for value in values) + "]"


# build_csv_export writes a CSV containing only the rows for one project.
# Every row also embeds GLCM texture features as bracketed strings.
def build_csv_export(
    images: Sequence[ImageRecord],
    export_folder: str,
    upload_folder: str,
    project: str,
    export_format: str = "full",
) -> Path:
    normalized_format = "ai" if export_format.lower().strip() == "ai" else "full"
    selected_fields = EXPORT_FIELDS_FULL if normalized_format == "full" else EXPORT_FIELDS_AI

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    export_path = Path(export_folder) / f"export_{project}_{normalized_format}_{timestamp}.csv"
    upload_path = Path(upload_folder)

    # utf-8-sig writes a BOM so Excel on Windows opens accented or non-Latin text correctly.
    with export_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=selected_fields)
        writer.writeheader()
        for image in images:
            row = image.to_export_row()
            features = extract_glcm_features(upload_path / image.stored_filename)
            for key in GLCM_FEATURE_KEYS:
                row[key] = _format_feature_for_csv(features[key])
            writer.writerow({field: row.get(field, "") for field in selected_fields})

    return export_path


# build_json_export mirrors the CSV builder but emits JSON. Each entry gets
# a `features` dict so the GLCM values stay queryable as proper lists.
def build_json_export(
    images: Sequence[ImageRecord],
    export_folder: str,
    upload_folder: str,
    project: str,
    export_format: str = "full",
) -> Path:
    normalized_format = "ai" if export_format.lower().strip() == "ai" else "full"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    export_path = Path(export_folder) / f"export_{project}_{normalized_format}_{timestamp}.json"
    upload_path = Path(upload_folder)

    payload: list[dict] = []
    for image in images:
        features = extract_glcm_features(upload_path / image.stored_filename)
        if normalized_format == "ai":
            payload.append(
                {
                    "image_path": image.to_export_row()["image_path"],
                    "label": image.label or "",
                    "features": features,
                }
            )
        else:
            entry = image.to_export_row()
            entry["features"] = features
            payload.append(entry)

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
