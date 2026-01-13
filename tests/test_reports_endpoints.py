from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine, init_db
from app.main import app
from app.models import Business, Review, User
from datetime import datetime, timezone


def setup_module(module):
    # Reset the schema to ensure deterministic results.
    Base.metadata.drop_all(bind=engine)
    init_db()

    db = SessionLocal()
    try:
        user = User(
            id="user-1",
            name="Test User",
            email="test@example.com",
            country="Testland",
        )
        business = Business(
            id="biz-1",
            name="Test Business",
        )
        review = Review(
            id="rev-1",
            title="Great",
            rating=5,
            content="Very good",
            ip_address="127.0.0.1",
            review_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            user=user,
            business=business,
        )
        db.add_all([user, business, review])
        db.commit()
    finally:
        db.close()


client = TestClient(app)


def test_reviews_by_business_endpoint():
    resp = client.get("/reports/reviews/by-business", params={"business_id": "biz-1"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    body = resp.text
    assert "rev-1" in body
    assert "Test Business" in body
    assert "review_id" in body


def test_reviews_by_user_endpoint():
    resp = client.get("/reports/reviews/by-user", params={"user_id": "user-1"})
    assert resp.status_code == 200
    body = resp.text
    assert "rev-1" in body
    assert "biz-1" in body
    assert "Test User" in body
    assert "reviewer_name" in body


def test_user_account_endpoint():
    resp = client.get("/reports/users/user-1")
    assert resp.status_code == 200
    body = resp.text
    assert "Test User" in body
    assert "test@example.com" in body
    assert "reviewer_email" in body


