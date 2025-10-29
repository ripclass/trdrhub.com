"""
Notification Service
Multi-channel notification system with providers, subscriptions, and digests
"""

import asyncio
import json
import logging
import smtplib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
import hashlib
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from app.core.events import BaseEvent, EventType, EventSeverity, EventFilter
from app.models.notifications import (
    NotificationChannel, NotificationTemplate, NotificationSubscription,
    NotificationDelivery, NotificationDigest, ChannelType, DeliveryStatus
)
from app.core.database import get_db
from app.core.security import get_current_user

logger = logging.getLogger(__name__)


class NotificationProvider:
    """Base notification provider"""

    def __init__(self, channel: NotificationChannel):
        self.channel = channel
        self.config = json.loads(channel.config_encrypted)

    async def send(self, recipient: str, subject: str, body: str, metadata: Dict[str, Any] = None) -> bool:
        """Send notification. Return True if successful."""
        raise NotImplementedError

    async def test_connection(self) -> Dict[str, Any]:
        """Test provider connection. Return status and details."""
        raise NotImplementedError


class EmailProvider(NotificationProvider):
    """SMTP email provider"""

    async def send(self, recipient: str, subject: str, body: str, metadata: Dict[str, Any] = None) -> bool:
        try:
            smtp_host = self.config.get("smtp_host")
            smtp_port = self.config.get("smtp_port", 587)
            username = self.config.get("username")
            password = self.config.get("password")
            from_email = self.config.get("from_email")
            use_tls = self.config.get("use_tls", True)

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = recipient

            # Add HTML and plain text parts
            text_part = MIMEText(body, 'plain', 'utf-8')
            html_part = MIMEText(f"<pre>{body}</pre>", 'html', 'utf-8')

            msg.attach(text_part)
            msg.attach(html_part)

            # Send via SMTP
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if use_tls:
                    server.starttls()
                if username and password:
                    server.login(username, password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Email send failed to {recipient}: {str(e)}")
            return False

    async def test_connection(self) -> Dict[str, Any]:
        try:
            smtp_host = self.config.get("smtp_host")
            smtp_port = self.config.get("smtp_port", 587)
            username = self.config.get("username")
            password = self.config.get("password")

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if self.config.get("use_tls", True):
                    server.starttls()
                if username and password:
                    server.login(username, password)

            return {"status": "success", "message": "SMTP connection successful"}

        except Exception as e:
            return {"status": "error", "message": str(e)}


class SlackProvider(NotificationProvider):
    """Slack webhook provider"""

    async def send(self, recipient: str, subject: str, body: str, metadata: Dict[str, Any] = None) -> bool:
        try:
            webhook_url = self.config.get("webhook_url")

            # Format for Slack
            slack_message = {
                "text": subject,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": subject
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": body
                        }
                    }
                ]
            }

            # Add metadata fields if provided
            if metadata:
                fields = []
                for key, value in metadata.items():
                    fields.append({
                        "type": "mrkdwn",
                        "text": f"*{key}:* {value}"
                    })

                if fields:
                    slack_message["blocks"].append({
                        "type": "section",
                        "fields": fields
                    })

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=slack_message) as response:
                    if response.status == 200:
                        logger.info(f"Slack message sent successfully to {recipient}")
                        return True
                    else:
                        logger.error(f"Slack send failed: HTTP {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Slack send failed to {recipient}: {str(e)}")
            return False

    async def test_connection(self) -> Dict[str, Any]:
        try:
            webhook_url = self.config.get("webhook_url")

            test_message = {
                "text": "LCopilot notification test",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "🔔 This is a test notification from LCopilot"
                        }
                    }
                ]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=test_message) as response:
                    if response.status == 200:
                        return {"status": "success", "message": "Slack webhook test successful"}
                    else:
                        return {"status": "error", "message": f"HTTP {response.status}"}

        except Exception as e:
            return {"status": "error", "message": str(e)}


class WebhookProvider(NotificationProvider):
    """Generic webhook provider"""

    async def send(self, recipient: str, subject: str, body: str, metadata: Dict[str, Any] = None) -> bool:
        try:
            webhook_url = self.config.get("webhook_url")
            headers = self.config.get("headers", {})

            payload = {
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat()
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload, headers=headers) as response:
                    if response.status in [200, 201, 202]:
                        logger.info(f"Webhook sent successfully to {recipient}")
                        return True
                    else:
                        logger.error(f"Webhook send failed: HTTP {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Webhook send failed to {recipient}: {str(e)}")
            return False

    async def test_connection(self) -> Dict[str, Any]:
        try:
            webhook_url = self.config.get("webhook_url")
            headers = self.config.get("headers", {})

            test_payload = {
                "test": True,
                "message": "LCopilot notification test",
                "timestamp": datetime.utcnow().isoformat()
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=test_payload, headers=headers) as response:
                    if response.status in [200, 201, 202]:
                        return {"status": "success", "message": "Webhook test successful"}
                    else:
                        return {"status": "error", "message": f"HTTP {response.status}"}

        except Exception as e:
            return {"status": "error", "message": str(e)}


class SMSProvider(NotificationProvider):
    """SMS provider (stub implementation)"""

    async def send(self, recipient: str, subject: str, body: str, metadata: Dict[str, Any] = None) -> bool:
        # Stub implementation - would integrate with Twilio/AWS SNS
        logger.info(f"SMS stub: would send to {recipient}: {subject}")
        return True

    async def test_connection(self) -> Dict[str, Any]:
        return {"status": "success", "message": "SMS provider test (stub)"}


class NotificationService:
    """Main notification service"""

    def __init__(self, db: Session):
        self.db = db
        self.providers = {
            ChannelType.EMAIL: EmailProvider,
            ChannelType.SLACK: SlackProvider,
            ChannelType.WEBHOOK: WebhookProvider,
            ChannelType.SMS: SMSProvider
        }

    def get_provider(self, channel: NotificationChannel) -> NotificationProvider:
        """Get provider instance for channel"""
        provider_class = self.providers.get(channel.channel_type)
        if not provider_class:
            raise ValueError(f"Unsupported channel type: {channel.channel_type}")
        return provider_class(channel)

    async def emit_event(self, event: BaseEvent):
        """Emit event and trigger notifications"""
        logger.info(f"Emitting event {event.event_type} for tenant {event.tenant_alias}")

        # Find matching subscriptions
        subscriptions = await self.find_matching_subscriptions(event)

        # Process each subscription
        for subscription in subscriptions:
            await self.process_subscription(event, subscription)

    async def find_matching_subscriptions(self, event: BaseEvent) -> List[NotificationSubscription]:
        """Find subscriptions matching the event"""
        query = select(NotificationSubscription).where(
            and_(
                NotificationSubscription.tenant_alias == event.tenant_alias,
                NotificationSubscription.active == True,
                or_(
                    NotificationSubscription.event_types.contains([event.event_type.value]),
                    NotificationSubscription.event_types == []  # Empty means all events
                )
            )
        )

        result = self.db.execute(query)
        subscriptions = result.scalars().all()

        # Filter by event filters
        matching_subscriptions = []
        for subscription in subscriptions:
            event_filter = EventFilter(**subscription.filters)
            if event_filter.matches(event):
                matching_subscriptions.append(subscription)

        return matching_subscriptions

    async def process_subscription(self, event: BaseEvent, subscription: NotificationSubscription):
        """Process a single subscription for an event"""
        try:
            # Get channel
            channel = self.db.get(NotificationChannel, subscription.channel_id)
            if not channel or not channel.active:
                logger.warning(f"Channel {subscription.channel_id} not found or inactive")
                return

            # Get template
            template = await self.get_template(event.event_type, subscription.tenant_alias)
            if not template:
                logger.warning(f"No template found for {event.event_type}")
                return

            # Render message
            subject, body = await self.render_template(template, event)

            # Determine recipient
            recipient = subscription.recipient or channel.default_recipient
            if not recipient:
                logger.warning(f"No recipient for subscription {subscription.id}")
                return

            # Check for duplicate delivery (idempotency)
            delivery_id = self.generate_delivery_id(event.event_id, subscription.id)
            existing_delivery = self.db.query(NotificationDelivery).filter(
                NotificationDelivery.delivery_id == delivery_id
            ).first()

            if existing_delivery:
                logger.info(f"Delivery {delivery_id} already exists, skipping")
                return

            # Create delivery record
            delivery = NotificationDelivery(
                delivery_id=delivery_id,
                tenant_alias=event.tenant_alias,
                event_id=event.event_id,
                event_type=event.event_type,
                subscription_id=subscription.id,
                channel_id=channel.id,
                recipient=recipient,
                subject=subject,
                body=body,
                status=DeliveryStatus.PENDING,
                attempts=0,
                created_at=datetime.utcnow()
            )

            self.db.add(delivery)
            self.db.commit()

            # Send with retries
            await self.send_with_retries(delivery)

        except Exception as e:
            logger.error(f"Error processing subscription {subscription.id}: {str(e)}")

    async def send_with_retries(self, delivery: NotificationDelivery, max_attempts: int = 3):
        """Send notification with exponential backoff retries"""
        provider = None

        for attempt in range(max_attempts):
            try:
                # Get channel and provider
                channel = self.db.get(NotificationChannel, delivery.channel_id)
                if not channel:
                    delivery.status = DeliveryStatus.FAILED
                    delivery.last_error = "Channel not found"
                    break

                provider = self.get_provider(channel)

                # Update attempt count
                delivery.attempts = attempt + 1
                delivery.attempted_at = datetime.utcnow()

                # Prepare metadata
                metadata = {
                    "event_type": delivery.event_type,
                    "tenant": delivery.tenant_alias,
                    "event_id": delivery.event_id
                }

                # Send notification
                success = await provider.send(
                    delivery.recipient,
                    delivery.subject,
                    delivery.body,
                    metadata
                )

                if success:
                    delivery.status = DeliveryStatus.DELIVERED
                    delivery.delivered_at = datetime.utcnow()
                    delivery.last_error = None
                    logger.info(f"Delivery {delivery.delivery_id} successful")
                    break
                else:
                    delivery.last_error = "Provider send failed"

            except Exception as e:
                delivery.last_error = str(e)
                logger.error(f"Delivery attempt {attempt + 1} failed: {str(e)}")

            # Exponential backoff for retries
            if attempt < max_attempts - 1:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)

        # Mark as failed if all attempts exhausted
        if delivery.status == DeliveryStatus.PENDING:
            delivery.status = DeliveryStatus.FAILED

        self.db.commit()

    async def get_template(self, event_type: EventType, tenant_alias: str) -> Optional[NotificationTemplate]:
        """Get notification template for event type"""
        # Try tenant-specific template first
        query = select(NotificationTemplate).where(
            and_(
                NotificationTemplate.template_key == event_type.value,
                NotificationTemplate.tenant_alias == tenant_alias,
                NotificationTemplate.active == True
            )
        )

        result = self.db.execute(query)
        template = result.scalars().first()

        if template:
            return template

        # Fall back to default template
        query = select(NotificationTemplate).where(
            and_(
                NotificationTemplate.template_key == event_type.value,
                NotificationTemplate.tenant_alias.is_(None),
                NotificationTemplate.active == True
            )
        )

        result = self.db.execute(query)
        return result.scalars().first()

    async def render_template(self, template: NotificationTemplate, event: BaseEvent) -> tuple[str, str]:
        """Render template with event data"""
        context = {
            "event": event.dict(),
            "tenant": event.tenant_alias,
            "bank": event.bank_alias,
            "timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
            **event.context
        }

        # Simple template rendering (in production, use Jinja2)
        subject = template.subject_template
        body = template.body_template

        for key, value in context.items():
            placeholder = f"{{{key}}}"
            subject = subject.replace(placeholder, str(value) if value is not None else "")
            body = body.replace(placeholder, str(value) if value is not None else "")

        return subject, body

    def generate_delivery_id(self, event_id: str, subscription_id: str) -> str:
        """Generate unique delivery ID for idempotency"""
        content = f"{event_id}:{subscription_id}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def build_digest(self, tenant_alias: str, period: str = "daily") -> Optional[NotificationDigest]:
        """Build notification digest for period"""
        logger.info(f"Building {period} digest for tenant {tenant_alias}")

        # Calculate time range
        now = datetime.utcnow()
        if period == "daily":
            start_time = now - timedelta(days=1)
        elif period == "weekly":
            start_time = now - timedelta(weeks=1)
        else:
            raise ValueError(f"Unsupported digest period: {period}")

        # Check if digest already exists
        existing_digest = self.db.query(NotificationDigest).filter(
            and_(
                NotificationDigest.tenant_alias == tenant_alias,
                NotificationDigest.period == period,
                NotificationDigest.period_start >= start_time.date()
            )
        ).first()

        if existing_digest:
            logger.info(f"Digest already exists for {tenant_alias} {period}")
            return existing_digest

        # Collect events from the period
        from app.models.collaboration import Thread, Comment
        from app.models.bulk_jobs import BulkJob

        # Get collaboration activity
        threads_query = select(Thread).where(
            and_(
                Thread.tenant_alias == tenant_alias,
                Thread.created_at >= start_time
            )
        )
        threads = self.db.execute(threads_query).scalars().all()

        comments_query = select(Comment).where(
            and_(
                Comment.tenant_alias == tenant_alias,
                Comment.created_at >= start_time
            )
        )
        comments = self.db.execute(comments_query).scalars().all()

        # Get bulk job activity
        jobs_query = select(BulkJob).where(
            and_(
                BulkJob.tenant_alias == tenant_alias,
                BulkJob.created_at >= start_time
            )
        )
        jobs = self.db.execute(jobs_query).scalars().all()

        # Build summary
        summary = {
            "collaboration": {
                "threads_created": len(threads),
                "threads_resolved": len([t for t in threads if t.status == "resolved"]),
                "comments_added": len(comments),
                "high_priority_threads": len([t for t in threads if t.priority == "high"])
            },
            "bulk_processing": {
                "jobs_completed": len([j for j in jobs if j.status == "completed"]),
                "jobs_failed": len([j for j in jobs if j.status == "failed"]),
                "total_items_processed": sum(j.total_items for j in jobs if j.total_items),
                "average_success_rate": self.calculate_avg_success_rate(jobs)
            },
            "period": {
                "start": start_time.isoformat(),
                "end": now.isoformat(),
                "type": period
            }
        }

        # Create digest
        digest = NotificationDigest(
            tenant_alias=tenant_alias,
            period=period,
            period_start=start_time.date(),
            period_end=now.date(),
            summary=summary,
            created_at=now
        )

        self.db.add(digest)
        self.db.commit()

        logger.info(f"Created digest {digest.id} for {tenant_alias}")
        return digest

    def calculate_avg_success_rate(self, jobs: List) -> float:
        """Calculate average success rate for bulk jobs"""
        if not jobs:
            return 0.0

        total_items = sum(j.total_items for j in jobs if j.total_items)
        failed_items = sum(j.failed_items for j in jobs if j.failed_items)

        if total_items == 0:
            return 0.0

        return ((total_items - failed_items) / total_items) * 100

    async def send_digest(self, digest: NotificationDigest):
        """Send digest to subscribers"""
        # Find digest subscriptions
        subscriptions = self.db.query(NotificationSubscription).filter(
            and_(
                NotificationSubscription.tenant_alias == digest.tenant_alias,
                NotificationSubscription.digest_enabled == True,
                NotificationSubscription.active == True
            )
        ).all()

        for subscription in subscriptions:
            await self.send_digest_to_subscription(digest, subscription)

    async def send_digest_to_subscription(self, digest: NotificationDigest, subscription: NotificationSubscription):
        """Send digest to a specific subscription"""
        try:
            # Get channel
            channel = self.db.get(NotificationChannel, subscription.channel_id)
            if not channel or not channel.active:
                return

            # Render digest content
            subject = f"LCopilot {digest.period.title()} Digest - {digest.tenant_alias}"
            body = self.render_digest_body(digest)

            # Create delivery record
            delivery_id = f"digest_{digest.id}_{subscription.id}"
            delivery = NotificationDelivery(
                delivery_id=delivery_id,
                tenant_alias=digest.tenant_alias,
                event_id=f"digest_{digest.id}",
                event_type="digest",
                subscription_id=subscription.id,
                channel_id=channel.id,
                recipient=subscription.recipient or channel.default_recipient,
                subject=subject,
                body=body,
                status=DeliveryStatus.PENDING,
                attempts=0,
                created_at=datetime.utcnow()
            )

            self.db.add(delivery)
            self.db.commit()

            # Send with retries
            await self.send_with_retries(delivery)

        except Exception as e:
            logger.error(f"Error sending digest to subscription {subscription.id}: {str(e)}")

    def render_digest_body(self, digest: NotificationDigest) -> str:
        """Render digest email body"""
        summary = digest.summary

        body = f"""
LCopilot {digest.period.title()} Activity Digest
Period: {digest.period_start} to {digest.period_end}

COLLABORATION ACTIVITY:
• {summary['collaboration']['threads_created']} new discussion threads
• {summary['collaboration']['threads_resolved']} threads resolved
• {summary['collaboration']['comments_added']} comments added
• {summary['collaboration']['high_priority_threads']} high-priority threads

BULK PROCESSING:
• {summary['bulk_processing']['jobs_completed']} jobs completed successfully
• {summary['bulk_processing']['jobs_failed']} jobs failed
• {summary['bulk_processing']['total_items_processed']} total items processed
• {summary['bulk_processing']['average_success_rate']:.1f}% average success rate

This digest was generated automatically. To manage your notification preferences,
visit the LCopilot notification settings page.
        """.strip()

        return body