from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
REVIEW_POLICY_PATH = ROOT / "app" / "routers" / "validation" / "review_policy.py"


def _load_symbols(target_names: set[str]) -> Dict[str, Any]:
    source = REVIEW_POLICY_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name in target_names
    ]
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "os": os,
    }
    exec(compile(module_ast, str(REVIEW_POLICY_PATH), "exec"), namespace)
    return namespace


def test_apply_extraction_guard_downgrades_rich_text_with_no_fields() -> None:
    symbols = _load_symbols({"count_populated_canonical_fields", "apply_extraction_guard"})
    guard = symbols["apply_extraction_guard"]

    doc_info = {"extraction_status": "success", "extracted_fields": {}}
    guard(doc_info, "A" * 600)

    assert doc_info["extraction_status"] == "partial"
    assert doc_info["downgrade_reason"] == "rich_ocr_text_but_no_parsed_fields"


def test_finalize_text_backed_extraction_status_preserves_truthful_recovery_modes() -> None:
    symbols = _load_symbols({"_extraction_fallback_hotfix_enabled", "finalize_text_backed_extraction_status"})
    finalize = symbols["finalize_text_backed_extraction_status"]

    supporting = {"extraction_status": "empty", "extracted_fields": {}}
    finalize(supporting, "supporting_document", "Recovered text")
    assert supporting["extraction_status"] == "text_only"
    assert supporting["downgrade_reason"] == "text_recovered_but_fields_unresolved"

    invoice = {"extraction_status": "empty", "extracted_fields": {}}
    finalize(invoice, "commercial_invoice", "Recovered text")
    assert invoice["extraction_status"] == "parse_failed"
    assert invoice["downgrade_reason"] == "text_recovered_but_fields_unresolved"


def test_stabilize_document_review_semantics_clears_ocr_auth_only_review_hold() -> None:
    symbols = _load_symbols({"count_populated_canonical_fields", "stabilize_document_review_semantics"})
    stabilize = symbols["stabilize_document_review_semantics"]

    doc_info = {
        "extraction_status": "parse_failed",
        "extracted_fields": {"issuer": "SGS", "issue_date": "2026-04-20"},
        "review_reasons": ["OCR_AUTH_ERROR"],
        "reviewReasons": ["OCR_AUTH_ERROR"],
        "reason_codes": [],
        "review_required": True,
        "reviewRequired": True,
        "parse_complete": True,
    }
    stabilize(doc_info, "Recovered text " * 20)

    assert doc_info["extraction_status"] == "partial"
    assert doc_info["review_reasons"] == []
    assert doc_info["reviewReasons"] == []
    assert doc_info["review_required"] is False
    assert doc_info["reviewRequired"] is False


def test_context_payload_for_doc_type_returns_expected_bucket() -> None:
    symbols = _load_symbols({"context_payload_for_doc_type"})
    resolver = symbols["context_payload_for_doc_type"]

    context = {
        "invoice": {"invoice_number": "INV-1"},
        "packing_list": {"document_date": "2026-04-20"},
    }

    assert resolver(context, "commercial_invoice") == {"invoice_number": "INV-1"}
    assert resolver(context, "packing_list") == {"document_date": "2026-04-20"}
    assert resolver(context, "unknown_doc") == {}
