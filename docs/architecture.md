# Architecture

## Overview

The Dataset Labeling Tool is a Flask 3 web application designed to let researchers upload images, assign labels, browse the dataset, and export it as CSV or JSON for AI training.

It separates concerns into three layers:

1. **Backend** (Flask + SQLAlchemy) — routes, database model, services
2. **Frontend** (Jinja2 templates + Bootstrap 5 + vanilla JS) — pages and interactions
3. **Storage** (local filesystem) — `data/images/` for uploads, `data/exports/` for generated files

## High-level diagram

```
+------------------+       HTTP        +-----------------------+
|     Browser      | <---------------> |    Flask Application  |
| (Bootstrap 5 UI) |                   |    (backend/app.py)   |
+------------------+                   +-----------+-----------+
                                                   |
        +------------------------+-----------------+-----------------+
        |                        |                                   |
        v                        v                                   v
+----------------+      +------------------+              +---------------------+
| Upload Routes  |      |  Label Routes    |              |   Export Routes     |
| (upload.py)    |      |  (label.py)      |              |   (export.py)       |
+-------+--------+      +---------+--------+              +----------+----------+
        |                         |                                  |
        v                         v                                  v
+----------------------+   +----------------+              +----------------------+
| image_service.py     |   |   db (ORM)     |              |  export_service.py   |
| - persist_uploads    |   |   ImageRecord  |              |  - build_csv_export  |
| - delete_image_file  |   |                |              |  - build_json_export |
+----------+-----------+   +-------+--------+              +-----------+----------+
           |                       |                                   |
           v                       v                                   v
   data/images/             database/dataset.db                  data/exports/
```

## Folder layout

```
dataset-labeling-tool/
├── backend/
│   ├── app.py                   Flask entry point + factory + error handlers
│   ├── __main__.py              Allows `python -m backend`
│   ├── config.py                Config class (env-driven)
│   ├── routes/
│   │   ├── upload.py            GET /upload page, POST /upload, GET /images/<filename>
│   │   ├── label.py             GET /label, POST /label/<id>, GET /dataset, POST delete
│   │   └── export.py            GET /export page, GET /export/csv, GET /export/json
│   ├── models/
│   │   └── database.py          ImageRecord ORM model + db (SQLAlchemy)
│   └── services/
│       ├── image_service.py     File validation + persistence + safe deletion
│       └── export_service.py    CSV (BOM) + JSON builders, full and AI formats
│
├── frontend/
│   ├── templates/
│   │   ├── base.html            Shared layout (navbar, toasts, scripts)
│   │   ├── index.html           Home with summary + nav buttons
│   │   ├── upload.html          Upload form (file + contributor + notes)
│   │   ├── label.html           Labeling page (image + label buttons + shortcuts)
│   │   ├── dashboard.html       Dataset browser (table + filters)
│   │   ├── export.html          Export page (CSV / JSON, full / AI)
│   │   └── errors/
│   │       ├── 404.html
│   │       └── 500.html
│   └── static/
│       ├── css/app.css
│       ├── js/labeling.js       Keyboard shortcuts (1-9), label selection, submit
│       ├── js/upload.js         File picker text + English validation messages
│       ├── js/dataset.js        Delete confirmation
│       └── img/
│
├── database/
│   ├── schema.sql               Reference SQLite schema
│   └── dataset.db               Created on first run (gitignored)
│
├── data/
│   ├── images/                  Uploaded images (gitignored)
│   └── exports/                 Generated CSV / JSON (gitignored)
│
├── docs/
│   ├── architecture.md          This document
│   ├── setup.md                 Installation guide
│   └── screenshots/             UI captures
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Database schema

Single table: `images`.

| Column                    | Type         | Purpose                                                |
|---------------------------|--------------|--------------------------------------------------------|
| id                        | INTEGER PK   | Auto-increment primary key                             |
| original_filename         | VARCHAR(255) | Sanitized original filename                            |
| stored_filename           | VARCHAR(255) | Unique stored name: `YYYYMMDDHHMMSS_<uuid>.<ext>`      |
| contributor               | VARCHAR(100) | Optional uploader name                                 |
| notes                     | TEXT         | Optional free-form notes                               |
| label                     | VARCHAR(100) | Assigned label (NULL until labeled)                    |
| status                    | VARCHAR(20)  | `"unlabeled"` or `"labeled"`                           |
| uploaded_at               | DATETIME     | Set on insert                                          |
| labeled_at                | DATETIME     | Set when label is assigned                             |
| last_viewed_at            | DATETIME     | Reset on every label-page load (timing baseline)       |
| labeling_duration_seconds | FLOAT        | Time between display and confirmation                  |

See `database/schema.sql` for the canonical SQL definition.

## Request flow

### Upload (`POST /upload`)

1. The form sends `images[]` files plus optional `contributor` and `notes`.
2. CSRF token is validated by Flask-WTF.
3. `persist_uploaded_images()` validates each file extension, generates a unique stored name, writes it to `data/images/`, and creates an `ImageRecord` row with status `unlabeled`.
4. The user is redirected to `/label` (next image to label).

### Label (`POST /label/<image_id>`)

1. Form sends the selected `label` and CSRF token.
2. `last_viewed_at` is compared with `datetime.utcnow()` to compute `labeling_duration_seconds`.
3. `mark_as_labeled()` sets `label`, `status='labeled'`, and `labeled_at`.
4. User is redirected to the next unlabeled image, or to `/dataset` if none remain.

### Export (`GET /export/csv?format=full|ai` or `/export/json?format=full|ai`)

1. Query labeled images, ordered by `id`.
2. Build the file in `data/exports/` and return it as an attachment via `send_file`.
3. CSV uses UTF-8 with BOM (Excel-friendly). JSON uses UTF-8 without BOM (`indent=2`).

## Security

- **CSRF protection** on every POST form via Flask-WTF (`csrf.init_app(flask_app)`).
- **Path traversal blocked** by `send_from_directory` (uses `werkzeug.security.safe_join`).
- **Extension whitelist** on uploads: PNG, JPG, JPEG, BMP, GIF, TIF, TIFF, WEBP.
- **Stored filename collision avoidance** via `secure_filename` + timestamp + UUID.
- **Hard cap on upload size**: 16 MB per request (`MAX_CONTENT_LENGTH`).
- **Fail-fast on default secret**: app refuses to start in production if `SECRET_KEY` is the default.
- **No authentication is included.** Add a login layer (Flask-Login, reverse-proxy gateway) before exposing publicly.

## Tech stack rationale

| Choice              | Reason                                                              |
|---------------------|---------------------------------------------------------------------|
| Flask 3             | Minimal, well-documented, fits a small web app perfectly            |
| Flask-SQLAlchemy    | Standard ORM integration, easy schema evolution                     |
| Flask-WTF           | CSRF protection out of the box                                      |
| SQLite              | Zero-setup, single-file, sufficient for a research-scale dataset    |
| Bootstrap 5         | Clean default styling without writing custom CSS                    |
| Vanilla JavaScript  | No build step required, easy for reviewers to read                  |
| Chart.js (optional) | Could be added for analytics; not required by the spec              |

## Extension points

- **Authentication / user roles**: drop in Flask-Login and add a `users` table; gate routes with `@login_required`.
- **PostgreSQL**: change `DATABASE_URL` to `postgresql://...`. SQLAlchemy abstracts the dialect.
- **Cloud storage** (S3, GCS): replace `image_service.persist_uploaded_images` to upload to a bucket and store the public URL in `stored_filename`.
- **Multi-class / multi-label**: change `label` to a many-to-many relation with a `labels` table.
