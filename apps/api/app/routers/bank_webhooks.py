"""
Webhooks Router
CRUD operations for webhook subscriptions and delivery management
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.api_tokens_webhooks import WebhookSubscription, WebhookDelivery
from app.models import User
from app.schemas.api_tokens_webhooks import (
    WebhookSubscriptionCreate,
    WebhookSubscriptionRead,
    WebhookSubscriptionCreateResponse,
    WebhookSubscriptionUpdate,
    WebhookSubscriptionListResponse,
    WebhookDeliveryRead,
    WebhookDeliveryListResponse,
    WebhookTestRequest,
    WebhookTestResponse,
    WebhookReplayRequest,
    WebhookReplayResponse,
)
from app.services.webhook_service import WebhookService
from app.routers.bank import require_bank_or_admin


router = APIRouter(prefix="/bank/webhooks", tags=["bank", "webhooks"])


@router.post("", response_model=WebhookSubscriptionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    webhook_data: WebhookSubscriptionCreate,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Create a new webhook subscription"""
    webhook_service = WebhookService(db)
    
    secret = webhook_service.generate_secret()
    
    subscription = WebhookSubscription(
        company_id=current_user.company_id,
        created_by=current_user.id,
        name=webhook_data.name,
        description=webhook_data.description,
        url=webhook_data.url,
        secret=secret,
        events=webhook_data.events,
        timeout_seconds=webhook_data.timeout_seconds,
        retry_count=webhook_data.retry_count,
        retry_backoff_multiplier=webhook_data.retry_backoff_multiplier,
        headers=webhook_data.headers,
        is_active=True,
    )
    
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    return WebhookSubscriptionCreateResponse(
        subscription=WebhookSubscriptionRead.model_validate(subscription),
        secret=secret,
    )


@router.get("", response_model=WebhookSubscriptionListResponse)
async def list_webhooks(
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """List all webhook subscriptions for the current company"""
    subscriptions = db.query(WebhookSubscription).filter(
        WebhookSubscription.company_id == current_user.company_id,
        WebhookSubscription.deleted_at.is_(None),
    ).order_by(WebhookSubscription.created_at.desc()).all()
    
    return WebhookSubscriptionListResponse(
        subscriptions=[WebhookSubscriptionRead.model_validate(s) for s in subscriptions],
        total=len(subscriptions),
    )


@router.get("/{subscription_id}", response_model=WebhookSubscriptionRead)
async def get_webhook(
    subscription_id: UUID,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Get a specific webhook subscription"""
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == subscription_id,
        WebhookSubscription.company_id == current_user.company_id,
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook subscription not found",
        )
    
    return WebhookSubscriptionRead.model_validate(subscription)


@router.put("/{subscription_id}", response_model=WebhookSubscriptionRead)
async def update_webhook(
    subscription_id: UUID,
    webhook_data: WebhookSubscriptionUpdate,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Update a webhook subscription"""
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == subscription_id,
        WebhookSubscription.company_id == current_user.company_id,
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook subscription not found",
        )
    
    if webhook_data.name is not None:
        subscription.name = webhook_data.name
    if webhook_data.description is not None:
        subscription.description = webhook_data.description
    if webhook_data.url is not None:
        subscription.url = webhook_data.url
    if webhook_data.events is not None:
        subscription.events = webhook_data.events
    if webhook_data.is_active is not None:
        subscription.is_active = webhook_data.is_active
    if webhook_data.timeout_seconds is not None:
        subscription.timeout_seconds = webhook_data.timeout_seconds
    if webhook_data.headers is not None:
        subscription.headers = webhook_data.headers
    
    db.commit()
    db.refresh(subscription)
    
    return WebhookSubscriptionRead.model_validate(subscription)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    subscription_id: UUID,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Delete a webhook subscription (soft delete)"""
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == subscription_id,
        WebhookSubscription.company_id == current_user.company_id,
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook subscription not found",
        )
    
    subscription.deleted_at = datetime.utcnow()
    subscription.is_active = False
    
    db.commit()


@router.post("/{subscription_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    subscription_id: UUID,
    test_data: WebhookTestRequest,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Test a webhook subscription with a test payload"""
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == subscription_id,
        WebhookSubscription.company_id == current_user.company_id,
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook subscription not found",
        )
    
    webhook_service = WebhookService(db)
    
    # Use custom payload or default test payload
    payload = test_data.payload or {
        "event": "webhook.test",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {"message": "This is a test webhook"},
    }
    
    delivery = await webhook_service.deliver_webhook(
        subscription=subscription,
        event_type="webhook.test",
        event_id=None,
        payload=payload,
    )
    
    return WebhookTestResponse(
        delivery_id=delivery.id,
        status=delivery.status,
        http_status_code=delivery.http_status_code,
        response_body=delivery.response_body,
        duration_ms=delivery.duration_ms,
        error_message=delivery.error_message,
    )


@router.get("/{subscription_id}/deliveries", response_model=WebhookDeliveryListResponse)
async def list_deliveries(
    subscription_id: UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    event_type: Optional[str] = Query(None, alias="event_type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """List webhook deliveries for a subscription"""
    # Verify subscription belongs to company
    subscription = db.query(WebhookSubscription).filter(
        WebhookSubscription.id == subscription_id,
        WebhookSubscription.company_id == current_user.company_id,
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook subscription not found",
        )
    
    webhook_service = WebhookService(db)
    deliveries, total = webhook_service.get_deliveries(
        subscription_id=subscription_id,
        status=status_filter,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
    
    return WebhookDeliveryListResponse(
        deliveries=[WebhookDeliveryRead.model_validate(d) for d in deliveries],
        total=total,
    )


@router.post("/deliveries/{delivery_id}/replay", response_model=WebhookReplayResponse)
async def replay_delivery(
    delivery_id: UUID,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Replay a failed webhook delivery"""
    # Verify delivery belongs to company
    delivery = db.query(WebhookDelivery).filter(
        WebhookDelivery.id == delivery_id,
        WebhookDelivery.company_id == current_user.company_id,
    ).first()
    
    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found",
        )
    
    webhook_service = WebhookService(db)
    
    try:
        new_delivery = await webhook_service.replay_delivery(delivery_id)
        return WebhookReplayResponse(
            new_delivery_id=new_delivery.id,
            status=new_delivery.status,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

