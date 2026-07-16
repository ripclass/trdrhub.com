"""Payment arrangement is the first Proofline applicability decision."""

from __future__ import annotations

import pytest

from app.models import PaymentArrangement
from app.services.proofline.applicability import applicability_for


EXPECTED_PAYMENT_MODULE = {
    PaymentArrangement.LETTER_OF_CREDIT: "lcopilot",
    PaymentArrangement.OPEN_ACCOUNT: "open_account_review",
    PaymentArrangement.ADVANCE_TT: "advance_payment_review",
    PaymentArrangement.PARTIAL_ADVANCE_BALANCE: "staged_payment_review",
    PaymentArrangement.DOCUMENTS_AGAINST_PAYMENT: "documentary_collection_review",
    PaymentArrangement.DOCUMENTS_AGAINST_ACCEPTANCE: "documentary_collection_review",
    PaymentArrangement.BUYER_LED_SUPPLY_CHAIN_FINANCE: "supply_chain_finance_review",
    PaymentArrangement.FACTORING_RECEIVABLES_FINANCE: "receivables_finance_review",
    PaymentArrangement.CONSIGNMENT: "consignment_review",
    PaymentArrangement.OTHER: "payment_terms_review",
}


@pytest.mark.parametrize("arrangement,expected_module", EXPECTED_PAYMENT_MODULE.items())
def test_every_payment_arrangement_has_one_required_payment_review(arrangement, expected_module):
    results = applicability_for(arrangement, context={})
    payment_results = [item for item in results if item.category == "payment"]
    applicable = [item for item in payment_results if item.applicable]

    assert [item.module for item in applicable] == [expected_module]
    assert applicable[0].required is True
    assert applicable[0].reason


def test_lc_and_open_account_never_present_the_other_engine_as_failed():
    lc = {item.module: item for item in applicability_for("letter_of_credit", context={})}
    open_account = {item.module: item for item in applicability_for("open_account", context={})}

    assert lc["lcopilot"].applicable is True
    assert lc["open_account_review"].applicable is False
    assert lc["open_account_review"].state == "not_applicable"
    assert open_account["open_account_review"].applicable is True
    assert open_account["lcopilot"].applicable is False
    assert open_account["lcopilot"].state == "not_applicable"


def test_common_and_contextual_modules_are_explained():
    results = applicability_for(
        "open_account",
        context={
            "cbam_requested": True,
            "eudr_requested": False,
            "ein_requested": True,
            "buyer_requirements_present": True,
        },
    )
    by_module = {item.module: item for item in results}

    assert by_module["document_review"].applicable is True
    assert by_module["sanctions"].applicable is True
    assert by_module["rulhub"].applicable is True
    assert by_module["cbam"].applicable is True
    assert by_module["eudr"].state == "not_applicable"
    assert by_module["ein"].applicable is True
    assert by_module["buyer_requirements"].applicable is True


def test_unknown_payment_arrangement_is_rejected():
    with pytest.raises(ValueError, match="payment arrangement"):
        applicability_for("crypto_on_delivery", context={})

