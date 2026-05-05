# Dataset Labeling Tool

A simple web application that lets researchers upload medical or waste images, label them for AI training, and export the labeled dataset as CSV or JSON.

The system handles **two distinct research projects** under one tool, with strict data separation:

| Project    | Use case                       | Labels                                                              |
|------------|--------------------------------|---------------------------------------------------------------------|
| `DR`       | Diabetic retinopathy           | `severity 0`, `severity 1`, `severity 2`, `severity 3`, `severity 4`, `severity 5` |
| `SmartBin` | Waste sorting                  | `Can`, `Plastic`, `Glass`, `Cardboard`                              |

## Feature list

1. **Image Upload** - mandatory project choice (DR / SmartBin) via radio buttons, then upload one or many images with an optional contributor name and notes (16 MB cap per request).
2. **Image Labeling** - the buttons offered match the current image's project; keyboard shortcuts `1`-`9` for fast labeling.
3. **Dataset Browser** - table with filename, **project**, contributor, label, and upload date; two orthogonal filters (project: All / DR / SmartBin, status: All / Labeled / Unlabeled).
4. **Dataset Export** - one section per project, each producing CSV or JSON in two layouts:
   - Full metadata (id, filenames, project, contributor, notes, label, status, timestamps)
   - AI-ready (`image_path`, `label`) for direct ingest by PyTorch / Keras / pandas
   - Filenames embed the project name: `export_DR_full_<timestamp>.csv`, `export_SmartBin_ai_<timestamp>.json`, etc.

## Tech stack

- **Backend**: Python 3.10+, Flask 3, Flask-SQLAlchemy, Flask-WTF (CSRF)
- **Frontend**: Bootstrap 5, vanilla JavaScript
- **Database**: SQLite by default, swap to PostgreSQL via `DATABASE_URL`
- **Storage**: local folder (`data/images/`)

## Project structure

```
dataset-labeling-tool/
├── backend/
│   ├── app.py                Flask entry point
│   ├── routes/
│   │   ├── upload.py
│   │   ├── label.py
│   │   └── export.py
│   ├── models/
│   │   └── database.py
│   ├── services/
│   │   ├── image_service.py
│   │   └── export_service.py
│   └── config.py
├── frontend/
│   ├── templates/            index.html, upload.html, label.html, dashboard.html, export.html, errors/
│   └── static/               css/, js/, img/
├── database/
│   └── schema.sql            Reference SQLite schema (DB itself is created at runtime)
├── data/
│   ├── images/               Uploaded images (gitignored)
│   └── exports/              Generated CSV / JSON (gitignored)
├── docs/
│   ├── architecture.md
│   ├── setup.md
│   └── screenshots/
├── requirements.txt
├── README.md
├── .env.example
└── .gitignore
```

## Setup steps

### 1. Create a virtual environment (recommended)

Windows:
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux / macOS:
```
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Create `.env`

```
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated string as `SECRET_KEY` in `.env`. The app **refuses to start** in production mode if `SECRET_KEY` is the default value.

### 4. (Optional) Add or edit projects

Project IDs and label sets live in [`backend/config.py`](backend/config.py) as Python constants (the spec fixes them, so they are not env-driven). To add a third project, edit `PROJECT_IDS` and `PROJECT_LABELS` and restart the app — the upload form, dataset filters, and export page pick it up automatically.

## How to run

From the project root:

```
python -m backend
```

Then open http://127.0.0.1:5000.

For production:
```
gunicorn "backend.app:app" -b 0.0.0.0:8000 -w 4
```

## Usage

1. **Upload** images on `/upload` (or click *Upload Image* on the home page). Pick a project (DR or SmartBin) — required.
2. **Label** them on `/label` — click the matching label or press its number key. Buttons match the image's project.
3. **Browse** and filter the dataset on `/dataset` (filter by project and / or labeling status).
4. **Export** the labeled dataset of one project on `/export` — CSV or JSON, full or AI-ready.

## Configuration

Environment variables (both `CamelCase` and `UPPER_SNAKE_CASE` accepted):

| Variable               | Default                         | Notes                                |
|------------------------|---------------------------------|--------------------------------------|
| `SECRET_KEY`           | `dev-change-me-secret`          | Mandatory in production              |
| `DATABASE_URL`         | `sqlite:///database/dataset.db` | Any SQLAlchemy URL                   |
| `UPLOAD_FOLDER`        | `./data/images`                 |                                      |
| `EXPORT_FOLDER`        | `./data/exports`                |                                      |
| `FLASK_DEBUG`          | `false`                         | `true` / `1` / `yes` / `on`          |

Project IDs and label sets are defined in `backend/config.py` (`PROJECT_IDS`, `PROJECT_LABELS`) — not env-driven, since the spec fixes the exact values. `MAX_CONTENT_LENGTH` is hardcoded to 16 MB. Edit `backend/config.py` to change either.

## Security

- CSRF protection on every POST form (Flask-WTF).
- Path traversal blocked by `send_from_directory` (Werkzeug `safe_join`).
- File extension whitelist on uploads (PNG, JPG, JPEG, BMP, GIF, TIF, TIFF, WEBP).
- `secure_filename` + timestamp + UUID for stored names.
- `.env` is gitignored; `.env.example` is the only tracked template.
- The app does **not** include user authentication. Do not expose it on the public internet without a login layer.

## Documentation

- [`docs/setup.md`](docs/setup.md) - detailed installation and troubleshooting
- [`docs/architecture.md`](docs/architecture.md) - layers, schema, request flow, security
- [`database/schema.sql`](database/schema.sql) - reference SQL schema
