"""
Scheduled audit monitoring task.

This script can be run as a cron job or scheduled task to continuously
monitor the audit system and send alerts.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from database import SessionLocal
from services.audit_monitoring import AuditMonitoringService, AlertSeverity


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audit_monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AuditMonitoringTask:
    """Scheduled audit monitoring task."""

    def __init__(self):
        self.db = None

    def get_db_session(self):
        """Get database session."""
        if not self.db:
            self.db = SessionLocal()
        return self.db

    def close_db_session(self):
        """Close database session."""
        if self.db:
            self.db.close()
            self.db = None

    async def run_monitoring_checks(self):
        """Run all monitoring checks and handle alerts."""
        try:
            db = self.get_db_session()
            monitoring_service = AuditMonitoringService(db)

            logger.info("Starting audit monitoring checks...")

            # Run comprehensive monitoring
            monitoring_report = monitoring_service.run_all_checks()

            # Log monitoring summary
            logger.info(f"Monitoring completed - Status: {monitoring_report['overall_status']}")
            logger.info(f"Alert counts: {monitoring_report['alert_counts']}")

            # Handle alerts based on severity
            alerts = monitoring_report.get('alerts', [])
            for alert_data in alerts:
                severity = alert_data['severity']
                alert_type = alert_data['alert_type']
                message = alert_data['message']

                if severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
                    logger.critical(f"AUDIT ALERT [{severity.upper()}] {alert_type}: {message}")
                    # In production, send immediate notifications
                    await self.send_critical_alert(alert_data)
                elif severity == AlertSeverity.MEDIUM:
                    logger.warning(f"AUDIT WARNING [{severity.upper()}] {alert_type}: {message}")
                    # Send warning notifications with throttling
                    await self.send_warning_alert(alert_data)
                else:
                    logger.info(f"AUDIT INFO [{severity.upper()}] {alert_type}: {message}")

            # Generate daily summary if needed
            if self.should_send_daily_summary():
                await self.send_daily_summary(monitoring_report)

            return monitoring_report

        except Exception as e:
            logger.error(f"Error in audit monitoring task: {str(e)}")
            await self.send_error_alert(str(e))
            raise

        finally:
            self.close_db_session()

    async def send_critical_alert(self, alert_data: dict):
        """Send critical alert notification."""
        try:
            # Placeholder for critical alert notification
            # In production, integrate with:
            # - PagerDuty for immediate escalation
            # - Slack with @channel mentions
            # - SMS notifications to on-call team
            # - Email to security team

            logger.critical(f"🚨 CRITICAL AUDIT ALERT: {alert_data['message']}")

            # Example integrations:
            # await send_pagerduty_alert(alert_data)
            # await send_slack_critical_alert(alert_data)
            # await send_sms_alert(alert_data)

        except Exception as e:
            logger.error(f"Failed to send critical alert: {str(e)}")

    async def send_warning_alert(self, alert_data: dict):
        """Send warning alert notification with throttling."""
        try:
            # Implement throttling to avoid spam
            alert_type = alert_data['alert_type']

            # Check if we've already sent this type of alert recently
            if not self.should_send_warning(alert_type):
                return

            logger.warning(f"⚠️  AUDIT WARNING: {alert_data['message']}")

            # Example integrations:
            # await send_slack_warning(alert_data)
            # await send_email_warning(alert_data)

            # Record that we sent this alert type
            self.record_sent_warning(alert_type)

        except Exception as e:
            logger.error(f"Failed to send warning alert: {str(e)}")

    async def send_daily_summary(self, monitoring_report: dict):
        """Send daily monitoring summary."""
        try:
            summary = monitoring_report.get('summary', {})
            metrics = summary.get('metrics', {})

            summary_message = f"""
📊 Daily Audit Trail Summary - {datetime.now().strftime('%Y-%m-%d')}

System Status: {monitoring_report['overall_status'].upper()}

Key Metrics (24h):
- Total Actions: {metrics.get('total_logs_24h', 0):,}
- Success Rate: {metrics.get('success_rate_24h', 0):.1f}%
- Active Users: {metrics.get('active_users_24h', 0)}
- File Operations: {metrics.get('file_operations_24h', 0):,}

Alerts Summary:
- Critical: {monitoring_report['alert_counts']['critical']}
- High: {monitoring_report['alert_counts']['high']}
- Medium: {monitoring_report['alert_counts']['medium']}
- Low: {monitoring_report['alert_counts']['low']}

Dashboard: https://your-domain.com/admin/audit/monitoring
            """

            logger.info("Daily audit summary generated")
            print(summary_message)

            # Send summary via configured channels
            # await send_email_summary(summary_message)
            # await send_slack_summary(summary_message)

        except Exception as e:
            logger.error(f"Failed to send daily summary: {str(e)}")

    async def send_error_alert(self, error_message: str):
        """Send alert about monitoring system error."""
        try:
            logger.critical(f"🔴 MONITORING SYSTEM ERROR: {error_message}")

            # Critical: monitoring system itself is failing
            # await send_pagerduty_alert({
            #     'alert_type': 'monitoring_system_error',
            #     'severity': 'critical',
            #     'message': f'Audit monitoring system error: {error_message}'
            # })

        except Exception as e:
            logger.error(f"Failed to send error alert: {str(e)}")

    def should_send_daily_summary(self) -> bool:
        """Check if daily summary should be sent."""
        # Send daily summary at 9 AM
        current_hour = datetime.now().hour
        return current_hour == 9

    def should_send_warning(self, alert_type: str) -> bool:
        """Check if warning alert should be sent (throttling)."""
        # Implement throttling logic
        # For demo, always send warnings
        return True

    def record_sent_warning(self, alert_type: str):
        """Record that we sent a warning of this type."""
        # Implement warning tracking
        # Could use Redis, database, or file-based tracking
        pass


async def main():
    """Main monitoring task entry point."""
    logger.info("Starting audit monitoring task")

    task = AuditMonitoringTask()

    try:
        # Run monitoring checks
        monitoring_report = await task.run_monitoring_checks()

        # Exit with appropriate code
        overall_status = monitoring_report.get('overall_status', 'error')

        if overall_status == 'healthy':
            logger.info("Monitoring completed successfully - system healthy")
            sys.exit(0)
        elif overall_status in ['warning', 'degraded']:
            logger.warning("Monitoring completed - system has warnings")
            sys.exit(1)
        elif overall_status == 'critical':
            logger.critical("Monitoring completed - system critical")
            sys.exit(2)
        else:
            logger.error("Monitoring completed with errors")
            sys.exit(3)

    except Exception as e:
        logger.critical(f"Fatal error in monitoring task: {str(e)}")
        sys.exit(4)


if __name__ == "__main__":
    # Run the monitoring task
    asyncio.run(main())