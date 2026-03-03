from app.routers.validation.issue_resolver import collect_document_issue_stats, resolve_issue_stats
from app.routers.validation.document_builder import build_document_summaries
from app.routers.validate import (
    _build_issue_count_invariant_reason,
    _apply_pipeline_verification_gate,
    _build_processing_summary,
    _sum_ledger_discrepancies,
)

def test_collect_document_issue_stats_matches_filename_without_extension():
    issues = [
        {
            "rule": "invoice_total_mismatch",
            "severity": "major",
            "documents": ["Invoice.pdf"],
        },
        {
            "rule": "lc_field_missing",
            "severity": "critical",
            "documents": ["Letter of Credit"],
        },
        {
            "rule": "packing_type_issue",
            "severity": "minor",
            "document_type": "packing_list",
        },
    ]

    issue_by_name, issue_by_type, issue_by_id = collect_document_issue_stats(issues)

    assert resolve_issue_stats("doc-1", "Invoice.pdf", "commercial_invoice", issue_by_name, issue_by_type, issue_by_id)["count"] == 1
    assert resolve_issue_stats("doc-2", "LC.doc", "letter_of_credit", issue_by_name, issue_by_type, issue_by_id)["count"] == 1
    assert resolve_issue_stats("doc-3", "PL_2024.xlsx", "packing_list", issue_by_name, issue_by_type, issue_by_id)["count"] == 1


def test_build_document_summaries_uses_normalized_issue_lookup():
    results = [
        {
            "rule": "invoice_issue",
            "severity": "major",
            "documents": ["Invoice.pdf"],
        },
        {
            "rule": "invoice_name_alias",
            "severity": "minor",
            "document": "commercial_invoice",
        },
    ]
    documents = [
        {
            "id": "doc-1",
            "filename": "Invoice.pdf",
            "document_type": "commercial_invoice",
        },
        {
            "id": "doc-2",
            "filename": "LC.doc",
            "document_type": "letter_of_credit",
        },
    ]

    summaries = build_document_summaries([], results, document_details=documents)
    by_filename = {summary["name"]: summary["discrepancyCount"] for summary in summaries}

    assert by_filename["Invoice.pdf"] == 2
    assert by_filename["LC.doc"] == 0


def test_issue_count_invariant_reason_no_mismatch_when_totals_align():
    reason = _build_issue_count_invariant_reason(
        canonical_total_issues=5,
        source_total_issues=5,
    )
    assert reason is None


def test_issue_count_invariant_reason_flags_mismatch():
    reason = _build_issue_count_invariant_reason(
        canonical_total_issues=5,
        source_total_issues=3,
    )
    assert reason is not None
    assert "canonical_total_issues=5" in reason
    assert "documents_structured.discrepancyCount_sum=3" in reason


def test_processing_summary_carries_ledger_total_as_canonical_total():
    docs = [
        {"extraction_status": "success", "discrepancyCount": 2},
        {"extraction_status": "success", "discrepancyCount": 1},
    ]
    summary = _build_processing_summary(docs, 1.25, total_discrepancies=3)

    assert summary["total_issues"] == 3
    assert summary["discrepancies"] == 3


def test_processing_summary_ignores_stale_legacy_total_inputs():
    docs = [
        {"extraction_status": "success", "discrepancyCount": 2},
        {"extraction_status": "success", "discrepancyCount": 1},
    ]
    summary = _build_processing_summary(docs, 0.75, total_discrepancies=5)

    assert summary["total_issues"] == 3
    assert summary["discrepancies"] == 5


def test_pipeline_verification_gate_marks_invariant_fail_closed():
    payload = {
        "final_verdict": "PASS",
        "ai_verdict": "PASS",
        "ruleset_verdict": "PASS",
        "decision_trace": {},
    }
    out = _apply_pipeline_verification_gate(
        payload,
        mode="hybrid_enforced",
        issue_count_invariant_failure_reason="issue_count_invariant_failed",
    )

    assert out["pipeline_verification_status"] == "UNVERIFIED"
    assert out["pipeline_verification_fail_reasons"]
    assert any(
        reason.startswith("issue_count_invariant")
        for reason in out["pipeline_verification_fail_reasons"]
    )
    assert out["invariant_failure_reason"] == "issue_count_invariant_failed"


def test_pipeline_verification_gate_keeps_verified_when_invariant_matches():
    payload = {
        "final_verdict": "PASS",
        "ai_verdict": "PASS",
        "ruleset_verdict": "PASS",
        "decision_trace": {
            "decision_layers": ["rules", "ai"],
            "decision_mode": "hybrid_enforced",
            "enforcement_applied": True,
        },
    }
    out = _apply_pipeline_verification_gate(payload, mode="hybrid_enforced")

    assert out["pipeline_verification_status"] == "VERIFIED"
    assert out.get("invariant_failure_reason") is None


def test_sum_ledger_discrepancies_uses_discrepancy_count_field():
    docs = [
        {"extraction_status": "success", "discrepancyCount": 2},
        {"extraction_status": "success", "discrepancyCount": 5},
        {"name": "ignore", "discrepancyCount": None},
    ]

    assert _sum_ledger_discrepancies(docs) == 7
