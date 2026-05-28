"""WTForms used by the auth blueprint (login / register / forgot / reset)."""

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError

from backend.models.database import User


# Letters / digits / underscore / dash only. Predictable URLs and filenames.
USERNAME_PATTERN = r"^[A-Za-z0-9_\-]+$"
USERNAME_PATTERN_MESSAGE = "Username may contain letters, digits, underscore or dash only."

PASSWORD_MIN = 8
PASSWORD_MAX = 128


def _username_must_be_unique(form, field):
    if User.query.filter_by(username=field.data).first() is not None:
        raise ValidationError("Username already taken.")


class LoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(min=3, max=80)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=PASSWORD_MIN, max=PASSWORD_MAX)],
    )
    submit = SubmitField("Sign in")


class RegisterForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=80),
            Regexp(USERNAME_PATTERN, message=USERNAME_PATTERN_MESSAGE),
            _username_must_be_unique,
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=PASSWORD_MIN, max=PASSWORD_MAX,
                   message=f"Password must be at least {PASSWORD_MIN} characters."),
        ],
    )
    password_confirm = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords do not match."),
        ],
    )
    security_question = StringField(
        "Security question",
        validators=[DataRequired(), Length(min=5, max=255)],
    )
    security_answer = StringField(
        "Security answer",
        validators=[DataRequired(), Length(min=1, max=255)],
    )
    submit = SubmitField("Create account")


class ForgotPasswordForm(FlaskForm):
    """Recovery step 1: identify the account by username."""

    username = StringField(
        "Username",
        validators=[DataRequired(), Length(min=3, max=80)],
    )
    submit = SubmitField("Continue")


class ResetPasswordForm(FlaskForm):
    """Recovery step 2: answer the security question, set a new password."""

    security_answer = StringField(
        "Your answer",
        validators=[DataRequired(), Length(min=1, max=255)],
    )
    new_password = PasswordField(
        "New password",
        validators=[
            DataRequired(),
            Length(min=PASSWORD_MIN, max=PASSWORD_MAX,
                   message=f"Password must be at least {PASSWORD_MIN} characters."),
        ],
    )
    new_password_confirm = PasswordField(
        "Confirm new password",
        validators=[
            DataRequired(),
            EqualTo("new_password", message="Passwords do not match."),
        ],
    )
    submit = SubmitField("Update password")
