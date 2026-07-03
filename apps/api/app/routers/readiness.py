"""CBAM / EUDR readiness API — Phase 3 launch (2026-07).

Public surface (no auth, rate-limited by the global middleware):
* GET  /api/readiness/questions/{tool} — question sets (scope + intake).
* POST /api/readiness/scope-check     — free 5-question instant verdict.
* POST /api/readiness/scope-summary   — email-gated one-page summary
  (sends the summary to the visitor; a lead copy goes to support@).

Authenticated surface:
* POST /api/readiness/submit — paid report intake. Creates a
  ValidationSession (workflow_type cbam_readiness / eudr_readiness /
  cbam_eudr_readiness), runs the RulHub m13 engine over the answers, and
  enrolls the job in the SAME concierge review queue as LCopilot. The
  customer tracks it on /lcopilot/status/{job_id}; the operator curates and
  delivers the cited PDF from the admin Review Queue.

Payment is Phase 5 (Stripe Checkout at intake). Until that lands, submission
enters the queue unpaid — the operator invoices manually.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models import SessionStatus, User, ValidationSession
from app.services import report_review as review
from app.services.readiness import (
    QUESTION_SETS,
    READINESS_WORKFLOWS,
    build_scope_summary_html,
    run_readiness_engine,
    scope_verdict,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/readiness", tags=["Readiness (CBAM/EUDR)"])


def _valid_tool(tool: str, allow_both: bool = False) -> str:
    t = (tool or "").lower().strip()
    valid = ("cbam", "eudr", "both") if allow_both else ("cbam", "eudr")
    if t not in valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"tool must be one of {valid}")
    return t


# ---------------------------------------------------------------------------
# Public: question sets + free scope check + email-gated summary
# ---------------------------------------------------------------------------

@router.get("/questions/{tool}")
def get_questions(tool: str):
    """Question definitions for the scope check and the paid intake."""
    t = _valid_tool(tool)
    return {
        "tool": t,
        "scope_questions": QUESTION_SETS[t]["scope"],
        "intake_questions": QUESTION_SETS[t]["intake"],
    }


class ScopeCheckRequest(BaseModel):
    tool: str
    answers: Dict[str, Any] = Field(default_factory=dict)


@router.post("/scope-check")
def scope_check(payload: ScopeCheckRequest):
    """Free instant scope check — no signup, no persistence."""
    t = _valid_tool(payload.tool)
    result = scope_verdict(t, payload.answers or {})
    return {"tool": t, **result}


class ScopeSummaryRequest(BaseModel):
    tool: str
    email: EmailStr
    answers: Dict[str, Any] = Field(default_factory=dict)
    company: Optional[str] = Field(default=None, max_length=200)


@router.post("/scope-summary")
def scope_summary(payload: ScopeSummaryRequest):
    """Email the one-page scope summary (the lead-magnet gate)."""
    from app.services.email import send_email

    t = _valid_tool(payload.tool)
    verdict = scope_verdict(t, payload.answers or {})
    html = build_scope_summary_html(t, payload.answers or {}, verdict)
    tool_name = t.upper()

    sent = send_email(
        to=str(payload.email),
        subject=f"Your {tool_name} scope check — one-page summary",
        html_body=html,
    )

    # Lead notification — no leads table yet; support@ inbox is the CRM at
    # this stage of launch. Never blocks the visitor's response.
    try:
        send_email(
            to=os.getenv("READINESS_LEADS_EMAIL", "support@trdrhub.com"),
            subject=f"[lead] {tool_name} scope check — {payload.email}",
            html_body=(
                f"<p>New {tool_name} scope-check lead.</p>"
                f"<p><b>Email:</b> {payload.email}<br>"
                f"<b>Company:</b> {payload.company or '—'}<br>"
                f"<b>Verdict:</b> {verdict['verdict']}</p>"
                f"<p><b>Answers:</b> {payload.answers}</p>"
            ),
        )
    except Exception:  # pragma: no cover - defensive
        logger.exception("readiness lead notification failed")

    logger.info("readiness scope-summary [%s] verdict=%s email_sent=%s",
                t, verdict["verdict"], sent)
    return {"ok": True, "email_sent": sent, "tool": t, **verdict}


# ---------------------------------------------------------------------------
# Authenticated: paid report intake → concierge review queue
# ---------------------------------------------------------------------------

class ReadinessSubmit(BaseModel):
    tool: str  # cbam | eudr | both
    answers: Dict[str, Any] = Field(default_factory=dict)


def _readiness_structured_result(tool: str, answers: Dict[str, Any],
                                 engine: Dict[str, Any], reference: str) -> Dict[str, Any]:
    gaps = sum(1 for i in engine["issues"] if i.get("severity") in ("critical", "major"))
    partial = sum(1 for i in engine["issues"] if i.get("severity") == "minor")
    verdict = "gaps found" if gaps else ("partially ready" if partial else "ready")
    return {
        "report_kind": READINESS_WORKFLOWS[tool],
        "lc_number": reference,  # the template's reference field
        "verdict": verdict,
        "issues": engine["issues"],
        "intake_answers": answers,
        "readiness_summary": {
            "gaps": gaps,
            "partial": partial,
            "in_place": len(engine["issues"]) - gaps - partial,
            "rules_consulted": engine.get("rules_consulted", 0),
        },
        **({"_engine_error": engine["engine_error"]} if engine.get("engine_error") else {}),
    }


@router.post("/submit")
async def submit_readiness_intake(
    payload: ReadinessSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a readiness job: run the m13 engine, enroll in the review queue."""
    t = _valid_tool(payload.tool, allow_both=True)
    answers = payload.answers or {}
    if not answers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="answers required")

    session = ValidationSession(
        user_id=current_user.id,
        company_id=getattr(current_user, "company_id", None),
        workflow_type=READINESS_WORKFLOWS[t],
        status=SessionStatus.PROCESSING.value,
    )
    db.add(session)
    db.flush()  # assign session.id

    reference = f"RDY-{str(session.id)[:8].upper()}"

    # Engine — never blocks queue entry; a RulHub outage leaves engine_error
    # set and the operator re-runs from the admin queue before delivery.
    engine = await run_readiness_engine(t, answers)
    sr = _readiness_structured_result(t, answers, engine, reference)
    session.validation_results = {"structured_result": sr}
    session.status = SessionStatus.COMPLETED.value
    session.processing_completed_at = datetime.now(timezone.utc)

    # Concierge enrollment — the queue IS the product for readiness reports,
    # so this is unconditional (not behind LCOPILOT_REVIEW_QUEUE_ENABLED).
    review.begin_review(db, session, actor_user_id=current_user.id,
                        reason=f"{t} readiness intake submitted")

    # Phase 5 — pay first, then the job enters the operator's queue. With
    # checkout enabled the job holds at SUBMITTED (invisible to the operator,
    # who lists engine_complete/under_review/needs_info) until the
    # checkout.session.completed webhook advances it. Checkout off = straight
    # to the queue, operator invoices manually (pre-Phase-5 behavior).
    from app.services.checkout import (
        READINESS_TOOL_PRODUCTS,
        CheckoutError,
        create_checkout_session,
        is_checkout_enabled,
    )

    checkout_url: Optional[str] = None
    if is_checkout_enabled():
        db.commit()
        try:
            checkout_url = create_checkout_session(
                db, session, current_user, READINESS_TOOL_PRODUCTS[t],
            )
        except CheckoutError as exc:
            # Payment couldn't start — don't strand the customer: the status
            # page offers a retry via POST /api/payments/checkout.
            logger.error("readiness checkout creation failed for %s: %s", session.id, exc)
            session.payment_status = "pending"
            session.payment_product_id = READINESS_TOOL_PRODUCTS[t]
            db.commit()
    else:
        review.on_engine_complete(
            db, session, actor_user_id=current_user.id,
            reason="readiness engine complete" if not engine.get("engine_error")
            else "readiness engine DEGRADED — re-run before delivery",
        )
        db.commit()
        _notify_submitted(db, current_user, session, t)

    return {
        "job_id": str(session.id),
        "reference": reference,
        "review_state": session.review_state,
        "status_url": f"/lcopilot/status/{session.id}",
        "checkout_url": checkout_url,
        "payment_status": session.payment_status,
        "engine_degraded": bool(engine.get("engine_error")),
    }


def _notify_submitted(db: Session, user: User, session: ValidationSession, tool: str) -> None:
    """In-app + email confirmation with the 24h SLA promise. Best-effort."""
    tool_name = {"cbam": "CBAM", "eudr": "EUDR", "both": "CBAM + EUDR"}[tool]
    try:
        from app.services.user_notifications import dispatch as _dispatch
        from app.models.user_notifications import NotificationType
        _dispatch(
            db, user,
            NotificationType.REPORT_UNDER_REVIEW,
            title=f"Your {tool_name} readiness report is in review",
            body=(
                f"We've received your {tool_name} readiness intake. A specialist reviews "
                "every report before it ships — you'll get it within 24 hours."
            ),
            link_url=f"/lcopilot/status/{session.id}",
            metadata={"validation_session_id": str(session.id)},
        )
        db.commit()
    except Exception:  # pragma: no cover - defensive
        logger.exception("readiness submission notification skipped for %s", session.id)
