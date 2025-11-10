from typing import Any, Dict, List, Optional
import os
import re
import logging
from datetime import datetime
from uuid import UUID

from app.models.rules import Rule
from app.database import SessionLocal
from app.services.rulhub_client import fetch_rules_from_rulhub

logger = logging.getLogger(__name__)


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
    db_session
) -> List[Dict[str, Any]]:
    """
    Apply bank policy overlay and exceptions to validation results.
    
    This function:
    1. Loads active overlay for the bank
    2. Applies stricter checks from overlay
    3. Loads active exceptions
    4. Applies exceptions to matching failed rules
    
    Returns:
        Modified validation results with policy overlays/exceptions applied
    """
    if not bank_id:
        return validation_results
    
    try:
        # Load overlay
        overlay = get_active_overlay(bank_id, db_session)
        
        # Apply overlay stricter checks
        if overlay:
            validation_results = apply_policy_overlay(validation_results, overlay, document_data)
        
        # Load exceptions
        exceptions = get_active_exceptions(bank_id, db_session)
        
        # Apply exceptions
        if exceptions:
            validation_results = apply_policy_exceptions(validation_results, exceptions, document_data)
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Failed to apply bank policy: {e}", exc_info=True)
        # Don't fail validation if policy application fails
        return validation_results


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
    use_json_rules = os.getenv("USE_JSON_RULES", "false").lower() == "true"
    
    if use_json_rules:
        # Use new JSON ruleset system
        try:
            from app.services.rules_service import get_rules_service
            from app.services.rule_evaluator import RuleEvaluator
            
            rules_service = get_rules_service()
            
            # Determine domain and jurisdiction from document or use defaults
            # For LC documents, typically use ICC domain
            domain = document_data.get("domain", "icc")
            jurisdiction = document_data.get("jurisdiction", "global")
            
            # Fetch active ruleset
            ruleset_data = await rules_service.get_active_ruleset(domain, jurisdiction)
            rules = ruleset_data.get("rules", [])
            
            # Filter rules by document_type
            filtered_rules = [
                rule for rule in rules
                if rule.get("document_type") == document_type or rule.get("document_type") == "lc"
            ]
            
            if not filtered_rules:
                logger.warning(f"No rules found for document_type={document_type}, domain={domain}, jurisdiction={jurisdiction}")
                return []
            
            # Evaluate rules
            evaluator = RuleEvaluator()
            evaluation_result = await evaluator.evaluate_rules(filtered_rules, document_data)
            
            # Convert to legacy format for compatibility
            results = []
            for outcome in evaluation_result.get("outcomes", []):
                if outcome.get("not_applicable", False):
                    continue  # Skip not applicable rules
                
                results.append({
                    "rule": outcome.get("rule_id", "unknown"),
                    "title": outcome.get("title", outcome.get("rule_id", "unknown")),
                    "passed": outcome.get("passed", False),
                    "severity": outcome.get("severity", "warning"),
                    "message": outcome.get("message", ""),
                    "ruleset_version": ruleset_data.get("ruleset_version"),
                    "rulebook_version": ruleset_data.get("rulebook_version"),
                })
            
            logger.info(f"Evaluated {len(filtered_rules)} rules using JSON ruleset system (version: {ruleset_data.get('ruleset_version')})")
            return results
            
        except ValueError as e:
            # No active ruleset found - fall back to legacy system
            logger.warning(f"JSON ruleset not available ({e}), falling back to legacy validation")
            return validate_document(document_data, document_type)
        except Exception as e:
            logger.error(f"Error in JSON ruleset validation: {e}", exc_info=True)
            # Fall back to legacy system on error
            return validate_document(document_data, document_type)
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


