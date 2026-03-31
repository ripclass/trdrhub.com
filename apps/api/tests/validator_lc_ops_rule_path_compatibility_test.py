from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

os.environ["DEBUG"] = "false"

from app.services import validator as validator_module  # noqa: E402


def test_extract_rule_field_paths_includes_reference_and_computed_fields() -> None:
    rule = {
        "conditions": [
            {
                "field": "insurance_doc.originals_presented",
                "reference_field": "insurance_doc.originals_issued",
                "computed_field": "presentation.date + 5 banking_days",
                "type": "amount_comparison",
            }
        ]
    }

    paths = validator_module._extract_rule_field_paths(rule)

    assert "insurance_doc.originals_presented" in paths
    assert "insurance_doc.originals_issued" in paths
    assert "presentation.date + 5 banking_days" in paths


def test_rule_targets_documents_understands_insurance_doc_alias() -> None:
    rule = {
        "conditions": [
            {
                "field": "insurance_doc.originals_presented",
                "reference_field": "insurance_doc.originals_issued",
                "type": "amount_comparison",
            }
        ]
    }

    targets = validator_module._rule_targets_documents(rule)

    assert targets == {"insurance_certificate"}
