# Technical Guide

A practical handbook for the **Dataset Labeling Platform** &mdash; a Flask
web application that lets a research team annotate images and export
them with pre-computed GLCM texture features, ready for any
machine-learning pipeline.

This guide is the **single source of truth** for anyone taking over the
project: it covers the architecture, the security model, every workflow,
the GLCM internals, the admin / user management, the bootstrap seed
script, day-to-day maintenance and common troubleshooting.

---

## Table of contents

1. [Introduction](#1-introduction)
2. [Quick installation](#2-quick-installation)
3. [Architecture overview](#3-architecture-overview)
4. [Authentication and access control](#4-authentication-and-access-control)
5. [The seed admin script (`create_admin.py`)](#5-the-seed-admin-script-create_adminpy)
6. [Annotation workflow (two steps)](#6-annotation-workflow-two-steps)
7. [Dataset browser](#7-dataset-browser)
8. [Analytics dashboard](#8-analytics-dashboard)
9. [Exports and GLCM texture features](#9-exports-and-glcm-texture-features)
10. [Theme system (Light / Dark)](#10-theme-system-light--dark)
11. [Maintenance](#11-maintenance)
12. [Testing](#12-testing)
13. [Troubleshooting](#13-troubleshooting)
14. [Extending the application](#14-extending-the-application)
15. [Appendix &mdash; file map](#15-appendix--file-map)

---

## 1. Introduction

### What it does

The application gives a research team **one place** to:

- **Sign in** with a username + password (Flask-Login, PBKDF2-SHA256
  hashed credentials, security-question password recovery).
- **Annotate** images for two parallel research projects in two steps:
  - **Fundus** &mdash; diabetic retinopathy fundus photographs (5
    severity grades).
  - **WasteSorting** &mdash; waste sorting photographs (3 material
    classes).
- **Browse** the dataset, search by filename, paginate, delete.
- **Export** the labeled subset of each project as CSV, JSON or HTML,
  with **GLCM texture features automatically computed** at export time.
- **Manage users** (admin role only): promote, demote, delete accounts.

### Who it is for

- Researchers labeling data for AI training.
- Supervisors who need to see what was annotated, by whom, when.
- Reviewers and jury members who want to inspect the pipeline.
- Maintainers and contributors who need to keep the project running.

### What is **not** included

- **No mailing / SMS** &mdash; password recovery is autonomous via a
  security question chosen at registration.
- **No automatic off-site backup** &mdash; manual backup of
  `database/dataset.db` and `data/images/` is the team's responsibility
  (see [Section 11](#11-maintenance)).
- **No multi-language UI** &mdash; the UI ships in English. Labels and
  free-form fields handle any UTF-8 content (incl. Thai, French
  accents).

---

## 2. Quick installation

### Prerequisites

- **Python 3.10** or newer
- **pip** (bundled with Python)
- A terminal (PowerShell on Windows, Terminal on macOS / Linux)
- *Optional:* `git`

### Step-by-step

#### 1. Get the project

```
git clone <repository-url>
cd ModifV1_0_1_Correction
```

#### 2. Create a virtual environment

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

#### 3. Install dependencies

```
pip install -r requirements.txt
```

The project depends on **11 packages**:

- **Flask, Flask-SQLAlchemy, Flask-WTF, Flask-Login, SQLAlchemy,
  Werkzeug** &mdash; the web framework, ORM, CSRF, sessions, password
  hashing.
- **python-dotenv** &mdash; loads `.env` at startup.
- **gunicorn** &mdash; production WSGI server on Linux.
- **waitress** &mdash; production WSGI server on Windows (used by
  `run_server.py`).
- **scikit-image, opencv-python** &mdash; GLCM texture features
  computed at export time.

#### 4. Create `.env`

```
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated string as `SECRET_KEY=` in `.env`. The app
**refuses to start** in production mode if `SECRET_KEY` is left at its
default value &mdash; this prevents accidentally deploying with a
publicly-known signing key.

For local development you can either set a real key or set
`FLASK_DEBUG=true` to bypass the guard.

#### 5. Seed the bootstrap admin (recommended)

```
.\.venv\Scripts\python create_admin.py     (Windows)
.venv/bin/python create_admin.py           (Linux / macOS)
```

See [Section 5](#5-the-seed-admin-script-create_adminpy) for what the
script does and how to customise it.

If you skip this step, the **first** user to register at `/register`
becomes admin automatically.

#### 6. Start the app

For development (auto-reload, listens on 127.0.0.1:5000):

```
python -m backend
```

For LAN production (binds 0.0.0.0:8080 via waitress, prints the LAN
URL):

```
python run_server.py
```

For Linux production (behind nginx / Caddy):

```
gunicorn "backend.app:app" -b 0.0.0.0:8000 -w 4
```

---

## 3. Architecture overview

### Layered diagram

```
+--------------------+        HTTP         +-----------------------+
|     Browser        | <-----------------> |   Flask Application   |
| (Tailwind CSS,     |                     |   (backend/app.py)    |
|  custom viewer,    |                     +-----------+-----------+
|  toasts, theme)    |                                 |
+--------------------+                                 |
                                                       v
  +----------------+   +------------------+   +-------------------+   +----------------+   +----------------+
  |  auth_bp       |   |  annotation_bp   |   |     export_bp     |   |  dashboard_bp  |   |    admin_bp    |
  |  (login,       |   |  (2-step         |   |  (CSV / JSON /    |   |  (per-project  |   |  (user mgmt:   |
  |   register,    |   |   upload+label,  |   |   HTML, GLCM      |   |   analytics:   |   |   promote/     |
  |   forgot,      |   |   dataset        |   |   computed here)  |   |   label counts |   |   demote/      |
  |   reset,       |   |   browser)       |   |                   |   |   + chart)     |   |   delete)      |
  |   logout)      |   |                  |   |                   |   |                |   |                |
  +-------+--------+   +--------+---------+   +---------+---------+   +-------+--------+   +-------+--------+
          |                     |                       |                     |                    |
          v                     v                       v                     v                    v
   +-------------+      +------------------+    +------------------+    +------------------+   +-------------+
   | forms.py    |      | image_service.py |    | export_service   |    | SQL group_by     |   | auth_utils  |
   | (WTForms)   |      | (validation,     |    | (GLCM, CSV,      |    |  on label +      |   | (decorators)|
   +-------------+      |  rename,         |    |  JSON, HTML)     |    |  Chart.js (front)|   +-------------+
                        |  folder routing) |    +---------+--------+    +------------------+
                        +--------+---------+              |
                                 |                        v
                                 v               data/exports/
                          data/images/<Label>/
                                 |
                                 v
                          database/dataset.db
                          (users + images)
```

### Folder layout

```
ModifV1_0_1_Correction/
├── backend/
│   ├── app.py                    Flask factory + error handlers + CLI commands
│   ├── __main__.py               python -m backend (dev entry point)
│   ├── config.py                 env-driven settings, project metadata, timezone
│   ├── forms.py                  WTForms classes (Login / Register / Forgot / Reset)
│   ├── auth_utils.py             @admin_required decorator
│   ├── routes/
│   │   ├── auth.py               Public auth routes (and POST /logout)
│   │   ├── annotation.py         2-step annotation + image serving + dataset browser
│   │   ├── dashboard.py          /dashboard/<dataset_type> analytics view
│   │   ├── export.py             /export and CSV / JSON / HTML downloads
│   │   └── admin.py              /admin/users + promote / demote / delete
│   ├── models/database.py        SQLAlchemy + User + ImageRecord
│   └── services/
│       ├── image_service.py      file validation, sequential naming, folder routing
│       └── export_service.py     GLCM extraction + CSV / JSON / HTML builders
│
├── frontend/
│   ├── templates/
│   │   ├── base.html             Shared layout (Tailwind, navbar, toasts, theme toggle)
│   │   ├── index.html            Home with stat cards (each project card links to its dashboard)
│   │   ├── annotation.html       2-mode form (upload then label)
│   │   ├── dashboard.html        Dataset browser (project tabs + search + pagination)
│   │   ├── analytics.html        Per-project analytics page (list + Chart.js doughnut)
│   │   ├── export.html           Export cards per project
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   ├── register.html
│   │   │   ├── forgot.html
│   │   │   └── reset.html
│   │   ├── admin/users.html      User management table
│   │   └── errors/               403, 404, 500
│   └── static/
│       ├── css/app.css           Minimal custom CSS on top of Tailwind
│       └── js/
│           ├── theme.js          Light / Dark toggle (localStorage)
│           ├── toasts.js         Auto-dismiss + close-button delegation
│           ├── annotation.js     Dropzone + custom image viewer (zoom/pan/rotate)
│           ├── dataset.js        Search + pagination + delete confirm
│           ├── dashboard.js      Chart.js doughnut + theme-aware re-render
│           ├── auth.js           Password-match live check + English validation
│           └── admin.js          Delete-user confirm dialog
│
├── database/
│   ├── schema.sql                Reference SQL (informational)
│   └── dataset.db                Runtime DB (gitignored)
│
├── data/
│   ├── images/                   Uploaded files grouped by <Label>/ subfolder
│   └── exports/                  Generated CSV / JSON / HTML
│
├── docs/
│   ├── architecture.md           High-level architecture (also references this guide)
│   ├── setup.md                  Alternative install walk-through
│   └── screenshots/              UI captures for the report
│
├── run_server.py                 LAN production launcher (waitress + auto-IP)
├── create_admin.py               One-shot bootstrap-admin seed script
├── requirements.txt              11 pinned dependencies
├── README.md                     Quick start + features
├── TECHNICAL_GUIDE.md            This file
├── .env.example                  Template for local secrets
└── .gitignore
```

### Request flow at a glance

| Endpoint                                        | Method   | Guard               | Purpose                                                     |
|-------------------------------------------------|----------|---------------------|-------------------------------------------------------------|
| `/login`, `/register`, `/forgot`, `/reset`      | GET+POST | public              | Auth pages                                                  |
| `/logout`                                       | POST     | `@login_required`   | POST-only, CSRF-protected logout                            |
| `/`                                             | GET      | `@login_required`   | Home with per-project counts                                |
| `/annotation`                                   | GET      | blueprint-wide      | Dual-mode: upload form OR labeling viewer if pending image  |
| `/annotation/upload`                            | POST     | blueprint-wide      | Stage 1: save the file in `_pending/`                       |
| `/annotation/<id>/label`                        | POST     | blueprint-wide      | Stage 2: move to `<Label>/`, mark labeled                   |
| `/annotation/<id>/delete`                       | POST     | blueprint-wide      | Drop the image                                              |
| `/images/<filename>`                            | GET      | blueprint-wide      | Serve a stored image (path-traversal safe)                  |
| `/dataset`                                      | GET      | blueprint-wide      | Redirect to `/dataset/Fundus`                               |
| `/dataset/<project_id>`                         | GET      | blueprint-wide      | Project-scoped browser with tabs                            |
| `/dashboard/<dataset_type>`                     | GET      | blueprint-wide      | Per-project analytics (label counts + doughnut chart)       |
| `/export`                                       | GET      | blueprint-wide      | Per-project export cards                                    |
| `/export/csv?project=<id>`                      | GET      | blueprint-wide      | 26-column CSV with `;` delimiter                            |
| `/export/json?project=<id>`                     | GET      | blueprint-wide      | Same 26 keys, flat JSON                                     |
| `/export/html?project=<id>`                     | GET      | blueprint-wide      | Self-contained HTML preview                                 |
| `/admin/users`                                  | GET      | `@admin_required`   | List of users                                               |
| `/admin/users/<id>/role`                        | POST     | `@admin_required`   | Promote / demote                                            |
| `/admin/users/<id>/delete`                      | POST     | `@admin_required`   | Remove account                                              |

> "Blueprint-wide" means the guard is applied via
> `@blueprint.before_request @login_required` (or `@admin_required` for
> `admin_bp`), so it can never be accidentally forgotten on a single
> endpoint.

### Five Flask blueprints, one shape

Every business area is a blueprint registered in `create_app()`. The
shape is identical from one file to the next, so each one stays small
and reads predictably:

- a module-level `Blueprint(...)` instance,
- a `@before_request @login_required` (or `@admin_required`) hook,
- route handlers, one per endpoint, with `try/except + rollback`
  around every `db.session.commit()`,
- private helpers prefixed with `_`.

| Blueprint        | File                                | Surface                                        |
|------------------|-------------------------------------|------------------------------------------------|
| `auth_bp`        | `backend/routes/auth.py`            | Public auth pages + POST `/logout`             |
| `annotation_bp`  | `backend/routes/annotation.py`      | 2-step annotation + image serving + browser    |
| `dashboard_bp`   | `backend/routes/dashboard.py`       | `/dashboard/<dataset_type>` analytics          |
| `export_bp`      | `backend/routes/export.py`          | Export page + CSV / JSON / HTML downloads      |
| `admin_bp`       | `backend/routes/admin.py`           | User management                                |

### Frontend layering

The frontend has zero build step. Tailwind CDN drives styling,
Chart.js CDN drives the analytics doughnut (loaded only on that page).
JavaScript is **strictly separated from templates**:

- `frontend/templates/` holds Jinja templates and **no JS logic**. The
  only inline script kept in `base.html` is the four-line theme
  bootstrap (it has to run before paint to avoid FOUC).
- `frontend/static/js/` holds one focused file per concern: `theme.js`,
  `toasts.js`, `main.js` (mobile nav), `annotation.js`, `dataset.js`,
  `dashboard.js`, `auth.js`, `admin.js`. Each file is an IIFE and
  bails out cleanly when its DOM hooks are absent, so the same script
  bundle can ship on every page.
- Data hand-offs from Flask to JS go through `data-*` attributes or
  through a typed-content tag (`<script id="..." type="application/json">{{ payload | tojson }}</script>`),
  never through string concatenation - XSS-safe by construction.

---

## 4. Authentication and access control

### Storage model

| Column                 | Type           | Notes                                                                 |
|------------------------|----------------|-----------------------------------------------------------------------|
| `id`                   | INTEGER PK     | Auto-increment                                                        |
| `username`             | VARCHAR(80)    | Unique, indexed, 3-80 chars, `[A-Za-z0-9_-]+`                         |
| `password_hash`        | VARCHAR(255)   | PBKDF2-SHA256 (`werkzeug.security.generate_password_hash`)            |
| `role`                 | VARCHAR(20)    | `"admin"` or `"annotator"`                                            |
| `security_question`    | VARCHAR(255)   | Free-form, chosen by the user at registration                         |
| `security_answer_hash` | VARCHAR(255)   | PBKDF2-SHA256 of the lowercased, stripped answer                      |
| `created_at`           | DATETIME       | UTC                                                                   |

### Forms (WTForms in `backend/forms.py`)

| Form                  | Validators                                                                                              |
|-----------------------|---------------------------------------------------------------------------------------------------------|
| `LoginForm`           | username 3-80, password 8-128                                                                           |
| `RegisterForm`        | username 3-80 + regex + unique, password 8-128 + confirm match, security_question 5-255, answer 1-255   |
| `ForgotPasswordForm`  | username 3-80                                                                                           |
| `ResetPasswordForm`   | security_answer 1-255, new_password 8-128 + confirm match                                               |

### Password & security-answer hashing

- Both passwords AND security answers are hashed with PBKDF2-SHA256 via
  `werkzeug.security.generate_password_hash(method="pbkdf2:sha256")`,
  which uses **1,000,000** iterations by default.
- Security answers are normalised (`.strip().lower()`) before hashing
  so users can answer "Whiskers", "whiskers " and "WHISKERS" with the
  same result.

### Forgot-password recovery (autonomous, no email)

Two steps:

1. **`POST /forgot`** &mdash; user submits their username. The server
   stores the username in the session under
   `RESET_SESSION_KEY = "reset_username"` and redirects to `/reset`.
2. **`POST /reset`** &mdash; the server displays the user's
   `security_question`. The user submits the answer + a new password.
   If the answer matches, the password is updated and the user is
   logged in. The session key is cleared.

If a username does not exist at step 1, the server still flashes the
generic "if that account exists" message and silently redirects, so
attackers cannot enumerate valid usernames through `/forgot`.

### Roles and protected routes

| Role         | Can do                                                                  |
|--------------|-------------------------------------------------------------------------|
| `annotator`  | Annotate, browse the dataset, export                                    |
| `admin`      | Everything an annotator can do, plus `/admin/users` (CRUD on accounts)  |

`@admin_required` (defined in `backend/auth_utils.py`) chains
`@login_required` then checks `current_user.is_admin`. Anonymous users
get a 302 to `/login`; logged-in non-admins get a 403.

### Per-row delete authorization

Image deletion is **role-aware**, enforced in
`backend/routes/annotation.py::delete_annotation`:

| Caller         | Can delete                                                       |
|----------------|------------------------------------------------------------------|
| Admin          | Any image (pending or labeled), any contributor.                 |
| Annotator      | Only images where `image.contributor == current_user.username`.  |

The check runs after `get_or_404` and short-circuits with `abort(403)`
when it fails. It covers both pending and labeled rows, so it also
subsumes the per-user pending guard from
[Section 6](#6-annotation-workflow-two-steps).

The Delete button in `dashboard.html` (the dataset browser) is also
hidden when the current user has no right to delete that row &mdash;
**this is UX defence only**. The real barrier is the 403 in
`delete_annotation`. A user who forges a `POST /annotation/<id>/delete`
on someone else's image without admin role still gets a 403.

### CLI commands

These run via the **venv** Python, e.g.:

```
.\.venv\Scripts\flask --app backend.app list-users
.\.venv\Scripts\flask --app backend.app promote-admin USERNAME
```

| Command              | What it does                                                                            |
|----------------------|-----------------------------------------------------------------------------------------|
| `list-users`         | Prints every user with their role and creation date                                     |
| `promote-admin USR`  | Sets `USR.role = "admin"`. Does nothing if the user does not exist                      |

> If the global `flask` command is on PATH but pointing at a different
> Python (no Flask installed), call it through the venv directly as
> shown above. The system Python error
> `ModuleNotFoundError: No module named 'dotenv'` always means the wrong
> interpreter is being used.

### Admin self-protection

The admin panel refuses to:

- demote an admin who would leave the system with **zero admins**,
- delete an admin who would leave the system with **zero admins**,
- delete the **currently signed-in account** from the panel (this is
  not an admin-level safety, it is a UX guard).

---

## 5. The seed admin script (`create_admin.py`)

A short standalone script at the project root that **creates or forces
a known admin account** into the database. It is not wired into the
running app: no route imports it, the factory does not call it.
Operators run it on purpose, typically once after a fresh install or
when they need a guaranteed recovery account.

### Behaviour

- If the seed username does **not** exist &mdash; the script creates the
  account with the seed password / question / answer and `role=admin`.
- If the seed username **does** exist &mdash; the script **overwrites**
  the password, security question, answer and forces the role back to
  `admin`. This doubles as an emergency password reset for that
  account.

The script prints a summary on success:

```
Updated existing admin account 'USERNAME'.
  Username : USERNAME
  Password : PASSWORD
  Role     : admin/annotator
  Question : QUESTION TO RECOVER PASSWORD
  Answer   : ANSWER TO QUESTION
```

### How to customise the seed credentials

Open `create_admin.py` and edit the four constants near the top:

```python
SEED_USERNAME = "USERNAME"
SEED_PASSWORD = "PASSWORD"
SEED_QUESTION = "QUESTION"
SEED_ANSWER = "ANSWER"
```

- `SEED_USERNAME` &mdash; 3-80 chars, `[A-Za-z0-9_-]+`. If a user
  already exists with this name, they will be promoted to admin and
  their credentials overwritten.
- `SEED_PASSWORD` &mdash; at least 8 characters.
- `SEED_QUESTION` &mdash; at least 5 characters; this is the question
  the user will see at `/forgot`.
- `SEED_ANSWER` &mdash; the answer is stored hashed; comparison is
  case- and whitespace-insensitive (so "Dog", "DOG", "  dog " all
  match).

Save the file. There is nothing else to do; the script reads the
constants on each run.

### How to launch the script

Always use the **virtual environment Python** so dotenv, SQLAlchemy and
the rest of the stack resolve correctly:

Windows:

```
.\.venv\Scripts\python create_admin.py
```

Linux / macOS:

```
.venv/bin/python create_admin.py
```

Do **not** call `python create_admin.py` from outside the venv: your
system Python probably lacks the dependencies and you will get
`ModuleNotFoundError: No module named 'dotenv'`.

### When to run it

- Right after a fresh install if you want to log in **immediately**
  with a known account, before anyone uses `/register`.
- After a DB wipe (you deleted `database/dataset.db`).
- To **reset** the bootstrap admin's credentials if they were changed
  and you forgot them. Re-running the script forces the constants back
  into the row.

### When NOT to run it

- On every startup. The script is intentionally manual, not part of any
  auto-bootstrap path, so it cannot silently overwrite a password a
  user changed through the UI.

### Safety to delete the script

`create_admin.py` is **not imported** by `backend/app.py`,
`run_server.py`, any blueprint or any template. Deleting the file does
not affect the running app. Keep it as a recovery aid or remove it if
you no longer need it.

---

## 6. Annotation workflow (two steps)

Stored filenames follow `<Label>/<Prefix>_NNN.<ext>`, for example
`Severity_0/Fundus_007.jpg` or `PET/Waste_042.jpg`. The counter is
project-wide and never collides because of the per-project prefix.

### Step 1 &mdash; upload only

`GET /annotation` shows the upload form (project selector + dropzone +
author + description). The **author** field is locked to
`current_user.username` and the server ignores any client-side
tampering with it.

`POST /annotation/upload`:

1. Validates `project ∈ PROJECT_IDS`.
2. Validates the description and the file presence.
3. Calls `persist_pending_image()`:
   - `secure_filename` on the original name,
   - extension check against the whitelist,
   - sequential filename via `next_sequence_number(project)` &mdash;
     scans existing rows for that project and returns `max + 1`,
   - saves to `data/images/_pending/<Prefix>_NNN.<ext>`,
   - returns a fresh `ImageRecord` with `status="unlabeled"`.
4. Commits the row inside try/except + rollback. If the commit fails,
   the file is removed from disk so we never leave an orphan.

### Per-user pending isolation

Pending images (`status="unlabeled"`) are **private to their
contributor**. `GET /annotation` filters the pending queue on
`contributor == current_user.username`, so two annotators working in
parallel never see each other's drafts.

The same rule is enforced on the mutating endpoints:
`POST /annotation/<id>/label` and `POST /annotation/<id>/delete` both
check the contributor on `unlabeled` rows and `abort(403)` if a user
tries to act on someone else's pending image (id-guessing defence).
Labeled rows stay in the shared dataset and follow the role-based
delete rule documented in [Section 4](#4-authentication-and-access-control).

### Step 2 &mdash; labeling viewer

`GET /annotation` (now there is an unlabeled image you own) renders
the labeling viewer instead of the upload form. The image lives in a
fixed 640-px-tall frame with `bg-black`. `annotation.js` layers four
CSS transforms on top:

- **Zoom** &mdash; mouse wheel (clamped to 0.1x &ndash; 10x).
- **Pan** &mdash; click-and-drag.
- **Rotate** &mdash; small buttons under the image (&plusmn; 90 deg).
- **Flip** &mdash; horizontal and vertical buttons.
- **Reset** &mdash; restores the initial view.

Keyboard:

- `1` to `9` &mdash; select the matching label card.
- `Enter` &mdash; submit when a label is selected.

When the viewer is rendered, the route also stamps
`image.last_viewed_at = datetime.utcnow()`. This stamp is what powers
the labeling-time metric on the analytics dashboard
([Section 8](#8-analytics-dashboard)).

`POST /annotation/<id>/label`:

1. Validates the label against `PROJECT_LABELS[image.project]`.
2. Calls `finalize_with_label()`:
   - `os.replace` the file from `_pending/` to `<Label>/`,
   - updates `image.label`, `image.status = "labeled"`,
   - rewrites `image.stored_filename` to the new relative path.
3. Computes `labeling_duration_seconds = now - last_viewed_at`,
   stamps `labeled_at`, resets `last_viewed_at`. Negative deltas
   (clock skew) leave the duration NULL so `AVG()` skips the row.
4. Commits.

---

## 7. Dataset browser

`/dataset` redirects to `/dataset/Fundus`. The page renders one tab per
project; the active tab is highlighted in blue.

`/dataset/<project_id>` queries only that project's labeled rows.

### Columns

| Column        | Source                                         |
|---------------|------------------------------------------------|
| Thumbnail     | `<img>` served by `GET /images/<stored>`       |
| Filename      | `stored_filename` + `original_filename` below  |
| Label         | Blue pill                                      |
| Description   | `notes`, 3-line clamp with full text on hover  |
| Author        | `contributor` (always equal to a `username`)   |
| Upload date   | `uploaded_at` rendered via the `local_time` filter (Thai UTC+7) |
| Actions       | Delete button (POST with CSRF + JS confirm)    |

### Client-side controls (in `dataset.js`)

- **Search** &mdash; filters rows by `data-filename` (case-insensitive
  match across stored + original names).
- **Page size** &mdash; 10 / 25 / 50 / 100 rows per page.
- **Prev / Next** with a "Page X / Y" label.
- **Delete confirm** &mdash; asks before submitting the delete form.

All filtering and pagination happen in the browser; the server returns
the entire labeled set for the active project.

---

## 8. Analytics dashboard

A live, per-project view of how the labels are distributed. The
dashboard answers the kind of questions that come up in every team
meeting: *"Are we balanced across the severity grades yet ?"*,
*"How many PET images do we have today ?"*, *"Which class are we
under-collecting?"*.

### Where to find it

The dashboard is **discovered from the home page**, not from the
navbar. The two project cards on `/` (Fundus images and WasteSorting
images) are now clickable links to `/dashboard/<dataset_type>`. Each
card lifts on hover and reveals a small "View dashboard &rarr;" hint
so users notice it is interactive. There is intentionally **no nav-bar
entry** &mdash; the dashboard is a *drill-down* from the headline
counts, not a separate top-level area, so the navbar stays focused on
the everyday workflow (Annotation, Dataset, Export, Admin).

### Backend (`backend/routes/dashboard.py`)

The blueprint exposes a single endpoint:

```
GET /dashboard/<dataset_type>
```

Same protection model as `annotation_bp` and `export_bp`: a
`@blueprint.before_request @login_required` guard rejects anonymous
visitors with a 302 to `/login?next=...`. An unknown `dataset_type`
(anything not in `PROJECT_IDS`) returns a 404 via `abort(404)` &mdash;
no flash, no redirect, just a clean error page.

The label counts are queried **directly in SQL** so the route, the
template and the JavaScript never hold a hardcoded label list:

```python
rows = (
    db.session.query(ImageRecord.label, func.count(ImageRecord.id))
    .filter(ImageRecord.project == dataset_type)
    .filter(ImageRecord.status == "labeled")
    .filter(ImageRecord.label.isnot(None))
    .group_by(ImageRecord.label)
    .order_by(ImageRecord.label.asc())
    .all()
)
```

What this gives you for free:

- New labels appear in the dashboard the moment they appear in the
  data &mdash; no template change needed.
- A label that nobody is using anymore disappears on its own.
- Only `status="labeled"` rows are counted, so pending uploads never
  skew the distribution.

The route hands the template a `label_counts` list (each item is
`{"label": ..., "count": ...}`) plus the precomputed `total`.

### Personal labeling-time metric

In addition to the (shared) label distribution, each dashboard shows
**your average labeling time on this project**. The query is scoped
to the current user, so Fundus and WasteSorting each have their own
number and one user's pace never bleeds into another's view:

```python
avg_seconds = (
    db.session.query(func.avg(ImageRecord.labeling_duration_seconds))
    .filter(ImageRecord.project == dataset_type)
    .filter(ImageRecord.status == "labeled")
    .filter(ImageRecord.contributor == current_user.username)
    .filter(ImageRecord.labeling_duration_seconds.isnot(None))
    .scalar()
)
```

`AVG()` skips NULL rows natively, so pre-feature labeled images (where
`labeling_duration_seconds` was never recorded) are silently ignored
instead of poisoning the mean. A user who has never annotated on this
project sees `None`, rendered as a dash with a "No timing data yet"
caption.

The duration itself is populated by `submit_label()` &mdash; see the
view-time stamp in [Section 6]

### Template (`frontend/templates/analytics.html`)

The page uses a 5-column Tailwind grid that collapses to a single
column on mobile:

- **Left (2/5 width)** &mdash; a typed list of every label with its
  raw count and its percentage of the total. Counts are
  server-rendered, so they always match the chart exactly &mdash; no
  risk of drift between two number sources.
- **Right (3/5 width)** &mdash; a `<canvas id="datasetChart">` that
  hosts the Chart.js doughnut.

The handover between Flask and JavaScript follows the **no-inline-JS**
rule used everywhere else in the project. Data lives in a
typed-content script tag:

```html
<script id="chart-data" type="application/json">{{ label_counts | tojson }}</script>
```

`tojson` is Jinja's safe filter for this: it produces escaped JSON
that cannot break out of the script tag, even if a label one day
contains characters like `</script>` or `<` &mdash; XSS-safe by
construction. The `<canvas>` also carries a `data-dataset-type`
attribute. Those two DOM nodes are the **only** things `dashboard.js`
reads.

If the project has zero labeled images yet, the template renders a
friendly empty-state card with a call-to-action toward `/annotation`
instead of an empty chart. In that case the Chart.js CDN is still
loaded (via `head_extra`) but `dashboard.js` is **not** included,
because the `#chart-data` tag is absent &mdash; nothing to render.

### Frontend (`frontend/static/js/dashboard.js`)

A small, dependency-free module that:

1. Parses the JSON payload from `#chart-data` inside a `try/catch`
   (defensive against a malformed payload &mdash; the chart simply
   does not render).
2. Picks colours from an **eight-colour soft palette** (blue,
   emerald, amber, red, violet, cyan, orange, pink &mdash; all `*-400`
   shades). The palette cycles if more labels than colours exist, but
   each project has at most five labels so that limit is theoretical.
3. **Mirrors** the chosen slice colours onto the legend dots in the
   left-hand list, so the colour key on each side stays in sync
   without duplicating logic in two files.
4. Renders a `doughnut` chart via Chart.js. Tooltip format:
   `Label: N images (PP.P%)`. Hover offset is enabled so the active
   slice pops out slightly.
5. Watches `<html>` for `class` changes via `MutationObserver`. When
   the user toggles Light / Dark in the navbar, the chart re-renders
   **in place** with theme-appropriate legend text, title text and
   slice borders &mdash; no full page reload.

Chart.js itself is loaded from `cdn.jsdelivr.net` in the
`{% block head_extra %}` of `analytics.html` only, so other pages
stay lean and the CDN script never costs them anything.

### Routing summary

| URL                                | Behaviour                                                              |
|------------------------------------|------------------------------------------------------------------------|
| Anonymous &rarr; any `/dashboard/*`| 302 to `/login?next=/dashboard/<dataset_type>`                         |
| Logged-in + valid `dataset_type`   | 200 with the analytics page                                            |
| Logged-in + unknown `dataset_type` | 404 (branded error page)                                               |
| Project has no labeled images yet  | 200 with the empty-state card (no chart rendered)                      |

### Common tweaks

| Want to...                              | Touch                                                       |
|-----------------------------------------|-------------------------------------------------------------|
| Add a third project                     | Already automatic &mdash; extend `PROJECT_IDS` (Section 11.3) |
| Switch from doughnut to pie or bar      | `type: "doughnut"` in `dashboard.js`                        |
| Use a different colour palette          | `PALETTE` array at the top of `dashboard.js`                |
| Include unlabeled rows in the count     | Drop the `status="labeled"` filter in `dashboard.py`        |
| Break down by author instead of label   | Group by `ImageRecord.contributor` in the SQL query         |
| Show two projects on one page           | Render two chart canvases + two JSON tags with distinct IDs |

---

## 9. Exports and GLCM texture features

### GLCM in plain language

When the application exports a dataset, it adds **24 numbers per image**
that describe the texture of the photograph &mdash; how rough, smooth,
or repetitive the pixel patterns are. These numbers come from a
classical computer-vision technique called the **GLCM**
(Gray-Level Co-occurrence Matrix).

> **Simple analogy.** Imagine counting how often a pixel of brightness
> `A` is right next to a pixel of brightness `B`. Do that systematically
> for every pair, and you get a table &mdash; the co-occurrence matrix.
> From that table you compute summary numbers like "the image has lots
> of strong contrast" or "neighbouring pixels look alike most of the
> time".

### Six properties &times; four directions

| Property         | Plain-English meaning                                              |
|------------------|--------------------------------------------------------------------|
| `contrast`       | How much brightness changes between neighbouring pixels            |
| `dissimilarity`  | A linear-scale cousin of contrast, less sensitive to outliers      |
| `homogeneity`    | How "smooth" or uniform the texture is                             |
| `energy`         | How orderly the pixel pattern is                                   |
| `correlation`    | How predictable a pixel is from its neighbour                      |
| `asm`            | Angular Second Moment &mdash; the square of energy                 |

Each property is computed at four directions (`0°, 45°, 90°, 135°`)
and a distance of one pixel. That gives **24 values per image**.

### The strict 26-column schema (CSV and JSON)

```
img_path,
con1,  con2,  con3,  con4,        # contrast      at 0°, 45°, 90°, 135°
dis1,  dis2,  dis3,  dis4,        # dissimilarity at 0°, 45°, 90°, 135°
hom1,  hom2,  hom3,  hom4,        # homogeneity   at 0°, 45°, 90°, 135°
ene1,  ene2,  ene3,  ene4,        # energy        at 0°, 45°, 90°, 135°
corr1, corr2, corr3, corr4,       # correlation   at 0°, 45°, 90°, 135°
asm1,  asm2,  asm3,  asm4,        # ASM           at 0°, 45°, 90°, 135°
label
```

### CSV

```
img_path;con1;con2;con3;con4;dis1;...;asm4;label
data/images/Severity_0/Fundus_001.jpg;0.0636;0.1307;0.0816;0.1265;0.0630;...;0.0607;Severity 0
```

- **Delimiter** &mdash; `;` (semicolon). Works directly in European
  Excel (FR / IT / ES) without a "Text to columns" wizard, and pandas
  reads it with `sep=";"`.
- **Encoding** &mdash; UTF-8 with BOM (`utf-8-sig`), so Excel detects
  the encoding correctly even on Windows locales.

### JSON

```json
[
  {
    "img_path": "data/images/Severity_0/Fundus_001.jpg",
    "con1": 0.0636, "con2": 0.1307, "con3": 0.0816, "con4": 0.1265,
    "...": "...",
    "asm4": 0.0607,
    "label": "Severity 0"
  }
]
```

Same 26 keys, in the same order. Numbers are JSON numbers (not
strings) so pandas / numpy / pytorch read them natively.

### Visual HTML export

A single self-contained `.html` file with one row per image: thumbnail
left, label badge right. Images are embedded as `data:image/...;base64`
URLs so no companion folder is needed. The file ships with its own
inline styles (independent of Tailwind) so it works offline.

### Fail-soft GLCM pipeline

Exports cannot 500. One corrupt file out of a thousand still has to
ship a valid 26-column row, or the researchers lose the whole batch.
The pipeline enforces this at two layers:

- `extract_glcm_features()` returns zero-filled features and **logs**
  the path when:
  - the file is missing,
  - OpenCV cannot read it (`cv2.error` / `OSError`),
  - OpenCV returns `None` (unknown format),
  - `graycomatrix` / `graycoprops` raise (constant image, bad shape).
- `_build_export_row()` wraps the GLCM call in a broad `try/except`,
  so even an unexpected failure on one image only zeros out **that**
  row &mdash; the rest of the export still completes. The exception is
  logged via `logger.exception`, with image id, for post-mortem.

Combined with the per-commit `try/except + db.session.rollback()` on
every business route, no end-user action can crash the server.

---

## 10. Theme system (Light / Dark)

### How it works

- `<html>` carries a `dark` class when dark mode is active.
- An inline `<script>` in `base.html` reads `localStorage["theme"]` and
  applies the class **before paint** to avoid FOUC.
- `tailwind.config = { darkMode: "class" }` &mdash; Tailwind picks up
  `dark:` utility variants based on the class.
- A toggle button in the navbar swaps the class and writes the new
  value to `localStorage`. Logic lives in `frontend/static/js/theme.js`.

### Adding new dark-aware styles

Use Tailwind utility pairs:

```html
<div class="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"> ... </div>
```

Accent colour: `blue-600` (`blue-500` hover, `blue-400` dark-mode text).

### Responsive design

The UI is mobile-first via Tailwind utilities. Mobile is the default;
breakpoints (`sm`, `md`, `lg`, `xl`) layer on the desktop experience.
The strategy boils down to four rules applied consistently:

1. **Navbar collapses below `md`.** The text links carry
   `hidden md:flex`, and a hamburger button (`md:hidden`) reveals a
   dropdown panel. Logic in `frontend/static/js/main.js` &mdash; auto-closes
   on viewport resize and on link tap. No JS in the template.
2. **Multi-column grids fold to one column.** Analytics
   (`grid-cols-1 lg:grid-cols-5`) and annotation
   (`grid-cols-1 lg:grid-cols-10`) both stack vertically on small
   screens with no extra markup.
3. **Tables get a horizontal scroll wrapper.** Every `<table>` lives
   inside a `<div class="overflow-x-auto">` so the table can scroll
   sideways without breaking the page width on mobile (which would
   otherwise overflow the navbar and the sticky elements).
4. **Image viewer goes touch-native.** The frame carries
   `h-[50vh] lg:h-[640px] touch-none`. The `touch-none`
   (CSS `touch-action: none`) cedes pinch/pan/double-tap to JS instead
   of the browser. `annotation.js` then drives pan and pinch-zoom via
   the Pointer Events API &mdash; one code path covers mouse, finger
   and stylus, with `setPointerCapture` keeping drags alive even when
   the finger drifts off the frame.

The annotation right-hand column also uses `flex flex-col` plus
`lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto`, so on short laptop
screens the labels scroll inside the panel instead of pushing the
Save / Cancel buttons off-screen. The action group is pinned to the
bottom via `mt-auto`.

---

## 11. Maintenance

### 11.1 Backing up the dataset

| What                | Where                       | How                                                                   |
|---------------------|-----------------------------|-----------------------------------------------------------------------|
| The database        | `database/dataset.db`       | Stop the app and copy; or use `sqlite3 dataset.db ".backup b.db"`     |
| The image files     | `data/images/`              | Copy the whole directory (it includes label sub-folders + `_pending/`)|
| Exports             | `data/exports/`             | Optional; they can be regenerated                                     |

A weekly cron job that zips both folders is usually enough.

### 11.2 Resetting the application

Stop the app first, then:

```
rm database/dataset.db
rm -rf data/images/*
rm -rf data/exports/*
```

(Leave the `.gitkeep` files if present.) On next startup, SQLAlchemy
re-creates the schema. Run `create_admin.py` again to seed an admin
account.

### 11.3 Adding or editing labels for a project

Open `backend/config.py` and edit the `PROJECT_LABELS` dict. Existing
labels in the DB are untouched; new annotations use the updated list.

To **add a third project**, also extend `PROJECT_IDS` and
`PROJECT_FILENAME_PREFIX`:

```python
PROJECT_TELEMED = "Telemed"
PROJECT_IDS = (PROJECT_FUNDUS, PROJECT_WASTE, PROJECT_TELEMED)
PROJECT_LABELS = {
    PROJECT_FUNDUS:  ["Severity 0", ..., "Severity 4"],
    PROJECT_WASTE:   ["PET", "Can", "Plastic"],
    PROJECT_TELEMED: ["Normal", "Suspicious", "Pathological"],
}
PROJECT_FILENAME_PREFIX = {
    PROJECT_FUNDUS: "Fundus",
    PROJECT_WASTE:  "Waste",
    PROJECT_TELEMED: "Telemed",
}
```

Restart. The upload form, dataset tabs, and export page all loop over
`PROJECT_IDS`, so the new project appears everywhere automatically.

### 11.4 Changing the upload size limit

```python
# backend/config.py
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
```

Edit and restart. The 413 error page is updated automatically.

### 11.5 Switching to PostgreSQL

```
DATABASE_URL=postgresql://user:password@host:5432/dataset_labeling
```

Then `pip install psycopg2-binary`. SQLAlchemy abstracts the dialect;
the model code is unchanged.

### 11.6 Promoting a user from CLI

If you locked yourself out of the admin panel and `create_admin.py`
seems heavy:

```
.\.venv\Scripts\flask --app backend.app list-users
.\.venv\Scripts\flask --app backend.app promote-admin <username>
```

If even the CLI fails, `create_admin.py` is the universal recovery
path: it always restores the seed admin to a known state.

### 11.7 Updating dependencies

```
pip install --upgrade -r requirements.txt
```

Then run the test (next section) to confirm nothing broke.

---

## 12. Testing

After any structural change, verify the basics still work from an
active virtual environment:

```python
from backend.app import app

client = app.test_client()
# Anonymous: protected routes bounce, public auth pages 200
for path in ["/", "/annotation", "/dataset", "/export", "/admin/users"]:
    r = client.get(path, follow_redirects=False)
    assert r.status_code == 302 and "/login" in r.headers["Location"], path
for path in ["/login", "/register", "/forgot"]:
    assert client.get(path).status_code == 200, path

# Schema sanity
import json
import re
# (assume USERNAME already exists via create_admin.py)
tok_html = client.get("/login").data.decode()
csrf_token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', tok_html).group(1)
client.post("/login", data={"csrf_token": csrf_token,
                             "username": "USERNAME", "password": "PASSWORD"})

data = client.get("/export/json?project=Fundus").json
# (If you have labeled Fundus images:)
# assert len(data[0]) == 26
# assert list(data[0])[0] == "img_path"
# assert list(data[0])[-1] == "label"
```

The `frontend/static/js/*.js` files should also return 200 (cache
disabled in DevTools, hard-refresh the page):

```
/static/js/theme.js  toasts.js  auth.js  annotation.js  dataset.js  dashboard.js  admin.js
```

---

## 13. Troubleshooting

| Symptom                                                                | Fix                                                                                                              |
|------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| `RuntimeError: Refusing to start with the default SecretKey`           | Generate a real `SECRET_KEY` in `.env`, or set `FLASK_DEBUG=true` for local dev                                  |
| `ModuleNotFoundError: No module named 'dotenv'` when running `flask`   | You are calling the system Python's `flask`; use `.venv\Scripts\flask` (Win) or `.venv/bin/flask` (Unix) instead |
| `413 Request Entity Too Large`                                         | Upload exceeded 16 MB. Use a smaller file or change `MAX_CONTENT_LENGTH` in `backend/config.py`                  |
| Excel opens the CSV in a single column                                 | Re-open via *Data &rarr; From Text/CSV* and pick `;` as the separator (or use a FR / IT / ES locale)             |
| Other PCs on the Wi-Fi cannot reach the LAN server                     | Windows Firewall: allow Python on Private networks; or `New-NetFirewallRule -LocalPort 8080 -Action Allow ...`  |
| GLCM features are all zeros for some rows                              | The image file is missing or unreadable on disk. Check the server logs and `data/images/<Label>/`               |
| "Please log in to continue" loop                                       | Session cookies are blocked or `SECRET_KEY` changed between restarts (invalidates old sessions). Re-log in       |
| Forgot the bootstrap admin password                                    | Re-run `create_admin.py` &mdash; it overwrites the password with the seed value                                  |
| Want a clean slate                                                     | Stop the app, delete `database/dataset.db`, wipe `data/images/*` and `data/exports/*`, restart                  |

---

## 14. Extending the application

- **More projects** &mdash; see Section 11.3. The UI loops over
  `PROJECT_IDS` so new projects need no template changes.
- **Email-based password recovery** &mdash; add a Flask-Mail integration
  in `backend/routes/auth.py`. Generate a signed token (via
  `itsdangerous`) instead of the session-based step.
- **Activity log / audit trail** &mdash; add a `LabelEvent` model with
  `user_id`, `image_id`, `action`, `timestamp`. Insert a row at every
  POST inside `annotation.py` / `admin.py`.
- **Image content validation** &mdash; after `file.save()` in
  `persist_pending_image()`, call `PIL.Image.open(target).verify()`. If
  it raises, delete the file and reject.
- **Multi-label per image** &mdash; replace `label` with a
  `image_labels` association table. Update the labeling UI to use
  checkboxes; update exports to emit a list.
- **Cloud storage** &mdash; replace `file.save()` with an S3 / GCS
  upload. Adjust `serve_image()` to either stream or return a presigned
  URL.

---

## 15. Appendix &mdash; file map

A one-line description of every Python and JavaScript file in the repo.

| File                                                | Responsibility                                                       |
|-----------------------------------------------------|----------------------------------------------------------------------|
| `backend/__init__.py`                               | Marks `backend` as a Python package                                  |
| `backend/__main__.py`                               | `python -m backend` entry point                                      |
| `backend/app.py`                                    | Flask factory, login manager, error handlers, CLI commands           |
| `backend/config.py`                                 | Env-driven settings, project metadata, timezone                      |
| `backend/forms.py`                                  | WTForms (Login / Register / Forgot / Reset)                          |
| `backend/auth_utils.py`                             | `@admin_required` decorator                                          |
| `backend/routes/auth.py`                            | Public auth endpoints + POST `/logout`                               |
| `backend/routes/annotation.py`                      | 2-step annotation + image serving + dataset browser                  |
| `backend/routes/dashboard.py`                       | Per-project analytics route (`/dashboard/<dataset_type>`)            |
| `backend/routes/export.py`                          | Export page + CSV / JSON / HTML downloads                            |
| `backend/routes/admin.py`                           | Admin user management                                                |
| `backend/models/database.py`                        | `db` (SQLAlchemy), `User`, `ImageRecord`                             |
| `backend/services/image_service.py`                 | Upload validation, sequential naming, label-folder routing           |
| `backend/services/export_service.py`                | GLCM extraction, CSV / JSON / HTML builders                          |
| `frontend/templates/base.html`                      | Shared layout (Tailwind, navbar, toasts, theme toggle)               |
| `frontend/templates/index.html`                     | Home page (project cards link to per-dataset dashboards)             |
| `frontend/templates/annotation.html`                | Two-mode annotation form                                             |
| `frontend/templates/dashboard.html`                 | Dataset browser (tabs + search + pagination)                         |
| `frontend/templates/analytics.html`                 | Per-project analytics page (list + doughnut chart)                   |
| `frontend/templates/export.html`                    | Export cards                                                         |
| `frontend/templates/auth/{login,register,forgot,reset}.html` | Auth pages                                                  |
| `frontend/templates/admin/users.html`               | Admin user-management table                                          |
| `frontend/templates/errors/{403,404,500}.html`      | Branded error pages                                                  |
| `frontend/static/css/app.css`                       | Minimal custom CSS (image viewer geometry, transitions)              |
| `frontend/static/js/theme.js`                       | Light / Dark toggle (localStorage)                                   |
| `frontend/static/js/toasts.js`                      | Auto-dismiss + close-button delegation                               |
| `frontend/static/js/auth.js`                        | Password-match live check + English validation messages              |
| `frontend/static/js/annotation.js`                  | Dropzone + custom image viewer (zoom/pan/rotate)                     |
| `frontend/static/js/dataset.js`                     | Search + pagination + delete confirm                                 |
| `frontend/static/js/dashboard.js`                   | Chart.js doughnut + theme-aware re-render (analytics page)           |
| `frontend/static/js/admin.js`                       | User-delete confirm dialog                                           |
| `database/schema.sql`                               | Reference SQL for `users` and `images`                               |
| `run_server.py`                                     | LAN production launcher (waitress + auto-IP)                         |
| `create_admin.py`                                   | One-shot seed script for the bootstrap admin account                 |
| `requirements.txt`                                  | 11 pinned dependencies                                               |
| `.env.example`                                      | Template for local secrets                                           |
| `.gitignore`                                        | Ignores caches, venv, DB, runtime data, `.env`                       |
