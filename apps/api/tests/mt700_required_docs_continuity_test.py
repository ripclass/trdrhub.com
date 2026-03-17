from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = ROOT / "app" / "routers" / "validate.py"
LC_TAXONOMY_PATH = ROOT / "app" / "services" / "extraction" / "lc_taxonomy.py"
STRUCTURED_BUILDER_PATH = ROOT / "app" / "services" / "extraction" / "structured_lc_builder.py"


def _load_lc_taxonomy_module():
    spec = importlib.util.spec_from_file_location("lc_taxonomy_mt700_test", LC_TAXONOMY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load lc_taxonomy module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_structured_builder_module():
    spec = importlib.util.spec_from_file_location("structured_lc_builder_mt700_test", STRUCTURED_BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load structured_lc_builder module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_validate_required_doc_symbols() -> Dict[str, Any]:
    source = VALIDATE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    target_functions = {
        "_parse_json_if_possible",
        "_coerce_text_list",
        "_infer_required_document_types_from_lc",
        "_prepare_extractor_outputs_for_structured_result",
    }

    selected_nodes: List[ast.AST] = []
    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_DOC_REQUIREMENT_HINTS":
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
        "Tuple": Tuple,
        "json": json,
        "normalize_required_documents": taxonomy.normalize_required_documents,
        "_resolve_legacy_workflow_lc_fields": lambda context, payload=None: {
            "lc_type": "unknown",
            "lc_type_reason": "stub",
            "lc_type_confidence": 0.0,
            "lc_type_source": "stub",
        },
    }
    exec(compile(module_ast, str(VALIDATE_PATH), "exec"), namespace)
    return namespace


def test_validate_inference_keeps_compact_mt700_required_doc_tokens_consistent():
    ns = _load_validate_required_doc_symbols()
    infer_required_document_types = ns["_infer_required_document_types_from_lc"]
    required_codes = infer_required_document_types(
        {"documents_required": ["INVOICE/BL/PL/COO/INSURANCE"]}
    )
    assert "commercial_invoice" in required_codes
    assert "bill_of_lading" in required_codes
    assert "packing_list" in required_codes
    assert "certificate_of_origin" in required_codes
    assert "insurance_certificate" in required_codes
    assert "other_specified_document" not in required_codes


def test_prepare_extractor_outputs_rebuilds_classification_after_required_doc_backfill():
    ns = _load_validate_required_doc_symbols()
    prepare_structured = ns["_prepare_extractor_outputs_for_structured_result"]
    ns["build_lc_classification"] = (
        lambda source, payload=None: {
            "required_documents": [
                {"code": code}
                for code in sorted(
                    {
                        str(code).strip().lower()
                        for code in source.get("required_document_types", [])
                        if str(code).strip()
                    }
                )
            ]
        }
    )
    payload = {
        "lc_structured_output": {
            "lc_classification": {
                "required_documents": [{"code": "other_specified_document"}]
            }
        },
        "lc": {"documents_required": ["INVOICE/BL/PL/COO/INSURANCE"]},
    }

    merged = prepare_structured(payload)
    required_codes = {
        str(item.get("code")).strip().lower()
        for item in merged["lc_classification"]["required_documents"]
        if isinstance(item, dict)
    }
    assert "commercial_invoice" in required_codes
    assert "bill_of_lading" in required_codes
    assert "packing_list" in required_codes
    assert "certificate_of_origin" in required_codes
    assert "insurance_certificate" in required_codes
    assert "other_specified_document" not in required_codes


def test_structured_builder_preserves_mt700_blocks_from_raw_text_when_sparse():
    structured_builder = _load_structured_builder_module()
    build_unified_structured_result = structured_builder.build_unified_structured_result
    extractor_outputs = {
        "mt700": {
            "blocks": {
                "27": None,
                "31C": None,
                "40E": None,
                "32B": None,
                "41A": None,
                "41D": None,
                "44A": None,
                "44B": None,
                "44C": None,
                "44D": None,
                "44E": None,
                "44F": None,
                "45A": None,
                "46A": None,
                "47A": None,
                "71B": None,
                "78": None,
                "50": None,
                "59": None,
            },
            "raw_text": (
                ":20:100924060096\n"
                ":31C:20260308\n"
                ":46A:INVOICE/BL/PL/COO/INSURANCE\n"
                ":47A:ADDITIONAL CONDITIONS APPLY\n"
            ),
            "version": "mt700_v1",
        },
        "documents_required": ["INVOICE", "BL", "PL", "COO", "INSURANCE"],
        "required_document_types": [
            "commercial_invoice",
            "bill_of_lading",
            "packing_list",
            "certificate_of_origin",
            "insurance_certificate",
        ],
    }
    result = build_unified_structured_result([], extractor_outputs, None)
    mt700 = result["structured_result"]["lc_structured"]["mt700"]
    blocks = mt700["blocks"]

    assert mt700["raw_text"]
    assert blocks["46A"] == "INVOICE/BL/PL/COO/INSURANCE"
    assert blocks["47A"] == "ADDITIONAL CONDITIONS APPLY"
    assert blocks["31C"] == "20260308"
