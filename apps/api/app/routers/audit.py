"""
Admin API endpoints for audit log queries and compliance reporting.
"""

import math
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_

from ..database import get_db
from .. import models
from ..core.security import get_current_user, require_admin, require_bank_or_admin
from ..core.rbac import RBACPolicyEngine, Permission
from ..models.audit_log import AuditLog, AuditAction, AuditResult
from ..services.audit_service import AuditService
from ..services.audit_monitoring import AuditMonitoringService
from ..schemas.audit import (
    AuditLogQuery, AuditLogResponse, AuditLogSummaryResponse,
    AuditLogRead, AuditLogSummary, ComplianceReportQuery,
    ComplianceReportResponse, FileIntegrityCheck, AuditStatistics,
    AuditSearchResult, AuditRetentionPolicy
)


router = APIRouter(prefix="/admin/audit", tags=["audit-admin"])


@router.get("/logs", response_model=AuditLogSummaryResponse)
async def get_audit_logs(
    query: AuditLogQuery = Depends(),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get paginated audit logs with filtering.

    Requires admin privileges.
    """
    # Build query
    filters = []

    if query.user_id:
        filters.append(AuditLog.user_id == query.user_id)
    if query.user_email:
        filters.append(AuditLog.user_email.ilike(f"%{query.user_email}%"))
    if query.action:
        filters.append(AuditLog.action == query.action)
    if query.resource_type:
        filters.append(AuditLog.resource_type == query.resource_type)
    if query.lc_number:
        filters.append(AuditLog.lc_number == query.lc_number)
    if query.result:
        filters.append(AuditLog.result == query.result)
    if query.start_date:
        filters.append(AuditLog.timestamp >= query.start_date)
    if query.end_date:
        filters.append(AuditLog.timestamp <= query.end_date)
    if query.ip_address:
        filters.append(AuditLog.ip_address == query.ip_address)
    if query.correlation_id:
        filters.append(AuditLog.correlation_id == query.correlation_id)

    # Count total records
    total_query = db.query(func.count(AuditLog.id))
    if filters:
        total_query = total_query.filter(and_(*filters))
    total = total_query.scalar()

    # Build main query
    main_query = db.query(AuditLog)
    if filters:
        main_query = main_query.filter(and_(*filters))

    # Apply sorting
    if query.sort_by == "timestamp":
        sort_column = AuditLog.timestamp
    elif query.sort_by == "action":
        sort_column = AuditLog.action
    elif query.sort_by == "user_email":
        sort_column = AuditLog.user_email
    elif query.sort_by == "result":
        sort_column = AuditLog.result
    else:
        sort_column = AuditLog.timestamp

    if query.sort_order == "desc":
        main_query = main_query.order_by(desc(sort_column))
    else:
        main_query = main_query.order_by(sort_column)

    # Apply pagination
    offset = (query.page - 1) * query.per_page
    logs = main_query.offset(offset).limit(query.per_page).all()

    # Calculate pagination info
    pages = math.ceil(total / query.per_page)
    has_next = query.page < pages
    has_prev = query.page > 1

    return AuditLogSummaryResponse(
        logs=[AuditLogSummary.from_orm(log) for log in logs],
        total=total,
        page=query.page,
        per_page=query.per_page,
        pages=pages,
        has_next=has_next,
        has_prev=has_prev
    )


@router.get("/logs/{log_id}", response_model=AuditLogRead)
async def get_audit_log_detail(
    log_id: UUID,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed audit log by ID.

    Requires admin privileges.
    """
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log not found: {log_id}"
        )

    return AuditLogRead.from_orm(log)


@router.get("/compliance-report", response_model=ComplianceReportResponse)
async def get_compliance_report(
    query: ComplianceReportQuery = Depends(),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Generate compliance report for audit purposes.

    Requires admin privileges.
    """
    audit_service = AuditService(db)

    report = audit_service.get_compliance_report(
        start_date=query.start_date,
        end_date=query.end_date,
        user_id=query.user_id,
        action=query.action
    )

    # Convert logs to schema if details requested
    detailed_logs = None
    if query.include_details and report.get("logs"):
        detailed_logs = [AuditLogRead.from_orm(log) for log in report["logs"][:100]]  # Limit for performance

    return ComplianceReportResponse(
        report_period=report["report_period"],
        summary=report["summary"],
        action_breakdown=report["action_breakdown"],
        user_activity=report["user_activity"],
        logs=detailed_logs
    )


@router.get("/user/{user_id}/activity", response_model=List[AuditLogSummary])
async def get_user_activity(
    user_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    actions: Optional[List[str]] = Query(None, description="Action filter"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records"),
    current_user: models.User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get audit activity for a specific user.

    Requires bank or admin privileges.
    """
    audit_service = AuditService(db)

    logs = audit_service.get_user_activity(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        actions=actions,
        limit=limit
    )

    return [AuditLogSummary.from_orm(log) for log in logs]


@router.get("/lc/{lc_number}/activity", response_model=List[AuditLogSummary])
async def get_lc_activity(
    lc_number: str,
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records"),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get audit activity for a specific LC.

    Requires admin privileges.
    """
    audit_service = AuditService(db)

    logs = audit_service.get_lc_activity(
        lc_number=lc_number,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )

    return [AuditLogSummary.from_orm(log) for log in logs]


@router.get("/statistics", response_model=AuditStatistics)
async def get_audit_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get audit statistics and metrics.

    Requires admin privileges.
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    # Total actions
    total_actions = db.query(func.count(AuditLog.id))\
        .filter(AuditLog.timestamp >= start_date)\
        .scalar() or 0

    # Success rate
    successful_actions = db.query(func.count(AuditLog.id))\
        .filter(AuditLog.timestamp >= start_date)\
        .filter(AuditLog.result == AuditResult.SUCCESS)\
        .scalar() or 0

    success_rate = (successful_actions / max(total_actions, 1)) * 100

    # Most active user
    most_active_user = db.query(AuditLog.user_email, func.count(AuditLog.id).label('count'))\
        .filter(AuditLog.timestamp >= start_date)\
        .filter(AuditLog.user_email.isnot(None))\
        .group_by(AuditLog.user_email)\
        .order_by(desc('count'))\
        .first()

    # Most common action
    most_common_action = db.query(AuditLog.action, func.count(AuditLog.id).label('count'))\
        .filter(AuditLog.timestamp >= start_date)\
        .group_by(AuditLog.action)\
        .order_by(desc('count'))\
        .first()

    # Recent failures
    recent_failures = db.query(func.count(AuditLog.id))\
        .filter(AuditLog.timestamp >= datetime.utcnow() - timedelta(hours=24))\
        .filter(AuditLog.result.in_([AuditResult.FAILURE, AuditResult.ERROR]))\
        .scalar() or 0

    # File operations
    file_operations = db.query(func.count(AuditLog.id))\
        .filter(AuditLog.timestamp >= start_date)\
        .filter(AuditLog.file_hash.isnot(None))\
        .scalar() or 0

    # Last 24h actions
    last_24h_actions = db.query(func.count(AuditLog.id))\
        .filter(AuditLog.timestamp >= datetime.utcnow() - timedelta(hours=24))\
        .scalar() or 0

    return AuditStatistics(
        total_actions=total_actions,
        success_rate=round(success_rate, 2),
        most_active_user=most_active_user.user_email if most_active_user else None,
        most_common_action=most_common_action.action if most_common_action else None,
        recent_failures=recent_failures,
        file_operations=file_operations,
        last_24h_actions=last_24h_actions
    )


@router.post("/verify-integrity", response_model=FileIntegrityCheck)
async def verify_file_integrity(
    file_hash: str = Query(..., description="Current file hash"),
    expected_hash: str = Query(..., description="Expected file hash from audit log"),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Verify file integrity against audit log hash.

    Requires admin privileges.
    """
    audit_service = AuditService(db)

    # In a real implementation, you would:
    # 1. Retrieve the file from storage using the hash
    # 2. Calculate its current hash
    # 3. Compare against expected hash

    verified = file_hash == expected_hash

    return FileIntegrityCheck(
        file_hash=file_hash,
        expected_hash=expected_hash,
        verified=verified,
        timestamp=datetime.utcnow()
    )


@router.get("/search", response_model=List[AuditSearchResult])
async def search_audit_logs(
    q: str = Query(..., min_length=3, description="Search query"),
    limit: int = Query(50, ge=1, le=500, description="Number of results"),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Search audit logs by text query.

    Searches in user_email, action, resource_id, lc_number, and error_message.
    Requires admin privileges.
    """
    search_term = f"%{q}%"

    logs = db.query(AuditLog)\
        .filter(or_(
            AuditLog.user_email.ilike(search_term),
            AuditLog.action.ilike(search_term),
            AuditLog.resource_id.ilike(search_term),
            AuditLog.lc_number.ilike(search_term),
            AuditLog.error_message.ilike(search_term),
            AuditLog.correlation_id.ilike(search_term)
        ))\
        .order_by(desc(AuditLog.timestamp))\
        .limit(limit)\
        .all()

    results = []
    for log in logs:
        # Simple relevance scoring based on field matches
        relevance_score = 0.0
        if log.user_email and q.lower() in log.user_email.lower():
            relevance_score += 0.3
        if q.lower() in log.action.lower():
            relevance_score += 0.4
        if log.lc_number and q.lower() in log.lc_number.lower():
            relevance_score += 0.3

        resource = log.resource_id or log.lc_number or log.resource_type or "unknown"

        results.append(AuditSearchResult(
            correlation_id=log.correlation_id,
            timestamp=log.timestamp,
            user_email=log.user_email,
            action=log.action,
            resource=resource,
            result=log.result,
            relevance_score=relevance_score
        ))

    # Sort by relevance score
    results.sort(key=lambda x: x.relevance_score, reverse=True)

    return results


@router.get("/failures", response_model=List[AuditLogSummary])
async def get_recent_failures(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    limit: int = Query(100, ge=1, le=500, description="Number of failures"),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get recent failed audit events.

    Requires admin privileges.
    """
    since = datetime.utcnow() - timedelta(hours=hours)

    logs = db.query(AuditLog)\
        .filter(AuditLog.timestamp >= since)\
        .filter(AuditLog.result.in_([AuditResult.FAILURE, AuditResult.ERROR]))\
        .order_by(desc(AuditLog.timestamp))\
        .limit(limit)\
        .all()

    return [AuditLogSummary.from_orm(log) for log in logs]


@router.get("/correlation/{correlation_id}", response_model=List[AuditLogSummary])
async def get_logs_by_correlation(
    correlation_id: str,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all audit logs for a specific correlation ID.

    Useful for tracing a complete request flow.
    Requires admin privileges.
    """
    logs = db.query(AuditLog)\
        .filter(AuditLog.correlation_id == correlation_id)\
        .order_by(AuditLog.timestamp)\
        .all()

    if not logs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit logs found for correlation ID: {correlation_id}"
        )

    return [AuditLogSummary.from_orm(log) for log in logs]


@router.delete("/cleanup")
async def cleanup_old_logs(
    days: int = Query(2555, ge=365, description="Delete logs older than N days"),
    dry_run: bool = Query(True, description="Preview mode, don't actually delete"),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Clean up old audit logs based on retention policy.

    Requires admin privileges.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Count logs to be deleted
    count_query = db.query(func.count(AuditLog.id))\
        .filter(AuditLog.timestamp < cutoff_date)

    count = count_query.scalar() or 0

    if dry_run:
        return {
            "action": "preview",
            "logs_to_delete": count,
            "cutoff_date": cutoff_date.isoformat(),
            "note": "Set dry_run=false to actually delete"
        }

    # Actually delete (archive first in production)
    deleted = db.query(AuditLog)\
        .filter(AuditLog.timestamp < cutoff_date)\
        .delete()

    db.commit()

    return {
        "action": "deleted",
        "logs_deleted": deleted,
        "cutoff_date": cutoff_date.isoformat()
    }


@router.get("/retention-policy", response_model=AuditRetentionPolicy)
async def get_retention_policy(
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get current audit log retention policy.

    Requires admin privileges.
    """
    # In a real implementation, this would be stored in database/config
    return AuditRetentionPolicy(
        default_retention_days=2555,  # 7 years
        critical_action_retention_days=3650,  # 10 years
        min_retention_days=365,  # 1 year
        auto_archive_enabled=True
    )


@router.put("/retention-policy", response_model=AuditRetentionPolicy)
async def update_retention_policy(
    policy: AuditRetentionPolicy,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update audit log retention policy.

    Requires admin privileges.
    """
    # In a real implementation, this would be stored in database/config
    # For now, just return the provided policy as confirmation
    return policy


@router.get("/monitoring/health")
async def get_monitoring_health(
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get audit system health and monitoring status.

    Requires admin privileges.
    """
    monitoring_service = AuditMonitoringService(db)
    return monitoring_service.get_monitoring_summary()


@router.get("/monitoring/alerts")
async def get_audit_alerts(
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get current audit system alerts and warnings.

    Requires admin privileges.
    """
    monitoring_service = AuditMonitoringService(db)
    return monitoring_service.run_all_checks()


@router.get("/monitoring/failure-rate")
async def check_failure_rate(
    hours: int = Query(1, ge=1, le=168, description="Hours to check"),
    threshold: float = Query(0.10, ge=0.01, le=1.0, description="Failure rate threshold"),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Check current failure rate against threshold.

    Requires admin privileges.
    """
    monitoring_service = AuditMonitoringService(db)
    alert = monitoring_service.check_failure_rate(hours=hours, threshold=threshold)

    if alert:
        return {
            "status": "alert",
            "alert": alert.to_dict()
        }
    else:
        return {
            "status": "healthy",
            "message": f"Failure rate within threshold for last {hours}h"
        }


@router.get("/monitoring/suspicious-activity")
async def check_suspicious_activity(
    hours: int = Query(24, ge=1, le=168, description="Hours to check"),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Check for suspicious activity patterns.

    Requires admin privileges.
    """
    monitoring_service = AuditMonitoringService(db)
    alerts = monitoring_service.check_suspicious_activity(hours=hours)

    return {
        "status": "checked",
        "alerts_found": len(alerts),
        "alerts": [alert.to_dict() for alert in alerts]
    }


@router.get("/monitoring/file-integrity")
async def check_file_integrity(
    days: int = Query(7, ge=1, le=30, description="Days to check"),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Check for file integrity issues.

    Requires admin privileges.
    """
    monitoring_service = AuditMonitoringService(db)
    alerts = monitoring_service.check_file_integrity_issues(days=days)

    return {
        "status": "checked",
        "integrity_alerts": len(alerts),
        "alerts": [alert.to_dict() for alert in alerts]
    }


@router.get("/monitoring/compliance-gaps")
async def check_compliance_gaps(
    days: int = Query(1, ge=1, le=7, description="Days to check"),
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Check for compliance and audit trail gaps.

    Requires admin privileges.
    """
    monitoring_service = AuditMonitoringService(db)
    alerts = monitoring_service.check_compliance_gaps(days=days)

    return {
        "status": "checked",
        "compliance_alerts": len(alerts),
        "alerts": [alert.to_dict() for alert in alerts]
    }