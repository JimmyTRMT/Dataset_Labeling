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


@upload_bp.get("/upload")
def upload_page():
    return render_template("upload.html")


@upload_bp.post("/upload")
def upload_images():
    files = request.files.getlist("images")
    contributor = request.form.get("contributor", "").strip() or None
    notes = request.form.get("notes", "").strip() or None

    if not files or all(not file.filename for file in files):
        flash("Please choose at least one image.", "warning")
        return redirect(url_for("upload.upload_page"))

    saved_records, invalid_detected = persist_uploaded_images(
        files,
        current_app.config["UPLOAD_FOLDER"],
        contributor=contributor,
        notes=notes,
    )

    for record in saved_records:
        db.session.add(record)

    if saved_records:
        db.session.commit()
        flash(f"Upload successful: {len(saved_records)} image(s) added.", "success")
        return redirect(url_for("label.label_page"))

    if invalid_detected:
        flash(
            "No valid image found (allowed formats: png, jpg, jpeg, bmp, gif, tif, tiff, webp).",
            "warning",
        )
    else:
        flash("No image selected.", "warning")
    return redirect(url_for("upload.upload_page"))


@upload_bp.get("/images/<path:filename>")
def serve_image(filename: str):
    # send_from_directory uses safe_join under the hood and blocks path traversal.
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
