"""Bulk LC validation processor — Phase A1 part 2.

Customer-facing bulk pipeline. Companies (especially buying houses,
sourcing agents, and trading groups) need to validate dozens of LCs in
a single sitting. This processor:

  * Owns ``job_type = 'customer_lc_validation'``. Independent of the
    bank-side ``lc_validation`` job_type so we don't have to touch
    ``BulkProcessor._validate_job_config`` rules.
  * Spawns a real :class:`ValidationSession` per item by calling
    :func:`run_validate_pipeline` directly (the same code path the
    single-LC HTTP endpoint hits — no simulation).
  * Caps per-job concurrency via ``asyncio.Semaphore`` (default 4,
    overridable by ``BULK_CONCURRENCY`` env). Protects LLM rate limits
    and RulHub.
  * Caps total job lifetime at 30 minutes. Exceeding marks the job
    FAILED with reason ``"timeout"`` and items still PENDING get
    SKIPPED.
  * Publishes per-item progress events to
    :data:`app.services.bulk_progress_broker.broker` so the SSE
    endpoint can stream them to the dashboard live.
  * Writes ``bulk_job_id`` / ``bulk_item_id`` back onto the
    :class:`ValidationSession` row so reverse-lookup works.
  * On per-item success, transitions the session lifecycle to
    ``under_bank_review`` via the helper from Phase A1 part 1.

Single-instance assumption: the broker is process-local and files
live on local disk under ``settings.BULK_VALIDATE_STORAGE_DIR``. If
trdrhub-api goes multi-instance, the broker becomes Redis and the file
store becomes S3 — those are the two seams. Documented as v1.1
follow-up in SESSION_RESUME.

Failure isolation: an exception inside one item's validation is caught,
logged, recorded as a BulkFailure row, and the job continues with the
remaining items. A failure during the lifecycle transition is logged
but doesn't fail the item — the validation result is still good even
if the audit hop misfires.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import ValidationSession
from app.models.bulk_jobs import (
    BulkFailure,
    BulkItem,
    BulkJob,
    ItemStatus,
    JobEvent,
    JobEventType,
    JobStatus,
)
from app.models.lc_lifecycle import LCLifecycleState
from app.services.bulk_progress_broker import broker
from app.services.lc_lifecycle import (
    InvalidLifecycleTransition,
    transition as lifecycle_transition,
)

logger = logging.getLogger(__name__)


CUSTOMER_LC_VALIDATION_JOB_TYPE = "customer_lc_validation"

# Hard caps. Keep them low enough that a runaway job can't take down a
# production instance. Adjust via env if a customer is truly going to
# bulk-validate hundreds at once.
DEFAULT_CONCURRENCY = int(os.getenv("BULK_CONCURRENCY", "4"))
DEFAULT_JOB_TIMEOUT_SECONDS = int(os.getenv("BULK_JOB_TIMEOUT_SECONDS", "1800"))
DEFAULT_PER_ITEM_TIMEOUT_SECONDS = int(os.getenv("BULK_ITEM_TIMEOUT_SECONDS", "600"))


def _storage_root() -> Path:
    """Where bulk-uploaded LC PDFs live before the worker picks them up."""
    base = getattr(settings, "BULK_VALIDATE_STORAGE_DIR", None) or os.getenv(
        "BULK_VALIDATE_STORAGE_DIR", "/tmp/lcopilot-bulk"
    )
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def storage_dir_for_job(job_id: UUID | str) -> Path:
    path = _storage_root() / str(job_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Request-stub adapter
# ---------------------------------------------------------------------------


class _DiskUploadFile:
    """Mimics the slim subset of ``starlette.UploadFile`` that the
    validation pipeline actually touches.

    The real ``_build_document_context`` only calls ``.filename`` and
    ``await upload_file.read()``. That's the entire surface area, so
    the adapter stays small.
    """

    def __init__(self, path: Path, filename: Optional[str] = None) -> None:
        self.filename = filename or path.name
        # Mirror the UploadFile attribute so any adjacent code that probes
        # ``content_type`` doesn't get None — bulk LCs are PDFs.
        self.content_type = "application/pdf"
        self._path = path

    async def read(self) -> bytes:
        return self._path.read_bytes()

    async def seek(self, _pos: int) -> int:  # pragma: no cover — defensive
        return 0

    async def close(self) -> None:  # pragma: no cover — defensive
        return None


def _build_request_stub(current_user: Any) -> Any:
    """Synthesize the slim ``request`` object the pipeline expects.

    The pipeline reads ``request.headers.get(...)`` and
    ``request.state.org_id`` only. Everything else is gated by
    ``hasattr`` checks. A SimpleNamespace covers it.
    """
    state = SimpleNamespace()
    if getattr(current_user, "company_id", None) is not None:
        state.org_id = str(current_user.company_id)
    return SimpleNamespace(headers={}, state=state)


# ---------------------------------------------------------------------------
# Pipeline entry-point — overridable for tests.
# ---------------------------------------------------------------------------


# A plain module-level callable so tests can monkeypatch it without
# digging into the processor instance. Default points at the real
# pipeline; tests swap it for a fast mock.
async def _default_run_validate_pipeline(**kwargs: Any) -> Any:
    # Imported lazily to avoid pulling the entire validation graph at
    # module-import time (which keeps test startup snappy).
    from app.routers.validation.pipeline_runner import run_validate_pipeline

    return await run_validate_pipeline(**kwargs)


# Tests do: ``bulk_validate_processor._pipeline_runner = my_mock``.
_pipeline_runner: Callable[..., Awaitable[Any]] = _default_run_validate_pipeline


# ---------------------------------------------------------------------------
# Item-input model
# ---------------------------------------------------------------------------


@dataclass
class BulkItemInput:
    """One LC presentation to validate.

    ``files`` is the full set of uploaded PDFs for this LC — typically
    one LC document plus N supporting documents (invoice, BL, packing
    list, etc.). The first file matching ``letter_of_credit`` is treated
    as the LC itself; the rest are supporting docs. Naming convention is
    documented in the upload endpoint.
    """

    lc_identifier: str
    file_paths: List[Path]
    source_ref: Optional[str] = None
    document_tags: Optional[dict] = None


# ---------------------------------------------------------------------------
# Processor
# ---------------------------------------------------------------------------


class BulkValidateProcessor:
    """Async, in-process bulk validator. One instance per job run."""

    def __init__(
        self,
        *,
        concurrency: int = DEFAULT_CONCURRENCY,
        job_timeout_seconds: int = DEFAULT_JOB_TIMEOUT_SECONDS,
        per_item_timeout_seconds: int = DEFAULT_PER_ITEM_TIMEOUT_SECONDS,
    ) -> None:
        self.concurrency = max(1, concurrency)
        self.job_timeout_seconds = max(1, job_timeout_seconds)
        self.per_item_timeout_seconds = max(1, per_item_timeout_seconds)
        # Set on cancel(); checked between items so the loop drains
        # cleanly without orphaning work mid-LLM.
        self._cancel_flag = asyncio.Event()

    # ------------------------------------------------------------------
    # Public entry — call from FastAPI BackgroundTasks.
    # ------------------------------------------------------------------

    async def run(
        self,
        *,
        job_id: UUID,
        current_user: Any,
    ) -> None:
        """Execute every PENDING item in ``job_id``. Idempotent.

        Opens its own DB session — DO NOT pass the request session in;
        background tasks outlive the request lifecycle and FastAPI
        teardown will close it underneath us.

        ``current_user`` is read for ``.id`` and (optionally)
        ``.company_id`` only. Both are cached scalars on the SQLAlchemy
        instance so detachment after the originating request closes is
        harmless. Tests can pass a ``SimpleNamespace`` with the same
        attribute shape.
        """
        # Each background run gets its own session bound to the same
        # engine. Cleaner than borrowing the request session and racing
        # FastAPI's dependency teardown.
        db = SessionLocal()
        try:
            job = db.query(BulkJob).filter(BulkJob.id == job_id).first()
            if job is None:
                logger.error("BulkValidateProcessor.run: job %s not found", job_id)
                return
            status_value = (
                job.status.value if hasattr(job.status, "value") else job.status
            )
            if status_value not in (
                JobStatus.PENDING.value,
                JobStatus.RUNNING.value,
            ):
                logger.warning(
                    "BulkValidateProcessor.run: job %s already terminal status=%s — skipping",
                    job_id,
                    status_value,
                )
                return

            await self._mark_job_started(db, job)
            await broker.publish(
                job_id, {"event": "job_started", "total_items": job.total_items}
            )

            try:
                await asyncio.wait_for(
                    self._process_items(db, job, current_user),
                    timeout=self.job_timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "BulkValidateProcessor.run: job %s exceeded %ss — marking FAILED",
                    job_id,
                    self.job_timeout_seconds,
                )
                await self._mark_pending_items_skipped(db, job, reason="timeout")
                await self._finalize_job(db, job, forced_status=JobStatus.FAILED, reason="timeout")
                await broker.publish(
                    job_id,
                    {"event": "job_failed", "reason": "timeout"},
                )
            else:
                await self._finalize_job(db, job)
                await broker.publish(
                    job_id,
                    {
                        "event": "job_completed",
                        "status": job.status,
                        "succeeded_items": job.succeeded_items,
                        "failed_items": job.failed_items,
                    },
                )
        except Exception as exc:  # noqa: BLE001 — defensive top-level
            logger.exception("BulkValidateProcessor.run: unhandled error for job %s", job_id)
            try:
                job = db.query(BulkJob).filter(BulkJob.id == job_id).first()
                if job is not None:
                    await self._fail_job(
                        db,
                        job,
                        error_code="processor_crash",
                        error_message=str(exc)[:1000],
                    )
            finally:
                await broker.publish(
                    job_id,
                    {"event": "job_failed", "reason": "processor_crash", "error": str(exc)[:300]},
                )
        finally:
            await broker.close(job_id)
            db.close()

    def cancel(self) -> None:
        """Stop after the in-flight items finish. Pending items are
        marked SKIPPED on the next loop check.
        """
        self._cancel_flag.set()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _process_items(
        self,
        db: Session,
        job: BulkJob,
        current_user: User,
    ) -> None:
        items: List[BulkItem] = (
            db.query(BulkItem)
            .filter(BulkItem.job_id == job.id, BulkItem.status == ItemStatus.PENDING)
            .order_by(BulkItem.created_at.asc())
            .all()
        )
        if not items:
            return

        sem = asyncio.Semaphore(self.concurrency)

        async def _worker(item: BulkItem) -> None:
            if self._cancel_flag.is_set():
                # Can't acquire the lock if we're already stopping —
                # mark the item SKIPPED and return.
                self._mark_item_skipped(db, item, reason="cancelled")
                db.commit()
                await broker.publish(
                    job.id,
                    {"event": "item_skipped", "item_id": str(item.id), "reason": "cancelled"},
                )
                return
            async with sem:
                if self._cancel_flag.is_set():
                    self._mark_item_skipped(db, item, reason="cancelled")
                    db.commit()
                    await broker.publish(
                        job.id,
                        {"event": "item_skipped", "item_id": str(item.id), "reason": "cancelled"},
                    )
                    return
                await self._process_one(db, job, item, current_user)

        await asyncio.gather(*(_worker(item) for item in items), return_exceptions=False)

    async def _process_one(
        self,
        db: Session,
        job: BulkJob,
        item: BulkItem,
        current_user: User,
    ) -> None:
        item.status = ItemStatus.PROCESSING
        item.started_at = datetime.now(timezone.utc)
        item.attempts = (item.attempts or 0) + 1
        db.commit()

        await broker.publish(
            job.id,
            {
                "event": "item_started",
                "item_id": str(item.id),
                "lc_identifier": item.lc_identifier,
            },
        )

        start = time.monotonic()
        try:
            file_paths = self._resolve_item_file_paths(item)
            if not file_paths:
                raise RuntimeError(
                    f"BulkItem {item.id} has no file_paths in item_data"
                )

            files_list = [
                _DiskUploadFile(p, filename=p.name) for p in file_paths
            ]
            payload: dict = {
                "user_type": "exporter",
                "metadata": {
                    "bulk_job_id": str(job.id),
                    "bulk_item_id": str(item.id),
                    "lc_identifier": item.lc_identifier,
                },
            }
            document_tags = (item.item_data or {}).get("document_tags")
            if document_tags:
                payload["document_tags"] = document_tags

            runtime_context: dict = {
                "validation_session": None,
                "bulk_job_id": str(job.id),
                "bulk_item_id": str(item.id),
            }
            timings: dict = {}

            def _checkpoint(_name: str) -> None:
                # Bulk path doesn't subscribe to per-checkpoint SSE — we
                # publish at the item-level instead. Keep the no-op so
                # the pipeline call signature is satisfied.
                return None

            audit_context = {
                "correlation_id": f"bulk-{job.id}-{item.id}",
                "user_agent": "bulk-validate-processor",
            }

            request_stub = _build_request_stub(current_user)

            result = await asyncio.wait_for(
                _pipeline_runner(
                    request=request_stub,
                    current_user=current_user,
                    db=db,
                    payload=payload,
                    files_list=files_list,
                    doc_type="lc",
                    intake_only=False,
                    extract_only=False,
                    workflow_type="exporter_presentation",
                    start_time=time.time(),
                    timings=timings,
                    checkpoint=_checkpoint,
                    audit_service=None,  # bulk path does its own audit via JobEvent
                    audit_context=audit_context,
                    runtime_context=runtime_context,
                ),
                timeout=self.per_item_timeout_seconds,
            )

            duration_ms = int((time.monotonic() - start) * 1000)
            item.status = ItemStatus.SUCCEEDED
            item.finished_at = datetime.now(timezone.utc)
            item.duration_ms = duration_ms
            item.result_data = self._summarize_result(result)
            self._link_session_back_to_bulk(db, runtime_context, job.id, item.id)
            db.commit()

            await self._record_lifecycle_transition(
                db, runtime_context, current_user.id, job.id, item.id
            )

            await broker.publish(
                job.id,
                {
                    "event": "item_completed",
                    "item_id": str(item.id),
                    "lc_identifier": item.lc_identifier,
                    "duration_ms": duration_ms,
                    "summary": item.result_data,
                },
            )
        except asyncio.TimeoutError:
            duration_ms = int((time.monotonic() - start) * 1000)
            self._fail_item(
                db,
                item,
                error_code="item_timeout",
                error_message=f"Item exceeded {self.per_item_timeout_seconds}s",
                error_category="processing",
                duration_ms=duration_ms,
            )
            db.commit()
            await broker.publish(
                job.id,
                {
                    "event": "item_failed",
                    "item_id": str(item.id),
                    "lc_identifier": item.lc_identifier,
                    "reason": "item_timeout",
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "BulkValidateProcessor: item %s failed (job=%s)", item.id, job.id
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            self._fail_item(
                db,
                item,
                error_code="pipeline_error",
                error_message=str(exc)[:2000],
                error_category="processing",
                duration_ms=duration_ms,
            )
            db.commit()
            await broker.publish(
                job.id,
                {
                    "event": "item_failed",
                    "item_id": str(item.id),
                    "lc_identifier": item.lc_identifier,
                    "reason": "pipeline_error",
                    "error": str(exc)[:300],
                },
            )

    # ------------------------------------------------------------------
    # State transitions on the job + items
    # ------------------------------------------------------------------

    async def _mark_job_started(self, db: Session, job: BulkJob) -> None:
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        db.add(
            JobEvent(
                job_id=job.id,
                event_type=JobEventType.STARTED.value,
                event_data={"started_at": job.started_at.isoformat()},
            )
        )
        db.commit()

    async def _finalize_job(
        self,
        db: Session,
        job: BulkJob,
        *,
        forced_status: Optional[JobStatus] = None,
        reason: Optional[str] = None,
    ) -> None:
        # Refresh counts from the DB to avoid races with concurrent workers.
        from sqlalchemy import func as _func

        counts = dict(
            db.query(BulkItem.status, _func.count())
            .filter(BulkItem.job_id == job.id)
            .group_by(BulkItem.status)
            .all()
        )
        succeeded = int(counts.get(ItemStatus.SUCCEEDED, 0) or counts.get(ItemStatus.SUCCEEDED.value, 0) or 0)
        failed = int(counts.get(ItemStatus.FAILED, 0) or counts.get(ItemStatus.FAILED.value, 0) or 0)
        skipped = int(counts.get(ItemStatus.SKIPPED, 0) or counts.get(ItemStatus.SKIPPED.value, 0) or 0)
        processed = succeeded + failed + skipped

        job.succeeded_items = succeeded
        job.failed_items = failed
        job.skipped_items = skipped
        job.processed_items = processed
        job.finished_at = datetime.now(timezone.utc)
        if job.started_at is not None:
            job.duration_seconds = int(
                (job.finished_at - job.started_at).total_seconds()
            )
            if job.duration_seconds > 0:
                job.throughput_items_per_sec = round(succeeded / job.duration_seconds, 2)

        if forced_status is not None:
            job.status = forced_status.value if isinstance(forced_status, JobStatus) else forced_status
        elif failed == 0 and skipped == 0 and succeeded > 0:
            job.status = JobStatus.SUCCEEDED.value
        elif succeeded == 0 and failed > 0:
            job.status = JobStatus.FAILED.value
        elif self._cancel_flag.is_set():
            job.status = JobStatus.CANCELLED.value
        else:
            job.status = JobStatus.PARTIAL.value

        db.add(
            JobEvent(
                job_id=job.id,
                event_type=JobEventType.COMPLETED.value,
                event_data={
                    "status": job.status,
                    "succeeded_items": succeeded,
                    "failed_items": failed,
                    "skipped_items": skipped,
                    "reason": reason,
                },
            )
        )
        db.commit()

    async def _fail_job(
        self,
        db: Session,
        job: BulkJob,
        *,
        error_code: str,
        error_message: str,
    ) -> None:
        job.status = JobStatus.FAILED.value
        job.last_error = error_message
        job.error_code = error_code
        job.finished_at = datetime.now(timezone.utc)
        db.add(
            JobEvent(
                job_id=job.id,
                event_type=JobEventType.FAILED.value,
                event_data={"error_code": error_code, "error_message": error_message},
            )
        )
        db.commit()

    async def _mark_pending_items_skipped(
        self, db: Session, job: BulkJob, *, reason: str
    ) -> None:
        pending = (
            db.query(BulkItem)
            .filter(
                BulkItem.job_id == job.id,
                BulkItem.status.in_([ItemStatus.PENDING.value, ItemStatus.PROCESSING.value]),
            )
            .all()
        )
        now = datetime.now(timezone.utc)
        for item in pending:
            item.status = ItemStatus.SKIPPED.value
            item.finished_at = now
            item.last_error = f"job-level {reason}"
            item.error_code = reason
        db.commit()

    def _mark_item_skipped(self, db: Session, item: BulkItem, *, reason: str) -> None:
        item.status = ItemStatus.SKIPPED.value
        item.finished_at = datetime.now(timezone.utc)
        item.last_error = reason
        item.error_code = reason

    def _fail_item(
        self,
        db: Session,
        item: BulkItem,
        *,
        error_code: str,
        error_message: str,
        error_category: str,
        duration_ms: int,
    ) -> None:
        item.status = ItemStatus.FAILED.value
        item.finished_at = datetime.now(timezone.utc)
        item.duration_ms = duration_ms
        item.last_error = error_message
        item.error_code = error_code
        item.error_category = error_category
        db.add(
            BulkFailure(
                item_id=item.id,
                attempt_number=item.attempts or 1,
                error_code=error_code,
                error_message=error_message,
                error_category=error_category,
                error_severity="high",
                retriable=True,
                worker_id="bulk-validate-processor",
            )
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_item_file_paths(item: BulkItem) -> List[Path]:
        raw = (item.item_data or {}).get("file_paths") or []
        return [Path(p) for p in raw if p]

    @staticmethod
    def _summarize_result(result: Any) -> dict:
        """Compress the validation result into a small JSONB-friendly summary.

        Read the canonical paths the rest of the codebase uses:

          * verdict      → ``structured_result.bank_verdict.verdict``
                           (set by ``_build_bank_submission_verdict`` in
                           result_finalization.py)
          * score        → ``structured_result.analytics.compliance_score``
                           (the frontend-aliased copy of ``lc_compliance_score``)
          * finding_count → ``structured_result._provisional_issues``
                           (issues bucket from the same finalization step;
                           top-level ``provisional_issues`` is also accepted
                           as a fallback for older callers)

        Full structured_result lives on the spawned ValidationSession
        row; bulk's view is the summary + a link back to it.
        """
        if not isinstance(result, dict):
            return {"raw_type": type(result).__name__}
        structured = result.get("structured_result") or {}
        bank_verdict = structured.get("bank_verdict") or {}
        analytics = structured.get("analytics") or {}

        verdict = (
            bank_verdict.get("verdict")
            or structured.get("verdict")
            or result.get("verdict")
            or result.get("validation_status")
        )
        score = (
            analytics.get("compliance_score")
            or analytics.get("lc_compliance_score")
            or structured.get("compliance_score")
            or result.get("compliance_score")
        )
        findings = (
            structured.get("_provisional_issues")
            or result.get("provisional_issues")
            or []
        )
        finding_count = len(findings) if isinstance(findings, list) else 0
        return {
            "verdict": verdict,
            "compliance_score": score,
            "finding_count": finding_count,
            "session_id": result.get("session_id") or result.get("job_id"),
        }

    @staticmethod
    def _link_session_back_to_bulk(
        db: Session,
        runtime_context: dict,
        job_id: UUID,
        item_id: UUID,
    ) -> None:
        """Stamp ``bulk_job_id`` / ``bulk_item_id`` onto the session row
        the pipeline just created.

        The pipeline puts the spawned :class:`ValidationSession` into
        ``runtime_context["validation_session"]`` (see
        ``prepare_validation_session``). If for any reason it's None
        (e.g. anonymous demo path), we silently skip — bulk only runs
        for authenticated customers so this should never happen in
        practice.
        """
        session = runtime_context.get("validation_session")
        if session is None:
            return
        session.bulk_job_id = job_id
        session.bulk_item_id = item_id

    @staticmethod
    async def _record_lifecycle_transition(
        db: Session,
        runtime_context: dict,
        actor_user_id: UUID,
        job_id: UUID,
        item_id: UUID,
    ) -> None:
        """Bulk completion of an item moves the LC into
        ``docs_presented`` — the customer has presented their package
        through us. Actual bank-side review (``under_bank_review``) is
        a separate downstream event triggered by the bank submission
        flow, not bulk validation.

        Allowed transition table: docs_in_preparation → docs_presented
        (single hop). The earlier two-hop attempt to under_bank_review
        was rejected because the state machine requires going through
        docs_presented first.

        If the session is already in a state that doesn't allow this
        transition (e.g. a re-run on a terminal LC), we log + swallow.
        Don't blow up the bulk job for an audit hop.
        """
        session = runtime_context.get("validation_session")
        if session is None:
            return
        try:
            lifecycle_transition(
                db,
                session,
                LCLifecycleState.DOCS_PRESENTED,
                actor_user_id=actor_user_id,
                reason="bulk_validate_completed",
                extra={"bulk_job_id": str(job_id), "bulk_item_id": str(item_id)},
            )
            db.commit()
        except InvalidLifecycleTransition as exc:
            logger.info(
                "BulkValidateProcessor: lifecycle transition skipped for session %s: %s",
                session.id,
                exc,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "BulkValidateProcessor: unexpected error recording lifecycle event"
            )


__all__ = [
    "BulkItemInput",
    "BulkValidateProcessor",
    "CUSTOMER_LC_VALIDATION_JOB_TYPE",
    "DEFAULT_CONCURRENCY",
    "DEFAULT_JOB_TIMEOUT_SECONDS",
    "DEFAULT_PER_ITEM_TIMEOUT_SECONDS",
    "storage_dir_for_job",
]
