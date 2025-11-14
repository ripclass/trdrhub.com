from typing import Any, Dict, List, Optional, Tuple
import os
import re
import logging
from datetime import datetime
from uuid import UUID

from app.models.rules import Rule
from app.database import SessionLocal
from app.services.rulhub_client import fetch_rules_from_rulhub
from app.config import settings

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
    use_json_rules = settings.USE_JSON_RULES
    
    if use_json_rules:
        # Use new JSON ruleset system
        try:
            from app.services.rules_service import get_rules_service
            from app.services.rule_evaluator import RuleEvaluator
            
            rules_service = get_rules_service()
            
            requested_domain = document_data.get("domain")
            jurisdiction = document_data.get("jurisdiction", "global")
            extra_supplements = document_data.get("supplement_domains", []) or []

            if requested_domain and requested_domain != "icc":
                domain_sequence = _unique_preserve(
                    [requested_domain, *[d for d in extra_supplements if isinstance(d, str)]]
                )
            else:
                base_domain, detected_supplements = _detect_icc_ruleset_domains(document_data)
                domain_sequence = _unique_preserve(
                    [base_domain, *detected_supplements, *[d for d in extra_supplements if isinstance(d, str)]]
                )

            domain_sequence = [d for d in domain_sequence if isinstance(d, str) and d.strip()]
            if not domain_sequence:
                domain_sequence = ["icc.ucp600"]

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

            if not filtered_rules_with_meta:
                logger.warning(
                    f"No applicable rules after filtering for document_type={document_type}, domains={domain_sequence}, jurisdiction={jurisdiction}"
                )
                return []

            evaluator = RuleEvaluator()
            prepared_rules = [rule for rule, _ in filtered_rules_with_meta]
            rule_metadata = [meta for _, meta in filtered_rules_with_meta]

            evaluation_result = await evaluator.evaluate_rules(prepared_rules, document_data)

            results: List[Dict[str, Any]] = []
            outcomes = evaluation_result.get("outcomes", [])

            for idx, outcome in enumerate(outcomes):
                if outcome.get("not_applicable", False):
                    continue

                meta = rule_metadata[idx] if idx < len(rule_metadata) else base_metadata
                results.append({
                    "rule": outcome.get("rule_id", "unknown"),
                    "title": outcome.get("title", outcome.get("rule_id", "unknown")),
                    "passed": outcome.get("passed", False),
                    "severity": outcome.get("severity", "warning"),
                    "message": outcome.get("message", ""),
                    "ruleset_version": (meta or {}).get("ruleset_version"),
                    "rulebook_version": (meta or {}).get("rulebook_version"),
                    "ruleset_domain": (meta or {}).get("domain"),
                })

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


