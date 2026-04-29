# Dataset Labeling Tool

A simple web application that lets researchers upload medical or waste images, label them for AI training, and export the labeled dataset as CSV or JSON.

The system supports three research projects with the same tool:

- Diabetic retinopathy dataset preparation
- Telemedicine image data collection
- Waste sorting image dataset

## Feature list

1. **Image Upload** - upload one or many images with an optional contributor name and notes (16 MB cap per request).
2. **Image Labeling** - assign a label from a configurable list (default: `No DR / Mild / Moderate / Severe`); keyboard shortcuts `1`-`9`.
3. **Dataset Browser** - table view with filename, contributor, label, and upload date; filter All / Labeled / Unlabeled.
4. **Dataset Export** - download labeled data as CSV or JSON, in two layouts:
   - Full metadata (id, filenames, contributor, notes, label, status, timestamps)
   - AI-ready (`image_path`, `label`) for direct ingest by PyTorch / Keras / pandas

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

### 4. (Optional) Customize the label list

In `.env`:
```
AVAILABLE_LABELS=No DR,Mild,Moderate,Severe
```
or, for waste sorting:
```
AVAILABLE_LABELS=Plastic,Paper,Metal,Organic
```

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

1. **Upload** images on `/upload` (or click *Upload Image* on the home page).
2. **Label** them on `/label` - click the matching label or press its number key.
3. **Browse** and filter the dataset on `/dataset`.
4. **Export** as CSV or JSON on `/export`.

## Configuration

Environment variables (both `CamelCase` and `UPPER_SNAKE_CASE` accepted):

| Variable               | Default                         | Notes                                |
|------------------------|---------------------------------|--------------------------------------|
| `SECRET_KEY`           | `dev-change-me-secret`          | Mandatory in production              |
| `DATABASE_URL`         | `sqlite:///database/dataset.db` | Any SQLAlchemy URL                   |
| `UPLOAD_FOLDER`        | `./data/images`                 |                                      |
| `EXPORT_FOLDER`        | `./data/exports`                |                                      |
| `AVAILABLE_LABELS`     | `No DR,Mild,Moderate,Severe`    | Comma-separated list                 |
| `FLASK_DEBUG`          | `false`                         | `true` / `1` / `yes` / `on`          |

`MAX_CONTENT_LENGTH` is hardcoded to 16 MB. Edit `backend/config.py` to change.

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
