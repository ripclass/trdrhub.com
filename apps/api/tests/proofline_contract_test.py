"""Proofline shared contract parity and enum continuity."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCHEMAS_PATH = Path("packages/shared-types/python/schemas.py")


def _load_shared_schemas():
    spec = importlib.util.spec_from_file_location("proofline_shared_schemas", SCHEMAS_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_proofline_enum_values_are_complete_and_stable():
    schemas = _load_shared_schemas()

    assert {item.value for item in schemas.PaymentArrangement} == {
        "letter_of_credit",
        "open_account",
        "advance_tt",
        "partial_advance_balance",
        "documents_against_payment",
        "documents_against_acceptance",
        "buyer_led_supply_chain_finance",
        "factoring_receivables_finance",
        "consignment",
        "other",
    }
    assert {item.value for item in schemas.TradeCaseStatus} == {
        "draft",
        "awaiting_payment",
        "submitted",
        "processing",
        "automated_review_complete",
        "awaiting_analyst_review",
        "action_required",
        "customer_resubmitted",
        "final_review",
        "cleared",
        "conditionally_cleared",
        "blocked",
        "cancelled",
        "closed",
    }
    assert {item.value for item in schemas.ProoflineDecision} == {
        "CLEAR",
        "CONDITIONAL_CLEARANCE",
        "ACTION_REQUIRED",
        "MANUAL_REVIEW_REQUIRED",
        "BLOCKED",
        "UNABLE_TO_ASSESS",
    }
    assert {item.value for item in schemas.ProoflineCheckState} == {
        "pending",
        "running",
        "clear",
        "issue_found",
        "evidence_incomplete",
        "not_applicable",
        "unable_to_assess",
        "pending_review",
    }
    assert {item.value for item in schemas.ProoflineFindingStatus} == {
        "open",
        "acknowledged",
        "customer_action_required",
        "corrected",
        "accepted_exception",
        "false_positive",
        "resolved",
        "unable_to_resolve",
    }


def test_proofline_case_contract_supports_lc_and_open_account():
    schemas = _load_shared_schemas()
    base = {
        "id": "72c47e47-a8d4-49f2-9512-c9ca2a15b9d2",
        "case_reference": "PL-7QG4M2",
        "company_id": "25c8cbb4-9d77-4350-9f4e-fffd2f0f7fb2",
        "title": "US buyer July shipment",
        "status": "draft",
        "service_package_id": "proofline_standard",
        "recommended_decision": None,
        "final_decision": None,
        "currency": "USD",
        "amount": "125000.00",
        "origin_country": "BD",
        "destination_country": "US",
        "document_count": 0,
        "finding_counts": {"high": 0, "medium": 0, "low": 0},
        "created_at": "2026-07-16T08:00:00Z",
        "updated_at": "2026-07-16T08:00:00Z",
    }

    lc_case = schemas.TradeCaseSummary.model_validate(
        {**base, "payment_arrangement": "letter_of_credit"}
    )
    open_account_case = schemas.TradeCaseSummary.model_validate(
        {**base, "payment_arrangement": "open_account"}
    )

    assert lc_case.payment_arrangement.value == "letter_of_credit"
    assert open_account_case.payment_arrangement.value == "open_account"


def test_normalized_finding_requires_expected_observed_and_correction():
    schemas = _load_shared_schemas()
    finding = schemas.ProoflineFinding.model_validate(
        {
            "id": "f6ac91d9-2ed4-4645-adbb-f7448837860b",
            "source_module": "open_account",
            "source_finding_id": "OA-PAYMENT-TERMS-1",
            "category": "payment_terms",
            "severity": "high",
            "title": "Payment trigger is not evidenced",
            "explanation": "The submitted contract does not identify the invoice approval trigger.",
            "expected": "A dated, identifiable invoice approval or payment trigger",
            "observed": "No approval trigger was found in the submitted evidence",
            "suggested_correction": "Add or upload the agreed approval and payment terms.",
            "automated": True,
            "visibility": "customer",
            "status": "customer_action_required",
            "rule_reference": None,
            "evidence_references": [],
            "created_at": "2026-07-16T08:00:00Z",
            "updated_at": "2026-07-16T08:00:00Z",
        }
    )

    assert finding.expected.startswith("A dated")
    assert finding.observed.startswith("No approval")
    assert finding.suggested_correction.startswith("Add or upload")


def test_typescript_and_python_contracts_declare_the_same_proofline_values():
    ts_source = Path("packages/shared-types/src/api.ts").read_text(encoding="utf-8")
    py_source = SCHEMAS_PATH.read_text(encoding="utf-8")

    for value in (
        "letter_of_credit",
        "open_account",
        "buyer_led_supply_chain_finance",
        "CONDITIONAL_CLEARANCE",
        "unable_to_assess",
        "customer_action_required",
    ):
        assert value in ts_source
        assert value in py_source

