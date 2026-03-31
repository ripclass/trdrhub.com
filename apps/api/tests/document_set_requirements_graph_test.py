from __future__ import annotations

import ast
from pathlib import Path

CROSSDOC_VALIDATOR_PATH = Path("apps/api/app/services/validation/crossdoc_validator.py")


def _load_requirement_matcher():
    source = CROSSDOC_VALIDATOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes = []

    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_DOCUMENT_SET_REQUIREMENT_FAMILIES":
                    selected_nodes.append(node)
                    break
        elif isinstance(node, ast.FunctionDef) and node.name == "_document_requirement_is_satisfied":
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace = {"Set": set}
    exec(compile(module_ast, str(CROSSDOC_VALIDATOR_PATH), "exec"), namespace)
    return namespace["_document_requirement_is_satisfied"]


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


def test_document_requirement_matcher_treats_generic_bill_of_lading_as_ocean_requirement() -> None:
    matcher = _load_requirement_matcher()

    assert matcher("ocean_bill_of_lading", {"bill_of_lading"}) is True
    assert matcher("insurance_certificate", {"insurance_policy"}) is True
    assert matcher("ocean_bill_of_lading", {"air_waybill"}) is False
