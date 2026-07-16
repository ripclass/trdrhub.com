"""Deterministic open-account evidence and payment-readiness checks."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.proofline.open_account import run_open_account_checks


def _complete_case(**overrides):
    data = {
        "origin_country": "BD",
        "destination_country": "US",
        "shipment_status": "shipped",
        "shipment_date": date(2026, 7, 1),
        "documents": {
            "purchase_order": {"id": "po-1"},
            "sales_contract": {"id": "contract-1"},
            "commercial_invoice": {"id": "invoice-1"},
            "packing_list": {"id": "packing-1"},
            "transport_document": {"id": "bl-1"},
            "payment_undertaking": {"id": "undertaking-1"},
            "ad_bank_submission_receipt": {"id": "ad-1"},
        },
        "payment_terms": {
            "due_days": 60,
            "trigger": "buyer_invoice_approval",
            "approval_conditions": ["matching PO", "shipment evidence"],
        },
        "invoice_date": date(2026, 7, 3),
        "invoice_approval_date": date(2026, 7, 10),
        "expected_payment_date": date(2026, 9, 8),
        "deduction_terms_reviewed": True,
        "chargeback_terms_reviewed": True,
        "payment_risk_coverage": {
            "type": "foreign_bank_undertaking",
            "provider": "Example foreign bank",
            "reference": "PU-200",
        },
        "ad_bank_submission_date": date(2026, 7, 10),
        "purchase_order": {
            "amount": Decimal("125000.00"),
            "currency": "USD",
            "buyer_name": "US Buyer Inc",
            "seller_name": "BD Exporter Ltd",
        },
        "invoice": {
            "amount": Decimal("125000.00"),
            "currency": "USD",
            "buyer_name": "US Buyer Inc",
            "seller_name": "BD Exporter Ltd",
        },
    }
    data.update(overrides)
    return data


def test_complete_bangladesh_open_account_case_is_clear_and_calculates_payment_date():
    result = run_open_account_checks(_complete_case(expected_payment_date=None))

    assert result.state == "clear"
    assert result.findings == []
    assert result.expected_payment_date == date(2026, 9, 8)
    assert result.rule_references[0]["id"] == "BB-FE-31-2025-PART-D"


def test_missing_core_documents_and_payment_trigger_are_evidence_gaps():
    data = _complete_case(
        origin_country="VN",
        documents={"commercial_invoice": {"id": "invoice-1"}},
        payment_terms={"due_days": 60},
        deduction_terms_reviewed=False,
        chargeback_terms_reviewed=False,
        payment_risk_coverage=None,
        ad_bank_submission_date=None,
    )
    result = run_open_account_checks(data)
    by_id = {finding["source_finding_id"]: finding for finding in result.findings}

    assert result.state == "evidence_incomplete"
    assert "OA-DOC-PO-1" in by_id
    assert "OA-DOC-CONTRACT-1" in by_id
    assert "OA-PAYMENT-TRIGGER-1" in by_id
    assert "OA-DEDUCTIONS-1" in by_id
    assert all(item["expected"] for item in result.findings)
    assert all(item["observed"] for item in result.findings)
    assert all(item["suggested_correction"] for item in result.findings)


def test_po_invoice_value_currency_and_party_mismatches_are_issues():
    result = run_open_account_checks(
        _complete_case(
            invoice={
                "amount": Decimal("124000.00"),
                "currency": "EUR",
                "buyer_name": "Different Buyer LLC",
                "seller_name": "BD Exporter Limited",
            }
        )
    )
    ids = {finding["source_finding_id"] for finding in result.findings}

    assert result.state == "issue_found"
    assert {"OA-AMOUNT-1", "OA-CURRENCY-1", "OA-BUYER-1", "OA-SELLER-1"} <= ids


def test_bangladesh_risk_coverage_and_ad_bank_evidence_are_not_silently_cleared():
    result = run_open_account_checks(
        _complete_case(
            payment_risk_coverage=None,
            ad_bank_submission_date=None,
            documents={
                key: value
                for key, value in _complete_case()["documents"].items()
                if key not in {"payment_undertaking", "ad_bank_submission_receipt"}
            },
        )
    )
    by_id = {finding["source_finding_id"]: finding for finding in result.findings}

    assert result.state == "evidence_incomplete"
    assert by_id["OA-BD-RISK-COVERAGE-1"]["rule_reference"]["article"] == "Part-D, paragraph 39"
    assert by_id["OA-BD-AD-SUBMISSION-1"]["rule_reference"]["article"] == "Part-D, paragraph 44"
    assert "legal guarantee" not in by_id["OA-BD-RISK-COVERAGE-1"]["explanation"].lower()


def test_late_bangladesh_ad_bank_submission_is_an_issue_with_source_reference():
    result = run_open_account_checks(
        _complete_case(ad_bank_submission_date=date(2026, 7, 20))
    )
    finding = next(
        item for item in result.findings if item["source_finding_id"] == "OA-BD-AD-TIMING-1"
    )

    assert result.state == "issue_found"
    assert finding["observed"] == "Submission recorded 19 days after shipment"
    assert finding["rule_reference"]["url"].endswith("jul312025fepd31e.pdf")


def test_financing_request_requires_assignment_and_eligibility_evidence():
    result = run_open_account_checks(
        _complete_case(
            financing_requested=True,
            financing_evidence=None,
            assignment_terms_reviewed=False,
        )
    )
    ids = {finding["source_finding_id"] for finding in result.findings}

    assert "OA-FINANCE-EVIDENCE-1" in ids
    assert "OA-ASSIGNMENT-1" in ids

