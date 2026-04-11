# apps/api/app/services/extraction/ai_lc_extractor.py
"""
AI-powered LC extraction using GPT/Claude when rule-based parsers fail.

This is the fallback extractor that handles:
- Unknown LC formats
- Poor quality OCR
- Bank-specific templates
- Any format the regex/MT700 parsers can't handle
"""

import json
import logging
import re
from typing import Dict, Any, Optional, Tuple

from ..llm_provider import LLMProviderFactory

logger = logging.getLogger(__name__)

# =====================================================================
# SYSTEM PROMPT - Trade Finance Expert
# =====================================================================
LC_EXTRACTION_SYSTEM_PROMPT = """You are an expert trade finance document parser specializing in Letters of Credit (LC).

Your task is to extract structured data from LC documents. These documents may be:
- SWIFT MT700 format (raw or formatted)
- Bank-specific PDF exports
- Scanned documents with OCR text
- Any other LC format

IMPORTANT RULES:
1. Extract ONLY what is explicitly stated in the document
2. If a field label is on the document but the value is blank or unclear, include the key with an empty string ""
3. If a field is NOT on the document at all, OMIT the key entirely from your output - do NOT return null, do NOT guess
4. For amounts, include the full number without currency symbols
5. For dates, use ISO format (YYYY-MM-DD) when possible
6. For parties (applicant/beneficiary), extract the company/person NAME only
7. Be precise - banks rely on exact data
8. VERBATIM: Copy every value EXACTLY as printed. Do NOT correct, modernize, or rename anything. If it says 'Chittagong' write 'Chittagong', not 'Chattogram'. You are a photocopier.

OUTPUT FORMAT: JSON only, no markdown, no explanation."""

# =====================================================================
# USER PROMPT TEMPLATE
# =====================================================================
LC_EXTRACTION_PROMPT = """Extract the following fields from this Letter of Credit document:

REQUIRED FIELDS:
- lc_number: The LC reference number (e.g., "LC1234567", "EXP2026BD001")
- lc_type: The form of documentary credit (e.g., "IRREVOCABLE", "IRREVOCABLE TRANSFERABLE", "SIGHT", "USANCE", "DEFERRED PAYMENT")
- amount: The credit amount as a number (e.g., 458750.00)
- currency: The currency code (e.g., "USD", "EUR", "GBP")
- applicant: The buyer/importer company name
- beneficiary: The seller/exporter company name
- issuing_bank: The bank that issued the LC (SWIFT field :52A:)
- advising_bank: The bank advising the LC (SWIFT field :57A:)
- port_of_loading: The shipment origin port
- port_of_discharge: The destination port
- expiry_date: When the LC expires (ISO format YYYY-MM-DD)
- latest_shipment_date: Last allowed shipment date (ISO format YYYY-MM-DD)
- issue_date: When the LC was issued (ISO format YYYY-MM-DD, SWIFT field :31C:)
- incoterm: The trade term (e.g., "FOB", "CIF", "CFR")

OPTIONAL FIELDS:
- confirming_bank: The bank confirming the LC (if any)
- ucp_reference: UCP version (e.g., "UCP 600", "UCP LATEST VERSION")
- partial_shipments: "ALLOWED" or "NOT ALLOWED"
- transshipment: "ALLOWED" or "NOT ALLOWED"
- goods_description: Full description of goods including HS codes if present
- documents_required: List of required documents (e.g., "Commercial Invoice", "Bill of Lading", etc.)
- additional_conditions: Array of additional conditions from Field 47A (e.g., ["DOCUMENTS MUST BE PRESENTED WITHIN 21 DAYS", "ALL DOCS MUST INDICATE PO NUMBER 12345"])
- payment_terms: Payment conditions (e.g., "AT SIGHT", "60 DAYS AFTER B/L DATE")
- available_with: How the LC is available (e.g., "BY NEGOTIATION", "BY PAYMENT", "BY ACCEPTANCE")

Return a JSON object with EXACTLY these canonical keys only. Use null for any field not found. Do not add extra keys.

---
DOCUMENT TEXT:
{document_text}
---

Return ONLY valid JSON, no other text:"""


async def extract_lc_with_ai(
    ocr_text: str,
    max_chars: int = 12000,
    temperature: float = 0.1,
    use_ensemble: bool = True,
) -> Tuple[Dict[str, Any], float, str]:
    """
    Extract LC fields using AI when rule-based parsers fail.
    
    Args:
        ocr_text: The OCR/raw text from the LC document
        max_chars: Maximum characters to send (truncate if longer)
        temperature: LLM temperature (lower = more deterministic)
        use_ensemble: If True, use multi-model ensemble for higher accuracy
    
    Returns:
        (extracted_fields, confidence_score, provider_used)
    """
    if not ocr_text or not ocr_text.strip():
        logger.warning("AI LC Extractor: Empty text provided")
        return {}, 0.0, "none"
    
    # Truncate if too long (save tokens + stay under context limits)
    text_to_process = ocr_text[:max_chars] if len(ocr_text) > max_chars else ocr_text
    
    # Ensemble disabled — single Opus/Sonnet call is more accurate and
    # costs the same as running 3 providers in parallel.
    # The LC is the anchor document; use the best model available.
    import os as _os
    lc_model = (
        _os.getenv("EXTRACTION_LC_MODEL")
        or _os.getenv("EXTRACTION_VISION_L2_MODEL")
        or _os.getenv("EXTRACTION_PRIMARY_MODEL")
        or "anthropic/claude-opus-4-6"
    )
    lc_provider = (
        _os.getenv("EXTRACTION_LC_PROVIDER")
        or _os.getenv("EXTRACTION_VISION_L2_PROVIDER")
        or _os.getenv("EXTRACTION_PRIMARY_PROVIDER")
        or "openrouter"
    )

    prompt = LC_EXTRACTION_PROMPT.format(document_text=text_to_process)

    try:
        output, tokens_in, tokens_out, provider = await LLMProviderFactory.generate_with_fallback(
            prompt=prompt,
            system_prompt=LC_EXTRACTION_SYSTEM_PROMPT,
            max_tokens=1500,
            temperature=temperature,
            primary_provider=lc_provider,
            model_override=lc_model,
        )
        
        logger.info(
            "AI LC Extraction: provider=%s tokens_in=%d tokens_out=%d",
            provider, tokens_in, tokens_out
        )
        
        # Parse JSON response (+ one repair retry if invalid)
        extracted = _parse_ai_response(output)
        if not extracted:
            repaired = await _repair_ai_json_once(output)
            extracted = _parse_ai_response(repaired) if repaired else {}

        # Calculate confidence based on how many fields were extracted
        confidence = _calculate_extraction_confidence(extracted)
        
        logger.info(
            "AI LC Extraction result: %d fields extracted, confidence=%.2f",
            len([v for v in extracted.values() if v is not None]),
            confidence
        )
        
        # Mark as single-provider extraction
        extracted["_extraction_method"] = "single"
        extracted["_providers_used"] = [provider]
        
        return extracted, confidence, provider
        
    except Exception as e:
        logger.error(f"AI LC Extraction failed: {e}", exc_info=True)
        return {}, 0.0, "error"


def _parse_ai_response(response: str) -> Dict[str, Any]:
    """Parse JSON from AI response, handling common issues."""
    if not response:
        return {}
    
    # Clean up response - remove markdown code blocks if present
    cleaned = response.strip()
    
    # Remove ```json ... ``` wrapper if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Find the actual JSON content
        start_idx = 1 if lines[0].startswith("```") else 0
        end_idx = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "```":
                end_idx = i
                break
        cleaned = "\n".join(lines[start_idx:end_idx])
    
    # Try to find JSON object in response
    json_match = re.search(r'\{[\s\S]*\}', cleaned)
    if json_match:
        cleaned = json_match.group(0)
    
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse AI response as JSON: {e}")
        logger.debug(f"Raw response: {response[:500]}...")
        return {}


async def _repair_ai_json_once(raw_response: str) -> Optional[str]:
    """Single retry path to repair malformed JSON from model output."""
    try:
        provider = LLMProviderFactory.create_provider()
        if not provider:
            return None
        prompt = (
            "Repair the following payload into a valid JSON object only. "
            "Do not add commentary. Preserve original keys and values where possible.\n\n"
            f"PAYLOAD:\n{raw_response[:8000]}"
        )
        repaired, _, _ = await provider.generate(
            prompt=prompt,
            system_prompt="You are a JSON repair tool. Return ONLY valid JSON object.",
            temperature=0.0,
            max_tokens=1800,
        )
        return repaired
    except Exception as exc:
        logger.warning("LC JSON repair attempt failed: %s", exc)
        return None


def _calculate_extraction_confidence(extracted: Dict[str, Any]) -> float:
    """
    Calculate confidence score based on extracted fields.
    
    Critical fields are weighted higher.
    """
    if not extracted:
        return 0.0
    
    # Field weights (higher = more critical)
    field_weights = {
        "lc_number": 15,
        "lc_type": 10,  # Critical - determines LC classification
        "amount": 15,
        "currency": 10,
        "applicant": 10,
        "beneficiary": 10,
        "port_of_loading": 5,
        "port_of_discharge": 5,
        "expiry_date": 8,
        "latest_shipment_date": 5,
        "incoterm": 5,
        "issuing_bank": 8,  # Increased - critical for bank verification
        "issue_date": 5,  # Increased - needed for validation
        "advising_bank": 5,  # Increased - important for routing
        "confirming_bank": 3,
        "ucp_reference": 2,
        "partial_shipments": 2,
        "transshipment": 2,
        "goods_description": 5,  # Increased - needed for cross-doc matching
        "documents_required": 5,  # New - critical for checklist
        "payment_terms": 4,  # New - determines payment type
        "available_with": 3,  # New - negotiation method
    }
    
    total_weight = sum(field_weights.values())
    extracted_weight = 0
    
    for field, weight in field_weights.items():
        value = extracted.get(field)
        if value is not None and value != "" and value != {}:
            extracted_weight += weight
    
    confidence = extracted_weight / total_weight
    return round(confidence, 2)


def convert_ai_to_lc_structure(ai_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert AI extraction result to standard LC structure format.
    
    This maps the AI output to the same structure as the regex/MT700 parsers.
    """
    if not ai_result:
        return {}
    
    # Parse amount
    amount_val = ai_result.get("amount")
    if isinstance(amount_val, str):
        try:
            amount_val = float(amount_val.replace(",", ""))
        except (ValueError, TypeError):
            pass
    
    currency = ai_result.get("currency")
    
    # Build applicant/beneficiary structures
    applicant = None
    if ai_result.get("applicant"):
        applicant = {"name": ai_result["applicant"]}
    
    beneficiary = None
    if ai_result.get("beneficiary"):
        beneficiary = {"name": ai_result["beneficiary"]}
    
    # Build ports
    ports = {
        "loading": ai_result.get("port_of_loading"),
        "discharge": ai_result.get("port_of_discharge"),
    }
    
    # Build timeline
    timeline = {
        "issue_date": ai_result.get("issue_date"),
        "expiry_date": ai_result.get("expiry_date"),
        "latest_shipment": ai_result.get("latest_shipment_date"),
    }
    
    # Normalize LC type
    lc_type_raw = ai_result.get("lc_type")
    lc_type = None
    lc_type_confidence = 0
    if lc_type_raw:
        lc_type = str(lc_type_raw).upper()
        lc_type_confidence = 0.85
        # Normalize common variations
        if "IRREVOCABLE" in lc_type and "TRANSFERABLE" in lc_type:
            lc_type = "irrevocable_transferable"
        elif "IRREVOCABLE" in lc_type:
            lc_type = "irrevocable"
        elif "SIGHT" in lc_type:
            lc_type = "sight"
        elif "USANCE" in lc_type or "DEFERRED" in lc_type:
            lc_type = "usance"
        else:
            lc_type = lc_type.lower().replace(" ", "_")
    
    return {
        "number": ai_result.get("lc_number"),
        "lc_type": lc_type,
        "lc_type_confidence": lc_type_confidence,
        "lc_type_reason": f"Extracted from LC document: {lc_type_raw}" if lc_type_raw else "Not found in document",
        "lc_type_source": "ai_extraction",
        "amount": {"value": amount_val, "currency": currency} if amount_val else None,
        "currency": currency,
        "applicant": applicant,
        "beneficiary": beneficiary,
        "ports": ports,
        "incoterm": ai_result.get("incoterm"),
        "issuing_bank": ai_result.get("issuing_bank"),
        "advising_bank": ai_result.get("advising_bank"),
        "confirming_bank": ai_result.get("confirming_bank"),
        "ucp_reference": ai_result.get("ucp_reference"),
        "timeline": timeline,
        "partial_shipments": ai_result.get("partial_shipments"),
        "transshipment": ai_result.get("transshipment"),
        "goods_description": ai_result.get("goods_description"),
        "documents_required": ai_result.get("documents_required"),
        "payment_terms": ai_result.get("payment_terms"),
        "available_with": ai_result.get("available_with"),
        "source": {
            "parsers": ["ai_extraction"],
            "version": "ai_lc_extractor_v2",
        },
        # Mark as AI-extracted for audit
        "_extraction_method": "ai",
        "_ai_confidence": ai_result.get("_confidence", 0.0),
    }

