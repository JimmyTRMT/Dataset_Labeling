from flask import Blueprint, abort, current_app, render_template
from flask_login import login_required
from sqlalchemy import func

from backend.models.database import ImageRecord, db


dashboard_bp = Blueprint("dashboard", __name__)


# Same blueprint-level guard as annotation/export: every endpoint here is
# behind @login_required.
@dashboard_bp.before_request
@login_required
def _require_login():
    pass


# Analytics view for one dataset.
@dashboard_bp.get("/dashboard/<dataset_type>")
def dataset_dashboard(dataset_type: str):
    if dataset_type not in current_app.config["PROJECT_IDS"]:
        abort(404)

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
