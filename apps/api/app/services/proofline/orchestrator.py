"""Persisted, retry-safe execution of one applicable Proofline source module."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from sqlalchemy.orm import Session

from app.integrations.proofline.base import AdapterResult, ProoflineAdapter
from app.models import TradeCase, TradeCaseCheckRun
from app.services.proofline.applicability import ModuleApplicability
from app.services.proofline.findings import upsert_normalized_finding


TERMINAL_STATES = {
    "clear",
    "issue_found",
    "evidence_incomplete",
    "not_applicable",
    "unable_to_assess",
    "pending_review",
}


def canonical_input_hash(context: Mapping[str, Any]) -> str:
    payload = json.dumps(
        context,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


async def run_check(
    db: Session,
    *,
    trade_case: TradeCase,
    applicability: ModuleApplicability,
    context: Mapping[str, Any],
    adapter: Optional[ProoflineAdapter],
    idempotency_key: str,
) -> TradeCaseCheckRun:
    if not idempotency_key.strip():
        raise ValueError("A check idempotency key is required")
    existing = (
        db.query(TradeCaseCheckRun)
        .filter(
            TradeCaseCheckRun.trade_case_id == trade_case.id,
            TradeCaseCheckRun.module == applicability.module,
            TradeCaseCheckRun.idempotency_key == idempotency_key,
        )
        .first()
    )
    if existing is not None:
        return existing

    timestamp = datetime.now(timezone.utc)
    check_run = TradeCaseCheckRun(
        id=uuid.uuid4(),
        company_id=trade_case.company_id,
        trade_case_id=trade_case.id,
        module=applicability.module,
        module_version=getattr(adapter, "version", None),
        state="pending",
        applicable=applicability.applicable,
        required=applicability.required,
        applicability_reason=applicability.reason,
        idempotency_key=idempotency_key,
        input_hash=canonical_input_hash(context),
        attempt_count=0,
        result_summary={},
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(check_run)

    if not applicability.applicable:
        check_run.state = "not_applicable"
        check_run.completed_at = timestamp
        check_run.result_summary = {"summary": applicability.reason, "finding_count": 0}
        return check_run

    if adapter is None:
        check_run.state = "pending_review"
        check_run.completed_at = timestamp
        check_run.result_summary = {
            "summary": "No configured automated adapter is available; analyst review is required.",
            "finding_count": 0,
        }
        return check_run

    check_run.state = "running"
    check_run.started_at = timestamp
    check_run.attempt_count = 1
    db.flush()
    try:
        result = await adapter.run(context)
        if result.state not in TERMINAL_STATES - {"not_applicable"}:
            raise ValueError("Adapter returned an unsupported state")
        check_run.state = result.state
        check_run.module_version = getattr(adapter, "version", None)
        check_run.source_record_type = result.source_record_type
        check_run.source_record_id = result.source_record_id
        check_run.result_summary = {
            "summary": result.summary,
            "finding_count": len(result.findings),
            "metadata": result.metadata,
        }
        for source_finding in result.findings:
            upsert_normalized_finding(
                db,
                trade_case=trade_case,
                check_run=check_run,
                module=applicability.module,
                source=source_finding,
            )
    except TimeoutError:
        check_run.state = "unable_to_assess"
        check_run.error_code = "adapter_timeout"
        check_run.safe_error_message = (
            "The required check timed out. Analyst review is required."
        )
        check_run.result_summary = {
            "summary": check_run.safe_error_message,
            "finding_count": 0,
        }
    except Exception:
        check_run.state = "unable_to_assess"
        check_run.error_code = "adapter_error"
        check_run.safe_error_message = (
            "The required check could not be completed. Analyst review is required."
        )
        check_run.result_summary = {
            "summary": check_run.safe_error_message,
            "finding_count": 0,
        }
    check_run.completed_at = datetime.now(timezone.utc)
    check_run.updated_at = check_run.completed_at
    return check_run


__all__ = ["AdapterResult", "canonical_input_hash", "run_check"]
