"""
Alerting system for integration platform.
Monitors critical metrics and sends alerts for anomalies.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import logging

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.integrations import (
    IntegrationSubmission, IntegrationBillingEvent, IntegrationHealthCheck,
    Integration, CompanyIntegration
)
from ..config import settings

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    INTEGRATION_DOWN = "integration_down"
    HIGH_ERROR_RATE = "high_error_rate"
    BILLING_FAILURE = "billing_failure"
    QUOTA_EXCEEDED = "quota_exceeded"
    UNUSUAL_ACTIVITY = "unusual_activity"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    AUTHENTICATION_FAILURE = "authentication_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class Alert:
    """Alert data structure."""

    def __init__(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        description: str,
        metadata: Dict[str, Any] = None,
        integration_id: Optional[str] = None,
        company_id: Optional[str] = None
    ):
        self.alert_type = alert_type
        self.severity = severity
        self.title = title
        self.description = description
        self.metadata = metadata or {}
        self.integration_id = integration_id
        self.company_id = company_id
        self.timestamp = datetime.utcnow()
        self.alert_id = f"{alert_type.value}_{int(self.timestamp.timestamp())}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'alert_id': self.alert_id,
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'metadata': self.metadata,
            'integration_id': self.integration_id,
            'company_id': self.company_id,
            'timestamp': self.timestamp.isoformat()
        }


class IntegrationMonitor:
    """Monitors integration health and performance."""

    def __init__(self, db: Session):
        self.db = db
        self.alert_thresholds = {
            'error_rate_threshold': 0.05,  # 5% error rate
            'response_time_threshold': 30000,  # 30 seconds
            'health_check_failure_threshold': 3,  # 3 consecutive failures
            'billing_failure_threshold': 1,  # Any billing failure is critical
            'quota_warning_threshold': 0.9,  # 90% quota usage
            'unusual_activity_multiplier': 5  # 5x normal activity
        }

    async def check_integration_health(self) -> List[Alert]:
        """Check integration health and generate alerts."""
        alerts = []

        try:
            # Get recent health checks
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)

            # Check for consecutive health check failures
            integrations = self.db.query(Integration).filter(
                Integration.status == 'active'
            ).all()

            for integration in integrations:
                recent_checks = self.db.query(IntegrationHealthCheck).filter(
                    IntegrationHealthCheck.integration_id == integration.id,
                    IntegrationHealthCheck.checked_at >= one_hour_ago
                ).order_by(IntegrationHealthCheck.checked_at.desc()).limit(5).all()

                if len(recent_checks) >= 3:
                    failed_checks = [check for check in recent_checks if not check.is_healthy]

                    if len(failed_checks) >= self.alert_thresholds['health_check_failure_threshold']:
                        alert = Alert(
                            alert_type=AlertType.INTEGRATION_DOWN,
                            severity=AlertSeverity.CRITICAL,
                            title=f"Integration {integration.name} is down",
                            description=f"Integration {integration.name} has failed {len(failed_checks)} consecutive health checks",
                            metadata={
                                'integration_name': integration.name,
                                'integration_type': integration.type.value,
                                'failed_checks': len(failed_checks),
                                'recent_errors': [check.error_message for check in failed_checks if check.error_message]
                            },
                            integration_id=str(integration.id)
                        )
                        alerts.append(alert)

                # Check for performance degradation
                if recent_checks:
                    avg_response_time = sum(
                        check.response_time_ms for check in recent_checks
                        if check.response_time_ms
                    ) / len([check for check in recent_checks if check.response_time_ms])

                    if avg_response_time > self.alert_thresholds['response_time_threshold']:
                        alert = Alert(
                            alert_type=AlertType.PERFORMANCE_DEGRADATION,
                            severity=AlertSeverity.HIGH,
                            title=f"Performance degradation for {integration.name}",
                            description=f"Average response time ({avg_response_time:.0f}ms) exceeds threshold",
                            metadata={
                                'integration_name': integration.name,
                                'avg_response_time_ms': avg_response_time,
                                'threshold_ms': self.alert_thresholds['response_time_threshold']
                            },
                            integration_id=str(integration.id)
                        )
                        alerts.append(alert)

        except Exception as e:
            logger.error(f"Failed to check integration health: {str(e)}")

        return alerts

    async def check_error_rates(self) -> List[Alert]:
        """Check for high error rates."""
        alerts = []

        try:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)

            # Get submissions grouped by integration
            integrations = self.db.query(Integration).filter(
                Integration.status == 'active'
            ).all()

            for integration in integrations:
                total_submissions = self.db.query(IntegrationSubmission).filter(
                    IntegrationSubmission.integration_id == integration.id,
                    IntegrationSubmission.submitted_at >= one_hour_ago
                ).count()

                failed_submissions = self.db.query(IntegrationSubmission).filter(
                    IntegrationSubmission.integration_id == integration.id,
                    IntegrationSubmission.submitted_at >= one_hour_ago,
                    IntegrationSubmission.status_code >= 400
                ).count()

                if total_submissions > 10:  # Only alert if we have meaningful volume
                    error_rate = failed_submissions / total_submissions

                    if error_rate > self.alert_thresholds['error_rate_threshold']:
                        alert = Alert(
                            alert_type=AlertType.HIGH_ERROR_RATE,
                            severity=AlertSeverity.HIGH if error_rate > 0.2 else AlertSeverity.MEDIUM,
                            title=f"High error rate for {integration.name}",
                            description=f"Error rate ({error_rate:.1%}) exceeds threshold in the last hour",
                            metadata={
                                'integration_name': integration.name,
                                'error_rate': error_rate,
                                'total_submissions': total_submissions,
                                'failed_submissions': failed_submissions,
                                'threshold': self.alert_thresholds['error_rate_threshold']
                            },
                            integration_id=str(integration.id)
                        )
                        alerts.append(alert)

        except Exception as e:
            logger.error(f"Failed to check error rates: {str(e)}")

        return alerts

    async def check_billing_health(self) -> List[Alert]:
        """Check for billing system issues."""
        alerts = []

        try:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)

            # Check for billing failures (submissions without billing events)
            submissions_without_billing = self.db.query(IntegrationSubmission).filter(
                IntegrationSubmission.submitted_at >= one_hour_ago,
                IntegrationSubmission.status_code < 400,  # Successful submissions
                IntegrationSubmission.billing_recorded == False
            ).all()

            if submissions_without_billing:
                alert = Alert(
                    alert_type=AlertType.BILLING_FAILURE,
                    severity=AlertSeverity.CRITICAL,
                    title="Billing system failures detected",
                    description=f"{len(submissions_without_billing)} successful submissions missing billing records",
                    metadata={
                        'missing_billing_count': len(submissions_without_billing),
                        'submission_ids': [str(sub.id) for sub in submissions_without_billing[:10]],  # First 10
                        'time_window': '1 hour'
                    }
                )
                alerts.append(alert)

        except Exception as e:
            logger.error(f"Failed to check billing health: {str(e)}")

        return alerts

    async def check_quota_usage(self) -> List[Alert]:
        """Check for quota exhaustion."""
        alerts = []

        try:
            company_integrations = self.db.query(CompanyIntegration).filter(
                CompanyIntegration.monthly_quota.isnot(None),
                CompanyIntegration.is_enabled == True
            ).all()

            for company_integration in company_integrations:
                usage_ratio = company_integration.usage_count / company_integration.monthly_quota

                if usage_ratio >= 1.0:
                    alert = Alert(
                        alert_type=AlertType.QUOTA_EXCEEDED,
                        severity=AlertSeverity.HIGH,
                        title="Monthly quota exceeded",
                        description=f"Company {company_integration.company.name} has exceeded quota for {company_integration.integration.name}",
                        metadata={
                            'company_name': company_integration.company.name,
                            'integration_name': company_integration.integration.name,
                            'usage_count': company_integration.usage_count,
                            'quota_limit': company_integration.monthly_quota,
                            'usage_ratio': usage_ratio
                        },
                        integration_id=str(company_integration.integration_id),
                        company_id=str(company_integration.company_id)
                    )
                    alerts.append(alert)

                elif usage_ratio >= self.alert_thresholds['quota_warning_threshold']:
                    alert = Alert(
                        alert_type=AlertType.QUOTA_EXCEEDED,
                        severity=AlertSeverity.MEDIUM,
                        title="Approaching quota limit",
                        description=f"Company {company_integration.company.name} is at {usage_ratio:.1%} of quota for {company_integration.integration.name}",
                        metadata={
                            'company_name': company_integration.company.name,
                            'integration_name': company_integration.integration.name,
                            'usage_count': company_integration.usage_count,
                            'quota_limit': company_integration.monthly_quota,
                            'usage_ratio': usage_ratio
                        },
                        integration_id=str(company_integration.integration_id),
                        company_id=str(company_integration.company_id)
                    )
                    alerts.append(alert)

        except Exception as e:
            logger.error(f"Failed to check quota usage: {str(e)}")

        return alerts

    async def check_unusual_activity(self) -> List[Alert]:
        """Check for unusual activity patterns."""
        alerts = []

        try:
            now = datetime.utcnow()
            current_hour = now.replace(minute=0, second=0, microsecond=0)
            same_hour_last_week = current_hour - timedelta(weeks=1)

            # Compare current hour activity to same hour last week
            integrations = self.db.query(Integration).filter(
                Integration.status == 'active'
            ).all()

            for integration in integrations:
                # Current hour submissions
                current_submissions = self.db.query(IntegrationSubmission).filter(
                    IntegrationSubmission.integration_id == integration.id,
                    IntegrationSubmission.submitted_at >= current_hour
                ).count()

                # Same hour last week submissions
                last_week_submissions = self.db.query(IntegrationSubmission).filter(
                    IntegrationSubmission.integration_id == integration.id,
                    IntegrationSubmission.submitted_at >= same_hour_last_week,
                    IntegrationSubmission.submitted_at < same_hour_last_week + timedelta(hours=1)
                ).count()

                if (last_week_submissions > 0 and
                    current_submissions > last_week_submissions * self.alert_thresholds['unusual_activity_multiplier']):

                    alert = Alert(
                        alert_type=AlertType.UNUSUAL_ACTIVITY,
                        severity=AlertSeverity.MEDIUM,
                        title=f"Unusual activity spike for {integration.name}",
                        description=f"Current activity ({current_submissions}) is {current_submissions/last_week_submissions:.1f}x higher than same time last week",
                        metadata={
                            'integration_name': integration.name,
                            'current_hour_submissions': current_submissions,
                            'last_week_submissions': last_week_submissions,
                            'multiplier': current_submissions / last_week_submissions if last_week_submissions > 0 else 0
                        },
                        integration_id=str(integration.id)
                    )
                    alerts.append(alert)

        except Exception as e:
            logger.error(f"Failed to check unusual activity: {str(e)}")

        return alerts

    async def run_all_checks(self) -> List[Alert]:
        """Run all monitoring checks and return alerts."""
        all_alerts = []

        try:
            # Run all checks in parallel
            results = await asyncio.gather(
                self.check_integration_health(),
                self.check_error_rates(),
                self.check_billing_health(),
                self.check_quota_usage(),
                self.check_unusual_activity(),
                return_exceptions=True
            )

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Monitoring check failed: {str(result)}")
                else:
                    all_alerts.extend(result)

        except Exception as e:
            logger.error(f"Failed to run monitoring checks: {str(e)}")

        return all_alerts


class AlertManager:
    """Manages alert dispatching and notification."""

    def __init__(self):
        self.notification_channels = {
            'slack': self._send_slack_alert,
            'email': self._send_email_alert,
            'webhook': self._send_webhook_alert,
            'pagerduty': self._send_pagerduty_alert
        }

    async def send_alert(self, alert: Alert) -> None:
        """Send alert through configured channels."""
        try:
            # Determine channels based on severity
            channels = self._get_channels_for_severity(alert.severity)

            # Send to each channel
            tasks = []
            for channel in channels:
                if channel in self.notification_channels:
                    tasks.append(self.notification_channels[channel](alert))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            logger.info(f"Alert sent: {alert.title} (severity: {alert.severity.value})")

        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}")

    def _get_channels_for_severity(self, severity: AlertSeverity) -> List[str]:
        """Get notification channels based on alert severity."""
        if severity == AlertSeverity.CRITICAL:
            return ['slack', 'email', 'pagerduty']
        elif severity == AlertSeverity.HIGH:
            return ['slack', 'email']
        elif severity == AlertSeverity.MEDIUM:
            return ['slack']
        else:
            return []

    async def _send_slack_alert(self, alert: Alert) -> None:
        """Send alert to Slack."""
        if not hasattr(settings, 'SLACK_WEBHOOK_URL') or not settings.SLACK_WEBHOOK_URL:
            return

        try:
            # Format Slack message
            color_map = {
                AlertSeverity.LOW: "#36a64f",
                AlertSeverity.MEDIUM: "#ff9500",
                AlertSeverity.HIGH: "#ff0000",
                AlertSeverity.CRITICAL: "#8B0000"
            }

            payload = {
                "attachments": [
                    {
                        "color": color_map.get(alert.severity, "#808080"),
                        "title": alert.title,
                        "text": alert.description,
                        "fields": [
                            {
                                "title": "Severity",
                                "value": alert.severity.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Type",
                                "value": alert.alert_type.value.replace('_', ' ').title(),
                                "short": True
                            },
                            {
                                "title": "Timestamp",
                                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                                "short": True
                            }
                        ],
                        "footer": "LCopilot Integration Platform",
                        "ts": int(alert.timestamp.timestamp())
                    }
                ]
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.SLACK_WEBHOOK_URL,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()

        except Exception as e:
            logger.error(f"Failed to send Slack alert: {str(e)}")

    async def _send_email_alert(self, alert: Alert) -> None:
        """Send alert via email."""
        # Email implementation would go here
        # This is a placeholder for email notification
        logger.info(f"Email alert would be sent: {alert.title}")

    async def _send_webhook_alert(self, alert: Alert) -> None:
        """Send alert to webhook endpoint."""
        if not hasattr(settings, 'ALERT_WEBHOOK_URL') or not settings.ALERT_WEBHOOK_URL:
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.ALERT_WEBHOOK_URL,
                    json=alert.to_dict(),
                    timeout=10.0
                )
                response.raise_for_status()

        except Exception as e:
            logger.error(f"Failed to send webhook alert: {str(e)}")

    async def _send_pagerduty_alert(self, alert: Alert) -> None:
        """Send alert to PagerDuty."""
        # PagerDuty implementation would go here
        # This is a placeholder for PagerDuty integration
        logger.info(f"PagerDuty alert would be sent: {alert.title}")


class MonitoringScheduler:
    """Schedules and runs monitoring tasks."""

    def __init__(self, db: Session):
        self.db = db
        self.monitor = IntegrationMonitor(db)
        self.alert_manager = AlertManager()
        self.running = False

    async def start_monitoring(self) -> None:
        """Start the monitoring loop."""
        self.running = True
        logger.info("Starting integration monitoring...")

        while self.running:
            try:
                # Run monitoring checks
                alerts = await self.monitor.run_all_checks()

                # Send alerts
                for alert in alerts:
                    await self.alert_manager.send_alert(alert)

                # Wait before next check (5 minutes)
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"Monitoring loop error: {str(e)}")
                await asyncio.sleep(60)  # Shorter wait on error

    def stop_monitoring(self) -> None:
        """Stop the monitoring loop."""
        self.running = False
        logger.info("Stopping integration monitoring...")


# Global instances
alert_manager = AlertManager()


async def run_monitoring_check(db: Session) -> List[Dict[str, Any]]:
    """Run a single monitoring check and return results."""
    monitor = IntegrationMonitor(db)
    alerts = await monitor.run_all_checks()
    return [alert.to_dict() for alert in alerts]