from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
LAUNCH_PIPELINE_PATH = ROOT / "app" / "services" / "extraction" / "launch_pipeline.py"
CONTRACT_PATH = ROOT / "app" / "services" / "extraction_core" / "contract.py"
REVIEW_METADATA_PATH = ROOT / "app" / "services" / "extraction_core" / "review_metadata.py"
RESPONSE_SHAPING_PATH = ROOT / "app" / "routers" / "validation" / "response_shaping.py"


def _load_symbols(path: Path, names: set[str], namespace: Dict[str, Any]) -> Dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected: List[ast.stmt] = []
    for node in parsed.body:
        if isinstance(node, ast.Assign):
            targets = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if targets & names:
                selected.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
            selected.append(node)
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    exec(compile(module_ast, str(path), "exec"), namespace)
    return namespace


def _load_launch_pipeline_symbols() -> Dict[str, Any]:
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
    }
    return _load_symbols(
        LAUNCH_PIPELINE_PATH,
        {
            "_is_populated_field_value",
            "_assess_required_field_completeness",
            "_build_extraction_resolution_metrics",
            "_assess_invoice_financial_completeness",
        },
        namespace,
    )


def _load_review_metadata_symbols() -> Dict[str, Any]:
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Sequence": Sequence,
        "dataclass": dataclass,
        "field": field,
    }
    _load_symbols(
        CONTRACT_PATH,
        {
            "FieldExtraction",
            "ExtractionResolutionField",
            "ExtractionResolution",
        },
        namespace,
    )
    return _load_symbols(
        REVIEW_METADATA_PATH,
        {
            "_EXTRACTION_RESOLUTION_REASON_CODES",
            "_humanize_field_label",
            "_is_extraction_resolution_reason",
            "_build_extraction_resolution_from_fields",
        },
        namespace,
    )


def _load_response_shaping_symbols() -> Dict[str, Any]:
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
    }
    return _load_symbols(
        RESPONSE_SHAPING_PATH,
        {
            "_normalize_doc_status",
            "build_document_extraction_v1",
            "summarize_document_statuses",
        },
        namespace,
    )


def test_launch_pipeline_completeness_emits_extraction_resolution_not_review_reasons() -> None:
    symbols = _load_launch_pipeline_symbols()
    assess = symbols["_assess_invoice_financial_completeness"]

    result = assess({}, invoice_subtype="commercial_invoice")

    assert result["parse_complete"] is False
    assert result["review_reasons"] == []
    assert result["missing_required_fields"] == ["invoice_number", "amount"]
    assert result["extraction_resolution"]["required"] is True
    assert result["extraction_resolution"]["unresolved_count"] == 2
    assert result["extraction_resolution"]["fields"][0]["field_name"] == "invoice_number"


def test_extraction_core_builds_resolution_for_unconfirmed_ai_field() -> None:
    symbols = _load_review_metadata_symbols()
    FieldExtraction = symbols["FieldExtraction"]
    build_resolution = symbols["_build_extraction_resolution_from_fields"]
    is_reason = symbols["_is_extraction_resolution_reason"]

    resolution = build_resolution(
        fields=[
            FieldExtraction(
                name="issue_date",
                value_raw="20 Apr 2026",
                value_normalized="2026-04-20",
                state="found",
                confidence=0.61,
                reason_codes=["LOW_CONFIDENCE_CRITICAL"],
            ),
        ],
        field_details={"issue_date": {"verification": "model_suggested"}},
    )

    assert resolution is not None
    assert resolution.required is True
    assert resolution.unresolved_count == 1
    assert resolution.fields[0].field_name == "issue_date"
    assert resolution.fields[0].verification == "model_suggested"
    assert is_reason("FIELD_NOT_FOUND") is True
    assert is_reason("missing:issue_date") is True
    assert is_reason("manual_policy_review_required") is False


def test_document_extraction_contract_preserves_extraction_resolution() -> None:
    symbols = _load_response_shaping_symbols()
    build_document_extraction_v1 = symbols["build_document_extraction_v1"]

    payload = build_document_extraction_v1(
        [
            {
                "document_id": "doc-1",
                "document_type": "commercial_invoice",
                "filename": "Invoice.pdf",
                "status": "warning",
                "extraction_status": "partial",
                "parse_complete": False,
                "missing_required_fields": ["invoice_date"],
                "extraction_resolution": {
                    "required": True,
                    "unresolved_count": 1,
                    "summary": "1 extracted field still needs confirmation before validation can be treated as final.",
                    "fields": [
                        {
                            "field_name": "invoice_date",
                            "label": "Invoice Date",
                            "verification": "not_found",
                        }
                    ],
                    "source": "ai_extraction",
                },
            }
        ]
    )

    document = payload["documents"][0]
    assert document["extraction_resolution"]["required"] is True
    assert document["extraction_resolution"]["unresolved_count"] == 1
