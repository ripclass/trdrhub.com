from __future__ import annotations

from pathlib import Path


def test_crossdoc_validator_prefers_requirements_graph_for_47a_conditions() -> None:
    source = Path("apps/api/app/services/validation/crossdoc_validator.py").read_text(encoding="utf-8")

    assert "_condition_texts_from_graph" in source
    assert "_identifier_requirements_from_graph" in source
    assert 'lc_data.get("requirements_graph_v1")' in source
    assert "_condition_texts_from_graph(requirements_graph)" in source
    assert 'for key in ("documentary_conditions", "ambiguous_conditions")' in source
    assert 'requirements_graph.get("condition_requirements")' in source


def test_validation_execution_threads_requirements_graph_into_crossdoc_context() -> None:
    source = Path("apps/api/app/routers/validation/validation_execution.py").read_text(encoding="utf-8")

    assert "context={" in source
    assert '"requirements_graph_v1": requirements_graph_v1' in source
