"""
Bank SLA Dashboards API endpoints.

Provides SLA metrics, throughput, aging, and breach tracking for bank operations.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract, case
from pydantic import BaseModel
import logging

from ..database import get_db
from app.models import User, ValidationSession
from app.models.admin import JobQueue, JobStatus
from app.models.bank_workflow import BankApproval, DiscrepancyWorkflow
from ..core.security import get_current_user, require_bank_or_admin

router = APIRouter(prefix="/bank/sla", tags=["bank-sla"])
logger = logging.getLogger(__name__)


class SLAMetric(BaseModel):
    name: str
    target: float
    current: float
    unit: str
    status: str  # "met", "at_risk", "breached"
    trend: str  # "up", "down", "stable"
    trend_percentage: float


class SLABreach(BaseModel):
    id: str
    lc_number: str
    client_name: str
    metric: str
    target: float
    actual: float
    breach_time: str
    severity: str  # "critical", "major", "minor"


class SLAThroughputData(BaseModel):
    hour: str
    lcs: int


class SLAAgingData(BaseModel):
    time_range: str
    count: int
    percentage: float


class SLAMetricsResponse(BaseModel):
    metrics: List[SLAMetric]
    overall_compliance: float
    throughput_data: List[SLAThroughputData]
    aging_data: List[SLAAgingData]


class SLABreachesResponse(BaseModel):
    breaches: List[SLABreach]
    total: int


def get_time_range_filter(time_range: str):
    """Get datetime filter for time range."""
    now = datetime.utcnow()
    if time_range == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == "week":
        start = now - timedelta(days=7)
    elif time_range == "month":
        start = now - timedelta(days=30)
    elif time_range == "quarter":
        start = now - timedelta(days=90)
    else:
        start = now - timedelta(days=7)  # Default to week
    
    return start, now


@router.get("/metrics", response_model=SLAMetricsResponse)
async def get_sla_metrics(
    time_range: str = Query("week", description="Time range: today, week, month, quarter"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get SLA metrics for the bank.
    
    Calculates:
    - Average Processing Time (target: 5 minutes)
    - Time to First Review (target: 15 minutes)
    - Throughput (target: 20 LCs/hour)
    - Aging/Average Queue Time (target: 30 minutes)
    """
    start_date, end_date = get_time_range_filter(time_range)
    
    # Filter by bank's company_id
    bank_company_id = current_user.company_id
    
    # Get completed jobs for this bank
    completed_jobs = db.query(JobQueue).filter(
        and_(
            JobQueue.organization_id == bank_company_id,
            JobQueue.status == JobStatus.COMPLETED.value,
            JobQueue.completed_at >= start_date,
            JobQueue.completed_at <= end_date
        )
    ).all()
    
    # Calculate Average Processing Time
    processing_times = []
    for job in completed_jobs:
        if job.started_at and job.completed_at:
            duration = (job.completed_at - job.started_at).total_seconds() / 60  # minutes
            processing_times.append(duration)
    
    avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
    target_processing_time = 5.0  # minutes
    
    # Calculate Time to First Review (from job creation to first approval action)
    time_to_review_times = []
    for job in completed_jobs:
        if job.validation_session_id:
            approval = db.query(BankApproval).filter(
                BankApproval.validation_session_id == job.validation_session_id
            ).first()
            if approval and approval.created_at and job.created_at:
                duration = (approval.created_at - job.created_at).total_seconds() / 60  # minutes
                time_to_review_times.append(duration)
    
    avg_time_to_review = sum(time_to_review_times) / len(time_to_review_times) if time_to_review_times else 0
    target_time_to_review = 15.0  # minutes
    
    # Calculate Throughput (LCs per hour)
    # Group jobs by hour
    hourly_counts = {}
    for job in completed_jobs:
        if job.completed_at:
            hour_key = job.completed_at.strftime("%H:00")
            hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1
    
    # Calculate average throughput
    total_hours = len(set(job.completed_at.strftime("%H:00") for job in completed_jobs if job.completed_at))
    avg_throughput = len(completed_jobs) / total_hours if total_hours > 0 else 0
    target_throughput = 20.0  # LCs/hour
    
    # Calculate Aging/Average Queue Time (time from creation to start)
    queue_times = []
    for job in completed_jobs:
        if job.created_at and job.started_at:
            duration = (job.started_at - job.created_at).total_seconds() / 60  # minutes
            queue_times.append(duration)
    
    avg_queue_time = sum(queue_times) / len(queue_times) if queue_times else 0
    target_queue_time = 30.0  # minutes
    
    # Build metrics
    metrics = [
        SLAMetric(
            name="Average Processing Time",
            target=target_processing_time,
            current=round(avg_processing_time, 1),
            unit="minutes",
            status="met" if avg_processing_time <= target_processing_time else "at_risk" if avg_processing_time <= target_processing_time * 1.2 else "breached",
            trend="down" if avg_processing_time < target_processing_time else "up",
            trend_percentage=round(((avg_processing_time - target_processing_time) / target_processing_time) * 100, 1)
        ),
        SLAMetric(
            name="Time to First Review",
            target=target_time_to_review,
            current=round(avg_time_to_review, 1),
            unit="minutes",
            status="met" if avg_time_to_review <= target_time_to_review else "at_risk" if avg_time_to_review <= target_time_to_review * 1.2 else "breached",
            trend="down" if avg_time_to_review < target_time_to_review else "up",
            trend_percentage=round(((avg_time_to_review - target_time_to_review) / target_time_to_review) * 100, 1)
        ),
        SLAMetric(
            name="Throughput (LCs/hour)",
            target=target_throughput,
            current=round(avg_throughput, 1),
            unit="LCs/hour",
            status="met" if avg_throughput >= target_throughput else "at_risk" if avg_throughput >= target_throughput * 0.8 else "breached",
            trend="up" if avg_throughput > target_throughput else "down",
            trend_percentage=round(((avg_throughput - target_throughput) / target_throughput) * 100, 1)
        ),
        SLAMetric(
            name="Aging (Average Queue Time)",
            target=target_queue_time,
            current=round(avg_queue_time, 1),
            unit="minutes",
            status="met" if avg_queue_time <= target_queue_time else "at_risk" if avg_queue_time <= target_queue_time * 1.2 else "breached",
            trend="down" if avg_queue_time < target_queue_time else "up",
            trend_percentage=round(((avg_queue_time - target_queue_time) / target_queue_time) * 100, 1)
        ),
    ]
    
    # Calculate overall compliance
    met_count = sum(1 for m in metrics if m.status == "met")
    overall_compliance = round((met_count / len(metrics)) * 100, 1) if metrics else 0
    
    # Build throughput data (hourly distribution)
    throughput_data = [
        SLAThroughputData(hour=hour, lcs=count)
        for hour, count in sorted(hourly_counts.items())
    ]
    
    # Build aging data (distribution by time ranges)
    aging_ranges = {
        "0-15 min": 0,
        "15-30 min": 0,
        "30-45 min": 0,
        "45+ min": 0
    }
    for queue_time in queue_times:
        if queue_time <= 15:
            aging_ranges["0-15 min"] += 1
        elif queue_time <= 30:
            aging_ranges["15-30 min"] += 1
        elif queue_time <= 45:
            aging_ranges["30-45 min"] += 1
        else:
            aging_ranges["45+ min"] += 1
    
    total_aging = sum(aging_ranges.values())
    aging_data = [
        SLAAgingData(
            time_range=range_name,
            count=count,
            percentage=round((count / total_aging) * 100, 1) if total_aging > 0 else 0
        )
        for range_name, count in aging_ranges.items()
    ]
    
    return SLAMetricsResponse(
        metrics=metrics,
        overall_compliance=overall_compliance,
        throughput_data=throughput_data,
        aging_data=aging_data
    )


@router.get("/breaches", response_model=SLABreachesResponse)
async def get_sla_breaches(
    time_range: str = Query("week", description="Time range: today, week, month, quarter"),
    severity: Optional[str] = Query(None, description="Filter by severity: critical, major, minor"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get SLA breach incidents.
    
    Identifies breaches where:
    - Processing time > 5 minutes
    - Time to first review > 15 minutes
    - Queue time > 30 minutes
    """
    start_date, end_date = get_time_range_filter(time_range)
    bank_company_id = current_user.company_id
    
    breaches = []
    
    # Get completed jobs
    completed_jobs = db.query(JobQueue).filter(
        and_(
            JobQueue.organization_id == bank_company_id,
            JobQueue.status == JobStatus.COMPLETED.value,
            JobQueue.completed_at >= start_date,
            JobQueue.completed_at <= end_date
        )
    ).all()
    
    for job in completed_jobs:
        # Check processing time breach
        if job.started_at and job.completed_at:
            processing_time = (job.completed_at - job.started_at).total_seconds() / 60
            if processing_time > 5.0:  # Target is 5 minutes
                severity_level = "critical" if processing_time > 10 else "major" if processing_time > 7 else "minor"
                if not severity or severity == severity_level:
                    # Get LC number from validation session
                    lc_number = "Unknown"
                    client_name = "Unknown"
                    if job.validation_session_id:
                        session = db.query(ValidationSession).filter(
                            ValidationSession.id == job.validation_session_id
                        ).first()
                        if session:
                            # Extract LC number from extracted_data or lc_version
                            if session.extracted_data and isinstance(session.extracted_data, dict):
                                lc_number = session.extracted_data.get('lc_number') or session.extracted_data.get('lcNumber') or "Unknown"
                            elif session.lc_version:
                                lc_number = session.lc_version.lc_number or "Unknown"
                            
                            # Get client name from company
                            if session.company_id:
                                from app.models.company import Company
                                company = db.query(Company).filter(Company.id == session.company_id).first()
                                if company:
                                    client_name = company.name
                    
                    breaches.append(SLABreach(
                        id=str(job.id),
                        lc_number=lc_number,
                        client_name=client_name,
                        metric="Average Processing Time",
                        target=5.0,
                        actual=round(processing_time, 1),
                        breach_time=job.completed_at.isoformat(),
                        severity=severity_level
                    ))
        
        # Check queue time breach
        if job.created_at and job.started_at:
            queue_time = (job.started_at - job.created_at).total_seconds() / 60
            if queue_time > 30.0:  # Target is 30 minutes
                severity_level = "critical" if queue_time > 60 else "major" if queue_time > 45 else "minor"
                if not severity or severity == severity_level:
                    lc_number = "Unknown"
                    client_name = "Unknown"
                    if job.validation_session_id:
                        session = db.query(ValidationSession).filter(
                            ValidationSession.id == job.validation_session_id
                        ).first()
                        if session:
                            # Extract LC number from extracted_data or lc_version
                            if session.extracted_data and isinstance(session.extracted_data, dict):
                                lc_number = session.extracted_data.get('lc_number') or session.extracted_data.get('lcNumber') or "Unknown"
                            elif session.lc_version:
                                lc_number = session.lc_version.lc_number or "Unknown"
                            
                            if session.company_id:
                                from app.models.company import Company
                                company = db.query(Company).filter(Company.id == session.company_id).first()
                                if company:
                                    client_name = company.name
                    
                    breaches.append(SLABreach(
                        id=f"{job.id}-queue",
                        lc_number=lc_number,
                        client_name=client_name,
                        metric="Aging",
                        target=30.0,
                        actual=round(queue_time, 1),
                        breach_time=job.started_at.isoformat(),
                        severity=severity_level
                    ))
        
        # Check time to first review breach
        if job.validation_session_id:
            approval = db.query(BankApproval).filter(
                BankApproval.validation_session_id == job.validation_session_id
            ).first()
            if approval and approval.created_at and job.created_at:
                time_to_review = (approval.created_at - job.created_at).total_seconds() / 60
                if time_to_review > 15.0:  # Target is 15 minutes
                    severity_level = "critical" if time_to_review > 30 else "major" if time_to_review > 20 else "minor"
                    if not severity or severity == severity_level:
                        session = db.query(ValidationSession).filter(
                            ValidationSession.id == job.validation_session_id
                        ).first()
                        lc_number = "Unknown"
                        client_name = "Unknown"
                        if session:
                            # Extract LC number from extracted_data or lc_version
                            if session.extracted_data and isinstance(session.extracted_data, dict):
                                lc_number = session.extracted_data.get('lc_number') or session.extracted_data.get('lcNumber') or "Unknown"
                            elif session.lc_version:
                                lc_number = session.lc_version.lc_number or "Unknown"
                            
                            if session.company_id:
                                from app.models.company import Company
                                company = db.query(Company).filter(Company.id == session.company_id).first()
                                if company:
                                    client_name = company.name
                        
                        breaches.append(SLABreach(
                            id=f"{job.id}-review",
                            lc_number=lc_number,
                            client_name=client_name,
                            metric="Time to First Review",
                            target=15.0,
                            actual=round(time_to_review, 1),
                            breach_time=approval.created_at.isoformat(),
                            severity=severity_level
                        ))
    
    return SLABreachesResponse(
        breaches=breaches,
        total=len(breaches)
    )


@router.post("/export")
async def export_sla_report(
    time_range: str = Query("week", description="Time range: today, week, month, quarter"),
    format: str = Query("pdf", description="Export format: pdf, csv"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Export SLA report.
    
    TODO: Implement PDF/CSV generation
    """
    # Placeholder for export functionality
    return {
        "message": "Export functionality not yet implemented",
        "time_range": time_range,
        "format": format
    }

