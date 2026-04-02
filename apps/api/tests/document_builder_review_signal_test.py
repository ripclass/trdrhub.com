from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "app" / "routers" / "validation" / "document_builder.py"
RESPONSE_SHAPING_PATH = ROOT / "app" / "routers" / "validation" / "response_shaping.py"


class _LoggerStub:
    def info(self, *args: Any, **kwargs: Any) -> None:
        return None

    def warning(self, *args: Any, **kwargs: Any) -> None:
        return None


def _load_symbols() -> Dict[str, Any]:
    response_source = RESPONSE_SHAPING_PATH.read_text(encoding="utf-8")
    response_ast = ast.parse(response_source)
    response_nodes = [
        node
        for node in response_ast.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {
            "_uses_fact_resolution_contract",
            "_is_legacy_extraction_review_reason",
            "_has_runtime_extraction_review_signal",
            "sanitize_public_document_contract_v1",
        }
    ]

    source = MODULE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes = response_nodes + [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name == "build_document_summaries"
    ]

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
        "uuid4": uuid4,
        "logger": _LoggerStub(),
        "collect_document_issue_stats": lambda results: ({}, {}, {}),
        "resolve_issue_stats": lambda *_args, **_kwargs: {"count": 0, "max_severity": None},
        "severity_to_status": lambda _severity: "success",
        "resolve_structured_document_type": (
            lambda detail, filename=None, index=0: detail.get("document_type")
            or detail.get("documentType")
            or "supporting_document"
        ),
        "humanize_doc_type": lambda value: str(value or "").replace("_", " ").title(),
        "filter_user_facing_fields": lambda value: value if isinstance(value, dict) else {},
        "_empty_extraction_artifacts_v1": lambda raw_text="", ocr_confidence=None: {
            "selected_stage": None,
            "canonical_reason_codes": [],
            "raw_text": raw_text,
            "ocr_confidence": ocr_confidence,
        },
    }
    exec(compile(module_ast, str(MODULE_PATH), "exec"), namespace)
    return namespace


def test_build_document_summaries_preserves_degraded_review_signal() -> None:
    symbols = _load_symbols()
    build_document_summaries = symbols["build_document_summaries"]

    detail = {
        "id": "doc-invoice-1",
        "name": "Invoice.pdf",
        "document_type": "commercial_invoice",
        "status": "warning",
        "extraction_status": "partial",
        "ocr_confidence": None,
        "review_required": False,
        "review_reasons": [],
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
    }

    [summary] = build_document_summaries([], [], [detail])

    assert summary["review_required"] is True
    assert summary["reviewReasons"] == []
    assert summary["criticalFieldStates"]["issue_date"] == "missing"
    assert summary["extraction_artifacts_v1"]["selected_stage"] == "binary_metadata_scrape"


def test_build_document_summaries_keeps_clean_documents_clean() -> None:
    symbols = _load_symbols()
    build_document_summaries = symbols["build_document_summaries"]

    detail = {
        "id": "doc-invoice-2",
        "name": "Invoice.pdf",
        "document_type": "commercial_invoice",
        "status": "success",
        "extraction_status": "success",
        "ocr_confidence": 0.92,
        "review_required": False,
        "review_reasons": [],
        "critical_field_states": {
            "issue_date": "found",
            "issuer": "found",
        },
        "extraction_artifacts_v1": {
            "selected_stage": "native_text",
            "canonical_reason_codes": [],
        },
    }

    [summary] = build_document_summaries([], [], [detail])

    assert summary["review_required"] is False
    assert summary["reviewReasons"] == []
    assert summary["extraction_artifacts_v1"]["selected_stage"] == "native_text"
