"""
Admin Jobs Router

Handles job queue management, DLQ operations, and workflow control.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.auth import get_current_admin_user, require_permissions
from app.models.user import User
from app.models.admin import JobQueue, JobDLQ, JobHistory, JobStatus
from app.schemas.admin import (
    JobFilter, JobQueue as JobQueueSchema, JobDLQ as JobDLQSchema,
    BulkJobAction, DLQReplayRequest, BulkDLQReplay, PaginatedResponse
)

router = APIRouter(prefix="/jobs", tags=["Job Management"])
logger = logging.getLogger(__name__)


@router.get("/queue", response_model=PaginatedResponse)
async def get_job_queue(
    filters: JobFilter = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    _: None = Depends(require_permissions(["jobs:read"]))
):
    """
    Get job queue with filtering and pagination.

    Requires: jobs:read permission
    """
    try:
        query = db.query(JobQueue)

        # Apply filters
        if filters.status:
            query = query.filter(JobQueue.status == filters.status)
        if filters.job_type:
            query = query.filter(JobQueue.job_type == filters.job_type)
        if filters.organization_id:
            query = query.filter(JobQueue.organization_id == filters.organization_id)
        if filters.created_after:
            query = query.filter(JobQueue.created_at >= filters.created_after)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        jobs = query.order_by(
            JobQueue.priority.desc(),
            JobQueue.scheduled_at.asc()
        ).offset(filters.offset).limit(filters.limit).all()

        # Convert to response schemas
        job_schemas = [JobQueueSchema.from_orm(job) for job in jobs]

        response = PaginatedResponse(
            items=job_schemas,
            total=total,
            page=filters.offset // filters.limit + 1,
            size=filters.limit,
            pages=(total + filters.limit - 1) // filters.limit
        )

        logger.info(f"Job queue queried by admin {current_user.id}, returned {len(jobs)} jobs")
        return response

    except Exception as e:
        logger.error(f"Failed to query job queue: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query job queue"
        )


@router.get("/queue/stats")
async def get_queue_stats(
    time_range: str = Query("24h", regex="^(1h|6h|24h|7d)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    _: None = Depends(require_permissions(["jobs:read"]))
):
    """
    Get job queue statistics and metrics.

    Requires: jobs:read permission
    """
    try:
        # Calculate time range
        hours_map = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}
        hours = hours_map.get(time_range, 24)
        since_time = datetime.utcnow() - timedelta(hours=hours)

        # Query statistics
        total_jobs = db.query(func.count(JobQueue.id)).filter(
            JobQueue.created_at >= since_time
        ).scalar()

        status_counts = db.query(
            JobQueue.status,
            func.count(JobQueue.id)
        ).filter(
            JobQueue.created_at >= since_time
        ).group_by(JobQueue.status).all()

        type_counts = db.query(
            JobQueue.job_type,
            func.count(JobQueue.id)
        ).filter(
            JobQueue.created_at >= since_time
        ).group_by(JobQueue.job_type).all()

        # Average processing time for completed jobs
        avg_processing_time = db.query(
            func.avg(
                func.extract('epoch', JobQueue.completed_at - JobQueue.started_at) * 1000
            )
        ).filter(
            and_(
                JobQueue.status == JobStatus.COMPLETED,
                JobQueue.completed_at.isnot(None),
                JobQueue.started_at.isnot(None),
                JobQueue.created_at >= since_time
            )
        ).scalar()

        stats = {
            "time_range": time_range,
            "total_jobs": total_jobs,
            "status_breakdown": {status: count for status, count in status_counts},
            "type_breakdown": {job_type: count for job_type, count in type_counts},
            "avg_processing_time_ms": int(avg_processing_time) if avg_processing_time else 0,
            "queue_depth": db.query(func.count(JobQueue.id)).filter(
                JobQueue.status.in_([JobStatus.QUEUED, JobStatus.RUNNING])
            ).scalar()
        }

        logger.info(f"Queue stats requested by admin {current_user.id} for {time_range}")
        return stats

    except Exception as e:
        logger.error(f"Failed to get queue stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get queue stats"
        )


@router.post("/queue/{job_id}/retry")
async def retry_job(
    job_id: str,
    reason: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    _: None = Depends(require_permissions(["jobs:write"]))
):
    """
    Retry a specific job.

    Requires: jobs:write permission
    """
    try:
        job = db.query(JobQueue).filter(JobQueue.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
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

        # TODO: Audit log the retry action
        logger.info(f"Job {job_id} retried by admin {current_user.id}, reason: {reason}")

        return {"message": "Job queued for retry", "job_id": job_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry job {job_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retry job"
        )


@router.post("/queue/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    reason: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    _: None = Depends(require_permissions(["jobs:write"]))
):
    """
    Cancel a specific job.

    Requires: jobs:write permission
    """
    try:
        job = db.query(JobQueue).filter(JobQueue.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        if job.status not in [JobStatus.QUEUED, JobStatus.RUNNING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job with status {job.status}"
            )

        job.status = JobStatus.CANCELLED
        job.failed_at = datetime.utcnow()
        job.error_message = f"Cancelled by admin: {reason}"

        db.commit()

        # TODO: Signal worker to stop if job is running
        # TODO: Audit log the cancellation

        logger.info(f"Job {job_id} cancelled by admin {current_user.id}, reason: {reason}")

        return {"message": "Job cancelled", "job_id": job_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job"
        )


@router.post("/queue/bulk-action")
async def bulk_job_action(
    action_request: BulkJobAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    _: None = Depends(require_permissions(["jobs:write"]))
):
    """
    Perform bulk actions on multiple jobs.

    Requires: jobs:write permission
    """
    try:
        jobs = db.query(JobQueue).filter(
            JobQueue.id.in_(action_request.job_ids)
        ).all()

        if len(jobs) != len(action_request.job_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Some jobs not found"
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

        logger.info(
            f"Bulk {action_request.action} by admin {current_user.id}: "
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
        logger.error(f"Failed to perform bulk action: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk action"
        )


@router.get("/dlq", response_model=PaginatedResponse)
async def get_dlq(
    job_type: Optional[str] = Query(None),
    failure_reason: Optional[str] = Query(None),
    can_retry: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    _: None = Depends(require_permissions(["jobs:read"]))
):
    """
    Get dead letter queue entries with filtering.

    Requires: jobs:read permission
    """
    try:
        query = db.query(JobDLQ)

        # Apply filters
        if job_type:
            query = query.filter(JobDLQ.job_type == job_type)
        if failure_reason:
            query = query.filter(JobDLQ.failure_reason.ilike(f"%{failure_reason}%"))
        if can_retry is not None:
            query = query.filter(JobDLQ.can_retry == can_retry)

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        dlq_entries = query.order_by(
            JobDLQ.created_at.desc()
        ).offset(offset).limit(limit).all()

        # Convert to response schemas
        dlq_schemas = [JobDLQSchema.from_orm(entry) for entry in dlq_entries]

        response = PaginatedResponse(
            items=dlq_schemas,
            total=total,
            page=offset // limit + 1,
            size=limit,
            pages=(total + limit - 1) // limit
        )

        logger.info(f"DLQ queried by admin {current_user.id}, returned {len(dlq_entries)} entries")
        return response

    except Exception as e:
        logger.error(f"Failed to query DLQ: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query DLQ"
        )


@router.post("/dlq/{dlq_id}/replay")
async def replay_dlq_entry(
    dlq_id: str,
    replay_request: DLQReplayRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    _: None = Depends(require_permissions(["jobs:write"]))
):
    """
    Replay a single DLQ entry.

    Requires: jobs:write permission
    """
    try:
        dlq_entry = db.query(JobDLQ).filter(JobDLQ.id == dlq_id).first()
        if not dlq_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="DLQ entry not found"
            )

        if not dlq_entry.can_retry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="DLQ entry is marked as non-retryable"
            )

        # Create new job from DLQ entry
        job_data = dlq_entry.job_data.copy()
        if replay_request.modify_payload:
            job_data.update(replay_request.modify_payload)

        new_job = JobQueue(
            job_type=dlq_entry.job_type,
            job_data=job_data,
            priority=5,
            status=JobStatus.QUEUED,
            max_attempts=replay_request.retry_count,
            scheduled_at=datetime.utcnow() + timedelta(seconds=replay_request.delay_seconds)
        )

        db.add(new_job)

        # Mark DLQ entry as resolved
        dlq_entry.resolved_at = datetime.utcnow()
        dlq_entry.resolved_by = current_user.id

        db.commit()

        logger.info(f"DLQ entry {dlq_id} replayed by admin {current_user.id}")

        return {
            "message": "DLQ entry replayed",
            "new_job_id": str(new_job.id),
            "scheduled_at": new_job.scheduled_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to replay DLQ entry {dlq_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to replay DLQ entry"
        )


@router.post("/dlq/bulk-replay")
async def bulk_replay_dlq(
    replay_request: BulkDLQReplay,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    _: None = Depends(require_permissions(["jobs:write"]))
):
    """
    Replay multiple DLQ entries with various strategies.

    Requires: jobs:write permission
    """
    try:
        dlq_entries = db.query(JobDLQ).filter(
            JobDLQ.id.in_(replay_request.dlq_ids)
        ).all()

        if len(dlq_entries) != len(replay_request.dlq_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Some DLQ entries not found"
            )

        success_count = 0
        failed_entries = []

        for i, dlq_entry in enumerate(dlq_entries):
            try:
                if not dlq_entry.can_retry:
                    failed_entries.append(str(dlq_entry.id))
                    continue

                # Calculate delay based on strategy
                delay_seconds = 0
                if replay_request.strategy == "throttled" and replay_request.throttle_rate:
                    # Stagger jobs based on throttle rate (jobs per minute)
                    delay_seconds = (i * 60) // replay_request.throttle_rate

                # Create new job
                new_job = JobQueue(
                    job_type=dlq_entry.job_type,
                    job_data=dlq_entry.job_data,
                    priority=5,
                    status=JobStatus.QUEUED,
                    scheduled_at=datetime.utcnow() + timedelta(seconds=delay_seconds)
                )

                db.add(new_job)

                # Mark DLQ entry as resolved
                dlq_entry.resolved_at = datetime.utcnow()
                dlq_entry.resolved_by = current_user.id

                success_count += 1

            except Exception as e:
                logger.error(f"Failed to replay DLQ entry {dlq_entry.id}: {str(e)}")
                failed_entries.append(str(dlq_entry.id))

        db.commit()

        logger.info(
            f"Bulk DLQ replay by admin {current_user.id}: "
            f"{success_count} succeeded, {len(failed_entries)} failed"
        )

        return {
            "strategy": replay_request.strategy,
            "success_count": success_count,
            "failed_entries": failed_entries,
            "throttle_rate": replay_request.throttle_rate
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to perform bulk DLQ replay: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk DLQ replay"
        )


@router.get("/history/{job_id}")
async def get_job_history(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    _: None = Depends(require_permissions(["jobs:read"]))
):
    """
    Get execution history for a specific job.

    Requires: jobs:read permission
    """
    try:
        history_entries = db.query(JobHistory).filter(
            JobHistory.job_id == job_id
        ).order_by(JobHistory.created_at.asc()).all()

        if not history_entries:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job history not found"
            )

        history_data = {
            "job_id": job_id,
            "total_steps": len(history_entries),
            "total_duration_ms": sum(h.duration_ms or 0 for h in history_entries),
            "steps": [
                {
                    "step_name": h.step_name,
                    "status": h.status,
                    "duration_ms": h.duration_ms,
                    "memory_mb": h.memory_mb,
                    "cpu_percent": float(h.cpu_percent) if h.cpu_percent else None,
                    "step_data": h.step_data,
                    "timestamp": h.created_at
                }
                for h in history_entries
            ]
        }

        logger.info(f"Job history for {job_id} requested by admin {current_user.id}")
        return history_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job history for {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job history"
        )