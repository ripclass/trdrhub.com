"""
AI-Powered LC Validation Engine - FOCUSED VERSION

This module provides TARGETED AI-driven validation:
1. Document Completeness - Check if required docs are uploaded
2. B/L Field Validation - Check specific field requirements

NOTE: Goods matching is handled by crossdoc_validator - we skip it here to avoid duplicates.
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from app.config import settings
from app.services.ai.model_router import ModelRouter

logger = logging.getLogger(__name__)


def _coerce_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            normalized = value.replace(",", "").strip()
            if not normalized:
                return None
            return float(normalized)
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    if isinstance(value, (tuple, set)):
        return list(value)
    return []


def _coerce_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


@dataclass
class AIValidationIssue:
    """An issue detected by the AI validator."""
    rule_id: str
    title: str
    severity: IssueSeverity
    message: str
    expected: str
    found: str
    suggestion: str
    documents: List[str] = field(default_factory=list)
    ucp_reference: Optional[str] = None
    isbp_reference: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule_id,
            "title": self.title,
            "severity": self.severity.value,
            "message": self.message,
            "expected": self.expected,
            "actual": self.found,
            "suggestion": self.suggestion,
            "documents": self.documents,
            "document_names": self.documents,
            "ucp_reference": self.ucp_reference,
            "isbp_reference": self.isbp_reference,
            "ruleset_domain": "icc.lcopilot.ai_validation",
            "display_card": True,
            "auto_generated": True,
            "passed": False,
        }


# =============================================================================
# LC REQUIREMENT PARSER
# =============================================================================

def parse_lc_requirements_sync(lc_text: str) -> Dict[str, Any]:
    """
    Parse LC requirements from 46A clause using regex.
    Returns structured requirements that can be validated against.
    """
    if not lc_text or len(lc_text.strip()) < 50:
        logger.warning(f"LC text too short: {len(lc_text) if lc_text else 0} chars")
        return {"required_documents": [], "bl_must_show": []}
    
    text_upper = lc_text.upper()
    docs = []
    bl_must_show = []
    
    logger.info(f"Parsing LC requirements from {len(lc_text)} chars")
    
    # =================================================================
    # CRITICAL DOCUMENTS TO DETECT
    # =================================================================
    
    # 1. INSPECTION CERTIFICATE (SGS/Intertek)
    if "INSPECTION" in text_upper:
        issuer = None
        if "SGS" in text_upper:
            issuer = "SGS"
        if "INTERTEK" in text_upper:
            issuer = f"{issuer}/Intertek" if issuer else "Intertek"
        if "BUREAU VERITAS" in text_upper:
            issuer = f"{issuer}/Bureau Veritas" if issuer else "Bureau Veritas"
        
        docs.append({
            "document_type": "inspection_certificate",
            "display_name": f"Inspection Certificate{f' ({issuer})' if issuer else ''}",
            "issuer": issuer,
        })
        logger.info(f"✓ Detected: Inspection Certificate requirement (issuer: {issuer})")
    
    # 2. BENEFICIARY CERTIFICATE
    if "BENEFICIARY" in text_upper and any(x in text_upper for x in ["CERTIFICATE", "CERTIFYING", "STATING"]):
        must_state = None
        if "BRAND NEW" in text_upper:
            must_state = "goods are brand new"
        if "MANUFACTURED" in text_upper:
            year_match = re.search(r'MANUFACTURED\s*(?:IN\s*)?(\d{4})', text_upper)
            year = year_match.group(1) if year_match else "2026"
            must_state = f"{must_state}, manufactured in {year}" if must_state else f"manufactured in {year}"
        
        docs.append({
            "document_type": "beneficiary_certificate",
            "display_name": "Beneficiary Certificate",
            "must_state": must_state,
        })
        logger.info(f"✓ Detected: Beneficiary Certificate requirement")
    
    # =================================================================
    # B/L FIELD REQUIREMENTS
    # =================================================================
    
    # Check what B/L must show
    if "VOYAGE" in text_upper or "VOY" in text_upper:
        bl_must_show.append("voyage_number")
    if "GROSS" in text_upper and "WEIGHT" in text_upper:
        bl_must_show.append("gross_weight")
    if "NET" in text_upper and "WEIGHT" in text_upper:
        bl_must_show.append("net_weight")
    
    if bl_must_show:
        logger.info(f"✓ B/L must show: {bl_must_show}")
    
    return {
        "required_documents": docs,
        "bl_must_show": bl_must_show,
    }


# =============================================================================
# DOCUMENT COMPLETENESS CHECKER
# =============================================================================

def check_document_completeness(
    required_docs: List[Dict[str, Any]],
    uploaded_docs: List[Dict[str, Any]],
) -> List[AIValidationIssue]:
    """
    Check if CRITICAL required documents are present.
    Only checks: inspection_certificate, beneficiary_certificate
    """
    issues = []
    
    # Build set of uploaded document types from multiple sources
    uploaded_types: Set[str] = set()
    uploaded_filenames: List[str] = []
    
    for doc in uploaded_docs:
        # Get document type
        doc_type = (doc.get("document_type") or doc.get("type") or "").lower().replace(" ", "_")
        if doc_type:
            uploaded_types.add(doc_type)
        
        # Get filename
        filename = (doc.get("filename") or doc.get("name") or doc.get("original_filename") or "").lower()
        uploaded_filenames.append(filename)
        
        # Infer from filename
        if "inspection" in filename:
            uploaded_types.add("inspection_certificate")
        if "beneficiary" in filename:
            uploaded_types.add("beneficiary_certificate")
    
    logger.info(f"Uploaded types: {uploaded_types}")
    logger.info(f"Uploaded files: {uploaded_filenames}")
    
    # Check each CRITICAL required document
    for req in required_docs:
        req_type = req.get("document_type", "").lower()
        display_name = req.get("display_name", req_type)
        
        # Only check critical missing documents
        if req_type not in ["inspection_certificate", "beneficiary_certificate"]:
            continue
        
        if req_type not in uploaded_types:
            issuer = req.get("issuer")
            must_state = req.get("must_state")
            
            expected_text = f"{display_name} as specified in LC clause 46A"
            if issuer:
                expected_text = f"{display_name} issued by {issuer}"
            if must_state:
                expected_text = f"{display_name} stating: {must_state}"
            
            # Build list of what WAS uploaded
            found_text = f"Not found. Uploaded documents: {', '.join(uploaded_filenames) if uploaded_filenames else 'None'}"
            
            # Build specific suggestion based on document type
            if req_type == "inspection_certificate":
                suggestion = f"Contact {issuer or 'SGS/Intertek/Bureau Veritas'} to schedule a pre-shipment inspection. Obtain the certificate confirming quality, quantity, and packing before document presentation."
            elif req_type == "beneficiary_certificate":
                suggestion = f"Prepare a Beneficiary Certificate on your company letterhead stating: '{must_state or 'goods are brand new and manufactured as specified'}'. Sign, stamp, and date the certificate."
            else:
                suggestion = f"Obtain and upload the required {display_name} before bank submission."
            
            issues.append(AIValidationIssue(
                rule_id=f"AI-MISSING-{req_type.upper()}",
                title=f"Missing Required Document: {display_name}",
                severity=IssueSeverity.CRITICAL,
                message=f"LC clause 46A requires {display_name} but this document was not provided.",
                expected=expected_text,
                found="Document not provided in submission",
                suggestion=suggestion,
                documents=[display_name],
                ucp_reference="UCP600 Article 14(a)",
                isbp_reference="ISBP745 A14",
            ))
            logger.info(f"✗ Missing: {display_name}")
    
    return issues


# =============================================================================
# B/L FIELD VALIDATOR
# =============================================================================

def validate_bl_fields(
    required_fields: List[str],
    bl_data: Dict[str, Any],
) -> List[AIValidationIssue]:
    """
    Validate B/L has required fields, showing actual extracted values.
    """
    if not required_fields:
        return []
    
    issues = []
    
    # Normalize B/L data keys to lowercase
    bl_lower = {}
    for k, v in bl_data.items():
        if v and not k.startswith("_"):  # Skip metadata fields
            bl_lower[k.lower()] = v
    
    logger.info(f"B/L extracted fields: {list(bl_lower.keys())}")
    
    # Field mappings - what keys to check for each requirement
    field_info = {
        "voyage_number": {
            "keys": ["voyage_number", "voyage", "voyage_no", "voy_no"],
            "display": "Voyage Number",
        },
        "gross_weight": {
            "keys": ["gross_weight", "gw", "gross_wt", "total_gross_weight"],
            "display": "Gross Weight",
        },
        "net_weight": {
            "keys": ["net_weight", "nw", "net_wt", "total_net_weight"],
            "display": "Net Weight",
        },
    }
    
    checked_fields: Set[str] = set()  # Track to avoid duplicates
    
    for req_field in required_fields:
        # Skip if already checked (avoid duplicates)
        if req_field in checked_fields:
            continue
        checked_fields.add(req_field)
        
        info = field_info.get(req_field, {"keys": [req_field], "display": req_field.replace("_", " ").title()})
        
        # Look for the field in B/L data
        found_value = None
        for key in info["keys"]:
            if key in bl_lower:
                found_value = bl_lower[key]
                break
        
        if found_value:
            logger.info(f"✓ B/L has {info['display']}: {found_value}")
        else:
            # Concise "Found" text - just state the field is missing
            found_text = f"{info['display']} not found in Bill of Lading"
            
            # Build specific suggestion based on field type
            if req_field == "voyage_number":
                suggestion = "Contact your shipping line/carrier to request an amended B/L showing the voyage number. This is typically in format 'VOY. 123E' or similar."
            elif req_field == "gross_weight":
                suggestion = "Request the carrier to add gross weight (G.W.) to the B/L. This should match the packing list gross weight (e.g., '20,400 KGS')."
            elif req_field == "net_weight":
                suggestion = "Request the carrier to add net weight (N.W.) to the B/L. This should match the packing list net weight (e.g., '18,950 KGS')."
            else:
                suggestion = f"Request amended B/L from carrier showing the {info['display']}."
            
            issues.append(AIValidationIssue(
                rule_id=f"AI-BL-MISSING-{req_field.upper()}",
                title=f"B/L Missing Required Field: {info['display']}",
                severity=IssueSeverity.MAJOR,
                message=f"LC clause 46A requires B/L to show {info['display']}, but this field was not found.",
                expected=f"{info['display']} as required by LC clause 46A",
                found=found_text,
                suggestion=suggestion,
                documents=["Bill of Lading"],
                ucp_reference="UCP600 Article 14(d)",
                isbp_reference="ISBP745 E12",
            ))
            logger.info(f"✗ B/L missing: {info['display']}")
    
    return issues


# =============================================================================
# PACKING LIST VALIDATOR
# =============================================================================

def validate_packing_list(
    lc_text: str,
    packing_list_data: Dict[str, Any],
) -> List[AIValidationIssue]:
    """
    Validate packing list against LC requirements.
    Specifically checks for size breakdown if LC requires it.
    """
    issues = []
    
    if not lc_text:
        return issues
    
    text_upper = lc_text.upper()
    
    # Check if LC requires size breakdown in packing list
    requires_sizes = False
    if "PACKING" in text_upper and "SIZE" in text_upper:
        requires_sizes = True
    # Also check for explicit "SIZE BREAKDOWN" or "SIZES" requirement
    if "SIZE BREAKDOWN" in text_upper or "SIZE-BREAKDOWN" in text_upper:
        requires_sizes = True
    if re.search(r'PACKING\s+LIST.*SIZE', text_upper):
        requires_sizes = True
    
    if not requires_sizes:
        logger.info("LC does not require size breakdown in packing list")
        return issues
    
    logger.info("LC requires size breakdown in packing list - checking...")
    
    # Check if packing list has size information
    has_sizes = False
    
    # Check raw text
    pl_raw = (packing_list_data.get("raw_text") or "").upper()
    size_indicators = ["SIZE", "S/M/L", "SMALL", "MEDIUM", "LARGE", "XL", "XXL", 
                       "SIZE BREAKDOWN", "SIZE DISTRIBUTION", "SIZES PER CARTON"]
    
    for indicator in size_indicators:
        if indicator in pl_raw:
            has_sizes = True
            logger.info(f"✓ Packing list has size info: found '{indicator}'")
            break
    
    # Also check extracted fields
    if not has_sizes:
        for key, value in packing_list_data.items():
            if key.startswith("_"):
                continue
            key_lower = key.lower()
            value_str = str(value).upper() if value else ""
            
            if "size" in key_lower or any(ind in value_str for ind in size_indicators):
                has_sizes = True
                logger.info(f"✓ Packing list has size field: {key}")
                break
    
    if not has_sizes:
        issues.append(AIValidationIssue(
            rule_id="AI-PL-MISSING-SIZES",
            title="Packing List Missing Size Breakdown",
            severity=IssueSeverity.MAJOR,
            message="LC clause 46A requires packing list to show size breakdown, but no size information was found.",
            expected="Detailed size breakdown (S/M/L/XL distribution per carton) as required by LC",
            found="No size breakdown found in packing list",
            suggestion="Update packing list to include a size-wise breakdown showing quantity per size per carton. Example: 'Carton 1-100: S-500pcs, M-800pcs, L-600pcs, XL-300pcs'. This is a common LC requirement for garment shipments.",
            documents=["Packing List"],
            ucp_reference="UCP600 Article 14(d)",
            isbp_reference="ISBP745 L3",
        ))
        logger.info("✗ Packing list missing required size breakdown")
    
    return issues


def _router_confidence(output_text: str, tokens_out: int) -> float:
    text = (output_text or "").strip()
    if not text:
        return 0.0
    base = 0.55
    if "verdict" in text.lower():
        base += 0.2
    if "reason" in text.lower():
        base += 0.15
    if tokens_out > 30:
        base += 0.1
    return min(base, 0.98)


def _extract_json_block(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


# =============================================================================
# MAIN AI VALIDATION ORCHESTRATOR
# =============================================================================

async def run_ai_validation(
    lc_data: Dict[str, Any],
    documents: List[Dict[str, Any]],
    extracted_context: Dict[str, Any],
) -> Tuple[List[AIValidationIssue], Dict[str, Any]]:
    """
    Run FOCUSED AI-powered validation.
    
    Only checks:
    1. Missing critical documents (Inspection Cert, Beneficiary Cert)
    2. B/L field requirements (Voyage No, Gross Weight, Net Weight)
    
    NOTE: Goods matching is handled by crossdoc_validator - skipped here.
    """
    all_issues: List[AIValidationIssue] = []
    metadata = {
        "ai_validation_run": True,
        "checks_performed": [],
    }
    
    # Get LC raw text
    lc_text = lc_data.get("raw_text") or ""
    logger.info(f"AI Validation starting with {len(lc_text)} chars of LC text")
    
    if not lc_text:
        # Fallback: synthesize a context text from uploaded documents so layered AI
        # arbitration still runs and emits trace evidence.
        doc_snippets = []
        for doc in documents or []:
            if not isinstance(doc, dict):
                continue
            snippet = str(doc.get("raw_text") or doc.get("raw_text_preview") or "").strip()
            if snippet:
                doc_snippets.append(snippet[:1200])
        if doc_snippets:
            lc_text = "\n\n".join(doc_snippets)
            lc_data["raw_text"] = lc_text
            metadata["lc_text_fallback"] = "documents"
            logger.warning("LC raw_text missing; using document text fallback for AI validation")
        else:
            logger.warning("No LC text available for AI validation")
            metadata["error"] = "no_lc_text"
            # Continue with minimal context so router layers still emit telemetry.
            lc_text = "LC text unavailable; run conservative validation on available signals."
    
    # =================================================================
    # 1. PARSE LC REQUIREMENTS
    # =================================================================
    logger.info("Step 1: Parsing LC requirements...")
    metadata["checks_performed"].append("lc_requirement_parsing")
    
    requirements = parse_lc_requirements_sync(lc_text)
    required_docs = requirements.get("required_documents", [])
    bl_must_show = requirements.get("bl_must_show", [])
    
    metadata["required_critical_docs"] = [d["document_type"] for d in required_docs]
    metadata["bl_must_show"] = bl_must_show
    
    # =================================================================
    # 2. CHECK DOCUMENT COMPLETENESS (Critical docs only)
    # =================================================================
    if required_docs:
        logger.info(f"Step 2: Checking {len(required_docs)} critical document requirements...")
        metadata["checks_performed"].append("document_completeness")
        
        completeness_issues = check_document_completeness(required_docs, documents)
        all_issues.extend(completeness_issues)
        
        metadata["missing_critical_docs"] = len(completeness_issues)
    else:
        logger.info("Step 2: No critical documents to check (Inspection/Beneficiary Cert not required)")
        metadata["missing_critical_docs"] = 0
    
    # =================================================================
    # 3. VALIDATE B/L FIELDS
    # =================================================================
    if bl_must_show:
        logger.info(f"Step 3: Validating B/L has required fields: {bl_must_show}")
        metadata["checks_performed"].append("bl_field_validation")
        
        # Get B/L extracted data
        bl_data = extracted_context.get("bill_of_lading") or {}
        
        bl_issues = validate_bl_fields(bl_must_show, bl_data)
        all_issues.extend(bl_issues)
        
        metadata["bl_missing_fields"] = len(bl_issues)
    else:
        logger.info("Step 3: No specific B/L field requirements detected")
        metadata["bl_missing_fields"] = 0
    
    # =================================================================
    # 4. VALIDATE PACKING LIST (Size breakdown)
    # =================================================================
    packing_list_data = extracted_context.get("packing_list") or {}
    if packing_list_data:
        logger.info("Step 4: Validating packing list requirements...")
        metadata["checks_performed"].append("packing_list_validation")
        
        pl_issues = validate_packing_list(lc_text, packing_list_data)
        all_issues.extend(pl_issues)
        
        metadata["packing_list_issues"] = len(pl_issues)
    else:
        logger.info("Step 4: No packing list data to validate")
        metadata["packing_list_issues"] = 0
    
    # =================================================================
    # 5. DEDUPLICATE ISSUES
    # =================================================================
    seen_rules: Set[str] = set()
    unique_issues: List[AIValidationIssue] = []
    
    for issue in all_issues:
        if issue.rule_id not in seen_rules:
            seen_rules.add(issue.rule_id)
            unique_issues.append(issue)
        else:
            logger.info(f"Removing duplicate issue: {issue.rule_id}")
    
    # =================================================================
    # 6. LLM LAYERED ARBITRATION (L1/L2/L3 via router transport)
    # =================================================================
    metadata["llm_layers_attempted"] = []
    metadata["llm_layers_succeeded"] = []

    try:
        metadata["checks_performed"].append("llm_layered_arbitration")
        router = ModelRouter()
        docs_summary = ", ".join(sorted({(d.get("document_type") or d.get("type") or "unknown") for d in documents if isinstance(d, dict)}))
        issues_summary = ", ".join(sorted({i.rule_id for i in unique_issues})) or "none"

        l1_prompt = (
            "Return strict JSON only. Assess this LC package for bank submission. "
            "Fields: verdict(pass|review|reject), confidence_score(0-1), risk_score(0-100), "
            "applied_rules(list), blocking_rules(list), reasoning_summary(string).\n"
            f"LC excerpt: {lc_text[:2500]}\nUploaded document types: {docs_summary or 'none'}"
        )
        l2_prompt = (
            "Return strict JSON only. Cross-check document adequacy and discrepancy severity. "
            "Fields: verdict, confidence_score, risk_score, applied_rules, blocking_rules, reasoning_summary.\n"
            f"Known validator issues: {issues_summary}\nB/L requirements: {bl_must_show}"
        )
        l3_prompt = (
            "Return strict JSON only. Final arbitration for submission decision with conservative banking posture. "
            "Fields: verdict, confidence_score, risk_score, applied_rules, blocking_rules, reasoning_summary.\n"
            f"Detected issues: {issues_summary}\nMissing critical docs: {metadata.get('missing_critical_docs', 0)}"
        )

        llm_payloads: Dict[str, Dict[str, Any]] = {}
        for layer, prompt in (("L1", l1_prompt), ("L2", l2_prompt), ("L3", l3_prompt)):
            metadata["llm_layers_attempted"].append(layer)
            routed = await router.call_layer(
                layer=layer,
                prompt=prompt,
                system_prompt="You are a trade-compliance validation model. Output JSON only.",
                max_tokens=220,
                temperature=0.1,
                confidence_fn=_router_confidence,
                primary_provider="openai" if settings.OPENROUTER_API_KEY else settings.LLM_PROVIDER,
            )
            payload = _extract_json_block(routed.output_text)
            if not isinstance(payload, dict):
                payload = {}
            payload["verdict"] = _coerce_str(payload.get("verdict"))
            payload["confidence_score"] = _coerce_float(payload.get("confidence_score"))
            payload["risk_score"] = _coerce_float(payload.get("risk_score"))
            payload["applied_rules"] = _coerce_list(payload.get("applied_rules"))
            payload["blocking_rules"] = _coerce_list(payload.get("blocking_rules"))
            payload["reasoning_summary"] = _coerce_str(payload.get("reasoning_summary"))
            payload["provider_used"] = routed.provider_used
            payload["model_used"] = routed.model_used
            payload["fallback_used"] = routed.fallback_used
            payload["confidence_band"] = routed.confidence_band
            llm_payloads[layer] = payload
            metadata["llm_layers_succeeded"].append(layer)

        final = llm_payloads.get("L3") or llm_payloads.get("L2") or llm_payloads.get("L1") or {}
        metadata["llm_layer_payloads"] = llm_payloads
        metadata["llm_verdict"] = str(final.get("verdict") or "").strip().lower() or None
        metadata["confidence_score"] = final.get("confidence_score")
        metadata["risk_score"] = final.get("risk_score")
        metadata["applied_rules"] = final.get("applied_rules") if isinstance(final.get("applied_rules"), list) else []
        metadata["blocking_rules_llm"] = final.get("blocking_rules") if isinstance(final.get("blocking_rules"), list) else []
        metadata["reasoning_summary"] = final.get("reasoning_summary")
    except Exception as exc:  # noqa: BLE001
        metadata["llm_layer_error"] = str(exc)
        logger.warning("LLM layered arbitration failed: %s", exc)

    # =================================================================
    # 7. SUMMARY
    # =================================================================
    metadata["total_issues"] = len(unique_issues)
    metadata["critical_issues"] = sum(1 for i in unique_issues if i.severity == IssueSeverity.CRITICAL)
    metadata["major_issues"] = sum(1 for i in unique_issues if i.severity == IssueSeverity.MAJOR)

    logger.info(
        f"AI Validation complete: {len(unique_issues)} issues "
        f"(critical={metadata['critical_issues']}, major={metadata['major_issues']})"
    )

    return unique_issues, metadata
