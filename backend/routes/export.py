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


# Renders the export page with one card per project. Each card displays
# the live image counts and the four download buttons (CSV / JSON / HTML).
@export_bp.get("/export")
def export_page():
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


# Reads the ?project= query param and returns it only if it matches one of
# the configured project IDs. Returns None for missing or unknown values so
# the caller can flash a clear message and redirect.
def _resolve_project() -> str | None:
    project = request.args.get("project", "").strip()
    if project not in current_app.config["PROJECT_IDS"]:
        return None
    return project


# Common pre-flight: validate the project, fetch its labeled images, and
# either return them or redirect with an explanatory flash.
def _labeled_images_or_redirect():
    project = _resolve_project()
    if project is None:
        flash("Invalid project. Choose DR or SmartBin.", "warning")
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


# Exports labeled images of one project as CSV. The file follows the
# strict 26-column schema (img_path + 24 GLCM features + label) with a
# semicolon delimiter so European spreadsheets open it directly.
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


# Exports labeled images of one project as a single self-contained HTML
# file: a 2-column table (image | label) with images embedded as base64.
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


# Exports labeled images of one project as JSON. Each entry is a flat dict
# with the same 26 keys as the CSV (img_path, con1..corr4, asm1..asm4, label).
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
