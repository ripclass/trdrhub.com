"""Auto re-validation of corrected docs after a recipient upload —
Phase A2 closure.

Runs as a FastAPI BackgroundTask kicked from the recipient-upload
endpoint. Walks the corrected-files directory the upload step wrote
to, runs the validation pipeline against them as the original
requester, and on success links the new ``ValidationSession`` back to
the parent ``RepaperingRequest`` and transitions both the request and
the parent ``Discrepancy`` to RESOLVED.

The task opens its own DB session via SessionLocal — BackgroundTask
callbacks run after the request session is closed.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from ..database import SessionLocal
from ..models import Discrepancy, User
from ..models.discrepancy_workflow import (
    DiscrepancyState,
    RepaperingRequest,
    RepaperingState,
)
from .discrepancy_workflow import (
    InvalidDiscrepancyTransition,
    InvalidRepaperingTransition,
    transition_discrepancy,
    transition_repapering,
)

logger = logging.getLogger(__name__)


def _storage_dir(request_id: UUID | str) -> Path:
    base = os.getenv("BULK_VALIDATE_STORAGE_DIR", "/tmp/lcopilot-bulk")
    return Path(base) / "repaper" / str(request_id)


def _list_corrected_files(request_id: UUID | str) -> list[Path]:
    target = _storage_dir(request_id)
    if not target.exists():
        return []
    return sorted(p for p in target.iterdir() if p.is_file())


def _load_requester(db, requester_user_id) -> User | None:
    """Indirection point so tests can patch the user lookup without
    needing to materialise the User table on SQLite (it carries
    Postgres-only JSONB columns)."""
    if not requester_user_id:
        return None
    return db.query(User).filter(User.id == requester_user_id).first()


class _RequestStub:
    """Minimal request shape the pipeline uses (state + audit context)."""

    def __init__(self, requester: User) -> None:
        from starlette.datastructures import Headers

        self.headers = Headers({})
        self.state = type("State", (), {})()
        self.state.user_id = str(requester.id) if requester else None
        self.state.user_email = requester.email if requester else None
        self.client = type("Client", (), {"host": "background-task"})()
        self.url = type("URL", (), {"path": "/api/repaper/revalidate"})()
        self.method = "POST"


async def _run_pipeline(db, requester: User, file_paths: list[Path]) -> dict:
    """Wrap the validation pipeline call. Imported lazily so this
    module can be loaded in test environments where the pipeline's
    heavy deps (vision LLM clients, etc.) aren't available.
    """
    from app.routers.validation.pipeline_runner import run_validate_pipeline
    from app.services.bulk_validate_processor import _DiskUploadFile

    files_list = [_DiskUploadFile(p, filename=p.name) for p in file_paths]
    payload: dict = {
        "user_type": "exporter",
        "metadata": {
            "source": "repaper_auto_revalidate",
        },
    }
    runtime_context: dict = {"validation_session": None}
    timings: dict = {}

    def _checkpoint(_name: str) -> None:
        return None

    audit_context = {
        "correlation_id": f"repaper-revalidate-{int(time.time())}",
        "user_agent": "repaper-revalidate",
    }

    return await run_validate_pipeline(
        request=_RequestStub(requester),
        current_user=requester,
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
        audit_service=None,
        audit_context=audit_context,
        runtime_context=runtime_context,
    )


def _extract_session_id(result: Any) -> str | None:
    """Pull the new ValidationSession id out of the pipeline response."""
    if not isinstance(result, dict):
        return None
    for key in ("validation_session_id", "session_id", "job_id", "jobId"):
        v = result.get(key)
        if v:
            return str(v)
    sr = result.get("structured_result")
    if isinstance(sr, dict):
        for key in ("validation_session_id", "session_id"):
            v = sr.get(key)
            if v:
                return str(v)
    return None


def _count_findings(result: Any) -> int:
    """Roughly count user-facing findings on the new session result.
    Used to decide whether to flip the original discrepancy to
    RESOLVED — zero findings = clean re-validation."""
    if not isinstance(result, dict):
        return 0
    sr = result.get("structured_result") or {}
    issues = (
        result.get("issues")
        or sr.get("issues")
        or sr.get("issue_cards")
        or []
    )
    if isinstance(issues, list):
        return len(issues)
    return 0


async def revalidate_repaper_request(request_id: UUID | str) -> None:
    """Background task entry point.

    Idempotent: if the request is already RESOLVED or CANCELLED,
    returns early. If the pipeline fails, logs but doesn't surface —
    the requester can manually re-validate or cancel.
    """
    db = SessionLocal()
    try:
        request = (
            db.query(RepaperingRequest)
            .filter(RepaperingRequest.id == request_id)
            .first()
        )
        if request is None:
            logger.warning(
                "revalidate_repaper_request: request %s not found", request_id
            )
            return
        if request.state in (
            RepaperingState.RESOLVED.value,
            RepaperingState.CANCELLED.value,
        ):
            logger.info(
                "revalidate_repaper_request: request %s already %s — skipping",
                request_id,
                request.state,
            )
            return

        files = _list_corrected_files(request.id)
        if not files:
            logger.warning(
                "revalidate_repaper_request: no files at storage path for %s",
                request_id,
            )
            return

        requester = _load_requester(db, request.requester_user_id)
        if requester is None:
            logger.warning(
                "revalidate_repaper_request: requester user not found for %s",
                request_id,
            )
            return

        try:
            result = await _run_pipeline(db, requester, files)
        except Exception:
            logger.exception(
                "revalidate_repaper_request: pipeline failed for %s",
                request_id,
            )
            return

        new_session_id = _extract_session_id(result)
        finding_count = _count_findings(result)

        # Re-fetch the request — pipeline ran a long time, session may have
        # been touched by other actors.
        request = (
            db.query(RepaperingRequest)
            .filter(RepaperingRequest.id == request_id)
            .first()
        )
        if request is None:
            return
        new_session_uuid: UUID | None = None
        if new_session_id:
            try:
                new_session_uuid = UUID(str(new_session_id))
            except (ValueError, AttributeError, TypeError):
                new_session_uuid = None
        if new_session_uuid is not None:
            request.replacement_session_id = new_session_uuid

        # Repaper itself: corrected → resolved. If clean re-validation,
        # also resolve the parent discrepancy and link evidence.
        try:
            transition_repapering(
                db,
                request,
                RepaperingState.RESOLVED,
                replacement_session_id=new_session_uuid,
            )
        except InvalidRepaperingTransition:
            logger.info(
                "revalidate_repaper_request: %s already past CORRECTED — "
                "leaving state as-is",
                request_id,
            )

        if finding_count == 0:
            discrepancy = (
                db.query(Discrepancy)
                .filter(Discrepancy.id == request.discrepancy_id)
                .first()
            )
            if discrepancy is not None:
                try:
                    transition_discrepancy(
                        db,
                        discrepancy,
                        DiscrepancyState.RESOLVED,
                        actor_user_id=request.requester_user_id,
                        resolution_action="resolved",
                        resolution_evidence_session_id=new_session_uuid,
                        system_comment=(
                            "Auto-resolved: re-validation of corrected "
                            "documents returned no findings."
                        ),
                    )
                except InvalidDiscrepancyTransition:
                    logger.info(
                        "revalidate_repaper_request: discrepancy %s could "
                        "not transition to RESOLVED — leaving as-is",
                        discrepancy.id,
                    )

        request.resolved_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            "revalidate_repaper_request: %s — replacement_session=%s findings=%d",
            request_id,
            new_session_id,
            finding_count,
        )
    finally:
        db.close()


def schedule_revalidation(background, request_id: UUID | str) -> None:
    """FastAPI BackgroundTasks runs sync-callable tasks on the event
    loop; wrap our async coroutine so the task adapter can dispatch it.
    """

    def _runner() -> None:
        asyncio.run(revalidate_repaper_request(request_id))

    background.add_task(_runner)


__all__ = ["revalidate_repaper_request", "schedule_revalidation"]
