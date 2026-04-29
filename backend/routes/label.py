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

from backend.models.database import ImageRecord, db
from backend.services.image_service import delete_image_file


label_bp = Blueprint("label", __name__)


@label_bp.get("/label")
def label_page():
    selected_id = request.args.get("image_id", type=int)

    unlabeled_images = (
        ImageRecord.query.filter_by(status="unlabeled")
        .order_by(ImageRecord.uploaded_at.asc())
        .all()
    )

    current_image = None
    if selected_id is not None:
        current_image = next((img for img in unlabeled_images if img.id == selected_id), None)
    if current_image is None and unlabeled_images:
        current_image = unlabeled_images[0]

    if current_image:
        # Reset on every page load so refresh / tab-switch don't inflate the duration.
        current_image.last_viewed_at = datetime.utcnow()
        db.session.commit()

    total_count = ImageRecord.query.count()
    labeled_count = ImageRecord.query.filter_by(status="labeled").count()

    return render_template(
        "label.html",
        current_image=current_image,
        unlabeled_images=unlabeled_images,
        available_labels=current_app.config["AVAILABLE_LABELS"],
        total_count=total_count,
        labeled_count=labeled_count,
        unlabeled_count=total_count - labeled_count,
    )


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
    db.session.commit()

    flash(f"Image '{image.original_filename}' labeled: {selected_label}", "success")

    next_unlabeled = (
        ImageRecord.query.filter_by(status="unlabeled")
        .order_by(ImageRecord.uploaded_at.asc())
        .first()
    )
    if next_unlabeled:
        return redirect(url_for("label.label_page", image_id=next_unlabeled.id))

    flash("All images have been labeled.", "success")
    return redirect(url_for("label.dataset_browser"))


@label_bp.post("/label/<int:image_id>/delete")
def delete_image(image_id: int):
    image = ImageRecord.query.get_or_404(image_id)
    delete_image_file(image, current_app.config["UPLOAD_FOLDER"])
    db.session.delete(image)
    db.session.commit()

    flash("Image deleted.", "success")
    return redirect(url_for("label.dataset_browser"))


@label_bp.get("/dataset")
def dataset_browser():
    label_filter = request.args.get("filter", "all").strip().lower()

    query = ImageRecord.query
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
    )
