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

The application employs the Factory Pattern through the `create_app()` function in `app/__init__.py`. This design separates application initialization from configuration, enabling flexible instantiation and testing workflows.

**Benefits:**
- **Decoupling:** Configuration files and factory logic are independent, allowing environment-specific setup (development, testing, production).
- **Testability:** Multiple app instances can be created with different configs without side effects.
- **Simplicity:** A single entry point (`python -m app`) bootstraps the entire system.

**Initialization Steps:**
1. Create Flask instance with paths resolved via `pathlib`.
2. Load configuration from environment variables (via `Config` class).
3. Create upload/export directories if missing.
4. Initialize SQLAlchemy ORM with `db.init_app()`.
5. Create database table schema on first run (idempotent).
6. Register Blueprints (main, api) and error handlers.

### 1.2 Blueprint Architecture

Blueprints modularize routing logic and responsibility separation:

- **main_bp** (`blueprints/main.py`):
  - GET `/` : Render the labeling interface with session awareness.
  - GET `/history` : Render the session management and upload form.
  - GET `/dashboard` : Render analytics (distribution, pace, average time).
  - GET `/uploads/<filename>` : Serve locally stored images.

- **api_bp** (`blueprints/api.py`, with prefix `/api`):
  - POST `/upload` : Accept image uploads and create database records.
  - POST `/label/<id>` : Update image status and assign label.
  - GET `/export` : Generate and return full global CSV.
  - GET `/export/session/<name>` : Generate session-scoped CSV.
  - POST `/delete-session/<name>` : Destroy session and linked files.
  - POST `/delete-image/<id>` : Remove single image (disk and database).
  - POST `/reset-session` : Archive current session.

This separation keeps UI logic distinct from data/API logic, easing maintenance and scaling.

### 1.3 Service Layer

Two service modules encapsulate business logic:

- **image_service.py:**
  - `is_allowed_file()` : Validates file extensions against a whitelist.
  - `persist_uploaded_images()` : Saves files to disk, creates database records, returns metadata.

- **export_service.py:**
  - `build_export_csv()` : Generates CSV files in two formats (full metadata or AI).
  - Supports legacy format names ("complet"/"ia") for backward compatibility.

### 1.4 Frontend Separation of Concerns

The frontend follows a strict Separation of Concerns model:

- **HTML templates (`templates/*.html`)** are responsible for page structure and server-side rendering.
- **CSS (`static/css/app.css`)** handles visual presentation and responsive styling.
- **JavaScript modules (`static/js/*.js`)** implement page behavior and client-side interactions.

This architecture keeps templates clean, improves maintainability, and enables better browser caching because JavaScript files can be cached independently from server-rendered HTML.

## 2. Database Schema

### 2.1 ImageRecord Model

| Field | Type | Constraints | Purpose |
|-------|------|-------------|---------|
| `id` | Integer | Primary Key | Unique identifier. |
| `original_filename` | String(255) | Not Null | User-facing filename (for export/reference). |
| `stored_filename` | String(255) | Unique, Not Null | Server-side filename (timestamp_uuid format). |
| `file_path` | String(500) | Not Null | Absolute disk path (for cleanup/migration). |
| `session_name` | String(255) | Default="Default Session" | Groups images by annotation batch. |
| `label_option_1` | String(100) | Default="labelOne" | First binary label for the session. |
| `label_option_2` | String(100) | Default="labelTwo" | Second binary label for the session. |
| `uploaded_at` | DateTime | Default=utcnow, Not Null | Timestamp when file was uploaded. |
| `labeled_at` | DateTime | Nullable | Timestamp when image was labeled (null if unlabeled). |
| `last_viewed_at` | DateTime | Nullable | When the image was first displayed to the annotator. |
| `labeling_duration_seconds` | Float | Nullable | Time elapsed from display to confirmation. |
| `label` | String(100) | Nullable | The assigned label value (null if unlabeled). |
| `status` | String(20) | Default="unlabeled", Not Null | State: "unlabeled" or "labeled". |

### 2.2 Key Methods

- **mark_as_labeled(label_value, duration_seconds):** Atomically updates status, label, labeled_at, and labeling_duration_seconds. Clears last_viewed_at to prevent re-timing.

- **to_export_row():** Returns a dictionary suitable.

### 2.3 Schema Evolution

The `ensure_schema_compatibility()` function (in `__init__.py`) uses SQLAlchemy introspection to add missing columns to existing SQLite databases. This prevents schema mismatch errors when deploying schema updates to already deployed instances.

## 3. Data Workflow

### 3.1 Upload Flow

User selects images (form) 
  - POST /api/upload 
  - persist_uploaded_images() {
       - Validate extension (ALLOWED_EXTENSIONS)
       - Secure filename (werkzeug.utils.secure_filename)
       - Generate unique name: "{timestamp}_{uuid[:8]}.{ext}"
       - Write to disk (UPLOAD_FOLDER)
       - Create ImageRecord in database (status="unlabeled")
     }
  - Flash success message
  - Redirect to labeling page

**Key Design Choices:**
- **Filename Collision Avoidance:** Timestamp + UUID prefix ensures uniqueness even under concurrent uploads.
- **Original Filename Preservation:** stored in original_filename for human-readable export.
- **Session Grouping:** All uploads in one form request share a session_name, linking images for common labels.

### 3.2 Labeling Flow

User views image on GET /
  - Flask renders current ImageRecord (status="unlabeled")
  - Last_viewed_at = now (for timing)
  - User presses keyboard key 1 or 2 (or clicks button)
  - POST /api/label/<id> with selected label
  - mark_as_labeled(label, duration_seconds)
  - Database commit
  - Flash success message
  - If auto_advance is enabled:
       - Query next unlabeled image in session
       - Redirect with ?image_id=... (preserve URL state)
     Else:
       - Stay on labeling page (manual image selection)

**Timing Metric:**
Duration is calculated as `labeled_at - last_viewed_at`, representing the time from first display to confirmation. This metric feeds the dashboard's "Average Labeling Time" chart.

### 3.3 Export Flow

#### Full Dataset Format (CSV)
Columns: id, original_filename, stored_filename, session_name, label_option_1, label_option_2, uploaded_at, labeled_at, label, status

**Use Case:** Complete record for audit, retraining, or data analysis (includes metadata and timestamps).

#### AI Dataset Format (Minimal)
Columns: filename, label

**Use Case:** Direct import into ML training pipelines. Minimal schema reduces parsing overhead and focuses on the essential label-to-image mapping.

**Export Process:**
1. Query labeled images (status="labeled").
2. Call `build_export_csv(images, export_folder, format="full" or "ai")`.
3. Sanitize session name for safe filename.
4. Add timestamp to exported file: `export_sessionname_full_20260325_143022.csv`.
5. Stream file to user as attachment.

**Backward Compatibility:**
Format parameter accepts legacy names ("complet"-"full", "ia"-"ai") via aliases, preventing URL breakage on deployments.

## 4. Frontend Logic

Frontend behavior is now decoupled from HTML templates and centralized into dedicated JavaScript files:

- `static/js/labeling.js` for labeling page interactions (`index.html`).
- `static/js/history.js` for session/upload page interactions (`history.html`).
- `static/js/charts.js` for dashboard chart initialization (`dashboard.html`).

Templates only include external script references and data payloads when needed, which reduces inline complexity and improves long-term maintainability.

### 4.1 Session-Aware Labeling

The labeling interface (`index.html`) persists the active session in URL parameters:

http://localhost:5000/?session_name=Session%202026-03-25&auto_advance=1&image_id=42

**Query Parameters:**
- `session_name` : Scopes image queries and export operations.
- `auto_advance` : Enables/disables automatic progression (stored in localStorage for persistence).
- `image_id` : Forces a specific image (manual selection overrides auto-advance).

### 4.2 Keyboard Shortcuts

JavaScript event listener captures keydown events (unless focused on form inputs):

- Key "1" - Submit with label_option_1
- Key "2" - Submit with label_option_2

Implementation uses `event.key.toLowerCase()` for cross-browser consistency and checks `document.activeElement.tagName` to avoid interference with text input.

### 4.3 Progress Visualization

The main page displays a progress bar (`<div class="progress-bar">`). JavaScript hydrates the bar width from a server-rendered `data-progress` attribute:

const progressValue = parseInt(progressBar.dataset.progress || "0", 10);
progressBar.style.width = progressValue + "%";

This approach avoids JavaScript-based calculation, delegating computation to the server (cleaner separation of concerns).

### 4.4 Dashboard Analytics

The dashboard (`dashboard.html`) uses **Chart.js** (CDN) to visualize three metrics:

1. **Pie Chart (Label Distribution):**
   - Displays count of images per unique label.
   - Colors inherit from Bootstrap CSS variables (--bs-success, --bs-danger, --bs-secondary).

2. **Bar Chart (Labels per Day):**
   - Groups labeled images by the date of labeled_at.
   - Shows annotation pace over time.
   - Useful for spotting productivity trends.

3. **Average Labeling Time Card:**
   - Displays the mean labeling_duration_seconds across all labeled images.
   - Provides a single metric for efficiency assessment.

**Data Hydration:**
Flask renders data as JSON inside `<script type="application/json">` tags. JavaScript parses these server-side datasets before chart initialization, avoiding browser security restrictions and enabling static-file hosting in the future.

With this decoupled model, chart initialization logic remains in `static/js/charts.js`, while data stays server-driven in the template. This separation improves caching efficiency and keeps view files focused on content layout.

### 4.5 File Upload UI Customization

The native file input (`<input type="file">`) is hidden (CSS class `d-none`). A custom button ("Choose files") and read-only text field provide an English-only interface:

function updateSelectedFilesText() {
    const totalFiles = fileInput.files.length;
    if (totalFiles === 0) {
        selectedFilesText.value = "No file selected";
    } else if (totalFiles === 1) {
        selectedFilesText.value = fileInput.files[0].name;
    } else {
        selectedFilesText.value = `${totalFiles} files selected`;
    }
}

This prevents browser-localized text (e.g., French "Choisir des fichiers") from appearing in the UI.

## 5. Security & Portability

### 5.1 Environment-Based Configuration

All sensitive and deployment-specific settings are externalized via environment variables:

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///dataset.db")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
EXPORT_FOLDER = os.getenv("EXPORT_FOLDER", "exports")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false")

**Security Implications:**
- Production deployments must override `SECRET_KEY` (preventing session hijacking).
- Database credentials can be embedded in DATABASE_URL without hardcoding.
- Folder permissions are controlled externally (CI/CD or container orchestration handles creation).

### 5.2 Cross-Platform Path Handling

The `pathlib.Path` library is used throughout instead of string concatenation:

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
upload_dir = Path(app.config["UPLOAD_FOLDER"])
file_path = upload_dir / filename

**Advantages:**
- Automatic slash normalization (/ on Unix, \ on Windows).
- `.resolve()` returns absolute paths without manual os.path.join() calls.
- `.mkdir(exist_ok=True, parents=True)` is cleaner than os.makedirs().

**Portability:**
Code runs unchanged on Windows, Linux, and macOS without path hardcoding.

### 5.3 File Security

- **Filename Sanitization:** `werkzeug.utils.secure_filename()` prevents path traversal attacks (e.g., "../../etc/passwd").
- **Extension Whitelist:** Only image formats are accepted (ALLOWED_EXTENSIONS = {png, jpg, jpeg, bmp, gif, tif, tiff, webp}).
- **Unique Naming:** Server-generated filenames prevent enumeration and collision exploits.

### 5.4 Database Security

- **SQLAlchemy ORM:** Parameterized queries prevent SQL injection.
- **SQLite Local Development:** Simple, file-based database suitable for single-user workflows. Production deployments should use PostgreSQL or MySQL.
- **TRACK_MODIFICATIONS = False:** Disables Flask-SQLAlchemy event tracking (performance optimization, requires manual relationship management).

## 6. Deployment Considerations

### 6.1 Production WSGI Server

For production, replace Flask's debug server (`app.run()`) with a WSGI application server:

gunicorn --workers 4 --bind 0.0.0.0:5000 "app:create_app()"

### 6.2 Database Persistence

- **SQLite:** Suitable for research/prototype deployments. Ensure the database file is on a persistent volume.
- **PostgreSQL:** Recommended for multi-user or cloud deployments. Update DATABASE_URL:
  DATABASE_URL=postgresql://user:password@localhost:5432/labeling_app

### 6.3 Static Files & Uploads

In production:
- Serve static files (CSS, JS) via a CDN or reverse proxy (nginx).
- Store uploads on a dedicated volume or object storage (S3, Azure Blob).
- Use Flask's `send_file()` with `X-Accel-Redirect` headers (nginx) or `X-Sendfile` (Apache) for efficient file serving.

### 6.4 Environment Variables

Example `.env` file (not versioned in Git):

SECRET_KEY=your-production-secret-key-here
DATABASE_URL=postgresql://user:password@db-host:5432/labeling_db
UPLOAD_FOLDER=/mnt/uploads
EXPORT_FOLDER=/mnt/exports
FLASK_DEBUG=false

Load via:
export $(cat .env | xargs)
python -m app

### 6.5 Logging & Monitoring

In production, configure structured logging:

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

Monitor key metrics:
- Upload success/failure rates.
- Labeling duration trends.
- Database table size (images grows with uploads).
- API endpoint response times.
