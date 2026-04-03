from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services import crossdoc as crossdoc_module  # noqa: E402


def test_issue_card_marks_late_shipment_failures_as_critical() -> None:
    cards, references = crossdoc_module.build_issue_cards(
        [
            {
                "rule": "UCP600-20C",
                "title": "Bill of Lading: Shipment Date Must Not Exceed LC Latest Shipment Date",
                "description": "B/L shipment date is later than LC latest shipment date.",
                "severity": "fail",
                "ruleset_domain": "icc.ucp600",
                "rule_type": "letter",
                "consequence_class": "bill_of_lading_discrepancy",
                "execution_priority": "primary",
                "parent_rule": "UCP600-20",
                "display_card": True,
                "conditions": [
                    {
                        "field": "bill_of_lading.on_board_date",
                        "operator": "greater_than",
                        "reference_field": "lc.latest_shipment_date",
                        "type": "date_comparison",
                    }
                ],
                "expected_outcome": {
                    "invalid": [
                        "Late shipment discrepancy.",
                    ]
                },
            }
        ]
    )

    assert references == []
    assert cards[0]["severity"] == "critical"
    assert cards[0]["ruleset_domain"] == "icc.ucp600"
    assert cards[0]["consequence_class"] == "bill_of_lading_discrepancy"
    assert cards[0]["conditions"][0]["type"] == "date_comparison"


def test_issue_card_keeps_non_temporal_failures_at_review_grade() -> None:
    cards, references = crossdoc_module.build_issue_cards(
        [
            {
                "rule": "UCP600-28E",
                "title": "Insurance Document: Minimum 110% of Invoice Value Required",
                "description": "Insurance coverage is below minimum 110% of invoice/CIF value.",
                "severity": "fail",
                "ruleset_domain": "icc.ucp600",
                "rule_type": "letter",
                "consequence_class": "insurance_doc_discrepancy",
                "execution_priority": "primary",
                "parent_rule": "UCP600-28",
                "display_card": True,
                "conditions": [
                    {
                        "field": "insurance_doc.insured_amount",
                        "operator": "less_than",
                        "computed_field": "invoice.cif_amount * 1.10",
                        "type": "amount_comparison",
                    }
                ],
            }
        ]
    )

    assert references == []
    assert cards[0]["severity"] == "major"
    assert cards[0]["ruleset_domain"] == "icc.ucp600"
    assert cards[0]["consequence_class"] == "insurance_doc_discrepancy"
