from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from backend.models.database import ImageRecord, db
from backend.services.image_service import persist_uploaded_images


upload_bp = Blueprint("upload", __name__)


# Renders the upload form. Project IDs come from config so the radio
# buttons stay in sync with the rest of the app.
@upload_bp.get("/upload")
def upload_page():
    return render_template(
        "upload.html",
        project_ids=current_app.config["PROJECT_IDS"],
    )


# Validates the form, persists each accepted file, and creates one DB row
# per image. On any DB failure the transaction is rolled back so the table
# never ends up with rows pointing to nothing.
@upload_bp.post("/upload")
def upload_images():
    project = request.form.get("project", "").strip()
    files = request.files.getlist("images")
    contributor = request.form.get("contributor", "").strip() or None
    notes = request.form.get("notes", "").strip() or None

    if project not in current_app.config["PROJECT_IDS"]:
        flash("Please choose a project (DR or SmartBin) before uploading.", "warning")
        return redirect(url_for("upload.upload_page"))

    if not files or all(not file.filename for file in files):
        flash("Please choose at least one image.", "warning")
        return redirect(url_for("upload.upload_page"))

    saved_records, invalid_detected = persist_uploaded_images(
        files,
        current_app.config["UPLOAD_FOLDER"],
        project=project,
        contributor=contributor,
        notes=notes,
    )

    if saved_records:
        try:
            for record in saved_records:
                db.session.add(record)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Failed to persist uploaded images to database")
            flash("Could not save the upload. Please try again.", "warning")
            return redirect(url_for("upload.upload_page"))

        flash(
            f"Upload successful: {len(saved_records)} image(s) added to {project}.",
            "success",
        )
        return redirect(url_for("label.label_page"))

    if invalid_detected:
        flash(
            "No valid image found (allowed formats: png, jpg, jpeg, bmp, gif, tif, tiff, webp).",
            "warning",
        )
    else:
        flash("No image selected.", "warning")
    return redirect(url_for("upload.upload_page"))


# Serves a stored image file. Werkzeug's send_from_directory uses safe_join
# under the hood, so it blocks path traversal attempts.
@upload_bp.get("/images/<path:filename>")
def serve_image(filename: str):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
