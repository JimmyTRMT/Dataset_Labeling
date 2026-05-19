# Setup Guide

This guide walks through installing, configuring, and running the **Dataset Labeling Platform** on a local machine, then exposing it to other PCs on the same Wi-Fi.

## Prerequisites

- **Python 3.10** or higher
- **pip** (bundled with Python)
- A terminal (PowerShell on Windows, Terminal on macOS / Linux)
- *Optional:* `git`

## 1. Get the project

```
git clone <repository-url>
cd ModifV1_0_1_Correction
```

Or just copy the folder over to your machine.

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

The project depends on **10 packages**:

- **Flask, Flask-SQLAlchemy, Flask-WTF, SQLAlchemy, Werkzeug** — web framework and database layer.
- **python-dotenv** — reads the `.env` file.
- **gunicorn** — production WSGI server (Linux).
- **waitress** — production WSGI server (Windows-friendly, used by `run_server.py`).
- **scikit-image, opencv-python** — GLCM texture features computed at export time.

## 4. Configure environment variables

```
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the result as the `SECRET_KEY` value in `.env`.

The application **refuses to start** in production mode (`FLASK_DEBUG=false`) if `SECRET_KEY` is left at its default value — this prevents accidentally deploying with a publicly-known signing key.

### Available environment variables

| Variable        | Default                          | Notes                                       |
|-----------------|----------------------------------|---------------------------------------------|
| `SECRET_KEY`    | `dev-change-me-secret`           | Mandatory in production                     |
| `DATABASE_URL`  | `sqlite:///database/dataset.db`  | Any SQLAlchemy URL                          |
| `UPLOAD_FOLDER` | `./data/images`                  | Where uploaded images are stored            |
| `EXPORT_FOLDER` | `./data/exports`                 | Where generated CSV / JSON / HTML files land|
| `FLASK_DEBUG`   | `false`                          | `true` / `1` / `yes` / `on` to enable       |

Both `CamelCase` and `UPPER_SNAKE_CASE` variants are accepted (`SECRET_KEY` or `SecretKey`). Project IDs and label sets are not env-driven; see [`backend/config.py`](../backend/config.py) for `PROJECT_IDS` / `PROJECT_LABELS`.

## 5. Run the application

### Development mode (auto-reload, runs on 127.0.0.1:5000)

```
python -m backend
```

or, equivalently:

```
python -m backend.app
```

Open http://127.0.0.1:5000 in your browser.

### LAN production mode (this PC serves the team on port 8080)

```
python run_server.py
```

The script auto-detects the machine's LAN IPv4 and prints a ready-to-share URL on startup. Other PCs on the same Wi-Fi reach the app at `http://<your-LAN-IP>:8080`.

> **Windows Firewall** prompts the first time. Allow Python on **Private networks** so peer machines can connect. If you'd rather create the rule manually (PowerShell as administrator):
> ```powershell
> New-NetFirewallRule -DisplayName "Dataset Labeling 8080" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow -Profile Private,Domain
> ```

### Real production (Linux, behind nginx / Caddy)

```
gunicorn "backend.app:app" -b 0.0.0.0:8000 -w 4
```

The application does **not** include user authentication. Add a login layer (Flask-Login or an upstream auth gateway) before exposing it to the public internet.

## 6. Adding or editing projects

Project IDs and label sets are hardcoded in [`backend/config.py`](../backend/config.py) (the spec fixes them). To add a third project or edit a label:

```python
PROJECT_TELEMED = "Telemed"
PROJECT_IDS = (PROJECT_DR, PROJECT_SMARTBIN, PROJECT_TELEMED)

PROJECT_LABELS = {
    PROJECT_DR:       ["severity 0", ..., "severity 5"],
    PROJECT_SMARTBIN: ["Can", "Plastic", "Glass", "Cardboard"],
    PROJECT_TELEMED:  ["Normal", "Suspicious", "Pathological"],
}
```

Restart the application. The upload form, dataset filters, and export page all loop over `PROJECT_IDS`, so the new project shows up everywhere automatically.

## Troubleshooting

| Symptom                                                          | Fix                                                                          |
|------------------------------------------------------------------|------------------------------------------------------------------------------|
| `RuntimeError: Refusing to start with the default SecretKey`     | Generate and set a real `SECRET_KEY` in `.env`, or use `FLASK_DEBUG=true` locally |
| `413 Request Entity Too Large`                                   | The upload batch exceeded 16 MB. Upload in smaller batches or raise `MAX_CONTENT_LENGTH` in `backend/config.py` |
| Excel opens the CSV in a single column                           | Re-open the file: *Data → From Text/CSV* and pick `;` as separator. French / Italian / Spanish locales handle the `;` directly; English locales need that one-time pick. |
| Pages don't load on another PC of the same Wi-Fi                 | Windows Firewall is blocking inbound. Add the rule shown in section 5, or check that the network is not using AP-isolation |
| `unable to open database file` on first start                    | The DB path resolved against the wrong folder. `backend/config.py` auto-anchors relative URLs to the project root; verify your custom `DATABASE_URL` is correct |
| GLCM features all zeros for some rows                            | The image file is missing or corrupted on disk. Look under `data/images/`; re-upload if needed |
| Need a clean slate                                               | Stop the app, then `rm database/dataset.db data/images/* data/exports/*` (keep the `.gitkeep` files). The next start recreates an empty database |
