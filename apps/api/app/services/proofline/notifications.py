"""Best-effort customer notifications for meaningful Proofline milestones."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models import User
from app.models.user_notifications import NotificationType
from app.services.user_notifications import dispatch


logger = logging.getLogger(__name__)

EVENTS: dict[str, tuple[NotificationType, str, str]] = {
    "payment_required": (
        NotificationType.PROOFLINE_ACTION_REQUIRED,
        "Payment required for your Proofline case",
        "Complete checkout so verified trade clearance can begin for case {reference}.",
    ),
    "submitted": (
        NotificationType.PROOFLINE_CASE_UPDATE,
        "Proofline case submitted",
        "We received case {reference} and will begin the applicable checks.",
    ),
    "automated_review_complete": (
        NotificationType.PROOFLINE_CASE_UPDATE,
        "Proofline analyst review is next",
        "Automated checks are complete for case {reference}. A qualified analyst will verify the findings.",
    ),
    "action_required": (
        NotificationType.PROOFLINE_ACTION_REQUIRED,
        "Action required for your Proofline case",
        "Review the requested correction or evidence for case {reference} before final review.",
    ),
    "correction_received": (
        NotificationType.PROOFLINE_CASE_UPDATE,
        "Proofline correction received",
        "We received your correction for case {reference} and will review the updated evidence.",
    ),
    "final_report_ready": (
        NotificationType.PROOFLINE_REPORT_READY,
        "Your Proofline clearance report is ready",
        "The reviewer-approved Verified Trade Clearance report for case {reference} is ready to view.",
    ),
}


def notify_customer(db: Session, trade_case: Any, *, event: str):
    """Dispatch and commit one bounded notification after business data is durable.

    Delivery failure is deliberately non-fatal: it must never reverse a case status,
    correction request, or approved report.
    """
    event_config = EVENTS.get(event)
    customer_user_id = getattr(trade_case, "customer_user_id", None)
    if event_config is None or customer_user_id is None:
        return None
    try:
        customer = db.query(User).filter(User.id == customer_user_id).first()
        if customer is None:
            return None
        notification_type, title, body_template = event_config
        reference = str(
            getattr(trade_case, "case_reference", None) or getattr(trade_case, "id")
        )
        row = dispatch(
            db,
            customer,
            notification_type,
            title=title,
            body=body_template.format(reference=reference),
            link_url=f"/proofline/cases/{trade_case.id}",
            metadata={
                "trade_case_id": str(trade_case.id),
                "case_reference": reference,
                "event": event,
            },
        )
        if row is not None:
            db.commit()
        return row
    except Exception:
        db.rollback()
        logger.warning(
            "Proofline customer notification could not be delivered",
            extra={"trade_case_id": str(getattr(trade_case, "id", "")), "event": event},
            exc_info=True,
        )
        return None


__all__ = ["EVENTS", "notify_customer"]
