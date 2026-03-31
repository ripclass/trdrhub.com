from __future__ import annotations

from pathlib import Path


def test_validation_execution_applies_insurance_fact_graph_before_rules() -> None:
    source = Path("apps/api/app/routers/validation/validation_execution.py").read_text(encoding="utf-8")

    assert "apply_insurance_fact_graph_to_validation_inputs" in source
    assert "apply_insurance_fact_graph_to_validation_inputs(payload, extracted_context)" in source
    assert "def _resolve_insurance_rule_context(" in source
    assert "materialize_document_fact_graph_v1" in source
    assert "project_insurance_validation_context" in source
    assert 'insurance_rule_context = _resolve_insurance_rule_context(' in source
    assert '"insurance": insurance_rule_context' in source
    assert '"insurance_doc": insurance_rule_context' in source
