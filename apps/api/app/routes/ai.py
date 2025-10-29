from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import Optional
import logging

from app.services.llm_assist import (
    LLMAssistService,
    DiscrepancySummaryRequest,
    BankDraftRequest,
    AmendmentDraftRequest,
    ChatRequest,
    AIResponse
)
from app.models.user import User
from app.core.auth import get_current_user
from app.core.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])
security = HTTPBearer()
logger = logging.getLogger(__name__)

@router.post("/discrepancies", response_model=AIResponse)
async def generate_discrepancy_summary(
    request: DiscrepancySummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate AI-powered discrepancy summary for trade finance documents.

    Features:
    - Multi-modal analysis (text + document images)
    - Confidence scoring with fallback to rule-based system
    - Comprehensive audit logging
    - Multilingual support (EN/BN)

    Business Logic:
    - SME users: Basic discrepancy detection
    - Bank users: Enhanced analysis with regulatory compliance
    - Regulatory users: Full audit trail access
    """
    try:
        llm_service = LLMAssistService(db)
        result = await llm_service.generate_discrepancy_summary(request, current_user)

        logger.info(
            f"Discrepancy summary generated for user {current_user.id}, "
            f"LC {request.lc_id}, confidence: {result.confidence_score}"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to generate discrepancy summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate discrepancy summary"
        )

@router.post("/bank-draft", response_model=AIResponse)
async def generate_bank_draft(
    request: BankDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate bank-style formal discrepancy notifications.

    Features:
    - Professional banking language
    - Regulatory compliance formatting
    - SWIFT MT799 style messaging
    - Multi-currency support

    Access Control:
    - Bank users: Full access
    - SME users: Limited access (basic templates only)
    - Regulatory users: Read-only access for compliance
    """
    try:
        # Access control check
        if current_user.user_type not in ["bank", "regulator"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bank draft generation requires bank or regulator access"
            )

        llm_service = LLMAssistService(db)
        result = await llm_service.generate_bank_draft(request, current_user)

        logger.info(
            f"Bank draft generated for user {current_user.id}, "
            f"LC {request.lc_id}, confidence: {result.confidence_score}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate bank draft: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate bank draft"
        )

@router.post("/amendment-draft", response_model=AIResponse)
async def generate_amendment_draft(
    request: AmendmentDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate suggested amendment language for trade finance documents.

    Features:
    - Context-aware amendment suggestions
    - UCP 600 compliance checking
    - Risk assessment integration
    - Version control for amendments

    Business Model Protection:
    - SME users: Basic amendment templates
    - Bank users: Advanced AI-powered suggestions with legal compliance
    - Billing events tracked for dual revenue model
    """
    try:
        llm_service = LLMAssistService(db)
        result = await llm_service.generate_amendment_draft(request, current_user)

        logger.info(
            f"Amendment draft generated for user {current_user.id}, "
            f"LC {request.lc_id}, confidence: {result.confidence_score}"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to generate amendment draft: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate amendment draft"
        )

@router.post("/chat", response_model=AIResponse)
async def ai_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Interactive AI chat for trade finance assistance.

    Features:
    - Context-aware responses
    - Trade finance domain knowledge
    - Session-based conversation memory
    - Guardrails against non-trade finance queries

    Usage Limits:
    - SME users: 100 messages/month
    - Bank users: Unlimited
    - Rate limiting: 10 requests/minute
    """
    try:
        llm_service = LLMAssistService(db)
        result = await llm_service.chat(request, current_user)

        logger.info(
            f"AI chat response generated for user {current_user.id}, "
            f"session {request.session_id}, confidence: {result.confidence_score}"
        )

        return result

    except Exception as e:
        logger.error(f"Failed to generate chat response: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate chat response"
        )

@router.get("/audit/{event_id}")
async def get_ai_audit_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve AI audit event for compliance and debugging.

    Access Control:
    - Users can only access their own audit events
    - Bank admins can access events for their organization
    - Regulatory users have full access
    """
    try:
        llm_service = LLMAssistService(db)
        audit_event = await llm_service.get_audit_event(event_id, current_user)

        if not audit_event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audit event not found or access denied"
            )

        return audit_event

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve audit event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit event"
        )

@router.get("/health")
async def ai_health_check():
    """Health check endpoint for AI services."""
    try:
        # Basic health check - could be expanded to check LLM provider status
        return {
            "status": "healthy",
            "service": "ai_assistant",
            "version": "1.0.0",
            "features": [
                "discrepancy_summary",
                "bank_draft",
                "amendment_draft",
                "chat",
                "audit_trail"
            ]
        }
    except Exception as e:
        logger.error(f"AI health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service unavailable"
        )