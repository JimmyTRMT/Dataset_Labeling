from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# Database models 
db = SQLAlchemy()

class ImageRecord(db.Model):
    # One uploaded image and its labeling metadata.
    __tablename__ = "images"

    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    file_path = db.Column(db.String(500), nullable=False)
    session_name = db.Column(db.String(255), nullable=False, default="Default Session")
    label_option_1 = db.Column(db.String(100), nullable=False, default="labelOne")
    label_option_2 = db.Column(db.String(100), nullable=False, default="labelTwo")
    custom_labels = db.Column(db.Text, nullable=True)

    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    labeled_at = db.Column(db.DateTime, nullable=True)
    last_viewed_at = db.Column(db.DateTime, nullable=True)
    labeling_duration_seconds = db.Column(db.Float, nullable=True)

    label = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="unlabeled")
    #
    def mark_as_labeled(self, label_value: str, duration_seconds: float | None = None) -> None:
        # Update the record to reflect that it has been labeled.
        self.label = label_value
        self.status = "labeled"
        self.labeled_at = datetime.utcnow()
        self.labeling_duration_seconds = duration_seconds
        self.last_viewed_at = None

        # Convert the record to a dictionary suitable for CSV export.
    def to_export_row(self) -> dict:
        return {
            "id": self.id,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "session_name": self.session_name,
            "label_option_1": self.label_option_1,
            "label_option_2": self.label_option_2,
            "custom_labels": self.custom_labels or "",
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else "",
            "labeled_at": self.labeled_at.isoformat() if self.labeled_at else "",
            "label": self.label or "",
            "status": self.status,
        }
