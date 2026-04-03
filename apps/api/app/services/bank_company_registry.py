"""
Helpers for identifying and marking bank companies across legacy/live schemas.
"""

from __future__ import annotations

import re
from typing import Any

from app.models import Company, UserRole


_BANK_WORD_RE = re.compile(r"\bbank\b", re.IGNORECASE)
_BANK_META_KEYS = ("tenant_type", "company_type", "business_type")


def bank_role_values() -> list[str]:
    """Return the user-role values that represent bank operators."""
    return [UserRole.BANK_ADMIN.value, UserRole.BANK_OFFICER.value, UserRole.BANK.value]


def _normalized_event_metadata(company: Company) -> dict[str, str]:
    metadata = company.event_metadata or {}
    if not isinstance(metadata, dict):
        return {}
    return {
        str(key).strip().lower(): str(value).strip().lower()
        for key, value in metadata.items()
        if value is not None
    }


def is_bank_company(company: Company) -> bool:
    """
    Identify bank companies across old and new tenant shapes.

    Preferred signal is explicit company metadata. We keep a narrow name-based
    fallback for legacy rows that predate bank metadata backfills.
    """
    metadata = _normalized_event_metadata(company)
    if any(metadata.get(key) == "bank" for key in _BANK_META_KEYS):
        return True

    company_name_candidates = [
        getattr(company, "name", None),
        getattr(company, "legal_name", None),
    ]
    return any(
        isinstance(candidate, str) and _BANK_WORD_RE.search(candidate)
        for candidate in company_name_candidates
    )


def mark_company_as_bank(company: Company) -> None:
    """Stamp bank-company metadata without discarding any existing keys."""
    metadata: dict[str, Any]
    existing = company.event_metadata or {}
    metadata = dict(existing) if isinstance(existing, dict) else {}
    metadata["tenant_type"] = "bank"
    metadata["company_type"] = "bank"
    metadata["business_type"] = "bank"
    company.event_metadata = metadata
