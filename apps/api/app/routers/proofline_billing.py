"""Customer-owned Proofline package, quote, and hosted-checkout endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import TradeCase, User
from app.routers.proofline import ensure_case_write_access
from app.schemas.proofline import (
    ProoflineCheckoutResponse,
    ProoflineQuoteResponse,
    ProoflineServicePackageResponse,
)
from app.services.proofline.billing import (
    ProoflineCheckoutError,
    create_checkout_session,
    is_checkout_enabled,
    public_packages,
    quote_for_case,
)


router = APIRouter(prefix="/api/proofline", tags=["proofline-billing"])


def _owned_case(db: Session, current_user: User, case_id: UUID) -> TradeCase:
    company_id = getattr(current_user, "company_id", None)
    if company_id is None:
        raise HTTPException(status_code=403, detail="A company workspace is required")
    trade_case = (
        db.query(TradeCase)
        .filter(
            TradeCase.id == case_id,
            TradeCase.company_id == company_id,
            TradeCase.deleted_at.is_(None),
        )
        .first()
    )
    if trade_case is None:
        raise HTTPException(status_code=404, detail="Trade case not found")
    return trade_case


@router.get("/packages", response_model=list[ProoflineServicePackageResponse])
def list_proofline_packages(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProoflineServicePackageResponse]:
    if getattr(current_user, "company_id", None) is None:
        raise HTTPException(status_code=403, detail="A company workspace is required")
    return [
        ProoflineServicePackageResponse.model_validate(item)
        for item in public_packages(db)
    ]


@router.get("/cases/{case_id}/quote", response_model=ProoflineQuoteResponse)
def get_case_quote(
    case_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProoflineQuoteResponse:
    trade_case = _owned_case(db, current_user, case_id)
    try:
        package, quote = quote_for_case(db, trade_case)
    except ProoflineCheckoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ProoflineQuoteResponse(
        package=ProoflineServicePackageResponse.model_validate(package),
        currency=quote.currency,
        base_amount_cents=quote.base_amount_cents,
        credit_amount_cents=quote.credit_amount_cents,
        amount_due_cents=quote.amount_due_cents,
        credit_eligible_until=quote.credit_eligible_until,
        checkout_enabled=is_checkout_enabled(),
    )


@router.post("/cases/{case_id}/checkout", response_model=ProoflineCheckoutResponse)
def start_case_checkout(
    case_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProoflineCheckoutResponse:
    ensure_case_write_access(db, current_user)
    if not is_checkout_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Online Proofline payment is not enabled; your team will arrange invoicing.",
        )
    trade_case = _owned_case(db, current_user, case_id)
    try:
        package, quote = quote_for_case(db, trade_case)
        url = create_checkout_session(db, trade_case, package, current_user, quote=quote)
    except ProoflineCheckoutError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ProoflineCheckoutResponse(checkout_url=url)
