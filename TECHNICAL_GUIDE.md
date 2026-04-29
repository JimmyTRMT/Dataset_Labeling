# Technical Guide

A full technical reference for the **Dataset Labeling Tool** — a Flask web application that lets researchers upload images, assign labels, browse the dataset, and export it for AI training.

This document is written for engineers, reviewers, and contributors who need to understand the system in depth: how it boots, how requests flow, where data lives, and how to extend it.

---

## Table of contents

1. [Overview](#1-overview)
2. [Tech stack](#2-tech-stack)
3. [Project layout](#3-project-layout)
4. [Configuration](#4-configuration)
5. [Application bootstrap](#5-application-bootstrap)
6. [Database schema and ORM](#6-database-schema-and-orm)
7. [Routes and endpoints](#7-routes-and-endpoints)
8. [Services layer](#8-services-layer)
9. [Frontend templates](#9-frontend-templates)
10. [Static assets and JavaScript](#10-static-assets-and-javascript)
11. [Security model](#11-security-model)
12. [Request lifecycle](#12-request-lifecycle)
13. [Export formats](#13-export-formats)
14. [Running the application](#14-running-the-application)
15. [Smoke testing](#15-smoke-testing)
16. [Troubleshooting](#16-troubleshooting)
17. [Extending the application](#17-extending-the-application)
18. [File reference](#18-file-reference)

---

## 1. Overview

The system has four user-facing capabilities:

1. **Upload** images (single or batch) with an optional contributor name and notes.
2. **Label** each image by clicking a label button or pressing its number key (`1`–`9`).
3. **Browse** the dataset with filename, contributor, label, and upload date; filter by All / Labeled / Unlabeled.
4. **Export** the labeled dataset as CSV or JSON in two layouts:
   - *Full* metadata — all DB columns, useful for audit and traceability.
   - *AI-ready* — two columns (`image_path`, `label`), drops straight into PyTorch / Keras / pandas pipelines.

It is **research-grade software**: minimal scope, clean structure, no authentication. A login layer must be added before exposing it on the public internet.

### Design goals

| Goal                         | How it is met                                                |
|------------------------------|--------------------------------------------------------------|
| Beginner-friendly layout     | Three-tier separation: `backend/` · `frontend/` · `data/`    |
| Predictable behavior         | Absolute paths anchored to project root, fail-fast config    |
| Safe defaults                | CSRF on, path traversal blocked, extension whitelist         |
| Easy to swap label sets      | `AVAILABLE_LABELS` env variable, no code change required     |
| Easy to swap database        | SQLAlchemy URL, SQLite default, PostgreSQL one env away      |
| Easy to read for reviewers   | Vanilla JS, no build step, small files, pointed comments     |

---

## 2. Tech stack

| Layer    | Technology              | Version    | Reason                                     |
|----------|-------------------------|------------|--------------------------------------------|
| Backend  | Flask                   | 3.1        | Mature, minimal, well documented           |
| ORM      | Flask-SQLAlchemy        | 3.1        | Standard Flask-SQLAlchemy integration      |
| CSRF     | Flask-WTF               | 1.2        | One-line CSRF protection on every form     |
| SQL      | SQLAlchemy              | 2.0        | Pulled in transitively, used directly too  |
| WSGI     | Werkzeug                | 3.1        | Flask's request/response engine            |
| Env      | python-dotenv           | 1.2        | Loads `.env` before Config evaluates       |
| WSGI prod| gunicorn                | 21         | Recommended for production deployment      |
| DB       | SQLite                  | bundled    | Zero-setup, single file                    |
| UI       | Bootstrap               | 5.3 (CDN)  | Clean defaults, no build step              |
| Charts   | Chart.js                | (optional) | Available via CDN if metrics are added     |
| Python   | CPython                 | 3.10+      | `str \| None` syntax, modern type hints    |

The entire dependency graph fits in **7 lines** of `requirements.txt`.

---

## 3. Project layout

```
ModifV1_0_1_Correction/
├── backend/                      Server-side Python code
│   ├── __init__.py               Marks the package
│   ├── __main__.py               Allows `python -m backend`
│   ├── app.py                    Flask factory + entry point + error handlers
│   ├── config.py                 Config class, env-driven, anchors all paths
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── upload.py             /upload (page + POST), /images/<filename>
│   │   ├── label.py              /label, /label/<id> (POST + delete), /dataset
│   │   └── export.py             /export, /export/csv, /export/json
│   ├── models/
│   │   ├── __init__.py
│   │   └── database.py           ImageRecord ORM + db (SQLAlchemy)
│   └── services/
│       ├── __init__.py
│       ├── image_service.py      File validation, persistence, deletion
│       └── export_service.py     CSV + JSON builders, full + AI formats
│
├── frontend/                     Client-side assets
│   ├── templates/
│   │   ├── base.html             Shared layout (navbar, toasts, scripts)
│   │   ├── index.html            Home: summary + 3 nav buttons
│   │   ├── upload.html           Upload form
│   │   ├── label.html            Labeling page (image + buttons + shortcuts)
│   │   ├── dashboard.html        Dataset browser (table + filters)
│   │   ├── export.html           Export page (CSV / JSON, full / AI)
│   │   └── errors/
│   │       ├── 404.html
│   │       └── 500.html
│   └── static/
│       ├── css/app.css           Custom styles on top of Bootstrap
│       ├── js/labeling.js        Label selection, keyboard 1-9, submit
│       ├── js/upload.js          File picker text, English validation
│       ├── js/dataset.js         Delete confirmation
│       └── img/                  Logos, icons
│
├── database/
│   ├── schema.sql                Reference SQL schema (informational)
│   └── dataset.db                Created at runtime (gitignored)
│
├── data/
│   ├── images/                   Uploaded files (gitignored)
│   │   └── .gitkeep
│   └── exports/                  Generated CSV / JSON (gitignored)
│       └── .gitkeep
│
├── docs/
│   ├── architecture.md           Architecture overview with diagram
│   ├── setup.md                  Step-by-step setup guide
│   └── screenshots/              UI captures for the report
│
├── requirements.txt              Pinned dependencies (7 packages)
├── README.md                     Quick start + features
├── TECHNICAL_GUIDE.md            This file
├── .env.example                  Template for local secrets
├── .env                          Local secrets (gitignored)
└── .gitignore
```

### Why this layout?

- `backend/` and `frontend/` cleanly separate server code from browser code. A reviewer can audit each side in isolation.
- `database/` holds *both* the SQL reference and the runtime DB file. Reviewers can read `schema.sql` without running anything.
- `data/` contains *only* user-generated content. It is gitignored and safe to wipe.
- `docs/` holds long-form documentation. README and TECHNICAL_GUIDE stay at the root for visibility.

---

## 4. Configuration

All configuration lives in [`backend/config.py`](backend/config.py) as a single `Config` class. The class is consumed via `flask_app.config.from_object(Config)`.

### Environment variables

Both `UPPER_SNAKE_CASE` and `CamelCase` names are accepted, so deployments can use either convention. The first matching name wins.

| Variable             | Default                              | Notes                                    |
|----------------------|--------------------------------------|------------------------------------------|
| `SECRET_KEY`         | `dev-change-me-secret`               | **Mandatory in production** (see below)  |
| `DATABASE_URL`       | `sqlite:///<root>/database/dataset.db` | Any SQLAlchemy URL                     |
| `UPLOAD_FOLDER`      | `<root>/data/images`                 | Where uploads are stored                 |
| `EXPORT_FOLDER`      | `<root>/data/exports`                | Where exports are written                |
| `AVAILABLE_LABELS`   | `No DR,Mild,Moderate,Severe`         | Comma-separated list of label options    |
| `FLASK_DEBUG`        | `false`                              | `true` / `1` / `yes` / `on` to enable    |

### Path anchoring

Two helper functions normalize relative paths into absolute ones:

- `_anchor_sqlite_url()` converts `sqlite:///database/dataset.db` (relative) into `sqlite:///C:/.../database/dataset.db` (absolute). This is required because **Flask-SQLAlchemy resolves relative SQLite paths against `app.instance_path`, not the project root** — a foot-gun the helper neutralizes.
- `_anchor_folder()` converts `./data/images` into the absolute equivalent. Werkzeug's `send_file()` rejects relative paths with `TypeError`, so anchoring prevents 500 errors on `/export/csv`.

After anchoring, all three I/O paths (`UPLOAD_FOLDER`, `EXPORT_FOLDER`, `SQLALCHEMY_DATABASE_URI`) are guaranteed absolute regardless of what the user wrote in `.env`.

### Constants

```python
MAX_CONTENT_LENGTH = 16 * 1024 * 1024   # 16 MB upload cap
DEFAULT_LABELS = ["No DR", "Mild", "Moderate", "Severe"]
DEFAULT_SECRET_KEY = "dev-change-me-secret"
```

`MAX_CONTENT_LENGTH` is hardcoded; edit the file to change it.

---

## 5. Application bootstrap

Entry point: [`backend/app.py`](backend/app.py).

`load_dotenv()` is called **before** `Config` is imported, since `Config` reads `os.getenv()` at class-definition time. Reversing the order makes the `.env` file invisible to Config.

The `create_app()` factory does the following, in order:

1. Reads `Config.PROJECT_ROOT` (absolute path of the repo root).
2. Builds the Flask app with explicit `template_folder=frontend/templates` and `static_folder=frontend/static`. Without these overrides, Flask would look inside `backend/`.
3. Loads `Config` into `flask_app.config`.
4. Creates `data/images/`, `data/exports/`, and `database/` if they don't exist (`mkdir(exist_ok=True, parents=True)`).
5. Initializes SQLAlchemy and CSRFProtect against the app.
6. Calls `db.create_all()` inside an `app_context()` to create missing tables.
7. **Fail-fast guard**: in production mode (`FLASK_DEBUG=false`), refuses to start if `SECRET_KEY` is still the default value. This prevents a deployment with a publicly-known signing key.
8. Registers the three blueprints (`upload_bp`, `label_bp`, `export_bp`).
9. Registers the home route (`/`) and the 404/413/500 error handlers.

The module ends with `app = create_app()` so that `gunicorn backend.app:app` and `python -m backend` both work.

### Entry points

| Command                        | Effect                                       |
|--------------------------------|----------------------------------------------|
| `python -m backend`            | Runs the dev server via `__main__.py`        |
| `python -m backend.app`        | Same — calls `app.run()`                     |
| `gunicorn backend.app:app`     | Production WSGI server                       |

---

## 6. Database schema and ORM

A single table, defined in [`backend/models/database.py`](backend/models/database.py).

### `images` table

| Column                      | Type           | Nullable | Notes                                            |
|-----------------------------|----------------|----------|--------------------------------------------------|
| `id`                        | INTEGER PK     | no       | Auto-increment                                   |
| `original_filename`         | VARCHAR(255)   | no       | Output of `secure_filename()` on the upload      |
| `stored_filename`           | VARCHAR(255)   | no, UNIQUE | `YYYYMMDDHHMMSS_<8-hex>.<ext>`                 |
| `contributor`               | VARCHAR(100)   | yes      | Free-form name from the upload form              |
| `notes`                     | TEXT           | yes      | Free-form notes from the upload form             |
| `label`                     | VARCHAR(100)   | yes      | Set when status moves to `labeled`               |
| `status`                    | VARCHAR(20)    | no       | `"unlabeled"` (default) or `"labeled"`           |
| `uploaded_at`               | DATETIME       | no       | UTC, set on insert                               |
| `labeled_at`                | DATETIME       | yes      | UTC, set when label is assigned                  |
| `last_viewed_at`            | DATETIME       | yes      | UTC, reset on every label-page load              |
| `labeling_duration_seconds` | FLOAT          | yes      | `labeled_at - last_viewed_at` (annotation pace)  |

The canonical SQL definition lives in [`database/schema.sql`](database/schema.sql) for reviewers. The runtime database is created automatically by SQLAlchemy from the model definition — the SQL file is informational, not load-bearing.

### Helper methods on `ImageRecord`

```python
mark_as_labeled(label_value, duration_seconds=None)
    # Sets label, status='labeled', labeled_at, labeling_duration_seconds.
    # Clears last_viewed_at (so re-opening doesn't compute a fresh duration).

to_export_row() -> dict
    # Flat representation used by CSV and JSON exports.
    # Includes a derived `image_path` field of the form 'data/images/<stored_filename>'
    # so AI pipelines can call Image.open(row["image_path"]) directly.
```

### Why `last_viewed_at` is reset on every page load

Tab switching, refresh, and stepping away from the desk would all inflate `labeling_duration_seconds`. Resetting on each render gives a duration of "how long the image was actually in front of the user before they clicked", which is the metric we want.

---

## 7. Routes and endpoints

### `home` (in `backend/app.py`)

- `GET /` — renders `index.html`, passes `total_count`, `labeled_count`, `unlabeled_count`.

### `upload_bp` ([backend/routes/upload.py](backend/routes/upload.py))

- `GET /upload` — renders `upload.html`.
- `POST /upload` — accepts `images[]`, optional `contributor`, optional `notes`. Calls `persist_uploaded_images()`. Redirects to `/label` on success.
- `GET /images/<path:filename>` — serves a stored image file via `send_from_directory()`. Used by `<img src>` tags throughout the UI. **Path traversal is blocked** by Werkzeug's `safe_join()`.

### `label_bp` ([backend/routes/label.py](backend/routes/label.py))

- `GET /label` — renders `label.html`. Optional `?image_id=<id>` to jump to a specific image; otherwise the oldest unlabeled image is shown. Resets `last_viewed_at` on every load.
- `POST /label/<id>` — accepts `label` (form or JSON), records the assignment, redirects to the next unlabeled image or to `/dataset` if none remain.
- `POST /label/<id>/delete` — removes the file from disk and the row from the DB. Redirects to `/dataset`.
- `GET /dataset` — renders `dashboard.html`. Optional `?filter=all|labeled|unlabeled`. Lists images ordered by upload date (newest first).

### `export_bp` ([backend/routes/export.py](backend/routes/export.py))

- `GET /export` — renders `export.html` with summary counts.
- `GET /export/csv?format=full|ai` — generates the CSV via `build_csv_export()` and returns it as an attachment.
- `GET /export/json?format=full|ai` — generates the JSON via `build_json_export()` and returns it as an attachment.

Both export endpoints flash a warning and redirect to `/export` if there are no labeled images.

### Route summary table

| Method | Path                          | Endpoint name              |
|--------|-------------------------------|----------------------------|
| GET    | `/`                           | `home`                     |
| GET    | `/upload`                     | `upload.upload_page`       |
| POST   | `/upload`                     | `upload.upload_images`     |
| GET    | `/images/<filename>`          | `upload.serve_image`       |
| GET    | `/label`                      | `label.label_page`         |
| POST   | `/label/<id>`                 | `label.assign_label`       |
| POST   | `/label/<id>/delete`          | `label.delete_image`       |
| GET    | `/dataset`                    | `label.dataset_browser`    |
| GET    | `/export`                     | `export.export_page`       |
| GET    | `/export/csv`                 | `export.export_csv`        |
| GET    | `/export/json`                | `export.export_json`       |

---

## 8. Services layer

The blueprints stay thin. All business logic lives in `backend/services/`.

### `image_service.py`

```python
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "gif", "tif", "tiff", "webp"}

is_allowed_file(filename) -> bool
    # Lowercase extension match against the whitelist.

persist_uploaded_images(files, upload_folder, contributor=None, notes=None)
    -> tuple[list[ImageRecord], bool]
    # For each uploaded file:
    #   - Skip empty fields.
    #   - Reject non-whitelisted extensions (sets the second tuple element to True).
    #   - Sanitize the filename with secure_filename().
    #   - Build a unique stored name: YYYYMMDDHHMMSS_<8-hex>.<ext>.
    #   - Save the file to upload_folder.
    #   - Create an ImageRecord (not committed — caller commits).

delete_image_file(image, upload_folder) -> None
    # Best-effort deletion. Swallows OSError so the DB row can still be removed
    # even if the file is missing or locked.
```

The collision-resistant filename pattern (timestamp + random hex) guarantees uniqueness even when several users upload the same `cat.png` in the same second.

### `export_service.py`

```python
build_csv_export(images, export_folder, export_format="full") -> Path
    # Writes data/exports/dataset_<format>_<timestamp>.csv
    # Uses utf-8-sig (BOM) so Excel on Windows opens accented or non-Latin text correctly.
    # Format "full" -> all metadata columns.
    # Format "ai"   -> two columns (image_path, label).

build_json_export(images, export_folder, export_format="full") -> Path
    # Writes data/exports/dataset_<format>_<timestamp>.json
    # JSON arrays of dicts, indented for readability, ensure_ascii=False.
```

### Why CSV uses BOM and JSON does not

- **CSV with BOM**: Excel on Windows uses the BOM to detect UTF-8. Without it, accented or Thai characters render as `Ã©` or `???`.
- **JSON without BOM**: most JSON consumers (`json.load`, `pandas.read_json`, browsers) do not handle a BOM gracefully and raise on parse. UTF-8 is fine on its own here.

---

## 9. Frontend templates

All templates live in `frontend/templates/` and extend `base.html`.

### `base.html`

The shared layout. It renders:

- The HTML head with Bootstrap CSS and the custom `app.css`.
- A navbar with five entries (Home / Upload / Label / Dataset / Export). The `active` class is driven by `{% set active_page = '...' %}` in each child template.
- A toast container for flash messages (success / warning / secondary). The toasts auto-show via a small inline script.
- `{% block content %}` and `{% block scripts %}` for child templates.

### `index.html` (Home)

Two cards stacked vertically:

- A hero card with the three primary actions: *Upload Image*, *View Dataset*, *Export Data*.
- A summary card with three counts: Total / Labeled / Unlabeled. A *Continue Labeling* button shows up when there are unlabeled images.

### `upload.html`

A single form: file picker (multi-select), optional `contributor`, optional `notes`, submit button. The hidden `<input type="file">` is triggered by a styled "Choose File" button so the form looks consistent with Bootstrap.

### `label.html`

A two-column layout:

- **Left**: progress (X / Y images, percentage bar, counts) and shortcuts to Dataset / Export.
- **Right**: the current image, a row of label buttons (each with a `1`-`9` badge), Save / Skip / Delete buttons, and a thumbnail strip of pending images.

The Save button stays disabled until a label is selected — preventing empty submissions.

### `dashboard.html` (Dataset browser)

A table with five columns: Filename · Contributor · Label · Upload date · Actions. A filter toggle at the top switches between All / Labeled / Unlabeled (a query string is used so the URL is shareable). Each row offers a *Label* button (if unlabeled) and a *Delete* button (with JS confirmation).

### `export.html`

Two grouped sections: CSV exports (full / AI) and JSON exports (full / AI). All four buttons are disabled when `labeled_count == 0`.

### `errors/404.html` and `errors/500.html`

Small centered cards. Both extend `base.html` so the navbar stays consistent.

---

## 10. Static assets and JavaScript

All JS is **vanilla** — no build step, no bundler, no dependencies beyond Bootstrap.

### `frontend/static/css/app.css`

Five tiny rule blocks:
- `body` minimum height
- `.preview-image` for the labeling-page main image (max-height + `object-fit: contain`)
- `.thumb-image` for the pending-image thumbnails (4rem square + `object-fit: cover`)
- `.label-submit-pulse` for the click feedback shadow
- `.label-option-btn.selected` for the chosen label button styling

### `frontend/static/js/labeling.js`

Used on `/label`. Responsibilities:
- Track which label button is selected (`selected` class).
- Sync the chosen label into a hidden input.
- Enable the "Save Label" button once any label is selected.
- Listen for keyboard 1-9 to select labels (skipped when an input has focus, so typing in the contributor field doesn't trigger a label change).
- Listen for `Enter` to submit the form once a label is chosen.

### `frontend/static/js/upload.js`

Used on `/upload`. Responsibilities:
- Forward clicks on the styled "Choose File" button to the hidden `<input type="file">`.
- Update the read-only display next to the button: "No file selected" / "image.png" / "5 files selected".
- Override browser-native validation messages with English strings, regardless of browser locale ("Veuillez compléter ce champ" → "Please fill in this field").

### `frontend/static/js/dataset.js`

Used on `/dataset`. Single responsibility: confirm before deleting an image.

---

## 11. Security model

| Threat                      | Defense                                                          | Where                                  |
|-----------------------------|------------------------------------------------------------------|----------------------------------------|
| CSRF on state-changing POSTs | Flask-WTF `CSRFProtect` registers a global before-request hook   | `csrf.init_app(flask_app)` in app.py   |
| Path traversal via `/images/`| `send_from_directory()` uses `safe_join()` under the hood        | `upload.serve_image`                   |
| Unsafe filenames on disk     | `secure_filename()` strips path separators and exotic characters | `image_service.persist_uploaded_images`|
| Filename collisions          | Stored name = timestamp + 8-hex UUID prefix                       | same                                   |
| Wrong file types             | Extension whitelist (PNG/JPG/JPEG/BMP/GIF/TIF/TIFF/WEBP)          | `is_allowed_file`                      |
| Disk / RAM exhaustion        | `MAX_CONTENT_LENGTH = 16 MB`, 413 handler returns to /upload      | `Config`, `error_handlers`             |
| Default secret in production | `RuntimeError` at startup unless `SECRET_KEY` is overridden      | `create_app()` in app.py               |
| Leaking secrets              | `.env` is gitignored; only `.env.example` is tracked              | `.gitignore`                           |

### What is **not** included

- **Authentication** — there is no user / login system. This is documented in the README. Add Flask-Login or an upstream auth gateway before exposing publicly.
- **Authorization / roles** — the brief lists user roles (researcher / administrator) as *optional*; not implemented.
- **Rate limiting** — no protection against rapid-fire upload abuse. Add Flask-Limiter or rate-limit at the reverse proxy.
- **Image content validation** — we trust the file extension and Werkzeug's stream. We do not call `PIL.Image.open()` to verify the bytes are a real image. Add this if untrusted users can upload.

---

## 12. Request lifecycle

### Uploading images

```
Browser -- POST /upload (multipart, csrf_token) ----> Flask
  |                                                     |
  |                                              CSRFProtect validates token
  |                                                     |
  |                                              MAX_CONTENT_LENGTH check
  |                                                     |
  |                                              upload.upload_images()
  |                                                     |
  |                              persist_uploaded_images() iterates files:
  |                                                     |
  |                                  - is_allowed_file()? skip if not
  |                                  - secure_filename() + UUID stored name
  |                                  - file.save(target_path)
  |                                  - build ImageRecord
  |                                                     |
  |                                              db.session.commit()
  |                                                     |
  |  <-- 302 -- redirect to /label ----------------------|
```

### Labeling an image

```
GET /label?image_id=42
  -> SELECT all unlabeled images (order by uploaded_at)
  -> Pick image #42 (or first if not specified)
  -> UPDATE last_viewed_at = now() for the chosen image
  -> Render label.html with the image, label buttons, and pending thumbs

POST /label/42 with form { label: "Mild" }
  -> CSRF validated
  -> SELECT image #42
  -> duration = now() - last_viewed_at
  -> UPDATE image SET label='Mild', status='labeled', labeled_at=now(),
                      labeling_duration_seconds=duration, last_viewed_at=NULL
  -> Find the next unlabeled image
  -> 302 to /label?image_id=<next> (or /dataset if none left)
```

### Exporting CSV

```
GET /export/csv?format=ai
  -> SELECT all labeled images, ordered by id
  -> If empty: flash warning, redirect to /export
  -> build_csv_export()
       - Open data/exports/dataset_ai_<timestamp>.csv with utf-8-sig
       - Write header: image_path, label
       - For each image, write {image_path: "data/images/<stored>", label: <label>}
  -> send_file(absolute_path, as_attachment=True)
  -> Browser downloads dataset_ai_<timestamp>.csv
```

---

## 13. Export formats

### CSV — Full metadata

```
id,original_filename,stored_filename,image_path,contributor,notes,label,status,uploaded_at,labeled_at
1,cat.jpg,20260428093015_a1b2c3d4.jpg,data/images/20260428093015_a1b2c3d4.jpg,Alice,Sample,Mild,labeled,2026-04-28T09:30:15,2026-04-28T09:31:02
```

Use case: audit trail, data provenance, reproducibility.

### CSV — AI training

```
image_path,label
data/images/20260428093015_a1b2c3d4.jpg,Mild
data/images/20260428093017_b2c3d4e5.jpg,No DR
```

Use case: drop straight into a PyTorch `Dataset`, a Keras `image_dataset_from_directory`, or a pandas `read_csv` for a training notebook.

### JSON — Full metadata

```json
[
  {
    "id": 1,
    "original_filename": "cat.jpg",
    "stored_filename": "20260428093015_a1b2c3d4.jpg",
    "image_path": "data/images/20260428093015_a1b2c3d4.jpg",
    "contributor": "Alice",
    "notes": "Sample",
    "label": "Mild",
    "status": "labeled",
    "uploaded_at": "2026-04-28T09:30:15",
    "labeled_at": "2026-04-28T09:31:02"
  }
]
```

### JSON — AI training

```json
[
  {"image_path": "data/images/20260428093015_a1b2c3d4.jpg", "label": "Mild"},
  {"image_path": "data/images/20260428093017_b2c3d4e5.jpg", "label": "No DR"}
]
```

### Pandas integration

```python
import pandas as pd
from PIL import Image

dataframe = pd.read_csv("data/exports/dataset_ai_20260428_120000.csv")
first_image = Image.open(dataframe.loc[0, "image_path"])
```

The relative `data/images/` prefix means scripts run from the project root work without path juggling.

---

## 14. Running the application

### Local development

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows
# OR
source .venv/bin/activate         # Linux / macOS

pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
# Paste the result into SECRET_KEY in .env

python -m backend
```

Open http://127.0.0.1:5000.

### Production

```
gunicorn "backend.app:app" -b 0.0.0.0:8000 -w 4
```

Behind nginx or Caddy. Make sure `FLASK_DEBUG=false` (or unset) and `SECRET_KEY` is a real random value, otherwise the app refuses to start.

### Switching the label set

Set `AVAILABLE_LABELS` in `.env`:

```
# Diabetic retinopathy
AVAILABLE_LABELS=No DR,Mild,Moderate,Severe

# Waste sorting
AVAILABLE_LABELS=Plastic,Paper,Metal,Organic

# Telemedicine
AVAILABLE_LABELS=Normal,Suspicious,Pathological
```

Restart the app. No code change required.

### Switching to PostgreSQL

```
DATABASE_URL=postgresql://user:password@host:5432/dataset_labeling
```

Install `psycopg2-binary` (`pip install psycopg2-binary`). SQLAlchemy abstracts the dialect; the model code is unchanged.

---

## 15. Smoke testing

A quick end-to-end check after any structural change:

```bash
# 1. Boot
python -m backend          # Should print "Running on http://127.0.0.1:5000"

# 2. Probe routes (in a separate shell)
curl -s -o /dev/null -w "Home: %{http_code}\n"     http://127.0.0.1:5000/
curl -s -o /dev/null -w "Upload: %{http_code}\n"   http://127.0.0.1:5000/upload
curl -s -o /dev/null -w "Label: %{http_code}\n"    http://127.0.0.1:5000/label
curl -s -o /dev/null -w "Dataset: %{http_code}\n"  http://127.0.0.1:5000/dataset
curl -s -o /dev/null -w "Export: %{http_code}\n"   http://127.0.0.1:5000/export
curl -s -o /dev/null -w "404: %{http_code}\n"      http://127.0.0.1:5000/missing

# Expected: 200, 200, 200, 200, 200, 404
```

Or programmatically with the Flask test client:

```python
from backend.app import app

client = app.test_client()
for path in ["/", "/upload", "/label", "/dataset", "/export"]:
    response = client.get(path)
    print(path, response.status_code)
```

---

## 16. Troubleshooting

### `RuntimeError: Refusing to start with the default SecretKey while debug is disabled`

The `.env` does not set `SECRET_KEY`, or it is still `dev-change-me-secret`. Generate one:

```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the result as `SECRET_KEY=...` in `.env`. Or run with `FLASK_DEBUG=true` for local development.

### `sqlite3.OperationalError: unable to open database file`

The database path is being resolved against `app.instance_path` instead of the project root. The fix is already in `_anchor_sqlite_url()`, but if you bypassed it (e.g. by setting `SQLALCHEMY_DATABASE_URI` directly in code), use an absolute URL: `sqlite:///C:/full/path/to/dataset.db`.

### `500 Internal Server Error` on `/export/csv`

Werkzeug's `send_file()` rejects relative paths. If you set a custom `EXPORT_FOLDER`, make sure it is absolute, or trust `_anchor_folder()` to convert it.

### Images do not display, only filenames show

Same root cause as above — `UPLOAD_FOLDER` resolved to a path Werkzeug cannot serve from. Restart the app so the latest config takes effect.

### `413 Request Entity Too Large`

A batch exceeded 16 MB. Either upload smaller batches, compress the images, or raise `MAX_CONTENT_LENGTH` in `backend/config.py`.

### Excel shows everything in one column

Excel on French / Italian / Spanish locales uses `;` as the CSV separator by default. The export uses `,` (the ML / pandas standard). Either:
- Open the file with *Data → From Text/CSV* and pick Comma manually.
- Or change the locale in Excel options.

### Stale code after editing

Flask does not hot-reload unless `FLASK_DEBUG=true` is set. Stop and restart the server (Ctrl+C, then `python -m backend`).

### Two processes bound to port 5000

If `python -m backend` fails to bind, an old instance is still running. Find and kill it:

Windows:
```
netstat -ano | findstr :5000
taskkill /PID <pid> /F
```

Linux / macOS:
```
lsof -i :5000
kill <pid>
```

---

## 17. Extending the application

### Add user accounts

1. `pip install flask-login`
2. Create a `users` table with `id`, `username`, `password_hash`, `role`.
3. Wrap routes with `@login_required`. Wrap admin-only routes with a custom `@admin_required` decorator that checks the role.
4. Set `contributor` automatically from `current_user.username` instead of a free-form input.

### Add image content validation

In `persist_uploaded_images`, after `file.save(target_path)`:

```python
from PIL import Image
try:
    Image.open(target_path).verify()
except Exception:
    target_path.unlink(missing_ok=True)
    invalid_detected = True
    continue
```

### Add multi-label support

Replace the `label` column with a many-to-many relationship to a `labels` table. Update the labeling form to use checkboxes instead of radio buttons. Update exports to emit a list (CSV) or JSON array.

### Add cloud storage

Replace `file.save(target_path)` in `persist_uploaded_images()` with an upload to S3/GCS. Store the public URL or object key in `stored_filename`. Update `serve_image` to either redirect to a presigned URL or stream from the bucket.

### Add charts

Re-introduce Chart.js (it was in the original prototype). Add a `/dashboard` route that aggregates `label`, `labeled_at`, and `labeling_duration_seconds`, and renders a pie + bar chart.

---

## 18. File reference

A one-line description of every Python and JavaScript file in the repo.

| File                                          | Responsibility                                        |
|-----------------------------------------------|-------------------------------------------------------|
| `backend/__init__.py`                         | Marks `backend` as a Python package.                  |
| `backend/__main__.py`                         | Entry point for `python -m backend`.                  |
| `backend/app.py`                              | Flask factory, error handlers, home route.            |
| `backend/config.py`                           | `Config` class, env parsing, path anchoring.          |
| `backend/models/__init__.py`                  | Package marker.                                       |
| `backend/models/database.py`                  | `db` (SQLAlchemy) and `ImageRecord` model.            |
| `backend/services/__init__.py`                | Package marker.                                       |
| `backend/services/image_service.py`           | File validation, persistence, deletion.               |
| `backend/services/export_service.py`          | CSV and JSON builders (full and AI formats).          |
| `backend/routes/__init__.py`                  | Package marker.                                       |
| `backend/routes/upload.py`                    | Upload page + POST + image serving.                   |
| `backend/routes/label.py`                     | Labeling page + POST + dataset browser + delete.      |
| `backend/routes/export.py`                    | Export page + CSV download + JSON download.           |
| `frontend/templates/base.html`                | Shared layout (navbar, toasts, scripts).              |
| `frontend/templates/index.html`               | Home page.                                            |
| `frontend/templates/upload.html`              | Upload form.                                          |
| `frontend/templates/label.html`               | Labeling page.                                        |
| `frontend/templates/dashboard.html`           | Dataset browser table.                                |
| `frontend/templates/export.html`              | Export page.                                          |
| `frontend/templates/errors/404.html`          | 404 page.                                             |
| `frontend/templates/errors/500.html`          | 500 page.                                             |
| `frontend/static/css/app.css`                 | Custom styles on top of Bootstrap.                    |
| `frontend/static/js/labeling.js`              | Label selection, keyboard 1-9, submit.                |
| `frontend/static/js/upload.js`                | File picker text, English validation messages.        |
| `frontend/static/js/dataset.js`               | Delete confirmation.                                  |
| `database/schema.sql`                         | Reference SQL schema for reviewers.                   |
| `requirements.txt`                            | Pinned dependencies.                                  |
| `.env.example`                                | Template for local secrets.                           |
| `.gitignore`                                  | Ignores `__pycache__`, `.venv`, `data/*`, `database/*.db`, `.env`. |

---

## Appendix A — Quick reference card

```
Run dev server         python -m backend
Run prod server        gunicorn "backend.app:app" -b 0.0.0.0:8000 -w 4
Generate secret key    python -c "import secrets; print(secrets.token_urlsafe(48))"
Database file          database/dataset.db
Schema reference       database/schema.sql
Uploaded images        data/images/
Generated exports      data/exports/
Default labels         No DR, Mild, Moderate, Severe
Upload size cap        16 MB per request
Allowed extensions     PNG, JPG, JPEG, BMP, GIF, TIF, TIFF, WEBP
Keyboard shortcuts     1-9 select label, Enter submits
```

## Appendix B — Why some things are the way they are

**Why is `dashboard.html` the dataset browser, not a chart page?**
The original spec listed four templates and used the names interchangeably. The "Dataset Browser" mockup matched what would normally be called a dashboard. Sticking to the requested filename (`dashboard.html`) keeps the layout exactly as specified.

**Why store `original_filename` *and* `stored_filename`?**
- `original_filename` is what we show users (`cat.jpg`).
- `stored_filename` is what we save to disk (`20260428093015_a1b2c3d4.jpg`) to avoid collisions.

**Why UTF-8 with BOM for CSV but no BOM for JSON?**
Excel needs the BOM to detect UTF-8 in CSV files (otherwise accented characters break). JSON parsers reject BOMs, so the JSON export omits it.

**Why not commit `database/dataset.db`?**
The DB is regenerated from the model on first run. Committing it would mean every reviewer carries leftover test data, and any schema change would need a manual migration of the committed file. Letting SQLAlchemy build it fresh is simpler and reproducible.

**Why is there no migration tool (Alembic)?**
At this scope, `db.create_all()` plus a fresh DB on schema change is enough. Add Alembic when the schema starts evolving in production.
