from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

os.environ["DEBUG"] = "false"

from app.services.rules_importer import RulesImporter  # noqa: E402


def test_create_rule_model_bridges_staged_runtime_fields_into_metadata() -> None:
    importer = RulesImporter(db=None)
    ruleset = SimpleNamespace(
        rulebook_version="UCP600:2007",
        ruleset_version="1.0.2",
        domain="icc.ucp600",
        jurisdiction="global",
    )
    data = {
        "rule_id": "UCP600-28A",
        "title": "Insurance Document: Originals Must Be Presented",
        "document_type": "lc",
        "conditions": [
            {
                "type": "amount_comparison",
                "field": "insurance_doc.originals_presented",
                "operator": "less_than",
                "reference_field": "insurance_doc.originals_issued",
            }
        ],
        "metadata": {"ruleset_source": "RuleEngine Core"},
        "consequence_class": "insurance_doc_discrepancy",
        "execution_priority": "primary",
        "parent_rule": "UCP600-28",
        "suppression_policy": "suppress_when_child_fires",
    }

    model = importer._create_rule_model(
        data=data,
        ruleset_id="00000000-0000-0000-0000-000000000000",
        activate=True,
        ruleset=ruleset,
    )

    assert model.rule_metadata["ruleset_source"] == "RuleEngine Core"
    assert model.rule_metadata["consequence_class"] == "insurance_doc_discrepancy"
    assert model.rule_metadata["execution_priority"] == "primary"
    assert model.rule_metadata["parent_rule"] == "UCP600-28"
    assert model.rule_metadata["suppression_policy"] == "suppress_when_child_fires"


def test_update_rule_model_bridges_staged_runtime_fields_into_metadata() -> None:
    importer = RulesImporter(db=None)
    ruleset = SimpleNamespace(
        rulebook_version="UCP600:2007",
        ruleset_version="1.0.2",
        domain="icc.ucp600",
        jurisdiction="global",
    )
    existing = importer._create_rule_model(
        data={
            "rule_id": "UCP600-28A",
            "title": "Insurance Document: Originals Must Be Presented",
            "document_type": "lc",
            "metadata": {"ruleset_source": "RuleEngine Core"},
        },
        ruleset_id="00000000-0000-0000-0000-000000000000",
        activate=True,
        ruleset=ruleset,
    )

    importer._update_rule_model(
        existing,
        {
            "rule_id": "UCP600-28A",
            "title": "Insurance Document: Originals Must Be Presented",
            "document_type": "lc",
            "metadata": {"ruleset_source": "RuleEngine Core"},
            "consequence_class": "insurance_doc_discrepancy",
            "execution_priority": "primary",
            "parent_rule": "UCP600-28",
        },
        "00000000-0000-0000-0000-000000000000",
    )

    assert existing.rule_metadata["consequence_class"] == "insurance_doc_discrepancy"
    assert existing.rule_metadata["execution_priority"] == "primary"
    assert existing.rule_metadata["parent_rule"] == "UCP600-28"
