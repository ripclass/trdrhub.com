"""
Database Audit Endpoint for Admin/Exporter Dashboard
Verifies all required tables exist.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from ...database import get_db
from ...core.auth import get_current_admin_user
from ...models import User

router = APIRouter(tags=["admin-db"])


@router.get("/db-audit/exporter")
async def audit_exporter_database(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Audit Exporter Dashboard database tables.
    Verifies all required tables exist for LC upload and storage.
    """
    inspector = inspect(db.bind)
    existing_tables = set(inspector.get_table_names())
    
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
    
    results = {
        "status": "ok",
        "database_connected": True,
        "tables": {},
        "missing_tables": [],
        "summary": {
            "total_checked": len(exporter_critical_tables),
            "existing": 0,
            "missing": 0
        },
        "lc_storage": {
            "ready": False,
            "validation_sessions_count": 0,
            "documents_count": 0
        }
    }
    
    # Check each critical table
    for table_name, description in exporter_critical_tables.items():
        exists = table_name in existing_tables
        table_info = {
            "exists": exists,
            "description": description
        }
        
        if exists:
            results["summary"]["existing"] += 1
            # Get table structure
            try:
                columns = inspector.get_columns(table_name)
                table_info["columns"] = len(columns)
                table_info["column_names"] = [c["name"] for c in columns[:10]]  # First 10 columns
                
                # Check foreign keys
                fks = inspector.get_foreign_keys(table_name)
                table_info["foreign_keys"] = len(fks)
                
                # Check indexes
                indexes = inspector.get_indexes(table_name)
                table_info["indexes"] = len(indexes)
            except Exception as e:
                table_info["error"] = str(e)
        else:
            results["summary"]["missing"] += 1
            results["missing_tables"].append(table_name)
            results["status"] = "error"
        
        results["tables"][table_name] = table_info
    
    # Check LC storage capability
    if "validation_sessions" in existing_tables and "documents" in existing_tables:
        try:
            result = db.execute(text("SELECT COUNT(*) FROM validation_sessions"))
            results["lc_storage"]["validation_sessions_count"] = result.fetchone()[0]
            
            result = db.execute(text("SELECT COUNT(*) FROM documents"))
            results["lc_storage"]["documents_count"] = result.fetchone()[0]
            
            results["lc_storage"]["ready"] = True
        except Exception as e:
            results["lc_storage"]["error"] = str(e)
    
    # Overall status
    if results["summary"]["missing"] > 0:
        results["status"] = "error"
        results["message"] = f"Missing {results['summary']['missing']} critical table(s). Run migrations: alembic upgrade head"
    else:
        results["status"] = "ok"
        results["message"] = "All critical tables exist. Exporter Dashboard is ready for LC uploads!"
    
    return results

