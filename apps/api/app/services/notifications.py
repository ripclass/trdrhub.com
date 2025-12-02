"""
Notification Service

Handles sending notifications via email and SMS for tracking alerts
and other system notifications.
"""

import os
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class NotificationResult(BaseModel):
    success: bool
    channel: str
    recipient: str
    message_id: Optional[str] = None
    error: Optional[str] = None


# ============== Email Service (Resend) ==============

class EmailService:
    """Send emails via Resend API."""
    
    def __init__(self):
        self.api_key = os.getenv("RESEND_API_KEY")
        self.from_email = os.getenv("EMAIL_FROM", "alerts@trdrhub.com")
        self.enabled = bool(self.api_key)
    
    async def send(
        self,
        to: str,
        subject: str,
        html: str,
        text: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> NotificationResult:
        """Send an email via Resend."""
        if not self.enabled:
            logger.warning("Email service not configured (missing RESEND_API_KEY)")
            return NotificationResult(
                success=False,
                channel="email",
                recipient=to,
                error="Email service not configured"
            )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": self.from_email,
                        "to": [to],
                        "subject": subject,
                        "html": html,
                        "text": text,
                        "reply_to": reply_to,
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Email sent to {to}: {data.get('id')}")
                    return NotificationResult(
                        success=True,
                        channel="email",
                        recipient=to,
                        message_id=data.get("id")
                    )
                else:
                    error = response.text
                    logger.error(f"Email send failed: {error}")
                    return NotificationResult(
                        success=False,
                        channel="email",
                        recipient=to,
                        error=error
                    )
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return NotificationResult(
                success=False,
                channel="email",
                recipient=to,
                error=str(e)
            )


# ============== SMS Service (Twilio) ==============

class SMSService:
    """Send SMS via Twilio."""
    
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER")
        self.enabled = bool(self.account_sid and self.auth_token and self.from_number)
    
    async def send(self, to: str, message: str) -> NotificationResult:
        """Send an SMS via Twilio."""
        if not self.enabled:
            logger.warning("SMS service not configured (missing Twilio credentials)")
            return NotificationResult(
                success=False,
                channel="sms",
                recipient=to,
                error="SMS service not configured"
            )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json",
                    auth=(self.account_sid, self.auth_token),
                    data={
                        "From": self.from_number,
                        "To": to,
                        "Body": message,
                    }
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    logger.info(f"SMS sent to {to}: {data.get('sid')}")
                    return NotificationResult(
                        success=True,
                        channel="sms",
                        recipient=to,
                        message_id=data.get("sid")
                    )
                else:
                    error = response.text
                    logger.error(f"SMS send failed: {error}")
                    return NotificationResult(
                        success=False,
                        channel="sms",
                        recipient=to,
                        error=error
                    )
        except Exception as e:
            logger.error(f"SMS send error: {e}")
            return NotificationResult(
                success=False,
                channel="sms",
                recipient=to,
                error=str(e)
            )


# ============== Tracking Alert Templates ==============

def get_container_arrival_email(
    container_number: str,
    vessel: str,
    port: str,
    eta: str,
    user_name: str = "User",
) -> tuple[str, str, str]:
    """Generate email content for container arrival alert."""
    
    subject = f"🚢 Container {container_number} - Arrival Alert"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f172a; color: #e2e8f0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #3b82f6, #10b981); padding: 20px; border-radius: 8px 8px 0 0; }}
            .content {{ background: #1e293b; padding: 20px; border-radius: 0 0 8px 8px; }}
            .highlight {{ background: #334155; padding: 15px; border-radius: 4px; margin: 10px 0; }}
            .btn {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; 
                    text-decoration: none; border-radius: 6px; margin-top: 15px; }}
            .footer {{ text-align: center; color: #64748b; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; color: white;">📦 Container Arrival Alert</h1>
            </div>
            <div class="content">
                <p>Hi {user_name},</p>
                <p>Your tracked container is approaching its destination:</p>
                
                <div class="highlight">
                    <p style="margin: 5px 0;"><strong>Container:</strong> {container_number}</p>
                    <p style="margin: 5px 0;"><strong>Vessel:</strong> {vessel}</p>
                    <p style="margin: 5px 0;"><strong>Arriving at:</strong> {port}</p>
                    <p style="margin: 5px 0;"><strong>ETA:</strong> {eta}</p>
                </div>
                
                <p>Plan ahead for customs clearance and pickup.</p>
                
                <a href="https://trdrhub.com/tracking/container/{container_number}" class="btn">
                    View Details →
                </a>
            </div>
            <div class="footer">
                <p>TRDR Hub | Container & Vessel Tracking</p>
                <p><a href="https://trdrhub.com/hub/settings" style="color: #3b82f6;">Manage Alerts</a></p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
Container Arrival Alert

Hi {user_name},

Your tracked container is approaching its destination:

Container: {container_number}
Vessel: {vessel}
Arriving at: {port}
ETA: {eta}

Plan ahead for customs clearance and pickup.

View details: https://trdrhub.com/tracking/container/{container_number}

---
TRDR Hub | Container & Vessel Tracking
    """
    
    return subject, html, text


def get_delay_alert_email(
    container_number: str,
    original_eta: str,
    new_eta: str,
    delay_hours: int,
    reason: str = "Weather conditions",
    user_name: str = "User",
) -> tuple[str, str, str]:
    """Generate email content for delay alert."""
    
    subject = f"⚠️ Container {container_number} - Delay Alert ({delay_hours}h)"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f172a; color: #e2e8f0; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #f59e0b; padding: 20px; border-radius: 8px 8px 0 0; }}
            .content {{ background: #1e293b; padding: 20px; border-radius: 0 0 8px 8px; }}
            .highlight {{ background: #334155; padding: 15px; border-radius: 4px; margin: 10px 0; }}
            .warning {{ border-left: 4px solid #f59e0b; padding-left: 12px; }}
            .btn {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; 
                    text-decoration: none; border-radius: 6px; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; color: #1e293b;">⚠️ Shipment Delay Alert</h1>
            </div>
            <div class="content">
                <p>Hi {user_name},</p>
                <p>Your shipment has been delayed:</p>
                
                <div class="highlight warning">
                    <p style="margin: 5px 0;"><strong>Container:</strong> {container_number}</p>
                    <p style="margin: 5px 0;"><strong>Original ETA:</strong> {original_eta}</p>
                    <p style="margin: 5px 0;"><strong>New ETA:</strong> {new_eta}</p>
                    <p style="margin: 5px 0;"><strong>Delay:</strong> {delay_hours} hours</p>
                    <p style="margin: 5px 0;"><strong>Reason:</strong> {reason}</p>
                </div>
                
                <p>Please adjust your arrangements accordingly.</p>
                
                <a href="https://trdrhub.com/tracking/container/{container_number}" class="btn">
                    View Details →
                </a>
            </div>
        </div>
    </body>
    </html>
    """
    
    text = f"""
Shipment Delay Alert

Hi {user_name},

Your shipment has been delayed:

Container: {container_number}
Original ETA: {original_eta}
New ETA: {new_eta}
Delay: {delay_hours} hours
Reason: {reason}

View details: https://trdrhub.com/tracking/container/{container_number}
    """
    
    return subject, html, text


def get_container_arrival_sms(
    container_number: str,
    port: str,
    eta: str,
) -> str:
    """Generate SMS content for container arrival."""
    return f"TRDR Hub: Container {container_number} arriving {port} on {eta}. Track: trdrhub.com/t/{container_number[:8]}"


def get_delay_sms(
    container_number: str,
    delay_hours: int,
    new_eta: str,
) -> str:
    """Generate SMS content for delay alert."""
    return f"TRDR Hub: Container {container_number} delayed {delay_hours}h. New ETA: {new_eta}"


# ============== Unified Notification Service ==============

class NotificationService:
    """Unified service for sending notifications across channels."""
    
    def __init__(self):
        self.email = EmailService()
        self.sms = SMSService()
    
    async def send_container_arrival_alert(
        self,
        container_number: str,
        vessel: str,
        port: str,
        eta: str,
        user_email: Optional[str] = None,
        user_phone: Optional[str] = None,
        user_name: str = "User",
    ) -> List[NotificationResult]:
        """Send container arrival notifications via all configured channels."""
        results = []
        
        if user_email:
            subject, html, text = get_container_arrival_email(
                container_number, vessel, port, eta, user_name
            )
            result = await self.email.send(user_email, subject, html, text)
            results.append(result)
        
        if user_phone:
            sms_text = get_container_arrival_sms(container_number, port, eta)
            result = await self.sms.send(user_phone, sms_text)
            results.append(result)
        
        return results
    
    async def send_delay_alert(
        self,
        container_number: str,
        original_eta: str,
        new_eta: str,
        delay_hours: int,
        reason: str,
        user_email: Optional[str] = None,
        user_phone: Optional[str] = None,
        user_name: str = "User",
    ) -> List[NotificationResult]:
        """Send delay notifications via all configured channels."""
        results = []
        
        if user_email:
            subject, html, text = get_delay_alert_email(
                container_number, original_eta, new_eta, delay_hours, reason, user_name
            )
            result = await self.email.send(user_email, subject, html, text)
            results.append(result)
        
        if user_phone:
            sms_text = get_delay_sms(container_number, delay_hours, new_eta)
            result = await self.sms.send(user_phone, sms_text)
            results.append(result)
        
        return results
    
    def status(self) -> Dict[str, bool]:
        """Check which notification channels are configured."""
        return {
            "email": self.email.enabled,
            "sms": self.sms.enabled,
        }


# Singleton instance
notification_service = NotificationService()

