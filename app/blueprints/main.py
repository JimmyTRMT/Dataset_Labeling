from datetime import datetime
from pathlib import Path
import json
from flask import Blueprint, current_app, render_template, request, send_file
from sqlalchemy import func
from ..models import ImageRecord, db

# Main page routes (labeling, history, dashboard, file serving)

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():
    active_session = request.args.get("session_name", "").strip()
    unlabeled_query = ImageRecord.query.filter_by(status="unlabeled")
    if active_session:
        unlabeled_query = unlabeled_query.filter_by(session_name=active_session)

    unlabeled_images = unlabeled_query.order_by(ImageRecord.uploaded_at.asc()).all()

    auto_advance = request.args.get("auto_advance", default="1") != "0"
    selected_image_id = request.args.get("image_id", type=int)
    unlabeled_image = None
    if selected_image_id is not None:
        unlabeled_image = next((img for img in unlabeled_images if img.id == selected_image_id), None)
    if unlabeled_image is None and unlabeled_images and auto_advance:
        unlabeled_image = unlabeled_images[0]

    if unlabeled_image and unlabeled_image.last_viewed_at is None:
        unlabeled_image.last_viewed_at = datetime.utcnow()
        db.session.commit()

    labels = []
    if unlabeled_image and unlabeled_image.custom_labels:
        try:
            labels = json.loads(unlabeled_image.custom_labels)
        except Exception:
            pass

    if not unlabeled_image and active_session:
        session_reference = (
            ImageRecord.query.filter_by(session_name=active_session)
            .order_by(ImageRecord.uploaded_at.desc())
            .first()
        )
        if session_reference:
            if session_reference.custom_labels:
                try:
                    labels = json.loads(session_reference.custom_labels)
                except Exception:
                    pass

    if not labels:
        label_one = unlabeled_image.label_option_1 if unlabeled_image else "Label 1"
        label_two = unlabeled_image.label_option_2 if unlabeled_image else "Label 2"
        labels = [label_one, label_two]

    labeled_query = ImageRecord.query.filter_by(status="labeled")
    if active_session:
        labeled_query = labeled_query.filter_by(session_name=active_session)

    unlabeled_count = len(unlabeled_images)
    labeled_count = labeled_query.count()
    total_count = unlabeled_count + labeled_count
    progress_percent = int((labeled_count / total_count) * 100) if total_count > 0 else 0

    return render_template(
        "index.html",
        unlabeled_images=unlabeled_images,
        unlabeled_image=unlabeled_image,
        unlabeled_count=unlabeled_count,
        labeled_count=labeled_count,
        total_count=total_count,
        progress_percent=progress_percent,
        auto_advance=auto_advance,
        active_session=active_session,
        label_one=labels[0] if len(labels) > 0 else "Label 1",
        label_two=labels[1] if len(labels) > 1 else "Label 2",
        labels=labels,
    )


@main_bp.get("/history")
def history():
    session_names = (
        db.session.query(ImageRecord.session_name)
        .distinct()
        .order_by(ImageRecord.session_name.asc())
        .all()
    )

    sessions_rows: list[dict] = []
    for session_entry in session_names:
        session_name = session_entry.session_name
        image_count = ImageRecord.query.filter_by(session_name=session_name).count()
        labeled_count = ImageRecord.query.filter_by(session_name=session_name, status="labeled").count()
        reference = (
            ImageRecord.query.filter_by(session_name=session_name)
            .order_by(ImageRecord.uploaded_at.desc())
            .first()
        )
        if reference:
            custom_labels = []
            if reference.custom_labels:
                try:
                    custom_labels = json.loads(reference.custom_labels)
                except Exception:
                    pass
            if not custom_labels:
                custom_labels = [reference.label_option_1, reference.label_option_2]

            sessions_rows.append(
                {
                    "session_name": session_name,
                    "image_count": image_count,
                    "labeled_count": labeled_count,
                    "last_upload": reference.uploaded_at,
                    "label_one": reference.label_option_1,
                    "label_two": reference.label_option_2,
                    "labels": custom_labels,
                }
            )

    sessions_rows.sort(key=lambda row: row["last_upload"], reverse=True)

    latest_record = ImageRecord.query.order_by(ImageRecord.uploaded_at.desc()).first()
    default_session_name = f"Session {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
    selected_session_name = request.args.get("session_name", "").strip()
    selected_reference = None
    if selected_session_name:
        selected_reference = (
            ImageRecord.query.filter_by(session_name=selected_session_name)
            .order_by(ImageRecord.uploaded_at.desc())
            .first()
        )
    suggested_source = selected_reference or latest_record
    
    suggested_labels = []
    if suggested_source and suggested_source.custom_labels:
        try:
            suggested_labels = json.loads(suggested_source.custom_labels)
        except Exception:
            pass
    if not suggested_labels and suggested_source:
        suggested_labels = [suggested_source.label_option_1, suggested_source.label_option_2]

    return render_template(
        "history.html",
        sessions_rows=sessions_rows,
        suggested_session_name=suggested_source.session_name if suggested_source else default_session_name,
        suggested_label_one=suggested_source.label_option_1 if suggested_source else "labelOne",
        suggested_label_two=suggested_source.label_option_2 if suggested_source else "labelTwo",
        suggested_labels=suggested_labels if suggested_labels else ["labelOne", "labelTwo"],
    )


@main_bp.get("/dashboard")
def dashboard():
    labeled_rows = (
        db.session.query(ImageRecord.label, func.count(ImageRecord.id))
        .filter(ImageRecord.status == "labeled")
        .group_by(ImageRecord.label)
        .all()
    )

    label_counts: dict[str, int] = {}
    for label_name, count in labeled_rows:
        display_label = label_name or "(No label)"
        label_counts[display_label] = int(count)
    if not label_counts:
        label_counts = {"No data": 1}

    average_seconds = (
        db.session.query(func.avg(ImageRecord.labeling_duration_seconds))
        .filter(ImageRecord.labeling_duration_seconds.isnot(None))
        .scalar()
    )
    avg_labeling_seconds = float(average_seconds) if average_seconds is not None else None

    labels_per_day_rows = (
        db.session.query(func.date(ImageRecord.labeled_at), func.count(ImageRecord.id))
        .filter(ImageRecord.status == "labeled", ImageRecord.labeled_at.isnot(None))
        .group_by(func.date(ImageRecord.labeled_at))
        .order_by(func.date(ImageRecord.labeled_at).asc())
        .all()
    )

    day_labels: list[str] = []
    day_values: list[int] = []
    for day_value, count in labels_per_day_rows:
        day_labels.append(str(day_value))
        day_values.append(int(count))

    return render_template(
        "dashboard.html",
        chart_labels=list(label_counts.keys()),
        chart_values=list(label_counts.values()),
        day_labels=day_labels,
        day_values=day_values,
        total_labeled=sum(label_counts.values()),
        avg_labeling_seconds=avg_labeling_seconds,
    )


@main_bp.get("/uploads/<path:filename>")
def serve_upload(filename: str):
    return send_file(Path(current_app.config["UPLOAD_FOLDER"]) / filename)
