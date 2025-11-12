"""
Billing checkpoint middleware - CRITICAL for business model protection.
Ensures every API submission triggers appropriate billing events.
"""

import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
import logging

from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session

from ..models.integrations import (
    IntegrationSubmission, IntegrationBillingEvent,
    BillingEventType, CompanyIntegration
)
from ..models import User, UserRole
from ..services.billing import BillingService
from ..database import get_db

logger = logging.getLogger(__name__)


class BillingCheckpointMiddleware:
    """
    Critical middleware that enforces billing for all integration usage.
    Prevents revenue leakage and ensures dual billing model protection.
    """

    def __init__(self):
        self.billing_rates = {
            # SME Rates (per validation)
            BillingEventType.SME_VALIDATION: {
                'standard': Decimal('5.00'),
                'premium': Decimal('8.00'),
                'enterprise': Decimal('12.00')
            },
            # Bank Rates (per recheck)
            BillingEventType.BANK_RECHECK: {
                'standard': Decimal('15.00'),
                'premium': Decimal('25.00'),
                'enterprise': Decimal('40.00')
            },
            # Integration-specific rates
            BillingEventType.CUSTOMS_SUBMISSION: {
                'standard': Decimal('10.00'),
                'premium': Decimal('15.00'),
                'enterprise': Decimal('20.00')
            },
            BillingEventType.LOGISTICS_TRACKING: {
                'standard': Decimal('3.00'),
                'premium': Decimal('5.00'),
                'enterprise': Decimal('8.00')
            },
            BillingEventType.FX_QUOTE: {
                'standard': Decimal('2.00'),
                'premium': Decimal('3.00'),
                'enterprise': Decimal('5.00')
            }
        }

    async def __call__(self, request: Request, call_next):
        """Process request and enforce billing checkpoints."""
        # Only apply to integration endpoints
        if not self._is_integration_endpoint(request.url.path):
            return await call_next(request)

        # Extract context
        start_time = time.time()
        db = next(get_db())

        try:
            # Pre-processing: Check quotas and rate limits
            await self._pre_billing_check(request, db)

            # Process request
            response = await call_next(request)

            # Post-processing: Record billing events
            await self._post_billing_record(request, response, db, start_time)

            return response

        except Exception as e:
            # Log billing failures - critical for audit
            logger.error(f"Billing checkpoint failed: {str(e)}", extra={
                'path': request.url.path,
                'method': request.method,
                'user_id': getattr(request.state, 'user_id', None),
                'company_id': getattr(request.state, 'company_id', None)
            })
            raise
        finally:
            db.close()

    def _is_integration_endpoint(self, path: str) -> bool:
        """Check if path is an integration endpoint requiring billing."""
        integration_paths = [
            '/integrations/bank/',
            '/integrations/customs/',
            '/integrations/logistics/',
            '/integrations/fx/',
            '/sessions/',  # Session endpoints that may trigger integrations
        ]
        return any(path.startswith(p) for p in integration_paths)

    async def _pre_billing_check(self, request: Request, db: Session) -> None:
        """Pre-flight checks for quotas and permissions."""
        user = getattr(request.state, 'user', None)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for integration usage"
            )

        # Check company quotas for integration usage
        if hasattr(request.state, 'integration_id'):
            integration_id = request.state.integration_id
            company_integration = db.query(CompanyIntegration).filter(
                CompanyIntegration.company_id == user.company_id,
                CompanyIntegration.integration_id == integration_id,
                CompanyIntegration.is_enabled == True
            ).first()

            if not company_integration:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Integration not enabled for company"
                )

            # Check quota limits
            if not company_integration.has_quota_remaining:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Monthly quota exceeded for integration"
                )

    async def _post_billing_record(self, request: Request, response, db: Session, start_time: float) -> None:
        """Record billing events after successful API calls."""
        # Skip billing for failed requests (4xx/5xx)
        if response.status_code >= 400:
            return

        user = getattr(request.state, 'user', None)
        if not user:
            return

        # Determine billing event type based on user role and endpoint
        event_type = self._determine_billing_event(request, user)
        if not event_type:
            return

        # Get integration context
        integration_id = getattr(request.state, 'integration_id', None)
        submission_id = getattr(request.state, 'submission_id', None)

        if not integration_id:
            logger.warning(f"No integration_id found for billing: {request.url.path}")
            return

        # Get company integration for billing tier
        company_integration = db.query(CompanyIntegration).filter(
            CompanyIntegration.company_id == user.company_id,
            CompanyIntegration.integration_id == integration_id
        ).first()

        if not company_integration:
            logger.error(f"No company integration found for billing: {user.company_id}, {integration_id}")
            return

        # Calculate charge amount
        billing_tier = company_integration.billing_tier
        charge_amount = self._calculate_charge(event_type, billing_tier, company_integration)

        # Create billing event record (IMMUTABLE)
        billing_event = IntegrationBillingEvent(
            id=uuid.uuid4(),
            submission_id=submission_id,
            company_id=user.company_id,
            integration_id=integration_id,
            user_id=user.id,
            event_type=event_type,
            charged_amount=charge_amount,
            currency='USD',  # TODO: Support multi-currency
            billing_tier=billing_tier,
            metadata={
                'endpoint': request.url.path,
                'method': request.method,
                'response_status': response.status_code,
                'processing_time_ms': int((time.time() - start_time) * 1000),
                'ip_address': request.client.host if request.client else None,
                'user_agent': request.headers.get('user-agent'),
                'timestamp': datetime.utcnow().isoformat()
            },
            recorded_at=datetime.utcnow()
        )

        # Save billing event
        db.add(billing_event)

        # Update usage counter
        company_integration.increment_usage()

        # Mark submission as billed if applicable
        if submission_id:
            submission = db.query(IntegrationSubmission).filter(
                IntegrationSubmission.id == submission_id
            ).first()
            if submission:
                submission.billing_recorded = True

        # Commit billing transaction
        try:
            db.commit()

            # Async: Send to billing service for invoice generation
            await self._trigger_invoice_generation(billing_event, db)

            logger.info(f"Billing recorded: {event_type} for {user.company.name} - ${charge_amount}")

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to record billing event: {str(e)}")
            # Don't fail the request, but alert for manual intervention
            await self._alert_billing_failure(billing_event, str(e))

    def _determine_billing_event(self, request: Request, user: User) -> Optional[BillingEventType]:
        """Determine billing event type based on request context."""
        path = request.url.path

        # SME validation events
        if user.role in [UserRole.EXPORTER, UserRole.IMPORTER]:
            if '/sessions/' in path and request.method == 'POST':
                return BillingEventType.SME_VALIDATION
            elif '/integrations/customs/' in path:
                return BillingEventType.CUSTOMS_SUBMISSION
            elif '/integrations/logistics/' in path:
                return BillingEventType.LOGISTICS_TRACKING
            elif '/integrations/fx/' in path:
                return BillingEventType.FX_QUOTE

        # Bank recheck events
        elif user.role == UserRole.BANK:
            if '/integrations/bank/' in path or '/sessions/' in path:
                return BillingEventType.BANK_RECHECK

        return None

    def _calculate_charge(self, event_type: BillingEventType, billing_tier: str,
                         company_integration: CompanyIntegration) -> Decimal:
        """Calculate charge amount for billing event."""
        # Use custom pricing if configured
        if company_integration.price_per_check:
            return company_integration.price_per_check

        # Use standard rates
        rates = self.billing_rates.get(event_type, {})
        return rates.get(billing_tier, rates.get('standard', Decimal('5.00')))

    async def _trigger_invoice_generation(self, billing_event: IntegrationBillingEvent, db: Session) -> None:
        """Trigger async invoice generation for billing event."""
        try:
            billing_service = BillingService(db)
            await billing_service.record_integration_usage(
                company_id=billing_event.company_id,
                event_type=billing_event.event_type,
                amount=billing_event.charged_amount,
                metadata=billing_event.metadata
            )
        except Exception as e:
            logger.error(f"Failed to trigger invoice generation: {str(e)}")
            # Schedule for retry
            await self._schedule_billing_retry(billing_event)

    async def _alert_billing_failure(self, billing_event: IntegrationBillingEvent, error: str) -> None:
        """Alert on billing failures for manual intervention."""
        alert_data = {
            'type': 'billing_failure',
            'severity': 'critical',
            'company_id': str(billing_event.company_id),
            'integration_id': str(billing_event.integration_id),
            'event_type': billing_event.event_type,
            'charge_amount': float(billing_event.charged_amount),
            'error': error,
            'timestamp': datetime.utcnow().isoformat()
        }

        # Send to monitoring system
        # TODO: Integrate with alerting system (PagerDuty, Slack, etc.)
        logger.critical(f"BILLING FAILURE ALERT: {alert_data}")

    async def _schedule_billing_retry(self, billing_event: IntegrationBillingEvent) -> None:
        """Schedule retry for failed billing operations."""
        # TODO: Implement retry queue (Redis, Celery, etc.)
        logger.info(f"Scheduling billing retry for event {billing_event.id}")


class BillingGuard:
    """
    Additional guard to prevent unauthorized integration access.
    Ensures no silent reuse of SME validations by banks.
    """

    @staticmethod
    def enforce_bank_recheck(session_id: str, user: User, db: Session) -> None:
        """Enforce that banks must pay for rechecks, not reuse SME validations."""
        if user.role != UserRole.BANK:
            return

        # Check if this session already has a bank recheck billing event
        existing_bank_billing = db.query(IntegrationBillingEvent).filter(
            IntegrationBillingEvent.user_id == user.id,
            IntegrationBillingEvent.event_type == BillingEventType.BANK_RECHECK,
            IntegrationBillingEvent.metadata['session_id'].astext == session_id
        ).first()

        if not existing_bank_billing:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Bank recheck billing required - cannot reuse SME validation"
            )

    @staticmethod
    def prevent_duplicate_billing(submission_id: str, db: Session) -> None:
        """Prevent duplicate billing for the same submission."""
        existing_billing = db.query(IntegrationBillingEvent).filter(
            IntegrationBillingEvent.submission_id == submission_id
        ).first()

        if existing_billing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Billing already recorded for this submission"
            )


# Global middleware instance
billing_checkpoint = BillingCheckpointMiddleware()
billing_guard = BillingGuard()