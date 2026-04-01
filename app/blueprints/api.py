from datetime import datetime
from pathlib import Path
import json
from flask import Blueprint, current_app, flash, redirect, request, send_file, url_for
from ..models import ImageRecord, db
from ..services.export_service import build_export_csv
from ..services.image_service import persist_uploaded_images

# API routes for image upload, labeling, export, and deletion

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.post("/upload")
def upload_images():
    # Get uploaded files and session details
    files = request.files.getlist("images")
    session_name = request.form.get("session_name", "").strip() or f"Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
    
    # Extract or default label options
    label_one = (
        request.form.get("label_option_1", "").strip()
        or request.form.get("label_one", "").strip()
        or "labelOne"
    )
    label_two = (
        request.form.get("label_option_2", "").strip()
        or request.form.get("label_two", "").strip()
        or "labelTwo"
    )
    
    # Get custom labels from form
    labels_from_form = request.form.getlist("custom_labels")
    labels_from_form = [lbl.strip() for lbl in labels_from_form if lbl.strip()]
    
    # Use default labels if no custom labels provided
    if not labels_from_form:
        l1 = request.form.get("label_option_1", "").strip() or request.form.get("label_one", "").strip() or "labelOne"
        l2 = request.form.get("label_option_2", "").strip() or request.form.get("label_two", "").strip() or "labelTwo"
        labels_from_form = [l1, l2]
        
    custom_labels_json = json.dumps(labels_from_form)
    
    label_one_fallback = labels_from_form[0] if len(labels_from_form) > 0 else "labelOne"
    label_two_fallback = labels_from_form[1] if len(labels_from_form) > 1 else "labelTwo"
    
    # Check if uploading to existing or new session
    upload_mode = request.form.get("upload_mode", "new")

    existing_session_image = None
    if upload_mode == "existing":
        # Retrieve existing session
        existing_session_image = (
            ImageRecord.query.filter_by(session_name=session_name)
            .order_by(ImageRecord.uploaded_at.desc())
            .first()
        )
        if not existing_session_image:
            flash("Session not found. Use 'Create session' to create a new one.", "warning")
            return redirect(url_for("main.history"))

        # Use existing session labels
        label_one = existing_session_image.label_option_1
        label_two = existing_session_image.label_option_2
        label_one_fallback = existing_session_image.label_option_1
        label_two_fallback = existing_session_image.label_option_2
        custom_labels_json = existing_session_image.custom_labels
    else:
        # Ensure unique session name for new uploads
        session_name = ensure_unique_session_name(session_name)

    # Validate files
    if not files or all(not file.filename for file in files):
        flash("No image selected.", "warning")
        return redirect(url_for("main.history"))

    saved_records, invalid_detected = persist_uploaded_images(
        files,
        current_app.config["UPLOAD_FOLDER"],
        session_name=session_name,
        label_option_1=label_one_fallback,
        label_option_2=label_two_fallback,
        custom_labels=custom_labels_json,
    )

    # Commit saved records
    for record in saved_records:
        db.session.add(record)

    if saved_records:
        db.session.commit()
        if upload_mode == "existing" and existing_session_image:
            flash(
                f"{len(saved_records)} image(s) added to existing session '{session_name}'.",
                "success",
            )
            # Redirect to next unlabeled image
            next_unlabeled = (
                ImageRecord.query.filter_by(status="unlabeled", session_name=session_name)
                .order_by(ImageRecord.uploaded_at.asc())
                .first()
            )
            if next_unlabeled:
                return redirect(
                    url_for(
                        "main.index",
                        image_id=next_unlabeled.id,
                        auto_advance="1",
                        session_name=session_name,
                    )
                )

            return redirect(url_for("main.index", auto_advance="1", session_name=session_name))
        else:
            flash(f"{len(saved_records)} image(s) imported successfully for session '{session_name}'.", "success")
    elif invalid_detected:
        flash(
            "No valid image found (allowed formats: png, jpg, jpeg, bmp, gif, tif, tiff, webp).",
            "warning",
        )
    else:
        flash("No image selected.", "warning")

    return redirect(url_for("main.history"))


@api_bp.post("/label/<int:image_id>")
def assign_label(image_id: int):
    # Get label from JSON or form data
    json_payload = request.get_json(silent=True)

    selected_label = ""
    if json_payload and isinstance(json_payload, dict):
        selected_label = str(json_payload.get("label", "")).strip()
    if not selected_label:
        selected_label = request.form.get("label", "").strip()

    auto_advance = request.form.get("auto_advance", "1") == "1"
    session_name = request.form.get("session_name", "").strip()
    
    if not selected_label:
        flash("No label received.", "warning")
        return redirect(
            url_for(
                "main.index",
                auto_advance="1" if auto_advance else "0",
                session_name=session_name or None,
            )
        )

    # Mark image as labeled
    image = ImageRecord.query.get_or_404(image_id)
    duration_seconds = None
    if image.last_viewed_at:
        duration_seconds = max(0.0, (datetime.utcnow() - image.last_viewed_at).total_seconds())

    image.mark_as_labeled(selected_label, duration_seconds=duration_seconds)
    db.session.commit()

    flash(f"Image {image.original_filename} labeled: {selected_label}", "success")
    
    # Find next unlabeled image
    next_query = ImageRecord.query.filter_by(status="unlabeled")
    if session_name:
        next_query = next_query.filter_by(session_name=session_name)

    next_unlabeled = next_query.order_by(ImageRecord.uploaded_at.asc()).first()
    
    # Redirect to next image or show completion message
    if next_unlabeled and auto_advance:
        return redirect(
            url_for(
                "main.index",
                image_id=next_unlabeled.id,
                auto_advance="1",
                session_name=session_name or None,
            )
        )
    if next_unlabeled and not auto_advance:
        return redirect(
            url_for(
                "main.index",
                auto_advance="0",
                session_name=session_name or None,
            )
        )

    flash("All images have been processed.", "success")
    return redirect(
        url_for(
            "main.index",
            auto_advance="1" if auto_advance else "0",
            session_name=session_name or None,
        )
    )


@api_bp.get("/export")
def export_csv():
    # Export all labeled images
    labeled_images = ImageRecord.query.filter_by(status="labeled").order_by(ImageRecord.id.asc()).all()
    export_format = request.args.get("format", "full").strip().lower()
    
    if not labeled_images:
        flash("No labeled data to export.", "warning")
        return redirect(url_for("main.index"))

    export_path = build_export_csv(
        labeled_images,
        current_app.config["EXPORT_FOLDER"],
        filename_prefix="export_global",
        export_format=export_format,
    )
    return send_file(export_path, as_attachment=True)


@api_bp.get("/export/session/<path:session_name>")
def export_csv_for_session(session_name: str):
    # Export images for specific session
    export_format = request.args.get("format", "full").strip().lower()
    session_images = (
        ImageRecord.query.filter_by(session_name=session_name)
        .order_by(ImageRecord.id.asc())
        .all()
    )
    
    if not session_images:
        flash("No data found for this session.", "warning")
        return redirect(url_for("main.history"))

    export_path = build_export_csv(
        session_images,
        current_app.config["EXPORT_FOLDER"],
        filename_prefix=f"export_{session_name}",
        export_format=export_format,
    )
    return send_file(export_path, as_attachment=True)


@api_bp.post("/reset-session")
def reset_session():
    # Archive current session
    flash("Session archived. You can start a new session with different labels.", "success")
    return redirect(url_for("main.history"))


@api_bp.post("/delete-session/<path:session_name>")
def delete_session(session_name: str):
    # Delete all images in session
    session_images = ImageRecord.query.filter_by(session_name=session_name).all()
    
    if not session_images:
        flash("Session not found.", "warning")
        return redirect(url_for("main.history"))

    deleted_count = 0
    for image in session_images:
        delete_image_file(image)
        db.session.delete(image)
        deleted_count += 1

    db.session.commit()
    flash(f"Session '{session_name}' deleted ({deleted_count} image(s)).", "success")
    return redirect(url_for("main.history"))


@api_bp.post("/delete-image/<int:image_id>")
def delete_image(image_id: int):
    # Delete single image
    session_name = request.form.get("session_name", "").strip()
    auto_advance = request.form.get("auto_advance", "1")

    image = ImageRecord.query.get_or_404(image_id)
    if not session_name:
        session_name = image.session_name

    delete_image_file(image)
    db.session.delete(image)
    db.session.commit()

    # Find next unlabeled image
    next_query = ImageRecord.query.filter_by(status="unlabeled")
    if session_name:
        next_query = next_query.filter_by(session_name=session_name)
    next_unlabeled = next_query.order_by(ImageRecord.uploaded_at.asc()).first()

    flash("Image deleted.", "success")
    if next_unlabeled:
        return redirect(
            url_for(
                "main.index",
                image_id=next_unlabeled.id,
                auto_advance=auto_advance,
                session_name=session_name or None,
            )
        )

    return redirect(
        url_for(
            "main.index",
            auto_advance=auto_advance,
            session_name=session_name or None,
        )
    )


def ensure_unique_session_name(base_name: str) -> str:
    # Append timestamp if session name already exists
    existing = ImageRecord.query.filter_by(session_name=base_name).first()
    if not existing:
        return base_name

    suffix = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{suffix}"


def delete_image_file(image: ImageRecord) -> None:
    # Remove image file from disk
    candidate_paths = []
    if image.file_path:
        candidate_paths.append(Path(image.file_path))
    candidate_paths.append(Path(current_app.config["UPLOAD_FOLDER"]) / image.stored_filename)

    for path in candidate_paths:
        try:
            if path.exists():
                path.unlink()
                break
        except OSError:
            continue
