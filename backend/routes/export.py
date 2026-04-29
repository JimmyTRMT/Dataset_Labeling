from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from backend.models.database import ImageRecord
from backend.services.export_service import build_csv_export, build_json_export


export_bp = Blueprint("export", __name__)

# Export page shows export options and dataset statistics
@export_bp.get("/export")
def export_page():
    total = ImageRecord.query.count()
    labeled = ImageRecord.query.filter_by(status="labeled").count()
    return render_template(
        "export.html",
        total_count=total,
        labeled_count=labeled,
    )

# Export routes
@export_bp.get("/export/csv")
def export_csv():
    export_format = request.args.get("format", "full").strip().lower()
    labeled_images = (
        ImageRecord.query.filter_by(status="labeled")
        .order_by(ImageRecord.id.asc())
        .all()
    )
    if not labeled_images:
        flash("No labeled images to export yet.", "warning")
        return redirect(url_for("export.export_page"))

    export_path = build_csv_export(
        labeled_images,
        current_app.config["EXPORT_FOLDER"],
        export_format=export_format,
    )
    return send_file(export_path, as_attachment=True)


@export_bp.get("/export/json")
def export_json():
    export_format = request.args.get("format", "full").strip().lower()
    labeled_images = (
        ImageRecord.query.filter_by(status="labeled")
        .order_by(ImageRecord.id.asc())
        .all()
    )
    if not labeled_images:
        flash("No labeled images to export yet.", "warning")
        return redirect(url_for("export.export_page"))

    export_path = build_json_export(
        labeled_images,
        current_app.config["EXPORT_FOLDER"],
        export_format=export_format,
    )
    return send_file(export_path, as_attachment=True)
