"""
Database configuration and connection management.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from .config import settings

# Get DATABASE_URL from settings (should already be normalized by Pydantic validator)
DATABASE_URL = settings.DATABASE_URL

# If pooled Supabase port 6543 is unreachable in runtime, prefer DIRECT_DATABASE_URL (5432)
# when it is explicitly configured. This keeps production alive during pooler network incidents.
if (
    isinstance(DATABASE_URL, str)
    and ':6543' in DATABASE_URL
    and settings.DIRECT_DATABASE_URL
):
    DATABASE_URL = settings.DIRECT_DATABASE_URL

# Normalize postgres:// to postgresql:// for SQLAlchemy compatibility
# SQLAlchemy expects postgresql:// protocol, but Supabase uses postgres://
# This is a safety check in case the validator didn't run
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    # Log normalization for debugging
    import warnings
    warnings.warn(f"Normalized postgres:// to postgresql:// in DATABASE_URL. Original should have been normalized by validator.")

# Remove pgbouncer=true parameter if present - psycopg2 doesn't recognize it
# Supabase pooled connections just use port 6543, no special parameter needed
if "pgbouncer=true" in DATABASE_URL:
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    parsed = urlparse(DATABASE_URL)
    query_params = parse_qs(parsed.query)
    # Remove pgbouncer parameter
    if "pgbouncer" in query_params:
        del query_params["pgbouncer"]
    # Rebuild query string without pgbouncer
    new_query = urlencode(query_params, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    DATABASE_URL = urlunparse(new_parsed)

# Create engine - connection validation happens on first use, not at import time
# This allows the app to start even if database is temporarily unavailable
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    # SQLite doesn't support connect_timeout; also need to disable thread check
    connect_args["check_same_thread"] = False
else:
    connect_args["connect_timeout"] = 10  # 10 second timeout for Postgres

engine = create_engine(
    DATABASE_URL,  # Use the normalized URL
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Test connections before using them
    echo=settings.DEBUG,
    connect_args=connect_args,
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