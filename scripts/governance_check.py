"""
Governance check script - validates that all database columns are classified.

Usage:
    python scripts/governance_check.py

Returns exit code 0 if all columns are classified, 1 otherwise.
This can be used as a CI gate to ensure governance compliance.
"""

import sys
from sqlalchemy import inspect

from app.database import engine, init_db
from app.classification import COLUMN_CLASSIFICATION, DataClassification


def check_all_columns_classified() -> tuple[bool, list[str]]:
    """
    Check that every column in the database has a classification.
    
    Returns:
        (success, list of unclassified columns)
    """
    init_db()
    inspector = inspect(engine)
    
    unclassified = []
    
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        for col in columns:
            col_name = col["name"]
            key = (table_name, col_name)
            if key not in COLUMN_CLASSIFICATION:
                unclassified.append(f"{table_name}.{col_name}")
    
    return len(unclassified) == 0, unclassified


def check_pii_columns_documented() -> tuple[bool, list[str]]:
    """
    Check that all PII columns exist in the actual schema.
    (Catches stale classifications for removed columns)
    """
    init_db()
    inspector = inspect(engine)
    
    # Get all actual columns
    actual_columns = set()
    for table_name in inspector.get_table_names():
        for col in inspector.get_columns(table_name):
            actual_columns.add((table_name, col["name"]))
    
    # Check for stale classifications
    stale = []
    for (table, col), classification in COLUMN_CLASSIFICATION.items():
        if (table, col) not in actual_columns:
            stale.append(f"{table}.{col}")
    
    return len(stale) == 0, stale


def main() -> int:
    print("Running governance checks...")
    all_passed = True

    # Check 1: All columns classified
    success, unclassified = check_all_columns_classified()
    if success:
        print("OK: all DB columns are classified")
    else:
        print("FAIL: unclassified columns found:")
        for col in unclassified:
            print(f"    - {col}")
        all_passed = False
    
    # Check 2: No stale classifications
    success, stale = check_pii_columns_documented()
    if success:
        print("OK: no stale classifications")
    else:
        print("FAIL: classifications for non-existent columns:")
        for col in stale:
            print(f"    - {col}")
        all_passed = False
    
    if all_passed:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())

