-- This file is informational. The actual database is created automatically
-- by SQLAlchemy on first run via db.create_all() (see backend/app.py).

CREATE TABLE IF NOT EXISTS images (
    id                          INTEGER       PRIMARY KEY AUTOINCREMENT,
    original_filename           VARCHAR(255)  NOT NULL,
    -- Stored as "<label_folder>/<project_prefix>_NNN.<ext>", e.g.
    -- "Severity_0/Fundus_007.jpg" or "PET/Waste_042.jpg".
    stored_filename             VARCHAR(255)  NOT NULL UNIQUE,
    -- Project tag drives the label set and the export bucket.
    project                     VARCHAR(50)   NOT NULL DEFAULT 'Fundus',
    contributor                 VARCHAR(100),
    notes                       TEXT,
    label                       VARCHAR(100),
    status                      VARCHAR(20)   NOT NULL DEFAULT 'labeled',
    uploaded_at                 DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    labeled_at                  DATETIME,
    last_viewed_at              DATETIME,
    labeling_duration_seconds   FLOAT
);

CREATE INDEX IF NOT EXISTS idx_images_status      ON images(status);
CREATE INDEX IF NOT EXISTS idx_images_uploaded_at ON images(uploaded_at);
CREATE INDEX IF NOT EXISTS idx_images_label       ON images(label);
CREATE INDEX IF NOT EXISTS idx_images_project     ON images(project);
