"""User-facing notification endpoints — Phase A3.

Backs the bell icon + dropdown + settings panel.

Endpoints (all require auth):
  GET  /api/notifications                      — recent list
  GET  /api/notifications/unread-count         — for the bell badge
  POST /api/notifications/{id}/read            — mark one read
  POST /api/notifications/read-all             — mark every unread read
  GET  /api/notifications/preferences          — read prefs
  PUT  /api/notifications/preferences          — update prefs
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..database import get_db
from ..models import User
from ..models.user_notifications import (
    DEFAULT_NOTIFICATION_PREFS,
    Notification,
    NOTIFICATION_TYPE_VALUES,
)

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class NotificationRead(BaseModel):
    id: UUID
    type: str
    title: str
    body: str
    link_url: Optional[str]
    metadata: Optional[dict]
    read_at: Optional[datetime]
    created_at: datetime


class UnreadCountResponse(BaseModel):
    unread_count: int


class PreferenceEntry(BaseModel):
    in_app: bool
    email: bool


class PreferencesRead(BaseModel):
    preferences: dict[str, PreferenceEntry]


class PreferencesUpdate(BaseModel):
    preferences: dict[str, PreferenceEntry] = Field(
        ...,
        description="Map of notification type -> {in_app, email}.",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_read(row: Notification) -> NotificationRead:
    metadata: Optional[dict] = None
    if row.metadata_json:
        try:
            parsed = json.loads(row.metadata_json)
            if isinstance(parsed, dict):
                metadata = parsed
        except (TypeError, ValueError):
            metadata = None
    return NotificationRead(
        id=row.id,
        type=row.type,
        title=row.title,
        body=row.body,
        link_url=row.link_url,
        metadata=metadata,
        read_at=row.read_at,
        created_at=row.created_at,
    )


def _resolve_prefs(user: User) -> dict[str, dict[str, bool]]:
    """Merge user-stored prefs over defaults so the response always
    reflects every known notification type."""
    onboarding = user.onboarding_data or {}
    user_prefs = (onboarding.get("notifications") or {}) if isinstance(onboarding, dict) else {}
    out: dict[str, dict[str, bool]] = {}
    for type_value, default in DEFAULT_NOTIFICATION_PREFS.items():
        merged = dict(default)
        per_type = user_prefs.get(type_value) if isinstance(user_prefs, dict) else None
        if isinstance(per_type, dict):
            for key in ("in_app", "email"):
                if key in per_type:
                    merged[key] = bool(per_type[key])
        out[type_value] = merged
    return out


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=List[NotificationRead])
async def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    only_unread: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if only_unread:
        q = q.filter(Notification.read_at.is_(None))
    rows = q.order_by(Notification.created_at.desc()).limit(limit).all()
    return [_to_read(r) for r in rows]


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .filter(Notification.read_at.is_(None))
        .count()
    )
    return UnreadCountResponse(unread_count=count)


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .filter(Notification.user_id == current_user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    if row.read_at is None:
        row.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
    return _to_read(row)


@router.post("/read-all")
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .filter(Notification.read_at.is_(None))
        .update({"read_at": now}, synchronize_session=False)
    )
    db.commit()
    return {"marked_read": int(updated or 0)}


@router.get("/preferences", response_model=PreferencesRead)
async def read_preferences(
    current_user: User = Depends(get_current_user),
):
    return PreferencesRead(
        preferences={
            k: PreferenceEntry(**v) for k, v in _resolve_prefs(current_user).items()
        }
    )


@router.put("/preferences", response_model=PreferencesRead)
async def update_preferences(
    body: PreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Whitelist: only persist keys that match a known notification type
    allowed = set(NOTIFICATION_TYPE_VALUES)
    incoming: dict[str, dict[str, bool]] = {}
    for k, v in body.preferences.items():
        if k in allowed:
            incoming[k] = {"in_app": bool(v.in_app), "email": bool(v.email)}

    onboarding = dict(current_user.onboarding_data or {})
    existing = onboarding.get("notifications")
    merged = dict(existing) if isinstance(existing, dict) else {}
    merged.update(incoming)
    onboarding["notifications"] = merged
    current_user.onboarding_data = onboarding
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return PreferencesRead(
        preferences={
            k: PreferenceEntry(**v) for k, v in _resolve_prefs(current_user).items()
        }
    )


__all__ = ["router"]
