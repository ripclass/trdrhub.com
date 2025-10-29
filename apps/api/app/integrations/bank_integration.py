"""
Bank integration service for LC validation and recheck operations.
Supports SWIFT MT700/707 formats and ISO20022 messaging.
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
    BankSubmissionRequest, SubmissionResponse, SwiftMT700, SwiftMT707
)
from ..core.integration_auth import auth_manager
from ..middleware.billing_checkpoint import billing_guard
from ..config import settings

logger = logging.getLogger(__name__)


class BankIntegrationService:
    """Service for bank API integrations with SWIFT/ISO20022 support."""

    def __init__(self, db: Session):
        self.db = db
        self.timeout = 30.0
        self.max_retries = 3

    async def submit_lc_validation(
        self,
        session_id: str,
        user: User,
        submission_request: BankSubmissionRequest,
        integration_id: str
    ) -> SubmissionResponse:
        """
        Submit LC validation request to bank API.
        Enforces billing checkpoint for bank recheck operations.
        """
        # Verify user permissions
        if user.role != UserRole.BANK:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bank role required for LC validation submissions"
            )

        # Enforce billing guard - prevents reuse without billing
        billing_guard.enforce_bank_recheck(session_id, user, self.db)

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
                detail="Bank integration not configured for company"
            )

        # Create submission record
        submission = IntegrationSubmission(
            id=uuid.uuid4(),
            session_id=session_id,
            integration_id=integration_id,
            company_id=user.company_id,
            user_id=user.id,
            submission_type='bank_validation',
            idempotency_key=submission_request.idempotency_key,
            request_payload=submission_request.dict(),
            submitted_at=datetime.utcnow()
        )

        self.db.add(submission)
        self.db.commit()

        try:
            # Prepare SWIFT message
            swift_message = await self._prepare_swift_message(session, submission_request)

            # Submit to bank API
            response_data = await self._call_bank_api(
                company_integration,
                submission,
                swift_message
            )

            # Update submission with response
            submission.mark_completed(
                status_code=200,
                response_payload=response_data,
                external_reference_id=response_data.get('reference_id')
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

    async def submit_lc_amendment(
        self,
        session_id: str,
        user: User,
        amendment_data: Dict[str, Any],
        integration_id: str
    ) -> SubmissionResponse:
        """Submit LC amendment using SWIFT MT707 format."""
        # Similar structure to validation but for amendments
        # Generate MT707 message
        mt707_message = await self._prepare_mt707_message(amendment_data)

        # Process through bank API
        # Implementation similar to submit_lc_validation
        pass

    async def query_lc_status(
        self,
        lc_number: str,
        user: User,
        integration_id: str
    ) -> Dict[str, Any]:
        """Query LC status from bank API."""
        company_integration = self.db.query(CompanyIntegration).filter(
            CompanyIntegration.company_id == user.company_id,
            CompanyIntegration.integration_id == integration_id
        ).first()

        if not company_integration:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bank integration not configured"
            )

        # Query bank API for LC status
        api_url = company_integration.integration.get_api_url(
            use_sandbox=settings.USE_SANDBOX
        )

        headers = await auth_manager.get_oauth2_headers(company_integration)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{api_url}/lc/{lc_number}/status",
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def _prepare_swift_message(
        self,
        session: ValidationSession,
        request: BankSubmissionRequest
    ) -> SwiftMT700:
        """Prepare SWIFT MT700 message from validation session data."""
        # Extract LC data from session
        lc_data = session.validation_results.get('lc_data', {})

        return SwiftMT700(
            sender_bic=request.request_payload.get('sender_bic'),
            receiver_bic=request.request_payload.get('receiver_bic'),
            lc_number=request.lc_number,
            issue_date=datetime.fromisoformat(lc_data.get('issue_date')),
            expiry_date=datetime.fromisoformat(lc_data.get('expiry_date')),
            applicant=lc_data.get('applicant', {}),
            beneficiary=lc_data.get('beneficiary', {}),
            amount=Decimal(str(lc_data.get('amount', 0))),
            currency=lc_data.get('currency', 'USD'),
            description_of_goods=lc_data.get('description_of_goods', ''),
            documents_required=lc_data.get('documents_required', []),
            latest_shipment_date=lc_data.get('latest_shipment_date'),
            partial_shipments=lc_data.get('partial_shipments', False),
            transhipment=lc_data.get('transhipment', False)
        )

    async def _prepare_mt707_message(self, amendment_data: Dict[str, Any]) -> SwiftMT707:
        """Prepare SWIFT MT707 amendment message."""
        return SwiftMT707(
            sender_bic=amendment_data['sender_bic'],
            receiver_bic=amendment_data['receiver_bic'],
            lc_number=amendment_data['lc_number'],
            amendment_number=amendment_data['amendment_number'],
            amendment_date=datetime.utcnow(),
            amendments=amendment_data['amendments']
        )

    async def _call_bank_api(
        self,
        company_integration: CompanyIntegration,
        submission: IntegrationSubmission,
        swift_message: SwiftMT700
    ) -> Dict[str, Any]:
        """Make API call to bank system."""
        api_url = company_integration.integration.get_api_url(
            use_sandbox=settings.USE_SANDBOX
        )

        # Get authentication headers
        if company_integration.integration.requires_mtls:
            ssl_context = auth_manager.create_mtls_context(company_integration)
        else:
            ssl_context = None

        headers = await auth_manager.get_oauth2_headers(company_integration)

        # Prepare request payload
        payload = {
            'message_type': 'MT700',
            'reference_id': str(submission.id),
            'priority': submission.request_payload.get('priority', 'normal'),
            'swift_message': swift_message.dict(),
            'callback_url': submission.request_payload.get('callback_url'),
            'metadata': {
                'lcopilot_session_id': str(submission.session_id),
                'submitted_at': submission.submitted_at.isoformat()
            }
        }

        # Make API call with retries
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    verify=ssl_context
                ) as client:
                    response = await client.post(
                        f"{api_url}/lc/validate",
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
                        detail="Bank API timeout"
                    )
                await asyncio.sleep(2 ** attempt)

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Bank API error: {e.response.text}"
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
        """Get submission history for bank user."""
        submissions = self.db.query(IntegrationSubmission).filter(
            IntegrationSubmission.company_id == user.company_id,
            IntegrationSubmission.integration_id == integration_id,
            IntegrationSubmission.submission_type.like('bank_%')
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
        """Handle webhook from bank API."""
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

        if event_type == 'lc_validation_complete':
            await self._handle_validation_complete(reference_id, webhook_data)
        elif event_type == 'lc_amendment_processed':
            await self._handle_amendment_processed(reference_id, webhook_data)

        return {'received': True, 'processed': True}

    async def _handle_validation_complete(
        self,
        reference_id: str,
        webhook_data: Dict[str, Any]
    ) -> None:
        """Handle LC validation completion webhook."""
        submission = self.db.query(IntegrationSubmission).filter(
            IntegrationSubmission.external_reference_id == reference_id
        ).first()

        if submission:
            # Update submission with final results
            submission.response_payload = webhook_data
            submission.completed_at = datetime.utcnow()
            self.db.commit()

            # Notify user/system of completion
            logger.info(f"LC validation completed for submission {submission.id}")

    async def _handle_amendment_processed(
        self,
        reference_id: str,
        webhook_data: Dict[str, Any]
    ) -> None:
        """Handle LC amendment processing webhook."""
        # Similar to validation complete
        pass


# Standalone functions for API routes
async def submit_bank_validation(
    session_id: str,
    request: BankSubmissionRequest,
    user: User,
    integration_id: str,
    db: Session
) -> SubmissionResponse:
    """Route handler for bank validation submission."""
    service = BankIntegrationService(db)
    return await service.submit_lc_validation(session_id, user, request, integration_id)


async def query_bank_lc_status(
    lc_number: str,
    user: User,
    integration_id: str,
    db: Session
) -> Dict[str, Any]:
    """Route handler for LC status query."""
    service = BankIntegrationService(db)
    return await service.query_lc_status(lc_number, user, integration_id)