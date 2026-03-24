from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
RESPONSE_SHAPING_PATH = ROOT / "app" / "routers" / "validation" / "response_shaping.py"


def _load_symbols() -> Dict[str, Any]:
    source = RESPONSE_SHAPING_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    target_functions = {
        "_empty_resolution_queue_v1",
        "_normalize_resolution_queue_for_workflow_stage",
        "build_workflow_stage",
        "build_fact_resolution_v1",
    }
    selected_nodes = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name in target_functions
    ]
    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {"Any": Any, "Dict": Dict, "List": List, "Optional": Optional}
    namespace["materialize_document_fact_graphs_v1"] = lambda documents: documents
    namespace["build_resolution_queue_v1"] = lambda documents, *, workflow_stage=None: {
        "version": "resolution_queue_v1",
        "items": [],
        "summary": {
            "total_items": 0,
            "user_resolvable_items": 0,
            "unresolved_documents": 0,
            "document_counts": {},
        },
    }
    exec(compile(module_ast, str(RESPONSE_SHAPING_PATH), "exec"), namespace)
    return namespace


def test_build_fact_resolution_v1_exposes_invoice_slice_cleanly() -> None:
    symbols = _load_symbols()
    build_fact_resolution_v1 = symbols["build_fact_resolution_v1"]

    documents = [
        {
            "document_id": "doc-invoice",
            "document_type": "commercial_invoice",
            "filename": "Invoice.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "commercial_invoice",
                "facts": [{"field_name": "invoice_date", "verification_state": "candidate"}],
            },
        },
        {
            "document_id": "doc-packing",
            "document_type": "packing_list",
            "filename": "Packing.pdf",
        },
    ]
    workflow_stage = {
        "stage": "extraction_resolution",
        "provisional_validation": True,
        "ready_for_final_validation": False,
        "unresolved_documents": 1,
        "unresolved_fields": 1,
        "summary": "1 document still needs 1 field confirmed before validation should be treated as final.",
    }
    resolution_queue = {
        "version": "resolution_queue_v1",
        "items": [
            {
                "document_id": "doc-invoice",
                "document_type": "commercial_invoice",
                "filename": "Invoice.pdf",
                "field_name": "invoice_date",
                "label": "Invoice Date",
                "priority": "high",
                "candidate_value": "2026-04-20",
                "normalized_value": "2026-04-20",
                "reason": "system_could_not_confirm",
                "verification_state": "candidate",
                "resolvable_by_user": True,
            }
        ],
        "summary": {
            "total_items": 1,
            "user_resolvable_items": 1,
            "unresolved_documents": 1,
            "document_counts": {"commercial_invoice": 1},
        },
    }

    payload = build_fact_resolution_v1(
        documents,
        workflow_stage=workflow_stage,
        resolution_queue=resolution_queue,
    )

    assert payload["version"] == "fact_resolution_v1"
    assert payload["workflow_stage"]["stage"] == "extraction_resolution"
    assert payload["summary"]["total_documents"] == 2
    assert payload["summary"]["unresolved_documents"] == 1
    assert payload["summary"]["total_items"] == 1
    assert payload["documents"][0]["document_id"] == "doc-invoice"
    assert payload["documents"][0]["document_type"] == "commercial_invoice"
    assert payload["documents"][0]["resolution_required"] is True
    assert payload["documents"][0]["ready_for_validation"] is False
    assert payload["documents"][0]["resolution_items"][0]["field_name"] == "invoice_date"
    assert payload["documents"][1]["document_id"] == "doc-packing"
    assert payload["documents"][1]["document_type"] == "packing_list"
    assert payload["documents"][1]["resolution_required"] is False


def test_build_fact_resolution_v1_includes_rendered_lc_but_skips_unbacked_structured_lc() -> None:
    symbols = _load_symbols()
    build_fact_resolution_v1 = symbols["build_fact_resolution_v1"]

    documents = [
        {
            "document_id": "doc-lc-ai",
            "document_type": "letter_of_credit",
            "filename": "LC.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "letter_of_credit",
                "facts": [{"field_name": "lc_number", "verification_state": "candidate"}],
            },
        },
        {
            "document_id": "doc-lc-structured",
            "document_type": "letter_of_credit",
            "filename": "LC.txt",
            "extraction_lane": "structured_mt",
        },
    ]
    workflow_stage = {
        "stage": "extraction_resolution",
        "provisional_validation": True,
        "ready_for_final_validation": False,
        "unresolved_documents": 1,
        "unresolved_fields": 1,
        "summary": "1 document still needs 1 field confirmed before validation should be treated as final.",
    }
    resolution_queue = {
        "version": "resolution_queue_v1",
        "items": [
            {
                "document_id": "doc-lc-ai",
                "document_type": "letter_of_credit",
                "filename": "LC.pdf",
                "field_name": "lc_number",
                "label": "LC Number",
                "priority": "high",
                "candidate_value": "EXP2026BD001",
                "normalized_value": "EXP2026BD001",
                "reason": "system_could_not_confirm",
                "verification_state": "candidate",
                "resolvable_by_user": True,
            }
        ],
        "summary": {
            "total_items": 1,
            "user_resolvable_items": 1,
            "unresolved_documents": 1,
            "document_counts": {"letter_of_credit": 1},
        },
    }

    payload = build_fact_resolution_v1(
        documents,
        workflow_stage=workflow_stage,
        resolution_queue=resolution_queue,
    )

    assert payload["summary"]["total_documents"] == 1
    assert payload["documents"][0]["document_id"] == "doc-lc-ai"
    assert payload["documents"][0]["document_type"] == "letter_of_credit"
    assert payload["documents"][0]["resolution_items"][0]["field_name"] == "lc_number"


def test_build_fact_resolution_v1_clears_stale_queue_when_stage_is_validation_results() -> None:
    symbols = _load_symbols()
    build_fact_resolution_v1 = symbols["build_fact_resolution_v1"]

    documents = [
        {
            "document_id": "doc-invoice",
            "document_type": "commercial_invoice",
            "filename": "Invoice.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "commercial_invoice",
                "facts": [{"field_name": "invoice_date", "verification_state": "unconfirmed"}],
            },
        }
    ]
    workflow_stage = {
        "stage": "validation_results",
        "provisional_validation": False,
        "ready_for_final_validation": True,
        "unresolved_documents": 0,
        "unresolved_fields": 0,
        "summary": "Validation findings reflect the current confirmed document set.",
    }
    stale_resolution_queue = {
        "version": "resolution_queue_v1",
        "items": [
            {
                "document_id": "doc-invoice",
                "document_type": "commercial_invoice",
                "filename": "Invoice.pdf",
                "field_name": "invoice_date",
                "label": "Invoice Date",
                "priority": "high",
                "candidate_value": "2026-04-20",
                "normalized_value": "2026-04-20",
                "reason": "system_could_not_confirm",
                "verification_state": "unconfirmed",
                "resolvable_by_user": True,
            }
        ],
        "summary": {
            "total_items": 1,
            "user_resolvable_items": 1,
            "unresolved_documents": 1,
            "document_counts": {"commercial_invoice": 1},
        },
    }

    payload = build_fact_resolution_v1(
        documents,
        workflow_stage=workflow_stage,
        resolution_queue=stale_resolution_queue,
    )

    assert payload["workflow_stage"]["stage"] == "validation_results"
    assert payload["summary"]["total_items"] == 0
    assert payload["summary"]["unresolved_documents"] == 0
    assert payload["summary"]["ready_for_validation"] is True
    assert payload["documents"][0]["resolution_required"] is False
    assert payload["documents"][0]["unresolved_count"] == 0
    assert payload["documents"][0]["resolution_items"] == []
