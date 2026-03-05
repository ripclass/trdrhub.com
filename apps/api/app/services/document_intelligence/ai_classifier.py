"""
AI-Enhanced Document Classifier - High Accuracy Classification

Uses AI (GPT-4o-mini) when pattern-based classification isn't confident enough.
Provides:
- Document type classification (invoice, B/L, LC, etc.)
- LC type detection (export vs import vs draft)
- Trade document relevance check

Cost: ~$0.005 per document when AI is needed
Strategy: Pattern-first, AI-fallback (saves money when patterns are confident)
"""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

from app.config import settings
from app.models import DocumentType
from .doc_type_classifier import (
    DocumentTypeClassifier,
    ClassificationResult,
    ClassificationConfidence,
    get_doc_type_classifier,
)

logger = logging.getLogger(__name__)


class LCFlowType(str, Enum):
    """LC flow type from beneficiary perspective."""
    EXPORT = "export"      # User is beneficiary (seller)
    IMPORT = "import"      # User is applicant (buyer)
    DRAFT = "draft"        # Not yet issued
    UNKNOWN = "unknown"


class TradeRelevance(str, Enum):
    """Is this a trade document?"""
    TRADE_DOCUMENT = "trade_document"
    NON_TRADE = "non_trade"
    UNCERTAIN = "uncertain"


@dataclass
class AIClassificationResult:
    """Enhanced classification result with AI insights."""
    # Document type
    document_type: str
    document_type_confidence: float
    
    # LC-specific (only if document is LC)
    lc_flow_type: Optional[LCFlowType] = None
    lc_flow_confidence: Optional[float] = None
    lc_flow_reason: Optional[str] = None
    is_draft_lc: bool = False
    
    # Trade relevance
    is_trade_document: bool = True
    trade_relevance: TradeRelevance = TradeRelevance.TRADE_DOCUMENT
    
    # Classification details
    classification_method: str = "pattern"  # "pattern" or "ai"
    matched_patterns: List[str] = field(default_factory=list)
    ai_reasoning: Optional[str] = None
    alternative_types: List[Dict[str, Any]] = field(default_factory=list)
    
    # Warnings/flags
    warnings: List[str] = field(default_factory=list)
    should_block: bool = False
    block_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_type": self.document_type,
            "document_type_confidence": self.document_type_confidence,
            "lc_flow_type": self.lc_flow_type.value if self.lc_flow_type else None,
            "lc_flow_confidence": self.lc_flow_confidence,
            "lc_flow_reason": self.lc_flow_reason,
            "is_draft_lc": self.is_draft_lc,
            "is_trade_document": self.is_trade_document,
            "trade_relevance": self.trade_relevance.value,
            "classification_method": self.classification_method,
            "matched_patterns": self.matched_patterns,
            "ai_reasoning": self.ai_reasoning,
            "alternative_types": self.alternative_types,
            "warnings": self.warnings,
            "should_block": self.should_block,
            "block_reason": self.block_reason,
        }


# AI Classification prompt
AI_CLASSIFICATION_PROMPT = """Analyze this document and classify it.

Document Text (first 4000 chars):
{text}

Respond ONLY with JSON (no other text):
{{
    "document_type": "letter_of_credit" | "commercial_invoice" | "bill_of_lading" | "packing_list" | "insurance_certificate" | "certificate_of_origin" | "inspection_certificate" | "draft" | "other",
    "document_type_confidence": 0.0-1.0,
    "is_trade_document": true | false,
    "trade_document_reason": "brief reason",
    "lc_flow_type": "export" | "import" | "draft" | "unknown" | null,
    "lc_flow_confidence": 0.0-1.0 or null,
    "lc_flow_reason": "reason or null",
    "is_draft_lc": true | false,
    "reasoning": "brief classification explanation"
}}

Document type rules:
- letter_of_credit: MT700, MT760, SWIFT LC, "irrevocable", "documentary credit"
- commercial_invoice: Sales invoice with prices, quantities, buyer/seller
- bill_of_lading: Shipping doc with shipper, consignee, vessel, ports
- packing_list: Items with weights, dimensions, carton counts
- insurance_certificate: Marine/cargo insurance with coverage
- certificate_of_origin: Certifies country where goods made
- inspection_certificate: Quality/inspection from SGS, Bureau Veritas, etc.

LC Flow (only for letter_of_credit):
- export: Beneficiary is seller, shipping goods OUT
- import: Applicant is buyer, receiving goods IN
- draft: Contains "draft", "proposed", not yet issued"""


LC_FLOW_PROMPT = """Determine if this is an EXPORT or IMPORT LC.

LC Text (first 3000 chars):
{text}

Respond ONLY with JSON:
{{
    "type": "export" | "import" | "draft" | "unknown",
    "confidence": 0.0-1.0,
    "reason": "brief explanation",
    "is_draft": true | false,
    "beneficiary_country": "country or null",
    "applicant_country": "country or null"
}}

Rules:
- EXPORT LC: Beneficiary (seller) ships goods OUT of their country
- IMPORT LC: Applicant (buyer) receives goods INTO their country
- DRAFT LC: Contains "draft", "proposed", "for approval" - not issued
- Look at: ports, party addresses, bank locations, goods flow direction"""


class AIDocumentClassifier:
    """
    AI-enhanced document classifier.
    
    Strategy:
    1. Run pattern-based classification first (free)
    2. If confidence < 70%, use AI for better accuracy
    3. For LC documents, always run LC flow detection
    """
    
    AI_FALLBACK_THRESHOLD = 0.70
    LC_DOCUMENT_TYPES = {"letter_of_credit", "swift_message", "lc_application"}
    
    def __init__(self):
        self.pattern_classifier = get_doc_type_classifier()
    
    async def classify(
        self,
        text: str,
        filename: Optional[str] = None,
        force_ai: bool = False,
        detect_lc_flow: bool = True,
    ) -> AIClassificationResult:
        """
        Classify a document with AI enhancement.
        
        Args:
            text: OCR extracted text
            filename: Optional filename for hints
            force_ai: Force AI classification even if patterns confident
            detect_lc_flow: Detect export/import/draft for LC docs
        """
        if not text or len(text.strip()) < 50:
            return AIClassificationResult(
                document_type="unknown",
                document_type_confidence=0.0,
                is_trade_document=False,
                trade_relevance=TradeRelevance.UNCERTAIN,
                warnings=["Document text too short for classification"],
                should_block=True,
                block_reason="Insufficient document content",
            )
        
        # Step 1: Pattern-based classification (free)
        pattern_result = self.pattern_classifier.classify(text, filename)
        
        # Step 2: Decide if AI needed
        use_ai = (
            force_ai or 
            pattern_result.confidence < self.AI_FALLBACK_THRESHOLD or
            pattern_result.confidence_level == ClassificationConfidence.UNKNOWN
        )
        
        if use_ai:
            ai_result = await self._classify_with_ai(text)
            if ai_result:
                return ai_result
            logger.warning("AI classification failed, using pattern result")
        
        # Step 3: Build result from pattern classification
        result = AIClassificationResult(
            document_type=pattern_result.document_type.value,
            document_type_confidence=pattern_result.confidence,
            is_trade_document=True,
            trade_relevance=TradeRelevance.TRADE_DOCUMENT,
            classification_method="pattern",
            matched_patterns=pattern_result.matched_patterns,
            alternative_types=[
                {"type": t.value, "confidence": c}
                for t, c in pattern_result.alternative_types
            ],
        )
        
        # Step 4: LC flow detection for LC documents
        if detect_lc_flow and pattern_result.document_type.value in self.LC_DOCUMENT_TYPES:
            lc_flow = await self._detect_lc_flow(text)
            result.lc_flow_type = lc_flow.get("type", LCFlowType.UNKNOWN)
            result.lc_flow_confidence = lc_flow.get("confidence", 0.0)
            result.lc_flow_reason = lc_flow.get("reason")
            result.is_draft_lc = lc_flow.get("is_draft", False)
        
        return result
    
    async def _classify_with_ai(self, text: str) -> Optional[AIClassificationResult]:
        """Use AI for document classification."""
        try:
            from app.services.llm_provider import LLMProviderFactory
            
            provider = LLMProviderFactory.get_provider()
            truncated_text = text[:4000]
            prompt = AI_CLASSIFICATION_PROMPT.format(text=truncated_text)
            
            response = await provider.complete(
                prompt=prompt,
                max_tokens=500,
                temperature=0.1,
            )
            
            response_text = response.get("content", "") if isinstance(response, dict) else str(response)
            
            # Extract JSON
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response_text[json_start:json_end])
                
                lc_flow_type = None
                if data.get("lc_flow_type"):
                    try:
                        lc_flow_type = LCFlowType(data["lc_flow_type"])
                    except ValueError:
                        lc_flow_type = LCFlowType.UNKNOWN
                
                trade_relevance = (
                    TradeRelevance.TRADE_DOCUMENT 
                    if data.get("is_trade_document", True) 
                    else TradeRelevance.NON_TRADE
                )
                
                warnings = []
                should_block = False
                block_reason = None
                
                if not data.get("is_trade_document", True):
                    warnings.append("This doesn't appear to be a trade document")
                    should_block = True
                    block_reason = data.get("trade_document_reason", "Not trade-related")
                
                if data.get("is_draft_lc", False):
                    warnings.append("This appears to be a draft LC (not yet issued)")
                
                return AIClassificationResult(
                    document_type=data.get("document_type", "unknown"),
                    document_type_confidence=data.get("document_type_confidence", 0.5),
                    lc_flow_type=lc_flow_type,
                    lc_flow_confidence=data.get("lc_flow_confidence"),
                    lc_flow_reason=data.get("lc_flow_reason"),
                    is_draft_lc=data.get("is_draft_lc", False),
                    is_trade_document=data.get("is_trade_document", True),
                    trade_relevance=trade_relevance,
                    classification_method="ai",
                    ai_reasoning=data.get("reasoning"),
                    warnings=warnings,
                    should_block=should_block,
                    block_reason=block_reason,
                )
            
            return None
            
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return None
    
    async def _detect_lc_flow(self, text: str) -> Dict[str, Any]:
        """Detect LC flow type (export/import/draft) using AI."""
        try:
            from app.services.llm_provider import LLMProviderFactory
            
            provider = LLMProviderFactory.get_provider()
            prompt = LC_FLOW_PROMPT.format(text=text[:3000])
            
            response = await provider.complete(
                prompt=prompt,
                max_tokens=300,
                temperature=0.1,
            )
            
            response_text = response.get("content", "") if isinstance(response, dict) else str(response)
            
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response_text[json_start:json_end])
                
                lc_type = data.get("type", "unknown")
                try:
                    lc_flow_type = LCFlowType(lc_type)
                except ValueError:
                    lc_flow_type = LCFlowType.UNKNOWN
                
                return {
                    "type": lc_flow_type,
                    "confidence": data.get("confidence", 0.5),
                    "reason": data.get("reason"),
                    "is_draft": data.get("is_draft", False),
                }
            
            return {"type": LCFlowType.UNKNOWN, "confidence": 0.0}
            
        except Exception as e:
            logger.error(f"LC flow detection failed: {e}")
            return {"type": LCFlowType.UNKNOWN, "confidence": 0.0}
    
    async def check_trade_relevance(self, text: str) -> Dict[str, Any]:
        """Quick check if document is trade-related."""
        trade_keywords = [
            "invoice", "bill of lading", "consignee", "shipper",
            "letter of credit", "documentary", "beneficiary", "applicant",
            "port of loading", "port of discharge", "certificate",
            "packing list", "insurance", "shipment", "cargo",
        ]
        
        text_lower = text.lower()
        matches = sum(1 for kw in trade_keywords if kw in text_lower)
        
        if matches >= 3:
            return {
                "is_trade_document": True,
                "confidence": min(0.5 + matches * 0.1, 0.95),
                "reason": f"Found {matches} trade-related keywords"
            }
        
        if matches == 0:
            return {
                "is_trade_document": False,
                "confidence": 0.8,
                "reason": "No trade-related keywords found"
            }
        
        return {
            "is_trade_document": True,
            "confidence": 0.5,
            "reason": f"Found {matches} trade keywords (low confidence)"
        }


# Module-level instance
_ai_classifier: Optional[AIDocumentClassifier] = None


def get_ai_classifier() -> AIDocumentClassifier:
    """Get the global AI document classifier."""
    global _ai_classifier
    if _ai_classifier is None:
        _ai_classifier = AIDocumentClassifier()
    return _ai_classifier


async def classify_document(
    text: str,
    filename: Optional[str] = None,
    force_ai: bool = False,
) -> AIClassificationResult:
    """Convenience function to classify a document."""
    classifier = get_ai_classifier()
    return await classifier.classify(text, filename, force_ai)


async def detect_lc_type_ai(text: str) -> Dict[str, Any]:
    """
    Detect LC type (export/import/draft) using AI.
    
    Returns:
        {"lc_type": str, "confidence": float, "reason": str, "is_draft": bool}
    """
    classifier = get_ai_classifier()
    flow = await classifier._detect_lc_flow(text)
    return {
        "lc_type": flow["type"].value if isinstance(flow["type"], LCFlowType) else str(flow["type"]),
        "confidence": flow.get("confidence", 0.0),
        "reason": flow.get("reason"),
        "is_draft": flow.get("is_draft", False),
    }
