from __future__ import annotations

from pathlib import Path


def test_validation_execution_threads_requirements_graph_into_ai_validation_payload() -> None:
    source = Path("apps/api/app/routers/validation/validation_execution.py").read_text(encoding="utf-8")

    assert 'lc_data_for_ai["requirements_graph_v1"]' in source


def test_run_ai_validation_prefers_requirements_graph_when_present() -> None:
    source = Path("apps/api/app/services/validation/ai_validator.py").read_text(encoding="utf-8")

    assert '_parse_lc_requirements_from_graph(requirements_graph)' in source
    assert 'lc_data.get("requirements_graph_v1")' in source
