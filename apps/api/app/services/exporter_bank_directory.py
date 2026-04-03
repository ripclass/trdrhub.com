"""
Exporter-safe bank directory helpers.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Company, CompanyStatus, User, UserRole


def list_exporter_available_banks(db: Session) -> dict[str, Any]:
    """Return active bank companies that have at least one active bank user."""
    bank_role_values = [UserRole.BANK_ADMIN.value, UserRole.BANK_OFFICER.value, UserRole.BANK.value]
    active_bank_user_counts = (
        db.query(
            User.company_id.label("company_id"),
            func.count(User.id).label("active_user_count"),
        )
        .filter(
            User.company_id.isnot(None),
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            User.role.in_(bank_role_values),
        )
        .group_by(User.company_id)
        .subquery()
    )

    rows = (
        db.query(Company, active_bank_user_counts.c.active_user_count)
        .join(active_bank_user_counts, active_bank_user_counts.c.company_id == Company.id)
        .filter(Company.status == CompanyStatus.ACTIVE)
        .order_by(func.lower(Company.name).asc())
        .all()
    )

    items = [
        {
            "id": company.id,
            "name": company.name,
            "legal_name": company.legal_name,
            "country": company.country,
            "regulator_id": company.regulator_id,
            "active_user_count": int(active_user_count or 0),
        }
        for company, active_user_count in rows
    ]

    return {"items": items, "total": len(items)}
