"""
Analytics API endpoints for dashboard metrics.
"""

import csv
import io
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session

from ..database import get_db
from app.orm import User, UserRole
from ..core.security import get_current_user, require_admin, require_bank_or_admin
from ..core.rbac import RBACPolicyEngine, Permission
from ..services.analytics_service import AnalyticsService
from ..schemas.analytics import (
    SummaryStats, DiscrepancyStats, TrendStats, UserStats, SystemMetrics,
    ProcessingTimeBreakdown, AnalyticsDashboard, AnalyticsQuery, TimeRange,
    AnomalyAlert, AnalyticsExport, ComplianceReport
)
from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction, AuditResult
from app.orm import ValidationSession


router = APIRouter(prefix="/analytics", tags=["analytics"])


def require_analytics_access():
    """Dependency to ensure user has analytics access."""
    def analytics_access(user: User = Depends(get_current_user)):
        # All authenticated users can access their own analytics
        # Banks and admins can access system-wide analytics
        return user
    return analytics_access


@router.get("/summary", response_model=SummaryStats)
async def get_summary_stats(
    time_range: TimeRange = Query("30d", description="Time range for statistics"),
    start_date: Optional[datetime] = Query(None, description="Custom start date"),
    end_date: Optional[datetime] = Query(None, description="Custom end date"),
    user: User = Depends(require_analytics_access()),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for jobs and processing.

    - Exporters/Importers see their own stats only
    - Banks/Admins see system-wide stats
    """
    analytics_service = AnalyticsService(db)

    try:
        summary = analytics_service.get_summary_stats(
            user=user,
            time_range=time_range,
            start_date=start_date,
            end_date=end_date
        )

        # Log analytics access
        audit_service = AuditService(db)
        audit_service.log_action(
            action=AuditAction.ANALYTICS_VIEW,
            user=user,
            resource_type="summary_stats",
            result=AuditResult.SUCCESS,
            audit_metadata={
                "time_range": time_range,
                "total_jobs": summary.total_jobs,
                "rejection_rate": summary.rejection_rate
            }
        )

        return summary

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute summary statistics: {str(e)}"
        )


@router.get("/discrepancies", response_model=DiscrepancyStats)
async def get_discrepancy_stats(
    time_range: TimeRange = Query("30d", description="Time range for statistics"),
    start_date: Optional[datetime] = Query(None, description="Custom start date"),
    end_date: Optional[datetime] = Query(None, description="Custom end date"),
    user: User = Depends(require_analytics_access()),
    db: Session = Depends(get_db)
):
    """
    Get discrepancy analysis statistics.

    Includes top discrepancy types, fatal four frequency, and trends.
    """
    analytics_service = AnalyticsService(db)

    try:
        discrepancy_stats = analytics_service.get_discrepancy_stats(
            user=user,
            time_range=time_range,
            start_date=start_date,
            end_date=end_date
        )

        # Log analytics access
        audit_service = AuditService(db)
        audit_service.log_action(
            action=AuditAction.ANALYTICS_VIEW,
            user=user,
            resource_type="discrepancy_stats",
            result=AuditResult.SUCCESS,
            audit_metadata={
                "time_range": time_range,
                "total_discrepancies": discrepancy_stats.total_discrepancies
            }
        )

        return discrepancy_stats

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute discrepancy statistics: {str(e)}"
        )


@router.get("/trends", response_model=TrendStats)
async def get_trend_stats(
    time_range: TimeRange = Query("30d", description="Time range for trends"),
    start_date: Optional[datetime] = Query(None, description="Custom start date"),
    end_date: Optional[datetime] = Query(None, description="Custom end date"),
    user: User = Depends(require_analytics_access()),
    db: Session = Depends(get_db)
):
    """
    Get trend analysis over time.

    Shows daily timeline with job volumes, success rates, and processing times.
    """
    analytics_service = AnalyticsService(db)

    try:
        trend_stats = analytics_service.get_trend_stats(
            user=user,
            time_range=time_range,
            start_date=start_date,
            end_date=end_date
        )

        # Log analytics access
        audit_service = AuditService(db)
        audit_service.log_action(
            action=AuditAction.ANALYTICS_VIEW,
            user=user,
            resource_type="trend_stats",
            result=AuditResult.SUCCESS,
            audit_metadata={
                "time_range": time_range,
                "data_points": len(trend_stats.timeline)
            }
        )

        return trend_stats

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute trend statistics: {str(e)}"
        )


@router.get("/processing-times", response_model=ProcessingTimeBreakdown)
async def get_processing_time_breakdown(
    time_range: TimeRange = Query("30d", description="Time range for analysis"),
    start_date: Optional[datetime] = Query(None, description="Custom start date"),
    end_date: Optional[datetime] = Query(None, description="Custom end date"),
    user: User = Depends(require_analytics_access()),
    db: Session = Depends(get_db)
):
    """
    Get detailed processing time breakdown and percentiles.
    """
    analytics_service = AnalyticsService(db)

    try:
        processing_breakdown = analytics_service.get_processing_time_breakdown(
            user=user,
            time_range=time_range,
            start_date=start_date,
            end_date=end_date
        )

        # Log analytics access
        audit_service = AuditService(db)
        audit_service.log_action(
            action=AuditAction.ANALYTICS_VIEW,
            user=user,
            resource_type="processing_time_breakdown",
            result=AuditResult.SUCCESS,
            audit_metadata={
                "time_range": time_range
            }
        )

        return processing_breakdown

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute processing time breakdown: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=UserStats)
async def get_user_stats(
    user_id: UUID,
    time_range: TimeRange = Query("30d", description="Time range for user stats"),
    start_date: Optional[datetime] = Query(None, description="Custom start date"),
    end_date: Optional[datetime] = Query(None, description="Custom end date"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get statistics for a specific user.

    Requires bank or admin privileges.
    """
    # Get target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    analytics_service = AnalyticsService(db)

    try:
        user_stats = analytics_service.get_user_stats(
            target_user=target_user,
            requesting_user=current_user,
            time_range=time_range,
            start_date=start_date,
            end_date=end_date
        )

        # Log analytics access
        audit_service = AuditService(db)
        audit_service.log_action(
            action=AuditAction.ANALYTICS_VIEW,
            user=current_user,
            resource_type="user_stats",
            resource_id=str(user_id),
            result=AuditResult.SUCCESS,
            audit_metadata={
                "time_range": time_range,
                "target_user": target_user.email,
                "total_jobs": user_stats.total_jobs
            }
        )

        return user_stats

    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view user statistics"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute user statistics: {str(e)}"
        )


@router.get("/system", response_model=SystemMetrics)
async def get_system_metrics(
    time_range: TimeRange = Query("30d", description="Time range for system metrics"),
    start_date: Optional[datetime] = Query(None, description="Custom start date"),
    end_date: Optional[datetime] = Query(None, description="Custom end date"),
    user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get system-wide metrics and insights.

    Requires bank or admin privileges.
    """
    analytics_service = AnalyticsService(db)

    try:
        system_metrics = analytics_service.get_system_metrics(
            user=user,
            time_range=time_range,
            start_date=start_date,
            end_date=end_date
        )

        # Log analytics access
        audit_service = AuditService(db)
        audit_service.log_action(
            action=AuditAction.ANALYTICS_VIEW,
            user=user,
            resource_type="system_metrics",
            result=AuditResult.SUCCESS,
            audit_metadata={
                "time_range": time_range,
                "total_system_jobs": system_metrics.total_system_jobs,
                "active_users": system_metrics.total_active_users
            }
        )

        return system_metrics

    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System metrics require bank or admin privileges"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute system metrics: {str(e)}"
        )


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_analytics_dashboard(
    time_range: TimeRange = Query("30d", description="Time range for dashboard"),
    start_date: Optional[datetime] = Query(None, description="Custom start date"),
    end_date: Optional[datetime] = Query(None, description="Custom end date"),
    include_trends: bool = Query(True, description="Include trend analysis"),
    include_discrepancies: bool = Query(True, description="Include discrepancy analysis"),
    user: User = Depends(require_analytics_access()),
    db: Session = Depends(get_db)
):
    """
    Get complete dashboard data in a single request.

    Optimized endpoint that combines multiple analytics views.
    """
    analytics_service = AnalyticsService(db)

    try:
        # Get all required data
        summary = analytics_service.get_summary_stats(user, time_range, start_date, end_date)
        processing_times = analytics_service.get_processing_time_breakdown(user, time_range, start_date, end_date)

        trends = None
        if include_trends:
            trends = analytics_service.get_trend_stats(user, time_range, start_date, end_date)

        discrepancies = None
        if include_discrepancies:
            discrepancies = analytics_service.get_discrepancy_stats(user, time_range, start_date, end_date)

        # Role-specific data
        user_stats = None
        system_metrics = None

        if user.role in [UserRole.EXPORTER, UserRole.IMPORTER]:
            # Individual user dashboard
            user_stats = analytics_service.get_user_stats(user, user, time_range, start_date, end_date)
            data_scope = "own"
        else:
            # System-wide dashboard
            system_metrics = analytics_service.get_system_metrics(user, time_range, start_date, end_date)
            data_scope = "system-wide"

        dashboard = AnalyticsDashboard(
            summary=summary,
            trends=trends,
            discrepancies=discrepancies,
            processing_times=processing_times,
            user_stats=user_stats,
            system_metrics=system_metrics,
            generated_at=datetime.utcnow(),
            user_role=user.role,
            data_scope=data_scope
        )

        # Log dashboard access
        audit_service = AuditService(db)
        audit_service.log_action(
            action=AuditAction.ANALYTICS_VIEW,
            user=user,
            resource_type="dashboard",
            result=AuditResult.SUCCESS,
            audit_metadata={
                "time_range": time_range,
                "data_scope": data_scope,
                "include_trends": include_trends,
                "include_discrepancies": include_discrepancies
            }
        )

        return dashboard

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate analytics dashboard: {str(e)}"
        )


@router.get("/anomalies", response_model=List[AnomalyAlert])
async def get_anomaly_alerts(
    time_range: TimeRange = Query("7d", description="Time range for anomaly detection"),
    user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get anomaly detection alerts.

    Requires bank or admin privileges.
    """
    analytics_service = AnalyticsService(db)

    try:
        alerts = analytics_service.detect_anomalies(user, time_range)

        # Log anomaly check
        audit_service = AuditService(db)
        audit_service.log_action(
            action=AuditAction.ANALYTICS_VIEW,
            user=user,
            resource_type="anomaly_alerts",
            result=AuditResult.SUCCESS,
            audit_metadata={
                "time_range": time_range,
                "alerts_found": len(alerts)
            }
        )

        return alerts

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect anomalies: {str(e)}"
        )


@router.get("/export/csv")
async def export_analytics_csv(
    time_range: TimeRange = Query("30d", description="Time range for export"),
    start_date: Optional[datetime] = Query(None, description="Custom start date"),
    end_date: Optional[datetime] = Query(None, description="Custom end date"),
    user: User = Depends(require_analytics_access()),
    db: Session = Depends(get_db)
):
    """
    Export analytics data as CSV.
    """
    analytics_service = AnalyticsService(db)

    try:
        # Get summary data for export
        summary = analytics_service.get_summary_stats(user, time_range, start_date, end_date)
        trends = analytics_service.get_trend_stats(user, time_range, start_date, end_date)

        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)

        # Write summary section
        writer.writerow(["Analytics Export"])
        writer.writerow(["Generated At", datetime.utcnow().isoformat()])
        writer.writerow(["User", user.email])
        writer.writerow(["Time Range", f"{summary.start_date.date()} to {summary.end_date.date()}"])
        writer.writerow([])

        # Summary statistics
        writer.writerow(["Summary Statistics"])
        writer.writerow(["Total Jobs", summary.total_jobs])
        writer.writerow(["Successful Jobs", summary.success_count])
        writer.writerow(["Rejected Jobs", summary.rejection_count])
        writer.writerow(["Rejection Rate %", summary.rejection_rate])
        writer.writerow(["Avg Processing Time (min)", summary.avg_processing_time_minutes or "N/A"])
        writer.writerow([])

        # Document distribution
        writer.writerow(["Document Distribution"])
        writer.writerow(["Document Type", "Count"])
        for doc_type, count in summary.doc_distribution.items():
            writer.writerow([doc_type, count])
        writer.writerow([])

        # Trends
        writer.writerow(["Daily Trends"])
        writer.writerow(["Date", "Jobs Submitted", "Jobs Completed", "Jobs Rejected", "Success Rate %"])
        for point in trends.timeline:
            writer.writerow([
                point.date.isoformat(),
                point.jobs_submitted,
                point.jobs_completed,
                point.jobs_rejected,
                point.success_rate
            ])

        # Log export
        audit_service = AuditService(db)
        audit_service.log_action(
            action=AuditAction.ANALYTICS_EXPORT,
            user=user,
            resource_type="analytics_csv",
            result=AuditResult.SUCCESS,
            audit_metadata={
                "time_range": time_range,
                "format": "csv"
            }
        )

        # Return as downloadable file
        csv_content = output.getvalue()
        filename = f"analytics_{user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export analytics: {str(e)}"
        )


@router.get("/health")
async def get_analytics_health(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get analytics system health status.

    Requires admin privileges.
    """
    try:
        # Test database connectivity
        db.execute("SELECT 1")

        # Test analytics computation speed
        analytics_service = AnalyticsService(db)
        start_time = datetime.utcnow()

        # Run a quick analytics query
        summary = analytics_service.get_summary_stats(user, "7d")

        end_time = datetime.utcnow()
        query_time_ms = (end_time - start_time).total_seconds() * 1000

        # Check for recent data
        recent_jobs = db.query(ValidationSession).filter(
            ValidationSession.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()

        health_status = {
            "status": "healthy",
            "database_connected": True,
            "query_performance_ms": round(query_time_ms, 2),
            "recent_jobs_24h": recent_jobs,
            "last_checked": datetime.utcnow().isoformat()
        }

        # Performance warnings
        if query_time_ms > 1000:  # 1 second
            health_status["warnings"] = ["Analytics queries are slow (>1s)"]

        return health_status

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "last_checked": datetime.utcnow().isoformat()
        }