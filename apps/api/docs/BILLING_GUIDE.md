# LCopilot Billing System Guide

## Overview

LCopilot's billing system provides comprehensive usage tracking, quota enforcement, and payment processing for Letter of Credit validation services. The system supports multiple payment gateways, flexible pricing models, and detailed analytics.

## Table of Contents

1. [Architecture](#architecture)
2. [Database Models](#database-models)
3. [Pricing Structure](#pricing-structure)
4. [API Endpoints](#api-endpoints)
5. [Payment Providers](#payment-providers)
6. [Quota Enforcement](#quota-enforcement)
7. [Webhook Integration](#webhook-integration)
8. [Admin Features](#admin-features)
9. [Testing](#testing)
10. [Deployment](#deployment)

## Architecture

The billing system follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Router    │    │  Billing Service │    │ Payment Providers│
│   (billing.py)  │◄──►│  (billing_service)│◄──►│ (stripe/ssl)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         ▲                        ▲                        ▲
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Quota Middleware│    │   Database Models│    │   Webhooks      │
│ (quota_middleware)│    │ (Company, Invoice)│    │ (SSL/Stripe)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Key Components

- **API Router**: RESTful endpoints for billing operations
- **Billing Service**: Core business logic and data management
- **Payment Providers**: Abstracted payment gateway integrations
- **Quota Middleware**: Automatic usage enforcement
- **Database Models**: Persistent data storage
- **Webhook Handlers**: Real-time payment notifications

## Database Models

### Company Model
```python
class Company(Base):
    id: UUID                    # Primary key
    name: str                   # Company name
    plan: PlanType             # FREE, STARTER, PROFESSIONAL, ENTERPRISE
    quota_limit: Optional[int]  # Monthly validation limit
    billing_email: str         # Billing contact email
    payment_customer_id: str   # Payment provider customer ID
    billing_cycle_start: date  # Billing cycle start date
    status: CompanyStatus      # ACTIVE, SUSPENDED, CANCELLED
```

### Invoice Model
```python
class Invoice(Base):
    id: UUID                   # Primary key
    company_id: UUID          # Foreign key to Company
    invoice_number: str       # Unique invoice number
    amount: Decimal           # Total amount in local currency
    currency: Currency        # BDT, USD
    status: InvoiceStatus     # PENDING, PAID, OVERDUE, CANCELLED
    period_start: date        # Billing period start
    period_end: date          # Billing period end
    due_date: date           # Payment due date
    payment_intent_id: str   # Payment provider intent ID
    line_items: JSON         # Detailed billing items
```

### Usage Record Model
```python
class UsageRecord(Base):
    id: UUID                  # Primary key
    company_id: UUID         # Foreign key to Company
    user_id: UUID           # Foreign key to User
    session_id: UUID        # Foreign key to ValidationSession
    action: str             # per_check, import_draft, import_bundle
    cost: Decimal           # Cost in BDT
    units: int              # Number of units (usually 1)
    timestamp: datetime     # When the action occurred
    billed: bool           # Whether included in an invoice
    invoice_id: UUID       # Foreign key to Invoice (when billed)
```

## Pricing Structure

LCopilot uses a flexible pricing model supporting both pay-per-use and subscription plans.

### Current Pricing (BDT)
```python
PER_CHECK = Decimal("1200.00")          # Standard LC validation
IMPORT_DRAFT = Decimal("1000.00")       # Draft LC import
IMPORT_BUNDLE = Decimal("1800.00")      # Full document bundle import
```

### Subscription Plans

| Plan | Monthly Cost (BDT) | Quota | Features |
|------|-------------------|-------|----------|
| Free | 0 | 5 validations | Basic validation |
| Starter | 15,000 | 100 validations | Standard features |
| Professional | 45,000 | 500 validations | Advanced features |
| Enterprise | Custom | Unlimited | Custom integrations |

### Cost Calculation Logic

```python
def calculate_cost(action: str, quantity: int = 1) -> Decimal:
    """Calculate cost for a specific action."""
    base_costs = {
        BillingAction.PER_CHECK.value: PricingConstants.PER_CHECK,
        BillingAction.IMPORT_DRAFT.value: PricingConstants.IMPORT_DRAFT,
        BillingAction.IMPORT_BUNDLE.value: PricingConstants.IMPORT_BUNDLE,
    }
    return base_costs.get(action, Decimal("0")) * quantity
```

## API Endpoints

### Company Billing

#### GET `/billing/company`
Get company billing information including plan, quota usage, and payment details.

**Response:**
```json
{
  "id": "uuid",
  "name": "Company Name",
  "plan": "STARTER",
  "quota_limit": 100,
  "quota_used": 25,
  "quota_remaining": 75,
  "billing_email": "billing@company.com",
  "payment_customer_id": "cust_12345"
}
```

#### PUT `/billing/company`
Update company billing settings (requires admin role).

**Request:**
```json
{
  "plan": "PROFESSIONAL",
  "quota_limit": 500,
  "billing_email": "newbilling@company.com"
}
```

### Usage Tracking

#### GET `/billing/usage`
Get usage statistics for the current company.

**Response:**
```json
{
  "company_id": "uuid",
  "current_month": 25,
  "current_week": 8,
  "today": 3,
  "total_usage": 150,
  "total_cost": 180000.00,
  "quota_limit": 100,
  "quota_used": 25,
  "quota_remaining": 75
}
```

#### GET `/billing/usage/records`
Get paginated usage records with optional filtering.

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Records per page (default: 50, max: 100)
- `start_date`: Filter start date (YYYY-MM-DD)
- `end_date`: Filter end date (YYYY-MM-DD)
- `action`: Filter by action type

### Invoice Management

#### GET `/billing/invoices`
Get paginated list of company invoices.

**Query Parameters:**
- `page`: Page number
- `per_page`: Invoices per page
- `status`: Filter by invoice status

#### GET `/billing/invoices/{invoice_id}`
Get specific invoice details.

#### POST `/billing/invoices/generate`
Generate invoice for specified period (requires admin role).

**Query Parameters:**
- `period_start`: Start date (required)
- `period_end`: End date (required)

### Payment Processing

#### POST `/billing/payments/intents`
Create payment intent for invoice or custom amount.

**Request:**
```json
{
  "invoice_id": "uuid",  // Optional - for paying specific invoice
  "amount": 12000.00,    // Optional - for custom payments
  "currency": "BDT",
  "provider": "sslcommerz",  // or "stripe"
  "return_url": "https://app.com/success",
  "cancel_url": "https://app.com/cancel"
}
```

**Response:**
```json
{
  "id": "pi_12345",
  "amount": 12000.00,
  "currency": "BDT",
  "status": "pending",
  "checkout_url": "https://checkout.provider.com/...",
  "client_secret": "pi_12345_secret"
}
```

#### GET `/billing/payments/{payment_id}`
Get payment status.

#### POST `/billing/payments/{payment_id}/refund`
Refund a payment (requires admin role).

### Quota Management

#### GET `/billing/pricing`
Get current pricing information.

#### POST `/billing/quota/check`
Check if action is within quota limits.

**Request:**
```json
{
  "action": "per_check",
  "quantity": 1
}
```

**Response:**
```json
{
  "allowed": true,
  "remaining": 75,
  "limit": 100,
  "message": "Action allowed"
}
```

### Webhook Endpoints

#### POST `/billing/webhooks/stripe`
Handle Stripe webhook events.

#### POST `/billing/webhooks/sslcommerz`
Handle SSLCommerz IPN notifications.

## Payment Providers

### SSLCommerz Integration

SSLCommerz is the primary payment gateway for Bangladesh customers.

**Configuration:**
```python
SSLCOMMERZ_CONFIG = {
    "store_id": "your_store_id",
    "store_password": "your_store_password",
    "sandbox": True,  # False for production
    "success_url": "https://app.com/payment/success",
    "fail_url": "https://app.com/payment/failed",
    "cancel_url": "https://app.com/payment/cancelled"
}
```

**Features:**
- Local payment methods (bKash, Rocket, Nagad)
- Credit/debit cards
- Internet banking
- Real-time payment notifications

### Stripe Integration

Stripe handles international payments and provides advanced features.

**Configuration:**
```python
STRIPE_CONFIG = {
    "api_key": "sk_live_...",
    "publishable_key": "pk_live_...",
    "webhook_secret": "whsec_..."
}
```

**Features:**
- International credit/debit cards
- Digital wallets (Apple Pay, Google Pay)
- Subscription management
- Advanced analytics

## Quota Enforcement

### Middleware Implementation

The quota enforcement middleware automatically checks usage limits before processing validation requests.

**Monitored Endpoints:**
- `/sessions/*/process` → `per_check` action
- `/sessions/*/import-draft` → `import_draft` action
- `/sessions/*/import-bundle` → `import_bundle` action

**Flow:**
1. Extract company from authenticated user
2. Check current quota usage
3. Allow or deny request based on limits
4. Record usage after successful operation

### Manual Quota Checks

For custom implementations:

```python
from app.middleware.quota_middleware import requires_quota, check_quota_manually

# Using decorator
@requires_quota(BillingAction.PER_CHECK.value)
def validate_document(current_user: User = Depends(get_current_user)):
    # Endpoint logic here
    pass

# Manual check
if not check_quota_manually(company_id, "per_check"):
    raise HTTPException(status_code=429, detail="Quota exceeded")
```

### Error Response

When quota is exceeded:
```json
{
  "detail": "Quota limit exceeded",
  "error_code": "QUOTA_EXCEEDED",
  "action": "per_check",
  "quota_info": {
    "used": 100,
    "limit": 100,
    "remaining": 0,
    "percentage_used": 100
  },
  "company": {
    "id": "uuid",
    "name": "Company Name",
    "plan": "STARTER"
  },
  "upgrade_info": {
    "message": "Consider upgrading your plan to increase quota limits",
    "contact_email": "billing@lcopilot.com"
  }
}
```

## Webhook Integration

### Security

All webhooks are verified using provider-specific methods:

**Stripe:** HMAC-SHA256 signature verification
**SSLCommerz:** Store ID validation and optional API verification

### Event Processing

1. Verify webhook authenticity
2. Parse event data
3. Update invoice status
4. Send confirmation emails
5. Update company billing status

### Common Webhook Events

**Payment Succeeded:**
- Mark invoice as paid
- Update payment method
- Record transaction ID
- Send receipt email

**Payment Failed:**
- Mark invoice as failed
- Notify billing contact
- Suspend service if overdue

## Admin Features

### Company Management

Administrators can:
- View all company statistics
- Change company plans
- Adjust quota limits
- Generate manual invoices
- Process refunds

### Analytics and Reporting

#### GET `/billing/admin/companies`
List all companies with usage statistics.

#### GET `/billing/admin/usage-report`
Generate usage reports for specified periods.

**Response includes:**
- Total companies served
- Total validations processed
- Revenue by period
- Top customers by usage
- Plan distribution

### Bulk Operations

```python
# Change multiple companies to new plan
billing_service.bulk_plan_change(
    company_ids=[uuid1, uuid2, uuid3],
    new_plan=PlanType.PROFESSIONAL,
    effective_date=date.today()
)

# Generate invoices for all companies
billing_service.bulk_invoice_generation(
    period_start=date(2024, 1, 1),
    period_end=date(2024, 1, 31)
)
```

## Testing

### Running Tests

```bash
# Run all billing tests
pytest tests/test_billing_endpoints.py -v

# Run specific test class
pytest tests/test_billing_endpoints.py::TestCompanyBillingEndpoints -v

# Run with coverage
pytest tests/test_billing_endpoints.py --cov=app.services.billing_service
```

### Test Coverage

Tests cover:
- ✅ Company billing management
- ✅ Usage tracking and statistics
- ✅ Invoice generation and management
- ✅ Payment processing (mocked)
- ✅ Quota enforcement
- ✅ Webhook handling
- ✅ Admin functionality
- ✅ Error scenarios

### Mock Services

Tests use comprehensive mocks for:
- Database operations
- Payment provider APIs
- Authentication/authorization
- External service calls

## Deployment

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname

# SSLCommerz
SSLCOMMERZ_STORE_ID=your_store_id
SSLCOMMERZ_STORE_PASSWORD=your_store_password
SSLCOMMERZ_SANDBOX=false

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Application
FRONTEND_URL=https://app.lcopilot.com
API_BASE_URL=https://api.lcopilot.com
```

### Database Migrations

```bash
# Run billing system migrations
alembic upgrade head

# Or specifically run billing migration
alembic upgrade 20250916_170000  # billing system migration
```

### Production Configuration

1. **Enable SSL/HTTPS** for all payment endpoints
2. **Set up monitoring** for payment failures
3. **Configure email notifications** for billing events
4. **Set up backup payment provider** for redundancy
5. **Enable audit logging** for compliance

### Monitoring and Alerts

Key metrics to monitor:
- Payment success rates
- Quota utilization per company
- Invoice generation errors
- Webhook processing failures
- API endpoint response times

### Health Checks

```bash
# Check billing service health
curl https://api.lcopilot.com/billing/company

# Check payment provider connectivity
curl https://api.lcopilot.com/health/ready
```

## Security Considerations

1. **PCI Compliance:** Payment data is handled by certified providers
2. **Data Encryption:** All sensitive data encrypted at rest
3. **API Authentication:** All endpoints require valid JWT tokens
4. **Role-Based Access:** Admin functions restricted to admin users
5. **Webhook Security:** All webhooks verified with signatures
6. **Rate Limiting:** Prevent abuse of billing endpoints

## Support and Troubleshooting

### Common Issues

**Quota Not Enforced:**
- Check middleware is properly configured
- Verify company has quota limits set
- Review middleware endpoint patterns

**Payment Failures:**
- Verify webhook endpoints are accessible
- Check payment provider configuration
- Review webhook signature verification

**Invoice Generation Errors:**
- Ensure usage records exist for period
- Check company billing settings
- Verify line item calculations

### Log Analysis

```bash
# Check billing service logs
grep "billing_service" /var/log/lcopilot/app.log

# Monitor payment processing
grep "payment" /var/log/lcopilot/app.log | grep ERROR

# Review quota enforcement
grep "quota" /var/log/lcopilot/app.log
```

### Contact Information

- **Technical Support:** tech@lcopilot.com
- **Billing Support:** billing@lcopilot.com
- **Emergency Contact:** +880-XXX-XXXXX

---

*Last Updated: January 2025*
*Version: 1.0.0*