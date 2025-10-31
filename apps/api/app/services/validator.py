from typing import Any, Dict, List
import os
import re

from app.models.rules import Rule
from app.database import SessionLocal
from app.services.rulhub_client import fetch_rules_from_rulhub


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


