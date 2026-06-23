import base64
import csv
import html
import json
import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
from skimage.feature import graycomatrix, graycoprops

from backend.config import DISPLAY_TIMEZONE
from backend.models.database import ImageRecord


logger = logging.getLogger(__name__)


# GLCM: distance=1px, four angles. Each property yields 4 columns (con1..4
# etc.) so spreadsheets and ML tools read them without parsing list strings.
GLCM_DISTANCES = [1]
GLCM_ANGLES = [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]
# (export-column prefix, skimage.graycoprops property name).
GLCM_PROPS: tuple[tuple[str, str], ...] = (
    ("con", "contrast"),
    ("dis", "dissimilarity"),
    ("hom", "homogeneity"),
    ("ene", "energy"),
    ("corr", "correlation"),
    ("asm", "ASM"),
)
GLCM_DIRECTION_COUNT = 4
GLCM_DECIMALS = 4

# Spec-locked 26-column schema in fixed order. Researchers' downstream
# pipeline depends on it - never reorder, never rename.
GLCM_COLUMNS: tuple[str, ...] = tuple(
    f"{prefix}{direction}"
    for prefix, _ in GLCM_PROPS
    for direction in range(1, GLCM_DIRECTION_COUNT + 1)
)
EXPORT_COLUMNS: tuple[str, ...] = ("img_path", *GLCM_COLUMNS, "label")

# `;` so European Excel (FR/IT/ES) auto-splits without a wizard.
CSV_DELIMITER = ";"


def _zero_glcm_features() -> dict[str, float]:
    """Fallback: 24 keys at 0.0 when the image is missing or unreadable."""
    return {column: 0.0 for column in GLCM_COLUMNS}


# Fail-soft: any decoding / numpy error logs the path and returns zeros.
# A single corrupt image never breaks the rest of the export.
def extract_glcm_features(image_path: Path) -> dict[str, float]:
    if not image_path.exists():
        logger.warning("GLCM skipped: file not found at %s", image_path)
        return _zero_glcm_features()
    try:
        bgr_image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    except (cv2.error, OSError) as exc:
        logger.warning("GLCM skipped: OpenCV could not read %s (%s)", image_path, exc)
        return _zero_glcm_features()

    if bgr_image is None:
        logger.warning("GLCM skipped: OpenCV returned None for %s", image_path)
        return _zero_glcm_features()

    try:
        grayscale = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
        glcm_matrix = graycomatrix(
            grayscale,
            distances=GLCM_DISTANCES,
            angles=GLCM_ANGLES,
            symmetric=True,
            normed=True,
        )
        features: dict[str, float] = {}
        for prefix, prop in GLCM_PROPS:
            # graycoprops -> shape (distances, angles). One distance, so row 0.
            angle_values = graycoprops(glcm_matrix, prop)[0]
            for direction_index in range(GLCM_DIRECTION_COUNT):
                column_name = f"{prefix}{direction_index + 1}"
                features[column_name] = round(
                    float(angle_values[direction_index]), GLCM_DECIMALS
                )
        return features
    except (ValueError, cv2.error) as exc:
        logger.warning("GLCM computation failed for %s (%s)", image_path, exc)
        return _zero_glcm_features()


# Build one row in canonical column order. Broad try/except matches the
# fail-soft contract: one bad image cannot abort the whole export.
def _build_export_row(image: ImageRecord, upload_path: Path) -> dict:
    try:
        features = extract_glcm_features(upload_path / image.stored_filename)
    except Exception:
        logger.exception("Unexpected GLCM failure for image id=%s", image.id)
        features = _zero_glcm_features()

    row: dict = {"img_path": f"data/images/{image.stored_filename}"}
    row.update(features)
    row["label"] = image.label or ""
    return row


def build_csv_export(
    images: Sequence[ImageRecord],
    export_folder: str,
    upload_folder: str,
    project: str,
) -> Path:
    """Write the 26-column CSV. Returns the file path."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    export_path = Path(export_folder) / f"export_{project}_{timestamp}.csv"
    upload_path = Path(upload_folder)

    # utf-8-sig adds a BOM so Excel detects UTF-8 on Windows locales.
    with export_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file, delimiter=CSV_DELIMITER)
        writer.writerow(EXPORT_COLUMNS)
        for image in images:
            row = _build_export_row(image, upload_path)
            writer.writerow([row[column] for column in EXPORT_COLUMNS])

    return export_path


def build_json_export(
    images: Sequence[ImageRecord],
    export_folder: str,
    upload_folder: str,
    project: str,
) -> Path:
    """Write the 26-key JSON array. Numbers stay numeric for pandas/numpy."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    export_path = Path(export_folder) / f"export_{project}_{timestamp}.json"
    upload_path = Path(upload_folder)

    payload = [_build_export_row(image, upload_path) for image in images]

    with export_path.open("w", encoding="utf-8") as json_file:
        json.dump(payload, json_file, ensure_ascii=False, indent=2)

    return export_path


def build_html_export(
    images: Sequence[ImageRecord],
    export_folder: str,
    upload_folder: str,
    project: str,
) -> Path:
    """Write a self-contained preview. Images base64-embedded, works offline."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    export_path = Path(export_folder) / f"export_{project}_visual_{timestamp}.html"
    upload_path = Path(upload_folder)

    rows: list[str] = []
    for image in images:
        data_url = _encode_image_as_data_url(upload_path / image.stored_filename)
        label = html.escape(image.label or "")
        original = html.escape(image.original_filename or "")
        # Always emit the row - placeholder cell flags a missing file.
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


# Returns "" on missing/unreadable so the caller can render a placeholder.
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
