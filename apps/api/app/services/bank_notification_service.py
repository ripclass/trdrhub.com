"""
Bank Notification Service
Simplified notification service for bank LC validation alerts.
"""

import logging
import smtplib
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

from ..models import User, ValidationSession, SessionStatus
from ..config import settings

logger = logging.getLogger(__name__)


class BankNotificationService:
    """Service for sending bank-specific notifications."""

    def __init__(self, db: Session):
        self.db = db

    async def send_job_completion_notification(
        self,
        user: User,
        session: ValidationSession,
        discrepancy_count: int = 0,
        compliance_score: int = 100
    ) -> bool:
        """
        Send notification when a validation job completes.
        
        Args:
            user: User who submitted the validation
            session: Completed validation session
            discrepancy_count: Number of discrepancies found
            compliance_score: Compliance score (0-100)
        
        Returns:
            True if notification sent successfully, False otherwise
        """
        # Check user preferences
        preferences = user.onboarding_data or {}
        notification_prefs = preferences.get("notifications", {})
        
        # Check if job completion notifications are enabled (default: True)
        if not notification_prefs.get("job_completion_enabled", True):
            logger.info(f"Job completion notifications disabled for user {user.id}")
            return False
        
        # Check if email is enabled (default: True)
        if not notification_prefs.get("email_enabled", True):
            logger.info(f"Email notifications disabled for user {user.id}")
            return False
        
        # Extract LC details
        metadata = session.extracted_data or {}
        bank_metadata = metadata.get("bank_metadata", {})
        lc_number = bank_metadata.get("lc_number", "N/A")
        client_name = bank_metadata.get("client_name", "Unknown Client")
        
        # Determine status
        if session.status == SessionStatus.FAILED.value:
            status = "Failed"
            subject = f"LC Validation Failed - {lc_number}"
        elif discrepancy_count > 0:
            status = f"Completed with {discrepancy_count} discrepancy(ies)"
            subject = f"LC Validation Completed - {lc_number} (Discrepancies Found)"
        else:
            status = "Completed - Compliant"
            subject = f"LC Validation Completed - {lc_number}"
        
        # Build email body
        body = self._build_completion_email_body(
            lc_number=lc_number,
            client_name=client_name,
            status=status,
            discrepancy_count=discrepancy_count,
            compliance_score=compliance_score,
            job_id=str(session.id),
            completed_at=session.processing_completed_at or datetime.utcnow()
        )
        
        # Send email
        if user.email:
            return await self._send_email(
                recipient=user.email,
                subject=subject,
                body=body
            )
        
        return False

    async def send_high_discrepancy_alert(
        self,
        user: User,
        session: ValidationSession,
        discrepancy_count: int,
        compliance_score: int,
        threshold: int = 5
    ) -> bool:
        """
        Send alert when high discrepancy count is detected.
        
        Args:
            user: User who submitted the validation
            session: Validation session
            discrepancy_count: Number of discrepancies
            compliance_score: Compliance score
            threshold: Discrepancy threshold (default: 5)
        
        Returns:
            True if notification sent successfully, False otherwise
        """
        # Check user preferences
        preferences = user.onboarding_data or {}
        notification_prefs = preferences.get("notifications", {})
        
        # Check if high discrepancy alerts are enabled (default: True)
        if not notification_prefs.get("high_discrepancy_enabled", True):
            logger.info(f"High discrepancy alerts disabled for user {user.id}")
            return False
        
        # Check if email is enabled (default: True)
        if not notification_prefs.get("email_enabled", True):
            logger.info(f"Email notifications disabled for user {user.id}")
            return False
        
        # Get threshold from preferences (default: 5)
        threshold = notification_prefs.get("high_discrepancy_threshold", 5)
        
        # Extract LC details
        metadata = session.extracted_data or {}
        bank_metadata = metadata.get("bank_metadata", {})
        lc_number = bank_metadata.get("lc_number", "N/A")
        client_name = bank_metadata.get("client_name", "Unknown Client")
        
        subject = f"⚠️ High Discrepancy Alert - LC {lc_number}"
        
        body = self._build_high_discrepancy_email_body(
            lc_number=lc_number,
            client_name=client_name,
            discrepancy_count=discrepancy_count,
            compliance_score=compliance_score,
            threshold=threshold,
            job_id=str(session.id),
            completed_at=session.processing_completed_at or datetime.utcnow()
        )
        
        # Send email
        if user.email:
            return await self._send_email(
                recipient=user.email,
                subject=subject,
                body=body
            )
        
        return False

    def _build_completion_email_body(
        self,
        lc_number: str,
        client_name: str,
        status: str,
        discrepancy_count: int,
        compliance_score: int,
        job_id: str,
        completed_at: datetime
    ) -> str:
        """Build HTML email body for job completion."""
        dashboard_url = f"{settings.FRONTEND_URL}/lcopilot/bank-dashboard?tab=results"
        result_url = f"{settings.FRONTEND_URL}/lcopilot/bank-dashboard?tab=results&job={job_id}"
        
        status_color = "green" if discrepancy_count == 0 else "orange" if discrepancy_count < 5 else "red"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #1e40af; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; }}
                .status {{ display: inline-block; padding: 8px 16px; border-radius: 4px; font-weight: bold; }}
                .status-compliant {{ background-color: #10b981; color: white; }}
                .status-discrepancies {{ background-color: #f59e0b; color: white; }}
                .status-failed {{ background-color: #ef4444; color: white; }}
                .details {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 4px; border-left: 4px solid #3b82f6; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #3b82f6; color: white; text-decoration: none; border-radius: 4px; margin-top: 15px; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>LC Validation Complete</h1>
                </div>
                <div class="content">
                    <p>Your LC validation has been completed.</p>
                    
                    <div class="details">
                        <h3>Validation Details</h3>
                        <p><strong>LC Number:</strong> {lc_number}</p>
                        <p><strong>Client:</strong> {client_name}</p>
                        <p><strong>Status:</strong> <span class="status status-{status_color}">{status}</span></p>
                        <p><strong>Compliance Score:</strong> {compliance_score}%</p>
                        <p><strong>Discrepancies:</strong> {discrepancy_count}</p>
                        <p><strong>Completed At:</strong> {completed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    </div>
                    
                    <a href="{result_url}" class="button">View Results</a>
                    <br>
                    <a href="{dashboard_url}" style="margin-top: 10px; display: inline-block; color: #3b82f6;">Go to Dashboard</a>
                </div>
                <div class="footer">
                    <p>This is an automated notification from LCopilot Bank Validation System.</p>
                    <p>To manage your notification preferences, visit your account settings.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html

    def _build_high_discrepancy_email_body(
        self,
        lc_number: str,
        client_name: str,
        discrepancy_count: int,
        compliance_score: int,
        threshold: int,
        job_id: str,
        completed_at: datetime
    ) -> str:
        """Build HTML email body for high discrepancy alert."""
        dashboard_url = f"{settings.FRONTEND_URL}/lcopilot/bank-dashboard?tab=results"
        result_url = f"{settings.FRONTEND_URL}/lcopilot/bank-dashboard?tab=results&job={job_id}"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #dc2626; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #fef2f2; padding: 20px; border: 1px solid #fecaca; }}
                .alert-box {{ background-color: #fee2e2; border-left: 4px solid #dc2626; padding: 15px; margin: 15px 0; border-radius: 4px; }}
                .details {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 4px; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #dc2626; color: white; text-decoration: none; border-radius: 4px; margin-top: 15px; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ High Discrepancy Alert</h1>
                </div>
                <div class="content">
                    <div class="alert-box">
                        <h2 style="margin-top: 0; color: #dc2626;">Action Required</h2>
                        <p>This LC has {discrepancy_count} discrepancy(ies), which exceeds the threshold of {threshold}.</p>
                    </div>
                    
                    <div class="details">
                        <h3>Validation Details</h3>
                        <p><strong>LC Number:</strong> {lc_number}</p>
                        <p><strong>Client:</strong> {client_name}</p>
                        <p><strong>Compliance Score:</strong> {compliance_score}%</p>
                        <p><strong>Discrepancy Count:</strong> <strong style="color: #dc2626;">{discrepancy_count}</strong></p>
                        <p><strong>Threshold:</strong> {threshold}</p>
                        <p><strong>Completed At:</strong> {completed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    </div>
                    
                    <p><strong>Please review this validation immediately.</strong></p>
                    
                    <a href="{result_url}" class="button">View Results & Details</a>
                    <br>
                    <a href="{dashboard_url}" style="margin-top: 10px; display: inline-block; color: #3b82f6;">Go to Dashboard</a>
                </div>
                <div class="footer">
                    <p>This is an automated alert from LCopilot Bank Validation System.</p>
                    <p>To manage your notification preferences, visit your account settings.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html

    async def _send_email(
        self,
        recipient: str,
        subject: str,
        body: str
    ) -> bool:
        """
        Send email notification.
        
        Uses environment variables for SMTP configuration:
        - SMTP_HOST
        - SMTP_PORT (default: 587)
        - SMTP_USERNAME
        - SMTP_PASSWORD
        - SMTP_FROM_EMAIL
        - SMTP_USE_TLS (default: True)
        """
        try:
            smtp_host = os.getenv("SMTP_HOST")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_username = os.getenv("SMTP_USERNAME")
            smtp_password = os.getenv("SMTP_PASSWORD")
            smtp_from = os.getenv("SMTP_FROM_EMAIL", "noreply@lcopilot.com")
            smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
            
            # If SMTP not configured, log and return False
            if not smtp_host:
                logger.warning("SMTP_HOST not configured, skipping email notification")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = smtp_from
            msg['To'] = recipient
            
            # Add HTML part
            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Add plain text fallback
            text_part = MIMEText(
                self._html_to_text(body),
                'plain',
                'utf-8'
            )
            msg.attach(text_part)
            
            # Send via SMTP
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if smtp_use_tls:
                    server.starttls()
                if smtp_username and smtp_password:
                    server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent successfully to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification to {recipient}: {str(e)}", exc_info=True)
            return False

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (simple implementation)."""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        # Decode HTML entities
        import html as html_lib
        text = html_lib.unescape(text)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

