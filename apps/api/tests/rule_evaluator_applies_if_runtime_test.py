from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

os.environ["DEBUG"] = "false"

from app.services.rule_evaluator import RuleEvaluator  # noqa: E402


def test_rule_evaluator_handles_applies_if_with_indexed_preconditions() -> None:
    evaluator = RuleEvaluator()

    rule = {
        "rule_id": "UCP600-28A",
        "title": "Insurance Originals Match LC Requirement",
        "applies_if": [
            {
                "field": "lc.requirements_structured_v1.toggles.insurance_required",
                "operator": "equals",
                "value": True,
            }
        ],
        "conditions": [
            {"field": "insurance_doc.originals_presented", "operator": "exists"},
            {
                "field": "insurance_doc.originals_presented",
                "operator": "greater_than_or_equal",
                "value_ref": "lc.requirements_structured_v1.document_quantities.insurance_certificate.originals_required",
            },
        ],
    }
    context = {
        "lc": {
            "requirements_structured_v1": {
                "toggles": {"insurance_required": True},
                "document_quantities": {
                    "insurance_certificate": {"originals_required": 2}
                },
            }
        },
        "insurance_doc": {"originals_presented": 1},
    }

    outcome = evaluator.evaluate_rule(rule, context)

    assert outcome["rule_id"] == "UCP600-28A"
    assert outcome["passed"] is False
    assert "Evaluation error" not in str(outcome.get("message") or "")
    assert any(
        violation.get("field") == "insurance_doc.originals_presented"
        for violation in outcome.get("violations") or []
    )
