# Seed demo records for quick dashboard testing.

from __future__ import annotations

import argparse
import random
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.models import ImageRecord, db

logging.basicConfig(level=logging.INFO, format="%(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Insert demo entries into the SQLite database.")
    parser.add_argument("--count", type=int, default=8, help="Number of demo entries to generate (default: 8).")
    parser.add_argument("--reset", action="store_true", help="Delete existing entries before generation.")
    return parser.parse_args()


def seed_demo_data(count: int, reset: bool) -> None:
    app = create_app()
    with app.app_context():
        if reset:
            ImageRecord.query.delete()
            db.session.commit()

        labels_pool = ["labelOne", "labelTwo"]
        now = datetime.now()
        uploads_dir = Path(app.config["UPLOAD_FOLDER"])

        records: list[ImageRecord] = []
        for index in range(count):
            label_value = random.choice(labels_pool)
            days_ago = random.randint(0, 6)
            uploaded_at = now - timedelta(days=days_ago, minutes=random.randint(10, 500))
            labeled_at = uploaded_at + timedelta(seconds=random.randint(20, 180))
            duration = (labeled_at - uploaded_at).total_seconds()

            stored_name = f"demo_{index + 1:03d}.jpg"
            fake_path = uploads_dir / stored_name

            records.append(
                ImageRecord(
                    original_filename=stored_name,
                    stored_filename=f"demo_{index + 1:03d}_{random.randint(1000, 9999)}.jpg",
                    file_path=str(fake_path),
                    uploaded_at=uploaded_at,
                    labeled_at=labeled_at,
                    last_viewed_at=None,
                    labeling_duration_seconds=duration,
                    label=label_value,
                    status="labeled",
                )
            )

        db.session.add_all(records)
        db.session.commit()

        total = ImageRecord.query.count()
        labeled = ImageRecord.query.filter_by(status="labeled").count()
        logging.info(f" Generated data: {len(records)} entries")
        logging.info(f" Current database: total={total}, labeled={labeled}")
        logging.info(" Open /dashboard to view the charts.")


def main() -> None:
    args = parse_args()
    count = max(1, args.count)
    seed_demo_data(count=count, reset=args.reset)


if __name__ == "__main__":
    main()
