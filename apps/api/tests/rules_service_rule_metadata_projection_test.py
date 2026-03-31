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

from app.services.rules_service import DBRulesAdapter  # noqa: E402


def test_normalize_rule_record_projects_runtime_metadata_to_top_level() -> None:
    service = DBRulesAdapter()
    record = SimpleNamespace(
        rule_id="UCP600-28A",
        rule_version="1.0",
        article="28",
        version="UCP600:2007",
        domain="icc.ucp600",
        jurisdiction="global",
        document_type="lc",
        rule_type="letter",
        severity="fail",
        deterministic=True,
        requires_llm=False,
        title="Insurance Document: Originals Must Be Presented",
        reference=None,
        description="Insurance originals discrepancy",
        conditions=[{"field": "insurance_doc.originals_presented"}],
        expected_outcome={"invalid": ["Not all originals presented."]},
        tags=["ucp600", "insurance"],
        rule_metadata={
            "consequence_class": "insurance_doc_discrepancy",
            "execution_priority": "primary",
            "parent_rule": "UCP600-28",
            "suppression_policy": "suppress_when_child_fires",
            "applies_if": [{"field": "insurance_doc.originals_issued", "operator": "exists"}],
        },
        checksum="abc123",
        ruleset_id=None,
        ruleset_version="1.0.2",
    )

    payload = service._normalize_rule_record(record)

    assert payload["consequence_class"] == "insurance_doc_discrepancy"
    assert payload["execution_priority"] == "primary"
    assert payload["parent_rule"] == "UCP600-28"
    assert payload["suppression_policy"] == "suppress_when_child_fires"
    assert payload["applies_if"] == [{"field": "insurance_doc.originals_issued", "operator": "exists"}]
