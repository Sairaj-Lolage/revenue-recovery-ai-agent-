"""
Database engine, session factory, Base, and FastAPI dependency.

DATABASE_URL defaults to a local SQLite file.  Set the environment variable
to point at any SQLAlchemy-compatible database URL.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "sqlite:///./revenue_recovery.db"
)

# SQLite needs connect_args to allow cross-thread usage during FastAPI's
# request handling.  Other databases don't need this flag.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_db():
    """
    Yield a SQLAlchemy session and guarantee it is closed after the request.

    Usage::

        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Initialisation helper
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Create all tables defined on Base.metadata (idempotent)."""
    # Import models here so they register themselves on Base.metadata before
    # create_all is called.
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
