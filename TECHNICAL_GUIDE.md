# Technical Guide

A practical handbook for the **Dataset Labeling Tool** — a small web application that helps a research team upload images, label them, and export everything as CSV, JSON, or a visual HTML file with pre-computed texture features.

This guide is meant for the people who will *use* the tool: researchers, supervisors, and technical reviewers. It avoids developer jargon where it can. Where a technical term is unavoidable (CSV, GLCM, Flask…), a short plain-language explanation comes with it.

---

## Table of contents

1. [Introduction](#1-introduction)
2. [Quick installation](#2-quick-installation)
3. [How the GLCM texture features work](#3-how-the-glcm-texture-features-work)
4. [Maintenance](#4-maintenance)
5. [Appendix — file map](#5-appendix--file-map)

---

## 1. Introduction

### What it does

The application gives a research team **one place** to:

- **Upload** images for two parallel research projects:
  - **DR** — diabetic retinopathy fundus photographs (6 severity grades)
  - **SmartBin** — waste sorting photographs (4 material classes)
- **Label** each image by clicking a button or pressing a number key (`1`–`9`).
- **Browse** the dataset with filters, see who uploaded what, when, and what label it received.
- **Export** the labeled subset of either project, in three formats:
  - **CSV** — 26 columns, semicolon-separated, opens directly in Excel (FR / IT / ES locales) and pandas.
  - **JSON** — same 26 keys, flat structure, ready for any ML library.
  - **HTML** — a single self-contained file showing each image next to its label.
  - The CSV and JSON exports embed **GLCM texture features** for every image as 24 separate columns (see section 3).

### Who it is for

- Researchers labeling data for AI training.
- Supervisors who need to see what was annotated and by whom.
- Reviewers and jury members who want to inspect the pipeline.

### What you need to know to use it

- A web browser.
- Where the team's `.env` secret key is (or how to generate one — see section 2).
- Your name, if you want it recorded as the contributor.

### What is *not* included

- **No login system.** Anyone with network access to the running app can use it.
- **No automatic backup.** Manual backup of `database/dataset.db` and `data/images/` is the team's responsibility (see section 4).
- **No edit-after-the-fact for labels.** Once an image is labeled it stays labeled until deleted or re-uploaded.

---

## 2. Quick installation

### Requirements

- **Python 3.10 or newer**
- **pip** (comes with Python)
- A terminal (PowerShell on Windows, Terminal on macOS/Linux)

### Step-by-step

#### 1. Clone or copy the project folder

```
cd "path/to/your/working/directory"
git clone <your-repo-url>      # or just copy the folder over
cd ModifV1_0_1_Correction
```

#### 2. Create a virtual environment (recommended, keeps dependencies isolated)

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

#### 3. Install the dependencies

```
pip install -r requirements.txt
```

This pulls in 10 packages:

- **Flask, Flask-SQLAlchemy, Flask-WTF, SQLAlchemy, Werkzeug** — the web framework and database layer.
- **python-dotenv** — reads the `.env` file.
- **gunicorn** (Linux) and **waitress** (Windows) — production-grade ways to serve the app.
- **scikit-image, opencv-python** — used to compute the GLCM texture features at export time.

#### 4. Create your local `.env`

```
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the output of the `python -c` command into the `SECRET_KEY=` line in `.env`. The application **refuses to start** in production mode if `SECRET_KEY` is left at the default value — this prevents accidentally deploying with a publicly-known signing key.

For local development, you can set `FLASK_DEBUG=true` instead of supplying a real key.

#### 5. Run the application

For local development:

```
python -m backend
```

For a LAN production deployment on Windows (recommended — exposes the app on every interface, port 8080, with an auto-detected LAN URL printed in the terminal):

```
python run_server.py
```

The script forces `FLASK_DEBUG=false`, starts waitress, and prints both the loopback URL and the LAN URL so colleagues on the same Wi-Fi can connect immediately.

For Linux behind nginx / Caddy:

```
gunicorn "backend.app:app" -b 0.0.0.0:8000 -w 4
```

Open http://127.0.0.1:5000 (dev) or http://127.0.0.1:8080 (run_server.py) in a browser.

### What you should see

A home page titled **Dataset Labeling Tool** with three buttons (Upload, View Dataset, Export) and a summary of how many images you have. From there:

- *Upload* → choose **DR** or **SmartBin**, pick one or several files, click *Upload*.
- *Label* → click a label or press its number key. The tool jumps to the next image automatically.
- *Dataset* → table view, filter by project or by labeling status.
- *Export* → one card per project, each with CSV / JSON / HTML download buttons.

---

## 3. How the GLCM texture features work

### What GLCM is, in plain language

When the application exports a dataset, it adds six numbers per image that describe the **texture** of the photograph — how rough, smooth, or repetitive the pixel patterns are. These numbers come from a classical computer-vision technique called the **GLCM** (Gray-Level Co-occurrence Matrix).

**The simple analogy.** Imagine looking at a photo and counting how often a pixel of brightness `A` is right next to a pixel of brightness `B`. Do that systematically for every pair of brightness values, and you get a table — the co-occurrence matrix. From that table, you can compute summary numbers that say things like "the image has lots of strong contrast" or "neighbouring pixels look alike most of the time".

### Why we include it

For tasks like **diabetic retinopathy grading** and **waste sorting**, classical machine-learning models often work surprisingly well on these texture summaries — sometimes as well as deep learning, with far less data and compute. By writing the features directly into the export, we save the user from re-running an image-processing pipeline before training a model.

### What is computed

For every image, six properties are calculated, each in **four directions**:

| Property        | What it tells you (informally)                              |
|-----------------|-------------------------------------------------------------|
| `contrast`      | How much the brightness changes between neighbouring pixels |
| `dissimilarity` | A linear-scale cousin of contrast (less sensitive to outliers) |
| `homogeneity`   | How "smooth" or uniform the texture is                      |
| `energy`        | How orderly the pixel pattern is                            |
| `correlation`   | How predictable a pixel is from its neighbour               |
| `asm`           | Angular Second Moment — the square of energy, traditionally reported alongside it |

The four directions correspond to checking neighbour pairs at angles **0°, 45°, 90°, 135°**, all at a distance of one pixel. Together they capture how the texture looks when scanned horizontally, vertically, and diagonally.

### How it appears in each export format

The CSV and JSON share **one strict 26-column schema**, in this exact order:

```
img_path,
con1,  con2,  con3,  con4,        # contrast      at 0°, 45°, 90°, 135°
dis1,  dis2,  dis3,  dis4,        # dissimilarity at 0°, 45°, 90°, 135°
hom1,  hom2,  hom3,  hom4,        # homogeneity   at 0°, 45°, 90°, 135°
ene1,  ene2,  ene3,  ene4,        # energy        at 0°, 45°, 90°, 135°
corr1, corr2, corr3, corr4,       # correlation   at 0°, 45°, 90°, 135°
asm1,  asm2,  asm3,  asm4,        # ASM           at 0°, 45°, 90°, 135°
label
```

**CSV** — semicolon-separated, every metric in its own cell. UTF-8 with BOM so Excel reads accented or Thai characters correctly:

```
img_path;con1;con2;con3;con4;dis1;...;asm4;label
data/images/20260507030311_459b956f.jpg;0.0636;0.1307;0.0816;0.1265;0.063;...;0.0607;severity 0
```

**JSON** — array of flat dicts using the same 26 keys, numbers as JSON numbers:

```json
[
    {
        "img_path": "data/images/20260507030311_459b956f.jpg",
        "con1": 0.0636, "con2": 0.1307, "con3": 0.0816, "con4": 0.1265,
        "dis1": 0.063,  "dis2": 0.1289, "dis3": 0.0802, "dis4": 0.1248,
        "hom1": 0.9685, "hom2": 0.9357, "hom3": 0.96,   "hom4": 0.9378,
        "ene1": 0.2621, "ene2": 0.2454, "ene3": 0.2577, "ene4": 0.2464,
        "corr1": 0.9979, "corr2": 0.9957, "corr3": 0.9973, "corr4": 0.9959,
        "asm1": 0.0687, "asm2": 0.0602, "asm3": 0.0664, "asm4": 0.0607,
        "label": "severity 0"
    }
]
```

**HTML** — the visual layout focuses on *image + label* (texture features are not shown).

### What happens when an image is missing or corrupt

If a file referenced by the database is missing on disk, or the file fails to decode, the export does **not** crash. Instead the 24 feature columns of that row are all set to `0.0`, and the rest of the export continues. You can spot affected rows in two ways:

- The 24 GLCM cells (`con1` … `asm4`) are all `0.0`.
- The image cell in the HTML export shows "missing file".

### Where the code lives

The implementation is in [`backend/services/export_service.py`](backend/services/export_service.py):

- `extract_glcm_features(path)` — reads the image (OpenCV), converts it to grayscale, calls `skimage.feature.graycomatrix` and `graycoprops`, and returns a flat dict of 24 keys (`con1` … `asm4`).
- `build_csv_export`, `build_json_export` — emit the 26-column schema. CSV uses `csv.writer(..., delimiter=";")`; JSON keeps the keys flat to mirror the CSV.
- `build_html_export` — the visual gallery, independent of the GLCM pipeline.

---

## 4. Maintenance

This section covers the routine tasks a maintainer will need to perform.

### 4.1 Backing up the dataset

The two pieces of state worth backing up are:

| What                       | Where                       | Notes                                    |
|----------------------------|-----------------------------|------------------------------------------|
| The database               | `database/dataset.db`       | Single SQLite file; copy it while the app is stopped, or use `sqlite3 dataset.db ".backup backup.db"` for a hot copy. |
| The image files            | `data/images/`              | Standard files; copy the whole directory. |

A weekly cron job that zips both into a timestamped archive is usually enough.

### 4.2 Resetting the application to a clean state

To wipe everything (DB rows + image files) and start fresh:

```
# Stop the app first, then:
rm database/dataset.db
rm data/images/*       # keep .gitkeep
rm data/exports/*      # keep .gitkeep
```

The next start will recreate an empty database from the model definition.

### 4.3 Adding a new project

Open [`backend/config.py`](backend/config.py) and edit the two constants near the top:

```python
PROJECT_TELEMED = "Telemed"
PROJECT_IDS = (PROJECT_DR, PROJECT_SMARTBIN, PROJECT_TELEMED)

PROJECT_LABELS = {
    PROJECT_DR:       ["severity 0", ..., "severity 5"],
    PROJECT_SMARTBIN: ["Can", "Plastic", "Glass", "Cardboard"],
    PROJECT_TELEMED:  ["Normal", "Suspicious", "Pathological"],
}
```

Restart the application. The upload form, the dataset filters, and the export page all loop over `PROJECT_IDS`, so the new project shows up everywhere automatically.

### 4.4 Editing the label list of an existing project

Same file, edit the corresponding entry inside `PROJECT_LABELS`. Existing labels stored in the database are unaffected — they remain visible in the dataset table. Newly labeled images use the updated list.

### 4.5 Changing the upload size limit

The 16 MB cap lives in [`backend/config.py`](backend/config.py):

```python
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
```

Adjust the multiplier and restart. The 413 error page (shown when an upload exceeds the cap) updates automatically.

### 4.6 Switching to PostgreSQL

In `.env`:

```
DATABASE_URL=postgresql://user:password@host:5432/dataset_labeling
```

Then `pip install psycopg2-binary`. SQLAlchemy abstracts the dialect, so no code change is needed.

### 4.7 Common problems and fixes

| Symptom                                                     | Likely cause                                            | Fix                                                         |
|-------------------------------------------------------------|---------------------------------------------------------|-------------------------------------------------------------|
| `RuntimeError: Refusing to start with the default SecretKey` | `.env` missing or `SECRET_KEY` left at default          | Generate a key (see section 2 step 4)                       |
| Browser shows "please fill in this field" on SmartBin after picking DR | Stale custom-validity message (already fixed)  | Hard refresh the page (`Ctrl+Shift+R`)                      |
| "No labeled images in DR project yet" when you know there are some | Images are labeled in the *other* project        | Use the project filter on `/dataset` to confirm             |
| Excel shows everything in one column                        | Excel is using `;` as the separator (FR/IT/ES locale)   | Open via *Data → From Text/CSV* and pick comma              |
| 413 page after a big upload                                 | Total size of the batch exceeds 16 MB                   | Upload in smaller batches or change `MAX_CONTENT_LENGTH`    |
| GLCM features are all zeros for some rows                   | Image file is missing or corrupted on disk              | Look for the file under `data/images/`; re-upload if needed |

### 4.8 Updating dependencies

```
pip install --upgrade -r requirements.txt
```

Then run a quick smoke test (section below) to confirm everything still works.

### 4.9 Running a smoke test

After any change to the code or dependencies, verify the basics still respond. From an active virtual environment:

```python
# In a Python shell:
from backend.app import app
client = app.test_client()
for path in ["/", "/upload", "/label", "/dataset", "/export"]:
    print(path, client.get(path).status_code)   # should be 200
```

For exports, check both the HTTP status and the 26-column schema:

```python
import json
data = json.loads(client.get("/export/json?project=DR").data)
if data:
    print("key count:", len(data[0]))                # should be 26
    print("first key:", list(data[0])[0])             # 'img_path'
    print("last key:", list(data[0])[-1])             # 'label'
```

---

## 5. Appendix — file map

For maintainers who want a one-line summary of every file in the repository.

```
ModifV1_0_1_Correction/
├── backend/
│   ├── __init__.py            # marks the package
│   ├── __main__.py            # entry point: `python -m backend`
│   ├── app.py                 # Flask factory, error handlers, home route, local_time filter
│   ├── config.py              # env-driven settings, project IDs, label sets, timezone
│   ├── routes/
│   │   ├── upload.py          # /upload (page + POST), /images/<filename>
│   │   ├── label.py           # /label, /label/<id>, /label/<id>/delete, /dataset
│   │   └── export.py          # /export, /export/csv, /export/json, /export/html
│   ├── models/
│   │   └── database.py        # SQLAlchemy + ImageRecord (one table)
│   └── services/
│       ├── image_service.py   # upload validation + persistence + safe deletion
│       └── export_service.py  # CSV / JSON / HTML builders + GLCM extraction
│
├── frontend/
│   ├── templates/             # base.html, index.html, upload.html, label.html, dashboard.html, export.html, errors/
│   └── static/
│       ├── css/app.css        # custom styles on top of Tailwind (image viewer, label-card states)
│       └── js/                # labeling.js (zoom/pan/rotate), upload.js (dropzone), dataset.js
│
├── database/
│   ├── schema.sql             # reference SQL (informational)
│   └── dataset.db             # runtime DB, gitignored
│
├── data/
│   ├── images/                # uploaded files, gitignored
│   └── exports/               # generated CSV / JSON / HTML, gitignored
│
├── docs/
│   ├── architecture.md        # short architecture overview
│   ├── setup.md               # alternative install walk-through
│   └── screenshots/           # UI captures for the report
│
├── run_server.py              # LAN production launcher (waitress + auto-IP)
├── requirements.txt           # 10 pinned dependencies
├── README.md                  # quick start + features
├── TECHNICAL_GUIDE.md         # this file
├── .env.example               # template for local secrets
├── .env                       # local secrets, gitignored
└── .gitignore
```

### Routes at a glance

| Method | Path                  | What it does                                      |
|--------|-----------------------|---------------------------------------------------|
| GET    | `/`                   | Home page with summary                            |
| GET    | `/upload`             | Upload form                                       |
| POST   | `/upload`             | Process an upload (validates project, saves files)|
| GET    | `/images/<filename>`  | Serve a stored image (path-traversal safe)        |
| GET    | `/label`              | Labeling page (current image + buttons)           |
| POST   | `/label/<id>`         | Record a label, jump to next image                |
| POST   | `/label/<id>/delete`  | Remove an image (file + DB row)                   |
| GET    | `/dataset`            | Dataset table with filters                        |
| GET    | `/export`             | Export page                                       |
| GET    | `/export/csv`         | CSV download — 26 columns, `;` delimiter          |
| GET    | `/export/json`        | JSON download — same 26 keys, flat structure      |
| GET    | `/export/html`        | Self-contained HTML preview (image \| label)      |
