from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "app" / "routers" / "validation" / "response_shaping.py"


def _load_symbols() -> Dict[str, Any]:
    source = MODULE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef)
        and node.name
        in {
            "_uses_fact_resolution_contract",
            "_is_legacy_extraction_review_reason",
            "_has_runtime_extraction_review_signal",
            "sanitize_public_document_contract_v1",
        }
    ]
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
    }
    exec(compile(module_ast, str(MODULE_PATH), "exec"), namespace)
    return namespace


def test_sanitize_public_document_contract_preserves_runtime_review_required_from_severe_artifacts() -> None:
    symbols = _load_symbols()
    sanitize = symbols["sanitize_public_document_contract_v1"]

    document = {
        "document_type": "commercial_invoice",
        "review_required": True,
        "review_reasons": [],
        "status": "warning",
        "extraction_status": "partial",
        "critical_field_states": {
            "issue_date": "missing",
            "issuer": "missing",
        },
        "extraction_artifacts_v1": {
            "selected_stage": "binary_metadata_scrape",
            "canonical_reason_codes": [
                "FIELD_NOT_FOUND",
                "OCR_AUTH_ERROR",
                "OCR_EMPTY_RESULT",
            ],
        },
        "fact_graph_v1": {
            "version": "fact_graph_v1",
            "document_type": "commercial_invoice",
            "facts": [],
        },
    }

    sanitized = sanitize(document)

    assert sanitized["review_required"] is True
    assert sanitized["reviewRequired"] is True
    assert sanitized["review_reasons"] == []
    assert sanitized["reviewReasons"] == []


def test_sanitize_public_document_contract_keeps_clean_fact_resolution_docs_not_review_required() -> None:
    symbols = _load_symbols()
    sanitize = symbols["sanitize_public_document_contract_v1"]

    document = {
        "document_type": "commercial_invoice",
        "review_required": False,
        "review_reasons": [],
        "status": "success",
        "extraction_status": "success",
        "critical_field_states": {
            "issue_date": "found",
            "issuer": "found",
        },
        "extraction_artifacts_v1": {
            "selected_stage": "native_text",
            "canonical_reason_codes": [],
        },
        "fact_graph_v1": {
            "version": "fact_graph_v1",
            "document_type": "commercial_invoice",
            "facts": [],
        },
    }

    sanitized = sanitize(document)

    assert sanitized["review_required"] is False
    assert sanitized["reviewRequired"] is False
