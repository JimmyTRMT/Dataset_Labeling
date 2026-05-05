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

from backend.models.database import ImageRecord, db
from backend.services.image_service import persist_uploaded_images


upload_bp = Blueprint("upload", __name__)

# Upload page renders the form. The list of valid project IDs is passed in
# so the radio inputs and the validation message stay in sync with config.
@upload_bp.get("/upload")
def upload_page():
    return render_template(
        "upload.html",
        project_ids=current_app.config["PROJECT_IDS"],
    )


# Handle image uploads, save files, create database records, and redirect to labeling page.
@upload_bp.post("/upload")
def upload_images():
    project = request.form.get("project", "").strip()
    files = request.files.getlist("images")
    contributor = request.form.get("contributor", "").strip() or None
    notes = request.form.get("notes", "").strip() or None

    # Project must be one of the known IDs. Anything else is rejected so we
    # never persist images without a valid bucket.
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

    for record in saved_records:
        db.session.add(record)

    if saved_records:
        db.session.commit()
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

# Serve uploaded images for display in the labeling interface
@upload_bp.get("/images/<path:filename>")
def serve_image(filename: str):
    # send_from_directory uses safe_join under the hood and blocks path traversal.
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
