from __future__ import annotations

from pathlib import Path


def test_document_set_validator_prefers_requirements_graph_for_required_documents() -> None:
    source = Path("apps/api/app/services/validation/crossdoc_validator.py").read_text(
        encoding="utf-8"
    )

    assert '_required_document_types_from_graph(requirements_graph)' in source
    assert 'self.lc_terms.get("requirements_graph_v1")' in source
    assert 'self.required_docs.update(required_from_graph)' in source
    assert 'if required_from_graph:' in source


def test_result_finalization_threads_requirements_graph_into_document_set_completeness() -> None:
    source = Path("apps/api/app/routers/validation/result_finalization.py").read_text(
        encoding="utf-8"
    )

    assert 'requirements_graph_v1 = structured_result.get("requirements_graph_v1")' in source
    assert 'payload.get("documents")' in source
    assert 'requirements_graph_v1 = _response_shaping.build_requirements_graph_v1(' in source
    assert 'structured_result["requirements_graph_v1"] = requirements_graph_v1' in source
    assert 'lc_terms["requirements_graph_v1"] = requirements_graph_v1' in source
