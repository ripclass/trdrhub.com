"""
Price Verification Alert Service

Sends email notifications for price verification events:
- TBML high-risk alerts
- Daily/weekly digest summaries
- Threshold breach notifications
"""

import logging
import smtplib
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.models.commodity_prices import PriceVerification

logger = logging.getLogger(__name__)


class PriceAlertService:
    """Service for sending price verification alerts."""

    def __init__(self, db: Session):
        self.db = db
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("ALERT_FROM_EMAIL", "alerts@trdrhub.com")
        self.alert_enabled = os.getenv("PRICE_ALERTS_ENABLED", "true").lower() == "true"

    async def send_tbml_alert(
        self,
        verification: PriceVerification,
        recipient_email: str,
        company_name: Optional[str] = None,
    ) -> bool:
        """
        Send immediate alert for TBML-flagged transactions.
        
        Args:
            verification: The flagged verification
            recipient_email: Email to send alert to
            company_name: Optional company name for personalization
        
        Returns:
            True if sent successfully
        """
        if not self.alert_enabled or not recipient_email:
            return False

        subject = f"⚠️ TBML Alert: High-Risk Price Variance Detected - {verification.commodity_name}"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #dc2626; color: white; padding: 20px; text-align: center;">
                <h2>🚨 TBML Risk Alert</h2>
                <p>A high-risk price variance has been detected</p>
            </div>
            
            <div style="padding: 20px; background: #fff;">
                <h3>Transaction Details</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px; color: #666;">Commodity</td>
                        <td style="padding: 10px; font-weight: bold;">{verification.commodity_name}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px; color: #666;">Document Price</td>
                        <td style="padding: 10px;">${verification.document_price:,.2f}/{verification.document_unit}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px; color: #666;">Market Price</td>
                        <td style="padding: 10px;">${verification.market_price:,.2f}/{verification.document_unit}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px; color: #666;">Variance</td>
                        <td style="padding: 10px; color: #dc2626; font-weight: bold;">
                            {verification.variance_percent:+.1f}%
                        </td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px; color: #666;">Risk Level</td>
                        <td style="padding: 10px;">
                            <span style="background: #dc2626; color: white; padding: 4px 8px; border-radius: 4px;">
                                {(verification.risk_level or 'HIGH').upper()}
                            </span>
                        </td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 10px; color: #666;">Verification ID</td>
                        <td style="padding: 10px; font-family: monospace; font-size: 12px;">
                            {verification.id}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; color: #666;">Timestamp</td>
                        <td style="padding: 10px;">
                            {verification.created_at.strftime('%Y-%m-%d %H:%M UTC') if verification.created_at else 'N/A'}
                        </td>
                    </tr>
                </table>
                
                <div style="margin-top: 20px; padding: 15px; background: #fef2f2; border-radius: 8px;">
                    <h4 style="color: #dc2626; margin: 0 0 10px 0;">⚠️ Recommended Actions</h4>
                    <ul style="margin: 0; padding-left: 20px; color: #666;">
                        <li>Review transaction documentation</li>
                        <li>Verify supplier/pricing justification</li>
                        <li>Consider filing SAR/STR if warranted</li>
                        <li>Escalate to compliance team</li>
                    </ul>
                </div>
                
                <div style="margin-top: 20px; text-align: center;">
                    <a href="https://trdrhub.com/price-verify/dashboard/history" 
                       style="background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                        View Full Details
                    </a>
                </div>
            </div>
            
            <div style="padding: 15px; background: #f9fafb; text-align: center; font-size: 12px; color: #666;">
                <p>This alert was sent by TRDR Hub Price Verification System</p>
                <p>Company: {company_name or 'N/A'}</p>
            </div>
        </body>
        </html>
        """

        return await self._send_email(recipient_email, subject, body)

    async def send_daily_digest(
        self,
        recipient_email: str,
        company_name: Optional[str] = None,
    ) -> bool:
        """
        Send daily summary digest of price verifications.
        """
        if not self.alert_enabled or not recipient_email:
            return False

        # Get stats for last 24 hours
        since = datetime.now(timezone.utc) - timedelta(days=1)
        
        verifications = self.db.query(PriceVerification).filter(
            PriceVerification.created_at >= since
        ).all()
        
        if not verifications:
            return False  # Don't send if no activity
        
        total = len(verifications)
        passed = sum(1 for v in verifications if v.verdict == "pass")
        warnings = sum(1 for v in verifications if v.verdict == "warning")
        failed = sum(1 for v in verifications if v.verdict == "fail")
        tbml_count = sum(1 for v in verifications if v.risk_level in ["high", "critical"])
        
        subject = f"📊 Daily Price Verification Digest - {datetime.now().strftime('%B %d, %Y')}"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #3b82f6; color: white; padding: 20px; text-align: center;">
                <h2>📊 Daily Verification Summary</h2>
                <p>{datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            
            <div style="padding: 20px; background: #fff;">
                <h3>Today's Activity</h3>
                
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 120px; background: #f3f4f6; padding: 15px; border-radius: 8px; text-align: center;">
                        <p style="font-size: 24px; font-weight: bold; margin: 0; color: #3b82f6;">{total}</p>
                        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">Total</p>
                    </div>
                    <div style="flex: 1; min-width: 120px; background: #dcfce7; padding: 15px; border-radius: 8px; text-align: center;">
                        <p style="font-size: 24px; font-weight: bold; margin: 0; color: #22c55e;">{passed}</p>
                        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">Passed</p>
                    </div>
                    <div style="flex: 1; min-width: 120px; background: #fef3c7; padding: 15px; border-radius: 8px; text-align: center;">
                        <p style="font-size: 24px; font-weight: bold; margin: 0; color: #f59e0b;">{warnings}</p>
                        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">Warnings</p>
                    </div>
                    <div style="flex: 1; min-width: 120px; background: #fee2e2; padding: 15px; border-radius: 8px; text-align: center;">
                        <p style="font-size: 24px; font-weight: bold; margin: 0; color: #ef4444;">{failed}</p>
                        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">Failed</p>
                    </div>
                </div>
                
                {"<div style='margin-top: 15px; padding: 15px; background: #fef2f2; border-radius: 8px; border-left: 4px solid #dc2626;'><strong>⚠️ " + str(tbml_count) + " TBML high-risk transactions detected</strong></div>" if tbml_count > 0 else ""}
                
                <div style="margin-top: 20px; text-align: center;">
                    <a href="https://trdrhub.com/price-verify/dashboard/analytics" 
                       style="background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
                        View Full Analytics
                    </a>
                </div>
            </div>
            
            <div style="padding: 15px; background: #f9fafb; text-align: center; font-size: 12px; color: #666;">
                <p>TRDR Hub Price Verification Daily Digest</p>
                <p>Company: {company_name or 'N/A'}</p>
                <p><a href="https://trdrhub.com/price-verify/dashboard/settings">Manage notification preferences</a></p>
            </div>
        </body>
        </html>
        """

        return await self._send_email(recipient_email, subject, body)

    async def _send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        is_html: bool = True
    ) -> bool:
        """
        Send an email using SMTP.
        
        Args:
            recipient: Email address to send to
            subject: Email subject
            body: Email body (HTML or plain text)
            is_html: Whether body is HTML
        
        Returns:
            True if sent successfully
        """
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP not configured, skipping email")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = recipient

            mime_type = "html" if is_html else "plain"
            msg.attach(MIMEText(body, mime_type))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, recipient, msg.as_string())

            logger.info(f"Email sent successfully to {recipient}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")
            return False


def get_price_alert_service(db: Session) -> PriceAlertService:
    """Factory function to get alert service instance."""
    return PriceAlertService(db)

