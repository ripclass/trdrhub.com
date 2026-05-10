"""Public, no-auth LC checker — the free lead-magnet endpoint.

``POST /api/check``
    Accepts the same multipart payload as ``POST /api/validate/`` (the LC plus
    any supporting documents), runs the full validation pipeline anonymously,
    and returns a **trimmed** result::

        {
          "verdict": "SUBMIT" | "CAUTION" | "HOLD" | "REJECT" | "REVIEW",
          "verdict_label": "<short human message>",
          "verdict_color": "green" | "yellow" | "orange" | "red" | null,
          "finding_count": <int>,
          "top_findings": [{"title": str, "severity": str}, ...],   # <= 2
          "signup_cta": true
        }

    The full structured result, the customs-pack PDF and the complete finding
    list are deliberately withheld — that is the sign-up gate.

``GET /api/check/availability``
    Cheap, non-consuming probe so the page can tell the visitor up front
    whether they've already used today's free run.

Cost control: ONE run per client IP per 24 h, enforced with a Redis counter
(:mod:`app.utils.anon_rate_limit`). The generic ``RateLimiterMiddleware`` is
in-memory / per-process / short-window and cannot express a path-scoped
24 h limit. An un-rate-limited public endpoint that runs Sonnet/Opus on every
hit is unbounded free model spend, so this limiter is load-bearing — and so is
the ``PUBLIC_LC_CHECK_ENABLED`` kill switch.

Identity: anonymous runs use the existing ``demo@trdrhub.com`` sentinel user
(``get_or_create_demo_user``). That is the codebase's already-supported
"unauthenticated validation" identity — the pipeline's billing/quota/usage
blocks all special-case it — so ``/api/check`` needs zero changes to the
validation pipeline itself. A ``ValidationSession`` row is created under the
Demo Company and is eligible for later cleanup.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.audit_middleware import create_audit_context
from app.routers.validate import get_or_create_demo_user
from app.routers.validation.pipeline_runner import run_validate_pipeline
from app.routers.validation.request_parsing import parse_validate_request
from app.services.audit_service import AuditService
from app.utils.anon_rate_limit import peek_anon_run, release_anon_run, reserve_anon_run

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["public-check"])

_RATE_SCOPE = "lc_check"
_MAX_TOP_FINDINGS = 2

# Lower = more severe; anything unrecognised sorts last.
_SEVERITY_RANK = {
    "critical": 0,
    "major": 1,
    "discrepancy": 1,
    "high": 1,
    "minor": 2,
    "medium": 2,
    "low": 3,
    "advisory": 3,
    "info": 4,
}


def _window_seconds() -> int:
    return int(getattr(settings, "PUBLIC_LC_CHECK_WINDOW_SECONDS", 24 * 60 * 60) or 24 * 60 * 60)


def _limit_per_window() -> int:
    return int(getattr(settings, "PUBLIC_LC_CHECK_LIMIT_PER_WINDOW", 1) or 1)


def _ensure_enabled() -> None:
    if not bool(getattr(settings, "PUBLIC_LC_CHECK_ENABLED", True)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")


def _issue_title(issue: Any) -> str:
    if isinstance(issue, dict):
        for key in ("title", "message", "summary", "name", "description"):
            value = issue.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return "Discrepancy"
    for key in ("title", "message", "summary", "name", "description"):
        value = getattr(issue, key, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Discrepancy"


def _issue_severity(issue: Any) -> str:
    raw = issue.get("severity") if isinstance(issue, dict) else getattr(issue, "severity", None)
    if raw is None:
        return "minor"
    raw = getattr(raw, "value", raw)
    text = str(raw).strip().lower()
    return text or "minor"


def _extract_verdict(envelope: Dict[str, Any], structured: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Pull the customer-facing verdict + its colour/message out of the result.

    Prefers ``bank_verdict`` (the SUBMIT / CAUTION / HOLD / REJECT one with a
    friendly message), then the explicit ``final_verdict``, then a neutral
    fallback.
    """
    bank_verdict = envelope.get("bank_verdict")
    if not isinstance(bank_verdict, dict):
        bank_verdict = structured.get("bank_verdict") if isinstance(structured.get("bank_verdict"), dict) else None

    if isinstance(bank_verdict, dict) and bank_verdict.get("verdict"):
        return {
            "verdict": str(bank_verdict.get("verdict")).strip().upper(),
            "verdict_label": (
                str(bank_verdict.get("verdict_message")).strip()
                if bank_verdict.get("verdict_message")
                else None
            ),
            "verdict_color": (
                str(bank_verdict.get("verdict_color")).strip().lower()
                if bank_verdict.get("verdict_color")
                else None
            ),
        }

    final_verdict = (
        envelope.get("final_verdict")
        or envelope.get("ruleset_verdict")
        or structured.get("final_verdict")
    )
    if final_verdict:
        return {"verdict": str(final_verdict).strip().upper(), "verdict_label": None, "verdict_color": None}

    return {"verdict": "REVIEW", "verdict_label": None, "verdict_color": None}


def _finding_count(envelope: Dict[str, Any], structured: Dict[str, Any], issue_pool: List[Any]) -> int:
    """The count the verdict was computed from — prefer the bank-summary
    ``issue_summary.total`` (what the verdict reflects), then the final issue
    list length."""
    bank_verdict = envelope.get("bank_verdict")
    if not isinstance(bank_verdict, dict):
        bank_verdict = structured.get("bank_verdict") if isinstance(structured.get("bank_verdict"), dict) else None
    if isinstance(bank_verdict, dict):
        summary = bank_verdict.get("issue_summary")
        if isinstance(summary, dict) and isinstance(summary.get("total"), int):
            return max(summary["total"], 0)
    return len(issue_pool)


def _trim_result(envelope: Any) -> Dict[str, Any]:
    envelope = envelope if isinstance(envelope, dict) else {}
    structured = envelope.get("structured_result")
    structured = structured if isinstance(structured, dict) else {}

    issues = structured.get("issues")
    issues = issues if isinstance(issues, list) else []
    if not issues:
        # Fall back to provisional issues so the verdict and the surfaced
        # findings don't disagree on an otherwise-"clean" presentation.
        provisional = envelope.get("provisional_issues") or structured.get("_provisional_issues")
        issues = provisional if isinstance(provisional, list) else []

    sorted_issues = sorted(issues, key=lambda i: _SEVERITY_RANK.get(_issue_severity(i), 9))
    top_findings: List[Dict[str, str]] = [
        {"title": _issue_title(i), "severity": _issue_severity(i)}
        for i in sorted_issues[:_MAX_TOP_FINDINGS]
    ]

    verdict_block = _extract_verdict(envelope, structured)

    return {
        "verdict": verdict_block["verdict"],
        "verdict_label": verdict_block["verdict_label"],
        "verdict_color": verdict_block["verdict_color"],
        "finding_count": _finding_count(envelope, structured, issues),
        "top_findings": top_findings,
        "signup_cta": True,
    }


@router.get("/check/availability")
async def public_lc_check_availability(request: Request) -> Dict[str, Any]:
    """Has this visitor already used today's free LC check? (non-consuming)."""
    _ensure_enabled()
    retry_after = await peek_anon_run(request=request, scope=_RATE_SCOPE, limit=_limit_per_window())
    if retry_after is not None:
        return {"available": False, "retry_after_seconds": int(retry_after), "signup_cta": True}
    return {"available": True}


@router.post("/check")
async def public_lc_check(request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Run a one-off anonymous LC check (rate-limited 1 / IP / 24 h)."""
    _ensure_enabled()

    # ---- rate limit BEFORE any model spend --------------------------------
    try:
        retry_after = await reserve_anon_run(
            request=request,
            scope=_RATE_SCOPE,
            window_seconds=_window_seconds(),
            limit=_limit_per_window(),
        )
    except Exception as exc:  # noqa: BLE001 — Redis required but unreachable
        logger.error("public_lc_check: rate-limit backend unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "rate_limiter_unavailable",
                "message": "The free LC checker is briefly unavailable. Please try again in a moment.",
            },
        )
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error_code": "free_check_used",
                "message": (
                    "You've used today's free LC check. Create a free account to run more checks "
                    "and export the full report."
                ),
                "retry_after_seconds": int(retry_after),
                "signup_cta": True,
            },
            headers={"Retry-After": str(int(retry_after))},
        )

    start_time = time.time()
    timings: Dict[str, float] = {}
    runtime_context: Dict[str, Any] = {"validation_session": None, "anonymous_public_check": True}

    def checkpoint(name: str) -> None:
        timings[name] = round(time.time() - start_time, 3)

    audit_service = AuditService(db)
    audit_context = create_audit_context(request)

    # ---- parse the upload (cheap; refund the run if it's malformed) --------
    try:
        parsed = await parse_validate_request(request)
    except HTTPException:
        await release_anon_run(request=request, scope=_RATE_SCOPE)
        raise
    except Exception as exc:  # noqa: BLE001
        await release_anon_run(request=request, scope=_RATE_SCOPE)
        logger.info("public_lc_check: bad request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read the uploaded files. Please upload the LC (and any supporting documents) as PDFs or images.",
        )

    if not parsed.files_list:
        await release_anon_run(request=request, scope=_RATE_SCOPE)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents uploaded. Attach at least the Letter of Credit.",
        )

    # ---- run the full pipeline anonymously --------------------------------
    try:
        demo_user = get_or_create_demo_user(db)
    except Exception as exc:  # noqa: BLE001 — extremely unlikely; treat as transient
        await release_anon_run(request=request, scope=_RATE_SCOPE)
        logger.error("public_lc_check: could not provision the anonymous user: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error_code": "check_unavailable", "message": "The free LC checker is briefly unavailable. Please try again in a moment."},
        )

    try:
        result = await run_validate_pipeline(
            request=request,
            current_user=demo_user,
            db=db,
            payload=parsed.payload,
            files_list=parsed.files_list,
            doc_type=parsed.doc_type,
            intake_only=False,      # force a full run regardless of any query params
            extract_only=False,
            workflow_type="exporter_presentation",
            start_time=start_time,
            timings=timings,
            checkpoint=checkpoint,
            audit_service=audit_service,
            audit_context=audit_context,
            runtime_context=runtime_context,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("public_lc_check: validation pipeline failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "check_failed",
                "message": "We couldn't finish checking that document set. Please double-check the files and try again.",
            },
        )

    trimmed = _trim_result(result)
    logger.info(
        "public_lc_check completed verdict=%s findings=%d elapsed=%.1fs",
        trimmed.get("verdict"),
        trimmed.get("finding_count") or 0,
        time.time() - start_time,
    )
    return trimmed


__all__ = ["router"]
