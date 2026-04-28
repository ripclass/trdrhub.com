"""User-facing notification dispatcher — Phase A3.

Single entry point: ``dispatch(db, user, notification_type, ...)``.
Writes a row in ``notifications``, fires an email via
``services/email.send_email`` if the user's preferences allow, and
returns the row. Caller commits.

Preferences resolution:
  * If the user record carries ``onboarding_data['notifications']``,
    look up the per-type entry there.
  * Otherwise fall back to ``DEFAULT_NOTIFICATION_PREFS``.

Send failures are logged, never raised — one bad email or DB write
must not break the upstream business logic that triggered it.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models.user_notifications import (
    DEFAULT_NOTIFICATION_PREFS,
    Notification,
    NotificationType,
)
from .email import send_email

logger = logging.getLogger(__name__)


def _resolve_prefs(user: Any, notification_type: str) -> dict[str, bool]:
    """Merge user-set prefs over the per-type default."""
    default = DEFAULT_NOTIFICATION_PREFS.get(
        notification_type,
        {"in_app": True, "email": False},
    )
    onboarding = getattr(user, "onboarding_data", None) or {}
    user_prefs = (onboarding.get("notifications") or {}) if isinstance(onboarding, dict) else {}
    per_type = user_prefs.get(notification_type) if isinstance(user_prefs, dict) else None
    if not isinstance(per_type, dict):
        return dict(default)
    merged = dict(default)
    merged.update({k: bool(v) for k, v in per_type.items() if k in ("in_app", "email")})
    return merged


def _frontend_link(link_url: Optional[str]) -> Optional[str]:
    """Resolve a relative link to a fully-qualified URL using
    settings.FRONTEND_URL. Returns None for None inputs and absolute
    URLs unchanged."""
    if not link_url:
        return None
    if link_url.startswith(("http://", "https://")):
        return link_url
    try:
        from ..config import settings

        base = (settings.FRONTEND_URL or "").rstrip("/")
        if not base:
            return link_url
        suffix = link_url if link_url.startswith("/") else f"/{link_url}"
        return f"{base}{suffix}"
    except Exception:
        return link_url


def dispatch(
    db: Session,
    user: Any,
    notification_type: NotificationType | str,
    *,
    title: str,
    body: str,
    link_url: Optional[str] = None,
    metadata: Optional[dict] = None,
    force_email: bool = False,
) -> Optional[Notification]:
    """Write an in-app notification row and (optionally) send email.

    Returns the row if one was written, None if both channels were
    disabled by the user's prefs (or the user is None).

    Caller commits.
    """
    if user is None:
        return None
    type_value = (
        notification_type.value
        if isinstance(notification_type, NotificationType)
        else str(notification_type)
    )
    prefs = _resolve_prefs(user, type_value)

    row: Optional[Notification] = None
    if prefs.get("in_app", True):
        row = Notification(
            user_id=user.id,
            type=type_value,
            title=title[:255],
            body=body,
            link_url=link_url[:2048] if link_url else None,
            metadata_json=(
                json.dumps(metadata, default=str)
                if isinstance(metadata, dict) and metadata
                else None
            ),
        )
        db.add(row)

    if (force_email or prefs.get("email", False)) and getattr(user, "email", None):
        full_link = _frontend_link(link_url)
        cta = (
            f"<p><a href='{full_link}' style='display:inline-block;padding:8px 14px;"
            f"background:#0f172a;color:#fff;text-decoration:none;border-radius:6px;'>"
            f"Open</a></p>"
            if full_link
            else ""
        )
        html = f"""
        <p>{title}</p>
        <p style='color:#374151;'>{body}</p>
        {cta}
        <p style='color:#6b7280;font-size:12px;'>— TRDR Hub</p>
        """
        try:
            send_email(
                to=user.email,
                subject=title[:200],
                html_body=html,
            )
        except Exception:
            logger.exception(
                "user_notifications.dispatch: email send failed (user=%s type=%s)",
                getattr(user, "id", None),
                type_value,
            )

    return row


__all__ = ["dispatch"]
