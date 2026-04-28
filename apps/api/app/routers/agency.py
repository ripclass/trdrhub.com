"""Agency persona CRUD + portfolio — Phase A5.

Backs the rebuilt /lcopilot/agency-dashboard. All endpoints scope by
``current_user.company_id`` so agents only see their own rosters.

Endpoints:
  GET    /api/agency/suppliers
  POST   /api/agency/suppliers
  GET    /api/agency/suppliers/{id}
  PATCH  /api/agency/suppliers/{id}
  DELETE /api/agency/suppliers/{id}
  GET    /api/agency/buyers
  POST   /api/agency/buyers
  GET    /api/agency/buyers/{id}
  PATCH  /api/agency/buyers/{id}
  DELETE /api/agency/buyers/{id}
  GET    /api/agency/portfolio   — KPIs across all suppliers + recent activity
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..database import get_db
from ..models import Discrepancy, User, ValidationSession
from ..models.agency import ForeignBuyer, Supplier

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/agency", tags=["agency"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SupplierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    country: Optional[str] = Field(None, max_length=2)
    factory_address: Optional[str] = Field(None, max_length=2000)
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = Field(None, max_length=4000)
    foreign_buyer_id: Optional[UUID] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    country: Optional[str] = Field(None, max_length=2)
    factory_address: Optional[str] = Field(None, max_length=2000)
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = Field(None, max_length=4000)
    foreign_buyer_id: Optional[UUID] = None


class SupplierRead(BaseModel):
    id: UUID
    agent_company_id: UUID
    name: str
    country: Optional[str]
    factory_address: Optional[str]
    contact_name: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    notes: Optional[str]
    foreign_buyer_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    # Computed counts surfaced on list view to save the frontend a
    # second round-trip.
    active_lc_count: int = 0
    open_discrepancy_count: int = 0


class ForeignBuyerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    country: Optional[str] = Field(None, max_length=2)
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = Field(None, max_length=4000)


class ForeignBuyerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    country: Optional[str] = Field(None, max_length=2)
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = Field(None, max_length=4000)


class ForeignBuyerRead(BaseModel):
    id: UUID
    agent_company_id: UUID
    name: str
    country: Optional[str]
    contact_name: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class PortfolioActivity(BaseModel):
    validation_session_id: UUID
    supplier_id: Optional[UUID]
    supplier_name: Optional[str]
    lifecycle_state: Optional[str]
    status: str
    created_at: datetime


class PortfolioRead(BaseModel):
    supplier_count: int
    foreign_buyer_count: int
    active_lc_count: int
    open_discrepancy_count: int
    completed_this_month: int
    recent_activity: List[PortfolioActivity]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _company_id_or_403(user: User) -> UUID:
    if not user or not user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agency endpoints require a company-scoped user",
        )
    return user.company_id


def _load_owned_supplier(db: Session, user: User, supplier_id: UUID) -> Supplier:
    company_id = _company_id_or_403(user)
    row = (
        db.query(Supplier)
        .filter(Supplier.id == supplier_id)
        .filter(Supplier.agent_company_id == company_id)
        .filter(Supplier.deleted_at.is_(None))
        .first()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")
    return row


def _load_owned_buyer(db: Session, user: User, buyer_id: UUID) -> ForeignBuyer:
    company_id = _company_id_or_403(user)
    row = (
        db.query(ForeignBuyer)
        .filter(ForeignBuyer.id == buyer_id)
        .filter(ForeignBuyer.agent_company_id == company_id)
        .filter(ForeignBuyer.deleted_at.is_(None))
        .first()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foreign buyer not found")
    return row


_TERMINAL_LIFECYCLE = frozenset({"paid", "closed", "expired"})


def _supplier_to_read(
    row: Supplier,
    *,
    active_lc_count: int = 0,
    open_discrepancy_count: int = 0,
) -> SupplierRead:
    return SupplierRead(
        id=row.id,
        agent_company_id=row.agent_company_id,
        name=row.name,
        country=row.country,
        factory_address=row.factory_address,
        contact_name=row.contact_name,
        contact_email=row.contact_email,
        contact_phone=row.contact_phone,
        notes=row.notes,
        foreign_buyer_id=row.foreign_buyer_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        active_lc_count=active_lc_count,
        open_discrepancy_count=open_discrepancy_count,
    )


def _buyer_to_read(row: ForeignBuyer) -> ForeignBuyerRead:
    return ForeignBuyerRead(
        id=row.id,
        agent_company_id=row.agent_company_id,
        name=row.name,
        country=row.country,
        contact_name=row.contact_name,
        contact_email=row.contact_email,
        contact_phone=row.contact_phone,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------


@router.get("/suppliers", response_model=List[SupplierRead])
async def list_suppliers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = _company_id_or_403(current_user)

    suppliers = (
        db.query(Supplier)
        .filter(Supplier.agent_company_id == company_id)
        .filter(Supplier.deleted_at.is_(None))
        .order_by(Supplier.created_at.desc())
        .all()
    )
    if not suppliers:
        return []

    supplier_ids = [s.id for s in suppliers]

    # Bulk count active LCs (sessions not in terminal lifecycle states)
    active_rows = (
        db.query(ValidationSession.supplier_id, func.count(ValidationSession.id))
        .filter(ValidationSession.supplier_id.in_(supplier_ids))
        .filter(~ValidationSession.lifecycle_state.in_(_TERMINAL_LIFECYCLE))
        .group_by(ValidationSession.supplier_id)
        .all()
    )
    active_by_supplier = {sid: int(count) for sid, count in active_rows if sid is not None}

    # Bulk count open discrepancies (state IN raised/acknowledged/responded/repaper)
    open_states = ("raised", "acknowledged", "responded", "repaper")
    open_rows = (
        db.query(ValidationSession.supplier_id, func.count(Discrepancy.id))
        .join(Discrepancy, Discrepancy.validation_session_id == ValidationSession.id)
        .filter(ValidationSession.supplier_id.in_(supplier_ids))
        .filter(Discrepancy.state.in_(open_states))
        .filter(Discrepancy.deleted_at.is_(None))
        .group_by(ValidationSession.supplier_id)
        .all()
    )
    open_by_supplier = {sid: int(count) for sid, count in open_rows if sid is not None}

    return [
        _supplier_to_read(
            s,
            active_lc_count=active_by_supplier.get(s.id, 0),
            open_discrepancy_count=open_by_supplier.get(s.id, 0),
        )
        for s in suppliers
    ]


@router.post(
    "/suppliers",
    response_model=SupplierRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_supplier(
    body: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = _company_id_or_403(current_user)
    if body.foreign_buyer_id is not None:
        # Verify the buyer belongs to the same company
        _load_owned_buyer(db, current_user, body.foreign_buyer_id)

    supplier = Supplier(
        agent_company_id=company_id,
        name=body.name,
        country=body.country,
        factory_address=body.factory_address,
        contact_name=body.contact_name,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        notes=body.notes,
        foreign_buyer_id=body.foreign_buyer_id,
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return _supplier_to_read(supplier)


@router.get("/suppliers/{supplier_id}", response_model=SupplierRead)
async def get_supplier(
    supplier_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _load_owned_supplier(db, current_user, supplier_id)
    active = (
        db.query(func.count(ValidationSession.id))
        .filter(ValidationSession.supplier_id == row.id)
        .filter(~ValidationSession.lifecycle_state.in_(_TERMINAL_LIFECYCLE))
        .scalar()
        or 0
    )
    open_disc = (
        db.query(func.count(Discrepancy.id))
        .join(
            ValidationSession,
            Discrepancy.validation_session_id == ValidationSession.id,
        )
        .filter(ValidationSession.supplier_id == row.id)
        .filter(Discrepancy.state.in_(("raised", "acknowledged", "responded", "repaper")))
        .filter(Discrepancy.deleted_at.is_(None))
        .scalar()
        or 0
    )
    return _supplier_to_read(
        row,
        active_lc_count=int(active),
        open_discrepancy_count=int(open_disc),
    )


@router.patch("/suppliers/{supplier_id}", response_model=SupplierRead)
async def update_supplier(
    supplier_id: UUID,
    body: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _load_owned_supplier(db, current_user, supplier_id)
    payload = body.model_dump(exclude_unset=True)
    if "foreign_buyer_id" in payload and payload["foreign_buyer_id"] is not None:
        _load_owned_buyer(db, current_user, payload["foreign_buyer_id"])
    for key, value in payload.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _supplier_to_read(row)


@router.delete(
    "/suppliers/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_supplier(
    supplier_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _load_owned_supplier(db, current_user, supplier_id)
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Foreign buyers
# ---------------------------------------------------------------------------


@router.get("/buyers", response_model=List[ForeignBuyerRead])
async def list_buyers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = _company_id_or_403(current_user)
    rows = (
        db.query(ForeignBuyer)
        .filter(ForeignBuyer.agent_company_id == company_id)
        .filter(ForeignBuyer.deleted_at.is_(None))
        .order_by(ForeignBuyer.created_at.desc())
        .all()
    )
    return [_buyer_to_read(r) for r in rows]


@router.post(
    "/buyers",
    response_model=ForeignBuyerRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_buyer(
    body: ForeignBuyerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = _company_id_or_403(current_user)
    buyer = ForeignBuyer(
        agent_company_id=company_id,
        name=body.name,
        country=body.country,
        contact_name=body.contact_name,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        notes=body.notes,
    )
    db.add(buyer)
    db.commit()
    db.refresh(buyer)
    return _buyer_to_read(buyer)


@router.get("/buyers/{buyer_id}", response_model=ForeignBuyerRead)
async def get_buyer(
    buyer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _buyer_to_read(_load_owned_buyer(db, current_user, buyer_id))


@router.patch("/buyers/{buyer_id}", response_model=ForeignBuyerRead)
async def update_buyer(
    buyer_id: UUID,
    body: ForeignBuyerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _load_owned_buyer(db, current_user, buyer_id)
    payload = body.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _buyer_to_read(row)


@router.delete(
    "/buyers/{buyer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_buyer(
    buyer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _load_owned_buyer(db, current_user, buyer_id)
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------


@router.get("/portfolio", response_model=PortfolioRead)
async def get_portfolio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """KPI strip + recent activity for the agency dashboard."""
    company_id = _company_id_or_403(current_user)

    supplier_count = (
        db.query(func.count(Supplier.id))
        .filter(Supplier.agent_company_id == company_id)
        .filter(Supplier.deleted_at.is_(None))
        .scalar()
        or 0
    )
    buyer_count = (
        db.query(func.count(ForeignBuyer.id))
        .filter(ForeignBuyer.agent_company_id == company_id)
        .filter(ForeignBuyer.deleted_at.is_(None))
        .scalar()
        or 0
    )

    # All sessions attributed to a supplier in this company.
    supplier_ids_q = (
        db.query(Supplier.id)
        .filter(Supplier.agent_company_id == company_id)
        .filter(Supplier.deleted_at.is_(None))
        .subquery()
    )

    active_lc_count = (
        db.query(func.count(ValidationSession.id))
        .filter(ValidationSession.supplier_id.in_(supplier_ids_q))
        .filter(~ValidationSession.lifecycle_state.in_(_TERMINAL_LIFECYCLE))
        .scalar()
        or 0
    )

    open_disc_count = (
        db.query(func.count(Discrepancy.id))
        .join(
            ValidationSession,
            Discrepancy.validation_session_id == ValidationSession.id,
        )
        .filter(ValidationSession.supplier_id.in_(supplier_ids_q))
        .filter(Discrepancy.state.in_(("raised", "acknowledged", "responded", "repaper")))
        .filter(Discrepancy.deleted_at.is_(None))
        .scalar()
        or 0
    )

    # Completed this month — sessions that landed in a terminal-ish
    # state since the first of the calendar month.
    from datetime import date as _date, time as _time

    first_of_month = datetime.combine(
        _date.today().replace(day=1), _time.min
    ).replace(tzinfo=timezone.utc)
    completed_this_month = (
        db.query(func.count(ValidationSession.id))
        .filter(ValidationSession.supplier_id.in_(supplier_ids_q))
        .filter(ValidationSession.processing_completed_at.isnot(None))
        .filter(ValidationSession.processing_completed_at >= first_of_month)
        .scalar()
        or 0
    )

    # Recent activity: 10 most recent sessions across all suppliers.
    activity_rows = (
        db.query(
            ValidationSession.id,
            ValidationSession.supplier_id,
            ValidationSession.lifecycle_state,
            ValidationSession.status,
            ValidationSession.created_at,
            Supplier.name,
        )
        .outerjoin(Supplier, Supplier.id == ValidationSession.supplier_id)
        .filter(ValidationSession.supplier_id.in_(supplier_ids_q))
        .order_by(ValidationSession.created_at.desc())
        .limit(10)
        .all()
    )
    activity = [
        PortfolioActivity(
            validation_session_id=row[0],
            supplier_id=row[1],
            supplier_name=row[5],
            lifecycle_state=row[2],
            status=row[3] or "unknown",
            created_at=row[4],
        )
        for row in activity_rows
    ]

    return PortfolioRead(
        supplier_count=int(supplier_count),
        foreign_buyer_count=int(buyer_count),
        active_lc_count=int(active_lc_count),
        open_discrepancy_count=int(open_disc_count),
        completed_this_month=int(completed_this_month),
        recent_activity=activity,
    )


__all__ = ["router"]
