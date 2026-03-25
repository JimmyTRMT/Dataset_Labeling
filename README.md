# Image Labeling Platform (Flask)

Lightweight web platform to build labeled image datasets for AI research workflows.
It supports session-based annotation, keyboard-driven labeling, and export-ready CSV files.

## Project Overview

This application helps researchers and engineers:
- Upload image batches.
- Create labeling sessions with custom binary labels.
- Annotate quickly with UI buttons or keyboard shortcuts.
- Track progress and productivity with dashboard metrics.
- Export datasets in two formats (full metadata vs AI-ready minimal format).

## Tech Stack

- Backend: Flask
- ORM / Database: Flask-SQLAlchemy + SQLite
- Frontend: Bootstrap 5 + modular frontend architecture
  - HTML templates for structure
  - Dedicated CSS in `static/css/app.css` for styling
  - Vanilla JavaScript modules in `static/js/` for behavior
- Charts: Chart.js

## Project Structure

ProjetThailand/
  app/
    __init__.py
    __main__.py
    config.py
    error_handlers.py
    models.py
    blueprints/
      api.py
      main.py
    services/
      export_service.py
      image_service.py
  templates/
    errors/
      404.html
      500.html
    dashboard.html
    history.html
    index.html
  static/
    css/
      app.css
    js/
      labeling.js
      history.js
      charts.js
  scripts/
    seed_demo_data.py
  uploads/
  exports/
  requirements.txt

## Setup Instructions

### 1) Create a virtual environment

python -m venv .venv

### 2) Activate it

`.\.venv\Scripts\Activate.ps1`

### 3) Install dependencies

pip install -r requirements.txt

### 4) Run the application

python -m app

Open http://127.0.0.1:5000 in your browser.

## Workflow Guide

### Session concept

A **session** groups uploaded images and keeps a dedicated pair of labels (Label 1 / Label 2).
You can either:
- Create a new session.
- Append images to an existing session from the History page.

### Labeling process

On the Labeling page:
- Use the two main action buttons to assign labels.
- Press keyboard shortcuts:
  - `1` → Label 1
  - `2` → Label 2
- Enable or disable auto-advance depending on your review strategy.

### Export formats

Two export formats are available:
- **Full Dataset**: complete metadata (`id`, original/stored file names, session, labels, timestamps, status).
- **AI Dataset**: minimal training-ready schema (`filename`, `label`).

Exports are available globally or per session.

## Dashboard

The Dashboard includes:
- Label distribution (pie chart)
- Labels per day (bar chart)
- Average labeling time per image

## Optional Demo Data

Generate sample records for quick dashboard testing:

python scripts/seed_demo_data.py

Examples:

python scripts/seed_demo_data.py --count 10
python scripts/seed_demo_data.py --reset --count 12

## Configuration

Optional environment variables:
- `SECRET_KEY`
- `DATABASE_URL`
- `UPLOAD_FOLDER`
- `EXPORT_FOLDER`
- `FLASK_DEBUG`
