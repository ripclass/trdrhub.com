"""Concierge payments API — Phase 5 launch (2026-07).

POST /api/payments/checkout — owner-scoped: create a hosted Stripe Checkout
session for a job and return its URL. The status page drives this: unpaid
LC jobs offer the three tiers ($29/$49/$79); readiness jobs carry their
product from intake. Webhook processing lives in /billing/webhooks/stripe
(signature-verified) → app/services/checkout.py handlers.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models import User, ValidationSession
from app.services.checkout import (
    LAUNCH_PRODUCTS,
    CheckoutError,
    create_checkout_session,
    is_checkout_enabled,
    product_ids_for_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["Payments"])


class CheckoutRequest(BaseModel):
    job_id: str
    product_id: str


def _owned_session_or_error(db: Session, job_id: str, user: User) -> ValidationSession:
    session = (
        db.query(ValidationSession)
        .filter(ValidationSession.id == job_id, ValidationSession.deleted_at.is_(None))
        .first()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    owns = str(session.user_id) == str(user.id) or (
        session.company_id is not None
        and getattr(user, "company_id", None) is not None
        and str(session.company_id) == str(user.company_id)
    )
    if not owns:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your job")
    return session


@router.get("/products/{job_id}")
def get_purchasable_products(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Products purchasable for this job (drives the status-page pay CTA)."""
    session = _owned_session_or_error(db, job_id, current_user)
    return {
        "job_id": job_id,
        "checkout_enabled": is_checkout_enabled(),
        "payment_status": session.payment_status,
        "products": [
            {
                "id": pid,
                "name": LAUNCH_PRODUCTS[pid]["name"],
                "description": LAUNCH_PRODUCTS[pid]["description"],
                "amount_usd": LAUNCH_PRODUCTS[pid]["amount_cents"] / 100,
            }
            for pid in product_ids_for_session(session)
        ],
    }


@router.post("/checkout")
def start_checkout(
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a hosted Stripe Checkout session; the frontend redirects to it."""
    if not is_checkout_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Online payment isn't enabled yet — we'll invoice you directly.",
        )
    session = _owned_session_or_error(db, payload.job_id, current_user)
    try:
        url = create_checkout_session(db, session, current_user, payload.product_id)
    except CheckoutError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"checkout_url": url}
