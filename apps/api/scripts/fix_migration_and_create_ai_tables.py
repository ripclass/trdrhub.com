#!/usr/bin/env python3
"""
Fix broken Alembic migration chain and create AI usage tables directly.

This script:
1. Checks current Alembic version in database
2. Creates AI usage tables if they don't exist
3. Stamps the database with the correct migration version

Run this from apps/api directory:
    python scripts/fix_migration_and_create_ai_tables.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

def get_database_url():
    """Get database URL, preferring DIRECT_DATABASE_URL for migrations."""
    db_url = os.getenv("DIRECT_DATABASE_URL") or os.getenv("DATABASE_URL") or settings.DATABASE_URL
    
    # Normalize postgres:// to postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    return db_url

def check_tables_exist(engine):
    """Check if AI tables already exist."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('ai_usage_records', 'ai_assist_events')
        """))
        existing = [row[0] for row in result]
        return 'ai_usage_records' in existing, 'ai_assist_events' in existing

def create_ai_tables(engine):
    """Create AI usage tables directly."""
    sql = """
    -- Create ai_usage_records table
    CREATE TABLE IF NOT EXISTS ai_usage_records (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id UUID NOT NULL REFERENCES companies(id),
        user_id UUID REFERENCES users(id),
        validation_session_id UUID REFERENCES validation_sessions(id),
        feature VARCHAR(50) NOT NULL,
        tokens_in INTEGER NOT NULL DEFAULT 0,
        tokens_out INTEGER NOT NULL DEFAULT 0,
        estimated_cost_usd VARCHAR(64),
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
    );

    -- Create indexes for ai_usage_records
    CREATE INDEX IF NOT EXISTS ix_ai_usage_records_tenant_id ON ai_usage_records(tenant_id);
    CREATE INDEX IF NOT EXISTS ix_ai_usage_records_user_id ON ai_usage_records(user_id);
    CREATE INDEX IF NOT EXISTS ix_ai_usage_records_validation_session_id ON ai_usage_records(validation_session_id);

    -- Create ai_assist_events table
    CREATE TABLE IF NOT EXISTS ai_assist_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id UUID NOT NULL REFERENCES validation_sessions(id),
        user_id UUID NOT NULL REFERENCES users(id),
        company_id UUID NOT NULL REFERENCES companies(id),
        output_type VARCHAR(50) NOT NULL,
        confidence_level VARCHAR(20) NOT NULL,
        language VARCHAR(5) NOT NULL,
        model_version VARCHAR(50) NOT NULL,
        input_data JSONB NOT NULL,
        ai_output TEXT NOT NULL,
        fallback_used BOOLEAN NOT NULL DEFAULT false,
        tokens_in INTEGER,
        tokens_out INTEGER,
        estimated_cost_usd VARCHAR(64),
        lc_session_id UUID REFERENCES validation_sessions(id),
        rule_references JSONB,
        prompt_template_id VARCHAR(100) NOT NULL,
        processing_time_ms INTEGER NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
    );

    -- Create indexes for ai_assist_events
    CREATE INDEX IF NOT EXISTS ix_ai_assist_events_session_id ON ai_assist_events(session_id);
    CREATE INDEX IF NOT EXISTS ix_ai_assist_events_user_id ON ai_assist_events(user_id);
    CREATE INDEX IF NOT EXISTS ix_ai_assist_events_company_id ON ai_assist_events(company_id);
    """
    
    with engine.begin() as conn:
        conn.execute(text(sql))
        print("✅ AI usage tables created successfully")

def get_current_alembic_version(engine):
    """Get current Alembic version from database."""
    with engine.connect() as conn:
        try:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            return row[0] if row else None
        except Exception as e:
            print(f"⚠️  Could not read alembic_version: {e}")
            return None

def stamp_alembic_version(engine, version):
    """Stamp database with Alembic version."""
    with engine.begin() as conn:
        # Check if alembic_version table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'alembic_version'
            )
        """))
        table_exists = result.scalar()
        
        if not table_exists:
            print("⚠️  alembic_version table doesn't exist, creating it...")
            conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"))
        
        # Insert or update version
        conn.execute(text("""
            INSERT INTO alembic_version (version_num) 
            VALUES (:version)
            ON CONFLICT (version_num) DO UPDATE SET version_num = :version
        """), {"version": version})
        print(f"✅ Stamped database with version: {version}")

def main():
    print("🔧 Fixing migration chain and creating AI usage tables...")
    print()
    
    db_url = get_database_url()
    print(f"📊 Connecting to database...")
    
    engine = create_engine(db_url)
    
    # Check current version
    current_version = get_current_alembic_version(engine)
    print(f"📌 Current Alembic version: {current_version or 'None'}")
    print()
    
    # Check if tables exist
    usage_exists, events_exists = check_tables_exist(engine)
    print(f"📋 Tables status:")
    print(f"   - ai_usage_records: {'✅ exists' if usage_exists else '❌ missing'}")
    print(f"   - ai_assist_events: {'✅ exists' if events_exists else '❌ missing'}")
    print()
    
    if usage_exists and events_exists:
        print("✅ AI tables already exist!")
        # Still stamp the version to fix the chain
        stamp_alembic_version(engine, "20251116_add_ai_usage_and_events")
        print("✅ Migration version stamped")
        return
    
    # Create tables
    print("🔨 Creating AI usage tables...")
    create_ai_tables(engine)
    
    # Stamp version
    print()
    print("📝 Stamping database with migration version...")
    stamp_alembic_version(engine, "20251116_add_ai_usage_and_events")
    
    print()
    print("✅ Done! AI usage tables created and migration version stamped.")
    print()
    print("💡 You can now try running 'alembic upgrade head' again,")
    print("   or continue using the application - AI logging should work now.")

if __name__ == "__main__":
    main()

