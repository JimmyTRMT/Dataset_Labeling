-- Informational reference. The actual database is created automatically
-- by SQLAlchemy on first run via db.create_all() (see backend/app.py).

-- Registered users. Passwords AND security answers are stored as
-- PBKDF2-SHA256 hashes; plain text never touches the database.
CREATE TABLE IF NOT EXISTS users (
    id                    INTEGER       PRIMARY KEY AUTOINCREMENT,
    username              VARCHAR(80)   NOT NULL UNIQUE,
    password_hash         VARCHAR(255)  NOT NULL,
    -- "admin" or "annotator". First registered user is auto-promoted to admin.
    role                  VARCHAR(20)   NOT NULL DEFAULT 'annotator',
    security_question     VARCHAR(255)  NOT NULL,
    security_answer_hash  VARCHAR(255)  NOT NULL,
    created_at            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);


-- One row per annotated image.
CREATE TABLE IF NOT EXISTS images (
    id                          INTEGER       PRIMARY KEY AUTOINCREMENT,
    original_filename           VARCHAR(255)  NOT NULL,
    -- Stored as "<label_folder>/<project_prefix>_NNN.<ext>", e.g.
    -- "Severity_0/Fundus_007.jpg" or "PET/Waste_042.jpg". Pending uploads
    -- live in "_pending/" until they receive a label.
    stored_filename             VARCHAR(255)  NOT NULL UNIQUE,
    -- Project tag drives the label set and the export bucket.
    project                     VARCHAR(50)   NOT NULL DEFAULT 'Fundus',
    -- Captured from current_user.username at annotation time.
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
CREATE INDEX IF NOT EXISTS idx_images_project     ON images(project);
