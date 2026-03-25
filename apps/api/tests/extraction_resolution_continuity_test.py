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
VALIDATION_EXECUTION_PATH = ROOT / "app" / "routers" / "validation" / "validation_execution.py"


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
        "_top3_field_boost_v1_enabled": lambda: False,
        "_TOP3_FIELD_NAMES": set(),
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
            "_ParsedFieldCandidate",
            "_humanize_field_label",
            "_is_extraction_resolution_reason",
            "_build_extraction_resolution_from_fields",
            "_merge_field_candidates",
        },
        namespace,
    )


def _load_response_shaping_symbols() -> Dict[str, Any]:
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "materialize_document_fact_graphs_v1": lambda docs: docs,
        "_build_resolution_queue_payload": lambda docs: {
            "summary": {
                "total_items": 0,
                "unresolved_documents": 0,
            }
        },
    }
    return _load_symbols(
        RESPONSE_SHAPING_PATH,
        {
            "build_workflow_stage",
            "_normalize_doc_status",
            "build_document_extraction_v1",
            "summarize_document_statuses",
        },
        namespace,
    )


def _load_issues_pipeline_symbols() -> Dict[str, Any]:
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Set": set,
        "_priority_to_severity": lambda priority, severity=None: severity or priority or "minor",
    }
    return _load_symbols(
        ROOT / "app" / "routers" / "validation" / "issues_pipeline.py",
        {
            "_normalize_issue_field_key",
            "_normalize_issue_document_ids",
            "_is_extraction_provisional_issue",
            "_partition_workflow_stage_issues",
        },
        namespace,
    )


def _load_presentation_contract_symbols() -> Dict[str, Any]:
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": tuple,
        "json": __import__("json"),
        "logging": __import__("logging"),
        "logger": __import__("logging").getLogger(__name__),
        "_build_document_field_hint_index": lambda _documents: {},
        "_build_unresolved_critical_context": lambda _field_decisions, critical_fields=None, documents=None: [],
    }
    return _load_symbols(
        ROOT / "app" / "routers" / "validation" / "presentation_contract.py",
        {
            "_apply_workflow_stage_contract_overrides",
        },
        namespace,
    )


def _load_validation_execution_symbols() -> Dict[str, Any]:
    response_shaping_symbols = _load_response_shaping_symbols()
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "Optional": Optional,
        "_response_shaping": type(
            "_ResponseShapingStub",
            (),
            {"build_workflow_stage": staticmethod(response_shaping_symbols["build_workflow_stage"])},
        )(),
    }
    return _load_symbols(
        VALIDATION_EXECUTION_PATH,
        {
            "_should_defer_final_validation",
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


def test_document_extraction_contract_clears_legacy_parser_debt_for_fact_backed_docs() -> None:
    symbols = _load_response_shaping_symbols()
    build_document_extraction_v1 = symbols["build_document_extraction_v1"]

    payload = build_document_extraction_v1(
        [
            {
                "document_id": "doc-invoice",
                "document_type": "commercial_invoice",
                "filename": "Invoice.pdf",
                "status": "success",
                "extraction_status": "success",
                "parse_complete": False,
                "parse_completeness": 0.42,
                "missing_required_fields": ["seller"],
                "review_required": True,
                "review_reasons": ["FIELD_NOT_FOUND", "manual_policy_review_required"],
                "fact_graph_v1": {
                    "document_type": "commercial_invoice",
                    "facts": [],
                },
            }
        ]
    )

    document = payload["documents"][0]
    assert document["status"] == "success"
    assert document["parse_complete"] is None
    assert document["parse_completeness"] is None
    assert document["missing_required_fields"] == []
    assert document["review_required"] is True
    assert document["review_reasons"] == ["manual_policy_review_required"]


def test_workflow_stage_marks_extraction_resolution_until_unresolved_fields_clear() -> None:
    symbols = _load_response_shaping_symbols()
    build_workflow_stage = symbols["build_workflow_stage"]

    stage = build_workflow_stage(
        [
            {
                "document_id": "doc-1",
                "extraction_lane": "document_ai",
                "extraction_resolution": {
                    "required": True,
                    "unresolved_count": 2,
                    "summary": "2 fields need confirmation.",
                    "fields": [
                        {"field_name": "invoice_date", "label": "Invoice Date"},
                        {"field_name": "currency", "label": "Currency"},
                    ],
                },
            },
            {
                "document_id": "doc-2",
                "extraction_lane": "structured_iso",
            },
        ],
        validation_status="review",
    )

    assert stage["stage"] == "extraction_resolution"
    assert stage["provisional_validation"] is True
    assert stage["ready_for_final_validation"] is False
    assert stage["unresolved_documents"] == 1
    assert stage["unresolved_fields"] == 2
    assert stage["document_lane_counts"]["document_ai"] == 1
    assert stage["document_lane_counts"]["structured_iso"] == 1


def test_workflow_stage_moves_to_validation_results_when_extraction_is_resolved() -> None:
    symbols = _load_response_shaping_symbols()
    build_workflow_stage = symbols["build_workflow_stage"]

    stage = build_workflow_stage(
        [
            {
                "document_id": "doc-1",
                "extraction_lane": "document_ai",
                "extraction_resolution": {
                    "required": False,
                    "unresolved_count": 0,
                    "summary": "",
                    "fields": [],
                },
            }
        ],
        validation_status="review",
    )

    assert stage["stage"] == "validation_results"
    assert stage["provisional_validation"] is False
    assert stage["ready_for_final_validation"] is True
    assert stage["unresolved_documents"] == 0
    assert stage["unresolved_fields"] == 0


def test_workflow_stage_prefers_fact_backed_queue_counts_over_legacy_resolution_counts() -> None:
    symbols = _load_response_shaping_symbols()
    build_workflow_stage = symbols["build_workflow_stage"]
    build_workflow_stage.__globals__["_build_resolution_queue_payload"] = lambda docs: {
        "summary": {
            "total_items": 6,
            "unresolved_documents": 3,
        }
    }

    stage = build_workflow_stage(
        [
            {
                "document_id": "doc-1",
                "extraction_lane": "document_ai",
                "fact_graph_v1": {"document_type": "commercial_invoice", "facts": []},
                "extraction_resolution": {
                    "required": True,
                    "unresolved_count": 1,
                    "fields": [{"field_name": "invoice_date"}],
                },
            },
            {
                "document_id": "doc-2",
                "extraction_lane": "support_only",
                "extraction_resolution": {
                    "required": True,
                    "unresolved_count": 2,
                    "fields": [
                        {"field_name": "issuer_name"},
                        {"field_name": "permit_number"},
                    ],
                },
            },
        ],
        validation_status="review",
    )

    assert stage["stage"] == "extraction_resolution"
    assert stage["unresolved_documents"] == 4
    assert stage["unresolved_fields"] == 8
    assert stage["document_lane_counts"]["document_ai"] == 1
    assert stage["document_lane_counts"]["support_only"] == 1


def test_workflow_stage_contract_override_downgrades_submission_and_bank_verdict() -> None:
    symbols = _load_presentation_contract_symbols()
    apply_overrides = symbols["_apply_workflow_stage_contract_overrides"]

    overridden = apply_overrides(
        {
            "stage": "extraction_resolution",
            "summary": "2 fields still need confirmation.",
            "unresolved_documents": 1,
            "unresolved_fields": 2,
        },
        {
            "verdict": "SUBMIT",
            "can_submit": True,
            "action_items": [],
            "issue_summary": {"critical": 0, "major": 0, "minor": 0, "total": 0},
        },
        {
            "can_submit": True,
            "reasons": [],
            "missing_reason_codes": [],
            "unresolved_critical_fields": [],
            "unresolved_critical_statuses": [],
        },
        {
            "final_verdict": "pass",
            "review_required_reason": [],
            "escalation_triggers": [],
            "rules_evidence": {},
            "evidence_summary": {},
        },
    )

    assert overridden["bank_verdict"]["verdict"] == "CAUTION"
    assert overridden["bank_verdict"]["can_submit"] is False
    assert overridden["submission_eligibility"]["can_submit"] is False
    assert "workflow_stage_extraction_resolution" in overridden["submission_eligibility"]["reasons"]
    assert overridden["validation_contract"]["final_verdict"] == "review"
    assert overridden["validation_contract"]["override_reason"] == "extraction_resolution_pending"


def test_workflow_stage_issue_partition_moves_extraction_dependent_items_out_of_final_issues() -> None:
    symbols = _load_issues_pipeline_symbols()
    partition = symbols["_partition_workflow_stage_issues"]

    result = partition(
        [
            {
                "title": "Invoice date could not be confirmed",
                "field": "invoice_date",
                "document_ids": ["doc-1"],
                "reason_code": "FIELD_NOT_FOUND",
            },
            {
                "title": "Invoice amount mismatches packing list",
                "field": "amount",
                "document_ids": ["doc-1"],
                "reason_code": "crossdoc_mismatch",
                "description": "Cross-document discrepancy on amount.",
            },
        ],
        [
            {
                "document_id": "doc-1",
                "extraction_resolution": {
                    "required": True,
                    "unresolved_count": 1,
                    "fields": [{"field_name": "invoice_date"}],
                },
            }
        ],
        {"stage": "extraction_resolution"},
    )

    assert len(result["final_issues"]) == 1
    assert result["final_issues"][0]["reason_code"] == "crossdoc_mismatch"
    assert len(result["provisional_issues"]) == 1
    assert result["provisional_issues"][0]["reason_code"] == "FIELD_NOT_FOUND"


def test_validation_execution_defers_final_validation_when_extraction_resolution_is_open() -> None:
    symbols = _load_validation_execution_symbols()
    should_defer = symbols["_should_defer_final_validation"]

    state = should_defer(
        [
            {
                "document_id": "doc-1",
                "extraction_resolution": {
                    "required": True,
                    "unresolved_count": 1,
                    "fields": [{"field_name": "invoice_date"}],
                },
            }
        ]
    )

    assert state["defer"] is True
    assert state["workflow_stage"]["stage"] == "extraction_resolution"


def test_review_metadata_does_not_promote_preparser_guess_over_existing_extraction_state() -> None:
    symbols = _load_review_metadata_symbols()
    ParsedFieldCandidate = symbols["_ParsedFieldCandidate"]
    merge_candidates = symbols["_merge_field_candidates"]

    existing = ParsedFieldCandidate(
        name="issue_date",
        value_raw=None,
        value_normalized=None,
        state="missing",
        confidence=0.0,
        evidence_snippet=None,
        reason_codes=["FIELD_NOT_FOUND"],
        source="existing",
    )
    preparser = ParsedFieldCandidate(
        name="issue_date",
        value_raw="2026-03-08",
        value_normalized="2026-03-08",
        state="found",
        confidence=0.88,
        evidence_snippet="Invoice Date: 2026-03-08",
        reason_codes=[],
        source="preparser",
    )

    merged = merge_candidates(existing, preparser)

    assert merged.source == "existing"
    assert merged.state == "missing"
