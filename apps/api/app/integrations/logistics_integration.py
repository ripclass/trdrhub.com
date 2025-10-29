"""
Logistics integration service for shipping, tracking, and delivery management.
Supports major logistics providers (DHL, FedEx, UPS, Maersk) with real-time tracking.
"""

import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal
import logging

import httpx
from sqlalchemy.orm import Session

from ..models.integrations import (
    IntegrationSubmission, CompanyIntegration, BillingEventType
)
from ..models import ValidationSession, User, UserRole
from ..schemas.integrations import (
    LogisticsSubmissionRequest, SubmissionResponse
)
from ..core.integration_auth import auth_manager
from ..middleware.billing_checkpoint import billing_guard
from ..config import settings

logger = logging.getLogger(__name__)


class LogisticsIntegrationService:
    """Service for logistics provider API integrations."""

    def __init__(self, db: Session):
        self.db = db
        self.timeout = 30.0
        self.max_retries = 3

    async def request_shipping_quote(
        self,
        session_id: str,
        user: User,
        submission_request: LogisticsSubmissionRequest,
        integration_id: str
    ) -> SubmissionResponse:
        """
        Request shipping quote from logistics provider.
        Enforces billing checkpoint for logistics quotes.
        """
        # Verify user permissions (SME users only)
        if user.role not in [UserRole.EXPORTER, UserRole.IMPORTER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Exporter or importer role required for logistics quotes"
            )

        # Get validation session
        session = self.db.query(ValidationSession).filter(
            ValidationSession.id == session_id
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation session not found"
            )

        # Get company integration
        company_integration = self.db.query(CompanyIntegration).filter(
            CompanyIntegration.company_id == user.company_id,
            CompanyIntegration.integration_id == integration_id,
            CompanyIntegration.is_enabled == True
        ).first()

        if not company_integration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Logistics integration not configured for company"
            )

        # Validate country support
        origin_country = submission_request.origin_country
        destination_country = submission_request.destination_country
        supported_countries = company_integration.integration.supported_countries or []

        if supported_countries:
            if origin_country not in supported_countries or destination_country not in supported_countries:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Route {origin_country}->{destination_country} not supported"
                )

        # Create submission record
        submission = IntegrationSubmission(
            id=uuid.uuid4(),
            session_id=session_id,
            integration_id=integration_id,
            company_id=user.company_id,
            user_id=user.id,
            submission_type='logistics_quote',
            idempotency_key=submission_request.idempotency_key,
            request_payload=submission_request.dict(),
            submitted_at=datetime.utcnow()
        )

        self.db.add(submission)
        self.db.commit()

        try:
            # Prepare shipment data
            shipment_data = await self._prepare_shipment_data(session, submission_request)

            # Submit to logistics API
            response_data = await self._call_logistics_api(
                company_integration,
                submission,
                shipment_data,
                'quote'
            )

            # Update submission with response
            submission.mark_completed(
                status_code=200,
                response_payload=response_data,
                external_reference_id=response_data.get('quote_id')
            )

            # Set state for billing middleware
            request.state.integration_id = integration_id
            request.state.submission_id = str(submission.id)

            self.db.commit()

            return SubmissionResponse.from_orm(submission)

        except Exception as e:
            # Mark submission as failed
            submission.mark_completed(
                status_code=500,
                error_message=str(e)
            )

            # Schedule retry if appropriate
            if self._should_retry(e):
                submission.schedule_retry()

            self.db.commit()
            raise

    async def create_shipment(
        self,
        session_id: str,
        user: User,
        shipment_data: Dict[str, Any],
        integration_id: str
    ) -> SubmissionResponse:
        """Create actual shipment with logistics provider."""
        # Similar structure to quote but for actual shipping
        company_integration = self.db.query(CompanyIntegration).filter(
            CompanyIntegration.company_id == user.company_id,
            CompanyIntegration.integration_id == integration_id,
            CompanyIntegration.is_enabled == True
        ).first()

        if not company_integration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Logistics integration not configured"
            )

        # Create submission record
        submission = IntegrationSubmission(
            id=uuid.uuid4(),
            session_id=session_id,
            integration_id=integration_id,
            company_id=user.company_id,
            user_id=user.id,
            submission_type='logistics_shipment',
            idempotency_key=auth_manager.generate_idempotency_key(session_id, integration_id),
            request_payload=shipment_data,
            submitted_at=datetime.utcnow()
        )

        self.db.add(submission)
        self.db.commit()

        try:
            # Submit to logistics API
            response_data = await self._call_logistics_api(
                company_integration,
                submission,
                shipment_data,
                'create_shipment'
            )

            # Update submission with response
            submission.mark_completed(
                status_code=200,
                response_payload=response_data,
                external_reference_id=response_data.get('tracking_number')
            )

            self.db.commit()
            return SubmissionResponse.from_orm(submission)

        except Exception as e:
            submission.mark_completed(status_code=500, error_message=str(e))
            self.db.commit()
            raise

    async def track_shipment(
        self,
        tracking_number: str,
        user: User,
        integration_id: str
    ) -> Dict[str, Any]:
        """Track shipment using tracking number."""
        company_integration = self.db.query(CompanyIntegration).filter(
            CompanyIntegration.company_id == user.company_id,
            CompanyIntegration.integration_id == integration_id
        ).first()

        if not company_integration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Logistics integration not configured"
            )

        # Query logistics API for tracking
        api_url = company_integration.integration.get_api_url(
            use_sandbox=settings.USE_SANDBOX
        )

        headers = await auth_manager.get_oauth2_headers(company_integration)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{api_url}/tracking/{tracking_number}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def schedule_pickup(
        self,
        pickup_data: Dict[str, Any],
        user: User,
        integration_id: str
    ) -> Dict[str, Any]:
        """Schedule pickup with logistics provider."""
        company_integration = self.db.query(CompanyIntegration).filter(
            CompanyIntegration.company_id == user.company_id,
            CompanyIntegration.integration_id == integration_id
        ).first()

        if not company_integration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Logistics integration not configured"
            )

        api_url = company_integration.integration.get_api_url(
            use_sandbox=settings.USE_SANDBOX
        )

        headers = await auth_manager.get_oauth2_headers(company_integration)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{api_url}/pickup/schedule",
                json=pickup_data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def get_service_points(
        self,
        country_code: str,
        city: str,
        user: User,
        integration_id: str
    ) -> List[Dict[str, Any]]:
        """Get available service points (drop-off locations)."""
        company_integration = self.db.query(CompanyIntegration).filter(
            CompanyIntegration.company_id == user.company_id,
            CompanyIntegration.integration_id == integration_id
        ).first()

        if not company_integration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Logistics integration not configured"
            )

        api_url = company_integration.integration.get_api_url(
            use_sandbox=settings.USE_SANDBOX
        )

        headers = await auth_manager.get_oauth2_headers(company_integration)

        params = {
            'country_code': country_code,
            'city': city,
            'service_type': 'drop_off'
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{api_url}/service-points",
                params=params,
                headers=headers
            )
            response.raise_for_status()
            return response.json().get('service_points', [])

    async def _prepare_shipment_data(
        self,
        session: ValidationSession,
        request: LogisticsSubmissionRequest
    ) -> Dict[str, Any]:
        """Prepare shipment data from validation session."""
        # Extract LC and trade data from session
        lc_data = session.validation_results.get('lc_data', {})
        trade_data = session.validation_results.get('trade_data', {})

        # Map to logistics provider format
        shipment_data = {
            'service_type': request.service_type,
            'origin': {
                'country_code': request.origin_country,
                'address': {
                    'name': lc_data.get('applicant', {}).get('name', ''),
                    'company': lc_data.get('applicant', {}).get('company', ''),
                    'address_line_1': lc_data.get('applicant', {}).get('address', ''),
                    'city': trade_data.get('origin_city', ''),
                    'postal_code': trade_data.get('origin_postal_code', ''),
                    'country_code': request.origin_country
                },
                'contact': {
                    'name': lc_data.get('applicant', {}).get('contact_person', ''),
                    'phone': lc_data.get('applicant', {}).get('phone', ''),
                    'email': lc_data.get('applicant', {}).get('email', '')
                }
            },
            'destination': {
                'country_code': request.destination_country,
                'address': {
                    'name': lc_data.get('beneficiary', {}).get('name', ''),
                    'company': lc_data.get('beneficiary', {}).get('company', ''),
                    'address_line_1': lc_data.get('beneficiary', {}).get('address', ''),
                    'city': trade_data.get('destination_city', ''),
                    'postal_code': trade_data.get('destination_postal_code', ''),
                    'country_code': request.destination_country
                },
                'contact': {
                    'name': lc_data.get('beneficiary', {}).get('contact_person', ''),
                    'phone': lc_data.get('beneficiary', {}).get('phone', ''),
                    'email': lc_data.get('beneficiary', {}).get('email', '')
                }
            },
            'packages': [
                {
                    'weight': trade_data.get('gross_weight', 1.0),
                    'weight_unit': 'kg',
                    'dimensions': {
                        'length': trade_data.get('package_length', 10),
                        'width': trade_data.get('package_width', 10),
                        'height': trade_data.get('package_height', 10),
                        'unit': 'cm'
                    },
                    'description': lc_data.get('description_of_goods', ''),
                    'value': float(request.shipment_value or lc_data.get('amount', 0)),
                    'currency': lc_data.get('currency', 'USD')
                }
            ],
            'shipping_options': {
                'service_level': trade_data.get('service_level', 'standard'),
                'insurance': trade_data.get('insurance_required', False),
                'signature_required': trade_data.get('signature_required', False),
                'delivery_confirmation': True
            },
            'customs_info': {
                'contents_type': 'merchandise',
                'customs_invoice': True,
                'eel_pfc': trade_data.get('eel_pfc', ''),
                'customs_certify': True,
                'customs_signer': lc_data.get('applicant', {}).get('name', ''),
                'restriction_type': 'none',
                'restriction_comments': ''
            },
            'references': {
                'lc_number': lc_data.get('lc_number', ''),
                'purchase_order': trade_data.get('purchase_order', ''),
                'invoice_number': trade_data.get('invoice_number', ''),
                'customer_reference': trade_data.get('customer_reference', '')
            },
            'metadata': {
                'lcopilot_session_id': str(session.id),
                'submission_timestamp': datetime.utcnow().isoformat(),
                'system_version': settings.API_VERSION
            }
        }

        return shipment_data

    async def _call_logistics_api(
        self,
        company_integration: CompanyIntegration,
        submission: IntegrationSubmission,
        shipment_data: Dict[str, Any],
        operation: str
    ) -> Dict[str, Any]:
        """Make API call to logistics provider."""
        api_url = company_integration.integration.get_api_url(
            use_sandbox=settings.USE_SANDBOX
        )

        # Get authentication headers
        headers = await auth_manager.get_oauth2_headers(company_integration)

        # Determine endpoint based on operation
        endpoint_map = {
            'quote': '/quotes',
            'create_shipment': '/shipments',
            'track': '/tracking',
            'pickup': '/pickup'
        }

        endpoint = endpoint_map.get(operation, '/quotes')

        # Prepare request payload
        payload = {
            'reference_id': str(submission.id),
            'operation': operation,
            'data': shipment_data,
            'callback_url': submission.request_payload.get('callback_url'),
            'options': {
                'currency_preference': 'USD',
                'include_transit_times': True,
                'include_carbon_footprint': True
            },
            'metadata': {
                'lcopilot_submission_id': str(submission.id),
                'submitted_at': submission.submitted_at.isoformat()
            }
        }

        # Make API call with retries
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{api_url}{endpoint}",
                        json=payload,
                        headers=headers
                    )

                    if response.status_code == 429:  # Rate limited
                        retry_after = int(response.headers.get('Retry-After', 60))
                        await asyncio.sleep(retry_after)
                        continue

                    response.raise_for_status()
                    return response.json()

            except httpx.TimeoutException:
                if attempt == self.max_retries - 1:
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail="Logistics API timeout"
                    )
                await asyncio.sleep(2 ** attempt)

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Logistics API error: {e.response.text}"
                )

    def _should_retry(self, error: Exception) -> bool:
        """Determine if submission should be retried."""
        if isinstance(error, httpx.TimeoutException):
            return True
        if isinstance(error, httpx.HTTPStatusError):
            return 500 <= error.response.status_code < 600
        return False

    async def get_submission_history(
        self,
        user: User,
        integration_id: str,
        limit: int = 50
    ) -> List[SubmissionResponse]:
        """Get submission history for logistics user."""
        submissions = self.db.query(IntegrationSubmission).filter(
            IntegrationSubmission.company_id == user.company_id,
            IntegrationSubmission.integration_id == integration_id,
            IntegrationSubmission.submission_type.like('logistics_%')
        ).order_by(
            IntegrationSubmission.submitted_at.desc()
        ).limit(limit).all()

        return [SubmissionResponse.from_orm(sub) for sub in submissions]

    async def handle_webhook(
        self,
        integration_id: str,
        webhook_data: Dict[str, Any],
        signature: str
    ) -> Dict[str, Any]:
        """Handle webhook from logistics API."""
        # Verify webhook signature
        integration = self.db.query(Integration).filter(
            Integration.id == integration_id
        ).first()

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )

        webhook_secret = integration.webhook_secret
        if not auth_manager.verify_webhook_signature(
            payload=str(webhook_data).encode(),
            signature=signature,
            secret=webhook_secret
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )

        # Process webhook event
        event_type = webhook_data.get('event_type')
        tracking_number = webhook_data.get('tracking_number')

        if event_type == 'shipment_created':
            await self._handle_shipment_created(tracking_number, webhook_data)
        elif event_type == 'shipment_in_transit':
            await self._handle_shipment_in_transit(tracking_number, webhook_data)
        elif event_type == 'shipment_delivered':
            await self._handle_shipment_delivered(tracking_number, webhook_data)
        elif event_type == 'shipment_exception':
            await self._handle_shipment_exception(tracking_number, webhook_data)

        return {'received': True, 'processed': True}

    async def _handle_shipment_created(
        self,
        tracking_number: str,
        webhook_data: Dict[str, Any]
    ) -> None:
        """Handle shipment creation webhook."""
        submission = self.db.query(IntegrationSubmission).filter(
            IntegrationSubmission.external_reference_id == tracking_number
        ).first()

        if submission:
            # Update submission with tracking details
            submission.response_payload = webhook_data
            submission.completed_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Shipment created for submission {submission.id}, tracking: {tracking_number}")

    async def _handle_shipment_in_transit(
        self,
        tracking_number: str,
        webhook_data: Dict[str, Any]
    ) -> None:
        """Handle shipment in transit webhook."""
        submission = self.db.query(IntegrationSubmission).filter(
            IntegrationSubmission.external_reference_id == tracking_number
        ).first()

        if submission:
            # Update submission with transit details
            if not submission.response_payload:
                submission.response_payload = {}
            submission.response_payload['tracking_updates'] = webhook_data
            self.db.commit()

            logger.info(f"Shipment in transit for tracking: {tracking_number}")

    async def _handle_shipment_delivered(
        self,
        tracking_number: str,
        webhook_data: Dict[str, Any]
    ) -> None:
        """Handle shipment delivered webhook."""
        submission = self.db.query(IntegrationSubmission).filter(
            IntegrationSubmission.external_reference_id == tracking_number
        ).first()

        if submission:
            # Update submission with delivery confirmation
            if not submission.response_payload:
                submission.response_payload = {}
            submission.response_payload['delivery_status'] = 'delivered'
            submission.response_payload['delivery_data'] = webhook_data
            self.db.commit()

            logger.info(f"Shipment delivered for tracking: {tracking_number}")

    async def _handle_shipment_exception(
        self,
        tracking_number: str,
        webhook_data: Dict[str, Any]
    ) -> None:
        """Handle shipment exception webhook."""
        submission = self.db.query(IntegrationSubmission).filter(
            IntegrationSubmission.external_reference_id == tracking_number
        ).first()

        if submission:
            # Update submission with exception details
            if not submission.response_payload:
                submission.response_payload = {}
            submission.response_payload['exception'] = webhook_data
            self.db.commit()

            logger.warning(f"Shipment exception for tracking: {tracking_number}")


# Standalone functions for API routes
async def request_logistics_quote(
    session_id: str,
    request: LogisticsSubmissionRequest,
    user: User,
    integration_id: str,
    db: Session
) -> SubmissionResponse:
    """Route handler for logistics quote request."""
    service = LogisticsIntegrationService(db)
    return await service.request_shipping_quote(session_id, user, request, integration_id)


async def track_logistics_shipment(
    tracking_number: str,
    user: User,
    integration_id: str,
    db: Session
) -> Dict[str, Any]:
    """Route handler for shipment tracking."""
    service = LogisticsIntegrationService(db)
    return await service.track_shipment(tracking_number, user, integration_id)


async def schedule_logistics_pickup(
    pickup_data: Dict[str, Any],
    user: User,
    integration_id: str,
    db: Session
) -> Dict[str, Any]:
    """Route handler for pickup scheduling."""
    service = LogisticsIntegrationService(db)
    return await service.schedule_pickup(pickup_data, user, integration_id)