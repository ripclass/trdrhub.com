"""
Bank-facing API endpoints for portfolio visibility and governance.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, cast, case
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB
import asyncio
import json
import secrets
import time

from ..core.security import require_bank_or_admin
from ..database import get_db, SessionLocal
from ..models import User, ValidationSession, SessionStatus, UsageAction
from ..services.analytics_service import AnalyticsService
from ..services.entitlements import EntitlementService, EntitlementError
from ..services import ValidationSessionService
from ..services.validator import validate_document
from ..middleware.bank_rate_limit import bank_rate_limit
from ..services.audit_service import AuditService
from ..middleware.audit_middleware import create_audit_context
from ..models.audit_log import AuditAction, AuditResult
from ..config import settings
from ..utils.token_utils import create_signed_token, verify_signed_token
from ..utils.bulk_zip_processor import extract_and_detect_lc_sets
from ..utils.file_validation import validate_upload_file
import logging

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/bank", tags=["bank"])


def _resolve_bank_scope(request: Request) -> tuple[str, List[str]]:
    bank_id = getattr(request.state, "bank_id", None)
    tenant_ids = getattr(request.state, "tenant_ids", None)

    if not bank_id:
        raise HTTPException(status_code=403, detail="Bank scope could not be resolved for this request.")

    if tenant_ids is None:
        tenant_ids = []

    if isinstance(tenant_ids, list):
        tenant_scope = [str(tid) for tid in tenant_ids]
    else:
        tenant_scope = [str(tenant_ids)]

    return str(bank_id), tenant_scope


@router.get("/overview")
def get_bank_overview(
    request: Request,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    lookback_days: int = Query(30, ge=1, le=180),
):
    """Return aggregated KPIs for the authenticated bank."""
    analytics = AnalyticsService(db)
    bank_id, tenant_ids = _resolve_bank_scope(request)

    summary = analytics.get_bank_portfolio_summary(bank_id=bank_id, tenant_ids=tenant_ids, lookback_days=lookback_days)
    return summary


@router.get("/compliance")
def get_bank_compliance_heatmap(
    request: Request,
    period: Optional[str] = Query(None, regex=r"^\d{4}-\d{2}$", description="Reporting period (YYYY-MM)"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Return a rule-by-tenant compliance heatmap for the current bank."""
    analytics = AnalyticsService(db)
    bank_id, tenant_ids = _resolve_bank_scope(request)

    result = analytics.get_bank_compliance_heatmap(bank_id=bank_id, tenant_ids=tenant_ids, period=period)
    return result


@router.get("/exceptions")
def get_bank_exception_feed(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Return the most recent discrepancy events for the bank's portfolio."""
    analytics = AnalyticsService(db)
    bank_id, tenant_ids = _resolve_bank_scope(request)

    return analytics.get_bank_exception_feed(bank_id=bank_id, tenant_ids=tenant_ids, limit=limit)


@router.get("/audit")
async def search_bank_audit_log(
    request: Request,
    tenant_id: Optional[str] = Query(None, description="Filter by tenant company ID"),
    resource_id: Optional[str] = Query(None, description="Filter by validation session ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Search the bank-scoped audit log."""
    bank_id, tenant_ids = _resolve_bank_scope(request)

    if tenant_id and tenant_ids and tenant_id not in tenant_ids:
        raise HTTPException(status_code=403, detail="Tenant is not managed by this bank.")

    entries, total = await AuditService.search_entries(
        db=db,
        tenant_id=tenant_id,
        resource_id=resource_id,
        limit=limit,
        offset=offset,
        bank_id=bank_id,
    )

    return {
        "total": total,
        "count": len(entries),
        "results": [
            {
                "id": str(entry.id),
                "bank_id": str(entry.bank_id),
                "tenant_id": str(entry.tenant_id) if entry.tenant_id else None,
                "lc_id": str(entry.lc_id) if entry.lc_id else None,
                "event": entry.event,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            }
            for entry in entries
        ],
    }


@router.get("/jobs")
def list_bank_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """List validation jobs for the bank user."""
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        query = db.query(ValidationSession).filter(
            ValidationSession.user_id == current_user.id,
            ValidationSession.deleted_at.is_(None)
        )
        
        # Filter by status if provided
        if status:
            query = query.filter(ValidationSession.status == status)
        
        # Order by created_at desc
        query = query.order_by(ValidationSession.created_at.desc())
        
        # Count total
        total = query.count()
        
        # Apply pagination
        jobs = query.offset(offset).limit(limit).all()
        
        results = []
        for job in jobs:
            # Extract bank metadata from extracted_data
            metadata = job.extracted_data or {}
            bank_metadata = metadata.get("bank_metadata", {})
            
            results.append({
                "id": str(job.id),
                "job_id": str(job.id),
                "client_name": bank_metadata.get("client_name"),
                "lc_number": bank_metadata.get("lc_number"),
                "date_received": bank_metadata.get("date_received"),
                "status": job.status,
                "progress": _calculate_progress(job.status),
                "submitted_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.processing_completed_at.isoformat() if job.processing_completed_at else None,
            })
        
        # Log job list access
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_jobs",
            resource_id=f"list-{len(results)}",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "job_count": len(results),
                "total_available": total,
                "filters": {
                    "status": status,
                    "limit": limit,
                    "offset": offset,
                }
            }
        )
        
        return {
            "total": total,
            "count": len(results),
            "jobs": results,
        }
    except Exception as e:
        # Log failed request
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_jobs",
            resource_id="list-failed",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            error_message=str(e),
        )
        raise


@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: UUID,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Get status of a specific validation job."""
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        job = db.query(ValidationSession).filter(
            ValidationSession.id == job_id,
            ValidationSession.user_id == current_user.id,
            ValidationSession.deleted_at.is_(None)
        ).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Extract bank metadata
        metadata = job.extracted_data or {}
        bank_metadata = metadata.get("bank_metadata", {})
        
        # Log job status access
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_job",
            resource_id=str(job_id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "job_status": job.status,
                "client_name": bank_metadata.get("client_name"),
                "lc_number": bank_metadata.get("lc_number"),
            }
        )
        
        return {
            "id": str(job.id),
            "job_id": str(job.id),
            "client_name": bank_metadata.get("client_name"),
            "lc_number": bank_metadata.get("lc_number"),
            "date_received": bank_metadata.get("date_received"),
            "status": job.status,
            "progress": _calculate_progress(job.status),
            "submitted_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.processing_completed_at.isoformat() if job.processing_completed_at else None,
            "processing_started_at": job.processing_started_at.isoformat() if job.processing_started_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        # Log failed request
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_job",
            resource_id=str(job_id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            error_message=str(e),
        )
        raise


@router.get("/results")
def get_bank_results(
    start_date: Optional[datetime] = Query(None, description="Filter results from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter results until this date"),
    client_name: Optional[str] = Query(None, description="Filter by client name (partial match)"),
    status: Optional[str] = Query(None, description="Filter by compliance status (compliant/discrepancies)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Get validation results with filters."""
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        query = db.query(ValidationSession).filter(
            ValidationSession.user_id == current_user.id,
            ValidationSession.deleted_at.is_(None),
            ValidationSession.status.in_([SessionStatus.COMPLETED.value, SessionStatus.FAILED.value])
        )
        
        # Date filters (already in SQL)
        if start_date:
            query = query.filter(ValidationSession.created_at >= start_date)
        if end_date:
            query = query.filter(ValidationSession.created_at <= end_date)
        
        # Client name filter using JSON operators (SQL-based)
        if client_name:
            # Use PostgreSQL JSON operators to filter by client_name in extracted_data.bank_metadata.client_name
            # Cast JSON to JSONB for better operator support, then use ->> to extract text
            # Handle potential NULL values safely
            client_name_condition = cast(ValidationSession.extracted_data, JSONB)[
                'bank_metadata'
            ]['client_name'].astext.ilike(f"%{client_name}%")
            # Also check that extracted_data is not null
            query = query.filter(
                ValidationSession.extracted_data.isnot(None),
                client_name_condition
            )
        
        # Status filter using JSON operators (SQL-based)
        if status:
            # Cast validation_results to JSONB for JSON operations
            discrepancies_path = cast(ValidationSession.validation_results, JSONB)['discrepancies']
            
            if status == "compliant":
                # Compliant = no discrepancies or empty discrepancies array
                # Check if discrepancies array is empty or doesn't exist
                no_discrepancies = func.jsonb_array_length(discrepancies_path).is_(None) | \
                                  (func.jsonb_array_length(discrepancies_path) == 0)
                query = query.filter(
                    ValidationSession.validation_results.isnot(None),
                    no_discrepancies
                )
            elif status == "discrepancies":
                # Has discrepancies = discrepancies array exists and has length > 0
                has_discrepancies = func.jsonb_array_length(discrepancies_path) > 0
                query = query.filter(
                    ValidationSession.validation_results.isnot(None),
                    has_discrepancies
                )
        
        # Order by completed date desc
        query = query.order_by(ValidationSession.processing_completed_at.desc().nulls_last())
        
        # Count total (now accurate after SQL filtering)
        total = query.count()
        
        # Apply pagination
        sessions = query.offset(offset).limit(limit).all()
        
        # Build results (no Python filtering needed - all done in SQL)
        results = []
        for session in sessions:
            # Extract bank metadata
            metadata = session.extracted_data or {}
            bank_metadata = metadata.get("bank_metadata", {})
            
            # Extract validation results
            validation_results = session.validation_results or {}
            discrepancies = validation_results.get("discrepancies", [])
            
            # Determine compliance status
            has_discrepancies = len(discrepancies) > 0
            compliance_status = "discrepancies" if has_discrepancies else "compliant"
            if session.status == SessionStatus.FAILED.value:
                compliance_status = "failed"
            
            # Count documents
            document_count = len(session.documents) if session.documents else 0
            
            # Calculate compliance score (simplified - can be enhanced)
            compliance_score = max(0, min(100, 100 - (len(discrepancies) * 5)))
            
            # Calculate processing time in seconds
            processing_time_seconds = None
            if session.processing_started_at and session.processing_completed_at:
                delta = session.processing_completed_at - session.processing_started_at
                processing_time_seconds = round(delta.total_seconds(), 2)
            
            results.append({
                "id": str(session.id),
                "job_id": str(session.id),
                "jobId": str(session.id),
                "client_name": bank_metadata.get("client_name"),
                "lc_number": bank_metadata.get("lc_number"),
                "date_received": bank_metadata.get("date_received"),
                "submitted_at": session.created_at.isoformat() if session.created_at else None,
                "processing_started_at": session.processing_started_at.isoformat() if session.processing_started_at else None,
                "completed_at": session.processing_completed_at.isoformat() if session.processing_completed_at else None,
                "processing_time_seconds": processing_time_seconds,
                "status": compliance_status,
                "compliance_score": compliance_score,
                "discrepancy_count": len(discrepancies),
                "document_count": document_count,
            })
        
        # Log results view
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_results",
            resource_id=f"list-{len(results)}",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "result_count": len(results),
                "total_available": total,
                "filters": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "client_name": client_name,
                    "status": status,
                    "limit": limit,
                    "offset": offset,
                }
            }
        )
        
        return {
            "total": total,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        # Log failed request
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_results",
            resource_id="list-failed",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            error_message=str(e),
        )
        raise


@router.get("/results/export-pdf")
@bank_rate_limit(limiter_type="export", limit=10, window_seconds=60)
async def export_results_pdf(
    start_date: Optional[datetime] = Query(None, description="Filter results from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter results until this date"),
    client_name: Optional[str] = Query(None, description="Filter by client name (partial match)"),
    status: Optional[str] = Query(None, description="Filter by compliance status (compliant/discrepancies)"),
    job_ids: Optional[str] = Query(None, description="Comma-separated list of job IDs to export (if provided, other filters are ignored)"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Generate a PDF report for filtered or selected validation results."""
    import time
    start_time = time.time()
    
    from ..reports.generator import ReportGenerator
    from io import BytesIO
    from fastapi.responses import Response
    
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        # If specific job IDs provided, use those
        if job_ids:
            job_id_list = [UUID(jid.strip()) for jid in job_ids.split(",") if jid.strip()]
            sessions = db.query(ValidationSession).filter(
                ValidationSession.id.in_(job_id_list),
                ValidationSession.user_id == current_user.id,
                ValidationSession.deleted_at.is_(None)
            ).all()
            filtered_sessions = sessions
        else:
            # Get filtered results using optimized SQL queries (same logic as get_bank_results)
            query = db.query(ValidationSession).filter(
                ValidationSession.user_id == current_user.id,
                ValidationSession.deleted_at.is_(None),
                ValidationSession.status.in_([SessionStatus.COMPLETED.value, SessionStatus.FAILED.value])
            )
            
            # Date filters (SQL-based)
            if start_date:
                query = query.filter(ValidationSession.created_at >= start_date)
            if end_date:
                query = query.filter(ValidationSession.created_at <= end_date)
            
            # Client name filter using JSON operators (SQL-based)
            if client_name:
                client_name_condition = cast(ValidationSession.extracted_data, JSONB)[
                    'bank_metadata'
                ]['client_name'].astext.ilike(f"%{client_name}%")
                query = query.filter(
                    ValidationSession.extracted_data.isnot(None),
                    client_name_condition
                )
            
            # Status filter using JSON operators (SQL-based)
            if status:
                discrepancies_path = cast(ValidationSession.validation_results, JSONB)['discrepancies']
                
                if status == "compliant":
                    no_discrepancies = func.jsonb_array_length(discrepancies_path).is_(None) | \
                                      (func.jsonb_array_length(discrepancies_path) == 0)
                    query = query.filter(
                        ValidationSession.validation_results.isnot(None),
                        no_discrepancies
                    )
                elif status == "discrepancies":
                    has_discrepancies = func.jsonb_array_length(discrepancies_path) > 0
                    query = query.filter(
                        ValidationSession.validation_results.isnot(None),
                        has_discrepancies
                    )
            
            # Order by completed date desc
            query = query.order_by(ValidationSession.processing_completed_at.desc().nulls_last())
            
            # Get all matching sessions (no pagination for export)
            filtered_sessions = query.all()
        
        # Generate summary PDF report
        report_generator = ReportGenerator()
        
        # Create HTML summary report
        html_content = _generate_summary_report_html(filtered_sessions, current_user)
        
        # Convert to PDF
        pdf_buffer = report_generator._html_to_pdf(html_content)
        # Return PDF as response
        filename = f"bank-lc-results-{datetime.now().strftime('%Y-%m-%d')}.pdf"
        if job_ids:
            filename = f"bank-lc-results-selected-{len(filtered_sessions)}-{datetime.now().strftime('%Y-%m-%d')}.pdf"
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log successful export
        audit_service.log_action(
            action=AuditAction.DOWNLOAD,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_results_export",
            resource_id=f"pdf-{len(filtered_sessions)}-results",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            duration_ms=duration_ms,
            audit_metadata={
                "export_type": "pdf",
                "result_count": len(filtered_sessions),
                "filters": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "client_name": client_name,
                    "status": status,
                    "job_ids_count": len(job_ids.split(",")) if job_ids else None,
                }
            }
        )
        
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        # Log failed export
        audit_service.log_action(
            action=AuditAction.DOWNLOAD,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_results_export",
            resource_id="pdf-export-failed",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            duration_ms=duration_ms,
            error_message=str(e),
        )
        raise


def _generate_summary_report_html(sessions: List[ValidationSession], user: User) -> str:
    """Generate HTML summary report for multiple validation sessions."""
    from datetime import datetime
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Bank LC Validation Results Summary</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                color: #333;
            }}
            h1 {{
                color: #1f2937;
                border-bottom: 2px solid #3b82f6;
                padding-bottom: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #3b82f6;
                color: white;
                font-weight: bold;
            }}
            tr:nth-child(even) {{
                background-color: #f9fafb;
            }}
            .summary {{
                margin: 20px 0;
                padding: 15px;
                background-color: #f3f4f6;
                border-radius: 5px;
            }}
            .compliant {{
                color: #10b981;
                font-weight: bold;
            }}
            .discrepancies {{
                color: #f59e0b;
                font-weight: bold;
            }}
            .failed {{
                color: #ef4444;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h1>Bank LC Validation Results Summary</h1>
        <div class="summary">
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Total Results:</strong> {len(sessions)}</p>
            <p><strong>Generated By:</strong> {user.email if user else 'System'}</p>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Job ID</th>
                    <th>LC Number</th>
                    <th>Client Name</th>
                    <th>Date Received</th>
                    <th>Submitted At</th>
                    <th>Completed At</th>
                    <th>Processing Time (s)</th>
                    <th>Status</th>
                    <th>Score (%)</th>
                    <th>Discrepancies</th>
                    <th>Documents</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for session in sessions:
        metadata = session.extracted_data or {}
        bank_metadata = metadata.get("bank_metadata", {})
        validation_results = session.validation_results or {}
        discrepancies = validation_results.get("discrepancies", [])
        
        client_name = bank_metadata.get("client_name", "")
        lc_number = bank_metadata.get("lc_number", "")
        date_received = bank_metadata.get("date_received", "")
        
        has_discrepancies = len(discrepancies) > 0
        compliance_status = "discrepancies" if has_discrepancies else "compliant"
        if session.status == SessionStatus.FAILED.value:
            compliance_status = "failed"
        
        compliance_score = max(0, min(100, 100 - (len(discrepancies) * 5)))
        document_count = len(session.documents) if session.documents else 0
        
        processing_time = ""
        if session.processing_started_at and session.processing_completed_at:
            delta = session.processing_completed_at - session.processing_started_at
            processing_time = f"{round(delta.total_seconds(), 2)}"
        
        submitted_at = session.created_at.strftime("%Y-%m-%d %H:%M:%S") if session.created_at else ""
        completed_at = session.processing_completed_at.strftime("%Y-%m-%d %H:%M:%S") if session.processing_completed_at else ""
        
        status_class = compliance_status
        html += f"""
                <tr>
                    <td>{str(session.id)[:8]}...</td>
                    <td>{lc_number or "N/A"}</td>
                    <td>{client_name or ""}</td>
                    <td>{date_received or ""}</td>
                    <td>{submitted_at}</td>
                    <td>{completed_at}</td>
                    <td>{processing_time}</td>
                    <td class="{status_class}">{compliance_status.upper()}</td>
                    <td>{compliance_score}</td>
                    <td>{len(discrepancies)}</td>
                    <td>{document_count}</td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    return html


@router.get("/clients")
@bank_rate_limit(limiter_type="api", limit=30, window_seconds=60)
def get_client_names(
    query: Optional[str] = Query(None, description="Filter client names by search query"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Get distinct client names for autocomplete."""
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        # Query all validation sessions for this user
        sessions_query = db.query(ValidationSession).filter(
            ValidationSession.user_id == current_user.id,
            ValidationSession.deleted_at.is_(None),
            ValidationSession.extracted_data.isnot(None)
        )
        
        # If search query provided, filter in SQL (optimized)
        if query:
            client_name_condition = cast(ValidationSession.extracted_data, JSONB)[
                'bank_metadata'
            ]['client_name'].astext.ilike(f"%{query}%")
            sessions_query = sessions_query.filter(client_name_condition)
        
        # Extract distinct client names from extracted_data
        client_names = set()
        sessions = sessions_query.all()
        
        for session in sessions:
            metadata = session.extracted_data or {}
            bank_metadata = metadata.get("bank_metadata", {})
            client_name = bank_metadata.get("client_name")
            
            if client_name and isinstance(client_name, str):
                client_name_clean = client_name.strip()
                if client_name_clean:
                    client_names.add(client_name_clean)
        
        # Convert to sorted list
        client_list = sorted(list(client_names))
        
        # Apply limit
        client_list = client_list[:limit]
        
        # Log client list access
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_clients",
            resource_id="autocomplete",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "query": query,
                "results_count": len(client_list),
                "limit": limit,
            }
        )
        
        return {
            "count": len(client_list),
            "clients": client_list,
        }
    except Exception as e:
        # Log failed request
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_clients",
            resource_id="autocomplete-failed",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            error_message=str(e),
        )
        raise


@router.post("/bulk-upload/extract")
@bank_rate_limit(limiter_type="upload", limit=10, window_seconds=60)
async def extract_zip_file(
    zip_file: UploadFile = File(..., description="ZIP file containing multiple LC document sets"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Extract ZIP file and detect LC sets.
    Returns detected LC sets for user review before processing.
    """
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    MAX_ZIP_SIZE = 100 * 1024 * 1024  # 100MB
    
    try:
        # Read zip file content
        zip_content = await zip_file.read()
        
        # Validate zip file size
        if len(zip_content) > MAX_ZIP_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ZIP file exceeds maximum size of {MAX_ZIP_SIZE / (1024 * 1024):.0f}MB"
            )
        
        # Validate zip file content (check magic bytes)
        if not zip_content.startswith(b'PK'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ZIP file format"
            )
        
        # Extract and detect LC sets
        try:
            lc_sets, file_contents = extract_and_detect_lc_sets(zip_content)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        if not lc_sets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No LC sets detected in ZIP file"
            )
        
        # Prepare response with file info (not full content)
        lc_sets_response = []
        for lc_set in lc_sets:
            files_info = []
            for filename in lc_set['files']:
                if filename in file_contents:
                    file_size = len(file_contents[filename])
                    # Validate file type
                    header_bytes = file_contents[filename][:8]
                    is_valid, _ = validate_upload_file(
                        header_bytes,
                        filename=filename,
                        content_type=None
                    )
                    
                    files_info.append({
                        'filename': filename,
                        'size': file_size,
                        'valid': is_valid,
                    })
            
            lc_sets_response.append({
                'lc_number': lc_set.get('lc_number', ''),
                'client_name': lc_set.get('client_name', ''),
                'files': files_info,
                'file_count': len(files_info),
                'detected_document_types': lc_set.get('detected_document_types', {}),
                'detection_method': lc_set.get('detection_method', 'unknown'),
            })
        
        # Log extraction
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bulk_upload_extract",
            resource_id=f"zip_{zip_file.filename}",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                'zip_filename': zip_file.filename,
                'zip_size': len(zip_content),
                'lc_sets_detected': len(lc_sets),
            }
        )
        
        return {
            'status': 'success',
            'zip_filename': zip_file.filename,
            'zip_size': len(zip_content),
            'lc_sets': lc_sets_response,
            'total_lc_sets': len(lc_sets_response),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk upload extraction error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract ZIP file: {str(e)}"
        )


@router.get("/clients/stats")
@bank_rate_limit(limiter_type="api", limit=30, window_seconds=60)
def get_client_stats(
    query: Optional[str] = Query(None, description="Filter client names by search query"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Get client statistics with validation counts and compliance metrics."""
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        # Query all validation sessions for this user
        sessions_query = db.query(ValidationSession).filter(
            ValidationSession.user_id == current_user.id,
            ValidationSession.deleted_at.is_(None),
            ValidationSession.extracted_data.isnot(None),
            ValidationSession.status.in_([SessionStatus.COMPLETED.value, SessionStatus.FAILED.value])
        )
        
        # If search query provided, filter in SQL
        if query:
            client_name_condition = cast(ValidationSession.extracted_data, JSONB)[
                'bank_metadata'
            ]['client_name'].astext.ilike(f"%{query}%")
            sessions_query = sessions_query.filter(client_name_condition)
        
        # Get all matching sessions
        all_sessions = sessions_query.all()
        
        # Aggregate statistics by client name
        client_stats: Dict[str, Dict] = {}
        
        for session in all_sessions:
            metadata = session.extracted_data or {}
            bank_metadata = metadata.get("bank_metadata", {})
            client_name = bank_metadata.get("client_name")
            
            if not client_name or not isinstance(client_name, str):
                continue
            
            client_name_clean = client_name.strip()
            if not client_name_clean:
                continue
            
            # Initialize client stats if not exists
            if client_name_clean not in client_stats:
                client_stats[client_name_clean] = {
                    "client_name": client_name_clean,
                    "total_validations": 0,
                    "compliant_count": 0,
                    "discrepancies_count": 0,
                    "failed_count": 0,
                    "total_discrepancies": 0,
                    "compliance_scores": [],
                    "last_validation_date": None,
                    "first_validation_date": None,
                }
            
            stats = client_stats[client_name_clean]
            stats["total_validations"] += 1
            
            # Extract validation results
            validation_results = session.validation_results or {}
            discrepancies = validation_results.get("discrepancies", [])
            discrepancy_count = len(discrepancies) if isinstance(discrepancies, list) else 0
            
            # Determine status
            if session.status == SessionStatus.FAILED.value:
                stats["failed_count"] += 1
            elif discrepancy_count == 0:
                stats["compliant_count"] += 1
            else:
                stats["discrepancies_count"] += 1
            
            stats["total_discrepancies"] += discrepancy_count
            
            # Calculate compliance score
            compliance_score = max(0, min(100, 100 - (discrepancy_count * 5)))
            stats["compliance_scores"].append(compliance_score)
            
            # Track dates
            if session.processing_completed_at:
                completed_date = session.processing_completed_at
                if not stats["last_validation_date"] or completed_date > stats["last_validation_date"]:
                    stats["last_validation_date"] = completed_date
                if not stats["first_validation_date"] or completed_date < stats["first_validation_date"]:
                    stats["first_validation_date"] = completed_date
        
        # Convert to list and calculate averages
        client_list = []
        for client_name, stats in client_stats.items():
            avg_score = 0
            if stats["compliance_scores"]:
                avg_score = sum(stats["compliance_scores"]) / len(stats["compliance_scores"])
            
            compliance_rate = 0
            if stats["total_validations"] > 0:
                compliance_rate = (stats["compliant_count"] / stats["total_validations"]) * 100
            
            client_list.append({
                "client_name": client_name,
                "total_validations": stats["total_validations"],
                "compliant_count": stats["compliant_count"],
                "discrepancies_count": stats["discrepancies_count"],
                "failed_count": stats["failed_count"],
                "total_discrepancies": stats["total_discrepancies"],
                "average_compliance_score": round(avg_score, 1),
                "compliance_rate": round(compliance_rate, 1),
                "last_validation_date": stats["last_validation_date"].isoformat() if stats["last_validation_date"] else None,
                "first_validation_date": stats["first_validation_date"].isoformat() if stats["first_validation_date"] else None,
            })
        
        # Sort by total validations (descending) or last validation date
        client_list.sort(key=lambda x: (
            x["last_validation_date"] or "1970-01-01"
        ), reverse=True)
        
        # Apply pagination
        total = len(client_list)
        paginated_list = client_list[offset:offset + limit]
        
        # Log client stats access
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_clients_stats",
            resource_id="list",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "query": query,
                "results_count": len(paginated_list),
                "total_clients": total,
                "limit": limit,
                "offset": offset,
            }
        )
        
        return {
            "total": total,
            "count": len(paginated_list),
            "clients": paginated_list,
        }
    except Exception as e:
        # Log failed request
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="bank_clients_stats",
            resource_id="list-failed",
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.ERROR,
            error_message=str(e),
        )
        raise


STREAM_TOKEN_EXPIRY_SECONDS = 180


@router.get("/jobs/stream-token")
@bank_rate_limit(limiter_type="api", limit=30, window_seconds=60)
def get_job_stream_token(
    current_user: User = Depends(require_bank_or_admin),
):
    """Issue a short-lived token for establishing the SSE job stream."""

    token = create_signed_token(
        secret_key=settings.SECRET_KEY,
        payload={
            "uid": str(current_user.id),
            "nonce": secrets.token_urlsafe(8),
        },
        expires_in=STREAM_TOKEN_EXPIRY_SECONDS,
    )

    return {
        "token": token,
        "expires_in": STREAM_TOKEN_EXPIRY_SECONDS,
    }


def _calculate_progress(status: str) -> int:
    """Calculate progress percentage based on status."""
    status_map = {
        SessionStatus.CREATED.value: 0,
        SessionStatus.UPLOADING.value: 10,
        SessionStatus.PROCESSING.value: 50,
        SessionStatus.COMPLETED.value: 100,
        SessionStatus.FAILED.value: 0,
    }
    return status_map.get(status, 0)


@router.get("/jobs/stream")
async def stream_job_updates(
    request: Request,
    sse_token: str = Query(..., description="Short-lived signed token for SSE authentication"),
):
    """Server-Sent Events stream for real-time job status updates."""

    try:
        payload = verify_signed_token(settings.SECRET_KEY, sse_token)
        user_id = UUID(payload["uid"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired stream token",
        )

    session = SessionLocal()
    try:
        current_user = session.query(User).filter(User.id == user_id).first()
    finally:
        session.close()

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    if not (current_user.role in ["bank_officer", "bank_admin", "system_admin"] or current_user.is_bank_officer()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bank access required",
        )

    async def _fetch_job_snapshots(user: User) -> List[Dict[str, Any]]:
        def _sync_fetch() -> List[Dict[str, Any]]:
            db_session = SessionLocal()
            try:
                active_jobs = db_session.query(ValidationSession).filter(
                    ValidationSession.user_id == user.id,
                    ValidationSession.deleted_at.is_(None),
                    ValidationSession.status.in_(
                        [
                            SessionStatus.CREATED.value,
                            SessionStatus.UPLOADING.value,
                            SessionStatus.PROCESSING.value,
                        ]
                    ),
                ).all()

                recent_threshold = datetime.utcnow() - timedelta(seconds=30)
                recent_jobs = db_session.query(ValidationSession).filter(
                    ValidationSession.user_id == user.id,
                    ValidationSession.deleted_at.is_(None),
                    ValidationSession.status.in_(
                        [SessionStatus.COMPLETED.value, SessionStatus.FAILED.value]
                    ),
                    ValidationSession.updated_at >= recent_threshold,
                ).all()

                jobs = active_jobs + recent_jobs

                snapshots: List[Dict[str, Any]] = []
                for job in jobs:
                    metadata = job.extracted_data or {}
                    bank_metadata = metadata.get("bank_metadata", {})

                    processing_time = None
                    if job.processing_started_at and job.processing_completed_at:
                        processing_time = int(
                            max(
                                0,
                                (job.processing_completed_at - job.processing_started_at).total_seconds(),
                            )
                        )

                    updated_at = (
                        job.updated_at
                        or job.processing_completed_at
                        or job.processing_started_at
                        or job.created_at
                    )
                    version_marker = updated_at.isoformat() if updated_at else str(time.time())

                    snapshots.append(
                        {
                            "payload": {
                                "id": str(job.id),
                                "job_id": str(job.id),
                                "client_name": bank_metadata.get("client_name"),
                                "lc_number": bank_metadata.get("lc_number"),
                                "date_received": bank_metadata.get("date_received"),
                                "status": job.status,
                                "progress": _calculate_progress(job.status),
                                "submitted_at": job.created_at.isoformat() if job.created_at else None,
                                "processing_started_at": job.processing_started_at.isoformat() if job.processing_started_at else None,
                                "completed_at": job.processing_completed_at.isoformat() if job.processing_completed_at else None,
                                "processing_time_seconds": processing_time,
                                "discrepancy_count": len((job.validation_results or {}).get("discrepancies", [])),
                                "document_count": len(job.documents) if job.documents else 0,
                            },
                            "version": version_marker,
                        }
                    )

                return snapshots
            finally:
                db_session.close()

        return await asyncio.to_thread(_sync_fetch)

    async def event_generator():
        last_sent_versions: Dict[str, str] = {}
        last_poll_time = 0.0
        last_keepalive = time.monotonic()

        try:
            while True:
                current_time = time.monotonic()

                if current_time - last_poll_time >= 1.0:
                    snapshots = await _fetch_job_snapshots(current_user)

                    for snapshot in snapshots:
                        payload = snapshot["payload"]
                        job_id = payload["id"]
                        version_marker = snapshot["version"]

                        if last_sent_versions.get(job_id) != version_marker:
                            yield f"data: {json.dumps(payload)}\n\n"
                            last_sent_versions[job_id] = version_marker

                    last_poll_time = current_time

                if current_time - last_keepalive >= 30:
                    yield ": keepalive\n\n"
                    last_keepalive = current_time

                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            pass
        except Exception as exc:  # pragma: no cover - defensive logging
            error_data = {"error": str(exc)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
