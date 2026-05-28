from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


# Two user roles. Admins are reserved for future privileged actions; for
# now every user can annotate and browse.
ROLE_ADMIN = "admin"
ROLE_ANNOTATOR = "annotator"

# PBKDF2-SHA256 is the algorithm Werkzeug's generate_password_hash uses
# when we pass "pbkdf2:sha256". Centralised here so any future change
# (e.g. argon2 via passlib) only touches one place.
PASSWORD_HASH_METHOD = "pbkdf2:sha256"


# Represents a registered user. Passwords AND security answers are stored
# as PBKDF2-SHA256 hashes - the plain text never touches the database.
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    # Role gates future admin-only actions. Defaults to annotator.
    role = db.Column(db.String(20), nullable=False, default=ROLE_ANNOTATOR)
    # Free-form question the user picks themselves so the answer is
    # something only they would naturally know.
    security_question = db.Column(db.String(255), nullable=False)
    # The answer is hashed too - if the DB leaks, attackers can't read
    # what was, in effect, a second password.
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
        # Trim + lowercase so "Whiskers", "whiskers", "  whiskers " all match.
        # We do NOT touch the question (capitalisation matters there).
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


# ImageRecord represents one uploaded image plus all the metadata we track
# around it (project, contributor, label, timestamps).
class ImageRecord(db.Model):
    __tablename__ = "images"

    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    # Each image belongs to one research project (Fundus or WasteSorting).
    # Drives which label set is offered on the labeling page and which
    # export bucket the row ends up in.
    project = db.Column(db.String(50), nullable=False, default="Fundus")
    # Captured from current_user.username at annotation time.
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
