from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "app" / "routers" / "validation" / "issues_pipeline.py"


def _load_symbols() -> Dict[str, Any]:
    source = MODULE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef)
        and node.name
        in {
            "_normalize_issue_field_key",
            "_normalize_issue_document_ids",
            "_is_extraction_provisional_issue",
            "_partition_workflow_stage_issues",
        }
    ]
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Set": Set,
        "_priority_to_severity": lambda priority, severity=None: severity or priority or "minor",
    }
    exec(compile(module_ast, str(MODULE_PATH), "exec"), namespace)
    return namespace


def test_partition_moves_same_document_findings_and_weak_fallback_noise_to_provisional() -> None:
    module = _load_symbols()

    documents = [
        {
            "document_id": "doc-invoice",
            "document_type": "commercial_invoice",
            "filename": "Invoice.png",
            "review_required": True,
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
        }
    ]
    issues = [
        {
            "rule": "CROSSDOC-INV-005",
            "title": "Invoice Missing LC Reference",
            "description": "Invoice does not reference the Letter of Credit number.",
            "severity": "minor",
            "documentName": "commercial_invoice",
            "expected": "LC reference: exp2026bd001",
            "actual": "No LC reference found on invoice",
        },
        {
            "rule": "AI-L3-LOW-CONFIDENCE-INVOICE",
            "title": "Low Extraction Confidence: Commercial Invoice",
            "severity": "major",
            "documentName": "Commercial Invoice",
        },
        {
            "rule": "UCP600-20",
            "title": "Bill of Lading",
            "description": "Carrier’s name missing from bill of lading",
            "severity": "minor",
            "documentName": "Supporting Document",
            "expected": "—",
            "actual": "",
        },
        {
            "rule": "CROSSDOC-BL-003",
            "title": "Late Shipment",
            "description": "Bill of lading shipment date exceeds LC latest shipment date.",
            "severity": "major",
            "documentName": "Bill of Lading",
        },
    ]

    partition = module["_partition_workflow_stage_issues"](
        issues,
        documents,
        {"stage": "validation_results"},
    )

    final_rules = [issue["rule"] for issue in partition["final_issues"]]
    provisional_rules = [issue["rule"] for issue in partition["provisional_issues"]]

    assert final_rules == [
        "AI-L3-LOW-CONFIDENCE-INVOICE",
        "CROSSDOC-BL-003",
    ]
    assert provisional_rules == [
        "CROSSDOC-INV-005",
        "UCP600-20",
    ]
    assert partition["provisional_issues"][0]["provisional_reason"] == "ai_major_extraction_uncertainty"
    assert partition["provisional_issues"][1]["provisional_reason"] == "ai_major_extraction_fallback_noise"
    assert partition["provisional_issues"][0]["provisional_document_types"] == ["commercial_invoice"]


def test_partition_keeps_validation_results_issues_final_without_unreliable_documents() -> None:
    module = _load_symbols()

    result = module["_partition_workflow_stage_issues"](
        [
            {
                "rule": "CROSSDOC-INV-005",
                "title": "Invoice Missing LC Reference",
                "severity": "minor",
                "documentName": "commercial_invoice",
            }
        ],
        [
            {
                "document_id": "doc-invoice",
                "document_type": "commercial_invoice",
                "review_required": False,
                "extraction_status": "success",
                "critical_field_states": {"issue_date": "found"},
                "extraction_artifacts_v1": {
                    "selected_stage": "native_text",
                    "canonical_reason_codes": [],
                },
            }
        ],
        {"stage": "validation_results"},
    )

    assert [issue["rule"] for issue in result["final_issues"]] == ["CROSSDOC-INV-005"]
    assert result["provisional_issues"] == []
