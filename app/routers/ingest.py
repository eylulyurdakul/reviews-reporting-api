"""
Ingestion endpoint for uploading new CSV files.
"""

import logging
import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.ingestion import ingest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("")
def ingest_csv(
    file: UploadFile = File(..., description="Reviews CSV file to ingest"),
    db: Session = Depends(get_db),
):
    """
    Ingest a reviews CSV file into the database.

    This endpoint accepts a CSV file upload, validates the data, applies
    Last Write Wins (LWW) deduplication, and upserts the records into
    users, businesses, and reviews tables.

    Returns a summary with row counts and any skip reasons.
    """
    # Validate file type
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV file (.csv extension required)",
        )

    logger.info(f"Received CSV upload: {file.filename}")

    # Save uploaded file to a temp location
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".csv", delete=False
        ) as tmp:
            content = file.file.read()
            tmp.write(content)
            tmp_path = tmp.name

        logger.info(f"Saved upload to temp file: {tmp_path}")

        # Run ingestion using the existing function
        summary = ingest(tmp_path, db)

        logger.info(
            f"Ingestion completed: rows_inserted={summary['rows_inserted']}, "
            f"rows_skipped={summary['rows_skipped']}"
        )

        return summary

    except Exception as e:
        logger.exception("Ingestion failed")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

