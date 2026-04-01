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


def test_lc_ops_amount_comparison_reference_field_triggers_discrepancy() -> None:
    evaluator = RuleEvaluator()

    rule = {
        "rule_id": "UCP600-28A",
        "title": "Insurance Document: Originals Must Be Presented",
        "domain": "lc_ops",
        "consequence_class": "insurance_doc_discrepancy",
        "conditions": [
            {
                "field": "insurance_doc.originals_presented",
                "operator": "less_than",
                "reference_field": "insurance_doc.originals_issued",
                "type": "amount_comparison",
            }
        ],
        "expected_outcome": {
            "valid": ["Presentation complies"],
            "invalid": [
                "Not all issued originals of the insurance document presented.",
                "Remediation: Require all originals.",
            ],
        },
    }
    context = {
        "insurance_doc": {
            "originals_presented": 1,
            "originals_issued": 2,
        }
    }

    outcome = evaluator.evaluate_rule(rule, context)

    assert outcome["passed"] is False
    assert outcome["not_applicable"] is False
    assert "Not all issued originals" in outcome["message"]


def test_lc_ops_letter_rule_defaults_to_discrepancy_trigger_without_consequence_class() -> None:
    evaluator = RuleEvaluator()

    rule = {
        "rule_id": "UCP600-28A",
        "title": "Insurance Document: Originals Must Be Presented",
        "domain": "lc_ops",
        "rule_type": "letter",
        "conditions": [
            {
                "field": "insurance_doc.originals_presented",
                "operator": "less_than",
                "reference_field": "insurance_doc.originals_issued",
                "type": "amount_comparison",
            }
        ],
        "expected_outcome": {
            "valid": ["Presentation complies"],
            "invalid": ["Not all issued originals of the insurance document presented."],
        },
    }
    context = {
        "insurance_doc": {
            "originals_presented": 1,
            "originals_issued": 2,
        }
    }

    outcome = evaluator.evaluate_rule(rule, context)

    assert outcome["passed"] is False
    assert outcome["not_applicable"] is False
    assert "Not all issued originals" in outcome["message"]


def test_lc_ops_field_match_reference_field_uses_discrepancy_trigger_semantics() -> None:
    evaluator = RuleEvaluator()

    rule = {
        "rule_id": "UCP600-18A",
        "title": "Commercial Invoice: Issuer Must Be the Beneficiary",
        "domain": "lc_ops",
        "consequence_class": "invoice_discrepancy",
        "conditions": [
            {
                "field": "invoice.issuer_name",
                "operator": "not_equals",
                "reference_field": "lc.beneficiary_name",
                "type": "field_match",
            },
            {
                "field": "lc.is_transferred",
                "operator": "equals",
                "value": False,
                "type": "field_match",
            },
        ],
        "expected_outcome": {
            "valid": ["Presentation complies"],
            "invalid": ["Commercial invoice not issued by the LC beneficiary."],
        },
    }

    mismatch_context = {
        "invoice": {"issuer_name": "Other Exporter Ltd"},
        "lc": {"beneficiary_name": "Bangladesh Export Ltd", "is_transferred": False},
    }
    compliant_context = {
        "invoice": {"issuer_name": "Bangladesh Export Ltd"},
        "lc": {"beneficiary_name": "Bangladesh Export Ltd", "is_transferred": False},
    }

    mismatch_outcome = evaluator.evaluate_rule(rule, mismatch_context)
    compliant_outcome = evaluator.evaluate_rule(rule, compliant_context)

    assert mismatch_outcome["passed"] is False
    assert compliant_outcome["passed"] is True


def test_lc_ops_date_comparison_supports_computed_banking_day_reference() -> None:
    evaluator = RuleEvaluator()

    rule = {
        "rule_id": "UCP600-14A",
        "title": "Examination Deadline: Maximum 5 Banking Days",
        "domain": "lc_ops",
        "consequence_class": "examination_period_violation",
        "conditions": [
            {
                "field": "examination.decision_date",
                "operator": "greater_than",
                "computed_field": "presentation.date + 5 banking_days",
                "type": "date_comparison",
            }
        ],
        "expected_outcome": {
            "valid": ["Presentation complies"],
            "invalid": ["Examination decision issued after the maximum 5 banking-day limit."],
        },
    }
    context = {
        "presentation": {"date": "2026-03-02"},
        "examination": {"decision_date": "2026-03-10"},
    }

    outcome = evaluator.evaluate_rule(rule, context)

    assert outcome["passed"] is False
    assert "maximum 5 banking-day limit" in outcome["message"]


def test_narrative_singleton_conditions_are_skipped_not_failed() -> None:
    evaluator = RuleEvaluator()

    rule = {
        "rule_id": "ISBP745-A1",
        "title": "Abbreviations",
        "domain": "icc",
        "consequence_class": "domain_logic",
        "conditions": [
            {
                "type": "document_content",
                "rule": "Generally accepted abbreviations are acceptable in place of full words and vice versa.",
            }
        ],
    }

    outcome = evaluator.evaluate_rule(rule, {})

    assert outcome["passed"] is True
    assert outcome["not_applicable"] is True
    assert "non-evaluable" in outcome["message"].lower()
