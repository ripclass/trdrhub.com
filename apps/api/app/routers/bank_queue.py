"""
Bank Queue Operations API endpoints.

Bank officers can view queue (read-only).
Bank admins can view and manage queue (retry, cancel, assign, requeue).
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, String
import logging
import math

from ..database import get_db
from app.models import User
from app.models.admin import JobQueue, JobDLQ, JobStatus
from app.schemas.admin import (
    JobFilter, JobQueue as JobQueueSchema, PaginatedResponse,
    BulkJobAction
)
from ..core.security import get_current_user, require_bank_or_admin
from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction, AuditResult

router = APIRouter(prefix="/bank/queue", tags=["bank-queue"])
logger = logging.getLogger(__name__)


def require_bank_admin(user: User = Depends(get_current_user)) -> User:
    """Require bank_admin role for mutations."""
    if not user.is_bank_admin() and not user.is_system_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bank admin access required"
        )
    return user


@router.get("", response_model=PaginatedResponse)
async def get_bank_queue(
    status: Optional[str] = Query(None, description="Filter by job status"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    search: Optional[str] = Query(None, description="Search in job data"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get job queue for the current bank tenant with filtering and pagination.
    
    Bank officers and admins can view jobs in their bank tenant.
    Jobs are scoped to the bank's organization_id (mapped from company_id).
    """
    try:
        # Scope to current user's company (bank tenant)
        # Map company_id to organization_id for JobQueue
        query = db.query(JobQueue).filter(
            JobQueue.organization_id == current_user.company_id
        )

        # Apply filters
        if status:
            try:
                status_enum = JobStatus(status)
                query = query.filter(JobQueue.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}"
                )
        
        if job_type:
            query = query.filter(JobQueue.job_type == job_type)
        
        if search:
            # Search in job_data JSONB (basic text search)
            query = query.filter(
                JobQueue.job_data.cast(String).ilike(f"%{search}%")
            )

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        jobs = query.order_by(
            JobQueue.priority.desc(),
            JobQueue.scheduled_at.asc()
        ).offset(offset).limit(limit).all()

        # Convert to response schemas
        job_schemas = [JobQueueSchema.from_orm(job) for job in jobs]

        response = PaginatedResponse(
            items=job_schemas,
            total=total,
            page=offset // limit + 1 if limit > 0 else 1,
            size=limit,
            pages=math.ceil(total / limit) if limit > 0 else 1
        )

        logger.info(
            f"Bank queue queried by {current_user.role} {current_user.id}, "
            f"returned {len(jobs)} jobs for company {current_user.company_id}"
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query bank queue: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query job queue"
        )


@router.get("/stats")
async def get_bank_queue_stats(
    time_range: str = Query("24h", regex="^(1h|6h|24h|7d)$"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get job queue statistics for the bank tenant.
    
    Bank officers and admins can view queue stats.
    """
    try:
        # Calculate time range
        hours_map = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}
        hours = hours_map.get(time_range, 24)
        since_time = datetime.utcnow() - timedelta(hours=hours)

        # Scope to bank tenant
        base_query = db.query(JobQueue).filter(
            and_(
                JobQueue.organization_id == current_user.company_id,
                JobQueue.created_at >= since_time
            )
        )

        # Query statistics
        total_jobs = base_query.count()

        status_counts = base_query.with_entities(
            JobQueue.status,
            func.count(JobQueue.id)
        ).group_by(JobQueue.status).all()

        type_counts = base_query.with_entities(
            JobQueue.job_type,
            func.count(JobQueue.id)
        ).group_by(JobQueue.job_type).all()

        # Average processing time for completed jobs
        avg_processing_time = base_query.filter(
            and_(
                JobQueue.status == JobStatus.COMPLETED,
                JobQueue.completed_at.isnot(None),
                JobQueue.started_at.isnot(None)
            )
        ).with_entities(
            func.avg(
                func.extract('epoch', JobQueue.completed_at - JobQueue.started_at) * 1000
            )
        ).scalar()

        stats = {
            "time_range": time_range,
            "total_jobs": total_jobs,
            "status_breakdown": {str(status): count for status, count in status_counts},
            "type_breakdown": {job_type: count for job_type, count in type_counts},
            "avg_processing_time_ms": int(avg_processing_time) if avg_processing_time else 0,
            "queue_depth": base_query.filter(
                JobQueue.status.in_([JobStatus.QUEUED, JobStatus.RUNNING])
            ).count()
        }

        logger.info(
            f"Bank queue stats requested by {current_user.role} {current_user.id} "
            f"for {time_range}"
        )
        return stats

    except Exception as e:
        logger.error(f"Failed to get bank queue stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get queue stats"
        )


@router.post("/{job_id}/retry")
async def retry_bank_job(
    job_id: UUID,
    reason: str = Query(..., min_length=1, description="Reason for retry"),
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """
    Retry a specific job in the bank tenant.
    
    Bank admins only can retry jobs.
    """
    try:
        job = db.query(JobQueue).filter(
            and_(
                JobQueue.id == job_id,
                JobQueue.organization_id == current_user.company_id
            )
        ).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or not accessible"
            )

        # Reset job for retry
        job.status = JobStatus.QUEUED
        job.attempts = 0
        job.error_message = None
        job.error_stack = None
        job.scheduled_at = datetime.utcnow()
        job.started_at = None
        job.completed_at = None
        job.failed_at = None

        db.commit()

        # Audit log
        await AuditService.log_action(
            db=db,
            actor_id=current_user.id,
            actor_type="user",
            resource_type="job_queue",
            resource_id=str(job_id),
            organization_id=current_user.company_id,
            action=AuditAction.UPDATE,
            result=AuditResult.SUCCESS,
            metadata={"action": "retry", "reason": reason}
        )

        logger.info(
            f"Job {job_id} retried by bank admin {current_user.id}, "
            f"reason: {reason}"
        )

        return {"message": "Job queued for retry", "job_id": str(job_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry job {job_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry job"
        )


@router.post("/{job_id}/cancel")
async def cancel_bank_job(
    job_id: UUID,
    reason: str = Query(..., min_length=1, description="Reason for cancellation"),
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """
    Cancel a specific job in the bank tenant.
    
    Bank admins only can cancel jobs.
    """
    try:
        job = db.query(JobQueue).filter(
            and_(
                JobQueue.id == job_id,
                JobQueue.organization_id == current_user.company_id
            )
        ).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or not accessible"
            )

        if job.status not in [JobStatus.QUEUED, JobStatus.RUNNING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job with status {job.status}"
            )

        job.status = JobStatus.CANCELLED
        job.failed_at = datetime.utcnow()
        job.error_message = f"Cancelled by bank admin: {reason}"

        db.commit()

        # Audit log
        await AuditService.log_action(
            db=db,
            actor_id=current_user.id,
            actor_type="user",
            resource_type="job_queue",
            resource_id=str(job_id),
            organization_id=current_user.company_id,
            action=AuditAction.UPDATE,
            result=AuditResult.SUCCESS,
            metadata={"action": "cancel", "reason": reason}
        )

        logger.info(
            f"Job {job_id} cancelled by bank admin {current_user.id}, "
            f"reason: {reason}"
        )

        return {"message": "Job cancelled", "job_id": str(job_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job"
        )


@router.post("/{job_id}/requeue")
async def requeue_bank_job(
    job_id: UUID,
    reason: Optional[str] = Query(None, description="Reason for requeue"),
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """
    Requeue a specific job in the bank tenant.
    
    Bank admins only can requeue jobs.
    """
    try:
        job = db.query(JobQueue).filter(
            and_(
                JobQueue.id == job_id,
                JobQueue.organization_id == current_user.company_id
            )
        ).first()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found or not accessible"
            )

        job.status = JobStatus.QUEUED
        job.scheduled_at = datetime.utcnow()

        db.commit()

        # Audit log
        await AuditService.log_action(
            db=db,
            actor_id=current_user.id,
            actor_type="user",
            resource_type="job_queue",
            resource_id=str(job_id),
            organization_id=current_user.company_id,
            action=AuditAction.UPDATE,
            result=AuditResult.SUCCESS,
            metadata={"action": "requeue", "reason": reason or "Manual requeue"}
        )

        logger.info(
            f"Job {job_id} requeued by bank admin {current_user.id}"
        )

        return {"message": "Job requeued", "job_id": str(job_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to requeue job {job_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to requeue job"
        )


@router.post("/bulk-action")
async def bulk_bank_job_action(
    action_request: BulkJobAction,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """
    Perform bulk actions on multiple jobs in the bank tenant.
    
    Bank admins only can perform bulk actions.
    """
    try:
        # Scope to bank tenant and filter by job IDs
        jobs = db.query(JobQueue).filter(
            and_(
                JobQueue.id.in_([UUID(jid) for jid in action_request.job_ids]),
                JobQueue.organization_id == current_user.company_id
            )
        ).all()

        if len(jobs) != len(action_request.job_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Some jobs not found or not accessible"
            )

        success_count = 0
        failed_jobs = []

        for job in jobs:
            try:
                if action_request.action == "retry":
                    if job.status in [JobStatus.FAILED, JobStatus.CANCELLED]:
                        job.status = JobStatus.QUEUED
                        job.attempts = 0
                        job.error_message = None
                        job.scheduled_at = datetime.utcnow()
                        success_count += 1
                    else:
                        failed_jobs.append(str(job.id))

                elif action_request.action == "cancel":
                    if job.status in [JobStatus.QUEUED, JobStatus.RUNNING]:
                        job.status = JobStatus.CANCELLED
                        job.failed_at = datetime.utcnow()
                        job.error_message = f"Bulk cancelled: {action_request.reason}"
                        success_count += 1
                    else:
                        failed_jobs.append(str(job.id))

                elif action_request.action == "requeue":
                    job.status = JobStatus.QUEUED
                    job.scheduled_at = datetime.utcnow()
                    success_count += 1

            except Exception as e:
                logger.error(f"Failed to {action_request.action} job {job.id}: {str(e)}")
                failed_jobs.append(str(job.id))

        db.commit()

        # Audit log
        await AuditService.log_action(
            db=db,
            actor_id=current_user.id,
            actor_type="user",
            resource_type="job_queue",
            resource_id=None,
            organization_id=current_user.company_id,
            action=AuditAction.UPDATE,
            result=AuditResult.SUCCESS,
            metadata={
                "action": action_request.action,
                "job_count": len(action_request.job_ids),
                "success_count": success_count,
                "failed_jobs": failed_jobs,
                "reason": action_request.reason
            }
        )

        logger.info(
            f"Bulk {action_request.action} by bank admin {current_user.id}: "
            f"{success_count} succeeded, {len(failed_jobs)} failed"
        )

        return {
            "action": action_request.action,
            "success_count": success_count,
            "failed_jobs": failed_jobs,
            "reason": action_request.reason
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to perform bulk action: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk action"
        )

