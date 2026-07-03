"""Concierge checkout — Phase 5 launch (2026-07).

Stripe Checkout (hosted) at intake: the customer pays first, then the job
enters the operator's review queue. Flow:

    job created → review_state=submitted + payment_status='pending'
      → POST /api/payments/checkout → hosted Stripe page
      → checkout.session.completed webhook → payment_status='paid'
      → report_review.on_engine_complete() advances to UNDER_REVIEW
      → operator sees it; customer gets the confirmation email.

A job at review_state=submitted is invisible to the operator queue (it lists
engine_complete / under_review / needs_info only), so "pay first" needs no
extra gating. Refunds are performed by the operator in the Stripe dashboard;
the charge.refunded webhook just stamps payment_status='refunded' here.

Receipts/invoices are Stripe's built-in emails — nothing custom. No card
data ever touches this app (hosted Checkout only).

Master switch: settings.STRIPE_CHECKOUT_ENABLED (+ a secret key present).
Off = every flow behaves exactly as before Phase 5 (jobs enter the queue
unpaid; operator invoices manually).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, ValidationSession

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Product catalog — server-side source of truth for what can be bought.
# Amounts mirror apps/web/src/lib/pricing.ts (CONCIERGE_REPORTS +
# READINESS_REPORTS); if one changes, change both. The $299/mo retainer is
# deliberately NOT here — it's created by scripts/stripe_setup_products.py
# and offered manually (Payment Link from the dashboard), never in-app.
# ---------------------------------------------------------------------------

LAUNCH_PRODUCTS: Dict[str, Dict[str, Any]] = {
    "pack_review": {
        "name": "LC Pack Review",
        "description": "Full LC presentation set, checked and cited — delivered within 24 hours.",
        "amount_cents": 2900,
        "workflows": ("lc",),
    },
    "pack_review_memo": {
        "name": "LC Pack Review + Bank Memo",
        "description": "Pack review plus a bank-ready compliance memo — delivered within 24 hours.",
        "amount_cents": 4900,
        "workflows": ("lc",),
    },
    "priority_review": {
        "name": "LC Priority Review (6h)",
        "description": "Pack review + bank memo with 6-hour turnaround.",
        "amount_cents": 7900,
        "workflows": ("lc",),
    },
    "cbam_report": {
        "name": "CBAM Supplier-Readiness Report",
        "description": "Cited CBAM readiness assessment — delivered within 24 hours.",
        "amount_cents": 14900,
        "workflows": ("cbam_readiness",),
    },
    "eudr_report": {
        "name": "EUDR Readiness Report",
        "description": "Cited EUDR readiness assessment — delivered within 24 hours.",
        "amount_cents": 14900,
        "workflows": ("eudr_readiness",),
    },
    "cbam_eudr_bundle": {
        "name": "CBAM + EUDR Readiness Bundle",
        "description": "Both readiness reports for one supply chain — delivered within 24 hours.",
        "amount_cents": 24900,
        "workflows": ("cbam_eudr_readiness",),
    },
}

# Which product a readiness intake maps to (LCopilot jobs pick their tier at
# payment time on the status page instead).
READINESS_TOOL_PRODUCTS = {
    "cbam": "cbam_report",
    "eudr": "eudr_report",
    "both": "cbam_eudr_bundle",
}

# LCopilot tiers offered on the status page for an unpaid LC job.
LC_PRODUCT_IDS = ("pack_review", "pack_review_memo", "priority_review")


class CheckoutError(Exception):
    """Payment operation failed — caller maps to an HTTP error."""


def is_checkout_enabled() -> bool:
    """Checkout is live only when the flag is on AND a Stripe key is set."""
    return bool(getattr(settings, "STRIPE_CHECKOUT_ENABLED", False)) and bool(
        getattr(settings, "STRIPE_SECRET_KEY", None)
    )


def _workflow_family(session: ValidationSession) -> str:
    wt = str(getattr(session, "workflow_type", "") or "")
    return wt if wt.endswith("_readiness") else "lc"


def product_ids_for_session(session: ValidationSession) -> list[str]:
    """Products purchasable for this job (used by the status-page pay CTA)."""
    family = _workflow_family(session)
    return [pid for pid, p in LAUNCH_PRODUCTS.items() if family in p["workflows"]]


def create_checkout_session(
    db: Session,
    session: ValidationSession,
    user: User,
    product_id: str,
) -> str:
    """Create a hosted Stripe Checkout session for this job. Returns the URL.

    Idempotent-ish: a new Stripe session supersedes any previous unpaid one
    (the webhook matches on job id from metadata, not the stored session id).
    """
    product = LAUNCH_PRODUCTS.get(product_id)
    if product is None:
        raise CheckoutError(f"Unknown product: {product_id}")
    if _workflow_family(session) not in product["workflows"]:
        raise CheckoutError(f"Product {product_id} does not apply to this job type")
    if session.payment_status == "paid":
        raise CheckoutError("This job is already paid")

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    base = (settings.FRONTEND_URL or "https://trdrhub.com").rstrip("/")
    status_url = f"{base}/lcopilot/status/{session.id}"

    try:
        checkout = stripe.checkout.Session.create(
            mode="payment",
            customer_email=user.email,
            client_reference_id=str(session.id),
            line_items=[{
                "quantity": 1,
                "price_data": {
                    "currency": "usd",
                    "unit_amount": product["amount_cents"],
                    "product_data": {
                        "name": product["name"],
                        "description": product["description"],
                    },
                },
            }],
            metadata={
                "trdr_job_id": str(session.id),
                "trdr_product_id": product_id,
                "trdr_user_id": str(user.id),
            },
            payment_intent_data={
                "metadata": {
                    "trdr_job_id": str(session.id),
                    "trdr_product_id": product_id,
                },
            },
            success_url=f"{status_url}?checkout=success",
            cancel_url=f"{status_url}?checkout=cancelled",
        )
    except Exception as exc:  # stripe.error.* subclasses Exception
        logger.error("Stripe checkout creation failed for %s: %s", session.id, exc)
        raise CheckoutError("Could not start checkout — please try again") from exc

    session.payment_status = "pending"
    session.payment_product_id = product_id
    session.stripe_checkout_session_id = checkout.id
    db.commit()
    logger.info("Checkout %s created for job %s (%s, $%.2f)",
                checkout.id, session.id, product_id, product["amount_cents"] / 100)
    return checkout.url


# ---------------------------------------------------------------------------
# Webhook handlers (called from the signature-verified /billing/webhooks/stripe)
# ---------------------------------------------------------------------------

def handle_checkout_completed(db: Session, event_object: Dict[str, Any]) -> bool:
    """checkout.session.completed → mark paid, advance into the review queue.

    Returns True if the event belonged to a concierge job (handled here),
    False if it should fall through to the legacy subscription machinery.
    Idempotent: replayed events on an already-paid job are no-ops.
    """
    metadata = event_object.get("metadata") or {}
    job_id = metadata.get("trdr_job_id")
    if not job_id:
        return False  # not a concierge checkout — legacy path handles it

    session = (
        db.query(ValidationSession)
        .filter(ValidationSession.id == job_id, ValidationSession.deleted_at.is_(None))
        .first()
    )
    if session is None:
        logger.error("checkout.session.completed for unknown job %s", job_id)
        return True  # ours, but nothing to do — don't hand to legacy path

    if session.payment_status == "paid":
        logger.info("checkout replay for already-paid job %s — noop", job_id)
        return True

    session.payment_status = "paid"
    session.payment_product_id = metadata.get("trdr_product_id") or session.payment_product_id
    session.stripe_checkout_session_id = event_object.get("id") or session.stripe_checkout_session_id
    pi = event_object.get("payment_intent")
    session.stripe_payment_intent_id = str(pi) if pi else session.stripe_payment_intent_id
    amount = event_object.get("amount_total")
    if isinstance(amount, int):
        session.amount_paid_cents = amount
    session.paid_at = datetime.now(timezone.utc)

    # Advance into the operator queue. on_engine_complete walks
    # submitted → processing → engine_complete → under_review and no-ops on
    # jobs already under review / delivered.
    try:
        from app.services import report_review as review
        if getattr(session, "review_state", None) is None:
            review.begin_review(db, session, reason="paid — enrolling in review queue")
        review.on_engine_complete(db, session, reason="payment confirmed")
    except Exception:
        logger.exception("post-payment queue advance failed for %s (payment IS recorded)", job_id)
    db.commit()

    _notify_payment_confirmed(db, session)
    logger.info("Job %s paid (%s, %s cents) → review_state=%s",
                job_id, session.payment_product_id, session.amount_paid_cents,
                session.review_state)
    return True


def handle_charge_refunded(db: Session, event_object: Dict[str, Any]) -> bool:
    """charge.refunded → reflect the dashboard refund. Returns True if handled."""
    metadata = event_object.get("metadata") or {}
    job_id = metadata.get("trdr_job_id")
    session = None
    if job_id:
        session = (
            db.query(ValidationSession)
            .filter(ValidationSession.id == job_id, ValidationSession.deleted_at.is_(None))
            .first()
        )
    if session is None:
        pi = event_object.get("payment_intent")
        if pi:
            session = (
                db.query(ValidationSession)
                .filter(ValidationSession.stripe_payment_intent_id == str(pi))
                .first()
            )
    if session is None:
        return False

    session.payment_status = "refunded"
    session.refunded_at = datetime.now(timezone.utc)
    db.commit()
    logger.warning("Job %s marked refunded (charge %s)", session.id, event_object.get("id"))
    return True


def _notify_payment_confirmed(db: Session, session: ValidationSession) -> None:
    """Confirmation with the 24h SLA promise. Best-effort, never raises."""
    try:
        owner = db.query(User).filter(User.id == session.user_id).first()
        if owner is None:
            return
        product = LAUNCH_PRODUCTS.get(session.payment_product_id or "", {})
        product_name = product.get("name", "your report")
        turnaround = "6 hours" if session.payment_product_id == "priority_review" else "24 hours"
        from app.services.user_notifications import dispatch as _dispatch
        from app.models.user_notifications import NotificationType
        _dispatch(
            db, owner,
            NotificationType.REPORT_UNDER_REVIEW,
            title="Payment received — your review is underway",
            body=(
                f"Thanks — we've received your payment for {product_name}. "
                f"A specialist reviews every report before it ships; yours will be "
                f"delivered within {turnaround}. Your Stripe receipt arrives separately."
            ),
            link_url=f"/lcopilot/status/{session.id}",
            metadata={"validation_session_id": str(session.id)},
        )
        db.commit()
    except Exception:
        logger.exception("payment confirmation notification skipped for %s", session.id)
