from __future__ import annotations

from pathlib import Path


def test_build_lc_baseline_uses_requirements_graph_for_required_documents_when_legacy_fields_are_absent() -> None:
    source = Path("apps/api/app/routers/validate.py").read_text(encoding="utf-8-sig")

    assert 'requirements_graph = (' in source
    assert 'documents_required = requirements_graph.get("required_documents")' in source
    assert 'documents_required = requirements_graph.get("required_document_types")' in source


def test_build_lc_baseline_uses_requirements_graph_conditions_when_47a_text_is_missing() -> None:
    source = Path("apps/api/app/routers/validate.py").read_text(encoding="utf-8-sig")

    assert 'graph_documentary_conditions = [' in source
    assert 'requirements_graph.get("documentary_conditions")' in source
    assert 'requirements_graph.get("ambiguous_conditions")' in source
    assert 'additional_conditions = graph_conditions' in source
