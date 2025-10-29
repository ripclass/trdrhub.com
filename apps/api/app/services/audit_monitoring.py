"""
Audit monitoring and alerting service.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..models.audit_log import AuditLog, AuditAction, AuditResult
from ..services.audit_service import AuditService


logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditAlert:
    """Audit alert data structure."""

    def __init__(
        self,
        alert_type: str,
        severity: AlertSeverity,
        message: str,
        details: Dict[str, Any],
        timestamp: datetime = None
    ):
        self.alert_type = alert_type
        self.severity = severity
        self.message = message
        self.details = details
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class AuditMonitoringService:
    """Service for monitoring audit logs and generating alerts."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    # Failure Rate Monitoring
    def check_failure_rate(self, hours: int = 1, threshold: float = 0.10) -> Optional[AuditAlert]:
        """
        Check if failure rate exceeds threshold.

        Args:
            hours: Time window to check
            threshold: Failure rate threshold (0.10 = 10%)

        Returns:
            Alert if threshold exceeded, None otherwise
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        # Get total actions and failures in time window
        total_actions = self.db.query(func.count(AuditLog.id))\
            .filter(AuditLog.timestamp >= since)\
            .scalar() or 0

        if total_actions == 0:
            return None

        failed_actions = self.db.query(func.count(AuditLog.id))\
            .filter(AuditLog.timestamp >= since)\
            .filter(AuditLog.result.in_([AuditResult.FAILURE, AuditResult.ERROR]))\
            .scalar() or 0

        failure_rate = failed_actions / total_actions

        if failure_rate > threshold:
            return AuditAlert(
                alert_type="high_failure_rate",
                severity=AlertSeverity.HIGH if failure_rate > 0.25 else AlertSeverity.MEDIUM,
                message=f"High failure rate detected: {failure_rate:.1%} in last {hours}h",
                details={
                    "failure_rate": failure_rate,
                    "total_actions": total_actions,
                    "failed_actions": failed_actions,
                    "threshold": threshold,
                    "time_window_hours": hours
                }
            )

        return None

    def check_suspicious_activity(self, hours: int = 24) -> List[AuditAlert]:
        """
        Check for suspicious activity patterns.

        Args:
            hours: Time window to check

        Returns:
            List of alerts for suspicious activities
        """
        alerts = []
        since = datetime.utcnow() - timedelta(hours=hours)

        # Check for unusual IP activity
        ip_activity = self.db.query(
            AuditLog.ip_address,
            func.count(AuditLog.id).label('action_count'),
            func.count(
                func.case([(AuditLog.result == AuditResult.FAILURE, 1)])
            ).label('failure_count')
        ).filter(
            AuditLog.timestamp >= since,
            AuditLog.ip_address.isnot(None)
        ).group_by(AuditLog.ip_address).all()

        for ip_data in ip_activity:
            ip_address, action_count, failure_count = ip_data

            # Alert on high activity from single IP
            if action_count > 1000:  # Configurable threshold
                alerts.append(AuditAlert(
                    alert_type="high_ip_activity",
                    severity=AlertSeverity.MEDIUM,
                    message=f"High activity from IP {ip_address}: {action_count} actions",
                    details={
                        "ip_address": ip_address,
                        "action_count": action_count,
                        "failure_count": failure_count,
                        "time_window_hours": hours
                    }
                ))

            # Alert on high failure rate from single IP
            if action_count > 10 and failure_count / action_count > 0.5:
                alerts.append(AuditAlert(
                    alert_type="suspicious_ip_failures",
                    severity=AlertSeverity.HIGH,
                    message=f"High failure rate from IP {ip_address}: {failure_count}/{action_count}",
                    details={
                        "ip_address": ip_address,
                        "failure_rate": failure_count / action_count,
                        "action_count": action_count,
                        "failure_count": failure_count
                    }
                ))

        # Check for unusual user activity
        user_activity = self.db.query(
            AuditLog.user_email,
            func.count(AuditLog.id).label('action_count')
        ).filter(
            AuditLog.timestamp >= since,
            AuditLog.user_email.isnot(None)
        ).group_by(AuditLog.user_email).having(
            func.count(AuditLog.id) > 500  # Configurable threshold
        ).all()

        for user_email, action_count in user_activity:
            alerts.append(AuditAlert(
                alert_type="high_user_activity",
                severity=AlertSeverity.MEDIUM,
                message=f"High activity from user {user_email}: {action_count} actions",
                details={
                    "user_email": user_email,
                    "action_count": action_count,
                    "time_window_hours": hours
                }
            ))

        return alerts

    def check_file_integrity_issues(self, days: int = 7) -> List[AuditAlert]:
        """
        Check for potential file integrity issues.

        Args:
            days: Time window to check

        Returns:
            List of alerts for integrity issues
        """
        alerts = []
        since = datetime.utcnow() - timedelta(days=days)

        # Check for duplicate file hashes (potential replay attacks)
        duplicate_hashes = self.db.query(
            AuditLog.file_hash,
            func.count(AuditLog.id).label('hash_count')
        ).filter(
            AuditLog.timestamp >= since,
            AuditLog.file_hash.isnot(None),
            AuditLog.action == AuditAction.UPLOAD
        ).group_by(AuditLog.file_hash).having(
            func.count(AuditLog.id) > 5  # Configurable threshold
        ).all()

        for file_hash, hash_count in duplicate_hashes:
            # Get details of duplicate uploads
            duplicate_uploads = self.db.query(AuditLog).filter(
                AuditLog.file_hash == file_hash,
                AuditLog.timestamp >= since
            ).all()

            user_emails = set(log.user_email for log in duplicate_uploads if log.user_email)
            ip_addresses = set(log.ip_address for log in duplicate_uploads if log.ip_address)

            alerts.append(AuditAlert(
                alert_type="duplicate_file_hash",
                severity=AlertSeverity.MEDIUM,
                message=f"File hash {file_hash[:16]}... uploaded {hash_count} times",
                details={
                    "file_hash": file_hash,
                    "upload_count": hash_count,
                    "unique_users": len(user_emails),
                    "unique_ips": len(ip_addresses),
                    "time_window_days": days
                }
            ))

        return alerts

    def check_compliance_gaps(self, days: int = 1) -> List[AuditAlert]:
        """
        Check for compliance and audit trail gaps.

        Args:
            days: Time window to check

        Returns:
            List of compliance alerts
        """
        alerts = []
        since = datetime.utcnow() - timedelta(days=days)

        # Check for missing correlation IDs
        missing_correlation = self.db.query(func.count(AuditLog.id))\
            .filter(
                AuditLog.timestamp >= since,
                AuditLog.correlation_id.is_(None)
            ).scalar() or 0

        if missing_correlation > 0:
            alerts.append(AuditAlert(
                alert_type="missing_correlation_ids",
                severity=AlertSeverity.LOW,
                message=f"{missing_correlation} audit logs missing correlation IDs",
                details={
                    "missing_count": missing_correlation,
                    "time_window_days": days
                }
            ))

        # Check for long gaps in audit trail
        latest_log = self.db.query(AuditLog.timestamp)\
            .order_by(desc(AuditLog.timestamp))\
            .first()

        if latest_log:
            gap_hours = (datetime.utcnow() - latest_log.timestamp).total_seconds() / 3600
            if gap_hours > 6:  # Alert if no activity for 6+ hours during business hours
                alerts.append(AuditAlert(
                    alert_type="audit_trail_gap",
                    severity=AlertSeverity.MEDIUM,
                    message=f"No audit activity for {gap_hours:.1f} hours",
                    details={
                        "gap_hours": gap_hours,
                        "last_activity": latest_log.timestamp.isoformat()
                    }
                ))

        return alerts

    def check_retention_compliance(self) -> List[AuditAlert]:
        """
        Check audit log retention policy compliance.

        Returns:
            List of retention compliance alerts
        """
        alerts = []

        # Check for logs approaching retention deadline
        approaching_deadline = datetime.utcnow() + timedelta(days=30)  # 30-day warning

        logs_near_expiry = self.db.query(func.count(AuditLog.id))\
            .filter(
                AuditLog.retention_until <= approaching_deadline,
                AuditLog.archived != "archived"
            ).scalar() or 0

        if logs_near_expiry > 0:
            alerts.append(AuditAlert(
                alert_type="retention_deadline_approaching",
                severity=AlertSeverity.MEDIUM,
                message=f"{logs_near_expiry} audit logs approaching retention deadline",
                details={
                    "logs_count": logs_near_expiry,
                    "deadline_days": 30
                }
            ))

        # Check for logs past retention deadline
        expired_logs = self.db.query(func.count(AuditLog.id))\
            .filter(
                AuditLog.retention_until <= datetime.utcnow(),
                AuditLog.archived != "archived"
            ).scalar() or 0

        if expired_logs > 0:
            alerts.append(AuditAlert(
                alert_type="retention_deadline_exceeded",
                severity=AlertSeverity.HIGH,
                message=f"{expired_logs} audit logs have exceeded retention deadline",
                details={
                    "expired_logs_count": expired_logs
                }
            ))

        return alerts

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive monitoring summary.

        Returns:
            Dictionary with monitoring metrics and status
        """
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_hour = now - timedelta(hours=1)

        # Basic metrics
        total_logs_24h = self.db.query(func.count(AuditLog.id))\
            .filter(AuditLog.timestamp >= last_24h)\
            .scalar() or 0

        successful_logs_24h = self.db.query(func.count(AuditLog.id))\
            .filter(
                AuditLog.timestamp >= last_24h,
                AuditLog.result == AuditResult.SUCCESS
            ).scalar() or 0

        failed_logs_1h = self.db.query(func.count(AuditLog.id))\
            .filter(
                AuditLog.timestamp >= last_hour,
                AuditLog.result.in_([AuditResult.FAILURE, AuditResult.ERROR])
            ).scalar() or 0

        # Active users
        active_users_24h = self.db.query(func.count(func.distinct(AuditLog.user_email)))\
            .filter(
                AuditLog.timestamp >= last_24h,
                AuditLog.user_email.isnot(None)
            ).scalar() or 0

        # File operations
        file_operations_24h = self.db.query(func.count(AuditLog.id))\
            .filter(
                AuditLog.timestamp >= last_24h,
                AuditLog.file_hash.isnot(None)
            ).scalar() or 0

        return {
            "monitoring_timestamp": now.isoformat(),
            "metrics": {
                "total_logs_24h": total_logs_24h,
                "success_rate_24h": (successful_logs_24h / max(total_logs_24h, 1)) * 100,
                "failed_logs_1h": failed_logs_1h,
                "active_users_24h": active_users_24h,
                "file_operations_24h": file_operations_24h
            },
            "system_status": "healthy" if failed_logs_1h < 10 else "degraded"
        }

    def run_all_checks(self) -> Dict[str, Any]:
        """
        Run all monitoring checks and return comprehensive report.

        Returns:
            Dictionary with all alerts and monitoring summary
        """
        all_alerts = []

        try:
            # Run all monitoring checks
            failure_alert = self.check_failure_rate()
            if failure_alert:
                all_alerts.append(failure_alert)

            all_alerts.extend(self.check_suspicious_activity())
            all_alerts.extend(self.check_file_integrity_issues())
            all_alerts.extend(self.check_compliance_gaps())
            all_alerts.extend(self.check_retention_compliance())

            # Get monitoring summary
            summary = self.get_monitoring_summary()

            # Determine overall health
            critical_alerts = [a for a in all_alerts if a.severity == AlertSeverity.CRITICAL]
            high_alerts = [a for a in all_alerts if a.severity == AlertSeverity.HIGH]

            overall_status = "healthy"
            if critical_alerts:
                overall_status = "critical"
            elif high_alerts:
                overall_status = "warning"
            elif len(all_alerts) > 5:
                overall_status = "degraded"

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": overall_status,
                "summary": summary,
                "alerts": [alert.to_dict() for alert in all_alerts],
                "alert_counts": {
                    "critical": len([a for a in all_alerts if a.severity == AlertSeverity.CRITICAL]),
                    "high": len([a for a in all_alerts if a.severity == AlertSeverity.HIGH]),
                    "medium": len([a for a in all_alerts if a.severity == AlertSeverity.MEDIUM]),
                    "low": len([a for a in all_alerts if a.severity == AlertSeverity.LOW])
                }
            }

        except Exception as e:
            logger.error(f"Error running audit monitoring checks: {str(e)}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": "error",
                "error": str(e),
                "alerts": [],
                "alert_counts": {"critical": 1, "high": 0, "medium": 0, "low": 0}
            }

    def send_alert_notification(self, alert: AuditAlert) -> bool:
        """
        Send alert notification (placeholder for integration with notification systems).

        Args:
            alert: Alert to send notification for

        Returns:
            True if notification sent successfully
        """
        try:
            # Placeholder for notification system integration
            # In production, this would integrate with:
            # - Email systems (SMTP, SES)
            # - Slack/Teams webhooks
            # - PagerDuty/Opsgenie
            # - SMS services
            # - CloudWatch alarms

            logger.warning(
                f"AUDIT ALERT: {alert.severity.upper()} - {alert.message}",
                extra={
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "details": alert.details
                }
            )

            # Example integration patterns:
            # await send_slack_webhook(alert)
            # await send_email_alert(alert)
            # await create_pagerduty_incident(alert)

            return True

        except Exception as e:
            logger.error(f"Failed to send alert notification: {str(e)}")
            return False