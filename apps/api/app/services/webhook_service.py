"""
Webhook Service for Webhook Delivery Management
Handles webhook signing, delivery, retry logic, replay, and logging
"""
import hmac
import hashlib
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    # Fallback to requests if httpx not available
    try:
        import requests
        REQUESTS_AVAILABLE = True
    except ImportError:
        REQUESTS_AVAILABLE = False

from app.models.api_tokens_webhooks import (
    WebhookSubscription,
    WebhookDelivery,
    DeliveryStatus,
)
from app.models import Company


class WebhookService:
    """Service for managing webhook deliveries"""
    
    SIGNATURE_HEADER = "X-LCopilot-Signature"
    SIGNATURE_ALGORITHM = "sha256"
    TIMEOUT_DEFAULT = 30
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_secret(self) -> str:
        """Generate a random webhook secret"""
        return secrets.token_urlsafe(32)
    
    def sign_payload(self, payload: Dict[str, Any], secret: str) -> str:
        """
        Sign a webhook payload using HMAC-SHA256.
        Returns the signature string.
        """
        payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            secret.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{self.SIGNATURE_ALGORITHM}={signature}"
    
    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify a webhook signature"""
        expected_signature = self.sign_payload(json.loads(payload), secret)
        return hmac.compare_digest(signature, expected_signature)
    
    async def deliver_webhook(
        self,
        subscription: WebhookSubscription,
        event_type: str,
        event_id: Optional[str],
        payload: Dict[str, Any],
        attempt_number: int = 1
    ) -> WebhookDelivery:
        """
        Deliver a webhook to the subscription endpoint.
        Creates a delivery record and attempts to send.
        """
        # Sign the payload
        signature = self.sign_payload(payload, subscription.secret)
        
        # Create delivery record
        delivery = WebhookDelivery(
            subscription_id=subscription.id,
            company_id=subscription.company_id,
            event_type=event_type,
            event_id=event_id,
            payload=payload,
            signature=signature,
            status=DeliveryStatus.PENDING.value,
            attempt_number=attempt_number,
            max_attempts=subscription.retry_count + 1,  # +1 for initial attempt
            started_at=datetime.utcnow(),
        )
        
        self.db.add(delivery)
        self.db.commit()
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            self.SIGNATURE_HEADER: signature,
            "X-LCopilot-Event": event_type,
            "X-LCopilot-Delivery-Id": str(delivery.id),
        }
        
        # Add custom headers if configured
        if subscription.headers:
            headers.update(subscription.headers)
        
        # Attempt delivery
        start_time = time.time()
        try:
            if HTTPX_AVAILABLE:
                async with httpx.AsyncClient(timeout=subscription.timeout_seconds) as client:
                    response = await client.post(
                        subscription.url,
                        json=payload,
                        headers=headers,
                    )
                    http_status_code = response.status_code
                    response_body = response.text[:10000]
                    response_headers = dict(response.headers)
                    is_success = response.is_success
            elif REQUESTS_AVAILABLE:
                response = requests.post(
                    subscription.url,
                    json=payload,
                    headers=headers,
                    timeout=subscription.timeout_seconds,
                )
                http_status_code = response.status_code
                response_body = response.text[:10000]
                response_headers = dict(response.headers)
                is_success = 200 <= response.status_code < 300
            else:
                raise RuntimeError("Neither httpx nor requests library available")
                
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Update delivery record
            delivery.status = DeliveryStatus.SUCCESS.value if is_success else DeliveryStatus.FAILED.value
            delivery.http_status_code = http_status_code
            delivery.response_body = response_body
            delivery.response_headers = response_headers
            delivery.completed_at = datetime.utcnow()
            delivery.duration_ms = duration_ms
            
            if not is_success:
                delivery.error_message = f"HTTP {http_status_code}: {response_body[:500]}"
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            delivery.status = DeliveryStatus.FAILED.value
            delivery.error_message = str(e)[:1000]
            delivery.completed_at = datetime.utcnow()
            delivery.duration_ms = duration_ms
            
            # Try to extract HTTP status if available
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                delivery.http_status_code = e.response.status_code
        
        # Update subscription statistics
        if delivery.status == DeliveryStatus.SUCCESS.value:
            subscription.success_count += 1
            subscription.last_success_at = delivery.completed_at
        else:
            subscription.failure_count += 1
            subscription.last_failure_at = delivery.completed_at
        
        subscription.last_delivery_at = delivery.completed_at
        
        self.db.commit()
        self.db.refresh(delivery)
        
        # Schedule retry if failed and attempts remaining
        if delivery.status == DeliveryStatus.FAILED.value and attempt_number < delivery.max_attempts:
            self._schedule_retry(delivery, subscription)
        
        return delivery
    
    def _schedule_retry(self, delivery: WebhookDelivery, subscription: WebhookSubscription) -> None:
        """Schedule a retry for a failed delivery"""
        # Calculate backoff: multiplier ^ (attempt_number - 1) seconds
        backoff_seconds = subscription.retry_backoff_multiplier ** (delivery.attempt_number - 1)
        next_retry_at = datetime.utcnow() + timedelta(seconds=int(backoff_seconds))
        
        delivery.status = DeliveryStatus.RETRYING.value
        delivery.next_retry_at = next_retry_at
        delivery.retry_reason = f"Scheduled retry after {int(backoff_seconds)}s backoff"
        
        self.db.commit()
    
    async def retry_delivery(self, delivery_id: UUID) -> WebhookDelivery:
        """Retry a failed webhook delivery"""
        delivery = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id
        ).first()
        
        if not delivery:
            raise ValueError("Delivery not found")
        
        subscription = delivery.subscription
        
        if delivery.attempt_number >= delivery.max_attempts:
            raise ValueError("Maximum retry attempts reached")
        
        # Retry the delivery
        new_delivery = await self.deliver_webhook(
            subscription,
            delivery.event_type,
            delivery.event_id,
            delivery.payload,
            attempt_number=delivery.attempt_number + 1
        )
        
        return new_delivery
    
    async def replay_delivery(self, delivery_id: UUID) -> WebhookDelivery:
        """
        Replay a webhook delivery (creates a new delivery with same payload).
        Used for manually retrying after fixing issues.
        """
        original_delivery = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id
        ).first()
        
        if not original_delivery:
            raise ValueError("Delivery not found")
        
        subscription = original_delivery.subscription
        
        # Create new delivery (reset attempt counter)
        new_delivery = await self.deliver_webhook(
            subscription,
            original_delivery.event_type,
            original_delivery.event_id,
            original_delivery.payload,
            attempt_number=1
        )
        
        return new_delivery
    
    def get_deliveries(
        self,
        subscription_id: Optional[UUID] = None,
        company_id: Optional[UUID] = None,
        status: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[WebhookDelivery], int]:
        """Get webhook deliveries with filtering"""
        query = self.db.query(WebhookDelivery)
        
        if subscription_id:
            query = query.filter(WebhookDelivery.subscription_id == subscription_id)
        
        if company_id:
            query = query.filter(WebhookDelivery.company_id == company_id)
        
        if status:
            query = query.filter(WebhookDelivery.status == status)
        
        if event_type:
            query = query.filter(WebhookDelivery.event_type == event_type)
        
        total = query.count()
        
        deliveries = query.order_by(desc(WebhookDelivery.started_at)).limit(limit).offset(offset).all()
        
        return deliveries, total
    
    def get_pending_retries(self) -> List[WebhookDelivery]:
        """Get deliveries that are ready to retry"""
        return self.db.query(WebhookDelivery).filter(
            and_(
                WebhookDelivery.status == DeliveryStatus.RETRYING.value,
                WebhookDelivery.next_retry_at <= datetime.utcnow(),
                WebhookDelivery.attempt_number < WebhookDelivery.max_attempts
            )
        ).all()

