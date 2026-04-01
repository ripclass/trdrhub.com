from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_EXECUTION_PATH = ROOT / "app" / "routers" / "validation" / "validation_execution.py"


def test_db_rule_issue_conversion_preserves_icc_precedence_metadata() -> None:
    source = VALIDATION_EXECUTION_PATH.read_text(encoding="utf-8")

    assert '"rule_type": issue_dict.get("rule_type")' in source
    assert '"consequence_class": issue_dict.get("consequence_class")' in source
    assert '"execution_priority": issue_dict.get("execution_priority")' in source
    assert '"parent_rule": issue_dict.get("parent_rule")' in source
    assert '"has_specific_family_rules": issue_dict.get("has_specific_family_rules")' in source
