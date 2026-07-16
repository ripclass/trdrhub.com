"""Convert an owned completed LCopilot review into a linked Proofline draft."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.integrations.proofline.lcopilot import LCopilotAdapter
from app.models import Document, TradeCase, TradeCaseEvent
from app.repositories.proofline import ProoflineRepository
from app.services.proofline.applicability import ModuleApplicability
from app.services.proofline.documents import associate_document
from app.services.proofline.orchestrator import run_check


class LCopilotUpgradeError(ValueError):
    """The LCopilot session is not eligible for an owned Proofline upgrade."""


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _structured_result(source_session: Any) -> dict[str, Any]:
    stored = getattr(source_session, "validation_results", None) or {}
    if not isinstance(stored, dict):
        return {}
    result = stored.get("structured_result")
    return result if isinstance(result, dict) else stored


def _scalar(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("value", "amount", "name", "text", "raw"):
            nested = value.get(key)
            if nested not in (None, ""):
                return _scalar(nested)
        return None
    return value


def _text(result: dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = _scalar(result.get(key))
        if value not in (None, ""):
            return str(value).strip()
    return None


def _amount(result: dict[str, Any]) -> Optional[Decimal]:
    value = _scalar(result.get("amount"))
    if value is None:
        value = _scalar(result.get("credit_amount"))
    try:
        return Decimal(str(value).replace(",", "")) if value not in (None, "") else None
    except (InvalidOperation, ValueError):
        return None


async def upgrade_lcopilot_session(
    db: Session,
    *,
    source_session: Any,
    current_user: Any,
    repository: Optional[ProoflineRepository] = None,
) -> tuple[TradeCase, bool]:
    """Create one linked draft and seed its LC check from the stored result.

    Documents remain the original TRDRHub records. The normalized Proofline
    findings reference a check run whose adapter consumes the stored LCopilot
    payload, so no deterministic or AI validation is paid for twice.
    """
    company_id = getattr(current_user, "company_id", None)
    if company_id is None:
        raise LCopilotUpgradeError("A company workspace is required for Proofline")

    existing = (
        db.query(TradeCase)
        .filter(
            TradeCase.company_id == company_id,
            TradeCase.source_lcopilot_session_id == source_session.id,
            TradeCase.deleted_at.is_(None),
        )
        .first()
    )
    if existing is not None:
        return existing, False

    source_company_id = getattr(source_session, "company_id", None)
    source_user_id = getattr(source_session, "user_id", None)
    if source_company_id is not None and str(source_company_id) != str(company_id):
        raise LCopilotUpgradeError("The LCopilot review belongs to another workspace")
    if source_company_id is None and str(source_user_id) != str(current_user.id):
        raise LCopilotUpgradeError("The LCopilot review belongs to another account")

    source_status = _enum_value(getattr(source_session, "status", None))
    review_state = _enum_value(getattr(source_session, "review_state", None))
    if source_status != "completed" and review_state != "delivered":
        raise LCopilotUpgradeError("Complete the LCopilot review before upgrading")
    workflow_type = str(_enum_value(getattr(source_session, "workflow_type", "")) or "")
    if "readiness" in workflow_type:
        raise LCopilotUpgradeError("Only LCopilot instrument reviews can be upgraded")

    result = _structured_result(source_session)
    if not result:
        raise LCopilotUpgradeError("The completed LCopilot result is unavailable")
    lc_number = _text(result, "lc_number", "lc_reference", "reference")
    currency = _text(result, "currency")
    if currency:
        currency = currency.upper()[:3]
    source_report_id = getattr(source_session, "review_report_id", None)
    values = {
        "title": f"Proofline upgrade — {lc_number or str(source_session.id)[:8]}",
        "status": "draft",
        "payment_arrangement": "letter_of_credit",
        "service_package_id": "proofline_standard",
        "currency": currency,
        "amount": _amount(result),
        "source_lcopilot_session_id": source_session.id,
        "document_session_id": source_session.id,
        "transaction_details": {
            "lc_number": lc_number,
            "source_lcopilot_report_id": str(source_report_id) if source_report_id else None,
            "source_lcopilot_result_reused": True,
            "upgrade_created_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    repo = repository or ProoflineRepository(db)
    trade_case = repo.create_case(
        company_id=company_id,
        customer_user_id=current_user.id,
        owner_user_id=current_user.id,
        values=values,
    )
    db.flush()

    for role, name in (
        ("buyer", _text(result, "applicant", "buyer", "importer")),
        ("seller", _text(result, "beneficiary", "seller", "exporter")),
    ):
        if name:
            repo.create_party(
                company_id=company_id,
                case_id=trade_case.id,
                values={"role": role, "name": name, "identifiers": {}},
            )

    type_counts: dict[str, int] = {}
    for document in list(getattr(source_session, "documents", None) or []):
        if not isinstance(document, Document) and not getattr(document, "id", None):
            continue
        document_type = str(getattr(document, "document_type", None) or "supporting_document")
        type_counts[document_type] = type_counts.get(document_type, 0) + 1
        suffix = type_counts[document_type]
        logical_key = document_type if suffix == 1 else f"{document_type}_{suffix}"
        associate_document(
            db,
            trade_case=trade_case,
            company_id=company_id,
            actor_user_id=current_user.id,
            document_id=document.id,
            logical_key=logical_key,
            document_type=document_type,
        )

    reuse_context = {
        "trade_case_id": str(trade_case.id),
        "company_id": str(company_id),
        "source_lcopilot_session_id": str(source_session.id),
        "source_lcopilot_result": result,
    }
    await run_check(
        db,
        trade_case=trade_case,
        applicability=ModuleApplicability(
            module="lcopilot",
            category="payment",
            applicable=True,
            required=True,
            reason="Reused from the completed LCopilot review selected by the customer.",
            state="pending",
        ),
        context=reuse_context,
        adapter=LCopilotAdapter(),
        idempotency_key=f"lcopilot-upgrade:{source_session.id}",
    )
    db.add(
        TradeCaseEvent(
            id=uuid.uuid4(),
            company_id=company_id,
            trade_case_id=trade_case.id,
            event_type="lcopilot_upgrade_created",
            from_status=None,
            to_status="draft",
            actor_type="customer",
            actor_user_id=current_user.id,
            reason="Customer upgraded a completed LCopilot review to Proofline",
            details={
                "source_lcopilot_session_id": str(source_session.id),
                "source_report_id": str(source_report_id) if source_report_id else None,
                "reused_existing_work": True,
            },
            idempotency_key=f"lcopilot-upgrade-created:{source_session.id}",
            occurred_at=datetime.now(timezone.utc),
        )
    )
    return trade_case, True


__all__ = ["LCopilotUpgradeError", "upgrade_lcopilot_session"]
