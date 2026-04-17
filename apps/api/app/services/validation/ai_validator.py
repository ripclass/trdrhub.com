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

from app.services.validation.alias_normalization import (
    BL_RAW_PATTERNS,
    canonicalize_fields,
    extract_bl_required_field_candidates,
    find_first_pattern_value,
    text_has_size_breakdown,
)

logger = logging.getLogger(__name__)


_GRAPH_CRITICAL_DOC_TYPES = {
    "inspection_certificate": ("Inspection Certificate", "issuer"),
    "beneficiary_certificate": ("Beneficiary Certificate", "must_state"),
}

_L3_REVIEWABLE_DOCUMENT_TYPES = {
    "lc",
    "invoice",
    "bill_of_lading",
    "packing_list",
    "certificate_of_origin",
    "insurance",
    "inspection_certificate",
    "beneficiary_certificate",
}
_L3_DOCUMENT_TYPE_ALIASES = {
    "air_waybill": "bill_of_lading",
    "bill_of_lading": "bill_of_lading",
    "bl": "bill_of_lading",
    "certificate_of_origin": "certificate_of_origin",
    "coo": "certificate_of_origin",
    "commercial_invoice": "invoice",
    "insurance": "insurance",
    "insurance_certificate": "insurance",
    "insurance_policy": "insurance",
    "invoice": "invoice",
    "lc": "lc",
    "letter_of_credit": "lc",
    "packing_list": "packing_list",
}
_L3_DOCUMENT_LABELS = {
    "beneficiary_certificate": "Beneficiary Certificate",
    "bill_of_lading": "Bill of Lading",
    "certificate_of_origin": "Certificate of Origin",
    "inspection_certificate": "Inspection Certificate",
    "insurance": "Insurance Document",
    "invoice": "Commercial Invoice",
    "lc": "Letter of Credit",
    "packing_list": "Packing List",
}
_L3_WARNING_STATUSES = {
    "warning",
    "warn",
    "partial",
    "error",
    "failed",
    "fail",
    "parse_failed",
    "text_only",
}
_L3_MAJOR_REVIEWABLE_DOCUMENT_TYPES = {
    "lc",
    "invoice",
    "bill_of_lading",
    "insurance",
}
_L3_MAJOR_WARNING_STATUSES = {
    "error",
    "failed",
    "fail",
    "parse_failed",
}
_L3_LOW_CONFIDENCE_THRESHOLD = 0.35
_L3_SEVERE_CONFIDENCE_THRESHOLD = 0.2
_L3_DEGRADED_SELECTION_STAGES = {
    "binary_metadata_scrape",
}
_L3_EXTRACTION_FAILURE_REASON_CODES = {
    "OCR_AUTH_ERROR",
    "OCR_AUTH_FAILURE",
    "OCR_EMPTY_RESULT",
    "OCR_PROVIDER_UNAVAILABLE",
    "PARSER_EMPTY_OUTPUT",
    "PARSE_FAILED",
    "LOW_CONFIDENCE",
    "LOW_CONFIDENCE_CRITICAL",
}


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


def _normalize_document_type(value: Any) -> str:
    normalized = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return _L3_DOCUMENT_TYPE_ALIASES.get(normalized, normalized)


def _normalize_confidence_value(value: Any) -> Optional[float]:
    if value in (None, "", []):
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if confidence > 1.0 and confidence <= 100.0:
        confidence = confidence / 100.0
    if confidence < 0.0:
        confidence = 0.0
    if confidence > 1.0:
        confidence = 1.0
    return confidence


def _snapshot_display_name(doc_type: str) -> str:
    return _L3_DOCUMENT_LABELS.get(doc_type, doc_type.replace("_", " ").title())


def _classify_l3_confidence_severity(
    snapshot: Dict[str, Any],
) -> Optional[IssueSeverity]:
    doc_type = str(snapshot.get("document_type") or "").strip().lower()
    confidence = snapshot.get("confidence")
    status = str(snapshot.get("status") or "").strip().lower()
    review_required = bool(snapshot.get("review_required"))
    reason_codes = {
        str(item or "").strip().upper()
        for item in (snapshot.get("reason_codes") or [])
        if str(item or "").strip()
    }
    selected_stage = str(snapshot.get("selected_stage") or "").strip().lower()

    if confidence is None:
        severe_signal = bool(reason_codes.intersection(_L3_EXTRACTION_FAILURE_REASON_CODES))
        if not review_required and not severe_signal and selected_stage not in _L3_DEGRADED_SELECTION_STAGES:
            return None
        if doc_type in _L3_MAJOR_REVIEWABLE_DOCUMENT_TYPES and (
            severe_signal or selected_stage in _L3_DEGRADED_SELECTION_STAGES
        ):
            return IssueSeverity.MAJOR
        return IssueSeverity.MINOR if review_required or severe_signal else None

    normalized_status = str(status or "").strip().lower()
    is_suspicious = confidence < _L3_LOW_CONFIDENCE_THRESHOLD and (
        normalized_status in _L3_WARNING_STATUSES or confidence < _L3_SEVERE_CONFIDENCE_THRESHOLD
    )
    if not is_suspicious and review_required and reason_codes.intersection(_L3_EXTRACTION_FAILURE_REASON_CODES):
        is_suspicious = True
    if not is_suspicious:
        return None
    is_major = doc_type in _L3_MAJOR_REVIEWABLE_DOCUMENT_TYPES and (
        confidence < _L3_SEVERE_CONFIDENCE_THRESHOLD
        or normalized_status in _L3_MAJOR_WARNING_STATUSES
        or bool(reason_codes.intersection(_L3_EXTRACTION_FAILURE_REASON_CODES))
    )
    return IssueSeverity.MAJOR if is_major else IssueSeverity.MINOR


def _collect_l3_document_snapshots(
    documents: List[Dict[str, Any]],
    extracted_context: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    snapshots: Dict[str, Dict[str, Any]] = {}

    def ensure_snapshot(doc_type: str) -> Dict[str, Any]:
        snapshot = snapshots.setdefault(
            doc_type,
            {
                "document_type": doc_type,
                "display_name": _snapshot_display_name(doc_type),
                "confidence": None,
                "status": None,
                "has_text": False,
                "has_fields": False,
                "review_required": False,
                "reason_codes": [],
                "selected_stage": None,
            },
        )
        return snapshot

    for document in documents or []:
        if not isinstance(document, dict):
            continue
        doc_type = _normalize_document_type(
            document.get("document_type") or document.get("documentType") or document.get("type")
        )
        if doc_type not in _L3_REVIEWABLE_DOCUMENT_TYPES:
            continue
        snapshot = ensure_snapshot(doc_type)
        confidence = _normalize_confidence_value(
            document.get("_extraction_confidence")
            or document.get("extraction_confidence")
            or document.get("extractionConfidence")
            or document.get("ocr_confidence")
            or document.get("ocrConfidence")
        )
        if confidence is not None:
            snapshot["confidence"] = confidence
        status = str(
            document.get("status")
            or document.get("extraction_status")
            or document.get("extractionStatus")
            or ""
        ).strip().lower()
        if status:
            snapshot["status"] = status
        snapshot["review_required"] = snapshot["review_required"] or bool(
            document.get("review_required") or document.get("reviewRequired")
        )
        raw_text = document.get("raw_text")
        if isinstance(raw_text, str) and raw_text.strip():
            snapshot["has_text"] = True
        extracted_fields = document.get("extracted_fields") or document.get("extractedFields")
        if isinstance(extracted_fields, dict) and extracted_fields:
            snapshot["has_fields"] = True
        artifacts = document.get("extraction_artifacts_v1") or document.get("extractionArtifactsV1")
        if isinstance(artifacts, dict):
            selected_stage = str(artifacts.get("selected_stage") or artifacts.get("final_stage") or "").strip()
            if selected_stage:
                snapshot["selected_stage"] = selected_stage
            reason_codes = [
                str(item).strip().upper()
                for item in (artifacts.get("reason_codes") or [])
                if str(item).strip()
            ]
            if reason_codes:
                snapshot["reason_codes"] = sorted(set((snapshot.get("reason_codes") or []) + reason_codes))

    for key, value in (extracted_context or {}).items():
        if not isinstance(value, dict):
            continue
        doc_type = _normalize_document_type(key)
        if doc_type not in _L3_REVIEWABLE_DOCUMENT_TYPES:
            continue
        snapshot = ensure_snapshot(doc_type)
        confidence = _normalize_confidence_value(
            value.get("_extraction_confidence")
            or value.get("extraction_confidence")
            or value.get("extractionConfidence")
            or value.get("ocr_confidence")
            or value.get("ocrConfidence")
        )
        if confidence is not None:
            snapshot["confidence"] = confidence
        status = str(
            value.get("status")
            or value.get("extraction_status")
            or value.get("extractionStatus")
            or ""
        ).strip().lower()
        if status:
            snapshot["status"] = status
        snapshot["review_required"] = snapshot["review_required"] or bool(
            value.get("review_required") or value.get("reviewRequired")
        )
        raw_text = value.get("raw_text")
        if isinstance(raw_text, str) and raw_text.strip():
            snapshot["has_text"] = True
        snapshot["has_fields"] = snapshot["has_fields"] or bool(value)
        artifacts = value.get("extraction_artifacts_v1") or value.get("extractionArtifactsV1")
        if isinstance(artifacts, dict):
            selected_stage = str(artifacts.get("selected_stage") or artifacts.get("final_stage") or "").strip()
            if selected_stage:
                snapshot["selected_stage"] = selected_stage
            reason_codes = [
                str(item).strip().upper()
                for item in (artifacts.get("reason_codes") or [])
                if str(item).strip()
            ]
            if reason_codes:
                snapshot["reason_codes"] = sorted(set((snapshot.get("reason_codes") or []) + reason_codes))

    return snapshots


def review_advanced_anomalies(
    documents: List[Dict[str, Any]],
    extracted_context: Dict[str, Any],
) -> Tuple[List[AIValidationIssue], Dict[str, Any]]:
    """
    Run a bounded L3 anomaly scan over extraction quality signals.

    This stays intentionally narrow during exporter freeze:
    - it does not duplicate documentary rule checks
    - it only flags suspicious extraction quality on present core documents
    """
    snapshots = _collect_l3_document_snapshots(documents, extracted_context)
    issues: List[AIValidationIssue] = []
    low_confidence_details: List[Dict[str, Any]] = []

    for doc_type, snapshot in sorted(snapshots.items()):
        confidence = snapshot.get("confidence")
        status = str(snapshot.get("status") or "").strip().lower()
        severity = _classify_l3_confidence_severity(snapshot)
        if severity is None:
            continue

        display_name = str(snapshot.get("display_name") or _snapshot_display_name(doc_type))
        reason_codes = list(snapshot.get("reason_codes") or [])
        selected_stage = str(snapshot.get("selected_stage") or "").strip().lower() or None
        low_confidence_details.append(
            {
                "document_type": doc_type,
                "confidence": round(confidence, 3) if confidence is not None else None,
                "status": status or None,
                "severity": severity.value,
                "review_required": bool(snapshot.get("review_required")),
                "reason_codes": reason_codes,
                "selected_stage": selected_stage,
            }
        )
        found_text = (
            f"{display_name} confidence {confidence:.2f}" + (f" with status '{status}'" if status else "")
            if confidence is not None
            else f"{display_name} requires manual review due to extraction fallback signals"
        )
        issues.append(
            AIValidationIssue(
                rule_id=f"AI-L3-LOW-CONFIDENCE-{doc_type.upper().replace('_', '-')}",
                title=f"Low Extraction Confidence: {display_name}",
                severity=severity,
                message=(
                    f"{display_name} extraction quality is low enough that non-deterministic review may be needed "
                    f"before relying on the extracted values."
                ),
                expected="Stable extraction confidence on the uploaded documentary evidence",
                found=found_text,
                suggestion=(
                    "Review the extracted values for this document manually and consider re-uploading a clearer scan "
                    "if the text or fields look unreliable."
                ),
                documents=[display_name],
                ucp_reference="UCP600 Article 14",
            )
        )

    metadata = {
        "l3_documents_reviewed": sorted(snapshots.keys()),
        "l3_documents_reviewed_count": len(snapshots),
        "l3_low_confidence_document_types": [item["document_type"] for item in low_confidence_details],
        "l3_low_confidence_details": low_confidence_details,
        "l3_low_confidence_count": len(low_confidence_details),
        "l3_low_confidence_threshold": _L3_LOW_CONFIDENCE_THRESHOLD,
        "l3_issue_count": len(issues),
        "l3_critical_issues": 0,
        "l3_major_issues": sum(1 for issue in issues if issue.severity == IssueSeverity.MAJOR),
        "l3_minor_issues": sum(1 for issue in issues if issue.severity == IssueSeverity.MINOR),
    }
    return issues, metadata


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


def _parse_lc_requirements_from_graph(requirements_graph: Dict[str, Any]) -> Dict[str, Any]:
    required_docs: List[Dict[str, Any]] = []
    bl_must_show: List[str] = []

    required_types = {
        str(item or "").strip().lower()
        for item in (requirements_graph.get("required_document_types") or [])
        if str(item or "").strip()
    }
    for doc_type, (display_name, _) in _GRAPH_CRITICAL_DOC_TYPES.items():
        if doc_type in required_types:
            required_docs.append(
                {
                    "document_type": doc_type,
                    "display_name": display_name,
                }
            )

    for item in requirements_graph.get("condition_requirements") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("requirement_type") or "").strip().lower() != "document_field_presence":
            continue
        document_type = str(item.get("document_type") or "").strip().lower()
        field_name = str(item.get("field_name") or "").strip()
        if document_type != "bill_of_lading" or not field_name:
            continue
        if field_name not in bl_must_show:
            bl_must_show.append(field_name)

    if not bl_must_show:
        conditions_text = " ".join(
            str(item or "").strip()
            for item in (
                list(requirements_graph.get("documentary_conditions") or [])
                + list(requirements_graph.get("ambiguous_conditions") or [])
            )
            if str(item or "").strip()
        ).upper()

        if conditions_text:
            if "VOYAGE" in conditions_text or " VOY " in f" {conditions_text} ":
                bl_must_show.append("voyage_number")
            if "GROSS" in conditions_text and "WEIGHT" in conditions_text:
                bl_must_show.append("gross_weight")
            if "NET" in conditions_text and "WEIGHT" in conditions_text:
                bl_must_show.append("net_weight")

    return {
        "required_documents": required_docs,
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

    bl_canonical = canonicalize_fields(bl_data)
    
    logger.info(f"B/L canonical fields: {list(bl_canonical.keys())}")
    raw_text = str(bl_data.get("raw_text") or "")
    extraction_artifacts = bl_data.get("extraction_artifacts_v1") if isinstance(bl_data.get("extraction_artifacts_v1"), dict) else {}
    targeted_candidates = extract_bl_required_field_candidates(raw_text=raw_text, extraction_artifacts=extraction_artifacts)

    field_info = {
        "voyage_number": {"display": "Voyage Number"},
        "gross_weight": {"display": "Gross Weight"},
        "net_weight": {"display": "Net Weight"},
    }
    
    checked_fields: Set[str] = set()  # Track to avoid duplicates
    
    for req_field in required_fields:
        # Skip if already checked (avoid duplicates)
        if req_field in checked_fields:
            continue
        checked_fields.add(req_field)
        
        info = field_info.get(req_field, {"keys": [req_field], "display": req_field.replace("_", " ").title(), "raw_patterns": []})
        
        # Look for canonical field value only (aliases already normalized upstream)
        found_value = bl_canonical.get(req_field)

        # Targeted recovery from OCR text/layout blocks before declaring missing.
        if not found_value:
            candidate = targeted_candidates.get(req_field)
            if candidate:
                found_value = candidate
                logger.info(f"✓ B/L has {info['display']} (targeted candidate): {candidate}")

        # Generic raw-text regex fallback
        if not found_value and raw_text:
            raw_value = find_first_pattern_value(raw_text, BL_RAW_PATTERNS.get(req_field, []))
            if raw_value:
                found_value = raw_value
                logger.info(f"✓ B/L has {info['display']} (raw text): {raw_value}")
        
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

    # Raw text path
    pl_raw = packing_list_data.get("raw_text") or ""
    if text_has_size_breakdown(pl_raw):
        has_sizes = True
        logger.info("✓ Packing list has size info in raw text")

    # Structured field path (canonical keys only)
    if not has_sizes:
        pl_canonical = canonicalize_fields(packing_list_data)
        if "size_breakdown" in pl_canonical:
            has_sizes = True
            logger.info("✓ Packing list has canonical size_breakdown field")
    
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
        logger.warning("No LC text available for AI validation")
        metadata["error"] = "no_lc_text"
        return [], metadata
    
    # =================================================================
    # 1. PARSE LC REQUIREMENTS
    # =================================================================
    logger.info("Step 1: Parsing LC requirements...")
    metadata["checks_performed"].append("lc_requirement_parsing")

    requirements_graph = (
        lc_data.get("requirements_graph_v1")
        or lc_data.get("requirementsGraphV1")
        or (extracted_context.get("lc") or {}).get("requirements_graph_v1")
        or (extracted_context.get("lc") or {}).get("requirementsGraphV1")
        or extracted_context.get("requirements_graph_v1")
    )
    if isinstance(requirements_graph, dict):
        requirements = _parse_lc_requirements_from_graph(requirements_graph)
    else:
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
    # 5. ADVANCED ANOMALY REVIEW (L3) — gated OFF by default in C1 of the
    # consolidation plan. This pass flags "Low Extraction Confidence" items
    # that are extraction-quality signals, not LC-clause discrepancies. They
    # belong in an advisory/intelligence channel, not in Findings. Enable
    # with VALIDATION_L3_ANOMALY_REVIEW_ENABLED=true if you want to see
    # them for debugging; keep them off the user-facing findings list.
    from app.config import settings as _ai_settings
    _l3_enabled = bool(getattr(_ai_settings, "VALIDATION_L3_ANOMALY_REVIEW_ENABLED", False))
    if _l3_enabled:
        logger.info("Step 5: Running bounded advanced anomaly review...")
        metadata["checks_performed"].append("advanced_anomaly_review")
        l3_issues, l3_metadata = review_advanced_anomalies(documents, extracted_context)
        all_issues.extend(l3_issues)
        metadata.update(l3_metadata)
        logger.info(
            "Step 5: L3 reviewed %d documents and flagged %d low-confidence anomalies",
            metadata.get("l3_documents_reviewed_count", 0),
            metadata.get("l3_issue_count", 0),
        )
    else:
        logger.info("Step 5: L3 anomaly review SKIPPED (flag off, C1 spine-only mode)")
        metadata["l3_documents_reviewed_count"] = 0
        metadata["l3_issue_count"] = 0

    # =================================================================
    # 6. DEDUPLICATE ISSUES
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
    # 7. SUMMARY
    # =================================================================
    metadata["total_issues"] = len(unique_issues)
    metadata["critical_issues"] = sum(1 for i in unique_issues if i.severity == IssueSeverity.CRITICAL)
    metadata["major_issues"] = sum(1 for i in unique_issues if i.severity == IssueSeverity.MAJOR)
    metadata["minor_issues"] = sum(1 for i in unique_issues if i.severity == IssueSeverity.MINOR)
    
    logger.info(
        f"AI Validation complete: {len(unique_issues)} issues "
        f"(critical={metadata['critical_issues']}, major={metadata['major_issues']}, minor={metadata['minor_issues']})"
    )
    
    return unique_issues, metadata
