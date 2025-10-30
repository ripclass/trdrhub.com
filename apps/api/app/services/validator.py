from typing import Any, Dict, List
import re

from app.models.rules import Rule
from app.database import SessionLocal


def validate_document(document_data: Dict[str, Any], document_type: str) -> List[Dict[str, Any]]:
    session = SessionLocal()
    try:
        rules = session.query(Rule).filter(Rule.document_type == document_type).all()
        results = []
        for rule in rules:
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


