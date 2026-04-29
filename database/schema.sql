-- Dataset Labeling Tool - SQLite schema
-- This file is informational. The actual database is created automatically
-- by SQLAlchemy on first run via db.create_all() (see backend/app.py).
-- It is provided here as a reference for reviewers and other database engines.

CREATE TABLE IF NOT EXISTS images (
    id                          INTEGER       PRIMARY KEY AUTOINCREMENT,
    original_filename           VARCHAR(255)  NOT NULL,
    stored_filename             VARCHAR(255)  NOT NULL UNIQUE,
    contributor                 VARCHAR(100),
    notes                       TEXT,
    label                       VARCHAR(100),
    status                      VARCHAR(20)   NOT NULL DEFAULT 'unlabeled',
    uploaded_at                 DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    labeled_at                  DATETIME,
    last_viewed_at              DATETIME,
    labeling_duration_seconds   FLOAT
);

CREATE INDEX IF NOT EXISTS idx_images_status      ON images(status);
CREATE INDEX IF NOT EXISTS idx_images_uploaded_at ON images(uploaded_at);
CREATE INDEX IF NOT EXISTS idx_images_label       ON images(label);
