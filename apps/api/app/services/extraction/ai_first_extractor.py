"""
AI-First Extraction Pipeline

This module implements the AI-first extraction pattern:
1. AI extraction (PRIMARY) - high recall
2. Regex/MT700 validation - verify AI didn't hallucinate
3. Reference data normalization - canonical values
4. Confidence-aware output - trusted/review/untrusted

Why AI-first?
- AI handles format variations better than regex
- AI understands context (e.g., which "port" is loading vs discharge)
- Regex is brittle; AI is flexible
- We use regex to VERIFY, not extract

Flow:
  OCR Text → AI Extraction → Regex Validation → Reference Normalization → Output
                   ↓                ↓                    ↓
            AI confidence    Validator agrees?    Port/Currency lookup
                   ↓                ↓                    ↓
            ──────────────────────────────────────────────────
                              Final Status
            ──────────────────────────────────────────────────
            trusted: AI ≥ 0.8 AND validator agrees
            review:  AI 0.5-0.8 OR validator disagrees
            untrusted: AI < 0.5 AND validator fails
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FieldStatus(str, Enum):
    """Status of an extracted field."""
    TRUSTED = "trusted"
    REVIEW = "review"
    UNTRUSTED = "untrusted"
    NOT_FOUND = "not_found"


@dataclass
class ExtractedFieldResult:
    """Result for a single extracted field."""
    name: str
    value: Any
    normalized_value: Any = None
    ai_confidence: float = 0.0
    validator_agrees: bool = False
    status: FieldStatus = FieldStatus.NOT_FOUND
    issues: List[str] = field(default_factory=list)
    source: str = "ai"  # "ai", "regex", "merged"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.normalized_value or self.value,
            "raw_value": self.value,
            "confidence": round(self.ai_confidence, 3),
            "status": self.status.value,
            "validator_agrees": self.validator_agrees,
            "issues": self.issues,
            "source": self.source,
        }


class AIFirstExtractor:
    """
    AI-first extraction with regex validation.
    
    This is the recommended extraction pattern for LCopilot:
    1. Run AI extraction (handles any format)
    2. Run regex validators (catches hallucinations)
    3. Normalize with reference data (canonical values)
    4. Produce confidence-aware output
    """
    
    # Confidence thresholds
    TRUSTED_THRESHOLD = 0.8
    REVIEW_THRESHOLD = 0.5
    
    # Field validators (regex patterns to validate AI output)
    VALIDATORS = {
        "lc_number": {
            "pattern": r"^[A-Z0-9][A-Z0-9\-\/]{2,34}$",
            "flags": re.I,
            "description": "LC number should be 3-35 alphanumeric chars",
        },
        "amount": {
            "pattern": r"^\d+(?:\.\d{1,4})?$",
            "flags": 0,
            "description": "Amount should be a valid number",
        },
        "currency": {
            "pattern": r"^[A-Z]{3}$",
            "flags": 0,
            "description": "Currency should be 3-letter ISO code",
        },
        "expiry_date": {
            "pattern": r"^\d{4}-\d{2}-\d{2}$|^\d{2}[\/\-]\d{2}[\/\-]\d{4}$",
            "flags": 0,
            "description": "Date should be YYYY-MM-DD or DD/MM/YYYY",
        },
        "latest_shipment_date": {
            "pattern": r"^\d{4}-\d{2}-\d{2}$|^\d{2}[\/\-]\d{2}[\/\-]\d{4}$",
            "flags": 0,
            "description": "Date should be YYYY-MM-DD or DD/MM/YYYY",
        },
        "incoterm": {
            "pattern": r"^(EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|FOB|CFR|CIF)$",
            "flags": re.I,
            "description": "Should be a valid Incoterm",
        },
    }
    
    def __init__(self):
        # Lazy load reference registries
        self._port_registry = None
        self._currency_registry = None
    
    @property
    def port_registry(self):
        if self._port_registry is None:
            from app.reference_data.ports import get_port_registry
            self._port_registry = get_port_registry()
        return self._port_registry
    
    @property
    def currency_registry(self):
        if self._currency_registry is None:
            from app.reference_data.currencies import get_currency_registry
            self._currency_registry = get_currency_registry()
        return self._currency_registry
    
    async def extract_lc(
        self,
        raw_text: str,
        use_fallback_on_ai_failure: bool = True,
    ) -> Dict[str, Any]:
        """
        Extract LC fields using AI-first pattern.
        
        Args:
            raw_text: OCR/document text
            use_fallback_on_ai_failure: If AI fails, fall back to regex
            
        Returns:
            Structured LC data with confidence metadata
        """
        if not raw_text or not raw_text.strip():
            return self._empty_result("empty_input")
        
        # Step 1: AI Extraction (PRIMARY)
        ai_result, ai_provider = await self._run_ai_extraction(raw_text)
        
        if not ai_result and use_fallback_on_ai_failure:
            logger.warning("AI extraction failed, using regex fallback")
            return await self._regex_fallback(raw_text)
        
        if not ai_result:
            return self._empty_result("ai_failed")
        
        # Step 2: Process each field through validation + normalization
        fields: Dict[str, ExtractedFieldResult] = {}
        
        for field_name, ai_value in ai_result.items():
            if field_name.startswith("_"):  # Skip metadata
                continue
            
            field_result = self._process_field(
                field_name,
                ai_value,
                raw_text,
            )
            fields[field_name] = field_result
        
        # Step 3: Build output structure
        return self._build_output(fields, ai_provider)
    
    async def _run_ai_extraction(
        self,
        raw_text: str,
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """Run AI extraction."""
        try:
            from .ai_lc_extractor import extract_lc_with_ai
            
            ai_result, confidence, provider = await extract_lc_with_ai(
                raw_text,
                temperature=0.1,  # More deterministic
            )
            
            if not ai_result:
                return None, "none"
            
            # Add per-field confidence if not present
            # (For now, use overall confidence; can be enhanced)
            for key in ai_result:
                if isinstance(ai_result[key], dict) and "confidence" in ai_result[key]:
                    continue
                if ai_result[key] is not None:
                    ai_result[key] = {
                        "value": ai_result[key],
                        "confidence": confidence,
                    }
            
            logger.info(
                "AI extraction complete: provider=%s confidence=%.2f fields=%d",
                provider, confidence, len(ai_result)
            )
            
            return ai_result, provider
            
        except Exception as e:
            logger.error(f"AI extraction error: {e}", exc_info=True)
            return None, "error"
    
    def _process_field(
        self,
        field_name: str,
        ai_value: Any,
        raw_text: str,
    ) -> ExtractedFieldResult:
        """Process a single field through validation and normalization."""
        # Handle different AI output formats
        if isinstance(ai_value, dict):
            value = ai_value.get("value")
            ai_confidence = float(ai_value.get("confidence", 0.5))
        else:
            value = ai_value
            ai_confidence = 0.5
        
        # Empty value
        if value is None or (isinstance(value, str) and not value.strip()):
            return ExtractedFieldResult(
                name=field_name,
                value=None,
                ai_confidence=0.0,
                status=FieldStatus.NOT_FOUND,
            )
        
        # Clean string values
        if isinstance(value, str):
            value = value.strip()
        
        # Step 1: Regex validation (if we have a validator)
        validator_agrees = True
        issues = []
        
        if field_name in self.VALIDATORS:
            validator = self.VALIDATORS[field_name]
            pattern = re.compile(validator["pattern"], validator.get("flags", 0))
            str_value = str(value)
            
            if not pattern.match(str_value):
                validator_agrees = False
                issues.append(f"Format validation failed: {validator['description']}")
        
        # Step 2: Cross-check with regex extraction from raw text
        regex_value = self._regex_extract_field(field_name, raw_text)
        if regex_value:
            # Normalize both for comparison
            ai_normalized = self._normalize_for_comparison(field_name, value)
            regex_normalized = self._normalize_for_comparison(field_name, regex_value)
            
            if ai_normalized != regex_normalized:
                # AI and regex disagree
                if not validator_agrees:
                    # Both validation failed and regex different - untrust AI
                    issues.append(f"AI/regex mismatch: AI='{value}' vs regex='{regex_value}'")
                else:
                    # Validator passed but regex different - flag for review
                    issues.append(f"Regex found different value: '{regex_value}'")
        
        # Step 3: Normalize with reference data
        normalized_value = self._normalize_field(field_name, value)
        
        # Step 4: Determine status
        status = self._determine_status(ai_confidence, validator_agrees, issues)
        
        return ExtractedFieldResult(
            name=field_name,
            value=value,
            normalized_value=normalized_value,
            ai_confidence=ai_confidence,
            validator_agrees=validator_agrees,
            status=status,
            issues=issues,
            source="ai",
        )
    
    def _regex_extract_field(self, field_name: str, raw_text: str) -> Optional[str]:
        """Extract field using regex (for cross-validation)."""
        patterns = {
            "lc_number": r"(?:LC|L/C|Credit).*?(?:No\.?|Number|Ref)\s*[:\-]?\s*([A-Z0-9\-\/]+)",
            "amount": r"(?:Amount|Value)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)",
            "currency": r"(?:Currency|CCY)\s*[:\-]?\s*([A-Z]{3})|([A-Z]{3})\s+[\d,]+\.\d{2}",
            "port_of_loading": r"(?:Port of Loading|POL|Loading Port)\s*[:\-]?\s*([^\n]+)",
            "port_of_discharge": r"(?:Port of Discharge|POD|Destination)\s*[:\-]?\s*([^\n]+)",
            "applicant": r"(?:Applicant|Buyer|Importer)\s*[:\-]?\s*([^\n]+)",
            "beneficiary": r"(?:Beneficiary|Seller|Exporter)\s*[:\-]?\s*([^\n]+)",
        }
        
        if field_name not in patterns:
            return None
        
        match = re.search(patterns[field_name], raw_text, re.I)
        if match:
            # Return first non-empty group
            for group in match.groups():
                if group:
                    return group.strip()
        return None
    
    def _normalize_for_comparison(self, field_name: str, value: Any) -> str:
        """Normalize value for comparison."""
        if value is None:
            return ""
        s = str(value).strip().upper()
        # Remove common variations
        s = re.sub(r'[,\s\-\/]', '', s)
        return s
    
    def _normalize_field(self, field_name: str, value: Any) -> Any:
        """Normalize field using reference data."""
        if value is None:
            return None
        
        if field_name in ("port_of_loading", "port_of_discharge"):
            port = self.port_registry.resolve(str(value))
            if port:
                return port.full_name
            return str(value)
        
        if field_name == "currency":
            normalized = self.currency_registry.normalize(str(value))
            if normalized:
                return normalized
            return str(value).upper()
        
        if field_name == "amount":
            try:
                # Remove commas, convert to float
                clean = str(value).replace(",", "").strip()
                return float(clean)
            except ValueError:
                return value
        
        if field_name == "incoterm":
            return str(value).upper()
        
        return value
    
    def _determine_status(
        self,
        ai_confidence: float,
        validator_agrees: bool,
        issues: List[str],
    ) -> FieldStatus:
        """Determine field status based on confidence and validation."""
        # High AI confidence + validator agrees = trusted
        if ai_confidence >= self.TRUSTED_THRESHOLD and validator_agrees and not issues:
            return FieldStatus.TRUSTED
        
        # Medium confidence or validator disagrees = review
        if ai_confidence >= self.REVIEW_THRESHOLD:
            return FieldStatus.REVIEW
        
        # Low confidence = untrusted
        return FieldStatus.UNTRUSTED
    
    def _build_output(
        self,
        fields: Dict[str, ExtractedFieldResult],
        ai_provider: str,
    ) -> Dict[str, Any]:
        """Build final output structure."""
        # Main output with normalized values
        output: Dict[str, Any] = {}
        
        for name, field in fields.items():
            output[name] = field.normalized_value or field.value
        
        # Calculate aggregate confidence
        confidences = [f.ai_confidence for f in fields.values() if f.status != FieldStatus.NOT_FOUND]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Count statuses
        status_counts = {
            "trusted": sum(1 for f in fields.values() if f.status == FieldStatus.TRUSTED),
            "review": sum(1 for f in fields.values() if f.status == FieldStatus.REVIEW),
            "untrusted": sum(1 for f in fields.values() if f.status == FieldStatus.UNTRUSTED),
            "not_found": sum(1 for f in fields.values() if f.status == FieldStatus.NOT_FOUND),
        }
        
        # Determine overall status
        if status_counts["untrusted"] > 0:
            overall_status = "needs_review"
        elif status_counts["review"] > 0:
            overall_status = "review_advised"
        elif status_counts["not_found"] > 2:  # Missing too many critical fields
            overall_status = "incomplete"
        else:
            overall_status = "confident"
        
        # Add metadata
        output["_extraction_method"] = "ai_first"
        output["_extraction_confidence"] = round(avg_confidence, 3)
        output["_ai_provider"] = ai_provider
        output["_status"] = overall_status
        output["_field_details"] = {
            name: field.to_dict() for name, field in fields.items()
        }
        output["_status_counts"] = status_counts
        
        logger.info(
            "AI-first extraction complete: status=%s confidence=%.2f trusted=%d review=%d untrusted=%d",
            overall_status, avg_confidence,
            status_counts["trusted"],
            status_counts["review"],
            status_counts["untrusted"],
        )
        
        return output
    
    async def _regex_fallback(self, raw_text: str) -> Dict[str, Any]:
        """Fall back to pure regex extraction when AI fails."""
        from .lc_extractor import extract_lc_structured
        
        result = extract_lc_structured(raw_text)
        result["_extraction_method"] = "regex_fallback"
        result["_status"] = "ai_failed_regex_used"
        
        return result
    
    def _empty_result(self, reason: str) -> Dict[str, Any]:
        """Return empty result with reason."""
        return {
            "_extraction_method": "none",
            "_extraction_confidence": 0.0,
            "_status": "failed",
            "_failure_reason": reason,
        }


# Global instance
_extractor: Optional[AIFirstExtractor] = None


def get_ai_first_extractor() -> AIFirstExtractor:
    """Get or create the AI-first extractor."""
    global _extractor
    if _extractor is None:
        _extractor = AIFirstExtractor()
    return _extractor


async def extract_lc_ai_first(raw_text: str) -> Dict[str, Any]:
    """
    Convenience function for AI-first LC extraction.
    
    This is the RECOMMENDED extraction function for LCopilot.
    """
    extractor = get_ai_first_extractor()
    return await extractor.extract_lc(raw_text)


# =====================================================================
# INVOICE AI-FIRST EXTRACTOR
# =====================================================================

INVOICE_EXTRACTION_SYSTEM_PROMPT = """You are an expert trade finance document parser specializing in Commercial Invoices.

Your task is to extract structured data from invoice documents used in international trade.
These documents may be bank-formatted PDFs, scanned documents, or plain text.

IMPORTANT RULES:
1. Extract ONLY what is explicitly stated in the document
2. If a field is not found, return null - do NOT guess
3. For amounts, include the full number without currency symbols
4. For dates, use ISO format (YYYY-MM-DD) when possible
5. Look for LC/Credit reference numbers - they link the invoice to the LC
6. Be precise - banks rely on exact data for documentary credit compliance

OUTPUT FORMAT: JSON only, no markdown, no explanation."""

INVOICE_EXTRACTION_PROMPT = """Extract the following fields from this Commercial Invoice:

REQUIRED FIELDS:
- invoice_number: The invoice reference number
- invoice_date: The date of the invoice (ISO format if possible)
- amount: The total invoice amount as a number
- currency: The currency code (e.g., "USD", "EUR")
- seller_name: The seller/exporter company name
- buyer_name: The buyer/importer company name
- lc_reference: The Letter of Credit number (if mentioned)

OPTIONAL FIELDS:
- seller_address: Full address of the seller
- buyer_address: Full address of the buyer
- goods_description: Description of goods
- quantity: Quantity of goods
- unit_price: Price per unit
- incoterm: Trade term (FOB, CIF, etc.)
- country_of_origin: Where goods originate
- port_of_loading: Shipment origin
- port_of_discharge: Destination port

Return a JSON object with these fields. Use null for any field not found.

---
DOCUMENT TEXT:
{document_text}
---

Return ONLY valid JSON, no other text:"""


class InvoiceAIFirstExtractor(AIFirstExtractor):
    """AI-first extractor for Commercial Invoices."""
    
    VALIDATORS = {
        "invoice_number": {
            "pattern": r"^[A-Z0-9][A-Z0-9\-\/\.]{1,30}$",
            "flags": re.I,
            "description": "Invoice number should be alphanumeric",
        },
        "amount": {
            "pattern": r"^\d+(?:\.\d{1,4})?$",
            "flags": 0,
            "description": "Amount should be a valid number",
        },
        "currency": {
            "pattern": r"^[A-Z]{3}$",
            "flags": 0,
            "description": "Currency should be 3-letter ISO code",
        },
        "invoice_date": {
            "pattern": r"^\d{4}-\d{2}-\d{2}$|^\d{2}[\/\-]\d{2}[\/\-]\d{4}$",
            "flags": 0,
            "description": "Date should be YYYY-MM-DD or DD/MM/YYYY",
        },
        "lc_reference": {
            "pattern": r"^[A-Z0-9][A-Z0-9\-\/]{2,34}$",
            "flags": re.I,
            "description": "LC reference should be alphanumeric",
        },
        "incoterm": {
            "pattern": r"^(EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|FOB|CFR|CIF)$",
            "flags": re.I,
            "description": "Should be a valid Incoterm",
        },
    }
    
    async def extract_invoice(
        self,
        raw_text: str,
        use_fallback_on_ai_failure: bool = True,
    ) -> Dict[str, Any]:
        """Extract invoice fields using AI-first pattern."""
        if not raw_text or not raw_text.strip():
            return self._empty_result("empty_input")
        
        # Run AI extraction
        ai_result, ai_provider = await self._run_invoice_ai_extraction(raw_text)
        
        if not ai_result and use_fallback_on_ai_failure:
            logger.warning("AI invoice extraction failed, using regex fallback")
            return self._invoice_regex_fallback(raw_text)
        
        if not ai_result:
            return self._empty_result("ai_failed")
        
        # Process fields
        fields: Dict[str, ExtractedFieldResult] = {}
        for field_name, ai_value in ai_result.items():
            if field_name.startswith("_"):
                continue
            field_result = self._process_field(field_name, ai_value, raw_text)
            fields[field_name] = field_result
        
        return self._build_output(fields, ai_provider, doc_type="invoice")
    
    async def _run_invoice_ai_extraction(
        self,
        raw_text: str,
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """Run AI extraction for invoice."""
        try:
            from ..llm_provider import LLMProviderFactory
            
            provider = LLMProviderFactory.get_provider()
            if not provider:
                logger.warning("No LLM provider available for invoice extraction")
                return None, "none"
            
            prompt = INVOICE_EXTRACTION_PROMPT.format(
                document_text=raw_text[:12000]
            )
            
            response = await provider.generate(
                prompt=prompt,
                system_prompt=INVOICE_EXTRACTION_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=2000,
            )
            
            if not response:
                return None, "empty_response"
            
            # Parse JSON response
            import json
            try:
                # Clean response
                clean = response.strip()
                if clean.startswith("```"):
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                
                result = json.loads(clean)
                
                # Add confidence to each field
                for key in result:
                    if result[key] is not None:
                        result[key] = {"value": result[key], "confidence": 0.75}
                
                return result, provider.__class__.__name__
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse AI invoice response: {e}")
                return None, "parse_error"
                
        except Exception as e:
            logger.error(f"Invoice AI extraction error: {e}", exc_info=True)
            return None, "error"
    
    def _invoice_regex_fallback(self, raw_text: str) -> Dict[str, Any]:
        """Regex fallback for invoice extraction."""
        result: Dict[str, Any] = {}
        
        # Invoice number
        match = re.search(r"Invoice\s*(?:No\.?|Number|#)\s*[:\-]?\s*([A-Z0-9\-\/]+)", raw_text, re.I)
        if match:
            result["invoice_number"] = match.group(1).strip()
        
        # Amount
        match = re.search(r"Total\s*[:\-]?\s*([A-Z]{3})?\s*([\d,]+(?:\.\d{2})?)", raw_text, re.I)
        if match:
            if match.group(1):
                result["currency"] = match.group(1)
            result["amount"] = match.group(2).replace(",", "")
        
        # LC Reference
        match = re.search(r"(?:L/?C|Letter of Credit|Credit)\s*(?:No\.?|Ref|#)\s*[:\-]?\s*([A-Z0-9\-\/]+)", raw_text, re.I)
        if match:
            result["lc_reference"] = match.group(1).strip()
        
        result["_extraction_method"] = "regex_fallback"
        result["_status"] = "ai_failed_regex_used"
        return result
    
    def _build_output(
        self,
        fields: Dict[str, ExtractedFieldResult],
        ai_provider: str,
        doc_type: str = "invoice",
    ) -> Dict[str, Any]:
        """Build output with document type."""
        output = super()._build_output(fields, ai_provider)
        output["_document_type"] = doc_type
        return output


# =====================================================================
# BILL OF LADING AI-FIRST EXTRACTOR
# =====================================================================

BL_EXTRACTION_SYSTEM_PROMPT = """You are an expert trade finance document parser specializing in Bills of Lading (B/L).

Your task is to extract structured data from Bill of Lading documents used in international shipping.
These may be ocean B/Ls, air waybills, or multimodal transport documents.

IMPORTANT RULES:
1. Extract ONLY what is explicitly stated in the document
2. If a field is not found, return null - do NOT guess
3. For dates, use ISO format (YYYY-MM-DD) when possible
4. The "shipped on board" date is CRITICAL for LC compliance
5. Port names should be extracted exactly as written
6. Be precise - banks rely on exact data

OUTPUT FORMAT: JSON only, no markdown, no explanation."""

BL_EXTRACTION_PROMPT = """Extract the following fields from this Bill of Lading:

REQUIRED FIELDS:
- bl_number: The B/L reference number
- shipper: The shipper/exporter name
- consignee: The consignee (may be "TO ORDER OF [BANK]")
- notify_party: The party to notify
- port_of_loading: Where goods are loaded
- port_of_discharge: Where goods are discharged
- shipped_on_board_date: The date goods were shipped (CRITICAL)
- vessel_name: Name of the vessel

OPTIONAL FIELDS:
- voyage_number: Voyage reference
- goods_description: Description of goods
- gross_weight: Total weight
- number_of_packages: Package count
- container_number: Container ID
- seal_number: Seal ID
- freight_terms: "PREPAID" or "COLLECT"
- place_of_receipt: Where carrier received goods
- place_of_delivery: Final delivery location

Return a JSON object with these fields. Use null for any field not found.

---
DOCUMENT TEXT:
{document_text}
---

Return ONLY valid JSON, no other text:"""


class BLAIFirstExtractor(AIFirstExtractor):
    """AI-first extractor for Bills of Lading."""
    
    VALIDATORS = {
        "bl_number": {
            "pattern": r"^[A-Z]{2,4}[A-Z0-9\-\/]{4,20}$",
            "flags": re.I,
            "description": "B/L number should follow carrier format",
        },
        "shipped_on_board_date": {
            "pattern": r"^\d{4}-\d{2}-\d{2}$|^\d{2}[\/\-]\d{2}[\/\-]\d{4}$",
            "flags": 0,
            "description": "Date should be YYYY-MM-DD or DD/MM/YYYY",
        },
        "freight_terms": {
            "pattern": r"^(PREPAID|COLLECT|FREIGHT PREPAID|FREIGHT COLLECT)$",
            "flags": re.I,
            "description": "Should be PREPAID or COLLECT",
        },
    }
    
    async def extract_bl(
        self,
        raw_text: str,
        use_fallback_on_ai_failure: bool = True,
    ) -> Dict[str, Any]:
        """Extract B/L fields using AI-first pattern."""
        if not raw_text or not raw_text.strip():
            return self._empty_result("empty_input")
        
        # Run AI extraction
        ai_result, ai_provider = await self._run_bl_ai_extraction(raw_text)
        
        if not ai_result and use_fallback_on_ai_failure:
            logger.warning("AI B/L extraction failed, using regex fallback")
            return self._bl_regex_fallback(raw_text)
        
        if not ai_result:
            return self._empty_result("ai_failed")
        
        # Process fields
        fields: Dict[str, ExtractedFieldResult] = {}
        for field_name, ai_value in ai_result.items():
            if field_name.startswith("_"):
                continue
            field_result = self._process_field(field_name, ai_value, raw_text)
            fields[field_name] = field_result
        
        return self._build_output(fields, ai_provider, doc_type="bill_of_lading")
    
    async def _run_bl_ai_extraction(
        self,
        raw_text: str,
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """Run AI extraction for B/L."""
        try:
            from ..llm_provider import LLMProviderFactory
            
            provider = LLMProviderFactory.get_provider()
            if not provider:
                logger.warning("No LLM provider available for B/L extraction")
                return None, "none"
            
            prompt = BL_EXTRACTION_PROMPT.format(
                document_text=raw_text[:12000]
            )
            
            response = await provider.generate(
                prompt=prompt,
                system_prompt=BL_EXTRACTION_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=2000,
            )
            
            if not response:
                return None, "empty_response"
            
            # Parse JSON response
            import json
            try:
                clean = response.strip()
                if clean.startswith("```"):
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                
                result = json.loads(clean)
                
                # Add confidence to each field
                for key in result:
                    if result[key] is not None:
                        result[key] = {"value": result[key], "confidence": 0.75}
                
                return result, provider.__class__.__name__
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse AI B/L response: {e}")
                return None, "parse_error"
                
        except Exception as e:
            logger.error(f"B/L AI extraction error: {e}", exc_info=True)
            return None, "error"
    
    def _bl_regex_fallback(self, raw_text: str) -> Dict[str, Any]:
        """Regex fallback for B/L extraction."""
        result: Dict[str, Any] = {}
        
        # B/L number
        match = re.search(r"B/?L\s*(?:No\.?|Number|#)\s*[:\-]?\s*([A-Z0-9\-\/]+)", raw_text, re.I)
        if match:
            result["bl_number"] = match.group(1).strip()
        
        # Shipper
        match = re.search(r"Shipper\s*[:\-]?\s*([^\n]+)", raw_text, re.I)
        if match:
            result["shipper"] = match.group(1).strip()
        
        # Consignee
        match = re.search(r"Consignee\s*[:\-]?\s*([^\n]+)", raw_text, re.I)
        if match:
            result["consignee"] = match.group(1).strip()
        
        # Port of Loading
        match = re.search(r"Port of Loading\s*[:\-]?\s*([^\n]+)", raw_text, re.I)
        if match:
            result["port_of_loading"] = match.group(1).strip()
        
        # Port of Discharge
        match = re.search(r"Port of Discharge\s*[:\-]?\s*([^\n]+)", raw_text, re.I)
        if match:
            result["port_of_discharge"] = match.group(1).strip()
        
        # Shipped on board date
        match = re.search(r"(?:Shipped|On Board|Laden)\s*(?:Date)?\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}-\d{2}-\d{2})", raw_text, re.I)
        if match:
            result["shipped_on_board_date"] = match.group(1).strip()
        
        result["_extraction_method"] = "regex_fallback"
        result["_status"] = "ai_failed_regex_used"
        return result
    
    def _build_output(
        self,
        fields: Dict[str, ExtractedFieldResult],
        ai_provider: str,
        doc_type: str = "bill_of_lading",
    ) -> Dict[str, Any]:
        """Build output with document type."""
        output = super()._build_output(fields, ai_provider)
        output["_document_type"] = doc_type
        return output


# =====================================================================
# GLOBAL INSTANCES AND CONVENIENCE FUNCTIONS
# =====================================================================

_invoice_extractor: Optional[InvoiceAIFirstExtractor] = None
_bl_extractor: Optional[BLAIFirstExtractor] = None


def get_invoice_ai_first_extractor() -> InvoiceAIFirstExtractor:
    """Get or create the invoice AI-first extractor."""
    global _invoice_extractor
    if _invoice_extractor is None:
        _invoice_extractor = InvoiceAIFirstExtractor()
    return _invoice_extractor


def get_bl_ai_first_extractor() -> BLAIFirstExtractor:
    """Get or create the B/L AI-first extractor."""
    global _bl_extractor
    if _bl_extractor is None:
        _bl_extractor = BLAIFirstExtractor()
    return _bl_extractor


async def extract_invoice_ai_first(raw_text: str) -> Dict[str, Any]:
    """
    Convenience function for AI-first invoice extraction.
    """
    extractor = get_invoice_ai_first_extractor()
    return await extractor.extract_invoice(raw_text)


async def extract_bl_ai_first(raw_text: str) -> Dict[str, Any]:
    """
    Convenience function for AI-first B/L extraction.
    """
    extractor = get_bl_ai_first_extractor()
    return await extractor.extract_bl(raw_text)

