# Dataset Labeling Platform

A small Flask web application that lets a research team upload medical or
waste images, label them for AI training, and export the labeled dataset
together with **pre-computed GLCM texture features**, ready to drop into
any machine-learning pipeline.

The tool handles **two distinct research projects** in one UI, with strict
data separation:

| Project        | Use case             | Labels                                                              |
|----------------|----------------------|---------------------------------------------------------------------|
| `Fundus`       | Diabetic retinopathy | `Severity 0`, `Severity 1`, `Severity 2`, `Severity 3`, `Severity 4` |
| `WasteSorting` | Waste sorting        | `PET`, `Can`, `Plastic`                                              |

---

## Feature list

1. **Authentication** &mdash; register / login / logout, "forgot password"
   recovery via security question, role-based access (`admin` /
   `annotator`), every business route guarded by `@login_required`.
2. **Admin panel** &mdash; promote, demote and delete users. The first
   registered user becomes admin automatically; a CLI fallback exists for
   recovery. A seed script (`create_admin.py`) makes a known admin
   account available for repeatable setups.
3. **Annotation workflow** in two clean steps:
   - **Step 1 (upload)** &mdash; pick a project, drop one image (single file
     only), enter author + description, save.
   - **Step 2 (label)** &mdash; the image opens in an interactive viewer
     (mouse-wheel zoom, click-and-drag pan, rotate / flip / reset). Pick
     one label from large cards (or press `1`-`9`) and save.
4. **Storage layout** &mdash; files are renamed automatically to
   `Fundus_001.jpg`, `Fundus_002.jpg`, ... or `Waste_001.jpg`, ... and
   moved into the label folder on save (`data/images/Severity_0/`,
   `data/images/PET/`, etc.).
5. **Dataset browser** &mdash; two tabs (Fundus Dataset / WasteSorting
   Dataset). Each tab shows a table with thumbnail, filename, label,
   **description**, author and upload date. Per-tab text search and
   pagination (10 / 25 / 50 / 100 rows).
6. **Per-project analytics dashboard** &mdash; each project card on the
   home page links to `/dashboard/<project>`, a live view that combines
   a typed label breakdown (counts + percentages) on the left and a
   Chart.js doughnut chart on the right. Labels and counts are pulled
   straight from SQL (`GROUP BY label`), so the chart always reflects
   the current state of the database &mdash; no hardcoded lists, no
   manual refresh. Colours adapt to Light / Dark mode without a page
   reload.
7. **Exports** &mdash; one card per project, three formats:
   - **CSV** &mdash; 26 columns, semicolon-separated, opens directly in
     European Excel (FR / IT / ES locales) and pandas.
   - **JSON** &mdash; same 26 keys, flat structure, ready for any ML
     library.
   - **HTML** &mdash; single self-contained file showing each image next
     to its label.
   - CSV and JSON automatically compute and embed **6 GLCM texture
     features** (`contrast, dissimilarity, homogeneity, energy,
     correlation, asm`) for every image, expanded into 24 separate
     columns (4 directions each).
8. **Theme** &mdash; modern UI (Tailwind CSS) with an instant Light /
   Dark toggle, persisted in `localStorage`. Annotation viewer uses CSS
   transforms (no third-party library).

---

## Tech stack

- **Backend** &mdash; Python 3.10+, Flask 3, Flask-SQLAlchemy, Flask-WTF
  (CSRF protection), Flask-Login (sessions, role gates)
- **Frontend** &mdash; Tailwind CSS via CDN, vanilla JavaScript (no
  bundler), custom inline image viewer
- **Texture features** &mdash; scikit-image
  (`graycomatrix` / `graycoprops`) and OpenCV (image loading, grayscale
  conversion)
- **Database** &mdash; SQLite by default, swap to PostgreSQL via
  `DATABASE_URL`
- **Storage** &mdash; local folder (`data/images/<Label>/`), generated
  exports in `data/exports/`
- **Production server** &mdash; waitress (Windows-friendly, one
  command) or gunicorn (Linux)
- **Total** &mdash; 11 pinned Python dependencies

---

## Project structure

```
ModifV1_0_1_Correction/
├── backend/
│   ├── app.py                   Flask factory + error handlers + CLI commands
│   ├── __main__.py              python -m backend (dev entry point)
│   ├── config.py                env-driven settings, project IDs, label sets, timezone
│   ├── forms.py                 WTForms (Login / Register / Forgot / Reset)
│   ├── auth_utils.py            @admin_required decorator
│   ├── routes/
│   │   ├── auth.py              /login /logout /register /forgot /reset
│   │   ├── annotation.py        /annotation (2-step), /images/<filename>, /dataset/<project>
│   │   ├── dashboard.py         /dashboard/<dataset_type> analytics view
│   │   ├── export.py            /export, /export/csv, /export/json, /export/html
│   │   └── admin.py             /admin/users + promote / demote / delete
│   ├── models/database.py       User + ImageRecord ORM
│   └── services/
│       ├── image_service.py     file validation, sequential naming, label-folder routing
│       └── export_service.py    CSV / JSON / HTML builders + GLCM extraction
├── frontend/
│   ├── templates/               base + index + annotation + dashboard + analytics + export + auth/* + admin/* + errors/
│   └── static/
│       ├── css/app.css          minimal custom CSS on top of Tailwind
│       └── js/                  theme.js, toasts.js, annotation.js, dataset.js, dashboard.js, auth.js, admin.js
├── database/
│   ├── schema.sql               reference SQL schema (DB created at runtime)
│   └── dataset.db               runtime DB (gitignored)
├── data/
│   ├── images/                  uploaded files in <Label>/ subfolders (gitignored)
│   └── exports/                 generated CSV / JSON / HTML (gitignored)
├── docs/                        architecture.md, setup.md, screenshots/
├── run_server.py                LAN production launcher (waitress + auto-IP)
├── create_admin.py              one-shot seed script for the bootstrap admin account
├── requirements.txt             11 pinned dependencies
├── README.md                    this file
├── TECHNICAL_GUIDE.md           full handbook for maintainers
├── .env.example
└── .gitignore
```

---

## Quick start

### 1. Create a virtual environment

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

Paste the generated string as `SECRET_KEY` in `.env`. The app **refuses
to start** in production mode if `SECRET_KEY` is left at the default
value.

### 4. (Optional) Seed the bootstrap admin

If you want a known admin account ready before anyone uses `/register`,
run the seed script **once**:

```
.\.venv\Scripts\python create_admin.py     (Windows)
.venv/bin/python create_admin.py           (Linux / macOS)
```

Default credentials (edit the constants in `create_admin.py` to change them):

```
Username : XXXX
Password : XXXX
Question : XXXXXXXXXXX ?
Answer   : Safe answer 
```

The script is idempotent: re-running it later forces the seed values back
into the DB, which doubles as an emergency reset for the bootstrap admin.
---

## How to run

### Local development

```
python -m backend
```

Open http://127.0.0.1:5000. The dev server runs with `FLASK_DEBUG` taken
from your `.env`.

### LAN production (this PC becomes the team's server)

```
python run_server.py
```

This script:

- forces `FLASK_DEBUG=false` (the production guard activates),
- starts **waitress** on `0.0.0.0:8080`,
- auto-detects the machine's LAN IPv4 and prints a ready-to-share URL.

Output looks like:

```
================================================================
  Dataset Labeling Platform  -  production server (waitress)
================================================================
  Server online on port 8080
  This PC (server)     : http://127.0.0.1:8080
  Same Wi-Fi   : http://10.106.1.88:8080
```

Other PCs on the same Wi-Fi reach the app at the second URL.

> **Windows Firewall** prompts the first time. Allow Python on **Private
> networks** so other machines can connect.

### Linux production

```
gunicorn "backend.app:app" -b 0.0.0.0:8000 -w 4
```

Behind nginx or Caddy.

---

## Usage workflow

1. **Sign in** at `/login` (or `/register` if you have no account yet).
2. **Annotate**:
   - Step 1: `/annotation` &rarr; pick Fundus or WasteSorting, drag-and-drop
     one image, fill description, save. (Author is locked to your
     username for traceability.)
   - Step 2: the same page now shows the image viewer + the label cards.
     Pan / zoom / rotate to inspect, pick a label, save.
3. **Browse** `/dataset` &rarr; switch between the Fundus and
   WasteSorting tabs, search by filename, paginate. Delete with
   confirmation.
4. **Inspect distribution** &rarr; click the **Fundus images** or
   **WasteSorting images** card on the home page to open
   `/dashboard/<project>`. You get a live label breakdown (counts,
   percentages) and a doughnut chart. Labels are queried from SQL, so
   the chart updates the moment a new annotation lands.
5. **Export** `/export` &rarr; CSV / JSON (26-column GLCM schema) or HTML
   (visual preview), one card per project.
6. **Manage users** (admins only) &rarr; `/admin/users` to promote,
   demote or delete accounts.

---

## Configuration

Environment variables (both `CamelCase` and `UPPER_SNAKE_CASE` accepted
for legacy reasons):

| Variable        | Default                          | Notes                                       |
|-----------------|----------------------------------|---------------------------------------------|
| `SECRET_KEY`    | `dev-change-me-secret`           | **Mandatory** in production                 |
| `DATABASE_URL`  | `sqlite:///database/dataset.db`  | Any SQLAlchemy URL                          |
| `UPLOAD_FOLDER` | `./data/images`                  | Anchored to project root if relative        |
| `EXPORT_FOLDER` | `./data/exports`                 | Anchored to project root if relative        |
| `FLASK_DEBUG`   | `false`                          | `true` / `1` / `yes` / `on` to enable       |

Project IDs and label sets are defined in `backend/config.py`
(`PROJECT_IDS`, `PROJECT_LABELS`) &mdash; not env-driven, since the spec
fixes the exact values. `MAX_CONTENT_LENGTH` is hardcoded to 16 MB. Edit
`backend/config.py` to change either.

---

## Security

- **Password storage** &mdash; PBKDF2-SHA256 via
  `werkzeug.security.generate_password_hash`. Security answers are
  hashed too.
- **CSRF protection** &mdash; every POST form via Flask-WTF.
- **Path traversal blocked** by `send_from_directory` (Werkzeug
  `safe_join`).
- **File extension whitelist** on uploads (PNG, JPG, JPEG, BMP, GIF,
  TIF, TIFF, WEBP).
- **Stored filenames** are deterministic (`<Prefix>_NNN.<ext>`) and
  live inside their label folder; the project's filename prefix
  prevents cross-project collisions.
- **Robust try/except + rollback** around every DB commit; GLCM
  extraction degrades to zero-filled features on missing/corrupt files
  and logs the path.
- **Fail-fast** &mdash; the app refuses to boot in production if
  `SECRET_KEY` is the default.
- **Author tampering blocked** &mdash; the annotation form's `author`
  input is read-only client-side, and the server ignores it anyway,
  always using `current_user.username`.
- **CSRF-safe logout** &mdash; logout is POST-only with a token, so a
  drive-by link cannot kick a user out.
- **Admin self-protection** &mdash; an admin cannot demote themselves
  if they would leave the system without any admin, and cannot delete
  their own account from the UI.
- **`.env`** is gitignored; only `.env.example` is tracked.

---

## Documentation

- [`TECHNICAL_GUIDE.md`](TECHNICAL_GUIDE.md) &mdash; full handbook
  (architecture, GLCM internals, admin & user management, seed script,
  maintenance, troubleshooting).
- [`docs/setup.md`](docs/setup.md) &mdash; alternative install
  walk-through with troubleshooting.
- [`docs/architecture.md`](docs/architecture.md) &mdash; layered
  overview with diagram.
- [`database/schema.sql`](database/schema.sql) &mdash; reference SQL
  schema for both tables (`users` and `images`).

## ⚖️ Copyright and Intellectual Property

This project was developed by **Jimmy TREMOUILLAULT** as part of an international internship in collaboration with **Kasetsart University** (Sakon Nakhon/Bangkok, Thailand).

* **Author:** Jimmy TREMOUILLAULT
* **Institution:** Kasetsart University
* **Year:** 2026

⚠️ **Strict Restrictions:**
All rights reserved. This software, including its source code, user interface, database schemas, and documentation, is the intellectual property of the author and Kasetsart University. 

**Any unauthorized copy, modification, distribution, or commercial use of this platform without explicit prior written consent is strictly prohibited.**