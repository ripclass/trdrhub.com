"""
Bank AI Assistance API endpoints
Provides AI-powered features for bank users: discrepancy explanations, letter generation, document summarization, translation
"""
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..core.security import require_bank_or_admin
from ..database import get_db
from ..models import User, ValidationSession
from ..services.llm_assist import LLMAssistService, AILanguage, AIOutputType
from ..services.ai_usage_tracker import AIUsageTracker, AIFeature
from ..services.audit_service import AuditService
from ..middleware.audit_middleware import create_audit_context
from ..models.audit_log import AuditAction, AuditResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bank/ai", tags=["bank-ai"])


# Request/Response Models
class DiscrepancyExplainRequest(BaseModel):
    discrepancy: str = Field(..., description="Discrepancy description or rule ID")
    lc_number: Optional[str] = None
    validation_session_id: Optional[str] = None
    language: str = "en"


class LetterGenerateRequest(BaseModel):
    letter_type: str = Field(..., description="approval or rejection")
    client_name: str
    lc_number: str
    context: Optional[str] = None
    discrepancy_list: Optional[List[Dict[str, Any]]] = None
    language: str = "en"


class SummarizeRequest(BaseModel):
    document_text: str
    lc_number: Optional[str] = None
    language: str = "en"


class TranslateRequest(BaseModel):
    text: str
    target_language: str = Field(..., description="bn, ar, zh, es, fr, de, ja")
    source_language: Optional[str] = "en"


class AIUsageQuotaResponse(BaseModel):
    feature: str
    used: int
    limit: int
    remaining: int
    reset_at: Optional[str] = None


class AIResponse(BaseModel):
    content: str
    rule_basis: Optional[List[Dict[str, str]]] = None
    confidence_score: Optional[float] = None
    usage_remaining: Optional[int] = None
    event_id: Optional[str] = None


@router.get("/quota", response_model=AIUsageQuotaResponse)
async def get_ai_quota(
    feature: str,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
):
    """Get remaining AI usage quota for a specific feature."""
    try:
        usage_tracker = AIUsageTracker(db)
        is_bank = current_user.role in ["bank_admin", "bank_officer"]
        
        # Map feature string to AIFeature enum
        feature_map = {
            "discrepancy": AIFeature.SUMMARY,
            "letter": AIFeature.LETTER,
            "summarize": AIFeature.SUMMARY,
            "translate": AIFeature.TRANSLATE,
        }
        
        ai_feature = feature_map.get(feature, AIFeature.SUMMARY)
        
        # Get quota info (mock for now, will be implemented in AIUsageTracker)
        quota_info = usage_tracker.get_quota_info(current_user, ai_feature, is_bank)
        
        return AIUsageQuotaResponse(
            feature=feature,
            used=quota_info.get("used", 0),
            limit=quota_info.get("limit", 1000 if is_bank else 100),
            remaining=quota_info.get("remaining", 1000 if is_bank else 100),
            reset_at=quota_info.get("reset_at")
        )
    except Exception as e:
        logger.error(f"Failed to get AI quota: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quota information"
        )


@router.post("/discrepancy-explain", response_model=AIResponse)
async def explain_discrepancy(
    request: DiscrepancyExplainRequest,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """Generate AI-powered explanation for a discrepancy."""
    try:
        llm_service = LLMAssistService(db)
        usage_tracker = AIUsageTracker(db)
        
        # Check quota
        is_bank = current_user.role in ["bank_admin", "bank_officer"]
        session = None
        if request.validation_session_id:
            session = db.query(ValidationSession).filter(
                ValidationSession.id == request.validation_session_id
            ).first()
        
        allowed, error_msg, remaining_dict = usage_tracker.check_quota(
            user=current_user,
            session=session,
            feature=AIFeature.SUMMARY,
            is_bank=is_bank
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_msg or "AI usage quota exceeded"
            )
        
        # Get remaining quota (use per_user_day if available, else per_lc)
        remaining = remaining_dict.get("per_user_day", remaining_dict.get("per_lc", 0))
        
        # Get locale from request state (set by LocaleMiddleware)
        locale = getattr(http_request.state, "locale", "en") if http_request else "en"
        language = request.language or locale  # Use request locale as fallback
        
        # Generate explanation using LLM service
        # For now, use mock response (will wire to actual LLM service)
        from ..services.llm_assist import DiscrepancySummaryRequest, AILanguage
        
        lang = AILanguage.ENGLISH
        if language == "bn":
            lang = AILanguage.BANGLA
        elif request.language == "ar":
            lang = AILanguage.ARABIC
        
        explain_request = DiscrepancySummaryRequest(
            session_id=request.validation_session_id or str(UUID(int=0)),
            discrepancies=[{"description": request.discrepancy}],
            language=lang,
            include_explanations=True,
            include_fix_suggestions=True
        )
        
        result = await llm_service.generate_discrepancy_summary(explain_request, current_user)
        
        # Audit log
        audit_service = AuditService(db)
        audit_context = create_audit_context(http_request) if http_request else {}
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get('correlation_id', ''),
            resource_type="ai_discrepancy_explanation",
            resource_id=str(result.event_id) if hasattr(result, 'event_id') else '',
            details={
                "discrepancy": request.discrepancy,
                "lc_number": request.lc_number,
                "language": request.language
            },
            result=AuditResult.SUCCESS
        )
        
        logger.info("Telemetry: bank_ai_discrepancy_explain", extra={
            "user_id": str(current_user.id),
            "lc_number": request.lc_number,
            "language": request.language
        })
        
        return AIResponse(
            content=result.output,
            rule_basis=result.rule_references,
            confidence_score=getattr(result.confidence, 'value', 0.8) if hasattr(result.confidence, 'value') else 0.8,
            usage_remaining=remaining,
            event_id=str(result.event_id) if hasattr(result, 'event_id') else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate discrepancy explanation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate discrepancy explanation"
        )


@router.post("/generate-letter", response_model=AIResponse)
async def generate_letter(
    request: LetterGenerateRequest,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """Generate approval or rejection letter."""
    try:
        llm_service = LLMAssistService(db)
        usage_tracker = AIUsageTracker(db)
        
        # Check quota
        is_bank = current_user.role in ["bank_admin", "bank_officer"]
        allowed, error_msg, remaining_dict = usage_tracker.check_quota(
            user=current_user,
            session=None,
            feature=AIFeature.LETTER,
            is_bank=is_bank
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_msg or "AI usage quota exceeded"
            )
        
        # Get remaining quota (use per_user_day if available, else per_lc)
        remaining = remaining_dict.get("per_user_day", remaining_dict.get("per_lc", 0))
        
        # Get locale from request state (set by LocaleMiddleware)
        locale = getattr(http_request.state, "locale", "en") if http_request else "en"
        language = request.language or locale  # Use request locale as fallback
        
        # Generate letter using LLM service
        from ..services.llm_assist import BankDraftRequest, AILanguage
        
        lang = AILanguage.ENGLISH
        if language == "bn":
            lang = AILanguage.BANGLA
        elif language == "ar":
            lang = AILanguage.ARABIC
        
        draft_request = BankDraftRequest(
            session_id=str(UUID(int=0)),  # Mock session ID
            discrepancy_list=request.discrepancy_list or [],
            language=lang,
            formal_tone=True,
            include_regulations=True
        )
        
        result = await llm_service.generate_bank_draft(draft_request, current_user)
        
        # Format letter with client/LC details
        letter_content = f"""Dear {request.client_name},

RE: Letter of Credit {request.lc_number}

{result.output}

Yours faithfully,
{current_user.full_name or 'Bank Officer'}
LCopilot Validation Team"""
        
        # Audit log
        audit_service = AuditService(db)
        audit_context = create_audit_context(http_request) if http_request else {}
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get('correlation_id', ''),
            resource_type="ai_letter_generation",
            resource_id=str(result.event_id) if hasattr(result, 'event_id') else '',
            details={
                "letter_type": request.letter_type,
                "client_name": request.client_name,
                "lc_number": request.lc_number
            },
            result=AuditResult.SUCCESS
        )
        
        logger.info("Telemetry: bank_ai_letter_generated", extra={
            "user_id": str(current_user.id),
            "letter_type": request.letter_type,
            "lc_number": request.lc_number
        })
        
        return AIResponse(
            content=letter_content,
            rule_basis=result.rule_references,
            confidence_score=getattr(result.confidence, 'value', 0.8) if hasattr(result.confidence, 'value') else 0.8,
            usage_remaining=remaining,
            event_id=str(result.event_id) if hasattr(result, 'event_id') else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate letter: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate letter"
        )


@router.post("/summarize", response_model=AIResponse)
async def summarize_document(
    request: SummarizeRequest,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """Summarize LC document text."""
    try:
        llm_service = LLMAssistService(db)
        usage_tracker = AIUsageTracker(db)
        
        # Check quota
        is_bank = current_user.role in ["bank_admin", "bank_officer"]
        allowed, error_msg, remaining_dict = usage_tracker.check_quota(
            user=current_user,
            session=None,
            feature=AIFeature.SUMMARY,
            is_bank=is_bank
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_msg or "AI usage quota exceeded"
            )
        
        # Get remaining quota (use per_user_day if available, else per_lc)
        remaining = remaining_dict.get("per_user_day", remaining_dict.get("per_lc", 0))
        
        # Get locale from request state (set by LocaleMiddleware)
        locale = getattr(http_request.state, "locale", "en") if http_request else "en"
        language = request.language or locale  # Use request locale as fallback
        
        # Use chat endpoint for summarization
        from ..services.llm_assist import ChatRequest, AILanguage
        
        lang = AILanguage.ENGLISH
        if language == "bn":
            lang = AILanguage.BANGLA
        
        chat_request = ChatRequest(
            session_id=str(UUID(int=0)),
            question=f"Summarize this LC document:\n\n{request.document_text}",
            language=lang,
            context_documents=[]
        )
        
        result = await llm_service.chat(chat_request, current_user)
        
        # Audit log
        audit_service = AuditService(db)
        audit_context = create_audit_context(http_request) if http_request else {}
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get('correlation_id', ''),
            resource_type="ai_document_summary",
            resource_id=str(result.event_id) if hasattr(result, 'event_id') else '',
            details={
                "lc_number": request.lc_number,
                "language": request.language
            },
            result=AuditResult.SUCCESS
        )
        
        logger.info("Telemetry: bank_ai_document_summarized", extra={
            "user_id": str(current_user.id),
            "lc_number": request.lc_number
        })
        
        return AIResponse(
            content=result.output,
            rule_basis=result.rule_references,
            confidence_score=getattr(result.confidence, 'value', 0.8) if hasattr(result.confidence, 'value') else 0.8,
            usage_remaining=remaining,
            event_id=str(result.event_id) if hasattr(result, 'event_id') else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to summarize document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to summarize document"
        )


@router.post("/translate", response_model=AIResponse)
async def translate_text(
    request: TranslateRequest,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """Translate text to target language."""
    try:
        llm_service = LLMAssistService(db)
        usage_tracker = AIUsageTracker(db)
        
        # Check quota
        is_bank = current_user.role in ["bank_admin", "bank_officer"]
        allowed, error_msg, remaining = usage_tracker.check_quota(
            user=current_user,
            session=None,
            feature=AIFeature.TRANSLATE,
            is_bank=is_bank
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_msg or "AI usage quota exceeded"
            )
        
        # Get locale from request state (set by LocaleMiddleware)
        locale = getattr(http_request.state, "locale", "en") if http_request else "en"
        target_lang = request.target_language or locale  # Use request locale as fallback
        
        # Use chat endpoint for translation
        from ..services.llm_assist import ChatRequest, AILanguage
        
        lang_map = {
            "bn": AILanguage.BANGLA,
            "ar": AILanguage.ARABIC,
            "hi": AILanguage.HINDI,
            "ur": AILanguage.URDU,
        }
        lang = lang_map.get(target_lang, AILanguage.ENGLISH)
        
        chat_request = ChatRequest(
            session_id=str(UUID(int=0)),
            question=f"Translate the following text to {target_lang}:\n\n{request.text}",
            language=lang,
            context_documents=[]
        )
        
        result = await llm_service.chat(chat_request, current_user)
        
        # Audit log
        audit_service = AuditService(db)
        audit_context = create_audit_context(http_request) if http_request else {}
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get('correlation_id', ''),
            resource_type="ai_translation",
            resource_id=str(result.event_id) if hasattr(result, 'event_id') else '',
            details={
                "source_language": request.source_language,
                "target_language": request.target_language
            },
            result=AuditResult.SUCCESS
        )
        
        logger.info("Telemetry: bank_ai_text_translated", extra={
            "user_id": str(current_user.id),
            "target_language": request.target_language
        })
        
        return AIResponse(
            content=result.output,
            rule_basis=None,
            confidence_score=getattr(result.confidence, 'value', 0.8) if hasattr(result.confidence, 'value') else 0.8,
            usage_remaining=remaining,
            event_id=str(result.event_id) if hasattr(result, 'event_id') else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to translate text: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to translate text"
        )

