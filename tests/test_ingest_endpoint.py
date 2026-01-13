"""
Tests for the POST /ingest endpoint.
"""

import io
from fastapi.testclient import TestClient

from app.database import Base, engine, init_db
from app.main import app


def setup_module(module):
    """Reset DB for clean test state."""
    Base.metadata.drop_all(bind=engine)
    init_db()


client = TestClient(app)


def test_ingest_valid_csv():
    """Test ingesting a valid CSV file."""
    csv_content = """Review Id,Reviewer Id,Business Id,Reviewer Name,Email Address,Reviewer Country,Business Name,Review Title,Review Rating,Review Content,Review IP Address,Review Date
rev-100,user-100,biz-100,Test User,test@example.com,Testland,Test Biz,Great product,5,Loved it,1.2.3.4,2024-01-15 10:00:00+0000
rev-101,user-100,biz-100,Test User,test@example.com,Testland,Test Biz,Good service,4,Nice,1.2.3.4,2024-01-16 10:00:00+0000
"""
    
    response = client.post(
        "/ingest",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "succeeded"
    assert data["rows_read"] == 2
    assert data["rows_inserted"] == 2
    assert data["rows_skipped"] == 0


def test_ingest_with_duplicates_lww():
    """Test that Last Write Wins works for duplicate Review IDs."""
    # Same review_id, different dates - should keep the newer one
    csv_content = """Review Id,Reviewer Id,Business Id,Reviewer Name,Email Address,Reviewer Country,Business Name,Review Title,Review Rating,Review Content,Review IP Address,Review Date
rev-200,user-200,biz-200,User A,a@example.com,USA,Biz A,Old review,3,Old content,1.1.1.1,2024-01-01 10:00:00+0000
rev-200,user-200,biz-200,User A,a@example.com,USA,Biz A,New review,5,New content,1.1.1.1,2024-02-01 10:00:00+0000
"""
    
    response = client.post(
        "/ingest",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["rows_read"] == 2
    assert data["rows_inserted"] == 1  # Only one unique review after LWW
    assert "duplicate_ignored_older" in data["skip_reasons"] or "duplicate_superseded_older" in data["skip_reasons"]


def test_ingest_invalid_file_type():
    """Test that non-CSV files are rejected."""
    response = client.post(
        "/ingest",
        files={"file": ("test.txt", io.BytesIO(b"not a csv"), "text/plain")},
    )
    
    assert response.status_code == 400
    assert "CSV" in response.json()["detail"]


def test_ingest_with_invalid_rating():
    """Test that invalid ratings are skipped."""
    csv_content = """Review Id,Reviewer Id,Business Id,Reviewer Name,Email Address,Reviewer Country,Business Name,Review Title,Review Rating,Review Content,Review IP Address,Review Date
rev-300,user-300,biz-300,User,u@example.com,USA,Biz,Title,6,Content,1.1.1.1,2024-01-01 10:00:00+0000
"""
    
    response = client.post(
        "/ingest",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["rows_skipped"] == 1
    assert data["skip_reasons"].get("invalid_rating") == 1


def test_ingest_empty_csv():
    """Test ingesting a CSV with only headers (no data rows)."""
    csv_content = """Review Id,Reviewer Id,Business Id,Reviewer Name,Email Address,Reviewer Country,Business Name,Review Title,Review Rating,Review Content,Review IP Address,Review Date
"""
    
    response = client.post(
        "/ingest",
        files={"file": ("empty.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["rows_read"] == 0
    assert data["rows_inserted"] == 0


def test_ingest_missing_required_ids():
    """Test that rows with missing required IDs are skipped."""
    csv_content = """Review Id,Reviewer Id,Business Id,Reviewer Name,Email Address,Reviewer Country,Business Name,Review Title,Review Rating,Review Content,Review IP Address,Review Date
,user-400,biz-400,User,u@example.com,USA,Biz,Title,5,Content,1.1.1.1,2024-01-01 10:00:00+0000
rev-401,,biz-400,User,u@example.com,USA,Biz,Title,5,Content,1.1.1.1,2024-01-01 10:00:00+0000
rev-402,user-400,,User,u@example.com,USA,Biz,Title,5,Content,1.1.1.1,2024-01-01 10:00:00+0000
"""
    
    response = client.post(
        "/ingest",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["rows_read"] == 3
    assert data["rows_skipped"] == 3
    assert data["skip_reasons"].get("missing_ids") == 3


def test_ingest_invalid_date():
    """Test that rows with invalid dates are skipped."""
    csv_content = """Review Id,Reviewer Id,Business Id,Reviewer Name,Email Address,Reviewer Country,Business Name,Review Title,Review Rating,Review Content,Review IP Address,Review Date
rev-500,user-500,biz-500,User,u@example.com,USA,Biz,Title,5,Content,1.1.1.1,not-a-date
"""
    
    response = client.post(
        "/ingest",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["rows_skipped"] == 1
    assert data["skip_reasons"].get("invalid_review_date") == 1


def test_ingest_idempotent():
    """Test that re-ingesting the same data doesn't create duplicates."""
    csv_content = """Review Id,Reviewer Id,Business Id,Reviewer Name,Email Address,Reviewer Country,Business Name,Review Title,Review Rating,Review Content,Review IP Address,Review Date
rev-600,user-600,biz-600,User,u@example.com,USA,Biz,Title,5,Content,1.1.1.1,2024-01-01 10:00:00+0000
"""
    
    # First ingestion
    response1 = client.post(
        "/ingest",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert response1.status_code == 200
    assert response1.json()["rows_inserted"] == 1
    
    # Second ingestion (same data) - should still succeed, upsert handles it
    response2 = client.post(
        "/ingest",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert response2.status_code == 200
    assert response2.json()["rows_inserted"] == 1  # Upsert counts as "inserted"

