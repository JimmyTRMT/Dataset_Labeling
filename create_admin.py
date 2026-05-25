"""Seed an admin account into the database.

Run ONCE, from the project root, with the venv Python:

    .venv\\Scripts\\python create_admin.py        (Windows)
    .venv/bin/python create_admin.py              (macOS / Linux)

Idempotent by intent: each run leaves the database in the same target
state (XXXX = admin with the seed credentials). If the user already
exists with different values, the script ENFORCES the seed - so you can
re-run it any time as a recovery path. It is NOT wired into the regular
startup; once you've run it once, you can leave it alone.
"""

from backend.app import app
from backend.models.database import ROLE_ADMIN, User, db


# Edit these constants if you ever need a different seed account.
SEED_USERNAME = "USERNAME HERE"
SEED_PASSWORD = "PASSWORD HERE"
SEED_QUESTION = "QUESTION HERE"
SEED_ANSWER = "RESPONSE HERE"


def main() -> int:
    with app.app_context():
        user = User.query.filter_by(username=SEED_USERNAME).first()
        created = user is None

        if created:
            user = User(
                username=SEED_USERNAME,
                role=ROLE_ADMIN,
                security_question=SEED_QUESTION,
            )
            db.session.add(user)
        else:
            # Existing user: force the role + question/answer/password
            # to the seed values so the script's outcome is predictable.
            user.role = ROLE_ADMIN
            user.security_question = SEED_QUESTION

        user.set_password(SEED_PASSWORD)
        user.set_security_answer(SEED_ANSWER)
        db.session.commit()

        verb = "Created" if created else "Updated existing"
        print(f"{verb} admin account '{SEED_USERNAME}'.")
        print(f"  Username : {SEED_USERNAME}")
        print(f"  Password : {SEED_PASSWORD}")
        print(f"  Role     : {ROLE_ADMIN}")
        print(f"  Question : {SEED_QUESTION}")
        print(f"  Answer   : {SEED_ANSWER}")
        print()
        print("Log in at /login. You can now delete this script if you do")
        print("not need to re-seed; the running app does NOT import it.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
