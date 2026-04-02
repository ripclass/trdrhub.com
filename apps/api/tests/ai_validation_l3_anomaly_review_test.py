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
        "_collect_l3_document_snapshots",
        "review_advanced_anomalies",
    }
    selected_nodes = []
    allowed_assignments = {
        "_L3_REVIEWABLE_DOCUMENT_TYPES",
        "_L3_DOCUMENT_TYPE_ALIASES",
        "_L3_DOCUMENT_LABELS",
        "_L3_WARNING_STATUSES",
        "_L3_LOW_CONFIDENCE_THRESHOLD",
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
    assert "AI-L3-LOW-CONFIDENCE-INVOICE" in issue_ids


def test_ai_validator_source_runs_l3_review_and_records_check_name() -> None:
    source = AI_VALIDATOR_PATH.read_text(encoding="utf-8")

    assert "review_advanced_anomalies(documents, extracted_context)" in source
    assert 'metadata["checks_performed"].append("advanced_anomaly_review")' in source
