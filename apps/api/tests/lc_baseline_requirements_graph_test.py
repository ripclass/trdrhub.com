from __future__ import annotations

from pathlib import Path


def test_build_lc_baseline_uses_requirements_graph_for_required_documents_when_legacy_fields_are_absent() -> None:
    source = Path("apps/api/app/routers/validate.py").read_text(encoding="utf-8-sig")

    assert "def _graph_required_document_texts() -> List[str]:" in source
    assert 'graph_required_documents = _graph_required_document_texts()' in source
    assert 'requirements_graph = (' in source
    assert 'documents_required = graph_required_documents or requirements_graph.get("required_documents")' in source
    assert 'documents_required = requirements_graph.get("required_document_types")' in source


def test_build_lc_baseline_uses_requirements_graph_conditions_when_47a_text_is_missing() -> None:
    source = Path("apps/api/app/routers/validate.py").read_text(encoding="utf-8-sig")

    assert "def _graph_condition_requirement_texts() -> List[str]:" in source
    assert 'requirement_type == "document_quantity"' in source
    assert 'requirement_type == "document_exact_wording"' in source
    assert 'graph_structured_condition_texts = _graph_condition_requirement_texts()' in source
    assert 'graph_documentary_conditions + graph_ambiguous_conditions + graph_structured_condition_texts' in source
    assert 'graph_documentary_conditions = [' in source
    assert 'requirements_graph.get("documentary_conditions")' in source
    assert 'requirements_graph.get("ambiguous_conditions")' in source
    assert 'additional_conditions = graph_conditions' in source
