from __future__ import annotations

from pathlib import Path


def test_validator_prefers_requirements_graph_for_document_requirements() -> None:
    source = Path("apps/api/app/services/validator.py").read_text(encoding="utf-8")

    assert "_resolve_requirements_graph" in source
    assert "requirements_graph = _resolve_requirements_graph(lc_context, doc_set)" in source
    assert 'requirements_graph.get("required_document_types")' in source
