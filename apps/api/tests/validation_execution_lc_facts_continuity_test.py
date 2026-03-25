from __future__ import annotations

from pathlib import Path


def test_validation_execution_applies_lc_fact_graph_before_baseline_build() -> None:
    source = Path("apps/api/app/routers/validation/validation_execution.py").read_text(encoding="utf-8")

    assert "apply_lc_fact_graph_to_validation_inputs" in source
    assert "lc_context = apply_lc_fact_graph_to_validation_inputs(payload, extracted_context)" in source
    assert source.index("apply_lc_fact_graph_to_validation_inputs") < source.index("_build_lc_baseline_from_context")


def test_validation_execution_threads_requirements_graph_into_db_rule_payload() -> None:
    source = Path("apps/api/app/routers/validation/validation_execution.py").read_text(encoding="utf-8")

    assert '_response_shaping.build_requirements_graph_v1(' in source
    assert '"requirements_graph_v1": requirements_graph_v1' in source
