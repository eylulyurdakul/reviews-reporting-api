import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is required. Run via `docker compose up --build` "
        "or set DATABASE_URL to a Postgres URL."
    )

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields a DB session per request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create all tables based on SQLAlchemy models.
    """
    from . import models  # noqa: F401  - ensure models are imported

    _wait_for_db()
    Base.metadata.create_all(bind=engine)


def _wait_for_db(max_wait_seconds: int = 20) -> None:
    """
    Wait for the database to accept connections (for docker-compose startup ordering).
    """
    deadline = time.time() + max_wait_seconds
    last_exc: Exception | None = None

    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # pragma: no cover (varies by environment)
            last_exc = exc
            time.sleep(0.5)

    raise RuntimeError(f"Database not reachable after {max_wait_seconds}s: {last_exc}")


