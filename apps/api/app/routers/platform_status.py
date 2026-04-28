"""Platform status + search endpoints — Phase A12.

Two unrelated but small surfaces grouped together to avoid a router
sprawl:

  GET /api/status   — public health snapshot
  GET /api/search   — auth'd search across the caller's LCs by
                      lc_number, supplier name, or session id

The status endpoint is deliberately public so a customer's status
page widget or Pingdom check can hit it without auth. It does NOT
leak tenant data — only upstream-service health booleans.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..database import get_db
from ..models import User, ValidationSession
from ..models.agency import Supplier
from ..models.services import ServicesClient

logger = logging.getLogger(__name__)


router = APIRouter(tags=["platform"])


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


class UpstreamHealth(BaseModel):
    name: str
    healthy: bool
    note: Optional[str] = None


class StatusResponse(BaseModel):
    healthy: bool
    upstream: List[UpstreamHealth]
    generated_at: datetime
    region: Optional[str] = None


def _llm_configured() -> bool:
    return bool(
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )


def _rulhub_configured() -> bool:
    return bool(
        os.getenv("USE_RULHUB_API", "").lower() in ("true", "1")
        and os.getenv("RULHUB_API_KEY")
    )


def _smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST"))


@router.get("/api/status", response_model=StatusResponse)
async def get_status(db: Session = Depends(get_db)):
    """Public status snapshot. Returns booleans only — no tenant
    data. Frontend `/status` page renders against this; uptime
    monitors can poll it as their healthcheck."""
    upstream: List[UpstreamHealth] = []

    # Database — if get_db gave us a session, the connection is up.
    db_healthy = True
    try:
        db.execute("SELECT 1").scalar()
    except Exception:
        db_healthy = False
    upstream.append(
        UpstreamHealth(
            name="database",
            healthy=db_healthy,
            note=None if db_healthy else "Cannot reach Postgres",
        )
    )

    # LLM — config presence; we don't ping the actual provider here
    # because that costs money on every status hit.
    upstream.append(
        UpstreamHealth(
            name="llm_provider",
            healthy=_llm_configured(),
            note=None if _llm_configured() else "No LLM API key configured",
        )
    )

    # RulHub — config presence (optional integration).
    rulhub_ok = _rulhub_configured()
    upstream.append(
        UpstreamHealth(
            name="rulhub",
            healthy=rulhub_ok,
            note=None if rulhub_ok else "RulHub not enabled (optional)",
        )
    )

    # SMTP / email — config presence.
    smtp_ok = _smtp_configured()
    upstream.append(
        UpstreamHealth(
            name="email",
            healthy=smtp_ok,
            note=None if smtp_ok else "SMTP not configured (notifications skip)",
        )
    )

    overall = db_healthy  # only DB is load-bearing for the platform
    return StatusResponse(
        healthy=overall,
        upstream=upstream,
        generated_at=datetime.now(timezone.utc),
        region=os.getenv("RENDER_REGION") or os.getenv("FLY_REGION"),
    )


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchHit(BaseModel):
    kind: str  # "validation_session" | "supplier" | "services_client"
    id: str
    label: str
    detail: Optional[str] = None
    href: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    total: int
    hits: List[SearchHit]


@router.get("/api/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=128),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cross-entity search scoped to the caller's company. Plain
    ILIKE for v1; can be upgraded to Postgres full-text or trigram
    if the corpus grows past ~10k rows per company."""
    if not current_user or not current_user.company_id:
        return SearchResponse(query=q, total=0, hits=[])

    company_id = current_user.company_id
    needle = f"%{q.strip()}%"
    capped = max(1, min(int(limit or 20), 100))

    hits: List[SearchHit] = []

    # Validation sessions — search by id substring + extracted lc_number
    # via a JSON property on extracted_data when present. Falls back to
    # plain id substring for the simple case.
    sessions = (
        db.query(ValidationSession)
        .filter(ValidationSession.company_id == company_id)
        .filter(ValidationSession.deleted_at.is_(None))
        .order_by(ValidationSession.created_at.desc())
        .limit(capped)
        .all()
    )
    needle_lower = q.strip().lower()
    for s in sessions:
        text_haystack: List[str] = [str(s.id)]
        try:
            ed = s.extracted_data or {}
            if isinstance(ed, dict):
                lc = ed.get("lc") if isinstance(ed.get("lc"), dict) else None
                if isinstance(lc, dict):
                    for key in ("lc_number", "applicant", "beneficiary", "issuing_bank"):
                        v = lc.get(key)
                        if isinstance(v, str):
                            text_haystack.append(v)
        except Exception:
            pass
        if any(needle_lower in s_text.lower() for s_text in text_haystack if s_text):
            hits.append(
                SearchHit(
                    kind="validation_session",
                    id=str(s.id),
                    label=f"LC validation · {s.id}",
                    detail=(
                        f"Lifecycle: {s.lifecycle_state or 'unknown'} · "
                        f"Status: {s.status or 'unknown'}"
                    ),
                    href=f"/exporter/results/{s.id}",
                )
            )
            if len(hits) >= capped:
                break

    # Suppliers (agency persona)
    sup_rows = (
        db.query(Supplier)
        .filter(Supplier.agent_company_id == company_id)
        .filter(Supplier.deleted_at.is_(None))
        .filter(
            or_(
                Supplier.name.ilike(needle),
                Supplier.contact_email.ilike(needle),
                Supplier.country.ilike(needle),
            )
        )
        .limit(capped)
        .all()
    )
    for s in sup_rows:
        hits.append(
            SearchHit(
                kind="supplier",
                id=str(s.id),
                label=s.name,
                detail=f"{s.country or '—'} · {s.contact_email or 'no contact'}",
                href="/lcopilot/agency-dashboard",
            )
        )

    # Services clients
    client_rows = (
        db.query(ServicesClient)
        .filter(ServicesClient.services_company_id == company_id)
        .filter(ServicesClient.deleted_at.is_(None))
        .filter(
            or_(
                ServicesClient.name.ilike(needle),
                ServicesClient.contact_email.ilike(needle),
                ServicesClient.country.ilike(needle),
            )
        )
        .limit(capped)
        .all()
    )
    for c in client_rows:
        hits.append(
            SearchHit(
                kind="services_client",
                id=str(c.id),
                label=c.name,
                detail=f"{c.country or '—'} · {c.contact_email or 'no contact'}",
                href="/lcopilot/services-dashboard",
            )
        )

    return SearchResponse(query=q, total=len(hits), hits=hits[:capped])


__all__ = ["router"]
