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
from flask_login import login_required

from backend.models.database import ImageRecord
from backend.services.export_service import (
    build_csv_export,
    build_html_export,
    build_json_export,
)


export_bp = Blueprint("export", __name__)


# Blueprint-level login guard - same pattern as annotation_bp / dashboard_bp.
@export_bp.before_request
@login_required
def _require_login():
    pass


@export_bp.get("/export")
def export_page():
    """One card per project, live counts, CSV / JSON / HTML buttons."""
    project_ids = current_app.config["PROJECT_IDS"]
    counts: dict[str, dict[str, int]] = {}
    for project_id in project_ids:
        counts[project_id] = {
            "total": ImageRecord.query.filter_by(project=project_id).count(),
            "labeled": ImageRecord.query.filter_by(
                project=project_id, status="labeled"
            ).count(),
        }

    return render_template(
        "export.html",
        project_ids=project_ids,
        counts=counts,
    )


# Returns the validated ?project= or None (so the caller can flash + redirect).
def _resolve_project() -> str | None:
    project = request.args.get("project", "").strip()
    if project not in current_app.config["PROJECT_IDS"]:
        return None
    return project


# Pre-flight shared by all three export formats.
def _labeled_images_or_redirect():
    project = _resolve_project()
    if project is None:
        flash("Invalid project. Choose Fundus or WasteSorting.", "warning")
        return None, redirect(url_for("export.export_page"))

    labeled_images = (
        ImageRecord.query.filter_by(status="labeled", project=project)
        .order_by(ImageRecord.id.asc())
        .all()
    )
    if not labeled_images:
        flash(f"No labeled images in {project} project yet.", "warning")
        return None, redirect(url_for("export.export_page"))

    return (project, labeled_images), None


# CSV: 26 columns, `;` delimiter so European Excel opens it without a wizard.
@export_bp.get("/export/csv")
def export_csv():
    payload, redirect_response = _labeled_images_or_redirect()
    if payload is None:
        return redirect_response

    project, labeled_images = payload
    try:
        export_path = build_csv_export(
            labeled_images,
            current_app.config["EXPORT_FOLDER"],
            current_app.config["UPLOAD_FOLDER"],
            project=project,
        )
    except OSError:
        current_app.logger.exception("CSV export failed for project %s", project)
        flash("Could not write the CSV file. Please try again.", "warning")
        return redirect(url_for("export.export_page"))

    return send_file(export_path, as_attachment=True)


# HTML: one self-contained file, images base64-embedded, no companion folder.
@export_bp.get("/export/html")
def export_html():
    payload, redirect_response = _labeled_images_or_redirect()
    if payload is None:
        return redirect_response

    project, labeled_images = payload
    try:
        export_path = build_html_export(
            labeled_images,
            current_app.config["EXPORT_FOLDER"],
            current_app.config["UPLOAD_FOLDER"],
            project=project,
        )
    except OSError:
        current_app.logger.exception("HTML export failed for project %s", project)
        flash("Could not write the HTML file. Please try again.", "warning")
        return redirect(url_for("export.export_page"))

    return send_file(export_path, as_attachment=True)


# JSON: flat array of dicts, same 26 keys as the CSV, numbers (not strings).
@export_bp.get("/export/json")
def export_json():
    payload, redirect_response = _labeled_images_or_redirect()
    if payload is None:
        return redirect_response

    project, labeled_images = payload
    try:
        export_path = build_json_export(
            labeled_images,
            current_app.config["EXPORT_FOLDER"],
            current_app.config["UPLOAD_FOLDER"],
            project=project,
        )
    except OSError:
        current_app.logger.exception("JSON export failed for project %s", project)
        flash("Could not write the JSON file. Please try again.", "warning")
        return redirect(url_for("export.export_page"))

    return send_file(export_path, as_attachment=True)
