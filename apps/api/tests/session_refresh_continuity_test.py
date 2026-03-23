from __future__ import annotations

import ast
import asyncio
import copy
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
SESSION_REFRESH_PATH = ROOT / "app" / "routers" / "validation" / "session_refresh.py"


def _load_symbols(target_names: set[str]) -> Dict[str, Any]:
    source = SESSION_REFRESH_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected = [
        node
        for node in parsed.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in target_names
    ]
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    class _FakeComplianceScorer:
        def calculate_from_issues(self, issues: List[Dict[str, Any]], extraction_completeness: float = 1.0):
            major = sum(1 for issue in issues if str(issue.get("severity") or "").lower() == "major")
            critical = sum(1 for issue in issues if str(issue.get("severity") or "").lower() == "critical")
            minor = sum(1 for issue in issues if str(issue.get("severity") or "").lower() not in {"major", "critical"})
            verdict = "review" if issues else "pass"
            score = max(0.0, extraction_completeness * 100 - major * 15 - critical * 30 - minor * 5)
            return SimpleNamespace(
                score=score,
                level=SimpleNamespace(value=verdict),
                cap_reason=None,
                critical_count=critical,
                major_count=major,
                minor_count=minor,
            )

    async def _fake_run_validation_arbitration_escalation(contract, *_args, **_kwargs):
        contract = copy.deepcopy(contract)
        contract["final_verdict"] = contract.get("final_verdict") or ("pass" if contract.get("issue_count") == 0 else "review")
        return contract

    def _fake_build_bank_submission_verdict(*, critical_count: int, major_count: int, minor_count: int, compliance_score: float, all_issues: List[Any]):
        verdict = "SUBMIT" if critical_count == 0 and major_count == 0 else "CAUTION"
        return {
            "verdict": verdict,
            "can_submit": verdict == "SUBMIT",
            "action_items": [],
            "issue_summary": {
                "critical": critical_count,
                "major": major_count,
                "minor": minor_count,
                "total": critical_count + major_count + minor_count,
            },
        }

    def _fake_build_submission_eligibility_context(gate_result, field_decisions, documents=None):
        unresolved = []
        for field_name, decision in (field_decisions or {}).items():
            status = str((decision or {}).get("status") or "").lower()
            if status in {"retry", "rejected"}:
                unresolved.append(
                    {
                        "field": field_name,
                        "status": status,
                        "reason_code": (decision or {}).get("reason_code") or "unknown",
                    }
                )
        return {
            "missing_reason_codes": sorted({item["reason_code"] for item in unresolved}),
            "unresolved_critical_fields": unresolved,
            "unresolved_critical_statuses": sorted({item["status"] for item in unresolved}),
        }

    def _fake_build_validation_contract(_ai_validation, bank_verdict, _gate_result, eligibility, *, issues):
        return {
            "final_verdict": "pass" if bank_verdict.get("can_submit") and not issues else "review",
            "issue_count": len(issues or []),
            "eligibility_status": "eligible" if eligibility.get("can_submit") else "review_required",
        }

    def _fake_build_processing_summary_v2(processing_summary, documents, issues, compliance_rate=None):
        status_counts = {"success": len(documents or []), "warning": 0, "error": 0}
        return {
            "total_documents": len(documents or []),
            "successful_extractions": len(documents or []),
            "failed_extractions": 0,
            "total_issues": len(issues or []),
            "severity_breakdown": {"critical": 0, "major": len(issues or []), "medium": 0, "minor": 0},
            "documents": copy.deepcopy(documents or []),
            "documents_found": len(documents or []),
            "verified": len(documents or []),
            "warnings": 0,
            "errors": 0,
            "status_counts": status_counts,
            "document_status": status_counts,
            "compliance_rate": compliance_rate,
            "processing_time_seconds": (processing_summary or {}).get("processing_time_seconds"),
            "processing_time_display": (processing_summary or {}).get("processing_time_display"),
            "processing_time_ms": (processing_summary or {}).get("processing_time_ms"),
            "extraction_quality": (processing_summary or {}).get("extraction_quality"),
            "discrepancies": len(issues or []),
        }

    def _fake_count_issue_severity(issues):
        return {
            "critical": sum(1 for issue in issues if str(issue.get("severity") or "").lower() == "critical"),
            "major": sum(1 for issue in issues if str(issue.get("severity") or "").lower() == "major"),
            "medium": 0,
            "minor": sum(1 for issue in issues if str(issue.get("severity") or "").lower() not in {"critical", "major"}),
        }

    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Any,
        "copy": copy,
        "ComplianceScorer": _FakeComplianceScorer,
        "build_bank_submission_verdict": _fake_build_bank_submission_verdict,
        "_build_submission_eligibility_context": _fake_build_submission_eligibility_context,
        "_build_validation_contract": _fake_build_validation_contract,
        "_run_validation_arbitration_escalation": _fake_run_validation_arbitration_escalation,
        "build_processing_summary_v2": _fake_build_processing_summary_v2,
        "count_issue_severity": _fake_count_issue_severity,
        "validate_and_annotate_response": lambda payload: payload,
        "apply_cycle2_runtime_recovery": lambda payload: payload,
        "backfill_hybrid_secondary_surfaces": lambda payload: payload,
        "enforce_day1_response_contract": lambda payload: payload,
        "settings": SimpleNamespace(DAY1_CONTRACT_ENABLED=False),
        "logger": SimpleNamespace(warning=lambda *args, **kwargs: None),
    }
    exec(compile(module_ast, str(SESSION_REFRESH_PATH), "exec"), namespace)
    return namespace


def test_refresh_structured_result_after_field_override_recomputes_same_session_surfaces() -> None:
    symbols = _load_symbols(
        {
            "sync_structured_result_collections",
            "_normalize_field_key",
            "_normalize_issue_document_ids",
            "_issue_targets_overridden_field",
            "_is_override_resolved_extraction_issue",
            "_filter_resolved_override_issues",
            "_build_field_decisions_from_documents",
            "_copy_documents_to_secondary_surfaces",
            "_resolve_documents_for_refresh",
            "refresh_structured_result_after_field_override",
        }
    )
    refresh = symbols["refresh_structured_result_after_field_override"]

    document = {
        "document_id": "doc-invoice",
        "document_type": "commercial_invoice",
        "name": "Invoice.pdf",
        "extracted_fields": {
            "invoice_number": "DKEL/EXP/2026/114",
            "invoice_date": "2026-04-20",
        },
        "field_details": {
            "invoice_date": {
                "verification": "operator_confirmed",
                "source": "operator_override",
                "confidence": 1.0,
            }
        },
        "review_reasons": [],
        "critical_field_states": {"invoice_date": "found"},
        "status": "success",
    }
    structured_result = {
        "documents": [copy.deepcopy(document)],
        "documents_structured": [copy.deepcopy(document)],
        "document_extraction_v1": {"documents": [copy.deepcopy(document)]},
        "processing_summary": {
            "documents": [copy.deepcopy(document)],
            "processing_time_seconds": 12.3,
            "processing_time_display": "12.3s",
            "processing_time_ms": 12300,
            "extraction_quality": 96,
        },
        "processing_summary_v2": {"documents": [copy.deepcopy(document)]},
        "issues": [
            {
                "title": "Invoice date could not be confirmed",
                "severity": "major",
                "field": "invoice_date",
                "document_ids": ["doc-invoice"],
                "reason_code": "FIELD_NOT_FOUND",
            }
        ],
        "analytics": {},
        "gate_result": {"completeness": 0.95},
        "validation_blocked": False,
    }

    refreshed = asyncio.run(
        refresh(
            structured_result,
            document_id="doc-invoice",
            field_name="invoice_date",
        )
    )

    assert refreshed["issues"] == []
    assert refreshed["bank_verdict"]["verdict"] == "SUBMIT"
    assert refreshed["submission_eligibility"]["can_submit"] is True
    assert refreshed["processing_summary_v2"]["total_issues"] == 0
    assert refreshed["document_extraction_v1"]["documents"][0]["field_details"]["invoice_date"]["verification"] == "operator_confirmed"
    assert refreshed["_operator_field_refresh"]["field_name"] == "invoice_date"
