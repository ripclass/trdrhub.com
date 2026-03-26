from __future__ import annotations

from pathlib import Path


def test_session_setup_projects_lc_fact_graph_before_gate_inputs_are_frozen() -> None:
    source = Path("apps/api/app/routers/validation/session_setup.py").read_text(encoding="utf-8")

    assert "materialize_document_fact_graphs_v1(document_details)" in source
    assert "projected_lc = apply_lc_fact_graph_to_validation_inputs(payload, extracted_context)" in source
    assert 'payload["lc"] = projected_lc' in source
    assert 'extracted_context["lc"] = payload["lc"]' in source


def test_lc_baseline_can_recover_critical_fields_from_fact_graph_v1() -> None:
    source = Path("apps/api/app/routers/validate.py").read_text(encoding="utf-8-sig")

    assert 'fact_graph = (' in source
    assert 'def _fact_graph_value(field_name: str) -> Any:' in source
    assert 'lc_number = _fact_graph_value("lc_number")' in source
    assert 'applicant = _fact_graph_value("applicant")' in source
    assert 'beneficiary = _fact_graph_value("beneficiary")' in source
    assert 'fact_amount = _fact_graph_value("amount")' in source
    assert 'fact_currency = _fact_graph_value("currency")' in source


def test_validation_execution_updates_setup_state_with_projected_lc_context() -> None:
    source = Path("apps/api/app/routers/validation/validation_execution.py").read_text(encoding="utf-8")

    assert 'lc_context = apply_lc_fact_graph_to_validation_inputs(payload, extracted_context)' in source
    assert 'setup_state["lc_context"] = lc_context' in source
