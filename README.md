# Dataset Labeling Platform

A Flask web application for a research team to upload images, label them
for AI training, and export the result with **pre-computed GLCM texture
features**. Drop the exports straight into any machine-learning pipeline.

Two research projects share the same UI, with strict data separation:

| Project        | Use case             | Labels                                                              |
|----------------|----------------------|---------------------------------------------------------------------|
| `Fundus`       | Diabetic retinopathy | `Severity 0`, `Severity 1`, `Severity 2`, `Severity 3`, `Severity 4` |
| `WasteSorting` | Waste sorting        | `PET`, `Can`, `Plastic`                                              |

---

## Features

1. **Secure authentication** &mdash; Flask-Login sessions with
   PBKDF2-SHA256 password hashing (Werkzeug, 1M iterations). Username +
   password, plus a self-service recovery flow built on a user-chosen
   security question (no email, no SMTP). Two roles, `admin` and
   `annotator`. Every business route is gated by `@login_required` at
   the blueprint level, so no endpoint can accidentally stay public.
2. **Admin panel** &mdash; promote, demote, delete accounts. First
   registered user is auto-promoted to admin so the app is usable out of
   the box; a CLI command and a one-shot `create_admin.py` script cover
   the lockout cases. Self-protection: the last admin cannot demote or
   delete themselves.
3. **Two-step annotation** &mdash; (1) pick a project, drop one image,
   add author + description; (2) inspect the image in an interactive
   viewer (mouse-wheel zoom, click-and-drag pan, rotate, flip, reset)
   and pick a label from large cards (or hit `1`-`9` on the keyboard).
   Pending uploads are **per-user**: two annotators working at the
   same time never see each other's drafts.
4. **Touch-ready image viewer** &mdash; the same viewer works at the
   finger on tablet and phone via the Pointer Events API: one finger
   pans, two fingers pinch-zoom. `touch-action: none` on the frame
   keeps the browser from stealing the gesture.
5. **Deterministic storage** &mdash; uploads are renamed sequentially
   (`Fundus_001.jpg`, `Waste_042.jpg`) and moved into their label
   folder on save (`data/images/Severity_0/`, `data/images/PET/`).
   Project-prefixed names mean no cross-project collisions, ever.
6. **Dataset browser** &mdash; one tab per project, per-tab text search
   and pagination (10 / 25 / 50 / 100), thumbnail + filename + label +
   description + author + upload date. Delete is **role-aware**:
   admins can remove any image, annotators only their own. The Delete
   button is hidden when the rule doesn't grant access, but the real
   barrier is a server-side `abort(403)`.
7. **Live analytics dashboard** &mdash; each project card on the home
   page opens `/dashboard/<project>`. A doughnut chart (Chart.js) sits
   next to a typed label breakdown with counts and percentages. Labels
   are queried in SQL via `GROUP BY` &mdash; **never hardcoded** &mdash;
   so the view always reflects the current database. A personal
   "average labeling time" card (scoped to the current user on this
   project, NULL durations ignored) sits above the chart. Chart colours
   re-render on Light / Dark toggle without a page reload.
8. **Exports** &mdash; one card per project, three formats:
   - **CSV** &mdash; 26 columns, `;` delimiter, UTF-8 with BOM. Opens
     straight in European Excel (FR / IT / ES) and pandas.
   - **JSON** &mdash; same 26 keys, flat structure, numeric values.
   - **HTML** &mdash; self-contained preview (image + label per row),
     images base64-embedded, works offline.
   - CSV and JSON ship the 6 GLCM features (`contrast`, `dissimilarity`,
     `homogeneity`, `energy`, `correlation`, `asm`) at 4 angles each.
     The pipeline is **fail-soft**: a corrupt image yields zero-filled
     features and a log line, never a 500.
9. **Mobile-first responsive UI** &mdash; Tailwind utilities drive
   every breakpoint. The navbar collapses into a hamburger below `md`,
   the annotation viewer stacks under the controls on small screens,
   the analytics grid folds from 2-column to 1-column, tables overflow
   horizontally instead of breaking the page width.
10. **Light / Dark theme** &mdash; instant toggle persisted in
    `localStorage`, applied pre-paint to avoid FOUC.

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
  Same Wi-Fi   : http://XX.XXX.X.XX:8080
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

- **Password and security-answer hashing** &mdash; PBKDF2-SHA256 via
  `werkzeug.security.generate_password_hash` (1M iterations by default).
- **CSRF on every POST** via Flask-WTF, including logout.
- **Anti-enumeration** on `/login` and `/forgot`: identical wording and
  timing whether the username exists or not.
- **Open-redirect guard** on `?next=`: only internal paths are followed.
- **Path-traversal safe** image serving via `send_from_directory`.
- **Extension whitelist** on uploads (PNG, JPG, JPEG, BMP, GIF, TIF,
  TIFF, WEBP). 16 MB hard cap (`MAX_CONTENT_LENGTH`).
- **Deterministic filenames** (`<Prefix>_NNN.<ext>`) with per-project
  prefixes: no cross-project name collisions.
- **Author tampering ignored** &mdash; the server always uses
  `current_user.username`, never the form value.
- **Try/except + rollback** around every `db.session.commit()`; no
  business endpoint can crash on a transient DB error.
- **Fail-soft GLCM** &mdash; a missing or corrupt image yields
  zero-filled features and a log line, never aborts the export.
- **Fail-fast boot** &mdash; the app refuses to start in production if
  `SECRET_KEY` is left at the default.
- **Admin self-protection** &mdash; the last admin cannot demote or
  delete themselves; no self-delete from the panel.
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
