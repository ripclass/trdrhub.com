"""
Bank-facing API endpoints for portfolio visibility and governance.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, func, cast, case
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import JSONB

from ..core.security import require_bank_or_admin
from ..database import get_db
from ..models import User, ValidationSession, SessionStatus
from ..services.analytics_service import AnalyticsService
from ..services.audit_service import AuditService
from ..middleware.bank_rate_limit import bank_rate_limit
from ..middleware.audit_middleware import create_audit_context
from ..models.audit_log import AuditAction, AuditResult


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
