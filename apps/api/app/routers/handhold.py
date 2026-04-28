"""First-session handhold endpoints — Phase A3 part 5.

Adds the "Try a sample LC" path: a single endpoint that kicks the
validation pipeline against a small, repo-bundled sample set so a
fresh signup can see results without sourcing real LC documents.

Fixtures live at ``apps/api/app/fixtures/sample_lc/`` and are tracked
in git (BD-CN/SHIPMENT_CLEAN copied from apps/web/tests/fixtures/
importer-corpus). Total size is ~27 KB so it doesn't bloat the repo.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..database import get_db
from ..models import User

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/handhold", tags=["handhold"])


_SAMPLE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "sample_lc"


class SampleLCResponse(BaseModel):
    job_id: str
    validation_session_id: str
    status: str
    message: str


def _list_sample_files() -> list[Path]:
    if not _SAMPLE_DIR.exists():
        return []
    return sorted(p for p in _SAMPLE_DIR.iterdir() if p.suffix.lower() == ".pdf")


@router.post("/sample-lc", response_model=SampleLCResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_sample_lc(
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Kick a sample-LC validation as the current user.

    Schedules the pipeline as a BackgroundTask so the HTTP call
    returns immediately with the session id. Frontend navigates to
    ``/exporter/results/{validation_session_id}`` and polls for
    completion via the existing results-page pattern.
    """
    files = _list_sample_files()
    if not files:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "sample_fixtures_missing",
                "message": "Sample fixtures not bundled with this build.",
            },
        )

    # Reuse the bulk processor's _DiskUploadFile + pipeline runner. It's
    # already set up to drive the pipeline from on-disk files with no
    # multipart upload boundary.
    from ..services.bulk_validate_processor import _DiskUploadFile
    from ..routers.validation.pipeline_runner import run_validate_pipeline

    requester_id = current_user.id
    requester_email = current_user.email

    # The pipeline runs as a BackgroundTask. We can't reuse the
    # request-bound DB session because it'll close after the response
    # is returned. Open a fresh SessionLocal inside the task.
    from ..database import SessionLocal

    # Pre-create a placeholder job_id we hand back to the frontend.
    # The pipeline's session_setup step will create the real
    # ValidationSession; the frontend polls by job_id and gets the
    # final session id from the validation results once complete.
    import uuid as _uuid

    job_id = str(_uuid.uuid4())

    async def _runner() -> None:
        from ..services.repaper_revalidate import _RequestStub

        task_db = SessionLocal()
        try:
            files_list = [_DiskUploadFile(p, filename=p.name) for p in files]
            payload: dict[str, Any] = {
                "user_type": "exporter",
                "metadata": {
                    "source": "handhold_sample_lc",
                    "requester_email": requester_email,
                },
            }
            runtime_context: dict[str, Any] = {
                "validation_session": None,
                "preassigned_job_id": job_id,
            }
            timings: dict[str, Any] = {}

            def _checkpoint(_name: str) -> None:
                return None

            audit_context = {
                "correlation_id": f"sample-lc-{job_id}",
                "user_agent": "handhold-sample-lc",
            }
            requester = (
                task_db.query(User).filter(User.id == requester_id).first()
            )
            if requester is None:
                logger.warning(
                    "handhold sample-lc: requester user %s not found",
                    requester_id,
                )
                return
            try:
                await run_validate_pipeline(
                    request=_RequestStub(requester),
                    current_user=requester,
                    db=task_db,
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
            except Exception:
                logger.exception(
                    "handhold sample-lc: pipeline failed for user %s",
                    requester_id,
                )
        finally:
            task_db.close()

    background.add_task(_runner)

    return SampleLCResponse(
        job_id=job_id,
        validation_session_id=job_id,
        status="queued",
        message=(
            f"Sample validation queued. {len(files)} document(s) will be "
            "validated; results will appear on the dashboard shortly."
        ),
    )


__all__ = ["router"]
