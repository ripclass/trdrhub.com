from typing import Any, Dict, List, Optional, Set, Tuple, Union
import asyncio
import os
import re
import logging

from app.core.lc_types import LCType
from app.services.validator_rule_executor import execute_rules_with_semantics
from app.services.validator_rules_loader import load_rules_with_provenance
from app.services.validator_supplement_router import resolve_domain_sequence
from app.services.validator_audit_writer import apply_bank_policy
from app.services.validator_verdict_builder import build_validation_provenance, build_validation_results

logger = logging.getLogger(__name__)


def _extract_rule_lc_types(rule: Dict[str, Any]) -> List[str]:
    if not isinstance(rule, dict):
        return []
    metadata = rule.get("metadata") or {}
    lc_types = (
        rule.get("lc_types")
        or rule.get("lc_type")
        or metadata.get("lc_types")
        or metadata.get("lc_type")
    )
    if lc_types is None:
        tags = rule.get("tags")
        if isinstance(tags, list):
            inferred = []
            for tag in tags:
                if isinstance(tag, str) and tag.lower().startswith("lc:"):
                    inferred.append(tag.split(":", 1)[1].lower())
            lc_types = inferred or None
    if isinstance(lc_types, str):
        lc_types = [lc_types]
    if not lc_types:
        return []
    normalized: List[str] = []
    for item in lc_types:
        if not item:
            continue
        token = str(item).strip().lower()
        if token in {"all", "generic"}:
            token = "any"
        normalized.append(token)
    return normalized


def _rule_matches_lc_type(rule: Dict[str, Any], domain: Optional[str], lc_type: str) -> bool:
    domain_lower = (domain or "").lower()
    if lc_type == LCType.EXPORT.value and ".import" in domain_lower:
        return False
    if lc_type == LCType.IMPORT.value and ".export" in domain_lower:
        return False
    if lc_type == LCType.UNKNOWN.value and (
        ".import" in domain_lower or ".export" in domain_lower
    ):
        return False

    allowed_types = _extract_rule_lc_types(rule)
    if not allowed_types:
        return True
    if "any" in allowed_types or "*" in allowed_types:
        return True
    if lc_type == LCType.UNKNOWN.value:
        return "unknown" in allowed_types
    return lc_type in allowed_types


def filter_rules_by_lc_context(
    rules_with_meta: List[Tuple[Dict[str, Any], Dict[str, Any]]],
    document_data: Dict[str, Any],
) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """
    Backwards-compatible wrapper for legacy callers.
    """
    lc_context = document_data.get("lc") or {}
    return activate_rules_for_lc(lc_context, rules_with_meta, document_data)


def activate_rules_for_lc(
    lc_fields: Dict[str, Any],
    rule_definitions: List[Tuple[Dict[str, Any], Dict[str, Any]]],
    doc_set: Dict[str, Any],
) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """
    Rule activation layer. Returns only the rules relevant to this LC package.
    """
    if not rule_definitions:
        return []

    lc_context = lc_fields or {}
    lc_text = _build_lc_text_blob(lc_context, doc_set)
    doc_requirements = _infer_document_requirements(lc_context, lc_text, doc_set)
    toggles = _derive_rule_toggles(lc_context, lc_text, doc_requirements)
    goods_ready = _has_goods_context(lc_context, doc_set)
    ports_ready = _has_complete_ports(lc_context)
    lc_type = str(doc_set.get("lc_type") or lc_context.get("lc_type") or LCType.UNKNOWN.value).lower()
    doc_ready_map = _build_document_ready_map(lc_context, doc_set)

    drop_stats = {
        "informational": 0,
        "doc_requirement": 0,
        "direction": 0,
        "ports": 0,
        "goods": 0,
        "third_party": 0,
        "negotiability": 0,
        "hs_code": 0,
        "signed_invoice": 0,
        "insurance": 0,
    }

    active: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for rule, meta in rule_definitions:
        if not isinstance(rule, dict):
            continue
        domain_lower = ((meta or {}).get("domain") or "").lower()
        if _is_informational_rule(rule, domain_lower):
            drop_stats["informational"] += 1
            continue
        if not _rule_matches_doc_requirements(rule, doc_requirements, doc_ready_map):
            drop_stats["doc_requirement"] += 1
            continue
        if not _rule_matches_lc_direction(rule, lc_type):
            drop_stats["direction"] += 1
            continue
        if not ports_ready and _rule_targets_ports(rule):
            drop_stats["ports"] += 1
            continue
        if not goods_ready and _rule_targets_goods(rule):
            drop_stats["goods"] += 1
            continue
        if toggles["third_party_allowed"] and _rule_targets_third_party(rule):
            drop_stats["third_party"] += 1
            continue
        if toggles["non_negotiable_allowed"] and _rule_targets_negotiability(rule):
            drop_stats["negotiability"] += 1
            continue
        if not toggles["hs_code_required"] and _rule_targets_hs_code(rule):
            drop_stats["hs_code"] += 1
            continue
        if not toggles["signed_invoice_required"] and _rule_targets_signed_invoice(rule):
            drop_stats["signed_invoice"] += 1
            continue
        if not toggles["insurance_required"] and _rule_targets_insurance(rule):
            drop_stats["insurance"] += 1
            continue
        active.append((rule, meta))

    logger.info(
        "Rule activation summary: total=%s active=%s drops=%s lc_type=%s toggles=%s goods_ready=%s ports_ready=%s doc_ready=%s",
        len(rule_definitions),
        len(active),
        drop_stats,
        lc_type,
        toggles,
        goods_ready,
        ports_ready,
        doc_ready_map,
    )

    return active


DOC_KEYWORDS = {
    "commercial_invoice": ["commercial invoice", "signed commercial invoice", "invoice"],
    "bill_of_lading": ["bill of lading", "b/l", "transport document", "ocean bill"],
    "packing_list": ["packing list", "weight list"],
    "certificate_of_origin": ["certificate of origin", "c/o", "coo"],
    "insurance_certificate": ["insurance certificate", "insurance policy", "coverage"],
    "inspection_certificate": ["inspection certificate", "inspection report"],
    "beneficiary_certificate": ["beneficiary certificate"],
}

DOC_SYNONYMS = {
    "lc": "lc",
    "letter_of_credit": "lc",
    "commercial_invoice": "commercial_invoice",
    "invoice": "commercial_invoice",
    "ci": "commercial_invoice",
    "bill_of_lading": "bill_of_lading",
    "billoflading": "bill_of_lading",
    "bl": "bill_of_lading",
    "transport_document": "bill_of_lading",
    "transport-documents": "bill_of_lading",
    "packing_list": "packing_list",
    "certificate_of_origin": "certificate_of_origin",
    "coo": "certificate_of_origin",
    "insurance_certificate": "insurance_certificate",
    "insurance": "insurance_certificate",
    "policy": "insurance_certificate",
    "inspection_certificate": "inspection_certificate",
    "beneficiary_certificate": "beneficiary_certificate",
}

FIELD_PREFIX_TO_DOC = {
    "lc.": "lc",
    "letter_of_credit.": "lc",
    "invoice.": "commercial_invoice",
    "commercial_invoice.": "commercial_invoice",
    "bill_of_lading.": "bill_of_lading",
    "bl.": "bill_of_lading",
    "packing_list.": "packing_list",
    "certificate_of_origin.": "certificate_of_origin",
    "coo.": "certificate_of_origin",
    "insurance_certificate.": "insurance_certificate",
    "insurance.": "insurance_certificate",
    "inspection_certificate.": "inspection_certificate",
}

GOODS_TAG_HINTS = {"goods", "description", "product", "hs_code", "hs code", "quantity", "hs-code"}
PORT_TAG_HINTS = {"port", "ports", "shipment_route", "route", "loading_port", "discharge_port"}
THIRD_PARTY_TAGS = {"third_party", "third-party", "thirdparty"}
NEGOTIABILITY_TAGS = {"negotiable", "non_negotiable", "original_document", "negotiability"}
INSURANCE_TAGS = {"insurance", "coverage", "policy", "premium"}
SIGNED_INVOICE_TAGS = {"signed_invoice", "signed", "signature"}
HS_CODE_TAGS = {"hs_code", "hs-code", "harmonized", "customs_hs"}
DOCUMENT_NOISE_KEYS = {
    "raw_text",
    "rawText",
    "raw_text_preview",
    "rawTextPreview",
    "extraction_status",
    "extractionStatus",
    "tag",
    "id",
    "document_id",
    "documentId",
}


def _build_lc_text_blob(lc_context: Dict[str, Any], doc_set: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in ("additional_conditions", "raw_text"):
        value = lc_context.get(key)
        if isinstance(value, str):
            parts.append(value)
    lc_text = doc_set.get("lc_text")
    if isinstance(lc_text, str):
        parts.append(lc_text)
    return " ".join(parts).lower()


def _infer_document_requirements(
    lc_context: Dict[str, Any],
    lc_text: str,
    doc_set: Dict[str, Any],
) -> Dict[str, bool]:
    canonical_docs = [
        "commercial_invoice",
        "bill_of_lading",
        "packing_list",
        "certificate_of_origin",
        "insurance_certificate",
        "inspection_certificate",
        "beneficiary_certificate",
    ]
    requirements = {doc: False for doc in canonical_docs}
    requirements["lc"] = True

    requested_docs = _extract_requested_documents(lc_context, lc_text)
    if not requested_docs:
        requested_docs = _fallback_documents_from_payload(doc_set)

    for doc in canonical_docs:
        requirements[doc] = doc in requested_docs

    incoterm = (lc_context.get("incoterm") or "").upper()
    mentions_insurance = _text_contains_any(lc_text, DOC_KEYWORDS["insurance_certificate"])
    insurance_required = "insurance_certificate" in requested_docs or mentions_insurance
    if incoterm.startswith("FOB") and not mentions_insurance:
        insurance_required = False
    requirements["insurance_certificate"] = insurance_required

    return requirements


def _extract_requested_documents(lc_context: Dict[str, Any], lc_text: str) -> Set[str]:
    requested: Set[str] = set()

    def _consume_tokens(raw: Any):
        if isinstance(raw, str):
            tokens = re.split(r"[,\n;]+", raw)
        elif isinstance(raw, (list, tuple, set)):
            tokens = list(raw)
        else:
            return
        for token in tokens:
            normalized = _normalize_doc_label(token)
            if normalized:
                requested.add(normalized)

    for key in ("requested_documents", "documents_requested", "documents_required"):
        if key in lc_context:
            _consume_tokens(lc_context.get(key))

    if isinstance(lc_context.get("documents"), list):
        for entry in lc_context["documents"]:
            if isinstance(entry, str):
                _consume_tokens(entry)
            elif isinstance(entry, dict):
                label = entry.get("label") or entry.get("name")
                _consume_tokens(label)

    if lc_text:
        for doc, keywords in DOC_KEYWORDS.items():
            if _text_contains_any(lc_text, keywords):
                requested.add(doc)

    return requested


def _fallback_documents_from_payload(doc_set: Dict[str, Any]) -> Set[str]:
    fallback: Set[str] = set()
    documents_presence = doc_set.get("documents_presence") or {}
    for raw_key, entry in documents_presence.items():
        if not entry:
            continue
        if not entry.get("present"):
            continue
        normalized = _normalize_doc_label(raw_key)
        if normalized:
            fallback.add(normalized)

    payload_keys = {
        "commercial_invoice": doc_set.get("invoice"),
        "bill_of_lading": doc_set.get("bill_of_lading") or doc_set.get("billOfLading"),
        "packing_list": doc_set.get("packing_list"),
        "certificate_of_origin": doc_set.get("certificate_of_origin"),
        "insurance_certificate": doc_set.get("insurance_certificate"),
        "inspection_certificate": doc_set.get("inspection_certificate"),
        "beneficiary_certificate": doc_set.get("beneficiary_certificate"),
    }
    for doc, ctx in payload_keys.items():
        if isinstance(ctx, dict) and ctx:
            fallback.add(doc)

    return fallback


def _derive_rule_toggles(
    lc_context: Dict[str, Any],
    lc_text: str,
    doc_requirements: Dict[str, bool],
) -> Dict[str, bool]:
    text = lc_text or ""
    toggles = {
        "third_party_allowed": _text_contains_any(text, ["third party documents acceptable", "third-party documents acceptable", "third party docs acceptable"]),
        "non_negotiable_allowed": _text_contains_any(text, ["non-negotiable documents acceptable", "non negotiable documents acceptable"]),
        "hs_code_required": _text_contains_any(text, ["hs code", "harmonized system", "hs-code"]),
        "signed_invoice_required": _text_contains_any(text, ["signed commercial invoice", "signed invoice"]),
        "insurance_required": doc_requirements.get("insurance_certificate", False),
    }
    return toggles


def _rule_matches_doc_requirements(
    rule: Dict[str, Any],
    requirements: Dict[str, bool],
    doc_ready_map: Dict[str, bool],
) -> bool:
    targets = _rule_targets_documents(rule)
    if not targets:
        return True
    for target in targets:
        if target == "lc":
            continue
        canonical = "bill_of_lading" if target == "transport_document" else target
        allowed = requirements.get(canonical, True)
        if not allowed:
            return False
        if not doc_ready_map.get(canonical, False):
            return False
    return True


def _rule_matches_lc_direction(rule: Dict[str, Any], lc_type: str) -> bool:
    tags = _normalize_tags(rule)
    if lc_type == LCType.EXPORT.value and "import" in tags and "export" not in tags:
        return False
    if lc_type == LCType.IMPORT.value and "export" in tags and "import" not in tags:
        return False
    return True


def _rule_targets_ports(rule: Dict[str, Any]) -> bool:
    tags = _normalize_tags(rule)
    if tags.intersection(PORT_TAG_HINTS):
        return True
    for path in _extract_rule_field_paths(rule):
        if "port" in path or "shipment" in path:
            return True
    return False


def _rule_targets_goods(rule: Dict[str, Any]) -> bool:
    tags = _normalize_tags(rule)
    if tags.intersection(GOODS_TAG_HINTS):
        return True
    for path in _extract_rule_field_paths(rule):
        if "goods" in path or "hs_code" in path or "product" in path:
            return True
    return False


def _rule_targets_third_party(rule: Dict[str, Any]) -> bool:
    tags = _normalize_tags(rule)
    if tags.intersection(THIRD_PARTY_TAGS):
        return True
    title = (rule.get("title") or "").lower()
    return "third party" in title


def _rule_targets_negotiability(rule: Dict[str, Any]) -> bool:
    tags = _normalize_tags(rule)
    if tags.intersection(NEGOTIABILITY_TAGS):
        return True
    title = (rule.get("title") or "").lower()
    return "negotiable" in title


def _rule_targets_hs_code(rule: Dict[str, Any]) -> bool:
    tags = _normalize_tags(rule)
    if tags.intersection(HS_CODE_TAGS):
        return True
    title = (rule.get("title") or "").lower()
    return "hs code" in title


def _rule_targets_signed_invoice(rule: Dict[str, Any]) -> bool:
    tags = _normalize_tags(rule)
    if tags.intersection(SIGNED_INVOICE_TAGS):
        return True
    title = (rule.get("title") or "").lower()
    return "signed invoice" in title


def _rule_targets_insurance(rule: Dict[str, Any]) -> bool:
    tags = _normalize_tags(rule)
    if tags.intersection(INSURANCE_TAGS):
        return True
    for path in _extract_rule_field_paths(rule):
        if "insurance" in path:
            return True
    return False


def _rule_targets_documents(rule: Dict[str, Any]) -> Set[str]:
    targets: Set[str] = set()
    doc_entries = rule.get("documents") or rule.get("document_types") or []
    if isinstance(doc_entries, str):
        doc_entries = [doc_entries]
    for entry in doc_entries:
        normalized = _normalize_doc_label(entry)
        if normalized:
            targets.add(normalized)
    for path in _extract_rule_field_paths(rule):
        inferred = _infer_doc_from_field(path)
        if inferred:
            targets.add(inferred)
    return targets


def _normalize_doc_label(value: Any) -> Optional[str]:
    if not value:
        return None
    token = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if token in DOC_SYNONYMS:
        return DOC_SYNONYMS[token]
    compact = token.replace("_", "")
    if compact in DOC_SYNONYMS:
        return DOC_SYNONYMS[compact]
    return token if token in {"lc"} else None


def _infer_doc_from_field(field_path: Optional[str]) -> Optional[str]:
    if not field_path:
        return None
    lowered = field_path.lower()
    for prefix, doc in FIELD_PREFIX_TO_DOC.items():
        if lowered.startswith(prefix):
            return doc
    return None


def _extract_rule_field_paths(rule: Dict[str, Any]) -> List[str]:
    paths: List[str] = []
    for condition in rule.get("conditions") or []:
        field_path = condition.get("field") or condition.get("field_path")
        if isinstance(field_path, str):
            paths.append(field_path.lower())
        value_ref = condition.get("value_ref")
        if isinstance(value_ref, str):
            paths.append(value_ref.lower())
    return paths


def _normalize_tags(rule: Dict[str, Any]) -> Set[str]:
    tags = rule.get("tags")
    if not isinstance(tags, list):
        return set()
    return {str(tag).strip().lower() for tag in tags if tag}


def _text_contains_any(text: str, keywords: List[str]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _has_goods_context(lc_context: Dict[str, Any], doc_set: Dict[str, Any]) -> bool:
    lc_goods = lc_context.get("goods_description")
    invoice_ctx = doc_set.get("invoice") or {}
    packing_ctx = doc_set.get("packing_list") or {}
    invoice_goods = invoice_ctx.get("goods_description") or invoice_ctx.get("description") or invoice_ctx.get("product_description")
    packing_goods = packing_ctx.get("goods_description") or packing_ctx.get("description")
    return bool(lc_goods and (invoice_goods or packing_goods))


def _has_complete_ports(lc_context: Dict[str, Any]) -> bool:
    ports = lc_context.get("ports") or {}
    return bool(ports.get("loading") and ports.get("discharge"))


INFORMATIONAL_TITLE_KEYWORDS = (
    "application of ucp",
    "scope of application",
    "interpretation",
    "interpretations",
    "definitions",
    "disclaimer",
    "force majeure",
    "bank-to-bank reimbursement",
    "bank to bank reimbursement",
    "assignment of proceeds",
    "availability, expiry date",
    "expiry date and place",
    "role of confirming bank",
    "clarify advising bank",
    "chartered vessel",
    "original documents and copies",
    "mode of transport",
    "clause inconsistent",
    "set of transport documents",
    "mandatory fields missing",
)

INFORMATIONAL_TAGS = {
    "application",
    "scope",
    "interpretation",
    "definitions",
    "disclaimer",
    "reimbursement",
    "force_majeure",
}

INFORMATIONAL_ARTICLES = {"1", "2", "3", "4", "5", "34", "35", "36", "37"}
INFORMATIONAL_DROP_TITLES = [
    "Advising of Credits",
    "Advising of Credits and Amendments",
    "Dishonour Documents",
    "Waiver and Notice",
    "Confirming Bank Undertaking",
    "Availability, Expiry Date and Place for Presentation",
    "Force Majeure",
    "Interpretations",
    "Application of UCP",
    "Reimbursement Arrangements",
    "Original Documents and Copies",
    "Transport Document Covering at Least Two Different Modes of Transport",
    "Non-Negotiable Documents",
    "Set of Transport Documents",
    "Mode of Transport",
    "Technical References",
    "Bank-to-Bank Reimbursement",
]


def _is_informational_rule(rule: Dict[str, Any], domain_lower: str) -> bool:
    title = (rule.get("title") or "").lower()
    if any(keyword in title for keyword in INFORMATIONAL_TITLE_KEYWORDS):
        return True

    tags = rule.get("tags")
    if isinstance(tags, list):
        tag_values = {str(tag).strip().lower() for tag in tags if tag}
        if INFORMATIONAL_TAGS.intersection(tag_values):
            return True

    article = rule.get("article")
    if isinstance(article, str):
        article_code = article.strip().split()[0]
        if domain_lower.startswith("icc.") and article_code in INFORMATIONAL_ARTICLES:
            # Many articles in this range describe definitions/scope/disclaimers.
            # Only treat them as informational when no document types are referenced.
            documents = rule.get("documents") or rule.get("document_types")
            if not documents:
                return True

    return False


def filter_informational_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not issues:
        return issues
    drop_tokens = [title.lower() for title in INFORMATIONAL_DROP_TITLES]
    cleaned: List[Dict[str, Any]] = []
    for issue in issues:
        title_value = str(issue.get("title") or issue.get("rule") or "").lower()
        if title_value and any(token in title_value for token in drop_tokens):
            continue
        cleaned.append(issue)
    return cleaned


def _build_document_ready_map(lc_context: Dict[str, Any], doc_set: Dict[str, Any]) -> Dict[str, bool]:
    ready: Dict[str, bool] = {"lc": bool(lc_context)}
    for doc_key in DOC_KEYWORDS.keys():
        ctx = _resolve_document_context(doc_set, doc_key)
        ready[doc_key] = _document_has_structured_fields(ctx)
    return ready


def _resolve_document_context(doc_set: Dict[str, Any], canonical: str) -> Dict[str, Any]:
    ctx = doc_set.get(canonical)
    if isinstance(ctx, dict):
        return ctx
    for key, value in doc_set.items():
        if not isinstance(value, dict):
            continue
        normalized = _normalize_doc_label(key)
        if normalized == canonical:
            return value
    return {}


def _document_has_structured_fields(ctx: Any) -> bool:
    if not isinstance(ctx, dict):
        return False
    for key, value in ctx.items():
        if key in DOCUMENT_NOISE_KEYS:
            continue
        if value in (None, "", [], {}):
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return True
    return False


def _extract_additional_conditions(lc_text: str) -> Optional[str]:
    if not lc_text:
        return None
    match = re.search(r":?47A\s*:\s*([\s\S]*?)(?=\n:?[\d]{2}[A-Z]?\s*:|$)", lc_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


async def enrich_validation_results_with_ai(
    validation_results: List[Dict[str, Any]],
    document_data: Dict[str, Any],
    session_id: str,
    user_id: str,
    db_session
) -> Dict[str, Any]:
    """
    Optionally enrich validation results with AI-generated explanations.
    
    Only runs if AI_ENRICHMENT feature flag is enabled and user/tenant has access.
    
    Returns:
        Dict with 'ai_enrichment' key containing explanations and suggestions
    """
    ai_enrichment_enabled = os.getenv("AI_ENRICHMENT", "false").lower() == "true"
    
    if not ai_enrichment_enabled:
        return {}
    
    try:
        from app.services.llm_assist import LLMAssistService, DiscrepancySummaryRequest, AILanguage
        from app.models import ValidationSession, User
        
        # Get session and user
        session = db_session.query(ValidationSession).filter(
            ValidationSession.id == session_id
        ).first()
        
        user = db_session.query(User).filter(User.id == user_id).first()
        
        if not session or not user:
            logger.warning("Session or user not found for AI enrichment")
            return {}
        
        # Extract discrepancies (failed rules)
        discrepancies = [
            {
                "rule_code": r.get("rule", r.get("rule_id", "unknown")),
                "title": r.get("title", ""),
                "message": r.get("message", ""),
                "severity": r.get("severity", "warning")
            }
            for r in validation_results
            if not r.get("passed", False)
        ]
        
        if not discrepancies:
            # No discrepancies to enrich
            return {}
        
        # Check if AI assist is enabled for this tenant
        # For now, check feature flag; in production check tenant settings
        llm_service = LLMAssistService(db_session)
        
        # Generate AI enrichment
        enrichment_request = DiscrepancySummaryRequest(
            session_id=session_id,
            discrepancies=discrepancies,
            language=AILanguage.ENGLISH,
            include_explanations=True,
            include_fix_suggestions=True
        )
        
        ai_response = await llm_service.generate_discrepancy_summary(
            enrichment_request,
            user
        )
        
        return {
            "ai_enrichment": {
                "summary": ai_response.output,
                "confidence": ai_response.confidence.value,
                "rule_references": ai_response.rule_references,
                "suggestions": ai_response.suggestions,
                "fallback_used": ai_response.fallback_used
            }
        }
        
    except Exception as e:
        logger.error(f"AI enrichment failed: {e}", exc_info=True)
        # Don't fail validation if AI enrichment fails
        return {}


async def validate_document_async(
    document_data: Dict[str, Any],
    document_type: str,
    return_provenance: bool = False,
) -> Union[List[Dict[str, Any]], Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
    """
    DB-backed validation pipeline that loads rules from the normalized rules table,
    filters them for the LC context, and evaluates outcomes.
    """
    from app.services.rules_service import get_rules_service

    rules_service = get_rules_service()

    jurisdiction = document_data.get("jurisdiction", "global")
    domain_sequence = resolve_domain_sequence(document_data)

    aggregated_rules, base_metadata, provenance_rulesets = await load_rules_with_provenance(
        rules_service=rules_service,
        domain_sequence=domain_sequence,
        jurisdiction=jurisdiction,
        document_type=document_type,
    )

    if not aggregated_rules:
        raise RuntimeError(
            f"No rules retrieved for document_type={document_type}, domains={domain_sequence}, jurisdiction={jurisdiction}"
        )

    filtered_rules_with_meta = [
        (rule, meta)
        for rule, meta in aggregated_rules
        if rule.get("document_type") in (None, "", document_type, "lc")
    ]
    doc_scope_count = len(filtered_rules_with_meta)
    lc_type_context = str(document_data.get("lc_type") or LCType.UNKNOWN.value).lower()
    filtered_rules_with_meta = [
        (rule, meta)
        for rule, meta in filtered_rules_with_meta
        if _rule_matches_lc_type(rule, (meta or {}).get("domain"), lc_type_context)
    ]
    activated_rules_with_meta = activate_rules_for_lc(
        document_data.get("lc") or {},
        filtered_rules_with_meta,
        document_data,
    )
    sample_rules = [
        (rule.get("rule_id") or rule.get("code") or rule.get("title"))
        for rule, _ in activated_rules_with_meta[:5]
    ]
    logger.info(
        "DB rule selection summary",
        extra={
            "domains": domain_sequence,
            "total_rules": len(aggregated_rules),
            "doc_scope_rules": doc_scope_count,
            "activated_rules": len(activated_rules_with_meta),
            "sample_rule_ids": sample_rules,
        },
    )

    if not activated_rules_with_meta:
        raise RuntimeError(
            f"No applicable rules after filtering for document_type={document_type}, domains={domain_sequence}, jurisdiction={jurisdiction}"
        )

    outcomes, rule_envelopes, semantic_registry, prepared_rule_count = await execute_rules_with_semantics(
        activated_rules_with_meta,
        document_data,
        base_metadata,
        domain_sequence=domain_sequence,
        jurisdiction=jurisdiction,
    )
    results = build_validation_results(
        outcomes=outcomes,
        rule_envelopes=rule_envelopes,
        document_data=document_data,
        semantic_registry=semantic_registry,
        base_metadata=base_metadata,
    )
    provenance_payload = build_validation_provenance(
        base_metadata=base_metadata,
        jurisdiction=jurisdiction,
        prepared_rule_count=prepared_rule_count,
        provenance_rulesets=provenance_rulesets,
    )
    document_data["_db_rules_execution"] = provenance_payload
    if return_provenance:
        return results, provenance_payload
    return results


def validate_document(document_data: Dict[str, Any], document_type: str) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for validate_document_async.
    """
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            raise RuntimeError(
                "validate_document cannot be called from an active event loop; "
                "await validate_document_async instead."
            )
    except RuntimeError:
        # No running loop in this thread; safe to spawn a new one
        pass

    return asyncio.run(validate_document_async(document_data, document_type))


