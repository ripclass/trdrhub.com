"""
LLM Assist Layer for LCopilot - AI-powered trade document analysis.
Provides AI summaries, explanations, and drafting while enforcing compliance guardrails.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import logging

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, relationship
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from ..models.base import Base
from ..models import ValidationSession, User
from ..core.validation_engine import ValidationEngine
from ..core.prompt_library import PromptLibrary, PromptTemplate
from ..config import settings
from .llm_provider import LLMProviderFactory
from .text_guard import TextGuard
from .ai_usage_tracker import AIUsageTracker, AIFeature

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AILanguage(str, Enum):
    ENGLISH = "en"
    BANGLA = "bn"
    ARABIC = "ar"
    URDU = "ur"
    HINDI = "hi"


class AIOutputType(str, Enum):
    DISCREPANCY_SUMMARY = "discrepancy_summary"
    BANK_DRAFT = "bank_draft"
    AMENDMENT_DRAFT = "amendment_draft"
    CHAT_RESPONSE = "chat_response"
    FIX_SUGGESTION = "fix_suggestion"


# Database Models
class AIAssistEvent(Base):
    """Immutable audit log for all AI assistance events."""
    __tablename__ = "ai_assist_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('validation_sessions.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=False)

    # AI Operation Details
    output_type = Column(String(50), nullable=False)  # AIOutputType enum
    confidence_level = Column(String(20), nullable=False)  # ConfidenceLevel enum
    language = Column(String(5), nullable=False)  # AILanguage enum
    model_version = Column(String(50), nullable=False)

    # Input/Output Data
    input_data = Column(JSONB, nullable=False)
    ai_output = Column(Text, nullable=False)
    fallback_used = Column(Boolean, nullable=False, default=False)
    
    # Token and Cost Tracking
    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    estimated_cost_usd = Column(String(20), nullable=True)
    lc_session_id = Column(UUID(as_uuid=True), ForeignKey('validation_sessions.id'), nullable=True)

    # Traceability
    rule_references = Column(JSONB, nullable=True)  # ICC/UCP clause references
    prompt_template_id = Column(String(100), nullable=False)

    # Metadata
    processing_time_ms = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    session = relationship("ValidationSession", foreign_keys=[session_id])
    user = relationship("User")
    company = relationship("Company")


# Pydantic Models
class DiscrepancySummaryRequest(BaseModel):
    session_id: str
    discrepancies: List[Dict[str, Any]]
    language: AILanguage = AILanguage.ENGLISH
    include_explanations: bool = True
    include_fix_suggestions: bool = True


class BankDraftRequest(BaseModel):
    session_id: str
    discrepancy_list: List[Dict[str, Any]]
    language: AILanguage = AILanguage.ENGLISH
    formal_tone: bool = True
    include_regulations: bool = True


class AmendmentDraftRequest(BaseModel):
    session_id: str
    amendment_details: Dict[str, Any]
    language: AILanguage = AILanguage.ENGLISH
    amendment_type: str  # "date_extension", "amount_change", "document_modification", etc.


class ChatRequest(BaseModel):
    session_id: str
    question: str
    language: AILanguage = AILanguage.ENGLISH
    context_documents: List[str] = []


class AIResponse(BaseModel):
    output: str
    confidence: ConfidenceLevel
    language: AILanguage
    fallback_used: bool
    rule_references: List[Dict[str, str]]
    suggestions: List[str] = []
    processing_time_ms: int
    event_id: str


class LLMAssistService:
    """Core service for AI-powered LC assistance."""

    def __init__(self, db: Session):
        self.db = db
        self.validation_engine = ValidationEngine()
        self.prompt_library = PromptLibrary()
        self.model_version = settings.LLM_MODEL_VERSION
        self.confidence_threshold = 0.7  # Minimum confidence for AI responses
        
        # Initialize new services
        self.usage_tracker = AIUsageTracker(db)
        self.text_guard = TextGuard()
        
        # Determine max tokens based on output type
        self.max_tokens_map = {
            AIOutputType.DISCREPANCY_SUMMARY: settings.AI_MAX_OUTPUT_TOKENS_SYSTEM,
            AIOutputType.BANK_DRAFT: settings.AI_MAX_OUTPUT_TOKENS_LETTER,
            AIOutputType.AMENDMENT_DRAFT: settings.AI_MAX_OUTPUT_TOKENS_LETTER,
            AIOutputType.CHAT_RESPONSE: settings.AI_MAX_OUTPUT_TOKENS_CHAT,
        }

    async def generate_discrepancy_summary(
        self,
        request: DiscrepancySummaryRequest,
        user: User
    ) -> AIResponse:
        """Generate AI-powered summary of LC discrepancies."""
        start_time = datetime.utcnow()

        # Get validation session
        session = self.db.query(ValidationSession).filter(
            ValidationSession.id == request.session_id
        ).first()

        if not session:
            raise ValueError(f"Session {request.session_id} not found")

        # Check quota before proceeding
        is_bank = self._is_bank_user(user)
        feature = AIFeature.SUMMARY
        
        allowed, error_msg, remaining = self.usage_tracker.check_quota(
            user=user,
            session=session,
            feature=feature,
            is_bank=is_bank
        )
        
        if not allowed:
            raise ValueError(error_msg or "Quota exceeded")

        # Prepare input data
        input_data = {
            "discrepancies": request.discrepancies,
            "lc_data": session.validation_results.get("lc_data", {}),
            "language": request.language.value,
            "include_explanations": request.include_explanations,
            "include_fix_suggestions": request.include_fix_suggestions
        }

        try:
            # Get prompt template
            prompt_template = self.prompt_library.get_template(
                "discrepancy_summary",
                request.language.value
            )

            # Generate AI response
            ai_output, confidence, rule_refs, tokens_in, tokens_out, estimated_cost = await self._call_llm_api(
                prompt_template,
                input_data,
                AIOutputType.DISCREPANCY_SUMMARY,
                user,
                session
            )

            # Apply guardrails
            if confidence < self.confidence_threshold:
                ai_output, rule_refs = self._fallback_to_rules(
                    request.discrepancies,
                    request.language
                )
                fallback_used = True
                confidence = ConfidenceLevel.HIGH  # Rule-based is always high confidence
                tokens_in = 0
                tokens_out = 0
                estimated_cost = 0.0
            else:
                fallback_used = False
                confidence = self._map_confidence_score(confidence)
                
                # Record usage
                self.usage_tracker.record_usage(
                    user=user,
                    session=session,
                    feature=feature,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    estimated_cost=estimated_cost
                )

            # Generate fix suggestions if requested
            suggestions = []
            if request.include_fix_suggestions:
                suggestions = await self._generate_fix_suggestions(
                    request.discrepancies,
                    session,
                    request.language
                )

            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Create audit event
            event = AIAssistEvent(
                session_id=session.id,
                user_id=user.id,
                company_id=user.company_id,
                output_type=AIOutputType.DISCREPANCY_SUMMARY.value,
                confidence_level=confidence.value,
                language=request.language.value,
                model_version=self.model_version,
                input_data=input_data,
                ai_output=ai_output,
                fallback_used=fallback_used,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                estimated_cost_usd=str(estimated_cost) if estimated_cost else None,
                lc_session_id=session.id,
                rule_references=rule_refs,
                prompt_template_id=prompt_template.id,
                processing_time_ms=processing_time
            )

            self.db.add(event)
            self.db.commit()

            return AIResponse(
                output=ai_output,
                confidence=confidence,
                language=request.language,
                fallback_used=fallback_used,
                rule_references=rule_refs,
                suggestions=suggestions,
                processing_time_ms=processing_time,
                event_id=str(event.id)
            )

        except Exception as e:
            logger.error(f"AI discrepancy summary failed: {str(e)}")
            # Fallback to rule-based system
            return await self._emergency_fallback(
                request.discrepancies,
                request.language,
                user,
                session,
                AIOutputType.DISCREPANCY_SUMMARY
            )

    async def generate_bank_draft(
        self,
        request: BankDraftRequest,
        user: User
    ) -> AIResponse:
        """Generate bank-style formal discrepancy notifications."""
        start_time = datetime.utcnow()

        session = self.db.query(ValidationSession).filter(
            ValidationSession.id == request.session_id
        ).first()

        if not session:
            raise ValueError(f"Session {request.session_id} not found")

        # Check quota
        is_bank = self._is_bank_user(user)
        feature = AIFeature.LETTER
        
        allowed, error_msg, remaining = self.usage_tracker.check_quota(
            user=user,
            session=session,
            feature=feature,
            is_bank=is_bank
        )
        
        if not allowed:
            raise ValueError(error_msg or "Quota exceeded")

        input_data = {
            "discrepancy_list": request.discrepancy_list,
            "lc_data": session.validation_results.get("lc_data", {}),
            "language": request.language.value,
            "formal_tone": request.formal_tone,
            "include_regulations": request.include_regulations
        }

        try:
            prompt_template = self.prompt_library.get_template(
                "bank_draft",
                request.language.value
            )

            ai_output, confidence, rule_refs, tokens_in, tokens_out, estimated_cost = await self._call_llm_api(
                prompt_template,
                input_data,
                AIOutputType.BANK_DRAFT,
                user,
                session
            )

            # Enhanced guardrails for bank communications
            if confidence < 0.8:  # Higher threshold for bank drafts
                ai_output, rule_refs = self._fallback_to_bank_templates(
                    request.discrepancy_list,
                    request.language
                )
                fallback_used = True
                confidence = ConfidenceLevel.HIGH
                tokens_in = 0
                tokens_out = 0
                estimated_cost = 0.0
            else:
                fallback_used = False
                confidence = self._map_confidence_score(confidence)
                
                # Record usage
                self.usage_tracker.record_usage(
                    user=user,
                    session=session,
                    feature=feature,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    estimated_cost=estimated_cost
                )

            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Create audit event
            event = AIAssistEvent(
                session_id=session.id,
                user_id=user.id,
                company_id=user.company_id,
                output_type=AIOutputType.BANK_DRAFT.value,
                confidence_level=confidence.value,
                language=request.language.value,
                model_version=self.model_version,
                input_data=input_data,
                ai_output=ai_output,
                fallback_used=fallback_used,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                estimated_cost_usd=str(estimated_cost) if estimated_cost else None,
                lc_session_id=session.id,
                rule_references=rule_refs,
                prompt_template_id=prompt_template.id,
                processing_time_ms=processing_time
            )

            self.db.add(event)
            self.db.commit()

            return AIResponse(
                output=ai_output,
                confidence=confidence,
                language=request.language,
                fallback_used=fallback_used,
                rule_references=rule_refs,
                suggestions=[],
                processing_time_ms=processing_time,
                event_id=str(event.id)
            )

        except Exception as e:
            logger.error(f"AI bank draft failed: {str(e)}")
            return await self._emergency_fallback(
                request.discrepancy_list,
                request.language,
                user,
                session,
                AIOutputType.BANK_DRAFT
            )

    async def generate_amendment_draft(
        self,
        request: AmendmentDraftRequest,
        user: User
    ) -> AIResponse:
        """Generate suggested amendment language."""
        start_time = datetime.utcnow()

        session = self.db.query(ValidationSession).filter(
            ValidationSession.id == request.session_id
        ).first()

        if not session:
            raise ValueError(f"Session {request.session_id} not found")

        # Check quota
        is_bank = self._is_bank_user(user)
        feature = AIFeature.LETTER
        
        allowed, error_msg, remaining = self.usage_tracker.check_quota(
            user=user,
            session=session,
            feature=feature,
            is_bank=is_bank
        )
        
        if not allowed:
            raise ValueError(error_msg or "Quota exceeded")

        input_data = {
            "amendment_details": request.amendment_details,
            "amendment_type": request.amendment_type,
            "lc_data": session.validation_results.get("lc_data", {}),
            "language": request.language.value
        }

        try:
            prompt_template = self.prompt_library.get_template(
                "amendment_draft",
                request.language.value
            )

            ai_output, confidence, rule_refs, tokens_in, tokens_out, estimated_cost = await self._call_llm_api(
                prompt_template,
                input_data,
                AIOutputType.AMENDMENT_DRAFT,
                user,
                session
            )

            if confidence < self.confidence_threshold:
                ai_output, rule_refs = self._fallback_to_amendment_templates(
                    request.amendment_type,
                    request.amendment_details,
                    request.language
                )
                fallback_used = True
                confidence = ConfidenceLevel.HIGH
                tokens_in = 0
                tokens_out = 0
                estimated_cost = 0.0
            else:
                fallback_used = False
                confidence = self._map_confidence_score(confidence)
                
                # Record usage
                self.usage_tracker.record_usage(
                    user=user,
                    session=session,
                    feature=feature,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    estimated_cost=estimated_cost
                )

            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Create audit event
            event = AIAssistEvent(
                session_id=session.id,
                user_id=user.id,
                company_id=user.company_id,
                output_type=AIOutputType.AMENDMENT_DRAFT.value,
                confidence_level=confidence.value,
                language=request.language.value,
                model_version=self.model_version,
                input_data=input_data,
                ai_output=ai_output,
                fallback_used=fallback_used,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                estimated_cost_usd=str(estimated_cost) if estimated_cost else None,
                lc_session_id=session.id,
                rule_references=rule_refs,
                prompt_template_id=prompt_template.id,
                processing_time_ms=processing_time
            )

            self.db.add(event)
            self.db.commit()

            return AIResponse(
                output=ai_output,
                confidence=confidence,
                language=request.language,
                fallback_used=fallback_used,
                rule_references=rule_refs,
                suggestions=[],
                processing_time_ms=processing_time,
                event_id=str(event.id)
            )

        except Exception as e:
            logger.error(f"AI amendment draft failed: {str(e)}")
            return await self._emergency_fallback(
                request.amendment_details,
                request.language,
                user,
                session,
                AIOutputType.AMENDMENT_DRAFT
            )

    async def handle_chat_query(
        self,
        request: ChatRequest,
        user: User
    ) -> AIResponse:
        """Handle context-aware chat queries."""
        start_time = datetime.utcnow()

        session = self.db.query(ValidationSession).filter(
            ValidationSession.id == request.session_id
        ).first()

        if not session:
            raise ValueError(f"Session {request.session_id} not found")

        # Check quota
        is_bank = self._is_bank_user(user)
        feature = AIFeature.CHAT
        
        allowed, error_msg, remaining = self.usage_tracker.check_quota(
            user=user,
            session=session,
            feature=feature,
            is_bank=is_bank
        )
        
        if not allowed:
            raise ValueError(error_msg or "Quota exceeded")

        # Build context from session data
        context = {
            "question": request.question,
            "lc_data": session.validation_results.get("lc_data", {}),
            "discrepancies": session.validation_results.get("discrepancies", []),
            "documents": request.context_documents,
            "language": request.language.value
        }

        try:
            prompt_template = self.prompt_library.get_template(
                "chat_response",
                request.language.value
            )

            ai_output, confidence, rule_refs, tokens_in, tokens_out, estimated_cost = await self._call_llm_api(
                prompt_template,
                context,
                AIOutputType.CHAT_RESPONSE,
                user,
                session
            )

            if confidence < self.confidence_threshold:
                ai_output = self._fallback_to_help_text(
                    request.question,
                    request.language
                )
                rule_refs = []
                fallback_used = True
                confidence = ConfidenceLevel.MEDIUM
                tokens_in = 0
                tokens_out = 0
                estimated_cost = 0.0
            else:
                fallback_used = False
                confidence = self._map_confidence_score(confidence)
                
                # Record usage
                self.usage_tracker.record_usage(
                    user=user,
                    session=session,
                    feature=feature,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    estimated_cost=estimated_cost
                )

            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Create audit event
            event = AIAssistEvent(
                session_id=session.id,
                user_id=user.id,
                company_id=user.company_id,
                output_type=AIOutputType.CHAT_RESPONSE.value,
                confidence_level=confidence.value,
                language=request.language.value,
                model_version=self.model_version,
                input_data=context,
                ai_output=ai_output,
                fallback_used=fallback_used,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                estimated_cost_usd=str(estimated_cost) if estimated_cost else None,
                lc_session_id=session.id,
                rule_references=rule_refs,
                prompt_template_id=prompt_template.id,
                processing_time_ms=processing_time
            )

            self.db.add(event)
            self.db.commit()

            return AIResponse(
                output=ai_output,
                confidence=confidence,
                language=request.language,
                fallback_used=fallback_used,
                rule_references=rule_refs,
                suggestions=[],
                processing_time_ms=processing_time,
                event_id=str(event.id)
            )

        except Exception as e:
            logger.error(f"AI chat query failed: {str(e)}")
            return await self._emergency_fallback(
                {"question": request.question},
                request.language,
                user,
                session,
                AIOutputType.CHAT_RESPONSE
            )
    
    async def chat(self, request: ChatRequest, user: User) -> AIResponse:
        """Alias for handle_chat_query for backward compatibility."""
        return await self.handle_chat_query(request, user)

    def _is_bank_user(self, user: User) -> bool:
        """Check if user belongs to a bank company."""
        # Check user role or company type
        # For now, assume bank if company has bank-related attributes
        # In production, check company.type == "bank" or user.role includes "bank"
        return hasattr(user, 'company') and hasattr(user.company, 'type') and user.company.type == "bank"
    
    async def _call_llm_api(
        self,
        prompt_template: PromptTemplate,
        input_data: Dict[str, Any],
        output_type: AIOutputType,
        user: User,
        session: Optional[ValidationSession] = None
    ) -> Tuple[str, float, List[Dict[str, str]], int, int, float]:
        """
        Call external LLM API with prompt and data.
        
        Returns:
            (output_text, confidence_score, rule_refs, tokens_in, tokens_out, estimated_cost)
        """
        max_tokens = self.max_tokens_map.get(output_type, 600)
        
        # Format prompt from template
        user_prompt = prompt_template.user_template.format(**input_data)
        
        try:
            # Call provider with fallback
            output_text, tokens_in, tokens_out, provider_used = await LLMProviderFactory.generate_with_fallback(
                prompt=user_prompt,
                system_prompt=prompt_template.system_prompt,
                max_tokens=max_tokens,
                temperature=0.3,
                primary_provider=settings.LLM_PROVIDER
            )
            
            # Estimate cost
            provider = LLMProviderFactory.create_provider(provider_used)
            estimated_cost = provider.estimate_cost(tokens_in, tokens_out)
            
            # Validate output with text guard
            is_valid, validated_output, warning = self.text_guard.validate_output(output_text)
            
            if not is_valid and warning:
                logger.warning(f"Text guard flagged output: {warning}")
                # For now, use sanitized version; in production could retry with rephrase instruction
                output_text = validated_output
            
            # Extract rule references from output (simple regex-based extraction)
            rule_refs = self._extract_rule_references(output_text)
            
            # Calculate confidence (simplified - in production could use model confidence scores)
            confidence = 0.85 if len(output_text) > 50 and tokens_out > 20 else 0.65
            
            return output_text, confidence, rule_refs, tokens_in, tokens_out, estimated_cost
            
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            # Return fallback values
            return "", 0.0, [], 0, 0, 0.0
    
    def _extract_rule_references(self, text: str) -> List[Dict[str, str]]:
        """Extract UCP/ISBP article references from text."""
        import re
        
        rule_refs = []
        
        # Pattern: UCP 600 Article 14.b, ISBP 745 A22, etc.
        patterns = [
            r'(UCP\s*600)\s*(?:Article|Art\.?)\s*(\d+[a-z]?)',
            r'(ISBP\s*745)\s*(?:Article|Art\.?|A)\s*(\d+[a-z]?)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                regulation = match.group(1).upper()
                article = match.group(2)
                rule_refs.append({
                    "regulation": regulation,
                    "article": article,
                    "description": f"{regulation} Article {article}"
                })
        
        # Deduplicate
        seen = set()
        unique_refs = []
        for ref in rule_refs:
            key = (ref["regulation"], ref["article"])
            if key not in seen:
                seen.add(key)
                unique_refs.append(ref)
        
        return unique_refs

    def _fallback_to_rules(
        self,
        discrepancies: List[Dict[str, Any]],
        language: AILanguage
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Fallback to deterministic rule-based explanations."""
        rule_refs = []
        explanations = []

        for discrepancy in discrepancies:
            rule_code = discrepancy.get("rule_code", "UNKNOWN")
            explanation = self.validation_engine.get_rule_explanation(
                rule_code,
                language.value
            )
            explanations.append(explanation)

            rule_ref = self.validation_engine.get_rule_reference(rule_code)
            if rule_ref:
                rule_refs.append(rule_ref)

        if language == AILanguage.BANGLA:
            summary = "আপনার এলসিতে সমস্যা পাওয়া গেছে। " + " ".join(explanations)
        else:
            summary = "Your LC has validation issues. " + " ".join(explanations)

        return summary, rule_refs

    def _fallback_to_bank_templates(
        self,
        discrepancy_list: List[Dict[str, Any]],
        language: AILanguage
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Fallback to standard bank notification templates."""
        template = self.prompt_library.get_bank_template(language)

        # Format discrepancies in formal bank language
        formatted_discrepancies = []
        rule_refs = []

        for i, discrepancy in enumerate(discrepancy_list, 1):
            formal_text = f"{i}. {discrepancy.get('description', 'Document discrepancy noted')}"
            formatted_discrepancies.append(formal_text)

            rule_ref = self.validation_engine.get_rule_reference(
                discrepancy.get("rule_code", "")
            )
            if rule_ref:
                rule_refs.append(rule_ref)

        bank_draft = template.format(
            discrepancies="\n".join(formatted_discrepancies),
            date=datetime.utcnow().strftime("%Y-%m-%d")
        )

        return bank_draft, rule_refs

    def _fallback_to_amendment_templates(
        self,
        amendment_type: str,
        amendment_details: Dict[str, Any],
        language: AILanguage
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Fallback to standard amendment templates."""
        template = self.prompt_library.get_amendment_template(
            amendment_type,
            language
        )

        amendment_text = template.format(**amendment_details)

        rule_refs = [
            {
                "regulation": "UCP 600",
                "article": "10",
                "description": "Amendment procedures"
            }
        ]

        return amendment_text, rule_refs

    def _fallback_to_help_text(
        self,
        question: str,
        language: AILanguage
    ) -> str:
        """Fallback to static help responses."""
        if language == AILanguage.BANGLA:
            return "আমি আপনাকে এলসি সংক্রান্ত সাধারণ প্রশ্নের উত্তর দিতে পারি। অনুগ্রহ করে আরও নির্দিষ্ট প্রশ্ন করুন।"
        else:
            return "I can help you with LC-related questions. Please ask a more specific question about your documents or validation results."

    async def _generate_fix_suggestions(
        self,
        discrepancies: List[Dict[str, Any]],
        session: ValidationSession,
        language: AILanguage
    ) -> List[str]:
        """Generate specific fix suggestions for discrepancies."""
        suggestions = []

        for discrepancy in discrepancies:
            rule_code = discrepancy.get("rule_code", "")
            suggestion = self.validation_engine.get_fix_suggestion(
                rule_code,
                discrepancy,
                language.value
            )
            if suggestion:
                suggestions.append(suggestion)

        return suggestions

    def _map_confidence_score(self, score: float) -> ConfidenceLevel:
        """Map numerical confidence to enum."""
        if score >= 0.8:
            return ConfidenceLevel.HIGH
        elif score >= 0.6:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    async def _emergency_fallback(
        self,
        input_data: Any,
        language: AILanguage,
        user: User,
        session: ValidationSession,
        output_type: AIOutputType
    ) -> AIResponse:
        """Emergency fallback when all AI systems fail."""
        fallback_text = "We're experiencing technical difficulties. Please contact support for assistance."
        if language == AILanguage.BANGLA:
            fallback_text = "আমরা প্রযুক্তিগত সমস্যার সম্মুখীন হচ্ছি। অনুগ্রহ করে সহায়তার জন্য যোগাযোগ করুন।"

        # Still create audit event for tracking
        event = AIAssistEvent(
            session_id=session.id,
            user_id=user.id,
            company_id=user.company_id,
            output_type=output_type.value,
            confidence_level=ConfidenceLevel.LOW.value,
            language=language.value,
            model_version="fallback",
            input_data={"error": "emergency_fallback"},
            ai_output=fallback_text,
            fallback_used=True,
            rule_references=[],
            prompt_template_id="emergency_fallback",
            processing_time_ms=0
        )

        self.db.add(event)
        self.db.commit()

        return AIResponse(
            output=fallback_text,
            confidence=ConfidenceLevel.LOW,
            language=language,
            fallback_used=True,
            rule_references=[],
            suggestions=[],
            processing_time_ms=0,
            event_id=str(event.id)
        )

    async def get_ai_usage_stats(
        self,
        user: User,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get AI usage statistics for billing/analytics."""
        from sqlalchemy import func

        start_date = datetime.utcnow() - timedelta(days=days)

        # Query usage stats
        stats = self.db.query(
            AIAssistEvent.output_type,
            func.count(AIAssistEvent.id).label('count'),
            func.avg(AIAssistEvent.processing_time_ms).label('avg_processing_time'),
            func.sum(
                func.case([(AIAssistEvent.fallback_used == True, 1)], else_=0)
            ).label('fallback_count')
        ).filter(
            AIAssistEvent.user_id == user.id,
            AIAssistEvent.created_at >= start_date
        ).group_by(AIAssistEvent.output_type).all()

        return {
            "period_days": days,
            "total_requests": sum(stat.count for stat in stats),
            "by_type": [
                {
                    "output_type": stat.output_type,
                    "request_count": stat.count,
                    "avg_processing_time_ms": round(stat.avg_processing_time or 0),
                    "fallback_rate": round(stat.fallback_count / stat.count * 100, 1)
                }
                for stat in stats
            ],
            "total_fallback_rate": round(
                sum(stat.fallback_count for stat in stats) /
                sum(stat.count for stat in stats) * 100, 1
            ) if stats else 0
        }
