from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
ISSUES_PIPELINE_PATH = ROOT / "app" / "routers" / "validation" / "issues_pipeline.py"
PRESENTATION_CONTRACT_PATH = ROOT / "app" / "routers" / "validation" / "presentation_contract.py"


class _DummyLogger:
    def warning(self, *args, **kwargs) -> None:
        return None


def _load_issue_symbols(target_names: set[str]) -> Dict[str, Any]:
    source = ISSUES_PIPELINE_PATH.read_text(encoding="utf-8")
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
        "Set": Set,
    }
    exec(compile(module_ast, str(ISSUES_PIPELINE_PATH), "exec"), namespace)
    return namespace


def _load_contract_symbols(issue_symbols: Dict[str, Any], target_names: set[str]) -> Dict[str, Any]:
    source = PRESENTATION_CONTRACT_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected = [
        node
        for node in parsed.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in target_names
    ]
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
        "json": json,
        "logger": _DummyLogger(),
        "_build_document_field_hint_index": issue_symbols["_build_document_field_hint_index"],
        "_build_unresolved_critical_context": issue_symbols["_build_unresolved_critical_context"],
    }
    exec(compile(module_ast, str(PRESENTATION_CONTRACT_PATH), "exec"), namespace)
    return namespace


def test_submission_eligibility_context_preserves_unresolved_field_hints() -> None:
    issue_symbols = _load_issue_symbols(
        {
            "_build_document_field_hint_index",
            "_build_unresolved_critical_context",
        }
    )
    contract_symbols = _load_contract_symbols(issue_symbols, {"_build_submission_eligibility_context"})
    build_submission_eligibility_context = contract_symbols["_build_submission_eligibility_context"]

    gate_result = {
        "missing_critical": ["invoice_date"],
        "missing_reason_codes": ["field_not_found"],
    }
    field_decisions = {
        "invoice_date": {"status": "retry", "reason_code": "field_not_found"},
    }
    documents = [
        {
            "filename": "Invoice.pdf",
            "document_type": "commercial_invoice",
            "critical_field_states": {"invoice_date": "missing"},
        }
    ]

    context = build_submission_eligibility_context(gate_result, field_decisions, documents=documents)

    assert context["missing_reason_codes"] == ["field_not_found"]
    assert context["unresolved_critical_statuses"] == ["retry"]
    assert context["unresolved_critical_fields"] == [
        {
            "field": "invoice_date",
            "status": "retry",
            "reason_code": "field_not_found",
            "source_document": "Invoice.pdf",
            "document_type": "commercial_invoice",
        }
    ]


def test_field_decision_augmentation_preserves_issue_and_document_decision_metadata() -> None:
    issue_symbols = _load_issue_symbols(
        {
            "_augment_doc_field_details_with_decisions",
            "_augment_issues_with_field_decisions",
        }
    )
    augment_doc_field_details_with_decisions = issue_symbols["_augment_doc_field_details_with_decisions"]
    augment_issues_with_field_decisions = issue_symbols["_augment_issues_with_field_decisions"]

    documents = [
        {
            "extracted_fields": {
                "_field_decisions": {
                    "invoice_date": {
                        "status": "retry",
                        "reason_code": "field_not_found",
                        "retry_trace": ["fallback_scan"],
                    }
                }
            }
        }
    ]
    issues = [{"field": "invoice_date"}]
    field_decisions = {"invoice_date": {"status": "retry", "reason_code": "field_not_found"}}

    augment_doc_field_details_with_decisions(documents)
    augment_issues_with_field_decisions(issues, field_decisions)

    assert documents[0]["field_details"]["invoice_date"]["decision_status"] == "retry"
    assert documents[0]["field_details"]["invoice_date"]["reason_code"] == "field_not_found"
    assert documents[0]["field_details"]["invoice_date"]["retry_trace"] == ["fallback_scan"]
    assert issues[0]["decision_status"] == "retry"
    assert issues[0]["reason_code"] == "field_not_found"


def test_validation_contract_keeps_submission_gate_review_truth() -> None:
    issue_symbols = _load_issue_symbols(
        {
            "_build_document_field_hint_index",
            "_build_unresolved_critical_context",
        }
    )
    contract_symbols = _load_contract_symbols(
        issue_symbols,
        {
            "_classify_reason_semantics",
            "_extract_requirement_readiness_items",
            "_extract_rule_evidence_items",
            "_classify_rules_signal_classes",
            "_build_validation_contract",
        },
    )
    build_validation_contract = contract_symbols["_build_validation_contract"]

    contract = build_validation_contract(
        {"critical_issues": 0, "major_issues": 1, "minor_issues": 0},
        {"verdict": "SUBMIT", "reasons": [], "risk_flags": []},
        {"missing_critical": []},
        {
            "can_submit": False,
            "reasons": ["missing_document"],
            "missing_reason_codes": ["field_not_found"],
            "unresolved_critical_fields": [
                {"field": "invoice_date", "status": "retry", "reason_code": "field_not_found"}
            ],
        },
        issues=[{"rule_id": "RULE-1", "severity": "major", "reason_code": "FIELD_NOT_FOUND"}],
    )

    assert contract["final_verdict"] == "review"
    assert contract["override_reason"] == "ai_warn_requires_review"
    assert contract["next_action"] == "escalate_to_l2"
    assert contract["evidence_summary"]["submission_readiness"] == "not_ready"
    assert contract["rules_evidence"]["reason_semantics"]["extraction_failures"] == ["field_not_found"]
    assert "submission_not_ready" in contract["review_required_reason"]


def test_validation_contract_surfaces_requirements_driven_statement_findings_in_readiness_evidence() -> None:
    issue_symbols = _load_issue_symbols(
        {
            "_build_document_field_hint_index",
            "_build_unresolved_critical_context",
        }
    )
    contract_symbols = _load_contract_symbols(
        issue_symbols,
        {
            "_classify_reason_semantics",
            "_extract_requirement_readiness_items",
            "_extract_rule_evidence_items",
            "_classify_rules_signal_classes",
            "_build_validation_contract",
        },
    )
    build_validation_contract = contract_symbols["_build_validation_contract"]

    submission_eligibility = {
        "can_submit": False,
        "reasons": ["missing_document"],
        "missing_reason_codes": [],
        "unresolved_critical_fields": [],
    }
    contract = build_validation_contract(
        {"critical_issues": 1, "major_issues": 0, "minor_issues": 0},
        {"verdict": "SUBMIT", "reasons": [], "risk_flags": []},
        {"missing_critical": []},
        submission_eligibility,
        issues=[
            {
                "rule_id": "CROSSDOC-EXACT-WORDING",
                "severity": "critical",
                "title": "LC-required wording missing from Beneficiary Certificate",
                "message": "LC requires exact wording on Beneficiary Certificate.",
                "document_names": ["Letter of Credit", "Beneficiary Certificate"],
                "suggestion": "Add the required wording before presentation.",
                "requirement_source": "requirements_graph_v1",
                "requirement_kind": "document_exact_wording",
                "requirement_text": "WE HEREBY CERTIFY GOODS ARE BRAND NEW",
            }
        ],
    )

    assert "lc_required_statement_missing" in submission_eligibility["reasons"]
    assert contract["rules_evidence"]["requirement_reason_codes"] == ["lc_required_statement_missing"]
    assert contract["rules_evidence"]["requirements_review_needed"] is True
    assert contract["rules_evidence"]["requirement_readiness_items"][0]["requirement_kind"] == "document_exact_wording"
    assert contract["rules_evidence"]["reason_semantics"]["requirement_findings"] == ["lc_required_statement_missing"]
    assert contract["evidence_summary"]["requirements_review_needed"] is True
    assert "LC-required wording missing from Beneficiary Certificate" in contract["evidence_summary"]["primary_requirement_actions"]


def test_validation_contract_decision_surfaces_force_review_to_not_ready() -> None:
    issue_symbols = _load_issue_symbols(
        {
            "_build_document_field_hint_index",
            "_build_unresolved_critical_context",
        }
    )
    contract_symbols = _load_contract_symbols(
        issue_symbols,
        {
            "_apply_validation_contract_decision_surfaces",
        },
    )
    apply_validation_contract_decision_surfaces = contract_symbols[
        "_apply_validation_contract_decision_surfaces"
    ]

    aligned = apply_validation_contract_decision_surfaces(
        {
            "verdict": "SUBMIT",
            "can_submit": True,
            "recommendation": "Proceed",
        },
        {
            "can_submit": True,
            "reasons": ["bank_verdict_submit"],
        },
        {
            "final_verdict": "review",
            "rules_evidence": {"submission_can_submit": True, "submission_reasons": []},
            "evidence_summary": {"submission_readiness": "ready"},
        },
    )

    assert aligned["bank_verdict"]["verdict"] == "CAUTION"
    assert aligned["bank_verdict"]["can_submit"] is False
    assert aligned["submission_eligibility"]["can_submit"] is False
    assert "validation_contract_review" in aligned["submission_eligibility"]["reasons"]
    assert aligned["validation_contract"]["rules_evidence"]["submission_can_submit"] is False
    assert (
        aligned["validation_contract"]["evidence_summary"]["submission_readiness"]
        == "not_ready"
    )
