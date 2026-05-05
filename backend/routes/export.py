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
from backend.services.export_service import (
    build_csv_export,
    build_html_export,
    build_json_export,
)


export_bp = Blueprint("export", __name__)


# Export page shows one section per project, each with its own counts and
# its own set of CSV / JSON download buttons.
@export_bp.get("/export")
def export_page():
    project_ids = current_app.config["PROJECT_IDS"]
    counts: dict[str, dict[str, int]] = {}
    for project_id in project_ids:
        counts[project_id] = {
            "total": ImageRecord.query.filter_by(project=project_id).count(),
            "labeled": ImageRecord.query.filter_by(project=project_id, status="labeled").count(),
        }

    return render_template(
        "export.html",
        project_ids=project_ids,
        counts=counts,
    )


# _resolve_project validates the ?project= query param against the known IDs.
# Returns the validated project name or None if the value is missing/invalid.
def _resolve_project() -> str | None:
    project = request.args.get("project", "").strip()
    if project not in current_app.config["PROJECT_IDS"]:
        return None
    return project


# Export labeled images of one project as CSV (full or AI layout).
@export_bp.get("/export/csv")
def export_csv():
    project = _resolve_project()
    if project is None:
        flash("Invalid project. Choose DR or SmartBin.", "warning")
        return redirect(url_for("export.export_page"))

    export_format = request.args.get("format", "full").strip().lower()
    labeled_images = (
        ImageRecord.query.filter_by(status="labeled", project=project)
        .order_by(ImageRecord.id.asc())
        .all()
    )
    if not labeled_images:
        flash(f"No labeled images in {project} project yet.", "warning")
        return redirect(url_for("export.export_page"))

    export_path = build_csv_export(
        labeled_images,
        current_app.config["EXPORT_FOLDER"],
        project=project,
        export_format=export_format,
    )
    return send_file(export_path, as_attachment=True)


# Export labeled images of one project as a single self-contained HTML file:
# a 2-column table (image | label) with images embedded as base64. Open in
# any browser - no companion folder needed.
@export_bp.get("/export/html")
def export_html():
    project = _resolve_project()
    if project is None:
        flash("Invalid project. Choose DR or SmartBin.", "warning")
        return redirect(url_for("export.export_page"))

    labeled_images = (
        ImageRecord.query.filter_by(status="labeled", project=project)
        .order_by(ImageRecord.id.asc())
        .all()
    )
    if not labeled_images:
        flash(f"No labeled images in {project} project yet.", "warning")
        return redirect(url_for("export.export_page"))

    export_path = build_html_export(
        labeled_images,
        current_app.config["EXPORT_FOLDER"],
        current_app.config["UPLOAD_FOLDER"],
        project=project,
    )
    return send_file(export_path, as_attachment=True)


# Export labeled images of one project as JSON (full or AI layout).
@export_bp.get("/export/json")
def export_json():
    project = _resolve_project()
    if project is None:
        flash("Invalid project. Choose DR or SmartBin.", "warning")
        return redirect(url_for("export.export_page"))

    export_format = request.args.get("format", "full").strip().lower()
    labeled_images = (
        ImageRecord.query.filter_by(status="labeled", project=project)
        .order_by(ImageRecord.id.asc())
        .all()
    )
    if not labeled_images:
        flash(f"No labeled images in {project} project yet.", "warning")
        return redirect(url_for("export.export_page"))

    export_path = build_json_export(
        labeled_images,
        current_app.config["EXPORT_FOLDER"],
        project=project,
        export_format=export_format,
    )
    return send_file(export_path, as_attachment=True)
