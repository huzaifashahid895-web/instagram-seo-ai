# backend/app/core/db.py — SQLAlchemy engine and session management
# Cost classification: FREE + OPEN SOURCE

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Create SQLAlchemy engine
# The DATABASE_URL from settings can be either SQLite (for dev) or Postgres (for prod)
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    echo=False,  # Set to True for SQL query logging (debug only)
)

# SessionLocal class for dependency injection
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()


def init_db() -> None:
    """Initialize the database: create all tables defined in models."""
    # Import all models here to ensure they are registered with Base.metadata
    # This is important for Alembic autogenerate to work correctly.
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency that yields a SQLAlchemy session and ensures it is closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()