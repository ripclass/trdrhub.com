"""
Exporter-safe bank directory helpers.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Company, CompanyStatus, User
from app.services.bank_company_registry import bank_role_values, is_bank_company


def list_exporter_available_banks(db: Session) -> dict[str, Any]:
    """
    Return exporter-safe bank companies.

    Preferred source is active bank users linked to active companies. We also
    include explicit bank-company rows as a temporary bridge for legacy live
    data where bank users exist but were never linked back to their company.
    """
    bank_roles = bank_role_values()
    active_bank_user_counts = (
        db.query(
            User.company_id.label("company_id"),
            func.count(User.id).label("active_user_count"),
        )
        .filter(
            User.company_id.isnot(None),
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            User.role.in_(bank_roles),
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

    items = []
    seen_company_ids = set()

    for company, active_user_count in rows:
        items.append(
            {
                "id": company.id,
                "name": company.name,
                "legal_name": company.legal_name,
                "country": company.country,
                "regulator_id": company.regulator_id,
                "active_user_count": int(active_user_count or 0),
            }
        )
        seen_company_ids.add(company.id)

    fallback_companies = (
        db.query(Company)
        .filter(Company.status == CompanyStatus.ACTIVE)
        .order_by(func.lower(Company.name).asc())
        .all()
    )
    for company in fallback_companies:
        if company.id in seen_company_ids or not is_bank_company(company):
            continue
        items.append(
            {
                "id": company.id,
                "name": company.name,
                "legal_name": company.legal_name,
                "country": company.country,
                "regulator_id": company.regulator_id,
                "active_user_count": 0,
            }
        )

    return {"items": items, "total": len(items)}
