"""WTForms classes used by the auth blueprint.

Kept in one module because the four forms share validators and live close
to each other in the request lifecycle (login, register, forgot, reset).
"""

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError

from backend.models.database import User


# Username rule: 3-80 characters, letters / digits / underscore / dash
# only. Keeps URLs and filenames predictable, avoids whitespace bugs.
USERNAME_PATTERN = r"^[A-Za-z0-9_\-]+$"
USERNAME_PATTERN_MESSAGE = "Username may contain letters, digits, underscore or dash only."

PASSWORD_MIN = 8
PASSWORD_MAX = 128


# Reusable validator that fails if the username is already taken.
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
    """Step 1 of password recovery: identify the account by username."""
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(min=3, max=80)],
    )
    submit = SubmitField("Continue")


class ResetPasswordForm(FlaskForm):
    """Step 2 of password recovery: prove identity via security answer
    and set a new password."""
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
