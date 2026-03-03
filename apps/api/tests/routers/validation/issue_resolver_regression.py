from app.routers.validation.issue_resolver import collect_document_issue_stats, resolve_issue_stats
from app.routers.validation.document_builder import build_document_summaries


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
