from typing import Any, Dict, List, Optional, Set, Tuple
import os
import re
import logging
import copy
from datetime import datetime
from uuid import UUID

from app.models.rules import Rule
from app.database import SessionLocal
from app.services.rulhub_client import fetch_rules_from_rulhub
from app.config import settings
from app.core.lc_types import LCType
from app.services.semantic_compare import run_semantic_comparison
from app.services.rule_evaluator import RuleEvaluator

logger = logging.getLogger(__name__)


ICC_TEXT_KEYS = [
    "applicable_rules",
    "applicable_rules_text",
    "lc_text",
    "raw_text",
    "mt700_40e",
    "mt700_field_40e",
    "narrative",
    "notes",
    "clauses",
    "terms",
    "instructions",
    "reimbursement_text",
]

ICC_META_KEYS = [
    "lc_type",
    "instrument_type",
    "product",
    "product_type",
    "product_category",
    "transaction_type",
    "facility_type",
]

ICC_RULE_PATTERN = re.compile(
    r"(isp\s*98|isp98|ucp\s*600|ucp600|e[-\s]?ucp\s*(?:v?\s*2\.1|latest)|urr\s*725|urr725|urdg\s*758|urdg758|urc\s*522|urc522)",
    re.IGNORECASE,
)


def get_active_overlay(bank_id: str, db_session) -> Optional[Dict[str, Any]]:
    """
    Get the active policy overlay for a bank.
    
    Returns:
        Overlay dict with config, or None if not found
    """
    try:
        from app.models.bank_policy import BankPolicyOverlay
        
        # Convert string to UUID if needed
        bank_uuid = UUID(bank_id) if isinstance(bank_id, str) else bank_id
        
        overlay = db_session.query(BankPolicyOverlay).filter(
            BankPolicyOverlay.bank_id == bank_uuid,
            BankPolicyOverlay.active == True
        ).first()
        
        if overlay:
            return {
                "id": str(overlay.id),
                "version": overlay.version,
                "config": overlay.config,
            }
        return None
    except Exception as e:
        logger.warning(f"Failed to load policy overlay for bank {bank_id}: {e}")
        return None


def get_active_exceptions(bank_id: str, db_session) -> List[Dict[str, Any]]:
    """
    Get active policy exceptions for a bank.
    
    Returns:
        List of exception dicts
    """
    try:
        from app.models.bank_policy import BankPolicyException
        
        # Convert string to UUID if needed
        bank_uuid = UUID(bank_id) if isinstance(bank_id, str) else bank_id
        
        exceptions = db_session.query(BankPolicyException).filter(
            BankPolicyException.bank_id == bank_uuid
        ).filter(
            (BankPolicyException.expires_at.is_(None)) |
            (BankPolicyException.expires_at > datetime.utcnow())
        ).all()
        
        return [
            {
                "id": str(e.id),
                "rule_code": e.rule_code,
                "scope": e.scope,
                "effect": e.effect,
                "expires_at": e.expires_at.isoformat() if e.expires_at else None,
            }
            for e in exceptions
        ]
    except Exception as e:
        logger.warning(f"Failed to load policy exceptions for bank {bank_id}: {e}")
        return []


def apply_policy_overlay(
    validation_results: List[Dict[str, Any]],
    overlay: Optional[Dict[str, Any]],
    document_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Apply policy overlay stricter checks to validation results.
    
    Modifies results in-place based on overlay config.
    """
    if not overlay or not overlay.get("config"):
        return validation_results
    
    config = overlay["config"]
    stricter_checks = config.get("stricter_checks", {})
    thresholds = config.get("thresholds", {})
    
    # Apply stricter checks
    max_date_slippage = stricter_checks.get("max_date_slippage_days")
    if max_date_slippage is not None:
        # Check date-related rules and apply stricter tolerance
        for result in validation_results:
            if "date" in result.get("rule", "").lower() or "date" in result.get("title", "").lower():
                # If rule failed due to date mismatch, check if within tolerance
                # This is a simplified check - in production would need more sophisticated date comparison
                pass  # TODO: Implement date slippage check
    
    # Apply severity override
    severity_override = thresholds.get("discrepancy_severity_override")
    if severity_override:
        for result in validation_results:
            if not result.get("passed", False):
                result["severity"] = severity_override
                result["policy_override"] = True
    
    return validation_results


def apply_policy_exceptions(
    validation_results: List[Dict[str, Any]],
    exceptions: List[Dict[str, Any]],
    document_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Apply policy exceptions to validation results.
    
    If a failed rule matches an active exception scope, apply the exception effect.
    """
    if not exceptions:
        return validation_results
    
    for result in validation_results:
        if result.get("passed", False):
            continue  # Only apply exceptions to failed rules
        
        rule_code = result.get("rule", "")
        
        # Find matching exceptions
        for exception in exceptions:
            if exception["rule_code"] != rule_code:
                continue
            
            # Check scope match
            scope = exception.get("scope", {})
            matches_scope = True
            
            if scope.get("client"):
                doc_client = document_data.get("client_name") or document_data.get("client")
                if doc_client != scope["client"]:
                    matches_scope = False
            
            if scope.get("branch") and matches_scope:
                doc_branch = document_data.get("branch")
                if doc_branch != scope["branch"]:
                    matches_scope = False
            
            if scope.get("product") and matches_scope:
                doc_product = document_data.get("product")
                if doc_product != scope["product"]:
                    matches_scope = False
            
            if not matches_scope:
                continue
            
            # Apply exception effect
            effect = exception.get("effect", "waive")
            
            if effect == "waive":
                result["passed"] = True
                result["waived"] = True
                result["waived_reason"] = f"Policy exception: {exception.get('reason', 'N/A')}"
                result["severity"] = "info"  # Downgrade to info
            elif effect == "downgrade":
                # Downgrade severity
                current_severity = result.get("severity", "critical")
                if current_severity == "critical":
                    result["severity"] = "major"
                elif current_severity == "major":
                    result["severity"] = "minor"
                result["exception_applied"] = True
            elif effect == "override":
                result["passed"] = True
                result["overridden"] = True
                result["override_reason"] = f"Policy exception: {exception.get('reason', 'N/A')}"
            
            result["exception_id"] = exception.get("id")
            break  # Apply first matching exception
    
    return validation_results


async def apply_bank_policy(
    validation_results: List[Dict[str, Any]],
    bank_id: str,
    document_data: Dict[str, Any],
    db_session,
    validation_session_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Apply bank policy overlay and exceptions to validation results.
    
    This function:
    1. Loads active overlay for the bank
    2. Applies stricter checks from overlay
    3. Loads active exceptions
    4. Applies exceptions to matching failed rules
    5. Logs analytics events for policy application tracking
    
    Returns:
        Modified validation results with policy overlays/exceptions applied
    """
    if not bank_id:
        return validation_results
    
    try:
        from app.models.bank_policy import BankPolicyApplicationEvent
        from uuid import UUID
        import time
        
        start_time = time.time()
        
        # Calculate metrics before policy application
        discrepancies_before = len([r for r in validation_results if not r.get("passed", False)])
        severity_before = {}
        for result in validation_results:
            if not result.get("passed", False):
                severity = result.get("severity", "unknown")
                severity_before[severity] = severity_before.get(severity, 0) + 1
        
        # Load overlay
        overlay = get_active_overlay(bank_id, db_session)
        overlay_id = None
        overlay_version = None
        
        if overlay:
            overlay_id = overlay.get("id")
            overlay_version = overlay.get("version")
            validation_results = apply_policy_overlay(validation_results, overlay, document_data)
        
        # Load exceptions
        exceptions = get_active_exceptions(bank_id, db_session)
        
        # Track exception applications
        exception_applications = []
        if exceptions:
            validation_results = apply_policy_exceptions(validation_results, exceptions, document_data)
            
            # Track which exceptions were applied
            for result in validation_results:
                if result.get("exception_id") or result.get("waived") or result.get("overridden") or result.get("exception_applied"):
                    exception_id = result.get("exception_id")
                    rule_code = result.get("rule", "")
                    effect = None
                    if result.get("waived"):
                        effect = "waive"
                    elif result.get("overridden"):
                        effect = "override"
                    elif result.get("exception_applied"):
                        effect = "downgrade"
                    
                    if exception_id and rule_code:
                        exception_applications.append({
                            "exception_id": exception_id,
                            "rule_code": rule_code,
                            "effect": effect
                        })
        
        # Calculate metrics after policy application
        discrepancies_after = len([r for r in validation_results if not r.get("passed", False)])
        severity_after = {}
        for result in validation_results:
            if not result.get("passed", False):
                severity = result.get("severity", "unknown")
                severity_after[severity] = severity_after.get(severity, 0) + 1
        
        # Calculate severity changes
        severity_changes = {}
        all_severities = set(list(severity_before.keys()) + list(severity_after.keys()))
        for severity in all_severities:
            before_count = severity_before.get(severity, 0)
            after_count = severity_after.get(severity, 0)
            change = after_count - before_count
            if change != 0:
                severity_changes[severity] = change
        
        # Calculate result summary
        rules_affected = []
        severity_upgrades = 0
        severity_downgrades = 0
        waived_rules = 0
        overridden_rules = 0
        
        for result in validation_results:
            if result.get("waived"):
                waived_rules += 1
                rules_affected.append(result.get("rule", ""))
            elif result.get("overridden"):
                overridden_rules += 1
                rules_affected.append(result.get("rule", ""))
            elif result.get("exception_applied"):
                severity_downgrades += 1
                rules_affected.append(result.get("rule", ""))
            elif result.get("policy_override"):
                severity_upgrades += 1
                rules_affected.append(result.get("rule", ""))
        
        result_summary = {
            "rules_affected": list(set(rules_affected)),
            "severity_upgrades": severity_upgrades,
            "severity_downgrades": severity_downgrades,
            "waived_rules": waived_rules,
            "overridden_rules": overridden_rules
        }
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Determine application type
        application_type = "both" if overlay and exception_applications else ("overlay" if overlay else ("exception" if exception_applications else "none"))
        
        # Log analytics events
        if validation_session_id and user_id and application_type != "none":
            try:
                bank_uuid = UUID(bank_id) if isinstance(bank_id, str) else bank_id
                session_uuid = UUID(validation_session_id) if isinstance(validation_session_id, str) else validation_session_id
                user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
                
                # Log overlay application (if applied)
                if overlay:
                    overlay_uuid = UUID(overlay_id) if isinstance(overlay_id, str) else overlay_id
                    overlay_event = BankPolicyApplicationEvent(
                        validation_session_id=session_uuid,
                        bank_id=bank_uuid,
                        user_id=user_uuid,
                        overlay_id=overlay_uuid,
                        overlay_version=overlay_version,
                        application_type="overlay" if not exception_applications else "both",
                        discrepancies_before=discrepancies_before,
                        discrepancies_after=discrepancies_after,
                        severity_changes=severity_changes,
                        result_summary=result_summary,
                        document_type=document_data.get("document_type"),
                        processing_time_ms=processing_time_ms
                    )
                    db_session.add(overlay_event)
                
                # Log exception applications (one event per exception)
                for exc_app in exception_applications:
                    exception_uuid = UUID(exc_app["exception_id"]) if isinstance(exc_app["exception_id"], str) else exc_app["exception_id"]
                    exception_event = BankPolicyApplicationEvent(
                        validation_session_id=session_uuid,
                        bank_id=bank_uuid,
                        user_id=user_uuid,
                        overlay_id=UUID(overlay_id) if overlay_id and isinstance(overlay_id, str) else overlay_id,
                        overlay_version=overlay_version,
                        exception_id=exception_uuid,
                        application_type="exception" if not overlay else "both",
                        rule_code=exc_app["rule_code"],
                        exception_effect=exc_app["effect"],
                        discrepancies_before=discrepancies_before,
                        discrepancies_after=discrepancies_after,
                        severity_changes=severity_changes,
                        result_summary=result_summary,
                        document_type=document_data.get("document_type"),
                        processing_time_ms=processing_time_ms
                    )
                    db_session.add(exception_event)
                
                db_session.commit()
            except Exception as e:
                logger.warning(f"Failed to log policy application event: {e}", exc_info=True)
                db_session.rollback()
                # Don't fail validation if analytics logging fails
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Failed to apply bank policy: {e}", exc_info=True)
        # Don't fail validation if policy application fails
        return validation_results


def _gather_text_blob(document_data: Dict[str, Any]) -> str:
    """
    Collect relevant text fragments from the document for rule detection.
    """

    def _append_value(value: Any, parts: List[str]) -> None:
        if value is None:
            return
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                parts.append(stripped)
        elif isinstance(value, dict):
            for nested in value.values():
                _append_value(nested, parts)
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                _append_value(item, parts)
        else:
            parts.append(str(value))

    fragments: List[str] = []
    for key in ICC_TEXT_KEYS:
        _append_value(document_data.get(key), fragments)

    return " ".join(fragments)


def _gather_meta_blob(document_data: Dict[str, Any]) -> str:
    """
    Collect meta descriptors (product/instrument types) for rule inference.
    """
    fragments: List[str] = []
    for key in ICC_META_KEYS:
        value = document_data.get(key)
        if isinstance(value, str) and value.strip():
            fragments.append(value.strip())
    if document_data.get("is_standby"):
        fragments.append("standby")
    if document_data.get("is_guarantee"):
        fragments.append("guarantee")
    if document_data.get("is_collection"):
        fragments.append("collection")
    return " ".join(fragments)


def _unique_preserve(items: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


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

    documents_presence = doc_set.get("documents_presence") or {}
    for raw_key, entry in documents_presence.items():
        normalized = _normalize_doc_label(raw_key)
        if normalized:
            requirements[normalized] = requirements.get(normalized, False) or bool(entry.get("present"))

    doc_contexts = {
        "commercial_invoice": doc_set.get("invoice"),
        "bill_of_lading": doc_set.get("bill_of_lading") or doc_set.get("billOfLading"),
        "packing_list": doc_set.get("packing_list"),
        "certificate_of_origin": doc_set.get("certificate_of_origin"),
        "insurance_certificate": doc_set.get("insurance_certificate"),
        "inspection_certificate": doc_set.get("inspection_certificate"),
        "beneficiary_certificate": doc_set.get("beneficiary_certificate"),
    }
    for doc, ctx in doc_contexts.items():
        if isinstance(ctx, dict) and ctx:
            requirements[doc] = True

    for doc, keywords in DOC_KEYWORDS.items():
        if _text_contains_any(lc_text, keywords):
            requirements[doc] = True

    incoterm = (lc_context.get("incoterm") or "").upper()
    mentions_insurance = _text_contains_any(lc_text, DOC_KEYWORDS["insurance_certificate"])
    if incoterm.startswith("FOB") and not mentions_insurance:
        requirements["insurance_certificate"] = False
    else:
        requirements["insurance_certificate"] = requirements.get("insurance_certificate") or not incoterm.startswith("FOB") or mentions_insurance

    return requirements


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


def _lc_mentions_ucp(lc_context: Dict[str, Any], lc_text: str) -> bool:
    reference = str(lc_context.get("ucp_reference") or "")
    blob = f"{reference} {lc_text}".lower()
    return "ucp" in blob


def _allows_third_party_docs(additional_lower: str) -> bool:
    if "third" not in additional_lower:
        return False
    if "third party" not in additional_lower and "third-party" not in additional_lower:
        return False
    return any(token in additional_lower for token in ["allow", "accept", "permitted", "acceptable", "authorized"])


def _insurance_waived(additional_lower: str) -> bool:
    if "insurance" not in additional_lower:
        return False
    return any(
        phrase in additional_lower
        for phrase in [
            "insurance not required",
            "insurance to be covered by applicant",
            "insurance by applicant",
            "insurance at buyer",
        ]
    )


def _rule_mentions_keywords(rule: Dict[str, Any], keywords: Set[str]) -> bool:
    if not keywords:
        return False
    text_blobs: List[str] = []
    for key in ("title", "description", "message", "rule_id", "rule"):
        value = rule.get(key)
        if isinstance(value, str):
            text_blobs.append(value.lower())
    tags = rule.get("tags")
    if isinstance(tags, list):
        text_blobs.extend(str(tag).lower() for tag in tags if tag)
    combined = " ".join(text_blobs)
    return any(keyword in combined for keyword in keywords)


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


def _detect_icc_ruleset_domains(document_data: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Detect the base ICC ruleset domain and any supplement domains from document content.
    """
    text_blob = _gather_text_blob(document_data).lower()
    meta_blob = _gather_meta_blob(document_data).lower()

    hits = {
        match.group(0).lower().replace(" ", "").replace("-", "")
        for match in ICC_RULE_PATTERN.finditer(text_blob)
    }

    has_isp = any("isp98" in token for token in hits)
    has_ucp = any("ucp600" in token for token in hits) or "ucp 600" in text_blob
    has_eucp = ("eucp" in text_blob and ("2.1" in text_blob or "latest" in text_blob)) or any("eucp" in token for token in hits)
    has_urr = any("urr725" in token for token in hits)
    has_urdg = any("urdg758" in token for token in hits)
    has_urc = any("urc522" in token for token in hits)

    is_standby = bool(document_data.get("is_standby")) or "standby" in meta_blob or "sblc" in meta_blob
    is_guarantee = bool(document_data.get("is_guarantee")) or "guarantee" in meta_blob
    is_collection = bool(document_data.get("is_collection")) or "collection" in meta_blob or has_urc

    supplements: List[str] = []

    if has_isp and has_ucp:
        logger.warning("Detected both ISP98 and UCP600 references; prioritising ISP98.")

    if has_urdg and has_isp:
        logger.warning("Detected URDG text alongside ISP98; using URDG for guarantee context.")

    if has_isp:
        base_domain = "icc.isp98"
    elif has_urdg or is_guarantee:
        base_domain = "icc.urdg758"
    elif has_ucp:
        base_domain = "icc.ucp600"
    elif is_collection:
        base_domain = "icc.urc522"
    elif is_standby:
        base_domain = "icc.isp98"
    else:
        base_domain = "icc.ucp600"

    if base_domain == "icc.ucp600" and has_eucp:
        supplements.append("icc.eucp2.1")

    if has_urr:
        supplements.append("icc.urr725")

    if is_collection and base_domain != "icc.urc522":
        base_domain = "icc.urc522"

    return base_domain, _unique_preserve(supplements)


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


async def validate_document_async(document_data: Dict[str, Any], document_type: str) -> List[Dict[str, Any]]:
    """
    Async version of validate_document that supports JSON rulesets.
    
    Checks feature flag USE_JSON_RULES to determine which validation system to use.
    """
    use_json_rules = settings.USE_JSON_RULES
    
    if use_json_rules:
        # Use new JSON ruleset system
        try:
            from app.services.rules_service import get_rules_service
            
            rules_service = get_rules_service()
            
            requested_domain = document_data.get("domain")
            jurisdiction = document_data.get("jurisdiction", "global")
            extra_supplements = document_data.get("supplement_domains", []) or []

            if requested_domain and requested_domain != "icc":
                # Caller explicitly requested a non-ICC domain (e.g. customs, sanctions)
                domain_sequence = _unique_preserve(
                    [requested_domain, *[d for d in extra_supplements if isinstance(d, str)]]
                )
            else:
                # ICC flow: detect UCP/ISP/URDG/URC base + supplements (eUCP, URR, etc.)
                base_domain, detected_supplements = _detect_icc_ruleset_domains(document_data)
                domain_sequence = _unique_preserve(
                    [base_domain, *detected_supplements, *[d for d in extra_supplements if isinstance(d, str)]]
                )

            domain_sequence = [d for d in domain_sequence if isinstance(d, str) and d.strip()]
            if not domain_sequence:
                domain_sequence = ["icc.ucp600"]

            # Always try to load LCOPILOT cross-document rules alongside UCP600-based flows.
            # These are our proprietary LC cross-checks (LC vs invoice/B/L) and live in a
            # separate ruleset: domain='icc.lcopilot.crossdoc', jurisdiction='global'.
            if any(d.startswith("icc.") for d in domain_sequence):
                crossdoc_domain = "icc.lcopilot.crossdoc"
                if crossdoc_domain not in domain_sequence:
                    domain_sequence.append(crossdoc_domain)

            aggregated_rules: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
            base_metadata: Optional[Dict[str, Any]] = None

            for idx, domain_key in enumerate(domain_sequence):
                try:
                    logger.info(f"Fetching ruleset: domain={domain_key}, jurisdiction={jurisdiction}, index={idx}")
                    ruleset_data = await rules_service.get_active_ruleset(domain_key, jurisdiction)
                    logger.info(f"Successfully fetched ruleset: domain={domain_key}, rule_count={len(ruleset_data.get('rules', []))}")
                except ValueError as e:
                    logger.error(f"Failed to fetch ruleset: domain={domain_key}, jurisdiction={jurisdiction}, error={e}")
                    if idx == 0:
                        raise
                    logger.warning(f"No active ruleset found for supplement domain={domain_key}, skipping.")
                    continue

                meta = {
                    "domain": domain_key,
                    "ruleset_version": ruleset_data.get("ruleset_version"),
                    "rulebook_version": ruleset_data.get("rulebook_version"),
                }
                if idx == 0:
                    base_metadata = meta

                for rule in ruleset_data.get("rules", []) or []:
                    aggregated_rules.append((rule, meta))

            if not aggregated_rules:
                logger.warning(
                    f"No rules retrieved for document_type={document_type}, domains={domain_sequence}, jurisdiction={jurisdiction}"
                )
                return []

            filtered_rules_with_meta = [
                (rule, meta)
                for rule, meta in aggregated_rules
                if rule.get("document_type") in (None, "", document_type, "lc")
            ]

            lc_type_context = str(document_data.get("lc_type") or LCType.UNKNOWN.value).lower()
            filtered_rules_with_meta = [
                (rule, meta)
                for rule, meta in filtered_rules_with_meta
                if _rule_matches_lc_type(rule, (meta or {}).get("domain"), lc_type_context)
            ]
            filtered_rules_with_meta = activate_rules_for_lc(
                document_data.get("lc") or {},
                filtered_rules_with_meta,
                document_data,
            )

            if not filtered_rules_with_meta:
                logger.warning(
                    f"No applicable rules after filtering for document_type={document_type}, domains={domain_sequence}, jurisdiction={jurisdiction}"
                )
                return []

            evaluator = RuleEvaluator()
            prepared_rules = [rule for rule, _ in filtered_rules_with_meta]
            rule_envelopes = [
                {"rule": rule, "meta": meta}
                for rule, meta in filtered_rules_with_meta
            ]
            prepared_rules = [env["rule"] for env in rule_envelopes]
            semantic_registry: Dict[str, List[str]] = {}
            prepared_rules, semantic_registry = await _inject_semantic_conditions(
                prepared_rules,
                document_data,
                evaluator,
            )
            for idx, rule in enumerate(prepared_rules):
                rule_envelopes[idx]["rule"] = rule

            evaluation_result = await evaluator.evaluate_rules(prepared_rules, document_data)

            results: List[Dict[str, Any]] = []
            outcomes = evaluation_result.get("outcomes", [])

            for idx, outcome in enumerate(outcomes):
                if outcome.get("not_applicable", False):
                    continue

                envelope = rule_envelopes[idx] if idx < len(rule_envelopes) else {"rule": {}, "meta": base_metadata}
                rule_def = envelope.get("rule", {}) or {}
                meta = envelope.get("meta") or base_metadata or {}

                result_payload = {
                    "rule": outcome.get("rule_id", rule_def.get("rule_id", "unknown")),
                    "title": rule_def.get("title") or outcome.get("rule_id", "unknown"),
                    "description": rule_def.get("description"),
                    "article": rule_def.get("article"),
                    "tags": rule_def.get("tags"),
                    "documents": rule_def.get("documents") or rule_def.get("document_types"),
                    "display_card": rule_def.get("display_card") or rule_def.get("ui_card"),
                    "expected_outcome": rule_def.get("expected_outcome"),
                    "passed": outcome.get("passed", False),
                    "severity": outcome.get("severity", rule_def.get("severity", "warning")),
                    "message": outcome.get("message", rule_def.get("description") or ""),
                    "ruleset_version": meta.get("ruleset_version"),
                    "rulebook_version": meta.get("rulebook_version"),
                    "ruleset_domain": meta.get("domain"),
                }

                sem_keys = semantic_registry.get(result_payload["rule"], [])
                if sem_keys:
                    semantic_store = document_data.get("_semantic") or {}
                    comparisons = [
                        semantic_store.get(key)
                        for key in sem_keys
                        if semantic_store.get(key)
                    ]
                    if comparisons:
                        result_payload["semantic_differences"] = comparisons
                        primary = comparisons[0]
                        if primary.get("expected"):
                            result_payload.setdefault("expected", primary.get("expected"))
                        if primary.get("found"):
                            result_payload.setdefault("actual", primary.get("found"))
                        if primary.get("suggested_fix"):
                            result_payload.setdefault("suggestion", primary.get("suggested_fix"))
                        if not result_payload.get("documents") and primary.get("documents"):
                            result_payload["documents"] = primary.get("documents")

                results.append(result_payload)

            logger.info(
                "Evaluated %d rules using JSON ruleset system (domains=%s, jurisdiction=%s)",
                len(prepared_rules),
                domain_sequence,
                jurisdiction,
            )
            return results
            
        except ValueError as e:
            # No active ruleset found - fall back to legacy system
            logger.warning(f"JSON ruleset not available ({e}), falling back to legacy validation")
            try:
                return validate_document(document_data, document_type)
            except Exception as legacy_error:
                logger.error(f"Legacy validation also failed: {legacy_error}", exc_info=True)
                # Return empty results instead of crashing
                return []
        except Exception as e:
            logger.error(f"Error in JSON ruleset validation: {e}", exc_info=True)
            # Fall back to legacy system on error
            try:
                return validate_document(document_data, document_type)
            except Exception as legacy_error:
                logger.error(f"Legacy validation also failed: {legacy_error}", exc_info=True)
                # Return empty results instead of crashing
                return []
    else:
        # Use legacy validation system
        return validate_document(document_data, document_type)


async def _inject_semantic_conditions(
    rules: List[Dict[str, Any]],
    document_data: Dict[str, Any],
    evaluator: "RuleEvaluator",
) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    """
    Scan rules for semantic_check operators, evaluate them (AI or fallback), and
    replace with deterministic boolean checks.
    """
    if not rules:
        return rules, {}

    semantic_registry: Dict[str, List[str]] = {}
    semantic_store: Dict[str, Dict[str, Any]] = {}
    updated_rules: List[Dict[str, Any]] = []

    for rule in rules:
        working_rule = copy.deepcopy(rule)
        rule_id = working_rule.get("rule_id") or working_rule.get("rule") or "rule"
        conditions = working_rule.get("conditions") or []

        for idx, condition in enumerate(list(conditions)):
            operator = (condition.get("operator") or "").lower()
            if operator != "semantic_check":
                continue

            field_path = condition.get("field")
            left_value = evaluator.resolve_field_path(document_data, field_path) if field_path else None

            right_value = None
            if condition.get("value_ref"):
                right_value = evaluator.resolve_field_path(document_data, condition["value_ref"])
            elif condition.get("value") is not None:
                right_value = condition.get("value")

            semantic_cfg = condition.get("semantic") or {}
            context_label = semantic_cfg.get("context") or field_path or working_rule.get("title") or "cross_document"
            doc_hints = semantic_cfg.get("documents") or working_rule.get("documents") or working_rule.get("document_types") or []
            if isinstance(doc_hints, str):
                doc_hints = [doc_hints]

            comparison = await run_semantic_comparison(
                left_value,
                right_value,
                context=context_label,
                documents=doc_hints,
                threshold=semantic_cfg.get("threshold") or settings.AI_SEMANTIC_THRESHOLD_DEFAULT,
                enable_ai=semantic_cfg.get("enable_ai"),
            )

            semantic_key = f"{rule_id}:{idx}"
            semantic_store[semantic_key] = comparison
            semantic_registry.setdefault(rule_id, []).append(semantic_key)

            working_rule["conditions"][idx] = {
                "field": f"_semantic.{semantic_key}.match",
                "operator": "equals",
                "value": True,
                "message": condition.get("message"),
                "rule_type": condition.get("rule_type"),
            }

        updated_rules.append(working_rule)

    if semantic_store:
        document_data.setdefault("_semantic", {}).update(semantic_store)

    return updated_rules, semantic_registry


def validate_document(document_data: Dict[str, Any], document_type: str) -> List[Dict[str, Any]]:
    use_api = os.getenv("USE_RULHUB_API", "false").lower() == "true"
    session = SessionLocal()
    try:
        rules_source: List[Any] = []
        if use_api:
            try:
                rules_source = fetch_rules_from_rulhub(document_type)
            except Exception:
                # Fallback to local DB
                rules_source = session.query(Rule).filter(Rule.document_type == document_type).all()
        else:
            rules_source = session.query(Rule).filter(Rule.document_type == document_type).all()

        results: List[Dict[str, Any]] = []
        for rule in rules_source:
            # Support dict rules from API and ORM objects locally
            if isinstance(rule, dict):
                results.append(apply_rule_dict(rule, document_data))
            else:
                results.append(apply_rule(rule, document_data))
        return results
    finally:
        session.close()


def apply_rule(rule: Rule, doc: Dict[str, Any]) -> Dict[str, Any]:
    field = rule.condition.get("field")
    op = rule.condition.get("operator")
    val = rule.condition.get("value")
    actual = doc.get(field)

    if op == "equals":
        passed = actual == val
    elif op == "matches":
        # Interpret value as regex pattern
        try:
            passed = bool(re.match(str(val), str(actual)))
        except re.error:
            passed = False
    else:
        passed = False

    return {
        "rule": rule.code,
        "title": rule.title,
        "passed": passed,
        "severity": rule.severity,
        "message": rule.expected_outcome.get("message") if passed else rule.description,
    }


def apply_rule_dict(rule: Dict[str, Any], doc: Dict[str, Any]) -> Dict[str, Any]:
    condition = rule.get("condition", {})
    field = condition.get("field")
    op = condition.get("operator")
    val = condition.get("value")
    actual = doc.get(field)

    if op == "equals":
        passed = actual == val
    elif op == "matches":
        try:
            passed = bool(re.match(str(val), str(actual)))
        except re.error:
            passed = False
    else:
        passed = False

    return {
        "rule": rule.get("code"),
        "title": rule.get("title"),
        "passed": passed,
        "severity": rule.get("severity", "fail"),
        "message": (rule.get("expected_outcome", {}) or {}).get("message") if passed else rule.get("description"),
    }


