import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db, init_db
from .routers import ingest, reports

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    """
    # Startup
    logger.info("Initialising database schema (startup)")
    init_db()
    yield
    # Shutdown (nothing needed here)


app = FastAPI(title="Reviews Reporting API", lifespan=lifespan)


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Simple health endpoint that also validates DB connectivity.
    """
    # A lightweight no-op query to ensure the session is usable.
    db.execute(text("SELECT 1"))
    logger.info("Health check OK")
    return {"status": "ok"}


app.include_router(reports.router)
app.include_router(ingest.router)
