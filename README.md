# Dataset Labeling Platform

A small web application that lets a research team upload medical or waste images, label them for AI training, and export the labeled dataset with **pre-computed GLCM texture features** ready for any machine-learning pipeline.

The tool handles **two distinct research projects** under one UI, with strict data separation:

| Project    | Use case             | Labels                                                                              |
|------------|----------------------|-------------------------------------------------------------------------------------|
| `DR`       | Diabetic retinopathy | `severity 0`, `severity 1`, `severity 2`, `severity 3`, `severity 4`, `severity 5`  |
| `SmartBin` | Waste sorting        | `Can`, `Plastic`, `Glass`, `Cardboard`                                              |

## Feature list

1. **Image upload** — mandatory project choice (DR / SmartBin) via radio cards, drag-and-drop dropzone, optional contributor and notes. 16 MB cap per request.
2. **Image labeling** — interactive image viewer with mouse-wheel zoom, click-and-drag pan, rotate / flip / reset; the label buttons match the current image's project; keyboard shortcuts `1`-`9`.
3. **Dataset browser** — sortable table with filename, project, contributor, label, upload date; two orthogonal filters (project: All / DR / SmartBin · status: All / Labeled / Unlabeled).
4. **Dataset export** — one section per project, three formats:
   - **CSV** — 26 columns, semicolon-separated, opens directly in European Excel (FR / IT / ES locales) and pandas.
   - **JSON** — same 26 keys, flat structure, ready for any ML library.
   - **HTML** — single self-contained file showing each image next to its label.
   - The CSV and JSON exports automatically compute and embed **6 GLCM texture features** (`contrast, dissimilarity, homogeneity, energy, correlation, asm`) for every image, expanded into 24 separate columns (4 directions each).

## Tech stack

- **Backend** — Python 3.10+, Flask 3, Flask-SQLAlchemy, Flask-WTF (CSRF protection)
- **Frontend** — Tailwind CSS (CDN), vanilla JavaScript, custom image viewer (CSS transforms, no third-party lib)
- **Texture features** — scikit-image (`graycomatrix` / `graycoprops`) and OpenCV (image loading, grayscale conversion)
- **Database** — SQLite by default, swap to PostgreSQL via `DATABASE_URL`
- **Storage** — local folder (`data/images/`), generated exports in `data/exports/`
- **Production server** — waitress (Windows-friendly, single command) or gunicorn (Linux)

## Project structure

```
ModifV1_0_1_Correction/
├── backend/
│   ├── app.py                    Flask factory + error handlers + local_time filter
│   ├── __main__.py               python -m backend (dev entry point)
│   ├── config.py                 env-driven settings, project IDs, label sets, timezone
│   ├── routes/                   upload.py, label.py, export.py
│   ├── models/database.py        ImageRecord ORM (one table)
│   └── services/                 image_service.py, export_service.py
├── frontend/
│   ├── templates/                base + index/upload/label/dashboard/export + errors/
│   └── static/                   css/app.css, js/{upload, labeling, dataset}.js
├── database/schema.sql           reference SQL schema (DB created at runtime)
├── data/images/, data/exports/   runtime data (gitignored)
├── docs/                         architecture.md, setup.md, screenshots/
├── run_server.py                 LAN production launcher (waitress + auto-IP)
├── requirements.txt              10 pinned dependencies
├── README.md, TECHNICAL_GUIDE.md
├── .env.example, .gitignore
```

## Quick start

### 1. Create a virtual environment (recommended)

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

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Create `.env`

```
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated string as `SECRET_KEY` in `.env`. The app **refuses to start** in production mode if `SECRET_KEY` is left at the default value.

## How to run

### Local development

```
python -m backend
```

Open http://127.0.0.1:5000.

### LAN production (this PC becomes the server for the team)

```
python run_server.py
```

The script:

- forces `FLASK_DEBUG=false` (production guard active),
- starts waitress on `0.0.0.0:8080`,
- auto-detects the machine's LAN IPv4 and prints a ready-to-share URL.

Output looks like:

```
================================================================
  Dataset Labeling Platform  -  production server (waitress)
================================================================
  Server online on port 8080
  This PC      : http://127.0.0.1:8080
  Same Wi-Fi   : http://10.106.1.88:8080
```

Other PCs on the same Wi-Fi reach the app at the second URL.

> **Windows Firewall** prompts the first time. Allow Python on **Private networks** so other machines can connect.

### Linux production

```
gunicorn "backend.app:app" -b 0.0.0.0:8000 -w 4
```

Behind nginx or Caddy.

## Usage

1. **Upload** images on `/upload` — pick DR or SmartBin (required), drag-and-drop or browse, optional contributor + notes.
2. **Label** on `/label` — zoom and pan the image with the mouse, click a label card or press its number key (`1`-`9`), then *Save & Next*.
3. **Browse** the dataset on `/dataset` — table with two filter groups (project, status). Delete with confirmation.
4. **Export** on `/export` — per-project cards with CSV / JSON / HTML download buttons.

## Configuration

Environment variables (both `CamelCase` and `UPPER_SNAKE_CASE` accepted):

| Variable        | Default                          | Notes                                       |
|-----------------|----------------------------------|---------------------------------------------|
| `SECRET_KEY`    | `dev-change-me-secret`           | Mandatory in production                     |
| `DATABASE_URL`  | `sqlite:///database/dataset.db`  | Any SQLAlchemy URL                          |
| `UPLOAD_FOLDER` | `./data/images`                  | Anchored to project root if relative        |
| `EXPORT_FOLDER` | `./data/exports`                 | Anchored to project root if relative        |
| `FLASK_DEBUG`   | `false`                          | `true` / `1` / `yes` / `on` to enable       |

Project IDs and label sets are defined in `backend/config.py` (`PROJECT_IDS`, `PROJECT_LABELS`) — not env-driven, since the spec fixes the exact values. `MAX_CONTENT_LENGTH` is hardcoded to 16 MB. Edit `backend/config.py` to change either.

## Security

- CSRF protection on every POST form (Flask-WTF).
- Path traversal blocked by `send_from_directory` (Werkzeug `safe_join`).
- File extension whitelist on uploads (PNG, JPG, JPEG, BMP, GIF, TIF, TIFF, WEBP).
- `secure_filename` + UTC timestamp + UUID for stored names.
- Robust try/except + rollback around every DB commit; GLCM extraction degrades to zero-filled features on missing/corrupt files.
- Fail-fast: the app refuses to boot in production if `SECRET_KEY` is the default.
- `.env` is gitignored; `.env.example` is the only tracked template.
- The app does **not** include user authentication. Do not expose it on the public internet without a login layer.

## Documentation

- [`TECHNICAL_GUIDE.md`](TECHNICAL_GUIDE.md) — full handbook (intro, install, GLCM explained, maintenance, file map)
- [`docs/setup.md`](docs/setup.md) — alternative install walk-through with troubleshooting
- [`docs/architecture.md`](docs/architecture.md) — layered overview with diagram
- [`database/schema.sql`](database/schema.sql) — reference SQL schema

## ⚖️ Copyright and Intellectual Property

This project was developed by **Jimmy TREMOUILLAULT** as part of an international internship in collaboration with **Kasetsart University** (Sakon Nakhon/Bangkok, Thailand).

* **Author:** Jimmy TREMOUILLAULT
* **Institution:** Kasetsart University
* **Year:** 2026

⚠️ **Strict Restrictions:**
All rights reserved. This software, including its source code, user interface, database schemas, and documentation, is the intellectual property of the author and Kasetsart University. 

**Any unauthorized copy, modification, distribution, or commercial use of this platform without explicit prior written consent is strictly prohibited.**