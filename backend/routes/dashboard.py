from flask import Blueprint, abort, current_app, render_template
from flask_login import login_required
from sqlalchemy import func

from backend.models.database import ImageRecord, db


dashboard_bp = Blueprint("dashboard", __name__)


# Blueprint-level login guard - same pattern as annotation_bp / export_bp.
@dashboard_bp.before_request
@login_required
def _require_login():
    pass


@dashboard_bp.get("/dashboard/<dataset_type>")
def dataset_dashboard(dataset_type: str):
    """Live label distribution for one project."""
    if dataset_type not in current_app.config["PROJECT_IDS"]:
        abort(404)

    # GROUP BY in SQL - never hardcode labels here. Any label present in
    # the data shows up; removed labels drop out on their own.
    rows = (
        db.session.query(ImageRecord.label, func.count(ImageRecord.id))
        .filter(ImageRecord.project == dataset_type)
        .filter(ImageRecord.status == "labeled")
        .filter(ImageRecord.label.isnot(None))
        .group_by(ImageRecord.label)
        .order_by(ImageRecord.label.asc())
        .all()
    )

    label_counts = [{"label": label, "count": int(count)} for label, count in rows]
    total = sum(item["count"] for item in label_counts)

    return render_template(
        "analytics.html",
        dataset_type=dataset_type,
        label_counts=label_counts,
        total=total,
    )
