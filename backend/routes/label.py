from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from backend.models.database import ImageRecord, db
from backend.services.image_service import delete_image_file


label_bp = Blueprint("label", __name__)


# Renders the labeling page. The current image is either the one passed in
# the URL or the oldest unlabeled image. Label buttons match its project.
@label_bp.get("/label")
def label_page():
    selected_id = request.args.get("image_id", type=int)

    unlabeled_images = (
        ImageRecord.query.filter_by(status="unlabeled")
        .order_by(ImageRecord.uploaded_at.asc())
        .all()
    )

    current_image = None
    current_index = -1
    if selected_id is not None:
        for index, image in enumerate(unlabeled_images):
            if image.id == selected_id:
                current_image = image
                current_index = index
                break
    if current_image is None and unlabeled_images:
        current_image = unlabeled_images[0]
        current_index = 0

    # The Skip button advances to the next image in upload order, wrapping
    # to the first one once we reach the end. We compute this server-side
    # so the template stays declarative.
    next_image = None
    if len(unlabeled_images) > 1 and current_index >= 0:
        next_image = unlabeled_images[(current_index + 1) % len(unlabeled_images)]

    if current_image:
        # Reset on every page load so refresh / tab-switch don't inflate
        # the labeling duration we record later.
        current_image.last_viewed_at = datetime.utcnow()
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Failed to update last_viewed_at")

    project_labels = current_app.config["PROJECT_LABELS"]
    available_labels: list[str] = []
    if current_image:
        # If the project tag is unknown (e.g. a legacy row), fall back to
        # an empty list so the page still renders without crashing.
        available_labels = project_labels.get(current_image.project, [])

    total_count = ImageRecord.query.count()
    labeled_count = ImageRecord.query.filter_by(status="labeled").count()

    return render_template(
        "label.html",
        current_image=current_image,
        next_image=next_image,
        unlabeled_images=unlabeled_images,
        available_labels=available_labels,
        total_count=total_count,
        labeled_count=labeled_count,
        unlabeled_count=total_count - labeled_count,
    )


# Records a label, computes the time spent on the image, and jumps to the
# next unlabeled image inside the same project so the user keeps the flow.
@label_bp.post("/label/<int:image_id>")
def assign_label(image_id: int):
    selected_label = ""
    json_payload = request.get_json(silent=True)
    if json_payload and isinstance(json_payload, dict):
        selected_label = str(json_payload.get("label", "")).strip()
    if not selected_label:
        selected_label = request.form.get("label", "").strip()

    if not selected_label:
        flash("No label received.", "warning")
        return redirect(url_for("label.label_page", image_id=image_id))

    image = ImageRecord.query.get_or_404(image_id)

    duration_seconds = None
    if image.last_viewed_at:
        duration_seconds = max(0.0, (datetime.utcnow() - image.last_viewed_at).total_seconds())

    image.mark_as_labeled(selected_label, duration_seconds=duration_seconds)
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to save label for image %s", image_id)
        flash("Could not save the label. Please try again.", "warning")
        return redirect(url_for("label.label_page", image_id=image_id))

    flash(f"Image '{image.original_filename}' labeled: {selected_label}", "success")

    # Stay inside the same project as long as work remains, then fall back
    # to anything else still unlabeled.
    next_unlabeled = (
        ImageRecord.query.filter_by(status="unlabeled", project=image.project)
        .order_by(ImageRecord.uploaded_at.asc())
        .first()
    )
    if next_unlabeled is None:
        next_unlabeled = (
            ImageRecord.query.filter_by(status="unlabeled")
            .order_by(ImageRecord.uploaded_at.asc())
            .first()
        )

    if next_unlabeled:
        return redirect(url_for("label.label_page", image_id=next_unlabeled.id))

    flash("All images have been labeled.", "success")
    return redirect(url_for("label.dataset_browser"))


# Deletes the image from disk first, then the DB row. If the DB step fails,
# the file is already gone but the transaction is rolled back; the next
# scheduled cleanup (or a manual delete retry) reconciles state.
@label_bp.post("/label/<int:image_id>/delete")
def delete_image(image_id: int):
    image = ImageRecord.query.get_or_404(image_id)
    delete_image_file(image, current_app.config["UPLOAD_FOLDER"])
    try:
        db.session.delete(image)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to delete image %s", image_id)
        flash("Could not delete the image. Please try again.", "warning")
        return redirect(url_for("label.dataset_browser"))

    flash("Image deleted.", "success")
    return redirect(url_for("label.dataset_browser"))


# Lists images with two independent filters: project (all / DR / SmartBin)
# and status (all / labeled / unlabeled). Both sit in the URL so links stay
# shareable.
@label_bp.get("/dataset")
def dataset_browser():
    label_filter = request.args.get("filter", "all").strip().lower()
    project_filter = request.args.get("project", "all").strip()

    query = ImageRecord.query
    if project_filter in current_app.config["PROJECT_IDS"]:
        query = query.filter_by(project=project_filter)
    else:
        project_filter = "all"

    if label_filter == "labeled":
        query = query.filter_by(status="labeled")
    elif label_filter == "unlabeled":
        query = query.filter_by(status="unlabeled")
    else:
        label_filter = "all"

    images = query.order_by(ImageRecord.uploaded_at.desc()).all()

    return render_template(
        "dashboard.html",
        images=images,
        active_filter=label_filter,
        active_project=project_filter,
        project_ids=current_app.config["PROJECT_IDS"],
    )
