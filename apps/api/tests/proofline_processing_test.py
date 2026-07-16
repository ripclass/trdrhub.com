"""Proofline case snapshots, routing, and recommendation safety."""

from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace

import pytest

from app.integrations.proofline.registry import build_adapter_registry
from app.services.proofline.processing import (
    SubmissionValidationError,
    build_case_context,
    recommend_decision,
    validate_submission_context,
)


def _case(**overrides):
    values = {
        "id": uuid.uuid4(),
        "company_id": uuid.uuid4(),
        "payment_arrangement": "open_account",
        "origin_country": "BD",
        "destination_country": "US",
        "currency": "USD",
        "amount": 125000,
        "shipment_date": date(2026, 7, 1),
        "expected_payment_date": None,
        "payment_terms": "Net 60 after buyer invoice approval",
        "transaction_details": {
            "payment_terms": {
                "due_days": 60,
                "trigger": "buyer_invoice_approval",
                "approval_conditions": ["matching PO"],
            },
            "cbam_requested": False,
            "eudr_requested": False,
        },
        "source_lcopilot_session_id": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _party(role, name, country):
    return SimpleNamespace(
        id=uuid.uuid4(), role=role, name=name, country_code=country, identifiers={}
    )


def _document(document_type, fields, *, current=True):
    association = SimpleNamespace(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_type=document_type,
        logical_key=document_type,
        version_number=1,
        correction_round=0,
        is_current=current,
        evidence_metadata={"content_hash": "a" * 64},
    )
    document = SimpleNamespace(
        id=association.document_id,
        document_type=document_type,
        original_filename=f"{document_type}.pdf",
        extracted_fields=fields,
        ocr_confidence=0.96,
    )
    return association, document


def test_case_context_maps_current_evidence_into_payment_first_shape():
    context = build_case_context(
        _case(),
        parties=[
            _party("buyer", "US Buyer Inc", "US"),
            _party("seller", "BD Exporter Ltd", "BD"),
        ],
        documents=[
            _document(
                "purchase_order",
                {"amount": 125000, "currency": "USD", "buyer_name": "US Buyer Inc"},
            ),
            _document(
                "commercial_invoice",
                {"amount": 125000, "currency": "USD", "seller_name": "BD Exporter Ltd"},
            ),
            _document("packing_list", {}, current=False),
        ],
    )

    assert context["payment_arrangement"] == "open_account"
    assert context["purchase_order"]["amount"] == 125000
    assert context["invoice"]["currency"] == "USD"
    assert context["parties"][0]["name"] == "US Buyer Inc"
    assert "packing_list" not in context["documents"]
    assert context["payment_terms"]["due_days"] == 60
    assert context["documents"]["purchase_order"]["hash"] == "a" * 64


def test_customer_transaction_details_cannot_override_computed_case_evidence():
    trade_case = _case(transaction_details={
        "trade_case_id": "forged-case",
        "company_id": "forged-company",
        "parties": [{"name": "forged"}],
        "documents": {"forged": True},
        "ein_verification_results": [{"status": "Verified"}],
        "ein_requested": True,
    })
    context = build_case_context(
        trade_case,
        parties=[_party("buyer", "US Buyer Inc", "US"), _party("seller", "Exporter", "BD")],
        documents=[_document("commercial_invoice", {"amount": 10})],
    )

    assert context["trade_case_id"] == str(trade_case.id)
    assert context["company_id"] == str(trade_case.company_id)
    assert context["parties"][0]["name"] == "US Buyer Inc"
    assert "forged" not in context["documents"]
    assert "ein_verification_results" not in context
    assert context["ein_requested"] is True


def test_submission_requires_counterparties_and_current_evidence():
    with pytest.raises(SubmissionValidationError) as error:
        validate_submission_context(
            build_case_context(
                _case(),
                parties=[_party("buyer", "US Buyer Inc", "US")],
                documents=[],
            )
        )

    assert "at least two parties" in str(error.value).lower()
    assert "at least one current document" in str(error.value).lower()


def test_adapter_registry_routes_lc_and_open_account_without_copying_engines():
    registry = build_adapter_registry()

    assert registry["lcopilot"].module == "lcopilot"
    assert registry["open_account_review"].module == "open_account_review"
    assert registry["document_review"].module == "document_review"
    assert registry["sanctions"].module == "sanctions"
    assert registry["rulhub"].module == "rulhub"


@pytest.mark.parametrize(
    ("checks", "findings", "expected"),
    [
        ([SimpleNamespace(applicable=True, required=True, state="unable_to_assess")], [], "MANUAL_REVIEW_REQUIRED"),
        ([SimpleNamespace(applicable=True, required=True, state="issue_found")], [SimpleNamespace(severity="critical", status="open")], "BLOCKED"),
        ([SimpleNamespace(applicable=True, required=True, state="evidence_incomplete")], [], "ACTION_REQUIRED"),
        ([SimpleNamespace(applicable=True, required=True, state="clear")], [], "CLEAR"),
    ],
)
def test_recommendation_is_fail_closed(checks, findings, expected):
    assert recommend_decision(checks=checks, findings=findings) == expected
