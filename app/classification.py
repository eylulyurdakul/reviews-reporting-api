"""
Data classification labels for governance.

Reason: Explicit classification of columns enables governance checks,
audit reports, and policy enforcement (e.g., masking PII for non-Legal roles).
"""

from __future__ import annotations

from enum import Enum


class DataClassification(str, Enum):
    """
    Simple data classification scheme.
    """
    PII = "pii"
    SENSITIVE = "sensitive"
    NON_SENSITIVE = "non_sensitive"


# Classification for each column in the normalized database schema.
# This is used by governance checks to ensure all columns are classified.
COLUMN_CLASSIFICATION: dict[tuple[str, str], DataClassification] = {
    # users table
    ("users", "id"): DataClassification.NON_SENSITIVE,
    ("users", "name"): DataClassification.SENSITIVE,
    ("users", "email"): DataClassification.PII,
    ("users", "country"): DataClassification.SENSITIVE,
    # businesses table
    ("businesses", "id"): DataClassification.NON_SENSITIVE,
    ("businesses", "name"): DataClassification.NON_SENSITIVE,
    # reviews table
    ("reviews", "id"): DataClassification.NON_SENSITIVE,
    ("reviews", "title"): DataClassification.NON_SENSITIVE,
    ("reviews", "rating"): DataClassification.NON_SENSITIVE,
    ("reviews", "content"): DataClassification.NON_SENSITIVE,
    ("reviews", "ip_address"): DataClassification.PII,
    ("reviews", "review_date"): DataClassification.NON_SENSITIVE,
    ("reviews", "user_id"): DataClassification.NON_SENSITIVE,
    ("reviews", "business_id"): DataClassification.NON_SENSITIVE,
    ("reviews", "ingestion_run_id"): DataClassification.NON_SENSITIVE,
    # ingestion_runs table (metadata, not user data)
    ("ingestion_runs", "id"): DataClassification.NON_SENSITIVE,
    ("ingestion_runs", "source_path"): DataClassification.NON_SENSITIVE,
    ("ingestion_runs", "started_at"): DataClassification.NON_SENSITIVE,
    ("ingestion_runs", "finished_at"): DataClassification.NON_SENSITIVE,
    ("ingestion_runs", "status"): DataClassification.NON_SENSITIVE,
    ("ingestion_runs", "rows_read"): DataClassification.NON_SENSITIVE,
    ("ingestion_runs", "rows_inserted"): DataClassification.NON_SENSITIVE,
    ("ingestion_runs", "rows_skipped"): DataClassification.NON_SENSITIVE,
}


def get_pii_columns() -> list[tuple[str, str]]:
    """Return all columns classified as PII."""
    return [
        (table, col)
        for (table, col), classification in COLUMN_CLASSIFICATION.items()
        if classification == DataClassification.PII
    ]


def get_sensitive_columns() -> list[tuple[str, str]]:
    """Return all columns classified as SENSITIVE or PII."""
    return [
        (table, col)
        for (table, col), classification in COLUMN_CLASSIFICATION.items()
        if classification in (DataClassification.PII, DataClassification.SENSITIVE)
    ]

