from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.csv_utils import build_csv_response
from app.database import get_db
from app.models import Business, Review, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/reviews/by-business")
def reviews_by_business(
    business_id: str = Query(..., description="External Business Id from the CSV"),
    db: Session = Depends(get_db),
):
    """
    Return reviews for a specific business as CSV.
    """
    logger.info("Generating reviews_by_business report", extra={"business_id": business_id})

    business = (
        db.query(Business).filter(Business.id == business_id).one_or_none()
    )
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found")

    q = (
        db.query(Review, User, Business)
        .join(User, Review.user_id == User.id)
        .join(Business, Review.business_id == Business.id)
        .filter(Business.id == business.id)
        .order_by(Review.review_date.desc())
    )

    rows = []
    for review, user, biz in q.all():
        rows.append(
            {
                # Canonical (stable) export schema
                "review_id": review.id,
                "review_title": review.title,
                "review_rating": review.rating,
                "review_content": review.content,
                "review_ip_address": review.ip_address,
                "review_date": review.review_date.isoformat(),
                "reviewer_id": user.id,
                "reviewer_name": user.name,
                "reviewer_country": user.country,
                "business_id": biz.id,
                "business_name": biz.name,
            }
        )

    logger.info(
        "reviews_by_business report generated",
        extra={"business_id": business_id, "row_count": len(rows)},
    )

    fieldnames = [
        "review_id",
        "review_title",
        "review_rating",
        "review_content",
        "review_ip_address",
        "review_date",
        "reviewer_id",
        "reviewer_name",
        "reviewer_country",
        "business_id",
        "business_name",
    ]

    return build_csv_response(rows, fieldnames, filename="reviews_by_business.csv")


@router.get("/reviews/by-user")
def reviews_by_user(
    user_id: str = Query(..., description="External Reviewer Id from the CSV"),
    db: Session = Depends(get_db),
):
    """
    Return reviews written by a specific user as CSV.
    """
    logger.info("Generating reviews_by_user report", extra={"user_id": user_id})

    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    q = (
        db.query(Review, Business)
        .join(Business, Review.business_id == Business.id)
        .filter(Review.user_id == user.id)
        .order_by(Review.review_date.desc())
    )

    rows = []
    for review, biz in q.all():
        rows.append(
            {
                "review_id": review.id,
                "review_title": review.title,
                "review_rating": review.rating,
                "review_content": review.content,
                "review_ip_address": review.ip_address,
                "review_date": review.review_date.isoformat(),
                "reviewer_id": user.id,
                "reviewer_name": user.name,
                # Deliberately exclude email from this export (data minimization)
                "reviewer_country": user.country,
                "business_id": biz.id,
                "business_name": biz.name,
            }
        )

    logger.info(
        "reviews_by_user report generated",
        extra={"user_id": user_id, "row_count": len(rows)},
    )

    fieldnames = [
        "review_id",
        "review_title",
        "review_rating",
        "review_content",
        "review_ip_address",
        "review_date",
        "reviewer_id",
        "reviewer_name",
        "reviewer_country",
        "business_id",
        "business_name",
    ]

    return build_csv_response(rows, fieldnames, filename="reviews_by_user.csv")


@router.get("/users/{user_id}")
def user_account(
    user_id: str,
    db: Session = Depends(get_db),
):
    """
    Return user account information as CSV.
    """
    logger.info("Generating user_account report", extra={"user_id": user_id})

    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    rows = [
        {
            "reviewer_id": user.id,
            "reviewer_name": user.name,
            "reviewer_email": user.email,
            "reviewer_country": user.country,
        }
    ]

    logger.info(
        "user_account report generated",
        extra={"user_id": user_id, "row_count": len(rows)},
    )

    fieldnames = ["reviewer_id", "reviewer_name", "reviewer_email", "reviewer_country"]

    return build_csv_response(rows, fieldnames, filename="user_account.csv")


