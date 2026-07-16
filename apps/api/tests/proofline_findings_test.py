"""Proofline source-finding normalization preserves provenance and structure."""

from __future__ import annotations

from app.services.proofline.findings import normalize_source_finding


def test_lcopilot_expected_actual_suggestion_fields_are_preserved():
    normalized = normalize_source_finding(
        "lcopilot",
        {
            "rule": "UCP600-14-D",
            "severity": "major",
            "title": "Data conflict",
            "description": "Invoice and credit differ.",
            "expected": "Goods description matching the credit",
            "actual": "Abbreviated conflicting description",
            "suggestion": "Align the invoice wording with the credit.",
            "document_id": "document-1",
        },
    )

    assert normalized["source_finding_id"] == "UCP600-14-D"
    assert normalized["severity"] == "high"
    assert normalized["expected"] == "Goods description matching the credit"
    assert normalized["observed"] == "Abbreviated conflicting description"
    assert normalized["suggested_correction"] == "Align the invoice wording with the credit."
    assert normalized["source_detail_reference"]["source_module"] == "lcopilot"


def test_missing_optional_source_fields_get_explicit_not_source_data():
    normalized = normalize_source_finding(
        "ein",
        {
            "id": "EIN-EXPIRED-1",
            "severity": "warning",
            "title": "Credential expired",
        },
    )

    assert normalized["observed"] == "Not provided by source module"
    assert normalized["expected"] == "Not provided by source module"
    assert normalized["suggested_correction"] == "Review and resolve this finding with an analyst."

