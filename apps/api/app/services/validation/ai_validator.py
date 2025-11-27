"""
AI-Powered LC Validation Engine

This module provides comprehensive AI-driven validation for LC document sets:
1. LC Requirement Parser - Extracts required documents from 46A/47A
2. Document Completeness Checker - Verifies all required docs are uploaded
3. Semantic Goods Matching - AI understands meaning, not just strings
4. Field Requirement Validator - Checks documents have required fields
5. AI Discrepancy Explainer - Professional, bank-grade explanations
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


@dataclass
class RequiredDocument:
    """A document required by the LC."""
    doc_type: str
    display_name: str
    issuer: Optional[str] = None
    copies: int = 1
    must_show: List[str] = field(default_factory=list)
    must_state: Optional[str] = None
    lc_clause: str = "46A"


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

LC_REQUIREMENT_PROMPT = """You are an expert trade finance document analyst. 
Parse this Letter of Credit and extract the REQUIRED DOCUMENTS from clause 46A.

For each required document, identify:
- document_type: One of [commercial_invoice, bill_of_lading, packing_list, certificate_of_origin, inspection_certificate, insurance_certificate, beneficiary_certificate, draft, weight_certificate, other]
- display_name: Human readable name
- issuer: Who must issue it (if specified)
- copies: Number of copies required
- must_show: List of fields/information it must contain
- must_state: Specific statement it must include

LC TEXT:
{lc_text}

Return ONLY valid JSON in this format:
{
  "required_documents": [
    {
      "document_type": "commercial_invoice",
      "display_name": "Commercial Invoice",
      "issuer": null,
      "copies": 6,
      "must_show": ["HS code", "qty", "unit price", "total"],
      "must_state": null
    }
  ],
  "special_conditions": ["list of special conditions from 47A"],
  "prohibited": ["list of prohibited items"]
}"""


async def parse_lc_requirements(lc_text: str) -> Dict[str, Any]:
    """
    Use AI to parse LC requirements from 46A/47A clauses.
    
    Returns structured requirements that can be validated against.
    """
    if not lc_text or len(lc_text.strip()) < 100:
        logger.warning("LC text too short for requirement parsing")
        return {"required_documents": [], "special_conditions": [], "prohibited": []}
    
    try:
        from ..llm_provider import LLMProviderFactory
        
        prompt = LC_REQUIREMENT_PROMPT.format(lc_text=lc_text[:8000])
        
        response, tokens_in, tokens_out = await LLMProviderFactory.create_provider().generate(
            prompt=prompt,
            system_prompt="You are an expert LC document analyst. Return only valid JSON.",
            temperature=0.1,
            max_tokens=2000,
        )
        
        logger.info(f"LC requirement parsing: tokens_in={tokens_in}, tokens_out={tokens_out}")
        
        # Parse JSON response
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        if clean.endswith("```"):
            clean = clean[:-3]
        
        result = json.loads(clean.strip())
        
        logger.info(f"Parsed {len(result.get('required_documents', []))} required documents from LC")
        return result
        
    except Exception as e:
        logger.error(f"LC requirement parsing failed: {e}", exc_info=True)
        # Return default requirements based on common LC patterns
        return _get_default_requirements(lc_text)


def _get_default_requirements(lc_text: str) -> Dict[str, Any]:
    """Fallback: extract requirements using regex patterns."""
    docs = []
    text_upper = lc_text.upper()
    
    # Always required
    docs.append({
        "document_type": "commercial_invoice",
        "display_name": "Commercial Invoice",
        "copies": 6 if "6 COPIES" in text_upper else 3,
    })
    docs.append({
        "document_type": "bill_of_lading", 
        "display_name": "Bill of Lading",
        "must_show": ["vessel name", "voyage no"] if "VOYAGE" in text_upper else [],
    })
    
    # Conditional
    if "PACKING LIST" in text_upper:
        docs.append({"document_type": "packing_list", "display_name": "Packing List"})
    if "CERTIFICATE OF ORIGIN" in text_upper or "C/O" in text_upper:
        docs.append({"document_type": "certificate_of_origin", "display_name": "Certificate of Origin"})
    if "INSPECTION" in text_upper and "CERTIFICATE" in text_upper:
        issuer = None
        if "SGS" in text_upper:
            issuer = "SGS"
        elif "INTERTEK" in text_upper:
            issuer = "Intertek"
        docs.append({
            "document_type": "inspection_certificate",
            "display_name": "Inspection Certificate",
            "issuer": issuer,
        })
    if "BENEFICIARY CERTIFICATE" in text_upper or "BENEFICIARY'S CERTIFICATE" in text_upper:
        docs.append({
            "document_type": "beneficiary_certificate",
            "display_name": "Beneficiary Certificate",
        })
    if "INSURANCE" in text_upper and "CERTIFICATE" in text_upper:
        docs.append({"document_type": "insurance_certificate", "display_name": "Insurance Certificate"})
    
    return {"required_documents": docs, "special_conditions": [], "prohibited": []}


# =============================================================================
# DOCUMENT COMPLETENESS CHECKER
# =============================================================================

def check_document_completeness(
    required_docs: List[Dict[str, Any]],
    uploaded_docs: List[Dict[str, Any]],
) -> List[AIValidationIssue]:
    """
    Check if all required documents are present in the uploaded set.
    
    Args:
        required_docs: List of required documents from LC parsing
        uploaded_docs: List of uploaded document metadata
        
    Returns:
        List of issues for missing documents
    """
    issues = []
    
    # Normalize uploaded document types
    uploaded_types = set()
    for doc in uploaded_docs:
        doc_type = (doc.get("document_type") or doc.get("type") or "").lower()
        doc_type = _normalize_doc_type(doc_type)
        uploaded_types.add(doc_type)
        
        # Also check filename for hints
        filename = (doc.get("filename") or doc.get("name") or "").lower()
        if "invoice" in filename:
            uploaded_types.add("commercial_invoice")
        if "lading" in filename or "b/l" in filename or "bl" in filename:
            uploaded_types.add("bill_of_lading")
        if "packing" in filename:
            uploaded_types.add("packing_list")
        if "origin" in filename or "coo" in filename:
            uploaded_types.add("certificate_of_origin")
        if "inspection" in filename:
            uploaded_types.add("inspection_certificate")
        if "insurance" in filename:
            uploaded_types.add("insurance_certificate")
        if "beneficiary" in filename:
            uploaded_types.add("beneficiary_certificate")
    
    logger.info(f"Uploaded document types detected: {uploaded_types}")
    
    # Check each required document
    for req in required_docs:
        req_type = _normalize_doc_type(req.get("document_type", ""))
        display_name = req.get("display_name", req_type)
        
        if req_type not in uploaded_types:
            # Determine severity based on document type
            if req_type in ["inspection_certificate", "beneficiary_certificate"]:
                severity = IssueSeverity.CRITICAL
            elif req_type in ["bill_of_lading", "commercial_invoice"]:
                severity = IssueSeverity.CRITICAL
            else:
                severity = IssueSeverity.MAJOR
            
            issuer_note = ""
            if req.get("issuer"):
                issuer_note = f" (issued by {req['issuer']})"
            
            issues.append(AIValidationIssue(
                rule_id=f"AI-DOC-MISSING-{req_type.upper()}",
                title=f"Missing Required Document: {display_name}",
                severity=severity,
                message=f"The LC requires a {display_name}{issuer_note} but this document was not uploaded.",
                expected=f"{display_name} as specified in LC clause 46A",
                found="Document not found in uploaded set",
                suggestion=f"Upload the required {display_name} before bank submission. Without this document, the presentation will be discrepant.",
                documents=["Letter of Credit"],
                ucp_reference="UCP600 Article 14(a)",
            ))
    
    return issues


def _normalize_doc_type(doc_type: str) -> str:
    """Normalize document type to standard form."""
    doc_type = doc_type.lower().strip()
    
    mappings = {
        "invoice": "commercial_invoice",
        "commercial invoice": "commercial_invoice",
        "comm_invoice": "commercial_invoice",
        "bl": "bill_of_lading",
        "b/l": "bill_of_lading",
        "bill of lading": "bill_of_lading",
        "bol": "bill_of_lading",
        "packing list": "packing_list",
        "packinglist": "packing_list",
        "coo": "certificate_of_origin",
        "c/o": "certificate_of_origin",
        "certificate of origin": "certificate_of_origin",
        "origin": "certificate_of_origin",
        "inspection": "inspection_certificate",
        "inspection cert": "inspection_certificate",
        "insurance": "insurance_certificate",
        "insurance cert": "insurance_certificate",
        "beneficiary cert": "beneficiary_certificate",
        "beneficiary certificate": "beneficiary_certificate",
    }
    
    return mappings.get(doc_type, doc_type.replace(" ", "_"))


# =============================================================================
# SEMANTIC GOODS MATCHING
# =============================================================================

SEMANTIC_MATCH_PROMPT = """You are an expert trade finance analyst comparing goods descriptions.

Compare these two goods descriptions and determine if they refer to the SAME goods:

LC GOODS DESCRIPTION:
{lc_goods}

DOCUMENT GOODS DESCRIPTION:
{doc_goods}

Consider:
1. Are these fundamentally the same products?
2. Do quantities match (if specified)?
3. Do HS codes match (if specified)?
4. Are there any CONFLICTING details?

Per UCP600 Article 18(c), invoices may use general terms but must NOT CONFLICT with LC.

Return ONLY valid JSON:
{
  "match": true/false,
  "confidence": 0.0-1.0,
  "explanation": "Brief explanation",
  "conflicts": ["list of specific conflicts if any"],
  "acceptable_differences": ["differences that are acceptable under UCP600"]
}"""


async def semantic_goods_match(
    lc_goods: str,
    doc_goods: str,
    doc_type: str = "invoice",
) -> Dict[str, Any]:
    """
    Use AI to semantically compare goods descriptions.
    
    This understands that "100% Cotton T-Shirts" = "100% COTTON T-SHIRTS"
    but "Cotton T-shirts" ≠ "100% Polyester T-shirts"
    """
    if not lc_goods or not doc_goods:
        return {"match": True, "confidence": 0.5, "explanation": "Insufficient data for comparison"}
    
    # Quick check for obvious matches (case-insensitive, normalized)
    lc_norm = _normalize_goods_text(lc_goods)
    doc_norm = _normalize_goods_text(doc_goods)
    
    if lc_norm == doc_norm:
        return {"match": True, "confidence": 1.0, "explanation": "Exact match after normalization"}
    
    # Check if one contains the other (general terms acceptable)
    if doc_norm in lc_norm or lc_norm in doc_norm:
        return {
            "match": True, 
            "confidence": 0.9, 
            "explanation": "Document uses general terms consistent with LC",
            "acceptable_differences": ["General description acceptable per UCP600 Art 18(c)"]
        }
    
    try:
        from ..llm_provider import LLMProviderFactory
        
        prompt = SEMANTIC_MATCH_PROMPT.format(
            lc_goods=lc_goods[:2000],
            doc_goods=doc_goods[:2000],
        )
        
        response, _, _ = await LLMProviderFactory.create_provider().generate(
            prompt=prompt,
            system_prompt="You are an expert trade finance analyst. Return only valid JSON.",
            temperature=0.1,
            max_tokens=500,
        )
        
        # Parse response
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        if clean.endswith("```"):
            clean = clean[:-3]
        
        return json.loads(clean.strip())
        
    except Exception as e:
        logger.warning(f"Semantic goods matching failed: {e}")
        # Fallback to simple similarity
        similarity = _simple_similarity(lc_norm, doc_norm)
        return {
            "match": similarity > 0.7,
            "confidence": similarity,
            "explanation": f"Fallback similarity check: {similarity:.0%}",
        }


def _normalize_goods_text(text: str) -> str:
    """Normalize goods text for comparison."""
    text = text.lower()
    # Remove punctuation and extra whitespace
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    # Remove common filler words
    for word in ['the', 'a', 'an', 'of', 'for', 'and', 'or']:
        text = re.sub(rf'\b{word}\b', '', text)
    return text.strip()


def _simple_similarity(text1: str, text2: str) -> float:
    """Simple word overlap similarity."""
    words1 = set(text1.split())
    words2 = set(text2.split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)


# =============================================================================
# FIELD REQUIREMENT VALIDATOR
# =============================================================================

FIELD_VALIDATION_PROMPT = """You are an expert trade finance document analyst.

The LC requires the {doc_type} to show these specific fields/information:
{required_fields}

Here is the extracted data from the actual {doc_type}:
{doc_data}

Check if each required field is present and correctly shown.

Return ONLY valid JSON:
{
  "missing_fields": ["list of fields required but not found"],
  "present_fields": ["list of required fields that are present"],
  "issues": [
    {
      "field": "field name",
      "expected": "what LC requires",
      "found": "what document shows or 'NOT FOUND'",
      "severity": "critical/major/minor"
    }
  ]
}"""


async def validate_document_fields(
    doc_type: str,
    required_fields: List[str],
    doc_data: Dict[str, Any],
) -> List[AIValidationIssue]:
    """
    Validate that a document contains all required fields.
    
    Uses AI to understand field requirements and check against extracted data.
    """
    if not required_fields:
        return []
    
    issues = []
    
    # First, do quick deterministic checks
    doc_data_lower = {k.lower(): v for k, v in doc_data.items() if v}
    
    field_mappings = {
        "voyage no": ["voyage_number", "voyage", "voyage_no", "voy"],
        "voyage number": ["voyage_number", "voyage", "voyage_no", "voy"],
        "gross weight": ["gross_weight", "gw", "gross_wt"],
        "net weight": ["net_weight", "nw", "net_wt"],
        "vessel name": ["vessel", "vessel_name", "ship", "carrier"],
        "container no": ["container_number", "container_no", "container"],
        "seal no": ["seal_number", "seal_no", "seal"],
        "hs code": ["hs_code", "hscode", "hs_codes", "tariff"],
        "qty": ["quantity", "qty", "quantities"],
        "unit price": ["unit_price", "price", "rate"],
    }
    
    for req_field in required_fields:
        req_lower = req_field.lower()
        possible_keys = field_mappings.get(req_lower, [req_lower, req_lower.replace(" ", "_")])
        
        found = False
        for key in possible_keys:
            if key in doc_data_lower and doc_data_lower[key]:
                found = True
                break
        
        if not found:
            severity = IssueSeverity.MAJOR
            if req_lower in ["voyage no", "voyage number", "gross weight", "net weight"]:
                severity = IssueSeverity.MAJOR
            
            issues.append(AIValidationIssue(
                rule_id=f"AI-FIELD-MISSING-{req_field.upper().replace(' ', '_')}",
                title=f"{doc_type} Missing Required Field: {req_field}",
                severity=severity,
                message=f"The LC requires the {doc_type} to show '{req_field}' but this field was not found.",
                expected=f"{req_field} as required by LC clause 46A",
                found="Field not found in document",
                suggestion=f"Ensure the {doc_type} clearly shows the {req_field}. Request amended document if necessary.",
                documents=[doc_type],
                ucp_reference="UCP600 Article 14(d)",
            ))
    
    return issues


# =============================================================================
# AI DISCREPANCY EXPLAINER
# =============================================================================

EXPLANATION_PROMPT = """You are an expert trade finance specialist explaining a document discrepancy to an exporter.

DISCREPANCY:
Title: {title}
Expected: {expected}
Found: {found}

Provide a professional, bank-grade explanation that:
1. Explains why this is a discrepancy under UCP600/ISBP745
2. What the bank will likely do
3. Specific actionable steps to resolve it
4. Any alternative solutions (amendment, waiver request)

Keep it concise but comprehensive (2-3 sentences for explanation, 2-3 bullet points for actions).

Return ONLY valid JSON:
{
  "explanation": "Professional explanation of the discrepancy",
  "bank_action": "What the bank will likely do",
  "resolution_steps": ["step 1", "step 2"],
  "alternative": "Alternative solution if primary fix not possible",
  "risk_level": "high/medium/low"
}"""


async def generate_discrepancy_explanation(
    title: str,
    expected: str,
    found: str,
    ucp_reference: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a professional, bank-grade explanation for a discrepancy.
    """
    try:
        from ..llm_provider import LLMProviderFactory
        
        prompt = EXPLANATION_PROMPT.format(
            title=title,
            expected=expected,
            found=found,
        )
        
        response, _, _ = await LLMProviderFactory.create_provider().generate(
            prompt=prompt,
            system_prompt="You are an expert trade finance specialist. Return only valid JSON.",
            temperature=0.2,
            max_tokens=600,
        )
        
        # Parse response
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        if clean.endswith("```"):
            clean = clean[:-3]
        
        return json.loads(clean.strip())
        
    except Exception as e:
        logger.warning(f"Discrepancy explanation generation failed: {e}")
        return {
            "explanation": f"This discrepancy may cause bank rejection. Review and correct before submission.",
            "bank_action": "Bank will issue discrepancy notice",
            "resolution_steps": ["Review the specific requirement", "Correct or request amendment"],
            "risk_level": "medium",
        }


# =============================================================================
# MAIN AI VALIDATION ORCHESTRATOR
# =============================================================================

async def run_ai_validation(
    lc_data: Dict[str, Any],
    documents: List[Dict[str, Any]],
    extracted_context: Dict[str, Any],
) -> Tuple[List[AIValidationIssue], Dict[str, Any]]:
    """
    Run comprehensive AI-powered validation on the document set.
    
    Args:
        lc_data: Extracted LC data including raw text
        documents: List of uploaded document metadata
        extracted_context: Extracted data from all documents
        
    Returns:
        Tuple of (list of issues, validation metadata)
    """
    all_issues: List[AIValidationIssue] = []
    metadata = {
        "ai_validation_run": True,
        "checks_performed": [],
    }
    
    # Get LC raw text for parsing
    lc_text = lc_data.get("raw_text") or ""
    if not lc_text:
        # Try to reconstruct from structured data
        mt700 = lc_data.get("mt700") or {}
        if mt700.get("raw_text"):
            lc_text = mt700["raw_text"]
    
    # 1. Parse LC Requirements
    logger.info("AI Validation: Parsing LC requirements...")
    metadata["checks_performed"].append("lc_requirement_parsing")
    
    lc_requirements = await parse_lc_requirements(lc_text)
    required_docs = lc_requirements.get("required_documents", [])
    metadata["required_documents"] = [d.get("display_name") for d in required_docs]
    
    # 2. Check Document Completeness
    logger.info("AI Validation: Checking document completeness...")
    metadata["checks_performed"].append("document_completeness")
    
    completeness_issues = check_document_completeness(required_docs, documents)
    all_issues.extend(completeness_issues)
    metadata["missing_documents"] = len(completeness_issues)
    
    # 3. Semantic Goods Matching
    logger.info("AI Validation: Running semantic goods matching...")
    metadata["checks_performed"].append("semantic_goods_matching")
    
    lc_goods = lc_data.get("goods_description") or ""
    if not lc_goods and lc_data.get("goods"):
        if isinstance(lc_data["goods"], list):
            lc_goods = " ".join(str(g) for g in lc_data["goods"])
        else:
            lc_goods = str(lc_data["goods"])
    
    # Check invoice goods
    invoice_ctx = extracted_context.get("invoice") or {}
    invoice_goods = invoice_ctx.get("goods_description") or invoice_ctx.get("description") or ""
    
    if lc_goods and invoice_goods:
        goods_match = await semantic_goods_match(lc_goods, invoice_goods, "invoice")
        metadata["invoice_goods_match"] = goods_match
        
        if not goods_match.get("match", True):
            conflicts = goods_match.get("conflicts", [])
            all_issues.append(AIValidationIssue(
                rule_id="AI-GOODS-MISMATCH-INV",
                title="Invoice Goods Description Conflict",
                severity=IssueSeverity.MAJOR,
                message=goods_match.get("explanation", "Invoice goods may conflict with LC terms."),
                expected=f"Goods per LC: {lc_goods[:200]}...",
                found=f"Invoice states: {invoice_goods[:200]}...",
                suggestion=f"Review goods description. Conflicts: {', '.join(conflicts) if conflicts else 'See explanation'}. Per UCP600 Article 18(c), invoice may use general terms but must not conflict.",
                documents=["Commercial Invoice", "Letter of Credit"],
                ucp_reference="UCP600 Article 18(c)",
                isbp_reference="ISBP745 C6",
            ))
    
    # 4. Field Requirement Validation
    logger.info("AI Validation: Validating required fields...")
    metadata["checks_performed"].append("field_requirement_validation")
    
    # Check B/L required fields
    bl_requirements = next(
        (d for d in required_docs if d.get("document_type") == "bill_of_lading"),
        {}
    )
    bl_must_show = bl_requirements.get("must_show", [])
    
    # Add common B/L requirements if not specified
    if not bl_must_show and "VOYAGE" in lc_text.upper():
        bl_must_show = ["voyage no", "gross weight", "net weight"]
    
    if bl_must_show:
        bl_ctx = extracted_context.get("bill_of_lading") or {}
        bl_field_issues = await validate_document_fields(
            "Bill of Lading",
            bl_must_show,
            bl_ctx,
        )
        all_issues.extend(bl_field_issues)
    
    # 5. Generate enhanced explanations for all issues
    logger.info("AI Validation: Generating explanations...")
    metadata["checks_performed"].append("explanation_generation")
    
    # For the first few issues, generate detailed explanations
    for issue in all_issues[:5]:  # Limit to avoid too many API calls
        try:
            explanation = await generate_discrepancy_explanation(
                issue.title,
                issue.expected,
                issue.found,
                issue.ucp_reference,
            )
            # Enhance the suggestion with AI-generated content
            if explanation.get("resolution_steps"):
                steps = " → ".join(explanation["resolution_steps"])
                issue.suggestion = f"{issue.suggestion} STEPS: {steps}"
        except Exception as e:
            logger.warning(f"Could not enhance explanation for {issue.rule_id}: {e}")
    
    metadata["total_ai_issues"] = len(all_issues)
    metadata["critical_issues"] = sum(1 for i in all_issues if i.severity == IssueSeverity.CRITICAL)
    metadata["major_issues"] = sum(1 for i in all_issues if i.severity == IssueSeverity.MAJOR)
    
    logger.info(
        f"AI Validation complete: {len(all_issues)} issues found "
        f"(critical={metadata['critical_issues']}, major={metadata['major_issues']})"
    )
    
    return all_issues, metadata

