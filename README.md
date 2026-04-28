# Image Labeling Platform (Flask)

Web platform to build labeled image datasets for AI research workflows.
It supports session-based annotation, keyboard-driven labeling, and export-ready CSV files.

## Project Overview

This application helps researchers and engineers:
- Upload image batches (up to 16 MB per request).
- Create labeling sessions with N custom labels (not just two).
- Annotate quickly with UI buttons or keyboard shortcuts (keys `1`-`9`).
- Track progress and per-image timing on a dashboard.
- Export datasets in two formats: full metadata or AI-ready (`image_path`, `label`).

## Tech Stack

- Backend: Flask 3 + Flask-SQLAlchemy + Flask-WTF (CSRF)
- Database: SQLite (default), swap to PostgreSQL via `DatabaseUrl`
- Frontend: Bootstrap 5, vanilla JavaScript, Chart.js (CDN)

## Project Structure

```
ModifV1_0_1_Correction/
  app/
    __init__.py            # Application factory + CSRF + schema migrator
    __main__.py            # Entry point: python -m app
    config.py              # Config class (env-driven, PEP 8 names)
    error_handlers.py      # 404 / 413 / 500
    models.py              # ImageRecord ORM model
    blueprints/
      api.py               # POST routes: upload, label, delete, export
      main.py              # GET routes: index, history, dashboard, uploads
    services/
      export_service.py    # CSV builder (full + AI formats, UTF-8 BOM)
      image_service.py     # Upload validation + persistence
    utils/
      labels.py            # parse_custom_labels helper
  templates/               # Jinja2 templates (CSRF tokens included)
  static/
    css/app.css
    js/                    # labeling.js, history.js, charts.js
  scripts/seed_demo_data.py
  uploads/                 # Stored images (gitignored)
  exports/                 # Generated CSV (gitignored)
  .env.example             # Template for local secrets
  requirements.txt         # 7 direct dependencies
```

## Setup

### 1) Virtual environment (optional but recommended)

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows PowerShell
source .venv/bin/activate         # Linux/macOS
```

### 2) Install dependencies

```
pip install -r requirements.txt
```

### 3) Create your local `.env`

Copy `.env.example` to `.env`, then generate a strong secret:

```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the output as the `SecretKey` value in `.env`.

The application **refuses to start in production mode** (`FlaskDebug=false`) if `SecretKey` is left at its default value.

### 4) Run

```
python -m app
```

Open http://127.0.0.1:5000.

## Workflow

### Sessions

A session groups uploaded images and a list of custom labels. From the History page you can:
- Create a new session with custom labels.
- Append images to an existing session (labels are inherited).
- Delete a session and all its files.

### Labeling

- Keys `1`-`9` are mapped to the first nine labels of the session. Labels 10+ have no shortcut.
- Auto-advance toggle (persisted in `localStorage`) jumps to the next unlabeled image after each click.
- Per-image timing resets on every page load to avoid skewed statistics from refreshes or tab switches.

### Exports

Two formats, both UTF-8 with BOM (Excel-friendly, pandas-friendly):

| Format | Columns | Use case |
|--------|---------|----------|
| Full | id, original_filename, stored_filename, session_name, label_option_1, label_option_2, custom_labels, uploaded_at, labeled_at, label, status | Audit, traceability |
| AI | image_path, label | Direct ingest by PyTorch / Keras / HuggingFace |

The AI format includes the `uploads/` prefix so `Image.open(row["image_path"])` works directly.

## Dashboard

- Label distribution (pie)
- Annotation pace per day (bar)
- Mean time-to-label (seconds)

## Demo Data

```
python scripts/seed_demo_data.py
python scripts/seed_demo_data.py --count 10 --reset
```

## Configuration

Environment variables (both `CamelCase` and `UPPER_SNAKE_CASE` are accepted):

| Variable | Default | Notes |
|----------|---------|-------|
| `SecretKey` / `SECRET_KEY` | `dev-change-me-secret` | **Mandatory in production** |
| `DatabaseUrl` / `DATABASE_URL` | `sqlite:///dataset.db` | Any SQLAlchemy URL |
| `UploadFolder` / `UPLOAD_FOLDER` | `./uploads` | |
| `ExportFolder` / `EXPORT_FOLDER` | `./exports` | |
| `FlaskDebug` / `FLASK_DEBUG` | `false` | `true`/`1`/`yes`/`on` to enable |

`MAX_CONTENT_LENGTH` is hardcoded to 16 MB. Edit `app/config.py` to change it.

## Security

- CSRF protection enabled on every POST form (Flask-WTF).
- Path traversal blocked via `send_from_directory` on `/uploads/<filename>`.
- File extension whitelist on uploads (PNG/JPG/BMP/GIF/TIF/WEBP).
- `secure_filename` + UUID-based stored names.
- `.env` is gitignored. `.env.example` is the only tracked template.

This project does **not** include user authentication. Do not expose it on the public internet without adding a login layer (Flask-Login or a reverse-proxy auth gateway).

For deeper internals, see `TECHNICAL_GUIDE.md`.
