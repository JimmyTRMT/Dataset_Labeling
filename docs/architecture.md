# Architecture

## Overview

The **Dataset Labeling Platform** is a Flask 3 web application designed to let a small research team upload images, assign labels, browse the dataset, and export it as CSV / JSON / HTML with pre-computed GLCM texture features.

It separates concerns into three clear layers:

1. **Backend** (Flask + SQLAlchemy + scikit-image + OpenCV) — routes, ORM, services.
2. **Frontend** (Jinja2 templates + Tailwind CSS via CDN + vanilla JavaScript) — pages and interactions, including a custom mouse-driven image viewer.
3. **Storage** (local filesystem) — `data/images/` for uploads, `data/exports/` for generated files, `database/dataset.db` for metadata.

## High-level diagram

```
+------------------+         HTTP          +-----------------------+
|     Browser      | <-------------------> |    Flask Application  |
| (Tailwind CSS    |                       |    (backend/app.py)   |
|  custom viewer)  |                       +-----------+-----------+
+------------------+                                   |
                                                       |
        +------------------------+----------------------+------------------+
        |                        |                                         |
        v                        v                                         v
+----------------+        +------------------+                  +---------------------+
| Upload Routes  |        |  Label Routes    |                  |   Export Routes     |
| (upload.py)    |        |  (label.py)      |                  |   (export.py)       |
+-------+--------+        +---------+--------+                  +----------+----------+
        |                           |                                      |
        v                           v                                      v
+----------------------+   +------------------+                  +-----------------------+
| image_service.py     |   |   db (ORM)       |                  |  export_service.py    |
| - persist_uploads    |   |   ImageRecord    |                  |  - extract_glcm_      |
| - delete_image_file  |   |                  |                  |    features (skimage) |
+----------+-----------+   +-------+----------+                  |  - build_csv_export   |
           |                       |                             |  - build_json_export  |
           |                       |                             |  - build_html_export  |
           |                       |                             +-----------+-----------+
           v                       v                                         v
   data/images/             database/dataset.db                       data/exports/
```

## Folder layout

```
ModifV1_0_1_Correction/
├── backend/
│   ├── app.py                Flask factory, error handlers, home route, local_time filter
│   ├── __main__.py           python -m backend (dev entry point)
│   ├── config.py             env-driven settings, project IDs, label sets, timezone
│   ├── routes/
│   │   ├── upload.py         GET /upload, POST /upload, GET /images/<filename>
│   │   ├── label.py          GET /label, POST /label/<id>, POST /label/<id>/delete, GET /dataset
│   │   └── export.py         GET /export, GET /export/csv, GET /export/json, GET /export/html
│   ├── models/database.py    ImageRecord ORM + db (SQLAlchemy)
│   └── services/
│       ├── image_service.py  file validation, persistence, safe deletion
│       └── export_service.py CSV (BOM, ; delimiter) + JSON + HTML builders, GLCM extraction
│
├── frontend/
│   ├── templates/
│   │   ├── base.html         shared layout (Tailwind, navbar, flash toasts)
│   │   ├── index.html        home with stat cards + nav buttons
│   │   ├── upload.html       dropzone + project radio cards
│   │   ├── label.html        split-screen labeling (custom image viewer + label cards)
│   │   ├── dashboard.html    dataset browser table + project / status filters
│   │   ├── export.html       per-project download cards (CSV / JSON / HTML)
│   │   └── errors/           404.html, 500.html
│   └── static/
│       ├── css/app.css       minimal custom CSS on top of Tailwind utility classes
│       └── js/
│           ├── labeling.js   image viewer (zoom / pan / rotate / flip), label cards, shortcuts
│           ├── upload.js     dropzone + drag-and-drop + English validation
│           └── dataset.js    delete-confirmation dialog
│
├── database/
│   ├── schema.sql            reference SQL schema (informational)
│   └── dataset.db            runtime DB, gitignored
│
├── data/
│   ├── images/               uploaded files, gitignored
│   └── exports/              generated CSV / JSON / HTML, gitignored
│
├── docs/
│   ├── architecture.md       this document
│   ├── setup.md              install + run guide
│   └── screenshots/          UI captures for the report
│
├── run_server.py             LAN production launcher (waitress + auto-IP banner)
├── requirements.txt          10 pinned dependencies
├── README.md                 quick start + features
├── TECHNICAL_GUIDE.md        full handbook
├── .env.example, .env, .gitignore
```

## Database schema

Single table: `images`.

| Column                      | Type           | Purpose                                                  |
|-----------------------------|----------------|----------------------------------------------------------|
| `id`                        | INTEGER PK     | Auto-increment                                           |
| `original_filename`         | VARCHAR(255)   | Sanitized filename from the upload                       |
| `stored_filename`           | VARCHAR(255)   | Unique stored name: `YYYYMMDDHHMMSS_<8-hex>.<ext>`       |
| `project`                   | VARCHAR(50)    | `"DR"` or `"SmartBin"` — drives labels and export bucket |
| `contributor`               | VARCHAR(100)   | Optional uploader name                                   |
| `notes`                     | TEXT           | Optional free-form notes                                 |
| `label`                     | VARCHAR(100)   | Assigned label (NULL until labeled)                      |
| `status`                    | VARCHAR(20)    | `"unlabeled"` or `"labeled"`                             |
| `uploaded_at`               | DATETIME       | UTC, set on insert                                       |
| `labeled_at`                | DATETIME       | UTC, set when label is assigned                          |
| `last_viewed_at`            | DATETIME       | UTC, reset on every label-page load (timing baseline)    |
| `labeling_duration_seconds` | FLOAT          | Time between display and confirmation                    |

See [`database/schema.sql`](../database/schema.sql) for the canonical SQL.

## Request flow

### Upload (`POST /upload`)

1. CSRF token is validated by Flask-WTF.
2. `MAX_CONTENT_LENGTH` (16 MB) gate; 413 response on overflow.
3. The `project` form value is validated against `PROJECT_IDS`; an invalid value redirects with a flash.
4. `persist_uploaded_images()` filters each file by extension, sanitises the name, writes it to `data/images/<timestamp>_<uuid>.<ext>`, and creates an `ImageRecord` row.
5. The transaction is committed inside a try/except — any DB error rolls back and flashes a clear message.
6. Redirect to `/label` to start labeling.

### Label (`POST /label/<image_id>`)

1. CSRF validated; `label` is read from form or JSON.
2. `last_viewed_at` is compared with `datetime.utcnow()` to compute `labeling_duration_seconds`.
3. `mark_as_labeled()` sets `label`, `status='labeled'`, `labeled_at`. Wrapped in try/except + rollback.
4. The next unlabeled image **in the same project** is selected (falls back to any project if the current one is finished). Skip uses the same logic with wrap-around.
5. Redirect to `/label?image_id=<next>` or to `/dataset` when nothing remains.

### Export (`GET /export/{csv|json|html}?project=DR|SmartBin`)

1. `_resolve_project()` validates the query string against `PROJECT_IDS`.
2. Labeled images of that project are fetched, ordered by id.
3. For CSV and JSON, `extract_glcm_features()` reads each image with OpenCV, converts to grayscale, calls `skimage.feature.graycomatrix` (distance=1, angles=[0, π/4, π/2, 3π/4]), and extracts 6 properties × 4 directions = 24 columns.
4. The writer produces the strict 26-column schema:
   - `img_path`, 24 GLCM columns (`con1..corr4, asm1..asm4`), `label`.
   - CSV uses `csv.writer(..., delimiter=";")` and UTF-8 with BOM.
   - JSON keeps the same flat keys, indented for readability.
5. For HTML: each image is encoded as a base64 data URL inside a single self-contained file (2-column table: image \| label).
6. The file is written to `data/exports/export_<project>_<timestamp>.<ext>` and returned via `send_file(as_attachment=True)`. Disk failures are caught and surfaced as a flash + redirect.

## Security

- **CSRF protection** on every POST form via Flask-WTF (`csrf.init_app(flask_app)`).
- **Path traversal blocked** by `send_from_directory` (uses Werkzeug `safe_join`).
- **Extension whitelist** on uploads: PNG, JPG, JPEG, BMP, GIF, TIF, TIFF, WEBP.
- **Stored filename collision avoidance** via `secure_filename` + UTC timestamp + 8-hex UUID.
- **Hard cap on upload size** (16 MB per request), with a friendly 413 handler.
- **Robust error handling** — try/except + rollback around every DB commit; GLCM extraction degrades to zero-filled features on missing/corrupt files.
- **Fail-fast on default secret** — the app refuses to start in production mode if `SECRET_KEY` is the default.
- **No authentication is included.** Add a login layer (Flask-Login or reverse-proxy gateway) before exposing publicly.

## Tech-stack rationale

| Choice                 | Reason                                                                   |
|------------------------|--------------------------------------------------------------------------|
| Flask 3                | Minimal, well-documented, fits a small web app perfectly                 |
| Flask-SQLAlchemy       | Standard ORM integration, easy schema evolution                          |
| Flask-WTF              | One-line CSRF protection                                                 |
| SQLite                 | Zero-setup, single file, sufficient for research-scale datasets          |
| Tailwind CSS (CDN)     | Clean dark-clinical theme with utility classes, no build step            |
| Custom image viewer    | CSS transforms — no third-party library, exactly one `<img>` in the DOM  |
| Vanilla JavaScript     | No bundler, easy for reviewers to read                                   |
| scikit-image + OpenCV  | Industry-standard GLCM and grayscale conversion                          |
| waitress               | Pure-Python WSGI server that runs cleanly on Windows                     |

## Extension points

- **Authentication / user roles** — add a `users` table, gate routes with `@login_required`, drive `contributor` from `current_user.username`.
- **PostgreSQL** — set `DATABASE_URL=postgresql://...` and `pip install psycopg2-binary`. SQLAlchemy abstracts the dialect.
- **Cloud storage** (S3, GCS) — replace `image_service.persist_uploaded_images` with a bucket upload; store the object key or signed URL in `stored_filename`.
- **More projects** — append to `PROJECT_IDS` and `PROJECT_LABELS` in `backend/config.py`; the UI loops over them automatically.
- **Additional features** — extend `EXPORT_COLUMNS` and the GLCM extractor in `export_service.py`; consumers using the flat schema pick up the new columns transparently.
