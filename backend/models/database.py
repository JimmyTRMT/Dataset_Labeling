from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


ROLE_ADMIN = "admin"
ROLE_ANNOTATOR = "annotator"

# Single source of truth for the hashing scheme. Werkzeug's PBKDF2-SHA256
# at 1M iterations by default. Swap once here if argon2 lands later.
PASSWORD_HASH_METHOD = "pbkdf2:sha256"


class User(db.Model, UserMixin):
    """Registered user. Passwords AND security answers are PBKDF2-hashed."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_ANNOTATOR)
    # User-picked free-form question (the answer is effectively a second password).
    security_question = db.Column(db.String(255), nullable=False)
    security_answer_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # ----- password ------------------------------------------------------

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password, method=PASSWORD_HASH_METHOD)

    def check_password(self, raw_password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, raw_password)

    # ----- security answer ------------------------------------------------

    @staticmethod
    def _normalize_answer(raw_answer: str) -> str:
        # Trim + lowercase so "Whiskers" / "whiskers" / "  whiskers " all match.
        return (raw_answer or "").strip().lower()

    def set_security_answer(self, raw_answer: str) -> None:
        self.security_answer_hash = generate_password_hash(
            self._normalize_answer(raw_answer),
            method=PASSWORD_HASH_METHOD,
        )

    def check_security_answer(self, raw_answer: str) -> bool:
        if not self.security_answer_hash:
            return False
        return check_password_hash(self.security_answer_hash, self._normalize_answer(raw_answer))

    # ----- role helper ----------------------------------------------------

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN


class ImageRecord(db.Model):
    """One uploaded image plus its metadata."""

    __tablename__ = "images"

    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    # Picks the label set and the export bucket.
    project = db.Column(db.String(50), nullable=False, default="Fundus")
    # Stamped from current_user.username at annotation time.
    contributor = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    label = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="unlabeled")

    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    labeled_at = db.Column(db.DateTime, nullable=True)
    last_viewed_at = db.Column(db.DateTime, nullable=True)
    labeling_duration_seconds = db.Column(db.Float, nullable=True)

    def mark_as_labeled(self, label_value: str, duration_seconds: float | None = None) -> None:
        self.label = label_value
        self.status = "labeled"
        self.labeled_at = datetime.utcnow()
        self.labeling_duration_seconds = duration_seconds
        self.last_viewed_at = None

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
