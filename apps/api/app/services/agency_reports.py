"""Agency persona reports — Phase A7 slice 3.

Aggregates per-supplier and per-buyer activity into structured
summaries the dashboard renders inline + a small ReportLab PDF the
agent can hand to a client / archive.

Counts pull from ValidationSession + Discrepancy + RepaperingRequest
scoped by ``Supplier.agent_company_id == current_user.company_id``.
The PDF is a minimal one-pager — header, summary table, recent
activity table. Heavier formatting can land later if customers
push for it.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Discrepancy, ValidationSession
from ..models.agency import ForeignBuyer, Supplier
from ..models.discrepancy_workflow import RepaperingRequest


_TERMINAL_LIFECYCLE = frozenset({"paid", "closed", "expired"})
_OPEN_DISCREPANCY_STATES = ("raised", "acknowledged", "responded", "repaper")


@dataclass
class ReportRecentSession:
    validation_session_id: UUID
    lifecycle_state: Optional[str]
    status: str
    findings_count: int
    created_at: datetime


@dataclass
class SupplierReport:
    supplier_id: UUID
    supplier_name: str
    country: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    foreign_buyer_id: Optional[UUID]
    foreign_buyer_name: Optional[str]

    total_sessions: int
    active_sessions: int
    completed_this_month: int
    total_discrepancies: int
    open_discrepancies: int
    repaper_requests: int
    repaper_open: int
    discrepancy_rate: float  # discrepancies / total_sessions, 0..N
    recent_sessions: List[ReportRecentSession] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class BuyerReport:
    buyer_id: UUID
    buyer_name: str
    country: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    supplier_count: int
    total_sessions: int
    active_sessions: int
    open_discrepancies: int
    suppliers: List["SupplierReport"] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _first_of_month_utc() -> datetime:
    return datetime.combine(date.today().replace(day=1), time.min).replace(
        tzinfo=timezone.utc
    )


def build_supplier_report(
    db: Session, supplier: Supplier, *, recent_limit: int = 10
) -> SupplierReport:
    """Aggregate everything we know about one supplier into a single
    structured payload. Caller is expected to have already verified
    the supplier belongs to current_user's company."""
    base_q = db.query(ValidationSession).filter(
        ValidationSession.supplier_id == supplier.id
    )

    total_sessions = int(base_q.count() or 0)
    active_sessions = int(
        base_q.filter(
            ~ValidationSession.lifecycle_state.in_(_TERMINAL_LIFECYCLE)
        ).count()
        or 0
    )
    completed_this_month = int(
        base_q.filter(ValidationSession.processing_completed_at.isnot(None))
        .filter(ValidationSession.processing_completed_at >= _first_of_month_utc())
        .count()
        or 0
    )

    disc_q = (
        db.query(Discrepancy)
        .join(
            ValidationSession,
            Discrepancy.validation_session_id == ValidationSession.id,
        )
        .filter(ValidationSession.supplier_id == supplier.id)
        .filter(Discrepancy.deleted_at.is_(None))
    )
    total_discrepancies = int(disc_q.count() or 0)
    open_discrepancies = int(
        disc_q.filter(Discrepancy.state.in_(_OPEN_DISCREPANCY_STATES)).count() or 0
    )

    repaper_q = (
        db.query(RepaperingRequest)
        .join(Discrepancy, Discrepancy.id == RepaperingRequest.discrepancy_id)
        .join(
            ValidationSession,
            ValidationSession.id == Discrepancy.validation_session_id,
        )
        .filter(ValidationSession.supplier_id == supplier.id)
    )
    repaper_requests = int(repaper_q.count() or 0)
    repaper_open = int(
        repaper_q.filter(
            RepaperingRequest.state.in_(("requested", "in_progress", "corrected"))
        ).count()
        or 0
    )

    recent_rows = (
        db.query(
            ValidationSession.id,
            ValidationSession.lifecycle_state,
            ValidationSession.status,
            ValidationSession.created_at,
            func.count(Discrepancy.id),
        )
        .outerjoin(
            Discrepancy,
            (Discrepancy.validation_session_id == ValidationSession.id)
            & (Discrepancy.deleted_at.is_(None)),
        )
        .filter(ValidationSession.supplier_id == supplier.id)
        .group_by(
            ValidationSession.id,
            ValidationSession.lifecycle_state,
            ValidationSession.status,
            ValidationSession.created_at,
        )
        .order_by(ValidationSession.created_at.desc())
        .limit(recent_limit)
        .all()
    )
    recent = [
        ReportRecentSession(
            validation_session_id=r[0],
            lifecycle_state=r[1],
            status=r[2] or "unknown",
            findings_count=int(r[4] or 0),
            created_at=r[3],
        )
        for r in recent_rows
    ]

    discrepancy_rate = (
        round(total_discrepancies / total_sessions, 3)
        if total_sessions > 0
        else 0.0
    )

    buyer_name = None
    if supplier.foreign_buyer_id:
        buyer = (
            db.query(ForeignBuyer)
            .filter(ForeignBuyer.id == supplier.foreign_buyer_id)
            .first()
        )
        buyer_name = buyer.name if buyer else None

    return SupplierReport(
        supplier_id=supplier.id,
        supplier_name=supplier.name,
        country=supplier.country,
        contact_email=supplier.contact_email,
        contact_phone=supplier.contact_phone,
        foreign_buyer_id=supplier.foreign_buyer_id,
        foreign_buyer_name=buyer_name,
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        completed_this_month=completed_this_month,
        total_discrepancies=total_discrepancies,
        open_discrepancies=open_discrepancies,
        repaper_requests=repaper_requests,
        repaper_open=repaper_open,
        discrepancy_rate=discrepancy_rate,
        recent_sessions=recent,
    )


def build_buyer_report(db: Session, buyer: ForeignBuyer) -> BuyerReport:
    """Roll-up of every supplier shipping to this buyer."""
    suppliers = (
        db.query(Supplier)
        .filter(Supplier.foreign_buyer_id == buyer.id)
        .filter(Supplier.deleted_at.is_(None))
        .order_by(Supplier.name.asc())
        .all()
    )
    sub_reports = [
        build_supplier_report(db, s, recent_limit=3) for s in suppliers
    ]
    total_sessions = sum(r.total_sessions for r in sub_reports)
    active_sessions = sum(r.active_sessions for r in sub_reports)
    open_disc = sum(r.open_discrepancies for r in sub_reports)
    return BuyerReport(
        buyer_id=buyer.id,
        buyer_name=buyer.name,
        country=buyer.country,
        contact_email=buyer.contact_email,
        contact_phone=buyer.contact_phone,
        supplier_count=len(suppliers),
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        open_discrepancies=open_disc,
        suppliers=sub_reports,
    )


# ---------------------------------------------------------------------------
# PDF rendering — minimal one-pager via ReportLab
# ---------------------------------------------------------------------------


def render_supplier_report_pdf(report: SupplierReport) -> bytes:
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
        name="ReportTitle",
        parent=styles["Heading1"],
        fontSize=18,
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
    body = styles["BodyText"]

    flow = []
    flow.append(Paragraph(f"Supplier report — {report.supplier_name}", title))
    flow.append(
        Paragraph(
            f"{report.country or '—'} · {report.contact_email or 'no contact'} ·"
            f" Generated {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            subtitle,
        )
    )

    summary_rows = [
        ["Metric", "Value"],
        ["Total LCs", str(report.total_sessions)],
        ["Active LCs (not paid/closed/expired)", str(report.active_sessions)],
        ["Completed this month", str(report.completed_this_month)],
        ["Total discrepancies raised", str(report.total_discrepancies)],
        ["Open discrepancies", str(report.open_discrepancies)],
        ["Re-paper requests sent", str(report.repaper_requests)],
        ["Re-paper requests open", str(report.repaper_open)],
        [
            "Discrepancy rate (raised / LC)",
            f"{report.discrepancy_rate:.2f}",
        ],
        ["Default foreign buyer", report.foreign_buyer_name or "—"],
    ]
    flow.append(Paragraph("Summary", h2))
    summary = Table(summary_rows, colWidths=[None, None], hAlign="LEFT")
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ]
        )
    )
    flow.append(summary)
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("Recent activity", h2))
    if not report.recent_sessions:
        flow.append(Paragraph("No validations yet for this supplier.", body))
    else:
        recent_rows = [["Created", "Lifecycle", "Status", "Findings"]]
        for r in report.recent_sessions:
            recent_rows.append(
                [
                    r.created_at.strftime("%Y-%m-%d %H:%M"),
                    r.lifecycle_state or "—",
                    r.status,
                    str(r.findings_count),
                ]
            )
        recent = Table(recent_rows, hAlign="LEFT")
        recent.setStyle(
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
        flow.append(recent)

    doc.build(flow)
    return buf.getvalue()


def render_buyer_report_pdf(report: BuyerReport) -> bytes:
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
        name="ReportTitle",
        parent=styles["Heading1"],
        fontSize=18,
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
    body = styles["BodyText"]

    flow = []
    flow.append(Paragraph(f"Buyer report — {report.buyer_name}", title))
    flow.append(
        Paragraph(
            f"{report.country or '—'} · {report.contact_email or 'no contact'} ·"
            f" Generated {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            subtitle,
        )
    )

    summary_rows = [
        ["Metric", "Value"],
        ["Suppliers shipping to this buyer", str(report.supplier_count)],
        ["Total LCs", str(report.total_sessions)],
        ["Active LCs", str(report.active_sessions)],
        ["Open discrepancies", str(report.open_discrepancies)],
    ]
    flow.append(Paragraph("Summary", h2))
    summary = Table(summary_rows, hAlign="LEFT")
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ]
        )
    )
    flow.append(summary)
    flow.append(Spacer(1, 12))

    flow.append(Paragraph("Suppliers", h2))
    if not report.suppliers:
        flow.append(
            Paragraph("No suppliers have this buyer set as their default.", body)
        )
    else:
        rows = [["Supplier", "Country", "LCs", "Active", "Open"]]
        for s in report.suppliers:
            rows.append(
                [
                    s.supplier_name,
                    s.country or "—",
                    str(s.total_sessions),
                    str(s.active_sessions),
                    str(s.open_discrepancies),
                ]
            )
        tbl = Table(rows, hAlign="LEFT")
        tbl.setStyle(
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
        flow.append(tbl)

    doc.build(flow)
    return buf.getvalue()


__all__ = [
    "BuyerReport",
    "ReportRecentSession",
    "SupplierReport",
    "build_buyer_report",
    "build_supplier_report",
    "render_buyer_report_pdf",
    "render_supplier_report_pdf",
]
