"""
Database Audit Script for Exporter Dashboard
Verifies all required tables exist and are properly configured.
"""

import sys
import os
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from app.database import engine, Base
# Create a simpler engine for audit (without connect_timeout which psycopg2 doesn't support)
from sqlalchemy import create_engine as create_engine_simple
from app.config import settings
import os

# Create audit engine without problematic parameters
audit_db_url = settings.DATABASE_URL
if audit_db_url.startswith("postgres://"):
    audit_db_url = audit_db_url.replace("postgres://", "postgresql://", 1)

audit_engine = create_engine_simple(
    audit_db_url,
    pool_pre_ping=True,
    echo=False
)
from app.config import settings

# Import all models to ensure they're registered with Base.metadata
from app.models import (
    User, ValidationSession, Document, Discrepancy, Company
)
from app.models.exporter_submission import (
    ExportSubmission, SubmissionEvent, CustomsPack
)
from app.models.lc_versions import LCVersion
from app.models.audit_log import AuditLog

def get_table_names():
    """Get all table names from the database."""
    inspector = inspect(engine)
    return set(inspector.get_table_names())

def get_expected_tables():
    """Get all expected table names from SQLAlchemy models."""
    return set(Base.metadata.tables.keys())

def check_table_exists(table_name: str, existing_tables: set) -> tuple[bool, str]:
    """Check if a table exists and return status."""
    if table_name in existing_tables:
        return True, "[OK] EXISTS"
    return False, "[MISSING]"

def check_foreign_keys(table_name: str, inspector) -> list[dict]:
    """Check foreign key constraints for a table."""
    try:
        fks = inspector.get_foreign_keys(table_name)
        return fks
    except Exception as e:
        return []

def check_indexes(table_name: str, inspector) -> list[dict]:
    """Check indexes for a table."""
    try:
        indexes = inspector.get_indexes(table_name)
        return indexes
    except Exception as e:
        return []

def check_table_structure(table_name: str, inspector) -> dict:
    """Get detailed table structure."""
    try:
        columns = inspector.get_columns(table_name)
        return {
            "columns": len(columns),
            "column_names": [c["name"] for c in columns]
        }
    except Exception as e:
        return {"error": str(e)}

def main():
    """Main audit function."""
    print("=" * 80)
    print("EXPORTER DASHBOARD DATABASE AUDIT")
    print("=" * 80)
    print(f"\nDatabase: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Unknown'}")
    print(f"Environment: {settings.ENVIRONMENT}\n")
    
    try:
        # Test connection
        with audit_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            db_version = result.fetchone()[0]
            print(f"PostgreSQL Version: {db_version.split(',')[0]}\n")
    except Exception as e:
        print(f"[ERROR] Cannot connect to database: {e}\n")
        return False
    
    # Get inspector
    inspector = inspect(audit_engine)
    
    # Core tables needed for Exporter Dashboard
    exporter_critical_tables = {
        "users": "User accounts and authentication",
        "companies": "Company/organization data",
        "validation_sessions": "LC validation sessions (where LCs are stored)",
        "documents": "LC documents and attachments",
        "discrepancies": "Validation results and issues",
        "export_submissions": "Bank submission records",
        "submission_events": "Submission event timeline",
        "customs_packs": "Customs pack generation records",
        "lc_versions": "LC version history",
        "audit_logs": "Audit trail",
    }
    
    # Get existing tables
    existing_tables = get_table_names()
    expected_tables = get_expected_tables()
    
    print("=" * 80)
    print("CRITICAL TABLES FOR EXPORTER DASHBOARD")
    print("=" * 80)
    
    all_ok = True
    missing_tables = []
    
    for table_name, description in exporter_critical_tables.items():
        exists, status = check_table_exists(table_name, existing_tables)
        print(f"\n{table_name.upper()}")
        print(f"  Description: {description}")
        print(f"  Status: {status}")
        
        if exists:
            # Check structure
            structure = check_table_structure(table_name, inspector)
            if "error" not in structure:
                print(f"  Columns: {structure['columns']}")
            
            # Check foreign keys
            fks = check_foreign_keys(table_name, inspector)
            if fks:
                print(f"  Foreign Keys: {len(fks)}")
                for fk in fks[:3]:  # Show first 3
                    print(f"    → {fk['referred_table']}.{fk['referred_columns'][0]}")
            
            # Check indexes
            indexes = check_indexes(table_name, inspector)
            if indexes:
                print(f"  Indexes: {len(indexes)}")
        else:
            all_ok = False
            missing_tables.append(table_name)
            print(f"  [WARNING] CRITICAL: This table is required for Exporter Dashboard!")
    
    print("\n" + "=" * 80)
    print("RELATED TABLES (Supporting Infrastructure)")
    print("=" * 80)
    
    related_tables = {
        "rulesets": "Validation rules",
        "bank_tenants": "Bank organization data",
        "usage_records": "Usage tracking",
        "invoices": "Billing",
        "notification_channels": "Notifications",
    }
    
    for table_name, description in related_tables.items():
        exists, status = check_table_exists(table_name, existing_tables)
        print(f"\n{table_name}: {status}")
        if not exists:
            print(f"  Note: {description} - Optional but recommended")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if all_ok:
        print("\n[SUCCESS] ALL CRITICAL TABLES EXIST")
        print("\nThe Exporter Dashboard database is ready!")
        print("\nYou can safely upload LCs - they will be stored in:")
        print("  - validation_sessions (session metadata)")
        print("  - documents (LC files and attachments)")
        print("  - export_submissions (submission records)")
        print("  - customs_packs (generated customs packs)")
    else:
        print(f"\n[ERROR] MISSING {len(missing_tables)} CRITICAL TABLE(S):")
        for table in missing_tables:
            print(f"  - {table}")
        print("\n[ACTION REQUIRED]")
        print("  Run database migrations to create missing tables:")
        print("  alembic upgrade head")
        return False
    
    # Check for LC storage capability
    print("\n" + "=" * 80)
    print("LC STORAGE VERIFICATION")
    print("=" * 80)
    
    if "validation_sessions" in existing_tables and "documents" in existing_tables:
        try:
            with audit_engine.connect() as conn:
                # Check if tables have data
                result = conn.execute(text("SELECT COUNT(*) FROM validation_sessions"))
                session_count = result.fetchone()[0]
                
                result = conn.execute(text("SELECT COUNT(*) FROM documents"))
                doc_count = result.fetchone()[0]
                
                print(f"\n[SUCCESS] LC Storage Ready")
                print(f"  Validation Sessions: {session_count}")
                print(f"  Documents: {doc_count}")
                print("\n[SUCCESS] You can upload LCs - storage is configured!")
        except Exception as e:
            print(f"\n[WARNING] Could not verify LC storage: {e}")
    
    return all_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

