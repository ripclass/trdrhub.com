"""Customer-facing bulk LC validation API — Phase A1 part 2.

Endpoints (all under ``/api/bulk-validate``):

  * ``POST /``                — Create a job (PENDING). Returns job_id.
  * ``POST /{job_id}/items``  — Multipart upload: one item per LC, multiple
                                 PDFs per item via the ``files`` field plus
                                 ``lc_identifier`` form field.
  * ``POST /{job_id}/run``    — Kick off the worker via BackgroundTasks.
                                 Idempotent: a no-op on already-running jobs.
  * ``GET  /{job_id}``        — Fetch job + per-item status.
  * ``GET  /{job_id}/stream`` — Server-Sent Events progress stream.
  * ``POST /{job_id}/cancel`` — Stop the run after in-flight items finish.

Auth: standard JWT via ``get_current_user``. Tenant scoping uses the
caller's ``company_id``. Other companies' jobs return 404 (don't leak
their existence).

Job type is ``customer_lc_validation`` — distinct from the bank-side
``lc_validation`` so we don't have to satisfy
``BulkProcessor._validate_job_config``'s bank-internal config keys.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..database import get_db
from ..models import User
from ..models.bulk_jobs import (
    BulkItem,
    BulkJob,
    ItemStatus,
    JobEvent,
    JobEventType,
    JobStatus,
)
from ..services.bulk_progress_broker import broker
from ..services.bulk_validate_processor import (
    CUSTOMER_LC_VALIDATION_JOB_TYPE,
    BulkValidateProcessor,
    storage_dir_for_job,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bulk-validate", tags=["bulk-validate"])


# Per-process registry of currently-running processors so cancel can
# reach them. Keyed by job_id string. Cleared on job completion. Race-
# safe enough for single-instance — multi-instance needs a real cancel
# channel via Redis.
_active_processors: dict[str, BulkValidateProcessor] = {}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class BulkValidateJobCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = Field(None, max_length=2000)
    concurrency: Optional[int] = Field(
        None, ge=1, le=16, description="Override default concurrency"
    )


class BulkValidateItemRead(BaseModel):
    id: UUID
    lc_identifier: str
    status: str
    attempts: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_ms: Optional[int]
    last_error: Optional[str]
    error_code: Optional[str]
    result_summary: Optional[dict]

    @classmethod
    def from_orm_item(cls, item: BulkItem) -> "BulkValidateItemRead":
        return cls(
            id=item.id,
            lc_identifier=item.lc_identifier,
            status=item.status,
            attempts=item.attempts or 0,
            started_at=item.started_at,
            finished_at=item.finished_at,
            duration_ms=item.duration_ms,
            last_error=item.last_error,
            error_code=item.error_code,
            result_summary=item.result_data,
        )


class BulkValidateJobRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    status: str
    total_items: int
    processed_items: int
    succeeded_items: int
    failed_items: int
    skipped_items: int
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_seconds: Optional[int]
    created_at: datetime
    items: List[BulkValidateItemRead] = Field(default_factory=list)


class BulkValidateJobCreateResponse(BaseModel):
    job_id: UUID
    status: str
    name: str


class BulkValidateItemUploadResponse(BaseModel):
    item_id: UUID
    lc_identifier: str
    file_count: int


class BulkValidateRunResponse(BaseModel):
    job_id: UUID
    status: str
    queued: bool
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tenant_id_for(user: User) -> str:
    """Tenant scoping key. Falls back to user_id for users without a
    company (early-onboarding accounts).
    """
    company_id = getattr(user, "company_id", None)
    return str(company_id) if company_id is not None else str(user.id)


def _get_owned_job(db: Session, user: User, job_id: UUID) -> BulkJob:
    """Fetch a job that belongs to the caller's tenant. 404 otherwise —
    don't leak existence of other tenants' jobs.
    """
    job = (
        db.query(BulkJob)
        .filter(
            BulkJob.id == job_id,
            BulkJob.tenant_id == _tenant_id_for(user),
            BulkJob.job_type == CUSTOMER_LC_VALIDATION_JOB_TYPE,
        )
        .first()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


# ---------------------------------------------------------------------------
# 1. Create job
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=BulkValidateJobCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_bulk_job(
    body: BulkValidateJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config: dict = {"description": body.description}
    if body.concurrency is not None:
        config["concurrency"] = body.concurrency

    job = BulkJob(
        tenant_id=_tenant_id_for(current_user),
        name=body.name,
        description=body.description,
        job_type=CUSTOMER_LC_VALIDATION_JOB_TYPE,
        config=config,
        created_by=current_user.id,
        status=JobStatus.PENDING.value,
        total_items=0,
    )
    db.add(job)
    db.flush()
    db.add(
        JobEvent(
            job_id=job.id,
            event_type=JobEventType.CREATED.value,
            event_data={"job_type": CUSTOMER_LC_VALIDATION_JOB_TYPE, "name": body.name},
            user_id=current_user.id,
        )
    )
    db.commit()
    db.refresh(job)

    # Pre-create the storage dir so /items can drop files there.
    storage_dir_for_job(job.id)

    return BulkValidateJobCreateResponse(
        job_id=job.id, status=job.status, name=job.name
    )


# ---------------------------------------------------------------------------
# 2. Upload one item (one LC + N supporting PDFs)
# ---------------------------------------------------------------------------


@router.post(
    "/{job_id}/items",
    response_model=BulkValidateItemUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_bulk_item(
    job_id: UUID,
    lc_identifier: str = Form(..., min_length=1, max_length=128),
    supplier_id: Optional[UUID] = Form(
        None,
        description="Phase A6 — agency attribution. When provided, the resulting "
        "ValidationSession lands under this supplier in the agent's portfolio.",
    ),
    files: List[UploadFile] = File(..., description="LC PDF + supporting PDFs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = _get_owned_job(db, current_user, job_id)
    if job.status not in (JobStatus.PENDING.value, JobStatus.PENDING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot add items to job in status={job.status}",
        )
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file required",
        )

    # Persist files to per-job storage dir. Filename includes the future
    # item_id prefix so collisions across items in the same job are
    # impossible even if the customer reuses filenames.
    import uuid as _uuid

    job_dir = storage_dir_for_job(job.id)
    item_id = _uuid.uuid4()
    item_dir = job_dir / str(item_id)
    item_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: List[str] = []
    for upload in files:
        if not upload.filename:
            continue
        # Strip path separators that could escape item_dir.
        safe_name = upload.filename.replace("/", "_").replace("\\", "_")
        target = item_dir / safe_name
        with target.open("wb") as out:
            shutil.copyfileobj(upload.file, out)
        saved_paths.append(str(target))

    if not saved_paths:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No usable files in upload",
        )

    # Phase A6 — validate supplier_id ownership before storing it.
    # Cross-company ids get warned + dropped silently, same defensive
    # shape as session_setup uses for the single-validate path.
    validated_supplier_id: Optional[str] = None
    if supplier_id is not None and getattr(current_user, "company_id", None):
        from app.models.agency import Supplier as _Supplier

        owned = (
            db.query(_Supplier)
            .filter(_Supplier.id == supplier_id)
            .filter(_Supplier.agent_company_id == current_user.company_id)
            .filter(_Supplier.deleted_at.is_(None))
            .first()
        )
        if owned is not None:
            validated_supplier_id = str(supplier_id)

    item_data: dict = {
        "file_paths": saved_paths,
        "uploaded_filenames": [f.filename for f in files if f.filename],
    }
    if validated_supplier_id:
        item_data["supplier_id"] = validated_supplier_id

    item = BulkItem(
        id=item_id,
        job_id=job.id,
        lc_identifier=lc_identifier,
        item_data=item_data,
        status=ItemStatus.PENDING.value,
    )
    db.add(item)
    job.total_items = (job.total_items or 0) + 1
    db.commit()
    db.refresh(item)

    return BulkValidateItemUploadResponse(
        item_id=item.id,
        lc_identifier=item.lc_identifier,
        file_count=len(saved_paths),
    )


# ---------------------------------------------------------------------------
# 3. Run job (kicks the BackgroundTasks worker)
# ---------------------------------------------------------------------------


@router.post(
    "/{job_id}/run",
    response_model=BulkValidateRunResponse,
)
async def run_bulk_job(
    job_id: UUID,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = _get_owned_job(db, current_user, job_id)

    if job.status == JobStatus.RUNNING.value:
        return BulkValidateRunResponse(
            job_id=job.id,
            status=job.status,
            queued=False,
            message="Job already running",
        )
    if job.status not in (JobStatus.PENDING.value,):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot run job in status={job.status}",
        )
    if (job.total_items or 0) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No items to process — upload items first",
        )

    # Phase A4 — refuse upfront if this bulk run would push the
    # company past its monthly quota. The per-item EntitlementService
    # check inside the validation pipeline catches mid-run overflow,
    # but Solo-tier users uploading 12 LCs deserve a clean rejection
    # before the worker burns minutes on items #1-#10.
    if current_user.email != "demo@trdrhub.com" and current_user.company is not None:
        from app.models import UsageAction
        from app.services.entitlements import EntitlementError, EntitlementService

        try:
            EntitlementService(db).enforce_bulk_quota(
                current_user.company,
                UsageAction.VALIDATE,
                count=int(job.total_items or 0),
            )
        except EntitlementError as exc:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": exc.code,
                    "message": exc.message,
                    "quota": exc.result.to_dict(),
                    "next_action_url": exc.next_action_url,
                },
            ) from exc

    # Concurrency override from the original create request.
    config = job.config or {}
    concurrency = int(config.get("concurrency") or 0) or None
    processor = (
        BulkValidateProcessor(concurrency=concurrency)
        if concurrency
        else BulkValidateProcessor()
    )
    _active_processors[str(job.id)] = processor

    async def _runner() -> None:
        try:
            await processor.run(job_id=job.id, current_user=current_user)
        finally:
            _active_processors.pop(str(job.id), None)

    background.add_task(_runner)

    return BulkValidateRunResponse(
        job_id=job.id,
        status=JobStatus.RUNNING.value,
        queued=True,
        message=f"Queued {job.total_items} item(s) for processing",
    )


# ---------------------------------------------------------------------------
# 4. Get job + items
# ---------------------------------------------------------------------------


@router.get("", response_model=List[BulkValidateJobRead])
async def list_bulk_jobs(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recent bulk jobs for the caller's tenant. Phase A6 slice 3 —
    feeds the agent's "Recent jobs" panel under the Bulk Inbox.
    """
    capped = max(1, min(int(limit or 20), 100))
    jobs = (
        db.query(BulkJob)
        .filter(BulkJob.tenant_id == _tenant_id_for(current_user))
        .filter(BulkJob.job_type == CUSTOMER_LC_VALIDATION_JOB_TYPE)
        .order_by(BulkJob.created_at.desc())
        .limit(capped)
        .all()
    )
    if not jobs:
        return []
    job_ids = [j.id for j in jobs]
    items_by_job: dict = {}
    rows = (
        db.query(BulkItem)
        .filter(BulkItem.job_id.in_(job_ids))
        .order_by(BulkItem.created_at.asc())
        .all()
    )
    for r in rows:
        items_by_job.setdefault(r.job_id, []).append(r)

    return [
        BulkValidateJobRead(
            id=j.id,
            name=j.name,
            description=j.description,
            status=j.status,
            total_items=j.total_items or 0,
            processed_items=j.processed_items or 0,
            succeeded_items=j.succeeded_items or 0,
            failed_items=j.failed_items or 0,
            skipped_items=j.skipped_items or 0,
            started_at=j.started_at,
            finished_at=j.finished_at,
            duration_seconds=j.duration_seconds,
            created_at=j.created_at,
            items=[
                BulkValidateItemRead.from_orm_item(i)
                for i in items_by_job.get(j.id, [])
            ],
        )
        for j in jobs
    ]


@router.get("/{job_id}", response_model=BulkValidateJobRead)
async def get_bulk_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = _get_owned_job(db, current_user, job_id)
    items = (
        db.query(BulkItem)
        .filter(BulkItem.job_id == job.id)
        .order_by(BulkItem.created_at.asc())
        .all()
    )
    return BulkValidateJobRead(
        id=job.id,
        name=job.name,
        description=job.description,
        status=job.status,
        total_items=job.total_items or 0,
        processed_items=job.processed_items or 0,
        succeeded_items=job.succeeded_items or 0,
        failed_items=job.failed_items or 0,
        skipped_items=job.skipped_items or 0,
        started_at=job.started_at,
        finished_at=job.finished_at,
        duration_seconds=job.duration_seconds,
        created_at=job.created_at,
        items=[BulkValidateItemRead.from_orm_item(i) for i in items],
    )


# ---------------------------------------------------------------------------
# 5. SSE progress stream
# ---------------------------------------------------------------------------


@router.get("/{job_id}/stream")
async def stream_bulk_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Auth + tenant scope check before opening the stream.
    _get_owned_job(db, current_user, job_id)

    async def _event_source():
        # Initial hello event so consumers can confirm the stream is open
        # before any worker activity.
        yield f"event: ready\ndata: {json.dumps({'job_id': str(job_id)})}\n\n"
        try:
            async for event in broker.subscribe(job_id):
                event_type = str(event.get("event") or "progress")
                yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:  # pragma: no cover — client disconnect
            return

    return StreamingResponse(
        _event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disables proxy buffering on Render
        },
    )


# ---------------------------------------------------------------------------
# 6. Cancel
# ---------------------------------------------------------------------------


@router.post("/{job_id}/cancel", response_model=BulkValidateJobRead)
async def cancel_bulk_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = _get_owned_job(db, current_user, job_id)

    if job.status in (
        JobStatus.SUCCEEDED.value,
        JobStatus.FAILED.value,
        JobStatus.CANCELLED.value,
        JobStatus.PARTIAL.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job already terminal status={job.status}",
        )

    processor = _active_processors.get(str(job.id))
    if processor is not None:
        processor.cancel()
        await broker.publish(
            job.id,
            {"event": "cancel_requested", "job_id": str(job.id)},
        )
    else:
        # No active processor — the job was created but never run, or
        # the worker died. Mark CANCELLED directly.
        job.status = JobStatus.CANCELLED.value
        job.finished_at = datetime.utcnow()
        db.add(
            JobEvent(
                job_id=job.id,
                event_type=JobEventType.CANCELLED.value,
                event_data={"reason": "no_active_processor"},
                user_id=current_user.id,
            )
        )
        db.commit()

    db.refresh(job)
    items = (
        db.query(BulkItem)
        .filter(BulkItem.job_id == job.id)
        .order_by(BulkItem.created_at.asc())
        .all()
    )
    return BulkValidateJobRead(
        id=job.id,
        name=job.name,
        description=job.description,
        status=job.status,
        total_items=job.total_items or 0,
        processed_items=job.processed_items or 0,
        succeeded_items=job.succeeded_items or 0,
        failed_items=job.failed_items or 0,
        skipped_items=job.skipped_items or 0,
        started_at=job.started_at,
        finished_at=job.finished_at,
        duration_seconds=job.duration_seconds,
        created_at=job.created_at,
        items=[BulkValidateItemRead.from_orm_item(i) for i in items],
    )


__all__ = ["router"]
