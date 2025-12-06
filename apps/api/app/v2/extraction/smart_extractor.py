"""
Smart AI Extractor with Provider Routing

Routes documents to the best AI provider based on:
- Document type
- Quality score
- Handwriting presence
- Language

Target: <10 seconds for 10 documents with 99% accuracy
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

from ..core.types import (
    DocumentType, DocumentQuality, FieldConfidence, 
    ExtractedFields, IssueSeverity
)
from ..core.config import get_v2_config, AIProviderConfig

logger = logging.getLogger(__name__)


@dataclass
class ProviderResult:
    """Result from a single AI provider."""
    provider: str
    output: str
    parsed: Optional[Dict[str, Any]]
    tokens_in: int
    tokens_out: int
    latency_ms: int
    success: bool
    error: Optional[str] = None


@dataclass
class ExtractionResult:
    """Final extraction result with confidence."""
    document_id: str
    document_type: DocumentType
    fields: Dict[str, FieldConfidence]
    providers_used: List[str]
    providers_agreed: List[str]
    overall_confidence: float
    needs_review: bool
    review_reasons: List[str]
    total_tokens: int
    latency_ms: int


# Document-specific prompts
EXTRACTION_PROMPTS = {
    DocumentType.LETTER_OF_CREDIT: """Extract the following fields from this Letter of Credit document:

REQUIRED FIELDS:
- lc_number: The LC reference number
- lc_type: Form of documentary credit (IRREVOCABLE, IRREVOCABLE TRANSFERABLE, etc.)
- amount: Credit amount as number
- currency: Currency code (USD, EUR, etc.)
- applicant: Buyer/importer company name
- beneficiary: Seller/exporter company name
- issuing_bank: Bank that issued the LC
- advising_bank: Bank advising the LC
- port_of_loading: Shipment origin port
- port_of_discharge: Destination port
- expiry_date: When LC expires (YYYY-MM-DD)
- latest_shipment_date: Last allowed shipment date (YYYY-MM-DD)
- issue_date: When LC was issued (YYYY-MM-DD)
- incoterm: Trade term (FOB, CIF, etc.)

OPTIONAL FIELDS:
- confirming_bank, ucp_reference, partial_shipments, transshipment
- goods_description, documents_required, payment_terms, available_with

Return ONLY valid JSON. Use null for missing fields.""",

    DocumentType.COMMERCIAL_INVOICE: """Extract the following fields from this Commercial Invoice:

REQUIRED FIELDS:
- invoice_number: Invoice reference
- invoice_date: Date (YYYY-MM-DD)
- invoice_amount: Total amount as number
- currency: Currency code
- seller_name: Seller/exporter name
- buyer_name: Buyer/importer name
- goods_description: Product description
- quantity: Total quantity
- unit_price: Price per unit

OPTIONAL FIELDS:
- po_number, lc_reference, terms, origin_country
- line_items (array of {description, quantity, unit_price, amount})

Return ONLY valid JSON. Use null for missing fields.""",

    DocumentType.BILL_OF_LADING: """Extract the following fields from this Bill of Lading:

REQUIRED FIELDS:
- bl_number: B/L reference number
- bl_date: Date (YYYY-MM-DD)
- shipper: Shipper name
- consignee: Consignee name
- notify_party: Notify party
- vessel_name: Ship name
- voyage_number: Voyage reference
- port_of_loading: Origin port
- port_of_discharge: Destination port
- container_numbers: Container number(s)

OPTIONAL FIELDS:
- goods_description, gross_weight, net_weight, packages
- freight_prepaid, on_board_date, shipped_on_board

Return ONLY valid JSON. Use null for missing fields.""",
}

# Default prompt for other document types
DEFAULT_EXTRACTION_PROMPT = """Extract all relevant fields from this trade document.
Include: dates, amounts, parties, reference numbers, descriptions.
Return ONLY valid JSON. Use null for missing fields."""


class SmartExtractor:
    """
    Smart AI extractor with provider routing.
    
    Routes documents to optimal providers based on characteristics.
    Uses ensemble voting for critical fields.
    """
    
    # Provider strengths
    PROVIDER_STRENGTHS = {
        "openai": {
            "best_for": ["structured_data", "json_output", "mt700"],
            "quality_threshold": 0.5,
            "speed": "fast",
        },
        "anthropic": {
            "best_for": ["numbers", "accuracy", "reasoning", "invoices"],
            "quality_threshold": 0.3,
            "speed": "medium",
        },
        "gemini": {
            "best_for": ["poor_quality", "handwriting", "multilingual", "long_docs"],
            "quality_threshold": 0.0,  # Can handle anything
            "speed": "fast",
        },
    }
    
    # Critical fields that need ensemble verification
    CRITICAL_FIELDS = {
        "lc_number", "amount", "currency", "expiry_date", 
        "latest_shipment_date", "invoice_amount", "bl_number"
    }
    
    def __init__(self):
        self.config = get_v2_config()
        self._providers_cache = None
    
    async def extract_all(
        self,
        documents: List[Tuple[str, DocumentType, str, float, bool]],
    ) -> Dict[str, ExtractionResult]:
        """
        Extract from all documents using smart routing.
        
        Args:
            documents: List of (doc_id, doc_type, text, quality, has_handwriting)
            
        Returns:
            Dict of doc_id -> ExtractionResult
        """
        results = {}
        
        # Process all documents in parallel
        extraction_tasks = [
            self._extract_document(doc_id, doc_type, text, quality, has_hw)
            for doc_id, doc_type, text, quality, has_hw in documents
        ]
        
        extracted = await asyncio.gather(*extraction_tasks, return_exceptions=True)
        
        for i, result in enumerate(extracted):
            doc_id = documents[i][0]
            if isinstance(result, Exception):
                logger.error(f"Extraction failed for {doc_id}: {result}")
                results[doc_id] = self._error_result(doc_id, documents[i][1], str(result))
            else:
                results[doc_id] = result
        
        return results
    
    async def _extract_document(
        self,
        doc_id: str,
        doc_type: DocumentType,
        text: str,
        quality: float,
        has_handwriting: bool,
    ) -> ExtractionResult:
        """Extract from a single document with smart routing."""
        import time
        start = time.perf_counter()
        
        # Select providers based on document characteristics
        providers = self._select_providers(doc_type, quality, has_handwriting)
        
        logger.info(
            f"Extracting {doc_id} ({doc_type.value}): quality={quality:.2f}, "
            f"handwriting={has_handwriting}, providers={providers}"
        )
        
        # Get prompt for document type
        prompt = self._get_prompt(doc_type, text)
        
        # Run selected providers in parallel
        provider_results = await self._run_providers(providers, prompt)
        
        # Parse all results
        parsed_results = []
        for pr in provider_results:
            if pr.success and pr.parsed:
                parsed_results.append((pr.provider, pr.parsed))
        
        if not parsed_results:
            return self._error_result(doc_id, doc_type, "All providers failed")
        
        # Vote on fields
        fields, overall_confidence, agreed = self._vote_on_fields(parsed_results)
        
        # Determine if review needed
        needs_review, review_reasons = self._check_review_needed(
            fields, quality, has_handwriting
        )
        
        latency = int((time.perf_counter() - start) * 1000)
        total_tokens = sum(pr.tokens_in + pr.tokens_out for pr in provider_results)
        
        return ExtractionResult(
            document_id=doc_id,
            document_type=doc_type,
            fields=fields,
            providers_used=[pr.provider for pr in provider_results if pr.success],
            providers_agreed=agreed,
            overall_confidence=overall_confidence,
            needs_review=needs_review,
            review_reasons=review_reasons,
            total_tokens=total_tokens,
            latency_ms=latency,
        )
    
    def _select_providers(
        self,
        doc_type: DocumentType,
        quality: float,
        has_handwriting: bool,
    ) -> List[str]:
        """Select optimal providers for document."""
        available = self.config.ai.available_providers()
        selected = []
        
        # Always need at least one provider
        if not available:
            raise RuntimeError("No AI providers configured")
        
        # Rule 1: Poor quality or handwriting → Gemini
        if quality < 0.6 or has_handwriting:
            if "gemini" in available:
                selected.append("gemini")
        
        # Rule 2: Invoice with amounts → Claude (most accurate)
        if doc_type == DocumentType.COMMERCIAL_INVOICE:
            if "anthropic" in available:
                selected.append("anthropic")
        
        # Rule 3: Structured LC/MT700 → GPT (best at JSON)
        if doc_type in [DocumentType.LETTER_OF_CREDIT, DocumentType.MT700]:
            if "openai" in available:
                selected.append("openai")
        
        # Rule 4: LC always uses ensemble for critical fields
        if doc_type in [DocumentType.LETTER_OF_CREDIT, DocumentType.MT700]:
            # Add remaining providers for ensemble
            for p in available:
                if p not in selected:
                    selected.append(p)
        
        # Ensure at least one provider
        if not selected:
            selected.append(available[0])
        
        # Limit to 3 providers max
        return selected[:3]
    
    def _get_prompt(self, doc_type: DocumentType, text: str) -> str:
        """Get extraction prompt for document type."""
        base_prompt = EXTRACTION_PROMPTS.get(doc_type, DEFAULT_EXTRACTION_PROMPT)
        
        # Truncate text if too long
        max_text = 15000
        if len(text) > max_text:
            text = text[:max_text] + "\n\n[... truncated ...]"
        
        return f"{base_prompt}\n\n---\nDOCUMENT TEXT:\n{text}\n---\n\nReturn ONLY valid JSON:"
    
    async def _run_providers(
        self,
        providers: List[str],
        prompt: str,
    ) -> List[ProviderResult]:
        """Run extraction on multiple providers in parallel."""
        
        async def run_one(provider: str) -> ProviderResult:
            import time
            start = time.perf_counter()
            
            try:
                output, tokens_in, tokens_out = await self._call_provider(
                    provider, prompt
                )
                
                # Parse JSON
                parsed = self._parse_json(output)
                
                return ProviderResult(
                    provider=provider,
                    output=output,
                    parsed=parsed,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    latency_ms=int((time.perf_counter() - start) * 1000),
                    success=parsed is not None,
                    error=None if parsed else "Failed to parse JSON",
                )
                
            except Exception as e:
                logger.error(f"Provider {provider} failed: {e}")
                return ProviderResult(
                    provider=provider,
                    output="",
                    parsed=None,
                    tokens_in=0,
                    tokens_out=0,
                    latency_ms=int((time.perf_counter() - start) * 1000),
                    success=False,
                    error=str(e),
                )
        
        return await asyncio.gather(*[run_one(p) for p in providers])
    
    async def _call_provider(
        self,
        provider: str,
        prompt: str,
    ) -> Tuple[str, int, int]:
        """Call a specific AI provider."""
        from app.services.llm_provider import (
            OpenAIProvider, AnthropicProvider, GeminiProvider
        )
        
        system_prompt = """You are an expert trade finance document parser.
Extract structured data from documents accurately.
OUTPUT: JSON only, no markdown, no explanation."""
        
        if provider == "openai":
            p = OpenAIProvider(model=self.config.ai.openai_model)
        elif provider == "anthropic":
            p = AnthropicProvider(model=self.config.ai.anthropic_model)
        elif provider == "gemini":
            p = GeminiProvider(model=self.config.ai.gemini_model)
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        return await p.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=self.config.ai.max_extraction_tokens,
            temperature=self.config.ai.extraction_temperature,
        )
    
    def _parse_json(self, output: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM output."""
        if not output:
            return None
        
        text = output.strip()
        
        # Try to extract JSON from markdown code blocks
        if "```json" in text:
            try:
                json_str = text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            except (IndexError, json.JSONDecodeError):
                pass
        
        if "```" in text:
            try:
                json_str = text.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            except (IndexError, json.JSONDecodeError):
                pass
        
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON object
        try:
            match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _vote_on_fields(
        self,
        parsed_results: List[Tuple[str, Dict[str, Any]]],
    ) -> Tuple[Dict[str, FieldConfidence], float, List[str]]:
        """Vote on fields across providers."""
        fields = {}
        agreed_providers = set()
        
        # Get all unique field names
        all_fields = set()
        for _, parsed in parsed_results:
            all_fields.update(parsed.keys())
        
        num_providers = len(parsed_results)
        
        for field_name in all_fields:
            # Skip internal fields
            if field_name.startswith("_"):
                continue
            
            # Collect values from each provider
            values = {}
            for provider, parsed in parsed_results:
                if field_name in parsed:
                    values[provider] = parsed[field_name]
            
            if not values:
                continue
            
            # Vote
            value, agreement, agreeing = self._vote_on_value(values)
            
            # Calculate confidence
            is_critical = field_name in self.CRITICAL_FIELDS
            confidence = self._calculate_confidence(
                agreement, num_providers, is_critical
            )
            
            # Track agreement
            if agreement >= 0.66:
                agreed_providers.update(agreeing)
            
            fields[field_name] = FieldConfidence(
                value=value,
                confidence=confidence,
                source="ensemble" if len(values) > 1 else list(values.keys())[0],
                provider_agreement=agreement,
                needs_review=is_critical and agreement < 1.0,
                alternatives=list(values.values()) if agreement < 1.0 else None,
                review_reason=(
                    f"Provider disagreement on critical field"
                    if is_critical and agreement < 1.0 else None
                ),
            )
        
        # Calculate overall confidence
        if fields:
            overall = sum(f.confidence for f in fields.values()) / len(fields)
        else:
            overall = 0.0
        
        return fields, overall, list(agreed_providers)
    
    def _vote_on_value(
        self,
        values: Dict[str, Any],
    ) -> Tuple[Any, float, List[str]]:
        """Vote on a single field value."""
        if len(values) == 1:
            provider = list(values.keys())[0]
            return values[provider], 1.0, [provider]
        
        # Normalize values for comparison
        normalized = {}
        for provider, value in values.items():
            normalized[provider] = self._normalize_value(value)
        
        # Count occurrences
        from collections import Counter
        counts = Counter(normalized.values())
        
        # Find most common
        most_common = counts.most_common(1)[0]
        winning_normalized, count = most_common
        
        # Get original value and agreeing providers
        agreeing = [p for p, v in normalized.items() if v == winning_normalized]
        winning_value = values[agreeing[0]]
        
        agreement = count / len(values)
        
        return winning_value, agreement, agreeing
    
    def _normalize_value(self, value: Any) -> str:
        """Normalize value for comparison."""
        if value is None:
            return "__NULL__"
        
        if isinstance(value, str):
            return re.sub(r'\s+', ' ', value.strip().upper())
        
        if isinstance(value, (int, float)):
            return f"__NUM__{round(float(value), 2)}"
        
        if isinstance(value, list):
            return f"__LIST__{len(value)}"
        
        return str(value).upper()
    
    def _calculate_confidence(
        self,
        agreement: float,
        num_providers: int,
        is_critical: bool,
    ) -> float:
        """Calculate calibrated confidence."""
        if num_providers >= 3:
            if agreement >= 0.99:
                base = 0.98
            elif agreement >= 0.66:
                base = 0.85
            else:
                base = 0.60
        elif num_providers == 2:
            if agreement >= 0.99:
                base = 0.92
            else:
                base = 0.70
        else:
            base = 0.70
        
        # Reduce confidence for critical fields
        if is_critical:
            base *= 0.95
        
        return round(base, 3)
    
    def _check_review_needed(
        self,
        fields: Dict[str, FieldConfidence],
        quality: float,
        has_handwriting: bool,
    ) -> Tuple[bool, List[str]]:
        """Check if document needs manual review."""
        reasons = []
        
        # Check critical fields
        for field_name, field in fields.items():
            if field_name in self.CRITICAL_FIELDS:
                if field.confidence < 0.9:
                    reasons.append(f"Low confidence on {field_name}: {field.confidence:.0%}")
                if field.provider_agreement < 1.0:
                    reasons.append(f"Provider disagreement on {field_name}")
        
        # Check quality
        if quality < 0.5:
            reasons.append("Poor document quality")
        
        # Check handwriting
        if has_handwriting:
            reasons.append("Handwriting detected")
        
        return len(reasons) > 0, reasons
    
    def _error_result(
        self,
        doc_id: str,
        doc_type: DocumentType,
        error: str,
    ) -> ExtractionResult:
        """Create error result."""
        return ExtractionResult(
            document_id=doc_id,
            document_type=doc_type,
            fields={},
            providers_used=[],
            providers_agreed=[],
            overall_confidence=0.0,
            needs_review=True,
            review_reasons=[f"Extraction failed: {error}"],
            total_tokens=0,
            latency_ms=0,
        )

