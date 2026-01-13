from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    # Source system identifier (Reviewer Id) as primary key.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    # Reviewer name is considered sensitive but not strictly direct PII.
    name: Mapped[str] = mapped_column(String(255))
    # Email is direct PII and would typically be subject to stricter access
    # controls and/or hashing in a production environment.
    email: Mapped[str] = mapped_column(String(255))
    # Country is quasi-identifying and treated as sensitive in a governance
    # context (e.g. for regional policies).
    country: Mapped[str] = mapped_column(String(128))

    reviews: Mapped[list["Review"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Business(Base):
    __tablename__ = "businesses"

    # We use the source system's identifier (Business Id) as the primary key.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    name: Mapped[str] = mapped_column(String(255))

    reviews: Mapped[list["Review"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )


class Review(Base):
    __tablename__ = "reviews"

    # We use the source system's identifier (Review Id) as the primary key.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)

    title: Mapped[str] = mapped_column(String(255))
    rating: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    # IP address is considered PII in many jurisdictions and would normally be
    # masked, anonymised, or heavily access-controlled for compliance.
    ip_address: Mapped[str] = mapped_column(String(64))
    review_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), index=True)
    ingestion_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_runs.id"),
        index=True,
        nullable=True,
    )

    user: Mapped["User"] = relationship(back_populates="reviews")
    business: Mapped["Business"] = relationship(back_populates="reviews")
    ingestion_run: Mapped["IngestionRun"] = relationship(back_populates="reviews")


class IngestionRun(Base):
    """
    Metadata about each ingestion execution.
    """

    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_path: Mapped[str] = mapped_column(String(512))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32))
    rows_read: Mapped[int] = mapped_column(Integer, default=0)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0)

    reviews: Mapped[list["Review"]] = relationship(
        back_populates="ingestion_run",
        cascade="all, delete-orphan",
    )

