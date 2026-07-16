"""Customer-facing Proofline trade-case endpoints."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import CompanyMember, MemberRole, MemberStatus, TradeCaseStatus, User
from app.repositories.proofline import ProoflineRepository
from app.schemas.proofline import (
    TradeCaseCreate,
    TradeCaseDetailResponse,
    TradeCaseListResponse,
    TradeCaseSummaryResponse,
    TradeCaseUpdate,
)
from app.services.audit_service import AuditService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/proofline/cases", tags=["proofline"])


def _company_id(current_user: User) -> UUID:
    company_id = getattr(current_user, "company_id", None)
    if company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A company workspace is required to use Proofline",
        )
    return company_id


def ensure_case_write_access(db: Session, current_user: User) -> None:
    """Enforce current CompanyMember write semantics, with legacy-user continuity."""
    company_id = _company_id(current_user)
    member = (
        db.query(CompanyMember)
        .filter(
            CompanyMember.company_id == company_id,
            CompanyMember.user_id == current_user.id,
            CompanyMember.status == MemberStatus.ACTIVE.value,
        )
        .first()
    )
    if member is not None and member.role == MemberRole.VIEWER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read-only Proofline access",
        )
    if member is None and str(getattr(current_user, "role", "")).lower() == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read-only Proofline access",
        )


def _audit_action(
    *, db: Session, current_user: User, action: str, trade_case_id: UUID, values: dict
) -> None:
    """Call the existing audit hook without including trade-document content."""
    try:
        AuditService(db).log_action(
            action=action,
            user=current_user,
            resource_type="proofline_trade_case",
            resource_id=str(trade_case_id),
            request_data=values,
        )
    except Exception:
        logger.exception(
            "Proofline audit hook failed",
            extra={"trade_case_id": str(trade_case_id), "action": action},
        )


def _case_response(
    repository: ProoflineRepository, trade_case, *, detail: bool
) -> TradeCaseSummaryResponse | TradeCaseDetailResponse:
    document_count, finding_counts = repository.summary_counts(
        company_id=trade_case.company_id, case_id=trade_case.id
    )
    values = {
        "id": trade_case.id,
        "case_reference": trade_case.case_reference,
        "company_id": trade_case.company_id,
        "title": trade_case.title,
        "status": trade_case.status,
        "payment_arrangement": trade_case.payment_arrangement,
        "service_package_id": trade_case.service_package_id,
        "recommended_decision": trade_case.recommended_decision,
        "final_decision": trade_case.final_decision,
        "currency": trade_case.currency,
        "amount": trade_case.amount,
        "origin_country": trade_case.origin_country,
        "destination_country": trade_case.destination_country,
        "document_count": document_count,
        "finding_counts": finding_counts,
        "created_at": trade_case.created_at,
        "updated_at": trade_case.updated_at,
    }
    if detail:
        values.update(
            {
                "customer_user_id": trade_case.customer_user_id,
                "owner_user_id": trade_case.owner_user_id,
                "payment_terms": trade_case.payment_terms,
                "shipment_date": trade_case.shipment_date,
                "expected_payment_date": trade_case.expected_payment_date,
                "transaction_details": trade_case.transaction_details or {},
                "source_lcopilot_session_id": trade_case.source_lcopilot_session_id,
                "final_report_id": trade_case.final_report_id,
            }
        )
        return TradeCaseDetailResponse.model_validate(values)
    return TradeCaseSummaryResponse.model_validate(values)


@router.post("", response_model=TradeCaseDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_trade_case(
    payload: TradeCaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeCaseDetailResponse:
    ensure_case_write_access(db, current_user)
    company_id = _company_id(current_user)
    repository = ProoflineRepository(db)
    values = payload.model_dump(exclude_none=True)
    if "payment_arrangement" in values:
        values["payment_arrangement"] = values["payment_arrangement"].value
    try:
        trade_case = repository.create_case(
            company_id=company_id,
            customer_user_id=current_user.id,
            owner_user_id=current_user.id,
            values=values,
        )
        db.commit()
        db.refresh(trade_case)
    except Exception:
        db.rollback()
        logger.exception("Failed to create Proofline case")
        raise HTTPException(status_code=500, detail="Failed to create trade case")

    _audit_action(
        db=db,
        current_user=current_user,
        action="proofline_case_created",
        trade_case_id=trade_case.id,
        values={
            "payment_arrangement": trade_case.payment_arrangement,
            "service_package_id": trade_case.service_package_id,
        },
    )
    return _case_response(repository, trade_case, detail=True)


@router.get("", response_model=TradeCaseListResponse)
async def list_trade_cases(
    status_filter: Optional[TradeCaseStatus] = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeCaseListResponse:
    company_id = _company_id(current_user)
    repository = ProoflineRepository(db)
    rows, total = repository.list_cases(
        company_id=company_id,
        status=status_filter.value if status_filter else None,
        offset=offset,
        limit=limit,
    )
    return TradeCaseListResponse(
        items=[_case_response(repository, row, detail=False) for row in rows],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{case_id}", response_model=TradeCaseDetailResponse)
async def get_trade_case(
    case_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeCaseDetailResponse:
    repository = ProoflineRepository(db)
    trade_case = repository.get_case(company_id=_company_id(current_user), case_id=case_id)
    if trade_case is None:
        raise HTTPException(status_code=404, detail="Trade case not found")
    return _case_response(repository, trade_case, detail=True)


@router.patch("/{case_id}", response_model=TradeCaseDetailResponse)
async def update_trade_case(
    case_id: UUID,
    payload: TradeCaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TradeCaseDetailResponse:
    ensure_case_write_access(db, current_user)
    repository = ProoflineRepository(db)
    trade_case = repository.get_case(company_id=_company_id(current_user), case_id=case_id)
    if trade_case is None:
        raise HTTPException(status_code=404, detail="Trade case not found")
    if trade_case.status != TradeCaseStatus.DRAFT.value:
        raise HTTPException(status_code=409, detail="Only draft trade cases can be edited")

    values = payload.model_dump(exclude_unset=True)
    if "payment_arrangement" in values and values["payment_arrangement"] is not None:
        values["payment_arrangement"] = values["payment_arrangement"].value
    try:
        repository.update_case(trade_case, values=values)
        db.commit()
        db.refresh(trade_case)
    except Exception:
        db.rollback()
        logger.exception("Failed to update Proofline case", extra={"trade_case_id": str(case_id)})
        raise HTTPException(status_code=500, detail="Failed to update trade case")

    _audit_action(
        db=db,
        current_user=current_user,
        action="proofline_case_updated",
        trade_case_id=trade_case.id,
        values={"updated_fields": sorted(values)},
    )
    return _case_response(repository, trade_case, detail=True)


__all__ = ["router"]

