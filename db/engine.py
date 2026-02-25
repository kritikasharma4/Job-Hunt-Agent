"""
SQLAlchemy engine and session configuration for SQLite.

Provides database connection, session factory, and initialization utilities.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///job_hunt.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all database tables. Safe to call multiple times."""
    from db import models  # noqa: F401 — ensures models are registered
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")


def get_db():
    """Yield a database session. For use as a FastAPI dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
