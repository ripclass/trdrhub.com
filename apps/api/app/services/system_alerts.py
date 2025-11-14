"""
Service helpers for system/operational alerts surfaced in the admin dashboard.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import ValidationSession, SessionStatus, User
from app.models.admin import SystemAlert, SystemAlertSeverity, SystemAlertStatus


class SystemAlertService:
    """Persisted system alerts used by admin dashboard."""

    FAILURE_LOOKBACK_HOURS = 24

    def __init__(self, db: Session):
        self.db = db

    # ---- CRUD helpers --------------------------------------------------
    def list_alerts(
        self,
        *,
        page: int,
        page_size: int,
        severities: Optional[Iterable[SystemAlertSeverity]] = None,
        status: Optional[SystemAlertStatus] = None,
    ):
        query = self.db.query(SystemAlert)

        if severities:
            query = query.filter(SystemAlert.severity.in_(list(severities)))
        if status:
            query = query.filter(SystemAlert.status == status)

        total = query.count()
        alerts = (
            query.order_by(SystemAlert.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return alerts, total

    def acknowledge(self, alert_id: str, user: User) -> SystemAlert:
        alert = self.db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
        if not alert:
            raise ValueError("Alert not found")
        if alert.status == SystemAlertStatus.RESOLVED:
            return alert
        alert.status = SystemAlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = user.id
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def snooze(self, alert_id: str, minutes: int, user: User) -> SystemAlert:
        alert = self.db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
        if not alert:
            raise ValueError("Alert not found")
        alert.status = SystemAlertStatus.SNOOZED
        alert.snoozed_until = datetime.utcnow() + timedelta(minutes=minutes)
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = user.id
        self.db.commit()
        self.db.refresh(alert)
        return alert

    # ---- Auto generation -----------------------------------------------
    def sync_validation_failures(self) -> None:
        """
        Ensure each failed validation session in the recent window has an alert.
        """
        cutoff = datetime.utcnow() - timedelta(hours=self.FAILURE_LOOKBACK_HOURS)
        failing_sessions = (
            self.db.query(ValidationSession.id, ValidationSession.user_id, ValidationSession.status, ValidationSession.created_at)
            .filter(
                ValidationSession.status == SessionStatus.FAILED.value,
                ValidationSession.created_at >= cutoff,
            )
            .all()
        )

        for session in failing_sessions:
            existing = (
                self.db.query(SystemAlert)
                .filter(
                    SystemAlert.resource_type == "validation_session",
                    SystemAlert.resource_id == str(session.id),
                    SystemAlert.status.in_([SystemAlertStatus.ACTIVE, SystemAlertStatus.ACKNOWLEDGED, SystemAlertStatus.SNOOZED]),
                )
                .first()
            )
            if existing:
                continue

            alert = SystemAlert(
                title="Validation session failed",
                description="An LC validation session ended with failure status.",
                source="validation",
                category="lc-validation",
                severity=SystemAlertSeverity.HIGH if session.status == SessionStatus.ERROR.value else SystemAlertSeverity.MEDIUM,
                status=SystemAlertStatus.ACTIVE,
                resource_type="validation_session",
                resource_id=str(session.id),
                alert_metadata={
                    "session_id": str(session.id),
                    "status": session.status,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                },
                auto_generated=True,
            )
            self.db.add(alert)

        if failing_sessions:
            self.db.commit()

    def resolve_obsolete_alerts(self) -> None:
        """
        Automatically resolve alerts whose underlying resource is now healthy.
        """
        active_alerts_query = self.db.query(SystemAlert).filter(
            SystemAlert.resource_type == "validation_session",
            SystemAlert.status.in_([SystemAlertStatus.ACTIVE, SystemAlertStatus.ACKNOWLEDGED, SystemAlertStatus.SNOOZED]),
        )

        alerts = active_alerts_query.all()
        session_ids = [alert.resource_id for alert in alerts if alert.resource_id]
        if not session_ids:
            return

        healthy_sessions = (
            self.db.query(ValidationSession.id)
            .filter(
                ValidationSession.id.in_(session_ids),
                ValidationSession.status != SessionStatus.FAILED.value,
            )
            .all()
        )
        healthy_session_ids = {str(row.id) for row in healthy_sessions}

        updated = False
        for alert in alerts:
            if alert.resource_id in healthy_session_ids:
                alert.status = SystemAlertStatus.RESOLVED
                alert.resolved_at = datetime.utcnow()
                updated = True

        if updated:
            self.db.commit()

