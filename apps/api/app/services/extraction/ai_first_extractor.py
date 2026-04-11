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

import json
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _resolve_llm_trace(provider: Any, provider_used: str, router_layer: str = "L1") -> Dict[str, Any]:
    model = None
    if provider is not None:
        model = getattr(provider, "model", None)
    if not model:
        model = (
            os.getenv(f"AI_ROUTER_{router_layer}_PRIMARY_MODEL")
            or os.getenv("OPENROUTER_MODEL_VERSION")
            or os.getenv("LLM_PRIMARY_MODEL")
            or os.getenv("LLM_MODEL_VERSION")
        )
    return {
        "provider": provider_used or "unknown",
        "model": model or "unknown",
        "router_layer": router_layer,
    }


def _log_ai_first_event(event: str, **payload: Any) -> None:
    safe_payload = {k: v for k, v in payload.items() if v is not None}
    logger.info("ai_first.telemetry %s", json.dumps({"event": event, **safe_payload}, default=str))


def _is_two_stage_enabled() -> bool:
    return os.getenv("EXTRACTION_TWO_STAGE", "true").strip().lower() in ("1", "true", "yes", "on")


def _resolve_extraction_config() -> Dict[str, Any]:
    two_stage = _is_two_stage_enabled()

    if two_stage:
        # Stage 1: cheap model does the heavy lifting
        primary_provider = os.getenv("EXTRACTION_CHEAP_PROVIDER") or os.getenv("LLM_PROVIDER", "openrouter")
        primary_model = os.getenv("EXTRACTION_CHEAP_MODEL") or "openai/gpt-4o-mini"
    else:
        # Single-stage: use the primary (expensive) model directly
        primary_provider = os.getenv("EXTRACTION_PRIMARY_PROVIDER") or os.getenv("LLM_PROVIDER", "openrouter")
        primary_model = (
            os.getenv("EXTRACTION_PRIMARY_MODEL")
            or os.getenv("OPENROUTER_MODEL_VERSION")
            or os.getenv("LLM_PRIMARY_MODEL")
            or os.getenv("LLM_MODEL_VERSION")
            or "anthropic/claude-sonnet-4-6"
        )

    fallback_provider = os.getenv("EXTRACTION_FALLBACK_PROVIDER") or primary_provider
    fallback_model = (
        os.getenv("EXTRACTION_FALLBACK_MODEL")
        or os.getenv("LLM_FALLBACK_MODEL")
        or primary_model
    )
    max_tokens = int(os.getenv("EXTRACTION_MAX_TOKENS") or "2000")
    return {
        "primary_provider": primary_provider,
        "primary_model": primary_model,
        "fallback_provider": fallback_provider,
        "fallback_model": fallback_model,
        "max_tokens": max_tokens,
        "two_stage": two_stage,
    }


async def _generate_extraction_with_model_routing(
    prompt: str,
    system_prompt: str,
    *,
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
) -> Tuple[str, int, int, str, Dict[str, Any]]:
    from ..llm_provider import LLMProviderFactory

    extraction_cfg = _resolve_extraction_config()
    effective_max_tokens = max_tokens or extraction_cfg["max_tokens"]

    response, tokens_in, tokens_out, provider_used = await LLMProviderFactory.generate_with_fallback(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=effective_max_tokens,
        primary_provider=extraction_cfg["primary_provider"],
        model_override=extraction_cfg["primary_model"],
        fallback_provider=extraction_cfg["fallback_provider"],
        fallback_model=extraction_cfg["fallback_model"],
        extraction_mode=True,
    )
    llm_trace = {
        "provider": provider_used or extraction_cfg["primary_provider"],
        "model": extraction_cfg["primary_model"],
        "router_layer": "EXTRACTION",
        "fallback_provider": extraction_cfg["fallback_provider"],
        "fallback_model": extraction_cfg["fallback_model"],
        "two_stage": extraction_cfg.get("two_stage", False),
    }
    return response, tokens_in, tokens_out, provider_used, llm_trace


# ---------------------------------------------------------------------------
# Two-stage review: Sonnet cross-checks the cheap model's extraction
# ---------------------------------------------------------------------------

_REVIEW_SYSTEM_PROMPT = (
    "You are a quality-control reviewer for trade document extraction. "
    "You receive the SOURCE TEXT of a document and a JSON extraction produced by a junior model. "
    "Cross-check every field in the JSON against the source text.\n\n"
    "Rules:\n"
    "1. VERBATIM — every value must match the source text EXACTLY as printed. "
    "Do NOT correct, modernize, translate, or rename anything.\n"
    "2. If the JSON has a value that does NOT appear in the source text, REMOVE that key (hallucination).\n"
    "3. If the source text has a clearly labeled field that the JSON missed, ADD it with the exact printed value.\n"
    "4. If a value is slightly wrong (typo, truncation, extra text from a different field), FIX it to match the source exactly.\n"
    "5. Preserve the original JSON keys. Do not rename keys.\n"
    "6. Return ONLY the corrected JSON object. No prose, no markdown fences."
)


async def _review_extraction(
    source_text: str,
    extracted_json: Dict[str, Any],
    doc_type: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Stage 2: Sonnet reviews the cheap model's extraction against the source text.

    Returns (reviewed_json, review_trace). If review fails or is disabled,
    returns (extracted_json, trace_with_skipped_reason).
    """
    if not _is_two_stage_enabled():
        return extracted_json, {"reviewed": False, "reason": "two_stage_disabled"}

    review_provider = os.getenv("EXTRACTION_REVIEW_PROVIDER") or os.getenv("EXTRACTION_PRIMARY_PROVIDER") or "openrouter"
    review_model = (
        os.getenv("EXTRACTION_REVIEW_MODEL")
        or os.getenv("EXTRACTION_PRIMARY_MODEL")
        or "anthropic/claude-sonnet-4-6"
    )

    # Build a compact prompt — source text + cheap JSON
    # Truncate to keep costs low: source 8K chars, JSON 4K chars
    clean_json = {k: v for k, v in extracted_json.items() if not k.startswith("_")}
    review_prompt = (
        f"DOCUMENT TYPE: {doc_type}\n\n"
        f"SOURCE TEXT (verbatim from the uploaded document):\n"
        f"---\n{source_text[:8000]}\n---\n\n"
        f"EXTRACTED JSON (by junior model — may contain errors):\n"
        f"{json.dumps(clean_json, indent=2, default=str)[:4000]}\n\n"
        f"Cross-check every field against the source text. Return corrected JSON only."
    )

    review_trace: Dict[str, Any] = {
        "reviewed": True,
        "review_provider": review_provider,
        "review_model": review_model,
        "doc_type": doc_type,
        "original_field_count": len(clean_json),
    }

    try:
        from ..llm_provider import LLMProviderFactory

        response, tokens_in, tokens_out, _ = await LLMProviderFactory.generate_with_fallback(
            prompt=review_prompt,
            system_prompt=_REVIEW_SYSTEM_PROMPT,
            temperature=0.0,
            max_tokens=2000,
            primary_provider=review_provider,
            model_override=review_model,
            extraction_mode=True,
        )
        review_trace["tokens_in"] = tokens_in
        review_trace["tokens_out"] = tokens_out

        if not response:
            review_trace["outcome"] = "empty_response"
            logger.warning("Two-stage review returned empty for %s — using original", doc_type)
            return extracted_json, review_trace

        # Parse the reviewed JSON
        candidate = _extract_candidate_json_text(response)
        try:
            reviewed = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            reviewed = None
        if not isinstance(reviewed, dict) or not reviewed:
            reviewed = await _parse_llm_json_with_repair(None, response)

        if isinstance(reviewed, dict) and reviewed:
            # Carry over internal metadata from original
            for k, v in extracted_json.items():
                if k.startswith("_") and k not in reviewed:
                    reviewed[k] = v
            review_trace["outcome"] = "success"
            review_trace["reviewed_field_count"] = len({k for k in reviewed if not k.startswith("_")})
            fields_added = set(reviewed.keys()) - set(extracted_json.keys()) - {"_"}
            fields_removed = set(extracted_json.keys()) - set(reviewed.keys()) - {k for k in extracted_json if k.startswith("_")}
            review_trace["fields_added"] = list(fields_added)[:10]
            review_trace["fields_removed"] = list(fields_removed)[:10]
            logger.info(
                "Two-stage review [%s]: %d→%d fields, +%d -%d",
                doc_type, len(clean_json), review_trace["reviewed_field_count"],
                len(fields_added), len(fields_removed),
            )
            return reviewed, review_trace
        else:
            review_trace["outcome"] = "parse_error"
            logger.warning("Two-stage review parse failed for %s — using original", doc_type)
            return extracted_json, review_trace

    except Exception as exc:
        review_trace["outcome"] = "error"
        review_trace["error"] = str(exc)[:200]
        logger.warning("Two-stage review failed for %s: %s — using original", doc_type, exc)
        return extracted_json, review_trace


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
    verification: str = "not_found"
    evidence: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.normalized_value or self.value,
            "raw_value": self.value,
            "confidence": round(self.ai_confidence, 3),
            "status": self.status.value,
            "validator_agrees": self.validator_agrees,
            "issues": self.issues,
            "source": self.source,
            "verification": self.verification,
            "evidence": self.evidence,
        }


def _derive_field_verification(
    *,
    status: FieldStatus,
    validator_agrees: bool,
    issues: List[str],
    evidence: Optional[Dict[str, Any]],
) -> str:
    if status == FieldStatus.NOT_FOUND:
        return "not_found"
    if evidence and validator_agrees and not issues:
        return "confirmed"
    if evidence and (validator_agrees or status == FieldStatus.REVIEW):
        return "text_supported"
    return "model_suggested"


def _build_text_evidence(
    raw_text: str,
    value: Any,
    *,
    source: str,
    strategy: str,
) -> Optional[Dict[str, Any]]:
    candidate = str(value or "").strip()
    text = str(raw_text or "")
    if not candidate or not text:
        return None

    escaped = re.escape(candidate)
    match = re.search(escaped, text, re.IGNORECASE)
    snippet: Optional[str] = None
    if match:
        start = max(0, match.start() - 40)
        end = min(len(text), match.end() + 40)
        snippet = text[start:end].replace("\n", " ").strip()
    elif len(candidate) >= 5:
        normalized_candidate = re.sub(r"[\s,:\-\/]+", "", candidate).lower()
        for line in text.splitlines():
            normalized_line = re.sub(r"[\s,:\-\/]+", "", line).lower()
            if normalized_candidate and normalized_candidate in normalized_line:
                snippet = line.strip()
                break

    if not snippet:
        return None

    return {
        "source": source,
        "snippet": snippet[:240],
        "strategy": strategy,
    }


def _build_default_field_details_from_wrapped_result(
    result: Dict[str, Any],
    *,
    source: str,
    raw_text: str = "",
) -> Dict[str, Dict[str, Any]]:
    field_details: Dict[str, Dict[str, Any]] = {}
    for key, value in (result or {}).items():
        if not isinstance(key, str) or key.startswith("_"):
            continue

        wrapped_value = value
        confidence = 0.0
        raw_value = value
        if isinstance(value, dict) and "value" in value:
            wrapped_value = value.get("value")
            raw_value = value.get("value")
            confidence = float(value.get("confidence", 0.0) or 0.0)
        elif value is not None:
            confidence = float(result.get("_extraction_confidence", 0.0) or 0.0)

        evidence = _build_text_evidence(
            raw_text,
            wrapped_value,
            source=source,
            strategy="support_text_match",
        )
        status = "trusted" if evidence and confidence >= 0.8 else "review"
        verification = "confirmed" if evidence else "model_suggested"

        field_details[key] = {
            "value": wrapped_value,
            "raw_value": raw_value,
            "confidence": round(confidence, 3),
            "status": status,
            "validator_agrees": bool(evidence),
            "issues": [] if evidence else ["support_text_not_confirmed"],
            "source": source,
            "verification": verification,
            "evidence": evidence,
        }

    return field_details


def _summarize_field_detail_statuses(field_details: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    counts = {"trusted": 0, "review": 0, "untrusted": 0, "not_found": 0}
    for detail in (field_details or {}).values():
        status = str((detail or {}).get("status") or "").strip().lower()
        if status in counts:
            counts[status] += 1
    return counts


def _derive_overall_status_from_field_details(field_details: Dict[str, Dict[str, Any]]) -> str:
    counts = _summarize_field_detail_statuses(field_details)
    if counts["untrusted"] > 0:
        return "needs_review"
    if counts["review"] > 0:
        return "review_advised"
    if counts["not_found"] > 2:
        return "incomplete"
    return "confident"


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

    DOC_TYPE_FIELDS: Dict[str, Dict[str, List[str]]] = {
        "letter_of_credit": {
            "required": [
                "lc_number", "lc_type", "amount", "currency", "applicant", "beneficiary",
                "issuing_bank", "advising_bank", "port_of_loading", "port_of_discharge",
                "expiry_date", "latest_shipment_date", "issue_date", "incoterm",
            ],
            "optional": [
                "confirming_bank", "ucp_reference", "partial_shipments", "transshipment",
                "goods_description", "documents_required", "additional_conditions",
                "payment_terms", "available_with",
            ],
        },
        "commercial_invoice": {
            "required": [
                "invoice_number", "invoice_date", "amount", "currency",
                "seller_name", "buyer_name", "lc_reference",
            ],
            "optional": [
                "seller_address", "buyer_address", "goods_description", "quantity", "unit_price",
                "incoterm", "country_of_origin", "port_of_loading", "port_of_discharge",
                "exporter_bin", "exporter_tin",
            ],
        },
        "bill_of_lading": {
            "required": [
                "bl_number", "shipper", "consignee", "notify_party", "port_of_loading",
                "port_of_discharge", "shipped_on_board_date", "vessel_name",
            ],
            "optional": [
                "voyage_number", "goods_description", "gross_weight", "net_weight",
                "number_of_packages", "container_number", "seal_number", "freight_terms",
                "place_of_receipt", "place_of_delivery", "exporter_bin", "exporter_tin",
            ],
        },
        "packing_list": {
            "required": [
                "packing_list_number", "date", "shipper", "consignee",
                "total_packages", "gross_weight", "net_weight",
            ],
            "optional": [
                "invoice_reference", "lc_reference", "goods_description", "marks_and_numbers",
                "dimensions", "packing_size_breakdown", "container_number", "port_of_loading",
                "port_of_discharge", "exporter_bin", "exporter_tin",
            ],
        },
        "certificate_of_origin": {
            "required": [
                "certificate_number", "country_of_origin", "exporter_name", "importer_name",
                "goods_description", "certifying_authority",
            ],
            "optional": [
                "issue_date", "invoice_reference", "lc_reference", "hs_code",
                "destination_country", "transport_details", "marks_and_numbers",
            ],
        },
        "insurance_certificate": {
            "required": [
                "certificate_number", "insured_amount", "currency", "insured_party",
                "insurance_company", "coverage_type",
            ],
            "optional": [
                "issue_date", "invoice_reference", "lc_reference", "goods_description",
                "voyage_details", "vessel_name", "claims_payable_at", "survey_agent",
            ],
        },
    }
    
    # Field validators (regex patterns to validate AI output)
    VALIDATORS = {
        "lc_number": {
            "pattern": r"^[A-Z0-9][A-Z0-9\-\/]{2,34}$",
            "flags": re.I,
            "description": "LC number should be 3-35 alphanumeric chars",
        },
        "lc_type": {
            "pattern": r"^(IRREVOCABLE|REVOCABLE|TRANSFERABLE|SIGHT|USANCE|DEFERRED|STANDBY|CONFIRMED|UNCONFIRMED|RED\s*CLAUSE|GREEN\s*CLAUSE).*$",
            "flags": re.I,
            "description": "Should be a valid LC type",
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
        "issue_date": {
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
        "payment_terms": {
            "pattern": r"^(AT\s*SIGHT|SIGHT|\d+\s*DAYS?\s*(AFTER|FROM)?\s*(B/?L|SHIPMENT|INVOICE|SIGHT)?|DEFERRED|USANCE).*$",
            "flags": re.I,
            "description": "Should be a valid payment term",
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
        
        ai_result = self._filter_canonical_ai_result(ai_result, "letter_of_credit")

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
            llm_trace = _resolve_llm_trace(None, provider, router_layer="L1")
            _log_ai_first_event(
                "lc_model_call",
                provider=llm_trace["provider"],
                model=llm_trace["model"],
                router_layer=llm_trace["router_layer"],
                ai_response_present=bool(ai_result),
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
            
            ai_result["_llm_provider"] = llm_trace["provider"]
            ai_result["_llm_model"] = llm_trace["model"]
            ai_result["_llm_router_layer"] = llm_trace["router_layer"]

            _log_ai_first_event(
                "lc_parse_output",
                provider=llm_trace["provider"],
                model=llm_trace["model"],
                router_layer=llm_trace["router_layer"],
                ai_parse_success=True,
                parsed_field_count=sum(1 for k, v in ai_result.items() if isinstance(k, str) and not k.startswith("_") and v not in (None, "", [], {})),
            )

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
                verification="not_found",
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
        evidence = _build_text_evidence(
            raw_text,
            normalized_value or value,
            source="native_text",
            strategy="regex_text_match" if regex_value else "text_match",
        )
        verification = _derive_field_verification(
            status=status,
            validator_agrees=validator_agrees,
            issues=issues,
            evidence=evidence,
        )
        
        return ExtractedFieldResult(
            name=field_name,
            value=value,
            normalized_value=normalized_value,
            ai_confidence=ai_confidence,
            validator_agrees=validator_agrees,
            status=status,
            issues=issues,
            source="ai",
            verification=verification,
            evidence=evidence,
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
        doc_type: str = "letter_of_credit",
    ) -> Dict[str, Any]:
        """Build final output structure with strict extraction contract."""
        # Backward-compatible flat output
        output: Dict[str, Any] = {}
        for name, field in fields.items():
            output[name] = field.normalized_value or field.value

        confidences = [f.ai_confidence for f in fields.values() if f.status != FieldStatus.NOT_FOUND]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        status_counts = {
            "trusted": sum(1 for f in fields.values() if f.status == FieldStatus.TRUSTED),
            "review": sum(1 for f in fields.values() if f.status == FieldStatus.REVIEW),
            "untrusted": sum(1 for f in fields.values() if f.status == FieldStatus.UNTRUSTED),
            "not_found": sum(1 for f in fields.values() if f.status == FieldStatus.NOT_FOUND),
        }

        if status_counts["untrusted"] > 0:
            overall_status = "needs_review"
        elif status_counts["review"] > 0:
            overall_status = "review_advised"
        elif status_counts["not_found"] > 2:
            overall_status = "incomplete"
        else:
            overall_status = "confident"

        contract = self._build_contract_output(fields, doc_type)

        output.update(contract)
        output["_extraction_method"] = "ai_first"
        output["_extraction_confidence"] = round(avg_confidence, 3)
        output["_ai_provider"] = ai_provider
        output["_status"] = overall_status
        output["_field_details"] = {name: field.to_dict() for name, field in fields.items()}
        output["_status_counts"] = status_counts

        logger.info(
            "AI-first extraction complete: doc_type=%s status=%s confidence=%.2f trusted=%d review=%d untrusted=%d",
            doc_type, overall_status, avg_confidence,
            status_counts["trusted"],
            status_counts["review"],
            status_counts["untrusted"],
        )

        return output

    def _build_contract_output(
        self,
        fields: Dict[str, ExtractedFieldResult],
        doc_type: str,
    ) -> Dict[str, Any]:
        """Build strict extraction contract payload."""
        schema = self.DOC_TYPE_FIELDS.get(doc_type) or {"required": [], "optional": []}
        canonical_keys = list(dict.fromkeys(schema["required"] + schema["optional"]))

        extracted_fields: Dict[str, Any] = {}
        field_confidence: Dict[str, float] = {}
        field_evidence_spans: Dict[str, List[Dict[str, Any]]] = {}
        conflicts: List[Dict[str, Any]] = []

        for key in canonical_keys:
            field = fields.get(key)
            value = (field.normalized_value or field.value) if field else None
            extracted_fields[key] = value
            field_confidence[key] = round(field.ai_confidence, 3) if field else 0.0
            field_evidence_spans[key] = [field.evidence] if field and field.evidence else []

            if field and field.issues:
                conflicts.append({"field": key, "issues": list(field.issues)})

        missing_fields = [k for k in schema["required"] if extracted_fields.get(k) in (None, "", [])]

        return {
            "extracted_fields": extracted_fields,
            "field_confidence": field_confidence,
            "field_evidence_spans": field_evidence_spans,
            "missing_fields": missing_fields,
            "conflicts": conflicts,
        }
    
    def _filter_canonical_ai_result(self, ai_result: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        schema = self.DOC_TYPE_FIELDS.get(doc_type)
        if not schema:
            return dict(ai_result)
        allowed = set(schema["required"] + schema["optional"])
        doc_aliases: Dict[str, Dict[str, str]] = {
            "commercial_invoice": {
                "invoice_no": "invoice_number",
                "inv_no": "invoice_number",
                "invoice_num": "invoice_number",
                "invoice_reference": "invoice_number",
                "invoice_amount": "amount",
                "total_amount": "amount",
                "seller": "seller_name",
                "buyer": "buyer_name",
                "lc_number": "lc_reference",
                "lc_no": "lc_reference",
                "lc_ref": "lc_reference",
            },
            "bill_of_lading": {
                "bill_of_lading_number": "bl_number",
                "b_l_number": "bl_number",
                "bl_no": "bl_number",
                "bl_num": "bl_number",
                "on_board_date": "shipped_on_board_date",
                "date_of_shipment": "shipped_on_board_date",
                "vessel": "vessel_name",
                "voyage": "voyage_number",
                "notify": "notify_party",
                "loading_port": "port_of_loading",
                "discharge_port": "port_of_discharge",
            },
        }
        alias_map = doc_aliases.get(doc_type, {})

        # AI providers sometimes wrap canonical fields in nested objects
        # (e.g., {"extracted_fields": {...}} or {"fields": {...}}).
        candidate_sources: List[Dict[str, Any]] = [ai_result]
        for wrapper_key in ("extracted_fields", "fields", "data", "result", "payload"):
            wrapped = ai_result.get(wrapper_key)
            if isinstance(wrapped, dict):
                candidate_sources.append(wrapped)
                nested_value = wrapped.get("value")
                if isinstance(nested_value, dict):
                    candidate_sources.append(nested_value)

        # Import lazily to avoid introducing a hard dependency at module load.
        try:
            from app.services.validation.alias_normalization import canonical_field_key  # type: ignore
        except Exception:
            canonical_field_key = lambda key: str(key).strip().lower()

        filtered: Dict[str, Any] = {}
        for source in candidate_sources:
            if not isinstance(source, dict):
                continue
            for key, value in source.items():
                if not isinstance(key, str):
                    continue
                if key.startswith("_"):
                    continue
                normalized_key = canonical_field_key(key)
                source_key_normalized = re.sub(r"_+", "_", re.sub(r"\s+", "_", str(key).strip().lower().replace("&", "_and_").replace("/", "_"))).strip("_")

                # Handle combined key/value variants before generic canonical mapping.
                if doc_type == "bill_of_lading":
                    if (normalized_key in {"gross_net_weight", "gross_net"} or ("gross" in source_key_normalized and "net" in source_key_normalized)) and isinstance(value, str) and "/" in value:
                        gross_part, net_part = [p.strip() for p in value.split("/", 1)]
                        if gross_part and "gross_weight" in allowed:
                            existing = filtered.get("gross_weight")
                            if "gross_weight" not in filtered or existing in (None, "", [], {}):
                                filtered["gross_weight"] = gross_part
                        if net_part and "net_weight" in allowed:
                            existing = filtered.get("net_weight")
                            if "net_weight" not in filtered or existing in (None, "", [], {}):
                                filtered["net_weight"] = net_part
                        continue

                    if (normalized_key in {"vessel_and_voyage", "vessel_voyage", "vessel_voy", "vsl_voyage", "vsl_voy", "vvd"} or ("vessel" in source_key_normalized and "voy" in source_key_normalized)) and isinstance(value, str):
                        parts = [p.strip() for p in re.split(r"\s*/\s*", value, maxsplit=1)]
                        if len(parts) == 2:
                            vessel_part, voyage_part = parts
                            if vessel_part and "vessel_name" in allowed:
                                existing = filtered.get("vessel_name")
                                if "vessel_name" not in filtered or existing in (None, "", [], {}):
                                    filtered["vessel_name"] = vessel_part
                            if voyage_part and "voyage_number" in allowed:
                                existing = filtered.get("voyage_number")
                                if "voyage_number" not in filtered or existing in (None, "", [], {}):
                                    filtered["voyage_number"] = voyage_part
                            continue

                canonical = key if key in allowed else alias_map.get(normalized_key, normalized_key)
                if canonical not in allowed:
                    continue
                # Prefer populated values, but keep first seen otherwise.
                existing = filtered.get(canonical)
                if canonical not in filtered or existing in (None, "", [], {}) and value not in (None, "", [], {}):
                    filtered[canonical] = value

        # Preserve root metadata keys.
        for key, value in ai_result.items():
            if isinstance(key, str) and key.startswith("_"):
                filtered[key] = value

        return filtered

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
            "extracted_fields": {},
            "field_confidence": {},
            "field_evidence_spans": {},
            "missing_fields": [],
            "conflicts": [],
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
2. If a field label is on the document but the value is blank or unclear, include the key with an empty string ""
3. If a field is NOT on the document at all, OMIT the key entirely from your output - do NOT return null, do NOT guess
4. For amounts, include the full number without currency symbols
5. For dates, use ISO format (YYYY-MM-DD) when possible
6. Look for LC/Credit reference numbers - they link the invoice to the LC
7. Be precise - banks rely on exact data for documentary credit compliance
8. VERBATIM: Copy every value EXACTLY as printed. Do NOT correct, modernize, or rename anything. If it says 'Chittagong' write 'Chittagong', not 'Chattogram'. You are a photocopier.

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
- exporter_bin: Exporter BIN (if shown)
- exporter_tin: Exporter TIN (if shown)

Return a JSON object. Include ONLY keys for fields that are actually present on the document. OMIT keys for fields that are not on the document — do not include them with null.

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

        ai_result = self._filter_canonical_ai_result(ai_result, "commercial_invoice")
        
        # Process fields
        fields: Dict[str, ExtractedFieldResult] = {}
        for field_name, ai_value in ai_result.items():
            if field_name.startswith("_"):
                continue
            field_result = self._process_field(field_name, ai_value, raw_text)
            fields[field_name] = field_result
        
        return self._build_output(fields, ai_provider, doc_type="commercial_invoice")
    
    async def _run_invoice_ai_extraction(
        self,
        raw_text: str,
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """Run AI extraction for invoice."""
        try:
            from ..llm_provider import LLMProviderFactory
            
            provider = LLMProviderFactory.create_provider()
            if not provider:
                logger.warning("No LLM provider available for invoice extraction")
                return None, "none"

            prompt = INVOICE_EXTRACTION_PROMPT.format(
                document_text=raw_text[:12000]
            )

            response, tokens_in, tokens_out, provider_used, llm_trace = await _generate_extraction_with_model_routing(
                prompt=prompt,
                system_prompt=INVOICE_EXTRACTION_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=2000,
            )
            _log_ai_first_event(
                "invoice_model_call",
                provider=llm_trace["provider"],
                model=llm_trace["model"],
                router_layer=llm_trace["router_layer"],
                ai_response_present=bool(response),
            )
            
            if not response:
                return None, "empty_response"
            
            logger.info(f"Invoice AI extraction: tokens_in={tokens_in} tokens_out={tokens_out}")
            
            # Parse JSON response with single repair retry
            result = await _parse_llm_json_with_repair(provider, response)
            if not result:
                _log_ai_first_event(
                    "invoice_parse_output",
                    provider=llm_trace["provider"],
                    model=llm_trace["model"],
                    router_layer=llm_trace["router_layer"],
                    ai_parse_success=False,
                )
                logger.warning("Failed to parse/repair AI invoice response")
                return None, "parse_error"

            # --- Two-stage review: Sonnet cross-checks cheap model output ---
            result, review_trace = await _review_extraction(raw_text, result, "commercial_invoice")

            result = _wrap_ai_result_with_default_confidence(result)
            _unwrap_confidence_scalars_in_place(result)
            _flatten_structural_field_values_in_place(result)
            result["_llm_provider"] = llm_trace["provider"]
            result["_llm_model"] = llm_trace["model"]
            result["_llm_router_layer"] = llm_trace["router_layer"]
            result["_two_stage_review"] = review_trace.get("outcome", "skipped")
            _log_ai_first_event(
                "invoice_parse_output",
                provider=llm_trace["provider"],
                model=llm_trace["model"],
                router_layer=llm_trace["router_layer"],
                ai_parse_success=True,
                parsed_field_count=sum(1 for k, v in result.items() if isinstance(k, str) and not k.startswith("_") and v not in (None, "", [], {})),
                two_stage_review=review_trace.get("outcome", "skipped"),
            )

            return result, provider_used

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
        
        # Exporter BIN/TIN variants
        match = re.search(
            r"(?:EXPORTER\s+)?(?:B\.?I\.?N\.?|BIN|BUSINESS\s+IDENTIFICATION|BUSINESS\s+ID(?:ENTIFICATION)?|VAT\s*REG(?:ISTRATION)?|VAT\s*REG\.?|VAT\s*NO\.?|VAT\s*REG\s*NO\.?|VAT\s*REGISTRATION\s*NO\.?|VAT\s*REGISTRATION\s*NUMBER)\s*(?:NO\.?|NUMBER|#|:)?\s*([0-9][0-9\-]+)",
            raw_text,
            re.I,
        )
        if match:
            result["exporter_bin"] = match.group(1).strip()
        match = re.search(
            r"(?:EXPORTER\s+)?(?:T\.?I\.?N\.?|TIN|TAX\s+IDENTIFICATION|TAX\s+ID(?:ENTIFICATION)?|TAX\s*REG(?:ISTRATION)?|TAX\s*REG\.?|TAXPAYER\s+ID(?:ENTIFICATION)?|E-?TIN|ETIN)\s*(?:NO\.?|NUMBER|#|:)?\s*([0-9][0-9\-]+)",
            raw_text,
            re.I,
        )
        if match:
            result["exporter_tin"] = match.group(1).strip()
        
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
        output = super()._build_output(fields, ai_provider, doc_type=doc_type)
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
2. If a field label is on the document but the value is blank or unclear, include the key with an empty string ""
3. If a field is NOT on the document at all, OMIT the key entirely from your output - do NOT return null, do NOT guess
4. For dates, use ISO format (YYYY-MM-DD) when possible
5. The "shipped on board" date is CRITICAL for LC compliance
6. Port names must be extracted EXACTLY as written on the document
7. Be precise - banks rely on exact data
8. VERBATIM: Copy every value EXACTLY as printed. Do NOT correct, modernize, or rename anything. If it says 'Chittagong' write 'Chittagong', not 'Chattogram'. You are a photocopier.

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
- net_weight: Net weight (if stated)
- number_of_packages: Package count
- container_number: Container ID
- seal_number: Seal ID
- freight_terms: "PREPAID" or "COLLECT"
- place_of_receipt: Where carrier received goods
- place_of_delivery: Final delivery location
- exporter_bin: Exporter BIN (if shown)
- exporter_tin: Exporter TIN (if shown)

Return a JSON object. Include ONLY keys for fields that are actually present on the document. OMIT keys for fields that are not on the document — do not include them with null.

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

        ai_result = self._filter_canonical_ai_result(ai_result, "bill_of_lading")
        
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
            
            provider = LLMProviderFactory.create_provider()
            if not provider:
                logger.warning("No LLM provider available for B/L extraction")
                return None, "none"

            prompt = BL_EXTRACTION_PROMPT.format(
                document_text=raw_text[:12000]
            )

            response, tokens_in, tokens_out, provider_used, llm_trace = await _generate_extraction_with_model_routing(
                prompt=prompt,
                system_prompt=BL_EXTRACTION_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=2000,
            )
            _log_ai_first_event(
                "bl_model_call",
                provider=llm_trace["provider"],
                model=llm_trace["model"],
                router_layer=llm_trace["router_layer"],
                ai_response_present=bool(response),
            )
            
            if not response:
                return None, "empty_response"
            
            logger.info(f"B/L AI extraction: tokens_in={tokens_in} tokens_out={tokens_out}")
            
            # Parse JSON response with single repair retry
            result = await _parse_llm_json_with_repair(provider, response)
            if not result:
                _log_ai_first_event(
                    "bl_parse_output",
                    provider=llm_trace["provider"],
                    model=llm_trace["model"],
                    router_layer=llm_trace["router_layer"],
                    ai_parse_success=False,
                )
                logger.warning("Failed to parse/repair AI B/L response")
                return None, "parse_error"

            # --- Two-stage review: Sonnet cross-checks cheap model output ---
            result, review_trace = await _review_extraction(raw_text, result, "bill_of_lading")

            result = _wrap_ai_result_with_default_confidence(result)
            _unwrap_confidence_scalars_in_place(result)
            _flatten_structural_field_values_in_place(result)
            result["_llm_provider"] = llm_trace["provider"]
            result["_llm_model"] = llm_trace["model"]
            result["_llm_router_layer"] = llm_trace["router_layer"]
            result["_two_stage_review"] = review_trace.get("outcome", "skipped")
            _log_ai_first_event(
                "bl_parse_output",
                provider=llm_trace["provider"],
                model=llm_trace["model"],
                router_layer=llm_trace["router_layer"],
                ai_parse_success=True,
                parsed_field_count=sum(1 for k, v in result.items() if isinstance(k, str) and not k.startswith("_") and v not in (None, "", [], {})),
                two_stage_review=review_trace.get("outcome", "skipped"),
            )

            return result, provider_used

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
        
        # Vessel/Voyage combined line (e.g., "VSL/VOY: EVER GLORY / 123E")
        combo_match = re.search(
            r"(?:VSL|VESSEL)\s*/\s*VOY(?:AGE)?\s*[:\-]?\s*([^\n\r\-/]{2,60}?)\s*(?:/|\s{2,}|\s+-\s+)\s*([A-Z0-9\-\/\.]{2,30})\b",
            raw_text,
            re.I,
        )
        if combo_match:
            vessel_candidate = combo_match.group(1).strip(" .:-")
            voy_candidate = combo_match.group(2).strip()
            if vessel_candidate and "vessel_name" not in result:
                result["vessel_name"] = vessel_candidate
            if voy_candidate:
                result["voyage_number"] = voy_candidate

        # Voyage number
        if "voyage_number" not in result:
            match = re.search(
                r"(?:VOY(?:AGE)?(?:\s*(?:NO\.?|NUMBER|#))?|VSL\s*/\s*VOY(?:AGE)?|VESSEL\s*/\s*VOY(?:AGE)?|VESSEL\s+VOY(?:AGE)?)\s*[:\-]?\s*([A-Z0-9\-\/\.]+)",
                raw_text,
                re.I,
            )
            if match:
                result["voyage_number"] = match.group(1).strip()
        
        # Combined Gross/Net line variants (e.g., "GROSS/NET WEIGHT: 1200/1100 KGS")
        combo_match = re.search(
            r"(?:GROSS\s*/\s*NET|G\.?\s*W\.?\s*/\s*N\.?\s*W\.?|GW\s*/\s*NW)\s*(?:WEIGHT|WT|WGT)?\s*[:\-]?\s*([0-9][0-9,\.]*\s*(?:KGS?|KG|LBS?|LB)?)\s*/\s*([0-9][0-9,\.]*\s*(?:KGS?|KG|LBS?|LB)?)",
            raw_text,
            re.I,
        )
        if combo_match:
            result["gross_weight"] = combo_match.group(1).strip()
            result["net_weight"] = combo_match.group(2).strip()

        # Gross weight
        if "gross_weight" not in result:
            match = re.search(
                r"(?:TOTAL\s+)?(?:GROSS\s*(?:WEIGHT|WT|WGT)|G\.?\s*W\.?|G\.?\s*WT\.?|G\.?\s*WGT\.?|G/\s*W|G\s*W)\s*[:\-]?\s*([^\n]+)",
                raw_text,
                re.I,
            )
            if match:
                result["gross_weight"] = match.group(1).strip()
        
        # Net weight
        if "net_weight" not in result:
            match = re.search(
                r"(?:TOTAL\s+)?(?:NET\s*(?:WEIGHT|WT|WGT)|N\.?\s*W\.?|N\.?\s*WT\.?|N\.?\s*WGT\.?|N/\s*W|N\s*W)\s*[:\-]?\s*([^\n]+)",
                raw_text,
                re.I,
            )
            if match:
                result["net_weight"] = match.group(1).strip()
        
        # Exporter BIN/TIN
        match = re.search(
            r"(?:EXPORTER\s+)?(?:B\.?I\.?N\.?|BIN|BUSINESS\s+IDENTIFICATION|BUSINESS\s+ID(?:ENTIFICATION)?|VAT\s*REG(?:ISTRATION)?|VAT\s*REG\.?|VAT\s*NO\.?|VAT\s*REG\s*NO\.?|VAT\s*REGISTRATION\s*NO\.?|VAT\s*REGISTRATION\s*NUMBER)\s*(?:NO\.?|NUMBER|#|:)?\s*([0-9][0-9\-]+)",
            raw_text,
            re.I,
        )
        if match:
            result["exporter_bin"] = match.group(1).strip()
        match = re.search(
            r"(?:EXPORTER\s+)?(?:T\.?I\.?N\.?|TIN|TAX\s+IDENTIFICATION|TAX\s+ID(?:ENTIFICATION)?|TAX\s*REG(?:ISTRATION)?|TAX\s*REG\.?|TAXPAYER\s+ID(?:ENTIFICATION)?|E-?TIN|ETIN)\s*(?:NO\.?|NUMBER|#|:)?\s*([0-9][0-9\-]+)",
            raw_text,
            re.I,
        )
        if match:
            result["exporter_tin"] = match.group(1).strip()
        
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
        output = super()._build_output(fields, ai_provider, doc_type=doc_type)
        output["_document_type"] = doc_type
        return output


# =====================================================================
# PACKING LIST AI-FIRST EXTRACTOR
# =====================================================================

PACKING_LIST_EXTRACTION_SYSTEM_PROMPT = """You are an expert trade finance document parser specializing in Packing Lists.

Your task is to extract structured data from packing list documents used in international trade.
These documents detail the contents of shipments and must match the commercial invoice and LC requirements.

IMPORTANT RULES:
1. Extract ONLY what is explicitly stated in the document
2. If a field label is on the document but the value is blank or unclear, include the key with an empty string ""
3. If a field is NOT on the document at all, OMIT the key entirely from your output - do NOT return null, do NOT guess
4. Package counts and weights must be exact
5. Marks and numbers must be captured exactly as written
6. Be precise - banks check packing details against LC requirements
7. VERBATIM: Copy every value EXACTLY as printed. Do NOT correct, modernize, or rename anything. If it says 'Chittagong' write 'Chittagong', not 'Chattogram'. You are a photocopier.

OUTPUT FORMAT: JSON only, no markdown, no explanation."""

PACKING_LIST_EXTRACTION_PROMPT = """Extract the following fields from this Packing List:

REQUIRED FIELDS:
- packing_list_number: The packing list reference number
- date: The date of the packing list
- shipper: The shipper/exporter name
- consignee: The consignee/buyer name
- total_packages: Total number of packages/cartons
- gross_weight: Total gross weight with unit
- net_weight: Total net weight with unit

OPTIONAL FIELDS:
- invoice_reference: Related invoice number
- lc_reference: Related LC number
- goods_description: Description of goods
- marks_and_numbers: Shipping marks
- dimensions: Package dimensions
- packing_size_breakdown: Size breakdown by package/carton (if listed)
- container_number: Container ID
- port_of_loading: Origin port
- port_of_discharge: Destination port
- exporter_bin: Exporter BIN (if shown)
- exporter_tin: Exporter TIN (if shown)

Return a JSON object. Include ONLY keys for fields that are actually present on the document. OMIT keys for fields that are not on the document — do not include them with null.

---
DOCUMENT TEXT:
{document_text}
---

Return ONLY valid JSON, no other text:"""


class PackingListAIFirstExtractor(AIFirstExtractor):
    """AI-first extractor for Packing Lists."""
    
    VALIDATORS = {
        "packing_list_number": {
            "pattern": r"^[A-Z0-9][A-Z0-9\-\/\.]{1,30}$",
            "flags": re.I,
            "description": "Packing list number should be alphanumeric",
        },
        "total_packages": {
            "pattern": r"^\d+$",
            "flags": 0,
            "description": "Package count should be a number",
        },
        "date": {
            "pattern": r"^\d{4}-\d{2}-\d{2}$|^\d{2}[\/\-]\d{2}[\/\-]\d{4}$",
            "flags": 0,
            "description": "Date should be YYYY-MM-DD or DD/MM/YYYY",
        },
    }
    
    async def extract_packing_list(
        self,
        raw_text: str,
        use_fallback_on_ai_failure: bool = True,
    ) -> Dict[str, Any]:
        """Extract packing list fields using AI-first pattern."""
        if not raw_text or not raw_text.strip():
            return self._empty_result("empty_input")
        
        ai_result, ai_provider = await self._run_ai_extraction_generic(
            raw_text, PACKING_LIST_EXTRACTION_PROMPT, PACKING_LIST_EXTRACTION_SYSTEM_PROMPT,
            doc_type="packing_list",
        )
        
        if not ai_result and use_fallback_on_ai_failure:
            logger.warning("AI packing list extraction failed, using regex fallback")
            return self._packing_list_regex_fallback(raw_text)
        
        if not ai_result:
            return self._empty_result("ai_failed")

        ai_result = self._filter_canonical_ai_result(ai_result, "packing_list")
        
        fields: Dict[str, ExtractedFieldResult] = {}
        for field_name, ai_value in ai_result.items():
            if field_name.startswith("_"):
                continue
            field_result = self._process_field(field_name, ai_value, raw_text)
            fields[field_name] = field_result
        
        return self._build_output(fields, ai_provider, doc_type="packing_list")
    
    def _packing_list_regex_fallback(self, raw_text: str) -> Dict[str, Any]:
        """Regex fallback for packing list."""
        result: Dict[str, Any] = {}
        
        match = re.search(r"Packing\s*List\s*(?:No\.?|#)\s*[:\-]?\s*([A-Z0-9\-\/]+)", raw_text, re.I)
        if match:
            result["packing_list_number"] = match.group(1).strip()
        
        match = re.search(r"Total\s*(?:Packages?|Cartons?)\s*[:\-]?\s*(\d+)", raw_text, re.I)
        if match:
            result["total_packages"] = match.group(1)
        
        match = re.search(r"(?:GROSS\s*WEIGHT|G\.?\s*W\.?|G/\s*W)\s*[:\-]?\s*([^\n]+)", raw_text, re.I)
        if match:
            result["gross_weight"] = match.group(1).strip()
        
        match = re.search(r"(?:NET\s*WEIGHT|N\.?\s*W\.?|N/\s*W)\s*[:\-]?\s*([^\n]+)", raw_text, re.I)
        if match:
            result["net_weight"] = match.group(1).strip()
        
        match = re.search(r"(?:Dimensions|Dimension|Measurements|Measurement|Size)\s*[:\-]?\s*([^\n]+)", raw_text, re.I)
        if match:
            result["dimensions"] = match.group(1).strip()
        
        match = re.search(
            r"(?:SIZE\s*BREAKDOWN|SIZE\s*DETAILS|SIZE\s*/\s*QTY|SIZE\s*QTY|SIZE\s*&\s*QTY|SIZE\s*WISE|SIZE\s*-\s*WISE|SIZE\s*DISTRIBUTION|SIZE\s*RATIO|SIZE\s*RUN|SIZE\s*MATRIX|SIZE\s*ASSORTMENT|ASSORTMENT|PRE-?\s*PACK|PREPACK|RATIO\s*PACK|QTY\s*PER\s*SIZE|QTY\s*/\s*SIZE|SIZE\s*PER\s*SIZE|SIZE\s*-\s*COLOR|SIZE\s*&\s*COLOR|SIZE\s*/\s*COLOR|SIZE\s*COLOR)\s*[:\-]?\s*([^\n]+)",
            raw_text,
            re.I,
        )
        if match:
            result["size_breakdown"] = match.group(1).strip()
        
        match = re.search(
            r"(?:CARTON\s*SIZE|CTN\s*SIZE|CARTON\s*DIMENSIONS?|CASE\s*SIZE|CTN\s*DIMENSIONS?|PACKING\s*SIZE|PACKAGE\s*SIZE)\s*[:\-]?\s*([^\n]+)",
            raw_text,
            re.I,
        )
        if match:
            result["carton_size"] = match.group(1).strip()

        if "packing_size_breakdown" not in result:
            fallback_size = result.get("size_breakdown") or result.get("carton_size") or result.get("dimensions")
            if fallback_size:
                result["packing_size_breakdown"] = fallback_size
        
        match = re.search(
            r"(?:EXPORTER\s+)?(?:B\.?I\.?N\.?|BIN|BUSINESS\s+IDENTIFICATION|BUSINESS\s+ID(?:ENTIFICATION)?|VAT\s*REG(?:ISTRATION)?|VAT\s*REG\.?|VAT\s*NO\.?|VAT\s*REG\s*NO\.?|VAT\s*REGISTRATION\s*NO\.?|VAT\s*REGISTRATION\s*NUMBER)\s*(?:NO\.?|NUMBER|#|:)?\s*([0-9][0-9\-]+)",
            raw_text,
            re.I,
        )
        if match:
            result["exporter_bin"] = match.group(1).strip()
        match = re.search(
            r"(?:EXPORTER\s+)?(?:T\.?I\.?N\.?|TIN|TAX\s+IDENTIFICATION|TAX\s+ID(?:ENTIFICATION)?|TAX\s*REG(?:ISTRATION)?|TAX\s*REG\.?|TAXPAYER\s+ID(?:ENTIFICATION)?|E-?TIN|ETIN)\s*(?:NO\.?|NUMBER|#|:)?\s*([0-9][0-9\-]+)",
            raw_text,
            re.I,
        )
        if match:
            result["exporter_tin"] = match.group(1).strip()
        
        result["_extraction_method"] = "regex_fallback"
        result["_status"] = "ai_failed_regex_used"
        return result
    
    def _build_output(
        self,
        fields: Dict[str, ExtractedFieldResult],
        ai_provider: str,
        doc_type: str = "packing_list",
    ) -> Dict[str, Any]:
        output = super()._build_output(fields, ai_provider, doc_type=doc_type)
        output["_document_type"] = doc_type
        return output


# =====================================================================
# CERTIFICATE OF ORIGIN AI-FIRST EXTRACTOR
# =====================================================================

COO_EXTRACTION_SYSTEM_PROMPT = """You are an expert trade finance document parser specializing in Certificates of Origin.

Your task is to extract structured data from Certificate of Origin documents.
These documents certify where goods were manufactured/produced and are critical for customs and LC compliance.

IMPORTANT RULES:
1. Extract ONLY what is explicitly stated in the document
2. The country of origin is CRITICAL - extract exactly as stated
3. Certifying authority/chamber must be captured
4. If a field label is on the document but the value is blank, include the key with ""
5. If a field is NOT on the document at all, OMIT the key from your output - do NOT return null
6. Be precise - origin certificates affect duty rates and LC compliance
7. VERBATIM: Copy every value EXACTLY as printed. Do NOT correct, modernize, or rename anything. If it says 'Chittagong' write 'Chittagong', not 'Chattogram'. You are a photocopier.

OUTPUT FORMAT: JSON only, no markdown, no explanation."""

COO_EXTRACTION_PROMPT = """Extract the following fields from this Certificate of Origin:

REQUIRED FIELDS:
- certificate_number: The certificate reference number
- country_of_origin: The country where goods originated
- exporter_name: The exporter/manufacturer name
- importer_name: The importer/consignee name
- goods_description: Description of goods
- certifying_authority: Chamber of Commerce or authority name

OPTIONAL FIELDS:
- issue_date: Date certificate was issued
- invoice_reference: Related invoice number
- lc_reference: Related LC number
- hs_code: Harmonized System code
- destination_country: Where goods are going
- transport_details: Shipping information
- marks_and_numbers: Shipping marks

Return a JSON object. Include ONLY keys for fields that are actually present on the document. OMIT keys for fields that are not on the document — do not include them with null.

---
DOCUMENT TEXT:
{document_text}
---

Return ONLY valid JSON, no other text:"""


class CertificateOfOriginAIFirstExtractor(AIFirstExtractor):
    """AI-first extractor for Certificate of Origin."""
    
    VALIDATORS = {
        "certificate_number": {
            "pattern": r"^[A-Z0-9][A-Z0-9\-\/\.]{1,30}$",
            "flags": re.I,
            "description": "Certificate number should be alphanumeric",
        },
        "issue_date": {
            "pattern": r"^\d{4}-\d{2}-\d{2}$|^\d{2}[\/\-]\d{2}[\/\-]\d{4}$",
            "flags": 0,
            "description": "Date should be YYYY-MM-DD or DD/MM/YYYY",
        },
        "hs_code": {
            "pattern": r"^\d{4,10}$",
            "flags": 0,
            "description": "HS code should be 4-10 digits",
        },
    }
    
    async def extract_coo(
        self,
        raw_text: str,
        use_fallback_on_ai_failure: bool = True,
    ) -> Dict[str, Any]:
        """Extract certificate of origin fields using AI-first pattern."""
        if not raw_text or not raw_text.strip():
            return self._empty_result("empty_input")
        
        ai_result, ai_provider = await self._run_ai_extraction_generic(
            raw_text, COO_EXTRACTION_PROMPT, COO_EXTRACTION_SYSTEM_PROMPT,
            doc_type="certificate_of_origin",
        )
        
        if not ai_result and use_fallback_on_ai_failure:
            logger.warning("AI CoO extraction failed, using regex fallback")
            return self._coo_regex_fallback(raw_text)
        
        if not ai_result:
            return self._empty_result("ai_failed")

        ai_result = self._filter_canonical_ai_result(ai_result, "certificate_of_origin")
        
        fields: Dict[str, ExtractedFieldResult] = {}
        for field_name, ai_value in ai_result.items():
            if field_name.startswith("_"):
                continue
            field_result = self._process_field(field_name, ai_value, raw_text)
            fields[field_name] = field_result
        
        return self._build_output(fields, ai_provider, doc_type="certificate_of_origin")
    
    def _coo_regex_fallback(self, raw_text: str) -> Dict[str, Any]:
        """Regex fallback for certificate of origin."""
        result: Dict[str, Any] = {}
        
        match = re.search(r"Certificate\s*(?:No\.?|#|Number)\s*[:\-]?\s*([A-Z0-9\-\/]+)", raw_text, re.I)
        if match:
            result["certificate_number"] = match.group(1).strip()
        
        match = re.search(r"Country\s*of\s*Origin\s*[:\-]?\s*([A-Za-z\s]+?)(?:\n|$)", raw_text, re.I)
        if match:
            result["country_of_origin"] = match.group(1).strip()
        
        result["_extraction_method"] = "regex_fallback"
        result["_status"] = "ai_failed_regex_used"
        return result
    
    def _build_output(
        self,
        fields: Dict[str, ExtractedFieldResult],
        ai_provider: str,
        doc_type: str = "certificate_of_origin",
    ) -> Dict[str, Any]:
        output = super()._build_output(fields, ai_provider, doc_type=doc_type)
        output["_document_type"] = doc_type
        return output


# =====================================================================
# INSURANCE CERTIFICATE AI-FIRST EXTRACTOR
# =====================================================================

INSURANCE_EXTRACTION_SYSTEM_PROMPT = """You are an expert trade finance document parser specializing in Insurance Certificates.

Your task is to extract structured data from Marine/Cargo Insurance Certificates.
These documents prove goods are insured and must meet LC requirements (typically CIF + 10%).

IMPORTANT RULES:
1. Extract ONLY what is explicitly stated in the document
2. Insurance amount and coverage percentage are CRITICAL
3. The insured value must typically be invoice value + 10% (CIF + 10%)
4. Risk coverage types (All Risks, ICC-A, etc.) must be captured
5. If a field label is on the document but the value is blank, include the key with ""
6. If a field is NOT on the document at all, OMIT the key from your output - do NOT return null
7. Be precise - banks verify insurance coverage against LC requirements
8. VERBATIM: Copy every value EXACTLY as printed. Do NOT correct, modernize, or rename anything. You are a photocopier.

OUTPUT FORMAT: JSON only, no markdown, no explanation."""

INSURANCE_EXTRACTION_PROMPT = """Extract the following fields from this Insurance Certificate:

REQUIRED FIELDS:
- certificate_number: The certificate/policy reference
- insured_amount: The amount of coverage (number)
- currency: Currency of coverage
- insured_party: Who is insured (beneficiary)
- insurance_company: Name of the insurer
- coverage_type: Type of coverage (All Risks, ICC-A, ICC-B, ICC-C, etc.)

OPTIONAL FIELDS:
- issue_date: Date certificate was issued
- invoice_reference: Related invoice number
- lc_reference: Related LC number
- goods_description: Description of insured goods
- voyage_details: From/to ports
- vessel_name: Name of carrying vessel
- claims_payable_at: Where claims are paid
- survey_agent: Survey/claims agent

Return a JSON object. Include ONLY keys for fields that are actually present on the document. OMIT keys for fields that are not on the document — do not include them with null.

---
DOCUMENT TEXT:
{document_text}
---

Return ONLY valid JSON, no other text:"""


class InsuranceCertificateAIFirstExtractor(AIFirstExtractor):
    """AI-first extractor for Insurance Certificates."""
    
    VALIDATORS = {
        "certificate_number": {
            "pattern": r"^[A-Z0-9][A-Z0-9\-\/\.]{1,30}$",
            "flags": re.I,
            "description": "Certificate number should be alphanumeric",
        },
        "insured_amount": {
            "pattern": r"^\d+(?:\.\d{1,4})?$",
            "flags": 0,
            "description": "Amount should be a valid number",
        },
        "currency": {
            "pattern": r"^[A-Z]{3}$",
            "flags": 0,
            "description": "Currency should be 3-letter ISO code",
        },
        "coverage_type": {
            "pattern": r"^(ALL\s*RISKS?|ICC[\-\s]?[ABC]|INSTITUTE\s+CARGO|FPA|WA).*$",
            "flags": re.I,
            "description": "Should be a valid coverage type",
        },
    }
    
    async def extract_insurance(
        self,
        raw_text: str,
        use_fallback_on_ai_failure: bool = True,
    ) -> Dict[str, Any]:
        """Extract insurance certificate fields using AI-first pattern."""
        if not raw_text or not raw_text.strip():
            return self._empty_result("empty_input")
        
        ai_result, ai_provider = await self._run_ai_extraction_generic(
            raw_text, INSURANCE_EXTRACTION_PROMPT, INSURANCE_EXTRACTION_SYSTEM_PROMPT,
            doc_type="insurance_certificate",
        )
        
        if not ai_result and use_fallback_on_ai_failure:
            logger.warning("AI insurance extraction failed, using regex fallback")
            return self._insurance_regex_fallback(raw_text)
        
        if not ai_result:
            return self._empty_result("ai_failed")

        ai_result = self._filter_canonical_ai_result(ai_result, "insurance_certificate")
        
        fields: Dict[str, ExtractedFieldResult] = {}
        for field_name, ai_value in ai_result.items():
            if field_name.startswith("_"):
                continue
            field_result = self._process_field(field_name, ai_value, raw_text)
            fields[field_name] = field_result
        
        return self._build_output(fields, ai_provider, doc_type="insurance_certificate")
    
    def _insurance_regex_fallback(self, raw_text: str) -> Dict[str, Any]:
        """Regex fallback for insurance certificate."""
        result: Dict[str, Any] = {}
        
        match = re.search(r"(?:Certificate|Policy)\s*(?:No\.?|#|Number)\s*[:\-]?\s*([A-Z0-9\-\/]+)", raw_text, re.I)
        if match:
            result["certificate_number"] = match.group(1).strip()
        
        match = re.search(r"(?:Sum\s+Insured|Insured\s+(?:Amount|Value))\s*[:\-]?\s*([A-Z]{3})?\s*([\d,]+(?:\.\d{2})?)", raw_text, re.I)
        if match:
            if match.group(1):
                result["currency"] = match.group(1)
            result["insured_amount"] = match.group(2).replace(",", "")
        
        match = re.search(r"(ALL\s*RISKS?|ICC[\-\s]?[ABC]|INSTITUTE\s+CARGO)", raw_text, re.I)
        if match:
            result["coverage_type"] = match.group(1).strip().upper()
        
        result["_extraction_method"] = "regex_fallback"
        result["_status"] = "ai_failed_regex_used"
        return result
    
    def _build_output(
        self,
        fields: Dict[str, ExtractedFieldResult],
        ai_provider: str,
        doc_type: str = "insurance_certificate",
    ) -> Dict[str, Any]:
        output = super()._build_output(fields, ai_provider, doc_type=doc_type)
        output["_document_type"] = doc_type
        return output


# =====================================================================
# INSPECTION CERTIFICATE AI-FIRST EXTRACTOR
# =====================================================================

INSPECTION_EXTRACTION_SYSTEM_PROMPT = """You are an expert trade finance document parser specializing in Inspection Certificates.

Your task is to extract structured data from Pre-Shipment Inspection (PSI) and Quality Inspection certificates.
These documents verify that goods meet quality/quantity standards before shipment.

IMPORTANT RULES:
1. Extract ONLY what is explicitly stated in the document
2. Inspection agency/company name is CRITICAL (must be approved agency)
3. Inspection result (passed/failed) must be captured
4. If a field label is on the document but the value is blank, include the key with ""
5. If a field is NOT on the document at all, OMIT the key from your output - do NOT return null
6. Be precise - banks verify inspection agency against LC requirements
7. VERBATIM: Copy every value EXACTLY as printed. Do NOT correct, modernize, or rename anything. You are a photocopier.

OUTPUT FORMAT: JSON only, no markdown, no explanation."""

INSPECTION_EXTRACTION_PROMPT = """Extract the following fields from this Inspection Certificate:

REQUIRED FIELDS:
- certificate_number: The certificate reference number
- inspection_agency: Name of the inspection company
- inspection_date: When inspection was performed
- inspection_result: PASSED, FAILED, or specific finding
- goods_description: Description of inspected goods

OPTIONAL FIELDS:
- issue_date: Date certificate was issued
- invoice_reference: Related invoice number
- lc_reference: Related LC number
- quantity_verified: Quantity that was inspected
- quality_finding: Quality assessment details
- inspector_name: Name of the inspector
- inspection_location: Where inspection took place

Return a JSON object. Include ONLY keys for fields that are actually present on the document. OMIT keys for fields that are not on the document — do not include them with null.

---
DOCUMENT TEXT:
{document_text}
---

Return ONLY valid JSON, no other text:"""


class InspectionCertificateAIFirstExtractor(AIFirstExtractor):
    """AI-first extractor for Inspection Certificates."""
    
    VALIDATORS = {
        "certificate_number": {
            "pattern": r"^[A-Z0-9][A-Z0-9\-\/\.]{1,30}$",
            "flags": re.I,
            "description": "Certificate number should be alphanumeric",
        },
        "inspection_date": {
            "pattern": r"^\d{4}-\d{2}-\d{2}$|^\d{2}[\/\-]\d{2}[\/\-]\d{4}$",
            "flags": 0,
            "description": "Date should be YYYY-MM-DD or DD/MM/YYYY",
        },
        "inspection_result": {
            "pattern": r"^(PASS(ED)?|FAIL(ED)?|CONFORM(S|ING)?|NON[\-\s]?CONFORM|SATISFACTORY|UNSATISFACTORY)$",
            "flags": re.I,
            "description": "Should be a clear pass/fail result",
        },
    }
    
    async def extract_inspection(
        self,
        raw_text: str,
        use_fallback_on_ai_failure: bool = True,
    ) -> Dict[str, Any]:
        """Extract inspection certificate fields using AI-first pattern."""
        if not raw_text or not raw_text.strip():
            return self._empty_result("empty_input")
        
        ai_result, ai_provider = await self._run_ai_extraction_generic(
            raw_text, INSPECTION_EXTRACTION_PROMPT, INSPECTION_EXTRACTION_SYSTEM_PROMPT,
            doc_type="inspection_certificate",
        )
        
        if not ai_result and use_fallback_on_ai_failure:
            logger.warning("AI inspection extraction failed, using regex fallback")
            return self._inspection_regex_fallback(raw_text)
        
        if not ai_result:
            return self._empty_result("ai_failed")
        
        fields: Dict[str, ExtractedFieldResult] = {}
        for field_name, ai_value in ai_result.items():
            if field_name.startswith("_"):
                continue
            field_result = self._process_field(field_name, ai_value, raw_text)
            fields[field_name] = field_result
        
        return self._build_output(fields, ai_provider, doc_type="inspection_certificate")
    
    def _inspection_regex_fallback(self, raw_text: str) -> Dict[str, Any]:
        """Regex fallback for inspection certificate."""
        result: Dict[str, Any] = {}
        
        match = re.search(r"(?:Certificate|Report)\s*(?:No\.?|#|Number)\s*[:\-]?\s*([A-Z0-9\-\/]+)", raw_text, re.I)
        if match:
            result["certificate_number"] = match.group(1).strip()
        
        match = re.search(r"(?:Inspection|Surveyed)\s*(?:By|Agency)\s*[:\-]?\s*([^\n]+)", raw_text, re.I)
        if match:
            result["inspection_agency"] = match.group(1).strip()
        
        result["_extraction_method"] = "regex_fallback"
        result["_status"] = "ai_failed_regex_used"
        return result
    
    def _build_output(
        self,
        fields: Dict[str, ExtractedFieldResult],
        ai_provider: str,
        doc_type: str = "inspection_certificate",
    ) -> Dict[str, Any]:
        output = super()._build_output(fields, ai_provider, doc_type=doc_type)
        output["_document_type"] = doc_type
        return output


# =====================================================================
# GENERIC AI EXTRACTION HELPER
# =====================================================================

def _extract_candidate_json_text(response: str) -> str:
    clean = response.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    match = re.search(r"\{[\s\S]*\}", clean)
    return match.group(0) if match else clean


def _wrap_ai_result_with_default_confidence(
    result: Dict[str, Any],
    default_confidence: float = 0.75,
) -> Dict[str, Any]:
    """Attach default confidence to scalar AI fields without mutating wrapper payloads."""
    wrapped: Dict[str, Any] = dict(result or {})
    for key, value in list(wrapped.items()):
        if not isinstance(key, str) or key.startswith("_"):
            continue
        if value is None:
            continue
        if isinstance(value, dict):
            # Keep already-structured field payloads untouched.
            if "value" in value or "confidence" in value:
                continue
            # Preserve nested wrapper maps (e.g., extracted_fields/data) for canonical filter.
            if key in {"extracted_fields", "fields", "data", "result", "payload"}:
                continue
        wrapped[key] = {"value": value, "confidence": default_confidence}
    return wrapped


def _unwrap_confidence_scalars_in_place(result: Dict[str, Any]) -> None:
    """Flatten ``{"value": X, "confidence": Y}`` wrappers back to scalar X.

    ``_wrap_ai_result_with_default_confidence`` above is used to feed
    ``_build_default_field_details_from_wrapped_result`` which reads
    ``.value``/``.confidence`` off every field to build the ``_field_details``
    sidecar. Once that sidecar has been built, the main payload should carry
    scalars again — downstream shaping code (``_shape_lc_financial_payload``,
    ``build_lc_intake_summary``, the intake card on the upload page, the
    Extract & Review screen) expects plain strings/numbers and will render
    a ``{value, confidence}`` dict as its literal Python repr. Until this
    helper was added, fields like ``lc_number`` and
    ``form_of_documentary_credit`` were leaking into the UI as
    ``{'value': 'EXP2026BD001', 'confidence': 0.82}``.

    Only unwraps dicts that look exactly like a confidence wrapper — a
    ``value`` key plus at most a ``confidence`` key. Structural dicts like
    ``applicant = {name, address, country}`` or ``amount = {value, currency}``
    are left alone because those are consumed by field-specific unwrap
    branches in ``_shape_lc_financial_payload``.
    """
    if not isinstance(result, dict):
        return
    for key in list(result.keys()):
        if not isinstance(key, str) or key.startswith("_"):
            continue
        value = result[key]
        if not isinstance(value, dict) or "value" not in value:
            continue
        extra_keys = set(value.keys()) - {"value", "confidence"}
        if extra_keys:
            # Structural field payload (applicant, amount with currency, etc.) —
            # leave it for the field-specific unwrap branches downstream.
            continue
        result[key] = value.get("value")


# Field-name heuristics for the structural-field flattener below.  A field
# whose name matches any of these suggests a legitimately-plural shape and
# should NOT be collapsed to a scalar.  The check is on the canonical key
# name, so `line_items`, `goods_items` stay as lists when the LLM returns
# them that way, while `hs_code`, `quantity`, `size_breakdown` get flattened
# because the review form expects scalars.
_PLURAL_FIELD_NAME_FRAGMENTS: Tuple[str, ...] = (
    "_items",
    "_list",
    "_lines",
    "_entries",
    "_rows",
    "line_items",
    "goods_items",
)

# Suffix used for the structured-data sidecar written when we flatten a
# multi-item field.  Keys ending in this suffix are considered already-
# sidecar and are skipped on subsequent flatten passes (idempotency).
_STRUCTURAL_SIDECAR_SUFFIX = "__items"

# Keys we recognize as structural party/amount sub-objects.  A dict that
# carries any of these keys is assumed to be a structured record (applicant
# with {name, address, country}, amount with {value, currency}, etc.) and is
# left alone so the per-field unwrap branches in ``_shape_lc_financial_payload``
# / ``_shape_invoice_financial_payload`` continue to work.
_STRUCTURAL_DICT_KEYS: frozenset = frozenset({
    "name",
    "address",
    "country",
    "country_name",
    "country_code",
    "bic",
    "swift_code",
    "value",
    "amount",
    "currency",
    "code",
    "number",
    "iso",
    "postal_code",
})

# Numeric sub-field names we can sum across a list of line-item dicts.
# Matched case-insensitively against the dict keys.
_LINE_ITEM_NUMERIC_KEYS: frozenset = frozenset({
    "quantity",
    "qty",
    "amount",
    "value",
    "total",
    "weight",
    "gross_weight",
    "net_weight",
    "count",
    "packages",
    "cartons",
})


def _looks_like_plural_field(key: str) -> bool:
    if not isinstance(key, str):
        return False
    k = key.lower()
    return any(frag in k for frag in _PLURAL_FIELD_NAME_FRAGMENTS)


def _looks_like_structural_dict(value: Dict[str, Any]) -> bool:
    """Return True if the dict looks like a structured party / amount payload
    rather than a flat key -> number rollup map."""
    if not isinstance(value, dict) or not value:
        return False
    return any(k in _STRUCTURAL_DICT_KEYS for k in value.keys() if isinstance(k, str))


def _flatten_structural_field_values_in_place(result: Dict[str, Any]) -> None:
    """Collapse list-of-dict / dict-of-scalar values to scalar + breakdown sidecar.

    The vision LLM legitimately returns multi-item structured data when a
    document has several line items:

    * an invoice for 3 SKUs can return
      ``quantity = [{"item": "...", "quantity": 30000}, ...]``
    * a packing list can return
      ``size_breakdown = {"Small": 1000, "Medium": 500}``
    * an invoice with 3 HS codes can return
      ``hs_code = ["61091000", "62034200", "61044200"]``

    The structured shape is semantically correct — the document really has
    multiple items — but the Extract & Review form widgets and downstream
    scalar-comparing rules (amount tolerance, HS-code lookup, etc.) expect
    one value per field.  Left alone, the frontend's ``coerceToString``
    ``JSON.stringify`` fallback would render those values as jsonish
    strings in the review inputs.

    This helper collapses each structured value into a scalar representation
    suitable for the review form and preserves the original structured data
    in a sibling key ``<field>_breakdown`` so validators, the customs pack,
    and any downstream consumer that cares about line items can still reach
    the full data.

    Rules (in priority order):

    1. Skip private keys (``_extraction_method`` etc.) and plural field
       names (``line_items`` / ``goods_items`` / ``...{_items,_list,_lines}``)
       — those are intentionally list-shaped and should not be flattened.
    2. Skip dicts that carry structural party/amount keys
       (``name``/``address``/``currency``/...).  Those are handled by the
       per-field unwrap branches in ``_shape_X_financial_payload``.
    3. ``List[Dict]`` with a shared numeric sub-key (``quantity``/``qty``/
       ``amount``/``weight``/...) → sum the numeric sub-key, store total as
       the scalar value, keep the list in ``<field>_breakdown``.
    4. ``List[Dict]`` without a summable numeric sub-key → join the item
       description/name fields with ``"; "``, keep the list as sidecar.
    5. ``List[scalar]`` → join with ``", "``, keep the list as sidecar.
    6. ``Dict[str, scalar]`` that is not a structural dict → render as
       ``"k: v, k2: v2"``, keep the dict as sidecar.
    7. Everything else passes through untouched.

    The helper mutates ``result`` in place and is idempotent: running it
    twice is a no-op because the second pass sees scalars.
    """
    if not isinstance(result, dict):
        return

    for key in list(result.keys()):
        if not isinstance(key, str) or key.startswith("_"):
            continue
        if _looks_like_plural_field(key):
            continue
        # Already-sidecar keys from a previous flatten pass — leave them
        # alone so a second call on the same dict is a no-op.
        if key.endswith(_STRUCTURAL_SIDECAR_SUFFIX):
            continue

        value = result[key]
        sidecar_key = f"{key}{_STRUCTURAL_SIDECAR_SUFFIX}"

        # List[Dict] — line items
        if (
            isinstance(value, list)
            and value
            and all(isinstance(item, dict) for item in value)
        ):
            # Find a numeric sub-key shared by every item in the list.
            numeric_sub_key: Optional[str] = None
            for candidate in _LINE_ITEM_NUMERIC_KEYS:
                if all(
                    isinstance(item.get(candidate), (int, float))
                    for item in value
                    if isinstance(item, dict)
                ):
                    numeric_sub_key = candidate
                    break
            if numeric_sub_key:
                try:
                    total = sum(
                        float(item[numeric_sub_key])
                        for item in value
                        if isinstance(item, dict)
                    )
                    result[key] = int(total) if total.is_integer() else total
                except (TypeError, ValueError):
                    result[key] = None
            else:
                # No numeric rollup — join human-readable descriptions.
                parts: List[str] = []
                for item in value:
                    if not isinstance(item, dict):
                        continue
                    desc = (
                        item.get("description")
                        or item.get("item")
                        or item.get("name")
                        or item.get("title")
                        or item.get("label")
                    )
                    if desc is None:
                        desc = ", ".join(f"{k}: {v}" for k, v in item.items())
                    parts.append(str(desc))
                result[key] = "; ".join(parts) if parts else None
            # Preserve the structured data so validators and the customs
            # pack can still get at the line items.
            result.setdefault(sidecar_key, value)
            continue

        # List[scalar] — join with commas
        if (
            isinstance(value, list)
            and value
            and all(isinstance(item, (str, int, float, bool)) for item in value)
        ):
            result[key] = ", ".join(str(item) for item in value)
            result.setdefault(sidecar_key, list(value))
            continue

        # Dict[str, scalar] — map of label -> number, render "k: v, k2: v2"
        if (
            isinstance(value, dict)
            and value
            and all(
                isinstance(v, (str, int, float, bool))
                for v in value.values()
            )
            and not _looks_like_structural_dict(value)
        ):
            result[key] = ", ".join(
                f"{k}: {v}" for k, v in value.items() if k is not None
            )
            result.setdefault(sidecar_key, dict(value))
            continue


async def _repair_json_once(
    provider: Any,
    response_text: str,
) -> Optional[Dict[str, Any]]:
    """One retry/repair path for invalid JSON responses."""
    try:
        repair_prompt = (
            "Repair this payload into valid JSON object only. Keep original keys and values, "
            "remove comments/markdown/trailing commas, do not add explanatory text.\n\n"
            f"PAYLOAD:\n{response_text[:8000]}"
        )
        repaired, _, _ = await provider.generate(
            prompt=repair_prompt,
            system_prompt="You are a JSON repair tool. Return ONLY valid JSON object.",
            temperature=0.0,
            max_tokens=2200,
        )
        candidate = _extract_candidate_json_text(repaired)
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


async def _parse_llm_json_with_repair(
    provider: Any,
    response: str,
) -> Optional[Dict[str, Any]]:
    candidate = _extract_candidate_json_text(response)
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return await _repair_json_once(provider, response)


async def _run_ai_extraction_generic(
    self,
    raw_text: str,
    prompt_template: str,
    system_prompt: str,
    doc_type: str = "unknown",
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Generic AI extraction for any document type."""
    try:
        from ..llm_provider import LLMProviderFactory
        
        provider = LLMProviderFactory.create_provider()
        if not provider:
            logger.warning("No LLM provider available")
            return None, "none"

        prompt = prompt_template.format(document_text=raw_text[:12000])

        response, tokens_in, tokens_out, provider_used, llm_trace = await _generate_extraction_with_model_routing(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=2000,
        )
        _log_ai_first_event(
            "generic_model_call",
            provider=llm_trace["provider"],
            model=llm_trace["model"],
            router_layer=llm_trace["router_layer"],
            ai_response_present=bool(response),
        )
        
        if not response:
            return None, "empty_response"
        
        logger.info(f"Generic AI extraction: tokens_in={tokens_in} tokens_out={tokens_out}")
        
        result = await _parse_llm_json_with_repair(provider, response)
        if not result:
            _log_ai_first_event(
                "generic_parse_output",
                provider=llm_trace["provider"],
                model=llm_trace["model"],
                router_layer=llm_trace["router_layer"],
                ai_parse_success=False,
            )
            logger.warning("Failed to parse/repair AI response")
            return None, "parse_error"

        # --- Two-stage review: Sonnet cross-checks cheap model output ---
        result, review_trace = await _review_extraction(raw_text, result, doc_type)
        if review_trace.get("reviewed"):
            llm_trace["review"] = review_trace

        result = _wrap_ai_result_with_default_confidence(result)
        _unwrap_confidence_scalars_in_place(result)
        _flatten_structural_field_values_in_place(result)
        result["_llm_provider"] = llm_trace["provider"]
        result["_llm_model"] = llm_trace["model"]
        result["_llm_router_layer"] = llm_trace["router_layer"]
        result["_two_stage_review"] = review_trace.get("outcome", "skipped")
        _log_ai_first_event(
            "generic_parse_output",
            provider=llm_trace["provider"],
            model=llm_trace["model"],
            router_layer=llm_trace["router_layer"],
            ai_parse_success=True,
            parsed_field_count=sum(1 for k, v in result.items() if isinstance(k, str) and not k.startswith("_") and v not in (None, "", [], {})),
            two_stage_review=review_trace.get("outcome", "skipped"),
        )

        return result, provider_used

    except Exception as e:
        logger.error(f"AI extraction error: {e}", exc_info=True)
        return None, "error"


# Add the method to base class
AIFirstExtractor._run_ai_extraction_generic = _run_ai_extraction_generic


# =====================================================================
# GLOBAL INSTANCES AND CONVENIENCE FUNCTIONS
# =====================================================================

_invoice_extractor: Optional[InvoiceAIFirstExtractor] = None
_bl_extractor: Optional[BLAIFirstExtractor] = None
_packing_list_extractor: Optional[PackingListAIFirstExtractor] = None
_coo_extractor: Optional[CertificateOfOriginAIFirstExtractor] = None
_insurance_extractor: Optional[InsuranceCertificateAIFirstExtractor] = None
_inspection_extractor: Optional[InspectionCertificateAIFirstExtractor] = None


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


def get_packing_list_ai_first_extractor() -> PackingListAIFirstExtractor:
    """Get or create the packing list AI-first extractor."""
    global _packing_list_extractor
    if _packing_list_extractor is None:
        _packing_list_extractor = PackingListAIFirstExtractor()
    return _packing_list_extractor


def get_coo_ai_first_extractor() -> CertificateOfOriginAIFirstExtractor:
    """Get or create the certificate of origin AI-first extractor."""
    global _coo_extractor
    if _coo_extractor is None:
        _coo_extractor = CertificateOfOriginAIFirstExtractor()
    return _coo_extractor


def get_insurance_ai_first_extractor() -> InsuranceCertificateAIFirstExtractor:
    """Get or create the insurance certificate AI-first extractor."""
    global _insurance_extractor
    if _insurance_extractor is None:
        _insurance_extractor = InsuranceCertificateAIFirstExtractor()
    return _insurance_extractor


def get_inspection_ai_first_extractor() -> InspectionCertificateAIFirstExtractor:
    """Get or create the inspection certificate AI-first extractor."""
    global _inspection_extractor
    if _inspection_extractor is None:
        _inspection_extractor = InspectionCertificateAIFirstExtractor()
    return _inspection_extractor


async def extract_invoice_ai_first(raw_text: str) -> Dict[str, Any]:
    """Convenience function for AI-first invoice extraction."""
    extractor = get_invoice_ai_first_extractor()
    return await extractor.extract_invoice(raw_text)


async def extract_bl_ai_first(raw_text: str) -> Dict[str, Any]:
    """Convenience function for AI-first B/L extraction."""
    extractor = get_bl_ai_first_extractor()
    return await extractor.extract_bl(raw_text)


async def extract_packing_list_ai_first(raw_text: str) -> Dict[str, Any]:
    """Convenience function for AI-first packing list extraction."""
    extractor = get_packing_list_ai_first_extractor()
    return await extractor.extract_packing_list(raw_text)


async def extract_coo_ai_first(raw_text: str) -> Dict[str, Any]:
    """Convenience function for AI-first certificate of origin extraction."""
    extractor = get_coo_ai_first_extractor()
    return await extractor.extract_coo(raw_text)


async def extract_insurance_ai_first(raw_text: str) -> Dict[str, Any]:
    """Convenience function for AI-first insurance certificate extraction."""
    extractor = get_insurance_ai_first_extractor()
    return await extractor.extract_insurance(raw_text)


async def extract_inspection_ai_first(raw_text: str) -> Dict[str, Any]:
    """Convenience function for AI-first inspection certificate extraction."""
    extractor = get_inspection_ai_first_extractor()
    return await extractor.extract_inspection(raw_text)

