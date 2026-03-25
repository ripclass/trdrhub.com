from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "app" / "services" / "validator.py"
LC_TAXONOMY_PATH = ROOT / "app" / "services" / "extraction" / "lc_taxonomy.py"


def _load_lc_taxonomy_module():
    spec = importlib.util.spec_from_file_location("lc_taxonomy_validator_requirements_test", LC_TAXONOMY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load lc_taxonomy module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_validator_requirement_symbols() -> Dict[str, Any]:
    source = VALIDATOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    target_assignments = {
        "DOC_KEYWORDS",
        "DOC_SYNONYMS",
        "REQUIREMENTS_GRAPH_TRANSPORT_TYPES",
        "REQUIREMENTS_GRAPH_INVOICE_TYPES",
        "REQUIREMENTS_GRAPH_INSURANCE_TYPES",
    }
    target_functions = {
        "_get_lc_classification",
        "_normalize_doc_label",
        "_text_contains_any",
        "_extract_requested_documents",
        "_fallback_documents_from_payload",
        "_resolve_requirements_graph",
        "_infer_document_requirements",
    }

    selected_nodes: List[ast.AST] = []
    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in target_assignments:
                    selected_nodes.append(node)
                    break
        if isinstance(node, ast.FunctionDef) and node.name in target_functions:
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    taxonomy = _load_lc_taxonomy_module()
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Set": Set,
        "re": __import__("re"),
        "build_lc_classification": taxonomy.build_lc_classification,
    }
    exec(compile(module_ast, str(VALIDATOR_PATH), "exec"), namespace)
    return namespace


def test_infer_document_requirements_prefers_requirements_graph_v1() -> None:
    ns = _load_validator_requirement_symbols()
    infer_document_requirements = ns["_infer_document_requirements"]
    requirements = infer_document_requirements(
        {"requirements_graph_v1": {"required_document_types": ["commercial_invoice", "air_waybill", "insurance_policy"]}},
        "",
        {},
    )

    assert requirements["lc"] is True
    assert requirements["commercial_invoice"] is True
    assert requirements["bill_of_lading"] is True
    assert requirements["insurance_certificate"] is True
    assert requirements["packing_list"] is False
    assert requirements["certificate_of_origin"] is False


def test_infer_document_requirements_falls_back_when_graph_missing() -> None:
    ns = _load_validator_requirement_symbols()
    infer_document_requirements = ns["_infer_document_requirements"]
    requirements = infer_document_requirements(
        {"documents_required": ["INVOICE/PL/COO"]},
        "invoice packing list certificate of origin",
        {},
    )

    assert requirements["commercial_invoice"] is True
    assert requirements["packing_list"] is True
    assert requirements["certificate_of_origin"] is True
    assert requirements["bill_of_lading"] is False


def test_infer_document_requirements_reads_graph_from_extracted_context_documents() -> None:
    ns = _load_validator_requirement_symbols()
    infer_document_requirements = ns["_infer_document_requirements"]
    requirements = infer_document_requirements(
        {},
        "",
        {
            "extracted_context": {
                "documents": [
                    {
                        "document_type": "letter_of_credit",
                        "requirements_graph_v1": {
                            "required_document_types": ["packing_list", "certificate_of_origin"],
                        },
                    }
                ]
            }
        },
    )

    assert requirements["packing_list"] is True
    assert requirements["certificate_of_origin"] is True
    assert requirements["commercial_invoice"] is False
