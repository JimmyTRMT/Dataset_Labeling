# Setup Guide

This guide walks through installing, configuring, and running the Dataset Labeling Tool on a local machine.

## Prerequisites

- Python 3.10 or higher
- pip
- (Optional) git

## 1. Clone or download the project

```
git clone <repository-url>
cd dataset-labeling-tool
```

## 2. Create a virtual environment (recommended)

Windows (PowerShell):

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux / macOS:

```
python -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```
pip install -r requirements.txt
```

The project depends on 7 packages: Flask, Flask-SQLAlchemy, Flask-WTF, SQLAlchemy, Werkzeug, python-dotenv, and gunicorn (production WSGI server).

## 4. Configure environment variables

Copy the template and fill in your values:

```
cp .env.example .env
```

Generate a strong secret key:

```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the result as the `SECRET_KEY` value in `.env`.

The application **refuses to start** in production mode (`FLASK_DEBUG=false`) if `SECRET_KEY` is left at its default value.

### Available environment variables

| Variable             | Default                              | Notes                                    |
|----------------------|--------------------------------------|------------------------------------------|
| `SECRET_KEY`         | `dev-change-me-secret`               | Mandatory in production                  |
| `DATABASE_URL`       | `sqlite:///database/dataset.db`      | Any SQLAlchemy URL                       |
| `UPLOAD_FOLDER`      | `./data/images`                      | Where uploaded images are stored         |
| `EXPORT_FOLDER`      | `./data/exports`                     | Where generated CSV/JSON files land      |
| `AVAILABLE_LABELS`   | `No DR,Mild,Moderate,Severe`         | Comma-separated label list               |
| `FLASK_DEBUG`        | `false`                              | `true`/`1`/`yes`/`on` to enable          |

Both `CamelCase` and `UPPER_SNAKE_CASE` variants are accepted (`SECRET_KEY` or `SecretKey`).

## 5. Run the application

From the project root:

```
python -m backend
```

or, equivalently:

```
python -m backend.app
```

Then open http://127.0.0.1:5000 in your browser.

## 6. (Optional) Customize labels per use case

Switch label sets via `.env` without touching the code:

Diabetic retinopathy:
```
AVAILABLE_LABELS=No DR,Mild,Moderate,Severe
```

Waste sorting:
```
AVAILABLE_LABELS=Plastic,Paper,Metal,Organic
```

Restart the app after changing the value.

## 7. Production deployment

For real deployments, use gunicorn behind a reverse proxy (nginx, Caddy):

```
gunicorn "backend.app:app" -b 0.0.0.0:8000 -w 4
```

The application does **not** include user authentication. Add a login layer (Flask-Login or a reverse-proxy auth gateway) before exposing it to the public internet.

## Troubleshooting

- **`RuntimeError: Refusing to start with the default SecretKey`**
  Generate and set a real `SECRET_KEY` in `.env`, or run with `FLASK_DEBUG=true` for local development.
- **`413 Request Entity Too Large`**
  An upload exceeded 16 MB. Edit `MAX_CONTENT_LENGTH` in `backend/config.py` to change the cap.
- **Excel shows everything in one column**
  The CSV is comma-separated (ML standard). Use *Data → From Text/CSV* in Excel and select Comma as separator. Excel French locale defaults to `;`.
- **Database migration / schema change**
  Delete `database/dataset.db` and restart. SQLAlchemy recreates the schema from `backend/models/database.py`.
