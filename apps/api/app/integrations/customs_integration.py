"""
Customs integration service for trade document validation and submission.
Supports automated customs declaration processing and compliance checks.
"""

import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

import httpx
from sqlalchemy.orm import Session

from ..models.integrations import (
    IntegrationSubmission, CompanyIntegration, BillingEventType
)
from ..models import ValidationSession, User, UserRole
from ..schemas.integrations import (
    CustomsSubmissionRequest, SubmissionResponse
)
from ..core.integration_auth import auth_manager
from ..middleware.billing_checkpoint import billing_guard
from ..config import settings

logger = logging.getLogger(__name__)


class CustomsIntegrationService:
    """Service for customs authority API integrations."""

    def __init__(self, db: Session):
        self.db = db
        self.timeout = 45.0  # Customs APIs can be slower
        self.max_retries = 3

    async def submit_customs_declaration(
        self,
        session_id: str,
        user: User,
        submission_request: CustomsSubmissionRequest,
        integration_id: str
    ) -> SubmissionResponse:
        """
        Submit customs declaration to government API.
        Enforces billing checkpoint for customs submissions.
        """
        # Verify user permissions (SME users only)
        if user.role not in [UserRole.EXPORTER, UserRole.IMPORTER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Exporter or importer role required for customs submissions"
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
                detail="Customs integration not configured for company"
            )

        # Validate country support
        country_code = submission_request.country_code
        supported_countries = company_integration.integration.supported_countries or []
        if supported_countries and country_code not in supported_countries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Country {country_code} not supported by this integration"
            )

        # Create submission record
        submission = IntegrationSubmission(
            id=uuid.uuid4(),
            session_id=session_id,
            integration_id=integration_id,
            company_id=user.company_id,
            user_id=user.id,
            submission_type='customs_declaration',
            idempotency_key=submission_request.idempotency_key,
            request_payload=submission_request.dict(),
            submitted_at=datetime.utcnow()
        )

        self.db.add(submission)
        self.db.commit()

        try:
            # Prepare customs declaration data
            declaration_data = await self._prepare_customs_declaration(session, submission_request)

            # Submit to customs API
            response_data = await self._call_customs_api(
                company_integration,
                submission,
                declaration_data
            )

            # Update submission with response
            submission.mark_completed(
                status_code=200,
                response_payload=response_data,
                external_reference_id=response_data.get('declaration_number')
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

    async def query_declaration_status(
        self,
        declaration_number: str,
        user: User,
        integration_id: str
    ) -> Dict[str, Any]:
        """Query customs declaration status."""
        company_integration = self.db.query(CompanyIntegration).filter(
            CompanyIntegration.company_id == user.company_id,
            CompanyIntegration.integration_id == integration_id
        ).first()

        if not company_integration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customs integration not configured"
            )

        # Query customs API for declaration status
        api_url = company_integration.integration.get_api_url(
            use_sandbox=settings.USE_SANDBOX
        )

        headers = await auth_manager.get_oauth2_headers(company_integration)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{api_url}/declarations/{declaration_number}/status",
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def get_tariff_classification(
        self,
        product_description: str,
        country_code: str,
        user: User,
        integration_id: str
    ) -> Dict[str, Any]:
        """Get HS code classification for products."""
        company_integration = self.db.query(CompanyIntegration).filter(
            CompanyIntegration.company_id == user.company_id,
            CompanyIntegration.integration_id == integration_id
        ).first()

        if not company_integration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customs integration not configured"
            )

        api_url = company_integration.integration.get_api_url(
            use_sandbox=settings.USE_SANDBOX
        )

        headers = await auth_manager.get_oauth2_headers(company_integration)

        payload = {
            'product_description': product_description,
            'country_code': country_code,
            'language': 'en'
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{api_url}/classification/hs-code",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def calculate_duties_taxes(
        self,
        commodity_codes: List[str],
        values: List[float],
        origin_country: str,
        destination_country: str,
        user: User,
        integration_id: str
    ) -> Dict[str, Any]:
        """Calculate customs duties and taxes."""
        company_integration = self.db.query(CompanyIntegration).filter(
            CompanyIntegration.company_id == user.company_id,
            CompanyIntegration.integration_id == integration_id
        ).first()

        if not company_integration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customs integration not configured"
            )

        api_url = company_integration.integration.get_api_url(
            use_sandbox=settings.USE_SANDBOX
        )

        headers = await auth_manager.get_oauth2_headers(company_integration)

        payload = {
            'items': [
                {
                    'hs_code': code,
                    'value': value,
                    'currency': 'USD'
                }
                for code, value in zip(commodity_codes, values)
            ],
            'origin_country': origin_country,
            'destination_country': destination_country,
            'trade_agreement': 'auto_detect'
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{api_url}/duties/calculate",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def _prepare_customs_declaration(
        self,
        session: ValidationSession,
        request: CustomsSubmissionRequest
    ) -> Dict[str, Any]:
        """Prepare customs declaration from validation session data."""
        # Extract LC and trade data from session
        lc_data = session.validation_results.get('lc_data', {})
        trade_data = session.validation_results.get('trade_data', {})

        # Map LC data to customs declaration format
        declaration = {
            'declaration_type': request.declaration_type,
            'country_code': request.country_code,
            'customs_office': request.customs_office,
            'declarant': {
                'name': lc_data.get('applicant', {}).get('name', ''),
                'address': lc_data.get('applicant', {}).get('address', ''),
                'tin': trade_data.get('declarant_tin', ''),
                'eori': trade_data.get('declarant_eori', '')
            },
            'consignee': {
                'name': lc_data.get('beneficiary', {}).get('name', ''),
                'address': lc_data.get('beneficiary', {}).get('address', ''),
                'country': lc_data.get('beneficiary', {}).get('country', '')
            },
            'goods': [
                {
                    'commodity_code': code,
                    'description': lc_data.get('description_of_goods', ''),
                    'quantity': trade_data.get('quantity', 1),
                    'unit': trade_data.get('unit', 'PCE'),
                    'value': float(lc_data.get('amount', 0)),
                    'currency': lc_data.get('currency', 'USD'),
                    'origin_country': trade_data.get('origin_country', ''),
                    'gross_weight': trade_data.get('gross_weight', 0),
                    'net_weight': trade_data.get('net_weight', 0)
                }
                for code in request.commodity_codes
            ],
            'transport': {
                'mode': trade_data.get('transport_mode', 'sea'),
                'vessel_name': trade_data.get('vessel_name', ''),
                'voyage_number': trade_data.get('voyage_number', ''),
                'loading_port': trade_data.get('loading_port', ''),
                'discharge_port': trade_data.get('discharge_port', '')
            },
            'financial': {
                'invoice_number': trade_data.get('invoice_number', ''),
                'invoice_date': trade_data.get('invoice_date', ''),
                'total_value': float(lc_data.get('amount', 0)),
                'currency': lc_data.get('currency', 'USD'),
                'payment_terms': trade_data.get('payment_terms', 'LC')
            },
            'documents': [
                {
                    'type': 'letter_of_credit',
                    'number': lc_data.get('lc_number', ''),
                    'date': lc_data.get('issue_date', ''),
                    'issuing_bank': lc_data.get('issuing_bank', '')
                }
            ] + [
                {
                    'type': doc_type,
                    'description': doc_type.replace('_', ' ').title()
                }
                for doc_type in lc_data.get('documents_required', [])
            ],
            'metadata': {
                'lcopilot_session_id': str(session.id),
                'submission_timestamp': datetime.utcnow().isoformat(),
                'system_version': settings.API_VERSION
            }
        }

        return declaration

    async def _call_customs_api(
        self,
        company_integration: CompanyIntegration,
        submission: IntegrationSubmission,
        declaration_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make API call to customs system."""
        api_url = company_integration.integration.get_api_url(
            use_sandbox=settings.USE_SANDBOX
        )

        # Get authentication headers
        headers = await auth_manager.get_oauth2_headers(company_integration)

        # Prepare request payload
        payload = {
            'reference_id': str(submission.id),
            'declaration': declaration_data,
            'callback_url': submission.request_payload.get('callback_url'),
            'validation_mode': submission.request_payload.get('validation_mode', 'full'),
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
                        f"{api_url}/declarations/submit",
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
                        detail="Customs API timeout"
                    )
                await asyncio.sleep(2 ** attempt)

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Customs API error: {e.response.text}"
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
        """Get submission history for customs user."""
        submissions = self.db.query(IntegrationSubmission).filter(
            IntegrationSubmission.company_id == user.company_id,
            IntegrationSubmission.integration_id == integration_id,
            IntegrationSubmission.submission_type.like('customs_%')
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
        """Handle webhook from customs API."""
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
        reference_id = webhook_data.get('reference_id')

        if event_type == 'declaration_processed':
            await self._handle_declaration_processed(reference_id, webhook_data)
        elif event_type == 'clearance_granted':
            await self._handle_clearance_granted(reference_id, webhook_data)
        elif event_type == 'examination_required':
            await self._handle_examination_required(reference_id, webhook_data)

        return {'received': True, 'processed': True}

    async def _handle_declaration_processed(
        self,
        reference_id: str,
        webhook_data: Dict[str, Any]
    ) -> None:
        """Handle customs declaration processing webhook."""
        submission = self.db.query(IntegrationSubmission).filter(
            IntegrationSubmission.external_reference_id == reference_id
        ).first()

        if submission:
            # Update submission with processing results
            submission.response_payload = webhook_data
            submission.completed_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Customs declaration processed for submission {submission.id}")

    async def _handle_clearance_granted(
        self,
        reference_id: str,
        webhook_data: Dict[str, Any]
    ) -> None:
        """Handle customs clearance granted webhook."""
        submission = self.db.query(IntegrationSubmission).filter(
            IntegrationSubmission.external_reference_id == reference_id
        ).first()

        if submission:
            # Update submission with clearance results
            if not submission.response_payload:
                submission.response_payload = {}
            submission.response_payload['clearance_status'] = 'granted'
            submission.response_payload['clearance_data'] = webhook_data
            self.db.commit()

            logger.info(f"Customs clearance granted for submission {submission.id}")

    async def _handle_examination_required(
        self,
        reference_id: str,
        webhook_data: Dict[str, Any]
    ) -> None:
        """Handle examination required webhook."""
        submission = self.db.query(IntegrationSubmission).filter(
            IntegrationSubmission.external_reference_id == reference_id
        ).first()

        if submission:
            # Update submission with examination requirements
            if not submission.response_payload:
                submission.response_payload = {}
            submission.response_payload['examination_required'] = True
            submission.response_payload['examination_data'] = webhook_data
            self.db.commit()

            logger.warning(f"Customs examination required for submission {submission.id}")


# Standalone functions for API routes
async def submit_customs_declaration(
    session_id: str,
    request: CustomsSubmissionRequest,
    user: User,
    integration_id: str,
    db: Session
) -> SubmissionResponse:
    """Route handler for customs declaration submission."""
    service = CustomsIntegrationService(db)
    return await service.submit_customs_declaration(session_id, user, request, integration_id)


async def query_customs_declaration_status(
    declaration_number: str,
    user: User,
    integration_id: str,
    db: Session
) -> Dict[str, Any]:
    """Route handler for customs declaration status query."""
    service = CustomsIntegrationService(db)
    return await service.query_declaration_status(declaration_number, user, integration_id)


async def get_customs_tariff_classification(
    product_description: str,
    country_code: str,
    user: User,
    integration_id: str,
    db: Session
) -> Dict[str, Any]:
    """Route handler for HS code classification."""
    service = CustomsIntegrationService(db)
    return await service.get_tariff_classification(product_description, country_code, user, integration_id)