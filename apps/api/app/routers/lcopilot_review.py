"""Concierge review queue — Phase 1 launch.

Two surfaces on one router:

* Customer status (owner-scoped): GET /api/lcopilot/status/{job_id} — the
  per-job status page feed (review_state + timeline + delivered flag).
* Operator review queue (system-admin only): list under-review jobs, open one,
  curate its findings (edit / suppress / annotate), attach a summary note, and
  Approve & Deliver — which generates the cited report, opens the customer gate,
  and emails the customer.

Operator finding edits mutate ``validation_session.validation_results
["structured_result"]["issues"]`` in place — that payload is the single source
of truth the customer results UI and the delivered report both read, so curation
there is what the customer sees.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_db
from app.core.security import get_current_user, require_sysadmin
from app.models import User, ValidationSession
from app.models.report_review import ReportReviewState
from app.services import report_review as review

logger = logging.getLogger(__name__)

router = APIRouter(tags=["LCopilot Review Queue"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_session_or_404(db: Session, job_id: str) -> ValidationSession:
    session = (
        db.query(ValidationSession)
        .filter(ValidationSession.id == job_id, ValidationSession.deleted_at.is_(None))
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return session


def _structured(session: ValidationSession) -> Dict[str, Any]:
    stored = session.validation_results or {}
    if isinstance(stored, dict):
        sr = stored.get("structured_result")
        if isinstance(sr, dict):
            return sr
    return {}


def _issues(session: ValidationSession) -> List[Dict[str, Any]]:
    sr = _structured(session)
    issues = sr.get("issues")
    return [i for i in issues if isinstance(i, dict)] if isinstance(issues, list) else []


def _issue_matches(issue: Dict[str, Any], finding_id: str) -> bool:
    return finding_id in (
        str(issue.get("id") or ""),
        str(issue.get("__discrepancy_uuid") or ""),
        str(issue.get("rule") or issue.get("rule_id") or ""),
    )


def _persist_structured(db: Session, session: ValidationSession, sr: Dict[str, Any]) -> None:
    stored = dict(session.validation_results or {})
    stored["structured_result"] = sr
    session.validation_results = stored
    flag_modified(session, "validation_results")


def _status_payload(db: Session, session: ValidationSession) -> Dict[str, Any]:
    rs = getattr(session, "review_state", None)
    delivered = rs == ReportReviewState.DELIVERED.value
    events = review.history(db, session, limit=50)
    timeline = [
        {
            "from_state": e.from_state,
            "to_state": e.to_state,
            "reason": e.reason,
            "at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in reversed(events)
    ]
    from app.services.checkout import is_checkout_enabled

    return {
        "job_id": str(session.id),
        "review_state": rs,
        "workflow_type": session.workflow_type,
        "is_review_job": rs is not None,
        # Phase 5 — drives the status page's pay CTA. payment_status NULL
        # means payment isn't part of this job's flow.
        "payment_status": getattr(session, "payment_status", None),
        "payment_product_id": getattr(session, "payment_product_id", None),
        "checkout_enabled": is_checkout_enabled(),
        "delivered": delivered,
        "delivered_at": session.delivered_at.isoformat() if getattr(session, "delivered_at", None) else None,
        "reviewer_note": session.review_note if delivered else None,
        "report_available": delivered and getattr(session, "review_report_id", None) is not None,
        "timeline": timeline,
    }


# ---------------------------------------------------------------------------
# Customer status page feed
# ---------------------------------------------------------------------------

def _require_owner_or_admin(session: ValidationSession, current_user: User) -> None:
    is_admin = current_user.is_system_admin() or current_user.is_tenant_admin()
    owns = str(session.user_id) == str(current_user.id) or (
        session.company_id is not None
        and getattr(current_user, "company_id", None) is not None
        and str(session.company_id) == str(current_user.company_id)
    )
    if not (owns or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your submission")


@router.get("/api/lcopilot/status/{job_id}")
def get_review_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner-scoped status of a concierge submission (drives the status page)."""
    session = _get_session_or_404(db, job_id)
    _require_owner_or_admin(session, current_user)
    return _status_payload(db, session)


@router.get("/api/lcopilot/status/{job_id}/report")
def get_delivered_report_url(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Presigned download URL for the delivered cited report (owner-scoped)."""
    import os

    session = _get_session_or_404(db, job_id)
    _require_owner_or_admin(session, current_user)

    if session.review_state != ReportReviewState.DELIVERED.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Report not yet delivered")
    report_id = getattr(session, "review_report_id", None)
    if report_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No report on file")

    from app.models import Report

    report = db.query(Report).filter(Report.id == report_id).first()
    if report is None or not report.s3_key:
        # Render/upload failed at delivery time — the results UI is still the
        # cited surface, there is just no downloadable file.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file unavailable")

    from app.utils.s3_client import get_s3_client

    bucket = os.getenv("S3_BUCKET_NAME", "lcopilot-documents")
    url = get_s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": report.s3_key},
        ExpiresIn=3600,
    )
    return {"url": url, "content_type": "application/pdf" if report.s3_key.endswith(".pdf") else "text/html"}


# ---------------------------------------------------------------------------
# Operator review queue (system admin only)
# ---------------------------------------------------------------------------

admin_router = APIRouter(
    prefix="/api/admin/review-queue",
    tags=["Admin Review Queue"],
    dependencies=[Depends(require_sysadmin)],
)

_QUEUE_STATES = (
    ReportReviewState.ENGINE_COMPLETE.value,
    ReportReviewState.UNDER_REVIEW.value,
    ReportReviewState.NEEDS_INFO.value,
)


@admin_router.get("")
def list_review_queue(
    state: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_sysadmin),
):
    """List sessions awaiting operator review, newest first."""
    q = db.query(ValidationSession).filter(ValidationSession.deleted_at.is_(None))
    if state:
        q = q.filter(ValidationSession.review_state == state)
    else:
        q = q.filter(ValidationSession.review_state.in_(_QUEUE_STATES))
    q = q.order_by(ValidationSession.review_state_changed_at.desc().nullslast()).limit(min(limit, 500))
    rows = q.all()
    items = []
    for s in rows:
        issues = _issues(s)
        items.append({
            "job_id": str(s.id),
            "review_state": s.review_state,
            "workflow_type": s.workflow_type,
            "user_id": str(s.user_id) if s.user_id else None,
            "company_id": str(s.company_id) if s.company_id else None,
            "finding_count": len(issues),
            "submitted_at": s.created_at.isoformat() if s.created_at else None,
            "state_changed_at": s.review_state_changed_at.isoformat() if s.review_state_changed_at else None,
        })
    return {"count": len(items), "items": items}


@admin_router.get("/{job_id}")
def get_review_detail(
    job_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_sysadmin),
):
    """Full review detail: the structured result + current findings to curate."""
    session = _get_session_or_404(db, job_id)
    return {
        "job_id": str(session.id),
        "review_state": session.review_state,
        "review_note": session.review_note,
        "workflow_type": session.workflow_type,
        "structured_result": _structured(session),
        "findings": _issues(session),
        "timeline": _status_payload(db, session)["timeline"],
    }


class FindingEdit(BaseModel):
    action: str  # "suppress" | "edit" | "annotate"
    severity: Optional[str] = None
    message: Optional[str] = None
    suggested_fix: Optional[str] = None
    reviewer_note: Optional[str] = None


@admin_router.post("/{job_id}/findings/{finding_id}")
def edit_finding(
    job_id: str,
    finding_id: str,
    payload: FindingEdit,
    db: Session = Depends(get_db),
    admin: User = Depends(require_sysadmin),
):
    """Curate a single finding on a session still under review.

    * suppress — remove it from the delivered findings (stashed for audit).
    * edit — override severity / message / suggested_fix in place.
    * annotate — attach a reviewer note visible on the finding.
    """
    session = _get_session_or_404(db, job_id)
    if session.review_state not in _QUEUE_STATES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Session not under review (state={session.review_state})")
    sr = _structured(session)
    issues = [i for i in (sr.get("issues") or []) if isinstance(i, dict)]
    target_idx = next((i for i, iss in enumerate(issues) if _issue_matches(iss, finding_id)), None)
    if target_idx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    action = payload.action.lower()
    if action == "suppress":
        removed = issues.pop(target_idx)
        removed["_suppressed_by"] = str(admin.id)
        removed["_suppressed_at"] = datetime.now(timezone.utc).isoformat()
        stash = sr.setdefault("_reviewer_suppressed", [])
        if isinstance(stash, list):
            stash.append(removed)
    elif action in ("edit", "annotate"):
        issue = issues[target_idx]
        if payload.severity:
            issue["severity"] = payload.severity
        if payload.message:
            issue["message"] = payload.message
            issue["title"] = payload.message
        if payload.suggested_fix:
            issue["suggested_fix"] = payload.suggested_fix
        if payload.reviewer_note:
            issue["reviewer_note"] = payload.reviewer_note
        issue["_edited_by"] = str(admin.id)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="action must be suppress | edit | annotate")

    sr["issues"] = issues
    _persist_structured(db, session, sr)
    db.commit()
    return {"ok": True, "action": action, "finding_count": len(issues)}


class ReviewNote(BaseModel):
    note: str


@admin_router.post("/{job_id}/note")
def set_review_note(
    job_id: str,
    payload: ReviewNote,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_sysadmin),
):
    """Attach/replace the operator's summary note (shown on the delivered report)."""
    session = _get_session_or_404(db, job_id)
    session.review_note = payload.note
    db.commit()
    return {"ok": True}


class NeedsInfo(BaseModel):
    reason: str


@admin_router.post("/{job_id}/needs-info")
def mark_needs_info(
    job_id: str,
    payload: NeedsInfo,
    db: Session = Depends(get_db),
    admin: User = Depends(require_sysadmin),
):
    """Bounce a submission back to the customer for more information."""
    session = _get_session_or_404(db, job_id)
    try:
        review.transition(db, session, ReportReviewState.NEEDS_INFO,
                          actor_user_id=admin.id, reason=payload.reason)
    except review.InvalidReviewTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    db.commit()
    return {"ok": True, "review_state": session.review_state}


@admin_router.post("/{job_id}/rerun-engine")
async def rerun_readiness_engine(
    job_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_sysadmin),
):
    """Re-run the readiness engine on a queued CBAM/EUDR job.

    Exists because intake can happen while RulHub is unreachable — the job
    still enters the queue with ``_engine_error`` set and empty citations;
    the operator re-runs here before Approve & Deliver. Readiness jobs only
    (LC jobs re-run through the validation pipeline, not this).
    """
    from app.services.readiness import READINESS_WORKFLOWS, run_readiness_engine

    session = _get_session_or_404(db, job_id)
    tool_by_workflow = {v: k for k, v in READINESS_WORKFLOWS.items()}
    tool = tool_by_workflow.get(str(session.workflow_type or ""))
    if tool is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Not a readiness job — engine re-run only applies to CBAM/EUDR intakes")
    if session.review_state not in _QUEUE_STATES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Session not under review (state={session.review_state})")

    sr = _structured(session)
    answers = sr.get("intake_answers")
    if not isinstance(answers, dict) or not answers:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="No stored intake answers on this session")

    engine = await run_readiness_engine(tool, answers)
    sr["issues"] = engine["issues"]
    summary = sr.get("readiness_summary") or {}
    gaps = sum(1 for i in engine["issues"] if i.get("severity") in ("critical", "major"))
    partial = sum(1 for i in engine["issues"] if i.get("severity") == "minor")
    summary.update({
        "gaps": gaps,
        "partial": partial,
        "in_place": len(engine["issues"]) - gaps - partial,
        "rules_consulted": engine.get("rules_consulted", 0),
    })
    sr["readiness_summary"] = summary
    sr["verdict"] = "gaps found" if gaps else ("partially ready" if partial else "ready")
    if engine.get("engine_error"):
        sr["_engine_error"] = engine["engine_error"]
    else:
        sr.pop("_engine_error", None)
    _persist_structured(db, session, sr)
    db.commit()
    return {
        "ok": True,
        "finding_count": len(engine["issues"]),
        "rules_consulted": engine.get("rules_consulted", 0),
        "engine_error": engine.get("engine_error"),
    }


@admin_router.post("/{job_id}/deliver")
def approve_and_deliver(
    job_id: str,
    payload: Optional[ReviewNote] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_sysadmin),
):
    """Approve & Deliver: generate the cited report, open the customer gate, notify."""
    session = _get_session_or_404(db, job_id)
    if session.review_state not in (ReportReviewState.UNDER_REVIEW.value, ReportReviewState.ENGINE_COMPLETE.value):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Session not deliverable (state={session.review_state})")
    # Phase 5 safety: never deliver an unpaid job while checkout is live.
    from app.services.checkout import is_checkout_enabled as _pay_on
    if _pay_on() and getattr(session, "payment_status", None) == "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Job is awaiting payment — cannot deliver")

    if payload and payload.note:
        session.review_note = payload.note

    # 1. Generate the cited report from the (curated) structured result.
    sr = _structured(session)
    owner = db.query(User).filter(User.id == session.user_id).first() if session.user_id else None
    report_id = None
    try:
        from app.services.lc_report import generate_lc_report
        report = generate_lc_report(db, session, owner or admin, sr, session.review_note)
        report_id = report.id
        session.review_report_id = report.id
    except Exception:
        logger.exception("cited report generation failed for %s (delivering without file)", session.id)

    # 2. Advance to DELIVERED (force through engine_complete if needed).
    if session.review_state == ReportReviewState.ENGINE_COMPLETE.value:
        review.transition(db, session, ReportReviewState.UNDER_REVIEW,
                          actor_user_id=admin.id, reason="auto-advance for delivery")
    review.transition(db, session, ReportReviewState.DELIVERED,
                      actor_user_id=admin.id, reason="approved & delivered")
    session.reviewed_by = admin.id
    session.reviewed_at = datetime.now(timezone.utc)
    session.delivered_at = datetime.now(timezone.utc)
    db.commit()

    # 3. Notify the customer the report is ready.
    _notify_delivered(db, session)

    return {
        "ok": True,
        "review_state": session.review_state,
        "report_id": str(report_id) if report_id else None,
    }


def _notify_delivered(db: Session, session: ValidationSession) -> None:
    try:
        from app.services.user_notifications import dispatch as _dispatch
        from app.models.user_notifications import NotificationType
        owner = db.query(User).filter(User.id == session.user_id).first() if session.user_id else None
        if owner is None:
            return
        _dispatch(
            db, owner,
            NotificationType.REPORT_DELIVERED,
            title="Your LC report is ready",
            body=(
                "Our specialist has reviewed your LC pack. Your cited discrepancy "
                "report is now available — open it to see every finding, its rule "
                "reference, and the fix before you present to your bank."
            ),
            link_url=f"/lcopilot/status/{session.id}",
            metadata={"validation_session_id": str(session.id)},
        )
        db.commit()
    except Exception:
        logger.exception("report_delivered notification skipped for session %s", session.id)
