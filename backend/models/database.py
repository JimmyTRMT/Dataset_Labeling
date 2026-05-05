from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


# ImageRecord represents one uploaded image plus all the metadata we track
# around it (project, contributor, label, timestamps).
class ImageRecord(db.Model):
    __tablename__ = "images"

    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    # Each image belongs to one research project (DR or SmartBin). Drives
    # which label set is offered on the labeling page and which export
    # bucket the row ends up in.
    project = db.Column(db.String(50), nullable=False, default="DR")
    contributor = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    label = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="unlabeled")

    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    labeled_at = db.Column(db.DateTime, nullable=True)
    last_viewed_at = db.Column(db.DateTime, nullable=True)
    labeling_duration_seconds = db.Column(db.Float, nullable=True)

    # mark_as_labeled flips the row from "unlabeled" to "labeled" and records
    # how long the annotation took.
    def mark_as_labeled(self, label_value: str, duration_seconds: float | None = None) -> None:
        self.label = label_value
        self.status = "labeled"
        self.labeled_at = datetime.utcnow()
        self.labeling_duration_seconds = duration_seconds
        self.last_viewed_at = None

    # to_export_row gives a flat dict used by both CSV and JSON exporters.
    def to_export_row(self) -> dict:
        return {
            "id": self.id,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "image_path": f"data/images/{self.stored_filename}",
            "project": self.project,
            "contributor": self.contributor or "",
            "notes": self.notes or "",
            "label": self.label or "",
            "status": self.status,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else "",
            "labeled_at": self.labeled_at.isoformat() if self.labeled_at else "",
        }
