"""
Database configuration and connection management.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from .config import settings

DATABASE_URL = settings.DATABASE_URL

# Normalize postgres:// to postgresql:// for SQLAlchemy compatibility
# SQLAlchemy expects postgresql:// protocol, but Supabase uses postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine - connection validation happens on first use, not at import time
# This allows the app to start even if database is temporarily unavailable
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Test connections before using them
    echo=settings.DEBUG,
    connect_args={"connect_timeout": 10},  # 10 second timeout for connection attempts
    pool_reset_on_return='commit'  # Reset connections when returned to pool
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Database dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()