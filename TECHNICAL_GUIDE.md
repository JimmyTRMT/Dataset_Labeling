# Technical Documentation: Image Labeling Platform

## Table of Contents

1. Architecture Overview
2. Database Schema
3. Data Workflow
4. Frontend Logic
5. Security & Portability
6. Deployment Considerations

## 1. Architecture Overview

### 1.1 Application Factory Pattern

`create_app()` in `app/__init__.py` builds and returns a configured Flask instance. This isolates initialization from import-time side effects, which is essential for testing and for deploying multiple variants of the app from the same code.

**Initialization sequence:**
1. Resolve project paths via `pathlib.Path` (cross-platform).
2. Load configuration from environment variables through the `Config` class.
3. Create `uploads/` and `exports/` directories if missing (idempotent).
4. Initialize SQLAlchemy ORM (`db.init_app`).
5. Initialize CSRF protection (`csrf.init_app`).
6. Run `db.create_all()` and `ensure_schema_compatibility()` to add any missing columns to legacy SQLite databases.
7. **Fail fast** if `FlaskDebug=false` and `SecretKey` is still the default placeholder. The app refuses to start, raising `RuntimeError`.
8. Register Blueprints (main, api) and error handlers (404, 413, 500).

### 1.2 Blueprint Architecture

- **main_bp** (`blueprints/main.py`):
  - GET `/` : Render the labeling interface.
  - GET `/history` : Render session list and upload form.
  - GET `/dashboard` : Render analytics.
  - GET `/uploads/<filename>` : Serve images via `send_from_directory` (path traversal safe).

- **api_bp** (`blueprints/api.py`, prefix `/api`):
  - POST `/upload` : Accept image batches, persist files, create records.
  - POST `/label/<id>` : Assign a label and record `labeling_duration_seconds`.
  - GET `/export` : Global CSV export.
  - GET `/export/session/<name>` : Per-session CSV export.
  - POST `/delete-session/<name>` : Drop session records and files.
  - POST `/delete-image/<id>` : Drop a single record and its file.

All POST routes require a CSRF token (Flask-WTF, hidden `csrf_token` input in every form).

### 1.3 Service Layer

- **image_service.py:**
  - `is_allowed_file()` : Extension whitelist check.
  - `persist_uploaded_images()` : Saves files with collision-resistant names (`{timestamp}_{uuid8}.{ext}`) and returns `ImageRecord` instances.

- **export_service.py:**
  - `build_export_csv()` : Writes a CSV with `utf-8-sig` encoding (Excel-friendly BOM, still parseable by `pandas.read_csv` without options).
  - Supports legacy format aliases (`complet`->`full`, `ia`->`ai`) for backward-compatible URLs.
  - `_sanitize_filename_part()` : Strips characters outside `[a-zA-Z0-9_-]` from filenames.

### 1.4 Utility Layer

`app/utils/labels.py` exposes `parse_custom_labels(raw)` which safely decodes the JSON-serialized `custom_labels` column, returning `[]` on missing/invalid input. Used by both `main.py` GET routes to avoid duplicated `try/except json.loads` blocks.

### 1.5 Frontend Separation

Templates handle structure and server-side rendering. Styling lives in `static/css/app.css`. Behavior lives in `static/js/{labeling,history,charts}.js`. Templates only include `<script src=...>` tags and JSON payloads; they never embed inline JS logic.

## 2. Database Schema

### 2.1 ImageRecord Model

| Field | Type | Constraints | Purpose |
|-------|------|-------------|---------|
| `id` | Integer | Primary Key | Unique identifier. |
| `original_filename` | String(255) | Not Null | User-facing filename (preserved for export). |
| `stored_filename` | String(255) | Unique, Not Null | Server filename: `{timestamp}_{uuid[:8]}.{ext}`. |
| `file_path` | String(500) | Not Null | Absolute disk path (used as primary deletion candidate). |
| `session_name` | String(255) | Default="Default Session" | Groups images by annotation batch. |
| `label_option_1` | String(100) | Default="labelOne" | First label of the session (legacy two-label compat). |
| `label_option_2` | String(100) | Default="labelTwo" | Second label of the session (legacy two-label compat). |
| `custom_labels` | Text | Nullable | JSON-encoded list of N labels for the session. |
| `uploaded_at` | DateTime | Default=utcnow, Not Null | Upload timestamp. |
| `labeled_at` | DateTime | Nullable | Label assignment timestamp. |
| `last_viewed_at` | DateTime | Nullable | Reset on every GET `/` so refresh/tab-switch don't inflate the timing. |
| `labeling_duration_seconds` | Float | Nullable | `labeled_at - last_viewed_at`. |
| `label` | String(100) | Nullable | Assigned label value. |
| `status` | String(20) | Default="unlabeled", Not Null | "unlabeled" or "labeled". |

### 2.2 Key Methods

- **`mark_as_labeled(label_value, duration_seconds)`** : Atomically sets `label`, `status="labeled"`, `labeled_at=utcnow()`, `labeling_duration_seconds`, and clears `last_viewed_at`.
- **`to_export_row()`** : Returns a dict shaped for the full CSV export.

### 2.3 Schema Evolution

`ensure_schema_compatibility()` introspects the SQLite `images` table on startup and runs `ALTER TABLE ADD COLUMN` for any missing field (`session_name`, `label_option_1`, `label_option_2`, `last_viewed_at`, `labeling_duration_seconds`, `custom_labels`). Skipped on non-SQLite engines because their ALTER syntax differs.

## 3. Data Workflow

### 3.1 Upload Flow

```
User submits multipart form
  -> POST /api/upload (CSRF-checked, 16 MB cap)
  -> persist_uploaded_images():
       - Validate extension against ALLOWED_EXTENSIONS
       - secure_filename() on original name
       - Generate unique stored name: {timestamp}_{uuid8}.{ext}
       - Save to UPLOAD_FOLDER
       - Build ImageRecord with status="unlabeled"
  -> Bulk insert + commit
  -> Flash success
  -> Redirect to labeling page (with session_name)
```

If the request body exceeds 16 MB, the global 413 handler intercepts and flashes a friendly warning instead of crashing.

### 3.2 Labeling Flow

```
User opens GET /
  -> last_viewed_at = utcnow() (reset every load)
  -> Render image + label buttons (badges 1-9 only)
User presses key 1..9 OR clicks a label button
  -> POST /api/label/<id>
  -> duration = utcnow() - last_viewed_at
  -> mark_as_labeled(label, duration)
  -> If auto_advance: redirect to next unlabeled image_id
  -> Else: stay on page, manual selection
```

Resetting `last_viewed_at` on every page load fixes the prior bug where a refresh after a long pause (lunch break, tab in background) inflated the recorded duration.

### 3.3 Export Flow

#### Full Dataset

Columns: `id, original_filename, stored_filename, session_name, label_option_1, label_option_2, custom_labels, uploaded_at, labeled_at, label, status`

Use case: full audit trail, retraining provenance, traceability.

#### AI Dataset

Columns: `image_path, label`

Sample row: `uploads/20260428023456_a1b2c3d4.png,labelTwo`

The `uploads/` prefix makes the CSV directly consumable by ML pipelines:

```python
import pandas as pd
from PIL import Image

df = pd.read_csv("export_global_ai_20260428_103045.csv")
img = Image.open(df.iloc[0]["image_path"])  # works as long as cwd is the project root
label = df.iloc[0]["label"]
```

#### Process

1. Query labeled images.
2. Call `build_export_csv(images, EXPORT_FOLDER, prefix, format)`.
3. Sanitize prefix (regex `[^a-zA-Z0-9_-]+` -> `_`).
4. Filename pattern: `{safe_prefix}_{format}_{YYYYMMDD_HHMMSS}.csv`.
5. Stream as attachment via `send_file`.

#### Encoding

`utf-8-sig` writes a BOM. Excel on Windows opens the file with correct character display (Thai, French accents, emojis). `pandas.read_csv()` automatically handles the BOM with no extra arguments.

## 4. Frontend Logic

### 4.1 Session-Aware URLs

```
/?session_name=Session+2026-04-28&auto_advance=1&image_id=42
```

- `session_name` : scopes queries.
- `auto_advance` : remembered in `localStorage`.
- `image_id` : forces a specific image (overrides auto-advance).

### 4.2 Keyboard Shortcuts

`labeling.js` listens to `keydown` events when the focused element is not an `INPUT/TEXTAREA/SELECT`. Keys `1`-`9` map to the first nine `.dynamic-label-btn` elements. Sessions with more than nine labels still work; labels 10+ simply show no shortcut badge.

### 4.3 Progress Bar Hydration

Server computes `progress_percent` and renders it as `data-progress`. JS reads the attribute and sets `style.width` and `aria-valuenow`. No client-side calculation, so the rendered HTML and the JS view are always in sync.

### 4.4 Dashboard Charts

`charts.js` reads JSON payloads embedded in the template via `<script type="application/json" id="...">`, then initializes Chart.js instances (pie + bar). No data is computed in JS, only visualized.

### 4.5 Localized UI Overrides

The native file input is hidden; a custom button + read-only text field show "No file selected" / "N files selected" in English, regardless of browser locale.

`history.js` calls `setCustomValidity()` on every `required` input so the browser's invalid messages stay in English even on French Windows. The override is reapplied to inputs created dynamically (Add label / Switch session).

## 5. Security & Portability

### 5.1 CSRF Protection

Flask-WTF's `CSRFProtect` is initialized on the app. Every form template includes:

```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

Cross-site POST attempts are rejected with HTTP 400 by default.

### 5.2 Environment-Based Configuration

```python
SECRET_KEY = os.getenv("SecretKey") or os.getenv("SECRET_KEY") or DEFAULT_SECRET_KEY
# Identical pattern for DatabaseUrl, UploadFolder, ExportFolder, FlaskDebug
```

If `FlaskDebug=false` and `SECRET_KEY == DEFAULT_SECRET_KEY`, `create_app()` raises `RuntimeError`. This prevents accidental production deployments with a forgeable session cookie.

### 5.3 Path Safety

- `serve_upload` uses `send_from_directory` which delegates to `werkzeug.security.safe_join`. Paths like `/uploads/../dataset.db` return 404.
- All filesystem code uses `pathlib.Path`, so paths render correctly on Windows and POSIX.
- `werkzeug.utils.secure_filename` is applied to every uploaded filename.

### 5.4 Upload Hardening

- Whitelist: `{png, jpg, jpeg, bmp, gif, tif, tiff, webp}`. SVG is intentionally excluded (XSS vector).
- `MAX_CONTENT_LENGTH = 16 MB`. Larger payloads are rejected before reaching disk.
- Stored filenames are server-generated UUIDs. Original filename is preserved separately.
- 413 handler converts the rejection into a flash message + redirect, not a stack trace.

### 5.5 Database Safety

All queries use SQLAlchemy ORM (`filter_by`, `get_or_404`). The only raw SQL (`text()`) is the schema migrator, which uses hardcoded DDL strings — no user input concatenation.

## 6. Deployment Considerations

### 6.1 WSGI Server

`gunicorn` is included in `requirements.txt`. Production launch:

```
gunicorn --workers 4 --bind 0.0.0.0:5000 "app:create_app()"
```

### 6.2 Database

SQLite is fine for local single-user use. For multi-user / cloud deployments, set `DatabaseUrl=postgresql://user:password@host:5432/labeling` (psycopg2 / psycopg installs would need to be added to `requirements.txt`).

### 6.3 Static & Uploads

- Put a reverse proxy (nginx, Caddy) in front of gunicorn.
- Serve `static/` directly from the proxy.
- Move `uploads/` to a dedicated volume or object storage if scale grows.

### 6.4 Authentication (out of scope, action required before public exposure)

This project does **not** ship with authentication. Before exposing the app on the public internet, add at minimum one of:
- Flask-Login with a user table.
- A reverse-proxy authentication gateway (oauth2-proxy, Authelia).
- HTTP basic auth at the nginx layer (acceptable for internal tools only).

### 6.5 Logging & Monitoring

Configure structured logging in production:

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
```

Recommended dashboards:
- Upload success/failure ratio.
- 413 frequency (signals user education needed on file size).
- Mean and tail of `labeling_duration_seconds` per session.
- Database file size growth.
