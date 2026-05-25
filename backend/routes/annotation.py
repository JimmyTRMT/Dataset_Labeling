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
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from backend.models.database import ImageRecord, db
from backend.services.image_service import (
    delete_image_file,
    finalize_with_label,
    persist_pending_image,
)


annotation_bp = Blueprint("annotation", __name__)


# Every route below requires an authenticated user. Registering the
# decorator at the blueprint level (via before_request) keeps the route
# bodies clean and guarantees we never accidentally leave one public.
@annotation_bp.before_request
@login_required
def _require_login():
    pass


# The annotation page has two states:
#   1. Upload form  - when no pending image is waiting,
#   2. Labeling UI  - when at least one image is uploaded but unlabeled.
# We pick the right state on every GET so the workflow flows naturally:
# upload -> label -> upload next -> label -> ...
@annotation_bp.get("/annotation")
def annotation_page():
    pending_image = (
        ImageRecord.query.filter_by(status="unlabeled")
        .order_by(ImageRecord.uploaded_at.asc())
        .first()
    )
    project_labels = current_app.config["PROJECT_LABELS"]

    if pending_image:
        return render_template(
            "annotation.html",
            mode="label",
            current_image=pending_image,
            available_labels=project_labels.get(pending_image.project, []),
        )

    return render_template(
        "annotation.html",
        mode="upload",
        project_ids=current_app.config["PROJECT_IDS"],
    )


# Stage 1 - upload only. Validates project + image + description (the
# label is picked at stage 2) and stages the file in _pending/. The
# author field on the form is read-only client-side; we ignore whatever
# the request sends and always use current_user.username server-side so
# a tampered POST cannot impersonate someone else.
@annotation_bp.post("/annotation/upload")
def submit_upload():
    project = request.form.get("project", "").strip()
    description = request.form.get("description", "").strip()
    image_file = request.files.get("image")
    author = current_user.username

    if project not in current_app.config["PROJECT_IDS"]:
        flash("Please choose a dataset (Fundus or WasteSorting).", "warning")
        return redirect(url_for("annotation.annotation_page"))
    if not description:
        flash("Description is required.", "warning")
        return redirect(url_for("annotation.annotation_page"))
    if image_file is None or not image_file.filename:
        flash("Please choose one image file.", "warning")
        return redirect(url_for("annotation.annotation_page"))

    try:
        record = persist_pending_image(
            image_file,
            current_app.config["UPLOAD_FOLDER"],
            project=project,
            author=author,
            description=description,
        )
    except ValueError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("annotation.annotation_page"))
    except OSError:
        current_app.logger.exception("Failed to write uploaded image to disk")
        flash("Could not save the image. Please try again.", "warning")
        return redirect(url_for("annotation.annotation_page"))

    try:
        db.session.add(record)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to insert pending image row")
        delete_image_file(record, current_app.config["UPLOAD_FOLDER"])
        flash("Could not save the upload. Please try again.", "warning")
        return redirect(url_for("annotation.annotation_page"))

    flash(f"Uploaded {record.stored_filename}. Now choose a label.", "success")
    return redirect(url_for("annotation.annotation_page"))


# Stage 2 - apply a label to a pending image and finalize it. Moves the
# file from _pending/ to its label folder and flips status to "labeled".
@annotation_bp.post("/annotation/<int:image_id>/label")
def submit_label(image_id: int):
    image = ImageRecord.query.get_or_404(image_id)
    label = request.form.get("label", "").strip()

    valid_labels = current_app.config["PROJECT_LABELS"].get(image.project, [])
    if label not in valid_labels:
        flash("Please choose a valid label for this image.", "warning")
        return redirect(url_for("annotation.annotation_page"))

    try:
        finalize_with_label(image, label, current_app.config["UPLOAD_FOLDER"])
    except OSError:
        current_app.logger.exception("Failed to move pending image %s into its label folder", image_id)
        flash("Could not move the image file. Please try again.", "warning")
        return redirect(url_for("annotation.annotation_page"))

    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to commit label for image %s", image_id)
        flash("Could not save the label. Please try again.", "warning")
        return redirect(url_for("annotation.annotation_page"))

    flash(f"Saved {image.stored_filename} - {image.label}.", "success")
    return redirect(url_for("annotation.annotation_page"))


# Removes a pending or finalized image. Disk cleanup first, then DB row.
@annotation_bp.post("/annotation/<int:image_id>/delete")
def delete_annotation(image_id: int):
    image = ImageRecord.query.get_or_404(image_id)
    delete_image_file(image, current_app.config["UPLOAD_FOLDER"])
    try:
        db.session.delete(image)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to delete image %s", image_id)
        flash("Could not delete the image. Please try again.", "warning")
        return redirect(url_for("annotation.dataset_browser"))

    flash("Image deleted.", "success")
    # Send the user back to wherever they came from: the dataset table for
    # finalized rows, the annotation page for pending rows.
    target = "annotation.dataset_browser" if image.status == "labeled" else "annotation.annotation_page"
    return redirect(url_for(target))


# Dataset browser is now project-scoped. The default URL redirects to the
# first project so the nav link in base.html stays simple, while each
# project gets its own page accessible via tabs.
@annotation_bp.get("/dataset")
def dataset_browser():
    default_project = current_app.config["PROJECT_IDS"][0]
    return redirect(url_for("annotation.dataset_for_project", project_id=default_project))


# One page per project. The template renders tabs to switch between them.
@annotation_bp.get("/dataset/<project_id>")
def dataset_for_project(project_id: str):
    project_ids = current_app.config["PROJECT_IDS"]
    if project_id not in project_ids:
        flash(f"Unknown project '{project_id}'.", "warning")
        return redirect(url_for("annotation.dataset_browser"))

    images = (
        ImageRecord.query.filter_by(project=project_id, status="labeled")
        .order_by(ImageRecord.uploaded_at.desc())
        .all()
    )

    return render_template(
        "dashboard.html",
        project_ids=project_ids,
        active_project=project_id,
        images=images,
    )


# Serves a stored image. send_from_directory uses safe_join, which blocks
# path traversal attempts (e.g. ../../etc/passwd).
@annotation_bp.get("/images/<path:filename>")
def serve_image(filename: str):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
