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
            "review_required_reason": list(eligibility.get("reasons") or []),
            "escalation_triggers": list(eligibility.get("missing_reason_codes") or []),
            "rules_evidence": {
                "missing_reason_codes": list(eligibility.get("missing_reason_codes") or []),
                "unresolved_critical_fields": copy.deepcopy(
                    list(eligibility.get("unresolved_critical_fields") or [])
                ),
                "reason_semantics": {
                    "extraction_failures": list(eligibility.get("missing_reason_codes") or []),
                    "missing_fields": [
                        str(item.get("field") or "")
                        for item in (eligibility.get("unresolved_critical_fields") or [])
                        if isinstance(item, dict) and str(item.get("field") or "").strip()
                    ],
                    "parse_failures": [],
                },
            },
            "evidence_summary": {
                "submission_readiness": "ready" if eligibility.get("can_submit") else "not_ready",
                "reason_semantics": {
                    "extraction_failures": list(eligibility.get("missing_reason_codes") or []),
                    "missing_fields": [
                        str(item.get("field") or "")
                        for item in (eligibility.get("unresolved_critical_fields") or [])
                        if isinstance(item, dict) and str(item.get("field") or "").strip()
                    ],
                    "parse_failures": [],
                },
            },
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

    def _fake_materialize_document_fact_graphs_v1(documents):
        for document in documents or []:
            if not isinstance(document, dict):
                continue
            field_details = document.get("field_details") or {}
            invoice_date_detail = field_details.get("invoice_date") if isinstance(field_details, dict) else {}
            verification = str((invoice_date_detail or {}).get("verification") or "").lower()
            candidate_value = (
                (invoice_date_detail or {}).get("value")
                or (invoice_date_detail or {}).get("rejected_value")
                or (document.get("extracted_fields") or {}).get("invoice_date")
            )
            if verification in {"operator_confirmed", "confirmed"}:
                state = "confirmed"
            elif verification == "operator_rejected":
                state = "operator_rejected"
            else:
                state = "unconfirmed"
            document["fact_graph_v1"] = {
                "version": "fact_graph_v1",
                "document_type": document.get("document_type") or "commercial_invoice",
                "document_subtype": "commercial_invoice",
                "facts": [
                    {
                        "field_name": "invoice_date",
                        "value": candidate_value,
                        "normalized_value": candidate_value,
                        "verification_state": state,
                        "origin": (invoice_date_detail or {}).get("source"),
                    }
                ],
            }
        return documents

    def _fake_build_resolution_queue_v1(documents, *, workflow_stage=None):
        if str((workflow_stage or {}).get("stage") or "").strip().lower() == "validation_results":
            return {
                "version": "resolution_queue_v1",
                "items": [],
                "summary": {
                    "total_items": 0,
                    "user_resolvable_items": 0,
                    "unresolved_documents": 0,
                    "document_counts": {},
                },
            }
        items = []
        unresolved_documents = 0
        for document in documents or []:
            fact_graph = document.get("fact_graph_v1") or {}
            doc_items = []
            for fact in fact_graph.get("facts") or []:
                if str(fact.get("verification_state") or "").lower() not in {"candidate", "unconfirmed", "operator_rejected"}:
                    continue
                doc_items.append(
                    {
                        "document_id": document.get("document_id") or document.get("id"),
                        "field_name": fact.get("field_name"),
                        "candidate_value": fact.get("value"),
                    }
                )
            if doc_items:
                unresolved_documents += 1
                items.extend(doc_items)
        return {
            "version": "resolution_queue_v1",
            "items": items,
            "summary": {
                "total_items": len(items),
                "user_resolvable_items": len(items),
                "unresolved_documents": unresolved_documents,
                "document_counts": {"commercial_invoice": len(items)} if items else {},
            },
        }

    def _fake_build_fact_resolution_v1(documents, *, workflow_stage=None, resolution_queue=None):
        queue = (
            resolution_queue
            if isinstance(resolution_queue, dict)
            else _fake_build_resolution_queue_v1(documents, workflow_stage=workflow_stage)
        )
        items = list(queue.get("items") or [])
        documents_payload = []
        for document in documents or []:
            if str(document.get("document_type") or "").lower() != "commercial_invoice":
                continue
            document_id = document.get("document_id") or document.get("id")
            doc_items = [item for item in items if item.get("document_id") == document_id]
            documents_payload.append(
                {
                    "document_id": document_id,
                    "document_type": "commercial_invoice",
                    "filename": document.get("name") or document.get("filename"),
                    "resolution_required": bool(doc_items),
                    "ready_for_validation": not bool(doc_items),
                    "unresolved_count": len(doc_items),
                    "summary": "needs confirmation" if doc_items else "resolved",
                    "resolution_items": doc_items,
                }
            )
        return {
            "version": "fact_resolution_v1",
            "workflow_stage": workflow_stage or {},
            "documents": documents_payload,
            "summary": {
                "total_documents": len(documents_payload),
                "unresolved_documents": sum(1 for doc in documents_payload if doc["resolution_required"]),
                "total_items": len(items),
                "user_resolvable_items": len(items),
                "ready_for_validation": len(items) == 0,
            },
        }

    def _fake_count_issue_severity(issues):
        return {
            "critical": sum(1 for issue in issues if str(issue.get("severity") or "").lower() == "critical"),
            "major": sum(1 for issue in issues if str(issue.get("severity") or "").lower() == "major"),
            "medium": 0,
            "minor": sum(1 for issue in issues if str(issue.get("severity") or "").lower() not in {"critical", "major"}),
        }

    def _fake_build_workflow_stage(documents, *, validation_status=None):
        unresolved_documents = 0
        unresolved_fields = 0
        for document in documents or []:
            extraction_resolution = (
                document.get("extraction_resolution")
                if isinstance(document.get("extraction_resolution"), dict)
                else {}
            )
            if bool(extraction_resolution.get("required")):
                unresolved_documents += 1
                unresolved_fields += int(extraction_resolution.get("unresolved_count") or 0)
        stage = "validation_results" if unresolved_documents == 0 else "extraction_resolution"
        return {
            "stage": stage,
            "provisional_validation": stage != "validation_results",
            "ready_for_final_validation": stage == "validation_results",
            "unresolved_documents": unresolved_documents,
            "unresolved_fields": unresolved_fields,
            "summary": f"stage={stage} status={validation_status}",
        }

    def _fake_apply_workflow_stage_contract_overrides(
        workflow_stage,
        bank_verdict,
        submission_eligibility,
        validation_contract=None,
        resolution_queue=None,
    ):
        stage = str((workflow_stage or {}).get("stage") or "").strip().lower()
        bank_verdict = copy.deepcopy(bank_verdict or {})
        submission_eligibility = copy.deepcopy(submission_eligibility or {})
        validation_contract = copy.deepcopy(validation_contract or {})
        resolution_queue = copy.deepcopy(resolution_queue or {})
        if stage == "extraction_resolution":
            bank_verdict["verdict"] = "CAUTION"
            bank_verdict["can_submit"] = False
            submission_eligibility["can_submit"] = False
            submission_eligibility["reasons"] = list(submission_eligibility.get("reasons") or []) + [
                "workflow_stage_extraction_resolution"
            ]
            validation_contract["final_verdict"] = "review"
            validation_contract["override_reason"] = "extraction_resolution_pending"
        elif stage == "validation_results":
            submission_eligibility["missing_reason_codes"] = []
            submission_eligibility["unresolved_critical_fields"] = []
            submission_eligibility["unresolved_critical_statuses"] = []
            submission_eligibility["reasons"] = [
                reason
                for reason in list(submission_eligibility.get("reasons") or [])
                if str(reason).strip().lower() != "workflow_stage_extraction_resolution"
            ]
            validation_contract.setdefault("rules_evidence", {})
            validation_contract.setdefault("evidence_summary", {})
            validation_contract["rules_evidence"]["missing_reason_codes"] = []
            validation_contract["rules_evidence"]["unresolved_critical_fields"] = []
            validation_contract["rules_evidence"]["reason_semantics"] = {
                "extraction_failures": [],
                "missing_fields": [],
                "parse_failures": [],
            }
            validation_contract["evidence_summary"]["reason_semantics"] = {
                "extraction_failures": [],
                "missing_fields": [],
                "parse_failures": [],
            }
            validation_contract["review_required_reason"] = [
                reason
                for reason in list(validation_contract.get("review_required_reason") or [])
                if str(reason).strip().lower() != "workflow_stage_extraction_resolution"
            ]
            validation_contract["provisional_validation"] = False
            resolution_queue["items"] = []
            resolution_queue["summary"] = {
                "total_items": 0,
                "user_resolvable_items": 0,
                "unresolved_documents": 0,
                "document_counts": {},
            }
        return {
            "bank_verdict": bank_verdict,
            "submission_eligibility": submission_eligibility,
            "validation_contract": validation_contract,
        }

    def _fake_partition_workflow_stage_issues(issues, documents=None, workflow_stage=None):
        stage = str((workflow_stage or {}).get("stage") or "").strip().lower()
        if stage != "extraction_resolution":
            return {
                "final_issues": copy.deepcopy(list(issues or [])),
                "provisional_issues": [],
            }
        final_issues = []
        provisional_issues = []
        for issue in issues or []:
            if str((issue or {}).get("reason_code") or "").strip().upper() == "FIELD_NOT_FOUND":
                provisional_issues.append(copy.deepcopy(issue))
            else:
                final_issues.append(copy.deepcopy(issue))
        return {
            "final_issues": final_issues,
            "provisional_issues": provisional_issues,
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
        "_apply_workflow_stage_contract_overrides": _fake_apply_workflow_stage_contract_overrides,
        "_partition_workflow_stage_issues": _fake_partition_workflow_stage_issues,
        "materialize_document_fact_graphs_v1": _fake_materialize_document_fact_graphs_v1,
        "build_document_extraction_v1": lambda documents: {
            "documents": copy.deepcopy(list(documents or [])),
        },
        "build_resolution_queue_v1": _fake_build_resolution_queue_v1,
        "build_fact_resolution_v1": _fake_build_fact_resolution_v1,
        "sanitize_public_document_contract_v1": lambda document: copy.deepcopy(document),
        "build_processing_summary_v2": _fake_build_processing_summary_v2,
        "count_issue_severity": _fake_count_issue_severity,
        "build_workflow_stage": _fake_build_workflow_stage,
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
            verification="operator_confirmed",
        )
    )

    assert refreshed["issues"] == []
    assert refreshed["bank_verdict"]["verdict"] == "SUBMIT"
    assert refreshed["submission_eligibility"]["can_submit"] is True
    assert refreshed["processing_summary_v2"]["total_issues"] == 0
    assert refreshed["document_extraction_v1"]["documents"][0]["field_details"]["invoice_date"]["verification"] == "operator_confirmed"
    assert refreshed["workflow_stage"]["stage"] == "validation_results"
    assert refreshed["resolution_queue_v1"]["summary"]["total_items"] == 0
    assert refreshed["fact_resolution_v1"]["summary"]["ready_for_validation"] is True
    assert refreshed["_operator_field_refresh"]["field_name"] == "invoice_date"
    assert refreshed["_operator_field_refresh"]["verification"] == "operator_confirmed"


def test_refresh_structured_result_keeps_submission_provisional_while_extraction_resolution_is_open() -> None:
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
            "invoice_date": None,
        },
        "field_details": {
            "invoice_date": {
                "verification": "not_found",
                "source": "ai_first",
                "confidence": 0.0,
            }
        },
        "review_reasons": [],
        "critical_field_states": {"invoice_date": "missing"},
        "extraction_resolution": {
            "required": True,
            "unresolved_count": 1,
            "summary": "1 field still needs confirmation.",
            "fields": [{"field_name": "invoice_date", "label": "Invoice Date"}],
        },
        "status": "warning",
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
            },
            {
                "title": "Invoice amount mismatches packing list",
                "severity": "major",
                "field": "amount",
                "document_ids": ["doc-invoice"],
                "reason_code": "crossdoc_mismatch",
            },
        ],
        "analytics": {},
        "gate_result": {"completeness": 0.95},
        "validation_blocked": False,
        "bank_verdict": {"verdict": "SUBMIT", "can_submit": True, "action_items": [], "issue_summary": {}},
        "submission_eligibility": {"can_submit": True, "reasons": []},
        "effective_submission_eligibility": {"can_submit": True, "reasons": []},
    }

    refreshed = asyncio.run(
        refresh(
            structured_result,
            document_id="doc-invoice",
            field_name="invoice_number",
            verification="operator_confirmed",
        )
    )

    assert refreshed["workflow_stage"]["stage"] == "extraction_resolution"
    assert refreshed["submission_eligibility"]["can_submit"] is False
    assert "workflow_stage_extraction_resolution" in refreshed["submission_eligibility"]["reasons"]
    assert refreshed["bank_verdict"]["verdict"] == "CAUTION"
    assert refreshed["validation_contract_v1"]["final_verdict"] == "review"
    assert len(refreshed["issues"]) == 1
    assert refreshed["resolution_queue_v1"]["summary"]["total_items"] == 1
    assert refreshed["fact_resolution_v1"]["summary"]["ready_for_validation"] is False
    assert refreshed["issues"][0]["reason_code"] == "crossdoc_mismatch"
    assert len(refreshed["_provisional_issues"]) == 1
    assert refreshed["_provisional_issues"][0]["reason_code"] == "FIELD_NOT_FOUND"


def test_refresh_structured_result_after_rejection_keeps_extraction_issue_open() -> None:
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
        "extracted_fields": {"invoice_number": "DKEL/EXP/2026/114"},
        "field_details": {
            "invoice_date": {
                "verification": "operator_rejected",
                "source": "operator_override",
                "confidence": 0.0,
                "rejected_value": "2026-04-20",
            }
        },
        "review_reasons": ["FIELD_NOT_FOUND"],
        "critical_field_states": {"invoice_date": "unconfirmed"},
        "extraction_resolution": {
            "required": True,
            "unresolved_count": 1,
            "summary": "1 field still needs confirmation.",
            "fields": [{"field_name": "invoice_date", "label": "Invoice Date"}],
        },
        "status": "warning",
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
            verification="operator_rejected",
        )
    )

    assert refreshed["workflow_stage"]["stage"] == "extraction_resolution"
    assert refreshed["submission_eligibility"]["can_submit"] is False
    assert len(refreshed["issues"]) == 0
    assert refreshed["resolution_queue_v1"]["summary"]["total_items"] == 1
    assert len(refreshed["_provisional_issues"]) == 1
    assert refreshed["_provisional_issues"][0]["reason_code"] == "FIELD_NOT_FOUND"
    assert refreshed["_operator_field_refresh"]["verification"] == "operator_rejected"


def test_refresh_structured_result_clears_stale_resolution_contract_state_after_stage_flip() -> None:
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
            "invoice_date": None,
        },
        "field_details": {
            "invoice_date": {
                "verification": "not_found",
                "source": "ai_first",
                "confidence": 0.0,
            }
        },
        "review_reasons": [],
        "critical_field_states": {"invoice_date": "missing"},
        "status": "warning",
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
        "issues": [],
        "analytics": {},
        "gate_result": {"completeness": 0.95},
        "validation_blocked": False,
        "submission_eligibility": {
            "can_submit": True,
            "reasons": ["workflow_stage_extraction_resolution"],
            "missing_reason_codes": ["field_not_found"],
            "unresolved_critical_fields": [
                {"field": "invoice_date", "status": "retry", "reason_code": "field_not_found"}
            ],
            "unresolved_critical_statuses": ["retry"],
        },
        "effective_submission_eligibility": {
            "can_submit": True,
            "reasons": ["workflow_stage_extraction_resolution"],
            "missing_reason_codes": ["field_not_found"],
            "unresolved_critical_fields": [
                {"field": "invoice_date", "status": "retry", "reason_code": "field_not_found"}
            ],
            "unresolved_critical_statuses": ["retry"],
        },
        "validation_contract_v1": {
            "final_verdict": "review",
            "review_required_reason": ["workflow_stage_extraction_resolution"],
            "rules_evidence": {
                "missing_reason_codes": ["field_not_found"],
                "unresolved_critical_fields": [
                    {"field": "invoice_date", "status": "retry", "reason_code": "field_not_found"}
                ],
                "reason_semantics": {
                    "extraction_failures": ["field_not_found"],
                    "missing_fields": ["invoice_date"],
                    "parse_failures": [],
                },
            },
            "evidence_summary": {
                "submission_readiness": "not_ready",
                "reason_semantics": {
                    "extraction_failures": ["field_not_found"],
                    "missing_fields": ["invoice_date"],
                    "parse_failures": [],
                },
            },
        },
    }

    refreshed = asyncio.run(
        refresh(
            structured_result,
            document_id="doc-invoice",
            field_name="invoice_number",
            verification="operator_confirmed",
        )
    )

    assert refreshed["workflow_stage"]["stage"] == "validation_results"
    assert refreshed["resolution_queue_v1"]["summary"]["total_items"] == 0
    assert refreshed["submission_eligibility"]["missing_reason_codes"] == []
    assert refreshed["submission_eligibility"]["unresolved_critical_fields"] == []
    assert "workflow_stage_extraction_resolution" not in refreshed["submission_eligibility"]["reasons"]
    assert refreshed["validation_contract_v1"]["rules_evidence"]["missing_reason_codes"] == []
    assert refreshed["validation_contract_v1"]["rules_evidence"]["unresolved_critical_fields"] == []
    assert refreshed["validation_contract_v1"]["rules_evidence"]["reason_semantics"]["missing_fields"] == []
    assert refreshed["validation_contract_v1"]["evidence_summary"]["reason_semantics"]["missing_fields"] == []
