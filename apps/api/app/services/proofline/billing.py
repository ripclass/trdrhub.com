"""Proofline package quotes and Stripe Checkout without duplicating billing rails."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.models import ProoflineServicePackage, TradeCase, TradeCaseStatus, User, ValidationSession
from app.services.proofline.state import transition_case


logger = logging.getLogger(__name__)


class ProoflineCheckoutError(ValueError):
    """The selected case/package cannot enter hosted checkout."""


@dataclass(frozen=True)
class ProoflineQuote:
    package_id: str
    currency: str
    base_amount_cents: int
    credit_amount_cents: int
    amount_due_cents: int
    credit_eligible_until: Optional[datetime]


@dataclass(frozen=True)
class ProoflineWebhookResult:
    handled: bool
    case_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    should_process: bool = False


def is_checkout_enabled() -> bool:
    return bool(getattr(settings, "PROOFLINE_CHECKOUT_ENABLED", False)) and bool(
        getattr(settings, "STRIPE_SECRET_KEY", None)
    )


def public_packages(db: Session) -> list[ProoflineServicePackage]:
    return (
        db.query(ProoflineServicePackage)
        .filter(
            ProoflineServicePackage.active.is_(True),
            ProoflineServicePackage.is_public.is_(True),
        )
        .order_by(ProoflineServicePackage.display_order.asc())
        .all()
    )


def calculate_quote(
    package: ProoflineServicePackage | Any,
    *,
    source_lcopilot_session: Optional[ValidationSession | Any] = None,
    now: Optional[datetime] = None,
    credit_days: Optional[int] = None,
    credit_percent: Optional[int] = None,
) -> ProoflineQuote:
    base = int(getattr(package, "amount_cents", 0) or 0)
    currency = str(getattr(package, "currency", "USD") or "USD").upper()
    evaluated_at = now or datetime.now(timezone.utc)
    days = max(
        0,
        int(
            credit_days
            if credit_days is not None
            else settings.PROOFLINE_LCOPILOT_CREDIT_DAYS
        ),
    )
    percent = min(
        100,
        max(
            0,
            int(
                credit_percent
                if credit_percent is not None
                else settings.PROOFLINE_LCOPILOT_CREDIT_PERCENT
            ),
        ),
    )
    credit = 0
    eligible_until: Optional[datetime] = None
    if source_lcopilot_session is not None:
        paid_at = getattr(source_lcopilot_session, "paid_at", None)
        if paid_at is not None and paid_at.tzinfo is None:
            paid_at = paid_at.replace(tzinfo=timezone.utc)
        if paid_at is not None:
            eligible_until = paid_at + timedelta(days=days)
        is_eligible = (
            getattr(source_lcopilot_session, "payment_status", None) == "paid"
            and paid_at is not None
            and evaluated_at <= eligible_until
        )
        if is_eligible:
            source_paid = max(
                0, int(getattr(source_lcopilot_session, "amount_paid_cents", 0) or 0)
            )
            credit = min(base, (source_paid * percent) // 100)
    return ProoflineQuote(
        package_id=str(package.id),
        currency=currency,
        base_amount_cents=base,
        credit_amount_cents=credit,
        amount_due_cents=max(0, base - credit),
        credit_eligible_until=eligible_until,
    )


def quote_for_case(
    db: Session, trade_case: TradeCase
) -> tuple[ProoflineServicePackage, ProoflineQuote]:
    if not trade_case.service_package_id:
        raise ProoflineCheckoutError("Select a Proofline service package first")
    package = (
        db.query(ProoflineServicePackage)
        .filter(
            ProoflineServicePackage.id == trade_case.service_package_id,
            ProoflineServicePackage.active.is_(True),
        )
        .first()
    )
    if package is None:
        raise ProoflineCheckoutError("The selected Proofline package is unavailable")
    source = None
    if trade_case.source_lcopilot_session_id:
        source = (
            db.query(ValidationSession)
            .filter(
                ValidationSession.id == trade_case.source_lcopilot_session_id,
                ValidationSession.company_id == trade_case.company_id,
                ValidationSession.deleted_at.is_(None),
            )
            .first()
        )
    return package, calculate_quote(package, source_lcopilot_session=source)


def create_checkout_session(
    db: Session,
    trade_case: TradeCase | Any,
    package: ProoflineServicePackage | Any,
    user: User | Any,
    *,
    quote: Optional[ProoflineQuote] = None,
) -> str:
    if not getattr(package, "active", True):
        raise ProoflineCheckoutError("The selected Proofline package is unavailable")
    if (
        not getattr(package, "self_service_enabled", False)
        or getattr(package, "billing_mode", None) != "payment"
    ):
        raise ProoflineCheckoutError(
            "This case needs a confirmed manual quote before payment"
        )
    if getattr(trade_case, "status", None) != TradeCaseStatus.AWAITING_PAYMENT.value:
        raise ProoflineCheckoutError("Submit the case for review before starting checkout")
    if getattr(trade_case, "payment_status", None) == "paid":
        raise ProoflineCheckoutError("This Proofline case is already paid")
    final_quote = quote or calculate_quote(package)
    if final_quote.amount_due_cents <= 0:
        raise ProoflineCheckoutError(
            "No online payment is due; the case will be released separately"
        )

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    base_url = (settings.FRONTEND_URL or "https://trdrhub.com").rstrip("/")
    case_url = f"{base_url}/proofline/cases/{trade_case.id}"
    stripe_price_id = getattr(package, "stripe_price_id", None)
    if stripe_price_id and final_quote.credit_amount_cents == 0:
        line_item: dict[str, Any] = {"quantity": 1, "price": stripe_price_id}
    else:
        line_item = {
            "quantity": 1,
            "price_data": {
                "currency": final_quote.currency.lower(),
                "unit_amount": final_quote.amount_due_cents,
                "product_data": {
                    "name": package.name,
                    "description": package.description,
                },
            },
        }
    metadata = {
        "trdr_proofline_case_id": str(trade_case.id),
        "trdr_proofline_company_id": str(trade_case.company_id),
        "trdr_proofline_package_id": str(package.id),
        "trdr_proofline_credit_cents": str(final_quote.credit_amount_cents),
        "trdr_user_id": str(user.id),
    }
    try:
        checkout = stripe.checkout.Session.create(
            mode="payment",
            customer_email=user.email,
            client_reference_id=str(trade_case.id),
            line_items=[line_item],
            metadata=metadata,
            payment_intent_data={"metadata": metadata},
            success_url=f"{case_url}?checkout=success",
            cancel_url=f"{case_url}?checkout=cancelled",
        )
    except Exception as exc:
        logger.error(
            "Proofline checkout creation failed for case %s: %s", trade_case.id, exc
        )
        raise ProoflineCheckoutError(
            "Could not start checkout; please try again"
        ) from exc

    trade_case.payment_status = "pending"
    trade_case.stripe_checkout_session_id = checkout.id
    trade_case.credit_amount_cents = final_quote.credit_amount_cents
    trade_case.payment_currency = final_quote.currency
    trade_case.pricing_snapshot = {
        **asdict(final_quote),
        "credit_eligible_until": (
            final_quote.credit_eligible_until.isoformat()
            if final_quote.credit_eligible_until
            else None
        ),
        "package_name": package.name,
        "quoted_at": datetime.now(timezone.utc).isoformat(),
    }
    db.commit()
    return checkout.url


def handle_checkout_completed(
    db: Session, event_object: dict[str, Any]
) -> ProoflineWebhookResult:
    metadata = event_object.get("metadata") or {}
    case_id = metadata.get("trdr_proofline_case_id")
    if not case_id:
        return ProoflineWebhookResult(handled=False)
    trade_case = (
        db.query(TradeCase)
        .filter(TradeCase.id == case_id, TradeCase.deleted_at.is_(None))
        .first()
    )
    if trade_case is None:
        logger.error("Proofline checkout completed for unknown case %s", case_id)
        return ProoflineWebhookResult(handled=True)
    if trade_case.payment_status == "paid":
        return ProoflineWebhookResult(
            handled=True,
            case_id=trade_case.id,
            company_id=trade_case.company_id,
            should_process=trade_case.status == TradeCaseStatus.SUBMITTED.value,
        )

    trade_case.payment_status = "paid"
    trade_case.service_package_id = (
        metadata.get("trdr_proofline_package_id") or trade_case.service_package_id
    )
    trade_case.stripe_checkout_session_id = (
        event_object.get("id") or trade_case.stripe_checkout_session_id
    )
    payment_intent = event_object.get("payment_intent")
    if payment_intent:
        trade_case.stripe_payment_intent_id = str(payment_intent)
    amount = event_object.get("amount_total")
    if isinstance(amount, int):
        trade_case.amount_paid_cents = amount
    currency = event_object.get("currency")
    if currency:
        trade_case.payment_currency = str(currency).upper()
    trade_case.paid_at = datetime.now(timezone.utc)
    should_process = False
    if trade_case.status == TradeCaseStatus.AWAITING_PAYMENT.value:
        transition_case(
            db,
            trade_case,
            TradeCaseStatus.SUBMITTED,
            actor_type="system",
            actor_user_id=None,
            reason="Proofline payment confirmed",
            idempotency_key=f"proofline-payment:{event_object.get('id') or case_id}",
            details={"package_id": trade_case.service_package_id},
        )
        should_process = True
    db.commit()
    return ProoflineWebhookResult(
        handled=True,
        case_id=trade_case.id,
        company_id=trade_case.company_id,
        should_process=should_process,
    )


def handle_charge_refunded(
    db: Session, event_object: dict[str, Any]
) -> ProoflineWebhookResult:
    metadata = event_object.get("metadata") or {}
    case_id = metadata.get("trdr_proofline_case_id")
    query = db.query(TradeCase)
    trade_case = None
    if case_id:
        trade_case = query.filter(
            TradeCase.id == case_id, TradeCase.deleted_at.is_(None)
        ).first()
    elif event_object.get("payment_intent"):
        trade_case = query.filter(
            TradeCase.stripe_payment_intent_id
            == str(event_object["payment_intent"]),
            TradeCase.deleted_at.is_(None),
        ).first()
    if trade_case is None:
        return ProoflineWebhookResult(handled=bool(case_id))
    trade_case.payment_status = "refunded"
    trade_case.refunded_at = datetime.now(timezone.utc)
    db.commit()
    return ProoflineWebhookResult(
        handled=True, case_id=trade_case.id, company_id=trade_case.company_id
    )


__all__ = [
    "ProoflineCheckoutError",
    "ProoflineQuote",
    "ProoflineWebhookResult",
    "calculate_quote",
    "create_checkout_session",
    "handle_charge_refunded",
    "handle_checkout_completed",
    "is_checkout_enabled",
    "public_packages",
    "quote_for_case",
]
