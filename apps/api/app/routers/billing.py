"""
Billing API endpoints for LCopilot.

This module provides REST API endpoints for billing operations including:
- Company billing management
- Usage tracking and reporting
- Invoice management
- Payment processing
- Quota management
"""

import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..core.security import get_current_user, require_roles, require_bank_or_admin
from ..models import User, UserRole
from ..models.invoice import Invoice as InvoiceModel
from ..services.billing_service import BillingService
from ..providers.payments.base import PaymentProviderFactory, PaymentProviderError
from ..config import settings
from ..schemas import billing as schemas

router = APIRouter(prefix="/billing", tags=["billing"])

COMPANY_ADMIN_ROLE = "company_admin"


def get_billing_service(db: Session = Depends(get_db)) -> BillingService:
    """Get billing service instance."""
    return BillingService(db)


def _resolve_bank_tenants(request: Request) -> List[uuid.UUID]:
    tenant_scope = getattr(request.state, "tenant_ids", None)
    if tenant_scope is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bank context unavailable for this request",
        )
    resolved: List[uuid.UUID] = []
    for tenant_id in tenant_scope:
        try:
            resolved.append(uuid.UUID(str(tenant_id)))
        except (ValueError, TypeError):
            continue
    return resolved


def _serialize_usage_record(stats: Dict[str, Any]) -> Dict[str, Any]:
    serialised = stats.copy()
    total_cost = serialised.get("total_cost")
    if isinstance(total_cost, Decimal):
        serialised["total_cost"] = float(total_cost)
    quota_remaining = serialised.get("quota_remaining")
    if isinstance(quota_remaining, Decimal):
        serialised["quota_remaining"] = float(quota_remaining)
    return serialised


def get_payment_provider(provider_name: str = "sslcommerz"):
    """Get payment provider instance."""
    try:
        if provider_name == "stripe":
            config = {
                "api_key": settings.STRIPE_SECRET_KEY,
                "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
                "webhook_secret": settings.STRIPE_WEBHOOK_SECRET,
            }
        else:  # default to sslcommerz
            config = {
                "store_id": settings.SSLCOMMERZ_STORE_ID,
                "store_password": settings.SSLCOMMERZ_STORE_PASSWORD,
                "sandbox": settings.SSLCOMMERZ_SANDBOX,
                "success_url": f"{settings.FRONTEND_URL}/billing/payment/success",
                "fail_url": f"{settings.FRONTEND_URL}/billing/payment/failed",
                "cancel_url": f"{settings.FRONTEND_URL}/billing/payment/cancelled",
                "ipn_url": f"{settings.API_BASE_URL}/billing/webhooks/sslcommerz"
            }

        return PaymentProviderFactory.create_provider(provider_name, config)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize payment provider: {str(e)}"
        )


# Company billing endpoints
@router.get("/company", response_model=schemas.CompanyBillingInfo)
async def get_company_billing_info(
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Get current company's billing information."""
    try:
        return billing_service.get_company_billing_info(current_user.company_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get billing info: {str(e)}"
        )


@router.put("/company", response_model=schemas.CompanyBillingInfo)
async def update_company_billing(
    update_data: schemas.CompanyBillingUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, COMPANY_ADMIN_ROLE])),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Update company billing settings."""
    try:
        return billing_service.update_company_billing(current_user.company_id, update_data.dict(exclude_unset=True))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update billing settings: {str(e)}"
        )


@router.get("/usage", response_model=schemas.UsageStats)
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Get company usage statistics."""
    try:
        return billing_service.get_usage_stats(current_user.company_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage stats: {str(e)}"
        )


@router.get("/usage/records", response_model=schemas.UsageRecordList)
async def get_usage_records(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    action: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Get paginated usage records for company."""
    try:
        return billing_service.get_usage_records(
            company_id=current_user.company_id,
            page=page,
            per_page=per_page,
            start_date=start_date,
            end_date=end_date,
            action=action
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage records: {str(e)}"
        )


# Invoice endpoints
@router.get("/invoices", response_model=schemas.InvoiceList)
async def get_invoices(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Get paginated invoices for company."""
    try:
        return billing_service.get_invoices(
            company_id=current_user.company_id,
            page=page,
            per_page=per_page,
            status=status
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get invoices: {str(e)}"
        )


@router.get("/invoices/{invoice_id}", response_model=schemas.Invoice)
async def get_invoice(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Get specific invoice details."""
    try:
        invoice = billing_service.get_invoice(invoice_id, current_user.company_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )
        return invoice
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get invoice: {str(e)}"
        )


@router.post("/invoices/generate", response_model=schemas.Invoice)
async def generate_invoice(
    period_start: date = Query(..., description="Invoice period start date"),
    period_end: date = Query(..., description="Invoice period end date"),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, COMPANY_ADMIN_ROLE])),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Generate invoice for specified period."""
    try:
        if period_end <= period_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )

        invoice = billing_service.generate_invoice(current_user.company_id, period_start, period_end)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No usage found for the specified period"
            )

        return invoice
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate invoice: {str(e)}"
        )


# Payment endpoints
@router.post("/payments/intents", response_model=schemas.PaymentIntent)
async def create_payment_intent(
    payment_data: schemas.PaymentIntentCreate,
    provider_override: Optional[str] = Query(None, description="Payment provider (sslcommerz or stripe)"),
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service),
    db: Session = Depends(get_db)
):
    """Create payment intent for invoice or custom amount."""
    try:
        provider_name = provider_override or payment_data.provider or "sslcommerz"
        provider_name = provider_name.lower()
        if provider_name not in {"sslcommerz", "stripe"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported payment provider"
            )

        # Determine amount/currency
        amount: Decimal
        currency: str
        if payment_data.invoice_id:
            invoice = db.query(InvoiceModel).filter(
                InvoiceModel.id == payment_data.invoice_id,
                InvoiceModel.company_id == current_user.company_id
            ).first()

            if not invoice:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invoice not found"
                )

            amount = invoice.amount
            currency = invoice.currency
        else:
            amount = Decimal(str(payment_data.amount)) if payment_data.amount is not None else Decimal("0")
            currency = payment_data.currency or ("USD" if provider_name == "stripe" else "BDT")

        # Get payment provider
        payment_provider = get_payment_provider(provider_name)

        # Create customer if not exists
        company = billing_service.get_company_billing_info(current_user.company_id)
        customer_id = company.get("payment_customer_id")

        if not customer_id:
            customer_id = payment_provider.create_customer(
                email=company.get("billing_email") or current_user.email,
                name=company.get("name"),
                metadata={"company_id": str(current_user.company_id)}
            )
            billing_service.update_company_billing(
                current_user.company_id,
                {"payment_customer_id": customer_id}
            )

        metadata = payment_data.metadata or {}
        metadata.setdefault("company_id", str(current_user.company_id))
        metadata.setdefault("user_id", str(current_user.id))
        if payment_data.invoice_id:
            metadata.setdefault("invoice_id", str(payment_data.invoice_id))
        if payment_data.price_id:
            metadata.setdefault("price_id", payment_data.price_id)
        if payment_data.mode:
            metadata.setdefault("checkout_mode", payment_data.mode)
        if payment_data.quantity and payment_data.quantity > 1:
            metadata.setdefault("quantity", payment_data.quantity)

        # Determine defaults for Stripe subscriptions when amount not provided
        if provider_name == "stripe" and amount <= 0:
            amount = Decimal("0")
            currency = payment_data.currency or "USD"

        intent = payment_provider.create_payment_intent(
            amount=amount,
            currency=currency,
            customer_id=customer_id,
            description=metadata.get("description") or f"Payment for {company.get('name')}",
            metadata=metadata,
            return_url=payment_data.return_url or f"{settings.FRONTEND_URL}/dashboard/billing?success=true",
            cancel_url=payment_data.cancel_url or f"{settings.FRONTEND_URL}/dashboard/billing?cancelled=true",
            payment_method_types=payment_data.payment_method_types,
        )

        if payment_data.invoice_id:
            billing_service.update_invoice_payment_intent(payment_data.invoice_id, intent.id)

        return schemas.PaymentIntent(
            id=intent.id,
            amount=intent.amount,
            currency=intent.currency,
            status=intent.status.value,
            client_secret=intent.client_secret,
            checkout_url=intent.checkout_url,
            payment_method_types=intent.payment_method_types,
            created_at=intent.created_at,
            expires_at=intent.expires_at
        )

    except HTTPException:
        raise
    except PaymentProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment provider error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment intent: {str(e)}"
        )


@router.get("/payments/{payment_id}", response_model=schemas.PaymentResult)
async def get_payment_status(
    payment_id: str,
    provider: str = Query("sslcommerz", description="Payment provider"),
    current_user: User = Depends(get_current_user)
):
    """Get payment status."""
    try:
        payment_provider = get_payment_provider(provider)
        result = payment_provider.get_payment_status(payment_id)

        return schemas.PaymentResult(
            success=result.success,
            payment_id=result.payment_id,
            transaction_id=result.transaction_id,
            status=result.status.value,
            amount=result.amount,
            currency=result.currency,
            payment_method=result.payment_method,
            error_message=result.error_message
        )

    except PaymentProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment provider error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment status: {str(e)}"
        )


@router.post("/payments/{payment_id}/refund", response_model=schemas.RefundResult)
async def refund_payment(
    payment_id: str,
    refund_data: schemas.RefundCreate,
    provider: str = Query("sslcommerz", description="Payment provider"),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, COMPANY_ADMIN_ROLE]))
):
    """Refund a payment."""
    try:
        payment_provider = get_payment_provider(provider)
        result = payment_provider.refund_payment(
            payment_id=payment_id,
            amount=refund_data.amount,
            reason=refund_data.reason
        )


@router.post("/payments/portal", response_model=Dict[str, str])
async def create_billing_portal(
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service),
):
    """Create a billing portal session for Stripe customers."""
    try:
        provider = get_payment_provider("stripe")
        company = billing_service.get_company_billing_info(current_user.company_id)
        customer_id = company.get("payment_customer_id")
        if not customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Stripe customer associated with this company yet",
            )

        portal_url = provider.create_billing_portal_session(
            customer_id=customer_id,
            return_url=f"{settings.FRONTEND_URL}/dashboard/billing",
        )

        return {"url": portal_url}

    except HTTPException:
        raise
    except PaymentProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment provider error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create billing portal session: {str(e)}",
        )

        return schemas.RefundResult(
            success=result.success,
            refund_id=result.refund_id,
            original_payment_id=result.original_payment_id,
            amount=result.amount,
            status=result.status.value,
            error_message=result.error_message
        )

    except PaymentProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment provider error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refund payment: {str(e)}"
        )


# Quota endpoints
@router.get("/pricing", response_model=schemas.PricingInfo)
async def get_pricing():
    """Get current pricing information."""
    return schemas.PricingInfo()


@router.post("/quota/check", response_model=schemas.QuotaCheckResult)
async def check_quota(
    quota_check: schemas.QuotaCheck,
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Check if action is within quota limits."""
    try:
        for _ in range(quota_check.quantity):
            allowed = billing_service.enforce_quota(current_user.company_id, quota_check.action)
            if not allowed:
                stats = billing_service.get_usage_stats(current_user.company_id)
                return schemas.QuotaCheckResult(
                    allowed=False,
                    remaining=stats.quota_remaining,
                    limit=stats.quota_limit,
                    message="Quota limit exceeded"
                )

        stats = billing_service.get_usage_stats(current_user.company_id)
        return schemas.QuotaCheckResult(
            allowed=True,
            remaining=stats.quota_remaining,
            limit=stats.quota_limit,
            message="Action allowed"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check quota: {str(e)}"
        )


# Webhook endpoints
@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    billing_service: BillingService = Depends(get_billing_service),
    db: Session = Depends(get_db)
):
    """Handle Stripe webhook events."""
    try:
        payload = await request.body()
        signature = request.headers.get("stripe-signature")

        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe signature"
            )

        payment_provider = get_payment_provider("stripe")

        # Verify webhook signature
        if not payment_provider.verify_webhook_signature(
            payload, signature, settings.STRIPE_WEBHOOK_SECRET
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature"
            )

        # Parse webhook event
        import json
        event_data = json.loads(payload.decode())
        webhook_event = payment_provider.parse_webhook_event(event_data)

        # Process payment webhook
        billing_service.process_payment_webhook(webhook_event)

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.post("/webhooks/sslcommerz")
async def sslcommerz_webhook(
    request: Request,
    billing_service: BillingService = Depends(get_billing_service),
    db: Session = Depends(get_db)
):
    """Handle SSLCommerz IPN webhook events."""
    try:
        # SSLCommerz sends form-encoded data
        payload = await request.body()

        payment_provider = get_payment_provider("sslcommerz")

        # Parse form data
        from urllib.parse import parse_qs
        form_data = parse_qs(payload.decode())
        # Convert to dict with single values
        webhook_data = {k: v[0] if isinstance(v, list) and v else v for k, v in form_data.items()}

        # Verify webhook (SSLCommerz uses different verification)
        if not payment_provider.verify_webhook_signature(payload, "", ""):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook data"
            )

        # Parse webhook event
        webhook_event = payment_provider.parse_webhook_event(webhook_data)

        # Process payment webhook
        billing_service.process_payment_webhook(webhook_event)

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


# Admin endpoints (require admin role)
@router.get("/admin/companies", response_model=List[schemas.AdminCompanyStats])
async def get_admin_company_stats(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value])),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Get company statistics for admin users."""
    try:
        return billing_service.get_admin_company_stats(page, per_page)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get company stats: {str(e)}"
        )


@router.get("/admin/usage-report", response_model=schemas.AdminUsageReport)
async def get_admin_usage_report(
    start_date: date = Query(..., description="Report start date"),
    end_date: date = Query(..., description="Report end date"),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value])),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Get usage report for admin users."""
    try:
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )

        return billing_service.get_admin_usage_report(start_date, end_date)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage report: {str(e)}"
        )


@router.get("/bank/summary")
def get_bank_billing_summary(
    request: Request,
    current_user: User = Depends(require_bank_or_admin),
    billing_service: BillingService = Depends(get_billing_service),
):
    """Aggregate billing metrics across all tenants managed by a bank."""
    tenant_ids = _resolve_bank_tenants(request)
    if not tenant_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tenant mappings found for this bank",
        )

    per_tenant: List[Dict[str, Any]] = []
    total_usage = 0
    total_cost = Decimal("0")

    for tenant_uuid in tenant_ids:
        try:
            stats = billing_service.get_usage_stats(tenant_uuid)
        except Exception:
            continue
        per_tenant.append(_serialize_usage_record(stats))
        total_usage += stats.get("total_usage", 0) or 0
        tenant_cost = stats.get("total_cost", Decimal("0")) or Decimal("0")
        if not isinstance(tenant_cost, Decimal):
            tenant_cost = Decimal(str(tenant_cost))
        total_cost += tenant_cost

    return {
        "bank_id": getattr(request.state, "bank_id", None),
        "tenant_count": len(per_tenant),
        "total_usage": total_usage,
        "total_cost": float(total_cost),
        "tenants": per_tenant,
    }


@router.get("/bank/tenants")
def list_bank_tenants_billing(
    request: Request,
    current_user: User = Depends(require_bank_or_admin),
    billing_service: BillingService = Depends(get_billing_service),
):
    """Return per-tenant billing usage for the current bank."""
    tenant_ids = _resolve_bank_tenants(request)
    tenants: List[Dict[str, Any]] = []

    for tenant_uuid in tenant_ids:
        try:
            stats = billing_service.get_usage_stats(tenant_uuid)
        except Exception:
            continue
        tenants.append(_serialize_usage_record(stats))

    return {
        "bank_id": getattr(request.state, "bank_id", None),
        "results": tenants,
        "count": len(tenants),
    }

