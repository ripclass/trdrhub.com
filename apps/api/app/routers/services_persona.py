"""Services persona CRUD + portfolio + invoice — Phases A8 + A9.

Mirrors the agency router shape (commit 7b487a4d). Endpoints:

  GET    /api/services/clients
  POST   /api/services/clients
  GET    /api/services/clients/{id}
  PATCH  /api/services/clients/{id}
  DELETE /api/services/clients/{id}

  GET    /api/services/time            — list, optional ?client_id=
  POST   /api/services/time            — log an entry
  PATCH  /api/services/time/{id}       — edit
  DELETE /api/services/time/{id}       — soft-delete

  GET    /api/services/portfolio       — KPI strip + recent activity

  POST   /api/services/invoices/generate            — JSON preview
  POST   /api/services/invoices/generate.pdf        — PDF download

Routes are scoped by ``current_user.company_id``.
"""

from __future__ import annotations

import io
import logging
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..database import get_db
from ..models import Discrepancy, User, ValidationSession
from ..models.services import ServicesClient, TimeEntry

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/services", tags=["services"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    country: Optional[str] = Field(None, max_length=2)
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = Field(None, max_length=4000)
    billing_rate: Optional[Decimal] = None
    retainer_active: Optional[bool] = None
    retainer_hours_per_month: Optional[Decimal] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    country: Optional[str] = Field(None, max_length=2)
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = Field(None, max_length=4000)
    billing_rate: Optional[Decimal] = None
    retainer_active: Optional[bool] = None
    retainer_hours_per_month: Optional[Decimal] = None


class ClientRead(BaseModel):
    id: UUID
    services_company_id: UUID
    name: str
    country: Optional[str]
    contact_name: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    notes: Optional[str]
    billing_rate: Optional[Decimal]
    retainer_active: bool
    retainer_hours_per_month: Optional[Decimal]
    created_at: datetime
    updated_at: datetime
    active_lc_count: int = 0
    open_discrepancy_count: int = 0
    hours_this_month: Decimal = Decimal("0")
    billable_hours_unbilled: Decimal = Decimal("0")


class TimeEntryCreate(BaseModel):
    services_client_id: UUID
    validation_session_id: Optional[UUID] = None
    hours: Decimal = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=4000)
    billable: bool = True
    performed_on: Optional[datetime] = None


class TimeEntryUpdate(BaseModel):
    hours: Optional[Decimal] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=4000)
    billable: Optional[bool] = None
    billed: Optional[bool] = None
    performed_on: Optional[datetime] = None


class TimeEntryRead(BaseModel):
    id: UUID
    services_company_id: UUID
    services_client_id: UUID
    validation_session_id: Optional[UUID]
    user_id: Optional[UUID]
    hours: Decimal
    description: Optional[str]
    billable: bool
    billed: bool
    performed_on: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class PortfolioActivity(BaseModel):
    validation_session_id: UUID
    services_client_id: Optional[UUID]
    client_name: Optional[str]
    lifecycle_state: Optional[str]
    status: str
    created_at: datetime


class PortfolioRead(BaseModel):
    client_count: int
    active_lc_count: int
    open_discrepancy_count: int
    completed_this_month: int
    hours_this_month: Decimal
    billable_hours_unbilled: Decimal
    recent_activity: List[PortfolioActivity]


class InvoiceLineLC(BaseModel):
    validation_session_id: UUID
    lifecycle_state: Optional[str]
    status: str
    created_at: datetime


class InvoiceLineTime(BaseModel):
    time_entry_id: UUID
    description: Optional[str]
    hours: Decimal
    rate: Decimal
    line_total: Decimal
    performed_on: Optional[datetime]


class InvoicePreview(BaseModel):
    client_id: UUID
    client_name: str
    period_start: datetime
    period_end: datetime
    lines: List[InvoiceLineTime]
    lcs: List[InvoiceLineLC]
    total_hours: Decimal
    total_amount: Decimal
    rate: Decimal
    generated_at: datetime


class InvoiceGenerateRequest(BaseModel):
    client_id: UUID
    period_start: datetime
    period_end: datetime
    rate_override: Optional[Decimal] = None
    mark_billed: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_TERMINAL_LIFECYCLE = frozenset({"paid", "closed", "expired"})
_OPEN_DISCREPANCY_STATES = ("raised", "acknowledged", "responded", "repaper")


def _company_id_or_403(user: User) -> UUID:
    if not user or not user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Services endpoints require a company-scoped user",
        )
    return user.company_id


def _load_owned_client(db: Session, user: User, client_id: UUID) -> ServicesClient:
    company_id = _company_id_or_403(user)
    row = (
        db.query(ServicesClient)
        .filter(ServicesClient.id == client_id)
        .filter(ServicesClient.services_company_id == company_id)
        .filter(ServicesClient.deleted_at.is_(None))
        .first()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found")
    return row


def _load_owned_time_entry(db: Session, user: User, entry_id: UUID) -> TimeEntry:
    company_id = _company_id_or_403(user)
    row = (
        db.query(TimeEntry)
        .filter(TimeEntry.id == entry_id)
        .filter(TimeEntry.services_company_id == company_id)
        .filter(TimeEntry.deleted_at.is_(None))
        .first()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Time entry not found")
    return row


def _first_of_month_utc() -> datetime:
    return datetime.combine(date.today().replace(day=1), time.min).replace(
        tzinfo=timezone.utc
    )


def _client_to_read(
    row: ServicesClient,
    *,
    active_lc_count: int = 0,
    open_discrepancy_count: int = 0,
    hours_this_month: Decimal = Decimal("0"),
    billable_hours_unbilled: Decimal = Decimal("0"),
) -> ClientRead:
    return ClientRead(
        id=row.id,
        services_company_id=row.services_company_id,
        name=row.name,
        country=row.country,
        contact_name=row.contact_name,
        contact_email=row.contact_email,
        contact_phone=row.contact_phone,
        notes=row.notes,
        billing_rate=row.billing_rate,
        retainer_active=bool(row.retainer_active),
        retainer_hours_per_month=row.retainer_hours_per_month,
        created_at=row.created_at,
        updated_at=row.updated_at,
        active_lc_count=active_lc_count,
        open_discrepancy_count=open_discrepancy_count,
        hours_this_month=hours_this_month,
        billable_hours_unbilled=billable_hours_unbilled,
    )


def _time_entry_to_read(row: TimeEntry) -> TimeEntryRead:
    return TimeEntryRead(
        id=row.id,
        services_company_id=row.services_company_id,
        services_client_id=row.services_client_id,
        validation_session_id=row.validation_session_id,
        user_id=row.user_id,
        hours=row.hours,
        description=row.description,
        billable=bool(row.billable),
        billed=bool(row.billed),
        performed_on=row.performed_on,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------


@router.get("/clients", response_model=List[ClientRead])
async def list_clients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = _company_id_or_403(current_user)
    clients = (
        db.query(ServicesClient)
        .filter(ServicesClient.services_company_id == company_id)
        .filter(ServicesClient.deleted_at.is_(None))
        .order_by(ServicesClient.created_at.desc())
        .all()
    )
    if not clients:
        return []
    client_ids = [c.id for c in clients]

    active_rows = (
        db.query(ValidationSession.services_client_id, func.count(ValidationSession.id))
        .filter(ValidationSession.services_client_id.in_(client_ids))
        .filter(~ValidationSession.lifecycle_state.in_(_TERMINAL_LIFECYCLE))
        .group_by(ValidationSession.services_client_id)
        .all()
    )
    active_by_client = {cid: int(cnt) for cid, cnt in active_rows if cid is not None}

    open_rows = (
        db.query(ValidationSession.services_client_id, func.count(Discrepancy.id))
        .join(Discrepancy, Discrepancy.validation_session_id == ValidationSession.id)
        .filter(ValidationSession.services_client_id.in_(client_ids))
        .filter(Discrepancy.state.in_(_OPEN_DISCREPANCY_STATES))
        .filter(Discrepancy.deleted_at.is_(None))
        .group_by(ValidationSession.services_client_id)
        .all()
    )
    open_by_client = {cid: int(cnt) for cid, cnt in open_rows if cid is not None}

    first_of_month = _first_of_month_utc()
    hours_rows = (
        db.query(TimeEntry.services_client_id, func.coalesce(func.sum(TimeEntry.hours), 0))
        .filter(TimeEntry.services_client_id.in_(client_ids))
        .filter(TimeEntry.deleted_at.is_(None))
        .filter(
            (TimeEntry.performed_on >= first_of_month)
            | (
                (TimeEntry.performed_on.is_(None))
                & (TimeEntry.created_at >= first_of_month)
            )
        )
        .group_by(TimeEntry.services_client_id)
        .all()
    )
    hours_by_client = {cid: Decimal(str(cnt)) for cid, cnt in hours_rows}

    unbilled_rows = (
        db.query(TimeEntry.services_client_id, func.coalesce(func.sum(TimeEntry.hours), 0))
        .filter(TimeEntry.services_client_id.in_(client_ids))
        .filter(TimeEntry.deleted_at.is_(None))
        .filter(TimeEntry.billable.is_(True))
        .filter(TimeEntry.billed.is_(False))
        .group_by(TimeEntry.services_client_id)
        .all()
    )
    unbilled_by_client = {cid: Decimal(str(cnt)) for cid, cnt in unbilled_rows}

    return [
        _client_to_read(
            c,
            active_lc_count=active_by_client.get(c.id, 0),
            open_discrepancy_count=open_by_client.get(c.id, 0),
            hours_this_month=hours_by_client.get(c.id, Decimal("0")),
            billable_hours_unbilled=unbilled_by_client.get(c.id, Decimal("0")),
        )
        for c in clients
    ]


@router.post(
    "/clients",
    response_model=ClientRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_client(
    body: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = _company_id_or_403(current_user)
    payload = body.model_dump(exclude_unset=True)
    payload.setdefault("retainer_active", False)
    client = ServicesClient(services_company_id=company_id, **payload)
    db.add(client)
    db.commit()
    db.refresh(client)
    return _client_to_read(client)


@router.get("/clients/{client_id}", response_model=ClientRead)
async def get_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _load_owned_client(db, current_user, client_id)
    active = (
        db.query(func.count(ValidationSession.id))
        .filter(ValidationSession.services_client_id == row.id)
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
        .filter(ValidationSession.services_client_id == row.id)
        .filter(Discrepancy.state.in_(_OPEN_DISCREPANCY_STATES))
        .filter(Discrepancy.deleted_at.is_(None))
        .scalar()
        or 0
    )
    first_of_month = _first_of_month_utc()
    hrs = (
        db.query(func.coalesce(func.sum(TimeEntry.hours), 0))
        .filter(TimeEntry.services_client_id == row.id)
        .filter(TimeEntry.deleted_at.is_(None))
        .filter(
            (TimeEntry.performed_on >= first_of_month)
            | (
                (TimeEntry.performed_on.is_(None))
                & (TimeEntry.created_at >= first_of_month)
            )
        )
        .scalar()
        or 0
    )
    unbilled = (
        db.query(func.coalesce(func.sum(TimeEntry.hours), 0))
        .filter(TimeEntry.services_client_id == row.id)
        .filter(TimeEntry.deleted_at.is_(None))
        .filter(TimeEntry.billable.is_(True))
        .filter(TimeEntry.billed.is_(False))
        .scalar()
        or 0
    )
    return _client_to_read(
        row,
        active_lc_count=int(active),
        open_discrepancy_count=int(open_disc),
        hours_this_month=Decimal(str(hrs)),
        billable_hours_unbilled=Decimal(str(unbilled)),
    )


@router.patch("/clients/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: UUID,
    body: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _load_owned_client(db, current_user, client_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _client_to_read(row)


@router.delete(
    "/clients/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _load_owned_client(db, current_user, client_id)
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return None


# ---------------------------------------------------------------------------
# Time entries
# ---------------------------------------------------------------------------


@router.get("/time", response_model=List[TimeEntryRead])
async def list_time_entries(
    client_id: Optional[UUID] = None,
    only_unbilled: bool = False,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = _company_id_or_403(current_user)
    capped = max(1, min(int(limit or 200), 1000))
    q = (
        db.query(TimeEntry)
        .filter(TimeEntry.services_company_id == company_id)
        .filter(TimeEntry.deleted_at.is_(None))
    )
    if client_id is not None:
        q = q.filter(TimeEntry.services_client_id == client_id)
    if only_unbilled:
        q = q.filter(TimeEntry.billable.is_(True)).filter(TimeEntry.billed.is_(False))
    rows = q.order_by(TimeEntry.performed_on.desc().nullslast(), TimeEntry.created_at.desc()).limit(capped).all()
    return [_time_entry_to_read(r) for r in rows]


@router.post(
    "/time",
    response_model=TimeEntryRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_time_entry(
    body: TimeEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company_id = _company_id_or_403(current_user)
    # Verify client ownership before writing.
    _load_owned_client(db, current_user, body.services_client_id)

    entry = TimeEntry(
        services_company_id=company_id,
        services_client_id=body.services_client_id,
        validation_session_id=body.validation_session_id,
        user_id=current_user.id,
        hours=body.hours,
        description=body.description,
        billable=bool(body.billable),
        billed=False,
        performed_on=body.performed_on or datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _time_entry_to_read(entry)


@router.patch("/time/{entry_id}", response_model=TimeEntryRead)
async def update_time_entry(
    entry_id: UUID,
    body: TimeEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _load_owned_time_entry(db, current_user, entry_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _time_entry_to_read(row)


@router.delete("/time/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_time_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _load_owned_time_entry(db, current_user, entry_id)
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
    company_id = _company_id_or_403(current_user)

    client_count = (
        db.query(func.count(ServicesClient.id))
        .filter(ServicesClient.services_company_id == company_id)
        .filter(ServicesClient.deleted_at.is_(None))
        .scalar()
        or 0
    )
    client_ids_q = (
        db.query(ServicesClient.id)
        .filter(ServicesClient.services_company_id == company_id)
        .filter(ServicesClient.deleted_at.is_(None))
        .subquery()
    )
    active_lc = (
        db.query(func.count(ValidationSession.id))
        .filter(ValidationSession.services_client_id.in_(client_ids_q))
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
        .filter(ValidationSession.services_client_id.in_(client_ids_q))
        .filter(Discrepancy.state.in_(_OPEN_DISCREPANCY_STATES))
        .filter(Discrepancy.deleted_at.is_(None))
        .scalar()
        or 0
    )
    first_of_month = _first_of_month_utc()
    completed_this_month = (
        db.query(func.count(ValidationSession.id))
        .filter(ValidationSession.services_client_id.in_(client_ids_q))
        .filter(ValidationSession.processing_completed_at.isnot(None))
        .filter(ValidationSession.processing_completed_at >= first_of_month)
        .scalar()
        or 0
    )
    hours_this_month = (
        db.query(func.coalesce(func.sum(TimeEntry.hours), 0))
        .filter(TimeEntry.services_company_id == company_id)
        .filter(TimeEntry.deleted_at.is_(None))
        .filter(
            (TimeEntry.performed_on >= first_of_month)
            | (
                (TimeEntry.performed_on.is_(None))
                & (TimeEntry.created_at >= first_of_month)
            )
        )
        .scalar()
        or 0
    )
    billable_unbilled = (
        db.query(func.coalesce(func.sum(TimeEntry.hours), 0))
        .filter(TimeEntry.services_company_id == company_id)
        .filter(TimeEntry.deleted_at.is_(None))
        .filter(TimeEntry.billable.is_(True))
        .filter(TimeEntry.billed.is_(False))
        .scalar()
        or 0
    )

    activity_rows = (
        db.query(
            ValidationSession.id,
            ValidationSession.services_client_id,
            ValidationSession.lifecycle_state,
            ValidationSession.status,
            ValidationSession.created_at,
            ServicesClient.name,
        )
        .outerjoin(
            ServicesClient,
            ServicesClient.id == ValidationSession.services_client_id,
        )
        .filter(ValidationSession.services_client_id.in_(client_ids_q))
        .order_by(ValidationSession.created_at.desc())
        .limit(10)
        .all()
    )
    activity = [
        PortfolioActivity(
            validation_session_id=r[0],
            services_client_id=r[1],
            client_name=r[5],
            lifecycle_state=r[2],
            status=r[3] or "unknown",
            created_at=r[4],
        )
        for r in activity_rows
    ]

    return PortfolioRead(
        client_count=int(client_count),
        active_lc_count=int(active_lc),
        open_discrepancy_count=int(open_disc),
        completed_this_month=int(completed_this_month),
        hours_this_month=Decimal(str(hours_this_month)),
        billable_hours_unbilled=Decimal(str(billable_unbilled)),
        recent_activity=activity,
    )


# ---------------------------------------------------------------------------
# Invoice generator (Phase A9)
# ---------------------------------------------------------------------------


def _build_invoice_preview(
    db: Session,
    client: ServicesClient,
    *,
    period_start: datetime,
    period_end: datetime,
    rate_override: Optional[Decimal] = None,
) -> InvoicePreview:
    rate = rate_override if rate_override is not None else (client.billing_rate or Decimal("0"))

    entries = (
        db.query(TimeEntry)
        .filter(TimeEntry.services_client_id == client.id)
        .filter(TimeEntry.deleted_at.is_(None))
        .filter(TimeEntry.billable.is_(True))
        .filter(TimeEntry.billed.is_(False))
        .filter(
            (
                (TimeEntry.performed_on >= period_start)
                & (TimeEntry.performed_on < period_end)
            )
            | (
                (TimeEntry.performed_on.is_(None))
                & (TimeEntry.created_at >= period_start)
                & (TimeEntry.created_at < period_end)
            )
        )
        .order_by(TimeEntry.performed_on.asc().nullsfirst(), TimeEntry.created_at.asc())
        .all()
    )

    lines: List[InvoiceLineTime] = []
    total_hours = Decimal("0")
    for e in entries:
        hours = Decimal(str(e.hours or 0))
        line_total = (hours * rate).quantize(Decimal("0.01"))
        total_hours += hours
        lines.append(
            InvoiceLineTime(
                time_entry_id=e.id,
                description=e.description,
                hours=hours,
                rate=rate,
                line_total=line_total,
                performed_on=e.performed_on,
            )
        )
    total_amount = (total_hours * rate).quantize(Decimal("0.01"))

    lcs_rows = (
        db.query(ValidationSession)
        .filter(ValidationSession.services_client_id == client.id)
        .filter(ValidationSession.created_at >= period_start)
        .filter(ValidationSession.created_at < period_end)
        .order_by(ValidationSession.created_at.asc())
        .limit(50)
        .all()
    )
    lcs = [
        InvoiceLineLC(
            validation_session_id=r.id,
            lifecycle_state=r.lifecycle_state,
            status=r.status or "unknown",
            created_at=r.created_at,
        )
        for r in lcs_rows
    ]

    return InvoicePreview(
        client_id=client.id,
        client_name=client.name,
        period_start=period_start,
        period_end=period_end,
        lines=lines,
        lcs=lcs,
        total_hours=total_hours,
        total_amount=total_amount,
        rate=rate,
        generated_at=datetime.now(timezone.utc),
    )


def _render_invoice_pdf(preview: InvoicePreview) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        name="InvoiceTitle",
        parent=styles["Heading1"],
        fontSize=20,
        spaceAfter=4,
    )
    subtitle = ParagraphStyle(
        name="Subtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=12,
    )
    h2 = ParagraphStyle(
        name="H2", parent=styles["Heading2"], fontSize=12, spaceAfter=6
    )

    flow = [
        Paragraph("Invoice", title),
        Paragraph(
            f"Client: {preview.client_name} · "
            f"{preview.period_start.strftime('%Y-%m-%d')} – "
            f"{preview.period_end.strftime('%Y-%m-%d')} · "
            f"Generated {preview.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            subtitle,
        ),
        Paragraph("Line items", h2),
    ]

    rows = [["Date", "Description", "Hours", "Rate", "Amount"]]
    for line in preview.lines:
        rows.append(
            [
                line.performed_on.strftime("%Y-%m-%d") if line.performed_on else "—",
                (line.description or "")[:60],
                f"{line.hours:.2f}",
                f"{line.rate:.2f}",
                f"{line.line_total:.2f}",
            ]
        )
    rows.append(
        [
            "",
            "",
            f"{preview.total_hours:.2f}",
            "",
            f"{preview.total_amount:.2f}",
        ]
    )
    tbl = Table(rows, hAlign="LEFT")
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
            ]
        )
    )
    flow.append(tbl)
    flow.append(Spacer(1, 12))

    if preview.lcs:
        flow.append(Paragraph("LCs in period", h2))
        lc_rows = [["Created", "Lifecycle", "Status"]]
        for lc in preview.lcs:
            lc_rows.append(
                [
                    lc.created_at.strftime("%Y-%m-%d %H:%M"),
                    lc.lifecycle_state or "—",
                    lc.status,
                ]
            )
        lc_tbl = Table(lc_rows, hAlign="LEFT")
        lc_tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ]
            )
        )
        flow.append(lc_tbl)

    doc.build(flow)
    return buf.getvalue()


@router.post("/invoices/generate", response_model=InvoicePreview)
async def generate_invoice_preview(
    body: InvoiceGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compute the invoice preview without rendering PDF or marking
    entries as billed. Used by the frontend to show the breakdown
    before the user confirms."""
    client = _load_owned_client(db, current_user, body.client_id)
    if body.period_end <= body.period_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period_end must be after period_start",
        )
    preview = _build_invoice_preview(
        db,
        client,
        period_start=body.period_start,
        period_end=body.period_end,
        rate_override=body.rate_override,
    )
    if body.mark_billed and preview.lines:
        ids = [line.time_entry_id for line in preview.lines]
        db.query(TimeEntry).filter(TimeEntry.id.in_(ids)).update(
            {TimeEntry.billed: True}, synchronize_session=False
        )
        db.commit()
    return preview


@router.post("/invoices/generate.pdf")
async def generate_invoice_pdf(
    body: InvoiceGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = _load_owned_client(db, current_user, body.client_id)
    if body.period_end <= body.period_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period_end must be after period_start",
        )
    preview = _build_invoice_preview(
        db,
        client,
        period_start=body.period_start,
        period_end=body.period_end,
        rate_override=body.rate_override,
    )
    if body.mark_billed and preview.lines:
        ids = [line.time_entry_id for line in preview.lines]
        db.query(TimeEntry).filter(TimeEntry.id.in_(ids)).update(
            {TimeEntry.billed: True}, synchronize_session=False
        )
        db.commit()

    pdf = _render_invoice_pdf(preview)
    safe_name = "".join(
        c if c.isalnum() or c in ("-", "_") else "-" for c in client.name
    )[:64].strip("-") or "client"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="invoice-{safe_name}.pdf"'
            )
        },
    )


__all__ = ["router"]
