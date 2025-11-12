import os
from typing import Optional
from supabase import create_client, Client
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Database URL for SQLAlchemy
DATABASE_URL = os.getenv("DATABASE_URL") or f"postgresql://postgres:{os.getenv('SUPABASE_DB_PASSWORD')}@{os.getenv('SUPABASE_DB_HOST')}:5432/postgres"

# Create Supabase client only if URL and key are configured
supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        # If Supabase is not configured, continue without it
        supabase = None

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Supabase Auth helper
def get_current_user(token: str):
    if supabase is None:
        return None
    try:
        user = supabase.auth.get_user(token)
        return user
    except Exception as e:
        return None

