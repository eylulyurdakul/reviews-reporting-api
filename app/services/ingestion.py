"""
Core ingestion logic for reviews CSV files.
"""

from __future__ import annotations

import csv
import logging
import os
from datetime import datetime, timezone
from typing import Dict

from sqlalchemy.orm import Session

from ..models import Business, IngestionRun, Review, User

logger = logging.getLogger(__name__)


def parse_review_date(value: str) -> datetime:
    """
    Parse the Review Date column into a timezone-aware datetime.
    """
    return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S%z")


def ingest(csv_path: str, db: Session) -> dict:
    """
    Ingest a reviews CSV file into the database.

    Implements:
    - Data quality checks (required IDs, valid rating, valid date)
    - Last Write Wins (LWW) deduplication by Review Date
    - Upsert via db.merge() for idempotent reruns

    Returns a summary dict with row counts and skip reasons.
    """
    # DQ metrics
    rows_read = 0
    rows_skipped = 0
    skip_reasons: Dict[str, int] = {}

    # LWW buffer: maps review_id -> (review_date, row_dict)
    latest_reviews: Dict[str, tuple[datetime, Dict[str, str]]] = {}

    # Create an ingestion run record for lineage
    logger.info("Starting ingestion run", extra={"csv_path": os.path.abspath(csv_path)})
    run = IngestionRun(
        source_path=os.path.abspath(csv_path),
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()

    try:
        with open(csv_path, mode="r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                rows_read += 1

                # DQ Check: Required IDs
                review_id = (row.get("Review Id") or "").strip()
                reviewer_id = (row.get("Reviewer Id") or "").strip()
                business_id = (row.get("Business Id") or "").strip()

                if not review_id or not reviewer_id or not business_id:
                    reason = "missing_ids"
                    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                    rows_skipped += 1
                    continue

                # DQ Check: Valid Rating
                try:
                    rating = int(row.get("Review Rating", ""))
                    if rating < 1 or rating > 5:
                        raise ValueError()
                except (ValueError, TypeError):
                    reason = "invalid_rating"
                    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                    rows_skipped += 1
                    continue

                # DQ Check: Valid Date + LWW Logic
                try:
                    review_date = parse_review_date(row["Review Date"])
                except Exception:
                    reason = "invalid_review_date"
                    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                    rows_skipped += 1
                    continue

                # Last Write Wins: keep the version with the latest timestamp
                if review_id in latest_reviews:
                    existing_date, _ = latest_reviews[review_id]
                    if review_date > existing_date:
                        latest_reviews[review_id] = (review_date, row)
                        reason = "duplicate_superseded_older"
                        skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                    else:
                        reason = "duplicate_ignored_older"
                        skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                        rows_skipped += 1
                else:
                    latest_reviews[review_id] = (review_date, row)

        # Upsert Phase: persist the latest versions to the DB
        rows_inserted = 0
        users_cache: Dict[str, User] = {}
        businesses_cache: Dict[str, Business] = {}

        for review_id, (review_date, row) in latest_reviews.items():
            reviewer_id = row["Reviewer Id"].strip()
            business_id = row["Business Id"].strip()

            # Upsert User
            if reviewer_id not in users_cache:
                user = User(
                    id=reviewer_id,
                    name=row["Reviewer Name"].strip(),
                    email=row["Email Address"].strip(),
                    country=row["Reviewer Country"].strip(),
                )
                user = db.merge(user)
                users_cache[reviewer_id] = user

            # Upsert Business
            if business_id not in businesses_cache:
                business = Business(
                    id=business_id,
                    name=row["Business Name"].strip(),
                )
                business = db.merge(business)
                businesses_cache[business_id] = business

            # Upsert Review
            review = Review(
                id=review_id,
                title=row["Review Title"].strip(),
                rating=int(row["Review Rating"]),
                content=row["Review Content"].strip(),
                ip_address=row["Review IP Address"].strip(),
                review_date=review_date,
                user_id=reviewer_id,
                business_id=business_id,
                ingestion_run_id=run.id,
            )
            db.merge(review)
            rows_inserted += 1

        run.status = "succeeded"
        run.rows_inserted = rows_inserted
        logger.info(
            "Ingestion run succeeded",
            extra={
                "run_id": run.id,
                "rows_read": rows_read,
                "rows_inserted": rows_inserted,
                "rows_skipped": rows_skipped,
            },
        )
    except Exception:
        run.status = "failed"
        logger.exception("Ingestion run failed")
        raise
    finally:
        run.rows_read = rows_read
        run.rows_skipped = rows_skipped
        run.finished_at = datetime.now(timezone.utc)
        db.commit()

    # Return summary dict (used by API)
    return {
        "run_id": run.id,
        "source_path": run.source_path,
        "status": run.status,
        "rows_read": run.rows_read,
        "rows_inserted": run.rows_inserted,
        "rows_skipped": run.rows_skipped,
        "skip_reasons": skip_reasons,
    }

