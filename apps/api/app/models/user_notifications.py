"""Per-user in-app notification model — Phase A3.

This is the simple, consumer-facing bell-icon notifications table. It
sits alongside the heavyweight notification_channels / notification_
templates / notification_events / notification_deliveries tables (used
by bank-side multi-channel routing) but doesn't depend on them.

One row = one in-app card. Dispatch is via
``app/services/user_notifications.dispatch`` which writes the row and
optionally fires an email through ``app/services/email.send_email``
based on the user's preferences (stored in
``User.onboarding_data['notifications']``).
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .base import Base


class NotificationType(str, enum.Enum):
    """Stable type strings the dispatcher accepts. Adding a new trigger
    means adding a value here AND a default-pref entry in
    ``DEFAULT_NOTIFICATION_PREFS`` below."""

    DISCREPANCY_RAISED = "discrepancy_raised"
    DISCREPANCY_RESOLVED = "discrepancy_resolved"
    REPAPER_REQUEST_RECEIVED = "repaper_request_received"
    REPAPER_RESOLVED = "repaper_resolved"
    VALIDATION_COMPLETE = "validation_complete"
    BULK_JOB_COMPLETE = "bulk_job_complete"
    LIFECYCLE_TRANSITION = "lifecycle_transition"
    SYSTEM = "system"  # generic catch-all


NOTIFICATION_TYPE_VALUES = tuple(t.value for t in NotificationType)


# Default per-type preferences. Preferences live under
# ``User.onboarding_data['notifications']`` as a flat dict mapping
# type-value -> {"in_app": bool, "email": bool}. Missing keys fall
# back to these defaults.
DEFAULT_NOTIFICATION_PREFS: dict[str, dict[str, bool]] = {
    NotificationType.DISCREPANCY_RAISED.value: {"in_app": True, "email": True},
    NotificationType.DISCREPANCY_RESOLVED.value: {"in_app": True, "email": False},
    NotificationType.REPAPER_REQUEST_RECEIVED.value: {"in_app": True, "email": True},
    NotificationType.REPAPER_RESOLVED.value: {"in_app": True, "email": True},
    NotificationType.VALIDATION_COMPLETE.value: {"in_app": True, "email": False},
    NotificationType.BULK_JOB_COMPLETE.value: {"in_app": True, "email": True},
    NotificationType.LIFECYCLE_TRANSITION.value: {"in_app": False, "email": False},
    NotificationType.SYSTEM.value: {"in_app": True, "email": False},
}


class Notification(Base):
    """A single in-app notification card for one user.

    Append-only — clients mark as read via ``read_at`` rather than
    deleting. Soft-archive via ``read_at`` + ttl can be layered later
    if list growth becomes a concern.
    """

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    link_url = Column(String(2048), nullable=True)

    # Free-form metadata for the frontend (e.g. {validation_session_id,
    # discrepancy_id, bulk_job_id}). Keep small — no large blobs.
    metadata_json = Column(Text, nullable=True)

    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_notifications_user_unread",
            "user_id",
            "read_at",
            "created_at",
        ),
        Index(
            "ix_notifications_user_created",
            "user_id",
            "created_at",
        ),
    )


__all__ = [
    "DEFAULT_NOTIFICATION_PREFS",
    "NOTIFICATION_TYPE_VALUES",
    "Notification",
    "NotificationType",
]
