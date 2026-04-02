from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


AI_VALIDATOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "validation"
    / "ai_validator.py"
)


def _load_ai_validator_symbols() -> Dict[str, Any]:
    source = AI_VALIDATOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_names = {
        "IssueSeverity",
        "AIValidationIssue",
        "_normalize_document_type",
        "_normalize_confidence_value",
        "_snapshot_display_name",
        "_classify_l3_confidence_severity",
        "_collect_l3_document_snapshots",
        "review_advanced_anomalies",
    }
    selected_nodes = []
    allowed_assignments = {
        "_L3_REVIEWABLE_DOCUMENT_TYPES",
        "_L3_DOCUMENT_TYPE_ALIASES",
        "_L3_DOCUMENT_LABELS",
        "_L3_WARNING_STATUSES",
        "_L3_MAJOR_REVIEWABLE_DOCUMENT_TYPES",
        "_L3_MAJOR_WARNING_STATUSES",
        "_L3_LOW_CONFIDENCE_THRESHOLD",
        "_L3_SEVERE_CONFIDENCE_THRESHOLD",
        "_L3_DEGRADED_SELECTION_STAGES",
        "_L3_EXTRACTION_FAILURE_REASON_CODES",
    }
    for node in parsed.body:
        if isinstance(node, ast.Assign):
            targets = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            if targets & allowed_assignments:
                selected_nodes.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in selected_names:
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
        "dataclass": dataclass,
        "field": field,
        "Enum": Enum,
    }
    exec(compile(module_ast, str(AI_VALIDATOR_PATH), "exec"), namespace)
    return namespace


def test_review_advanced_anomalies_flags_only_suspicious_low_confidence_documents() -> None:
    symbols = _load_ai_validator_symbols()
    review_advanced_anomalies = symbols["review_advanced_anomalies"]

    documents = [
        {
            "document_type": "letter_of_credit",
            "filename": "LC.pdf",
            "ocr_confidence": 0.96,
            "status": "success",
        },
        {
            "document_type": "commercial_invoice",
            "filename": "Invoice.pdf",
            "ocr_confidence": 0.21,
            "status": "warning",
        },
    ]
    extracted_context = {
        "lc": {
            "raw_text": "IRREVOCABLE DOCUMENTARY CREDIT",
            "_extraction_confidence": 0.96,
        },
        "invoice": {
            "raw_text": "COMMERCIAL INVOICE\nUSD 95,000.00",
            "_extraction_confidence": 0.21,
            "status": "warning",
        },
    }

    issues, metadata = review_advanced_anomalies(documents, extracted_context)

    issue_ids = [issue.rule_id for issue in issues]

    assert metadata["l3_documents_reviewed_count"] == 2
    assert metadata["l3_documents_reviewed"] == ["invoice", "lc"]
    assert metadata["l3_low_confidence_document_types"] == ["invoice"]
    assert metadata["l3_issue_count"] == 1
    assert metadata["l3_minor_issues"] == 1
    assert metadata["l3_major_issues"] == 0
    assert "AI-L3-LOW-CONFIDENCE-INVOICE" in issue_ids


def test_review_advanced_anomalies_escalates_core_doc_confidence_failures_to_major() -> None:
    symbols = _load_ai_validator_symbols()
    review_advanced_anomalies = symbols["review_advanced_anomalies"]
    IssueSeverity = symbols["IssueSeverity"]

    documents = [
        {
            "document_type": "letter_of_credit",
            "filename": "LC.pdf",
            "ocr_confidence": 0.18,
            "status": "error",
        }
    ]
    extracted_context = {
        "lc": {
            "raw_text": "IRREVOCABLE DOCUMENTARY CREDIT",
            "_extraction_confidence": 0.18,
            "status": "error",
        },
    }

    issues, metadata = review_advanced_anomalies(documents, extracted_context)

    assert len(issues) == 1
    assert issues[0].rule_id == "AI-L3-LOW-CONFIDENCE-LC"
    assert issues[0].severity == IssueSeverity.MAJOR
    assert metadata["l3_issue_count"] == 1
    assert metadata["l3_major_issues"] == 1
    assert metadata["l3_minor_issues"] == 0
    assert metadata["l3_low_confidence_details"] == [
        {
            "document_type": "lc",
            "confidence": 0.18,
            "status": "error",
            "severity": "major",
            "review_required": False,
            "reason_codes": [],
            "selected_stage": None,
        }
    ]


def test_review_advanced_anomalies_escalates_review_required_extraction_failures_without_numeric_confidence() -> None:
    symbols = _load_ai_validator_symbols()
    review_advanced_anomalies = symbols["review_advanced_anomalies"]
    IssueSeverity = symbols["IssueSeverity"]

    documents = [
        {
            "document_type": "commercial_invoice",
            "filename": "Invoice.png",
            "status": "partial",
            "review_required": True,
            "extraction_artifacts_v1": {
                "selected_stage": "binary_metadata_scrape",
                "reason_codes": [
                    "OCR_AUTH_ERROR",
                    "OCR_EMPTY_RESULT",
                    "PARSER_EMPTY_OUTPUT",
                ],
            },
        }
    ]
    extracted_context = {
        "invoice": {
            "status": "partial",
            "review_required": True,
        },
    }

    issues, metadata = review_advanced_anomalies(documents, extracted_context)

    assert len(issues) == 1
    assert issues[0].rule_id == "AI-L3-LOW-CONFIDENCE-INVOICE"
    assert issues[0].severity == IssueSeverity.MAJOR
    assert "manual review" in issues[0].found.lower()
    assert metadata["l3_issue_count"] == 1
    assert metadata["l3_major_issues"] == 1
    assert metadata["l3_minor_issues"] == 0
    assert metadata["l3_low_confidence_details"] == [
        {
            "document_type": "invoice",
            "confidence": None,
            "status": "partial",
            "severity": "major",
            "review_required": True,
            "reason_codes": [
                "OCR_AUTH_ERROR",
                "OCR_EMPTY_RESULT",
                "PARSER_EMPTY_OUTPUT",
            ],
            "selected_stage": "binary_metadata_scrape",
        }
    ]


def test_ai_validator_source_runs_l3_review_and_records_check_name() -> None:
    source = AI_VALIDATOR_PATH.read_text(encoding="utf-8")

    assert "review_advanced_anomalies(documents, extracted_context)" in source
    assert 'metadata["checks_performed"].append("advanced_anomaly_review")' in source
