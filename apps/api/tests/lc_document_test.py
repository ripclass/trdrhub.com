"""Unit tests for the canonical LCDocument model.

Anchored on the real live-verification-ideal LC.pdf content so the tests
double as a contract: any extractor that fills the same fields the vision
LLM does today must produce an equivalent LCDocument.
"""

from __future__ import annotations

import importlib.util
from datetime import date
from decimal import Decimal
from pathlib import Path


_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "extraction"
    / "lc_document.py"
)
_spec = importlib.util.spec_from_file_location("lc_document", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
lc_document = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lc_document)

LCDocument = lc_document.LCDocument
LCParty = lc_document.LCParty
LCAmount = lc_document.LCAmount
LCExpiry = lc_document.LCExpiry


# What the vision LLM extractor returns for the live-verification-ideal LC.pdf.
# Mirrors the actual fields the multimodal extractor produced when we ran
# job dc4d2122-eaf8-4f18-94c8-190e56e207a1 on 2026-04-08.
VISION_LLM_LC_OUTPUT = {
    "sequence_of_total": "1/1",
    "form_of_documentary_credit": "IRREVOCABLE",
    "lc_number": "EXP2026BD001",
    "issue_date": "2026-04-15",
    "expiry_date": "2026-10-15",
    "expiry_place": "USA",
    "applicable_rules": "UCP LATEST VERSION",
    "applicant": "GLOBAL IMPORTERS INC.\n1250 HUDSON STREET, NEW YORK, USA",
    "beneficiary": "DHAKA KNITWEAR & EXPORTS LTD.\nPLOT 22, DEPZ, SAVAR, DHAKA, BANGLADESH",
    "amount": 458750.00,
    "currency": "USD",
    "available_with": "ANY BANK IN USA",
    "available_by": "NEGOTIATION",
    "port_of_loading": "CHITTAGONG SEA PORT, BANGLADESH",
    "port_of_discharge": "NEW YORK, USA",
    "latest_shipment_date": "2026-09-30",
    "goods_description": (
        "GARMENTS FOR EXPORT MARKET: 100% COTTON KNIT T-SHIRTS, "
        "MENS WOVEN DENIM TROUSERS, GIRLS COTTON DRESSES."
    ),
    "documents_required": [
        "SIGNED COMMERCIAL INVOICE IN 6 COPIES INDICATING HS CODE, QTY, UNIT PRICE AND TOTAL.",
        (
            "FULL SET OF CLEAN ON-BOARD BILL OF LADING MADE OUT TO ORDER OF ISSUING BANK, "
            "MARKED FREIGHT COLLECT, NOTIFY APPLICANT. BL TO SHOW VESSEL NAME, VOYAGE NO., "
            "CONTAINER NO., SEAL NO., GROSS AND NET WEIGHT."
        ),
        "DETAILED PACKING LIST IN 6 COPIES SHOWING CARTON-WISE BREAKDOWN, G.W., N.W., SIZES.",
    ],
    "additional_conditions": [
        "DOCUMENTS MUST NOT BE DATED EARLIER THAN LC ISSUE DATE.",
        (
            "EXPORTER BIN: 000334455-0103 AND EXPORTER TIN: 545342112233 MUST APPEAR "
            "ON ALL DOCUMENTS."
        ),
    ],
    "period_for_presentation": "21 DAYS FROM SHIPMENT DATE",
    "partial_shipments": "ALLOWED",
    "transshipment": "ALLOWED",
    "drafts_at": "AT SIGHT",
    "issuing_bank": {"name": "ICBKCNBJ400", "bic": "ICBKCNBJ400"},
    "advising_bank": {"name": "ICBKUS33XXX", "bic": "ICBKUS33XXX"},
    "charges": "ALL BANK CHARGES OUTSIDE BANGLADESH ON APPLICANT ACCOUNT.",
}


# A legacy `swift_mt700_full.parse_mt700_full` style dict — different key
# names, nested shapes — used to prove the alias-soup adapter works.
LEGACY_MT700_FULL_OUTPUT = {
    "reference": "EXP2026BD001",  # alias for lc_number
    "sequence": "1/1",
    "form_of_doc_credit": "IRREVOCABLE",
    "applicable_rules": "UCP LATEST VERSION",
    "date_of_issue": "260415",  # YYMMDD format
    "expiry_details": {"date": "261015", "place": "USA"},
    "applicant": "GLOBAL IMPORTERS INC., 1250 HUDSON STREET, NEW YORK, USA",
    "beneficiary": "DHAKA KNITWEAR & EXPORTS LTD., PLOT 22, DEPZ, SAVAR, DHAKA, BANGLADESH",
    "credit_amount": {"amount": "458750.00", "currency": "USD"},
    "tolerance": "0",
    "available_with": {"bank": "ANY BANK IN USA", "by": "NEGOTIATION"},
    "shipment": {
        "drafts_at": "AT SIGHT",
        "drawee": "ISSUING BANK",
        "partial_shipments": "ALLOWED",
        "transshipment": "ALLOWED",
    },
    "shipment_details": {
        "port_of_loading_airport_of_departure": "CHITTAGONG SEA PORT, BANGLADESH",
        "port_of_discharge_airport_of_destination": "NEW YORK, USA",
        "latest_date_of_shipment": "260930",
    },
    "description_of_goods": "GARMENTS FOR EXPORT MARKET",
    "docs_required": [
        "SIGNED COMMERCIAL INVOICE IN 6 COPIES INDICATING HS CODE, QTY, UNIT PRICE AND TOTAL.",
    ],
    "additional_conditions": [
        "EXPORTER BIN: 000334455-0103 AND EXPORTER TIN: 545342112233 MUST APPEAR ON ALL DOCUMENTS.",
    ],
    "period_for_presentation": 21,
    "charges": "ALL BANK CHARGES OUTSIDE BANGLADESH ON APPLICANT ACCOUNT.",
}


# An ISO 20022 path output — nested objects, different key names again.
LEGACY_ISO20022_OUTPUT = {
    "format": "iso20022",
    "schema": "tsmt.014",
    "number": "EXP2026BD001",
    "amount": {"value": 458750.00, "currency": "USD"},
    "currency": "USD",
    "applicant": {
        "name": "GLOBAL IMPORTERS INC.",
        "address": {
            "street": "1250 HUDSON STREET",
            "city": "NEW YORK",
            "country": "USA",
            "country_code": "US",
        },
        "bic": None,
    },
    "beneficiary": {
        "name": "DHAKA KNITWEAR & EXPORTS LTD.",
        "address": {
            "street": "PLOT 22, DEPZ",
            "city": "SAVAR",
            "country": "BANGLADESH",
            "country_code": "BD",
        },
    },
    "issuing_bank": {"name": "ICBC", "bic": "ICBKCNBJ400"},
    "advising_bank": {"name": "ICBC USA", "bic": "ICBKUS33XXX"},
    "dates": {
        "expiry": "2026-10-15",
        "place_of_expiry": "USA",
        "latest_shipment": "2026-09-30",
    },
    "ports": {"loading": "CHITTAGONG SEA PORT, BANGLADESH", "discharge": "NEW YORK, USA"},
    "goods_description": "GARMENTS FOR EXPORT MARKET",
    "documents_required": [
        "SIGNED COMMERCIAL INVOICE IN 6 COPIES INDICATING HS CODE, QTY, UNIT PRICE AND TOTAL.",
    ],
    "form_of_doc_credit": "IRREVOCABLE",
    "_extraction_method": "iso20022_xml",
    "_extraction_confidence": 0.95,
}


# =============================================================================
# Tests against the vision LLM dict shape (the primary path today)
# =============================================================================


def test_from_vision_llm_extracts_lc_number():
    doc = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    assert doc.lc_number == "EXP2026BD001"
    assert doc.source_format == "vision_llm"


def test_from_vision_llm_parses_amount_and_currency():
    doc = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    assert doc.amount is not None
    assert doc.amount.value == Decimal("458750.0")
    assert doc.amount.currency == "USD"


def test_from_vision_llm_parses_dates_to_date_objects():
    doc = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    assert doc.issue_date == date(2026, 4, 15)
    assert doc.expiry is not None
    assert doc.expiry.date == date(2026, 10, 15)
    assert doc.expiry.place == "USA"
    assert doc.latest_shipment_date == date(2026, 9, 30)


def test_from_vision_llm_collapses_applicant_into_party_with_address():
    doc = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    assert doc.applicant is not None
    assert doc.applicant.name == "GLOBAL IMPORTERS INC."
    assert doc.applicant.address is not None
    assert "1250 HUDSON STREET" in (doc.applicant.address.raw or "")


def test_from_vision_llm_parses_availability():
    doc = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    assert doc.availability is not None
    assert doc.availability.available_with == "ANY BANK IN USA"
    assert doc.availability.available_by == "NEGOTIATION"


def test_from_vision_llm_parses_period_for_presentation_from_text():
    doc = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    # "21 DAYS FROM SHIPMENT DATE" — coercer should pull the leading int.
    assert doc.period_for_presentation_days == 21


def test_from_vision_llm_documents_required_carries_raw_text():
    doc = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    assert len(doc.documents_required) == 3
    assert "SIGNED COMMERCIAL INVOICE" in doc.documents_required[0].raw_text
    assert "BILL OF LADING" in doc.documents_required[1].raw_text


def test_from_vision_llm_additional_conditions_are_strings():
    doc = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    assert len(doc.additional_conditions) == 2
    assert any("EXPORTER BIN" in c for c in doc.additional_conditions)


def test_from_vision_llm_keeps_optional_fields():
    doc = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    assert doc.partial_shipments == "ALLOWED"
    assert doc.transshipment == "ALLOWED"
    assert doc.drafts is not None
    assert doc.drafts.drafts_at == "AT SIGHT"
    assert doc.charges and "BANK CHARGES" in doc.charges


# =============================================================================
# Tests against the legacy MT700-full alias soup
# =============================================================================


def test_from_legacy_dict_handles_swift_mt700_full_aliases():
    doc = LCDocument.from_legacy_dict(LEGACY_MT700_FULL_OUTPUT)
    assert doc.lc_number == "EXP2026BD001"  # `reference` alias
    assert doc.sequence_of_total == "1/1"
    assert doc.form_of_documentary_credit == "IRREVOCABLE"


def test_from_legacy_dict_handles_yymmdd_dates():
    doc = LCDocument.from_legacy_dict(LEGACY_MT700_FULL_OUTPUT)
    assert doc.issue_date == date(2026, 4, 15)  # parsed from "260415"
    assert doc.expiry is not None
    assert doc.expiry.date == date(2026, 10, 15)
    assert doc.expiry.place == "USA"
    assert doc.latest_shipment_date == date(2026, 9, 30)


def test_from_legacy_dict_handles_credit_amount_dict():
    doc = LCDocument.from_legacy_dict(LEGACY_MT700_FULL_OUTPUT)
    assert doc.amount is not None
    assert doc.amount.value == Decimal("458750.00")
    assert doc.amount.currency == "USD"


def test_from_legacy_dict_handles_nested_availability():
    doc = LCDocument.from_legacy_dict(LEGACY_MT700_FULL_OUTPUT)
    assert doc.availability is not None
    assert doc.availability.available_with == "ANY BANK IN USA"
    assert doc.availability.available_by == "NEGOTIATION"


def test_from_legacy_dict_pulls_drafts_from_nested_shipment():
    doc = LCDocument.from_legacy_dict(LEGACY_MT700_FULL_OUTPUT)
    assert doc.drafts is not None
    assert doc.drafts.drafts_at == "AT SIGHT"
    assert doc.drafts.drawee == "ISSUING BANK"


# =============================================================================
# Tests against the ISO 20022 alias soup
# =============================================================================


def test_from_legacy_dict_handles_iso20022_number_alias():
    doc = LCDocument.from_legacy_dict(LEGACY_ISO20022_OUTPUT)
    assert doc.lc_number == "EXP2026BD001"  # `number` alias
    assert doc.source_format == "iso20022"


def test_from_legacy_dict_handles_iso20022_nested_amount():
    doc = LCDocument.from_legacy_dict(LEGACY_ISO20022_OUTPUT)
    assert doc.amount is not None
    assert doc.amount.value == Decimal("458750.00")
    assert doc.amount.currency == "USD"


def test_from_legacy_dict_handles_iso20022_nested_dates():
    doc = LCDocument.from_legacy_dict(LEGACY_ISO20022_OUTPUT)
    assert doc.expiry is not None
    assert doc.expiry.date == date(2026, 10, 15)
    assert doc.expiry.place == "USA"
    assert doc.latest_shipment_date == date(2026, 9, 30)


def test_from_legacy_dict_handles_iso20022_nested_ports():
    doc = LCDocument.from_legacy_dict(LEGACY_ISO20022_OUTPUT)
    assert doc.port_of_loading == "CHITTAGONG SEA PORT, BANGLADESH"
    assert doc.port_of_discharge == "NEW YORK, USA"


def test_from_legacy_dict_handles_iso20022_structured_party_with_address():
    doc = LCDocument.from_legacy_dict(LEGACY_ISO20022_OUTPUT)
    assert doc.applicant is not None
    assert doc.applicant.name == "GLOBAL IMPORTERS INC."
    assert doc.applicant.address is not None
    assert doc.applicant.address.street == "1250 HUDSON STREET"
    assert doc.applicant.address.city == "NEW YORK"
    assert doc.applicant.address.country == "USA"


def test_from_legacy_dict_carries_iso20022_bic_codes():
    doc = LCDocument.from_legacy_dict(LEGACY_ISO20022_OUTPUT)
    assert doc.issuing_bank is not None
    assert doc.issuing_bank.bic == "ICBKCNBJ400"
    assert doc.advising_bank is not None
    assert doc.advising_bank.bic == "ICBKUS33XXX"


# =============================================================================
# Tests for to_lc_context() — the legacy dict shape downstream code expects
# =============================================================================


def test_to_lc_context_round_trips_lc_number_with_aliases():
    doc = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    ctx = doc.to_lc_context()
    assert ctx["lc_number"] == "EXP2026BD001"
    # Aliases that legacy consumers grep for
    assert ctx["number"] == "EXP2026BD001"
    assert ctx["reference"] == "EXP2026BD001"


def test_to_lc_context_flattens_amount_and_currency():
    doc = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    ctx = doc.to_lc_context()
    assert ctx["amount"] == 458750.0
    assert ctx["currency"] == "USD"


def test_to_lc_context_flattens_applicant_to_string():
    doc = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    ctx = doc.to_lc_context()
    # Legacy consumers read `applicant` as a bare string
    assert isinstance(ctx["applicant"], str)
    assert "GLOBAL IMPORTERS INC." in ctx["applicant"]
    # But the structured party is also available under `applicant_party`
    assert isinstance(ctx["applicant_party"], dict)
    assert ctx["applicant_party"]["name"] == "GLOBAL IMPORTERS INC."


def test_to_lc_context_documents_required_is_list_of_strings():
    doc = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    ctx = doc.to_lc_context()
    assert isinstance(ctx["documents_required"], list)
    assert all(isinstance(item, str) for item in ctx["documents_required"])
    assert len(ctx["documents_required"]) == 3


def test_to_lc_context_dates_are_iso_strings():
    doc = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    ctx = doc.to_lc_context()
    assert ctx["issue_date"] == "2026-04-15"
    assert ctx["expiry_date"] == "2026-10-15"
    assert ctx["latest_shipment_date"] == "2026-09-30"


def test_three_extractor_outputs_produce_equivalent_canonical_lc_number():
    # The same LC parsed via three different parsers should produce the
    # same canonical lc_number — this is the format-agnostic guarantee.
    doc_vision = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    doc_swift = LCDocument.from_legacy_dict(LEGACY_MT700_FULL_OUTPUT)
    doc_iso = LCDocument.from_legacy_dict(LEGACY_ISO20022_OUTPUT)
    assert doc_vision.lc_number == doc_swift.lc_number == doc_iso.lc_number == "EXP2026BD001"


def test_three_extractor_outputs_produce_equivalent_canonical_amount():
    doc_vision = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    doc_swift = LCDocument.from_legacy_dict(LEGACY_MT700_FULL_OUTPUT)
    doc_iso = LCDocument.from_legacy_dict(LEGACY_ISO20022_OUTPUT)
    for doc in (doc_vision, doc_swift, doc_iso):
        assert doc.amount is not None
        assert doc.amount.value == Decimal("458750.00")
        assert doc.amount.currency == "USD"


def test_three_extractor_outputs_produce_equivalent_to_lc_context_amount():
    """The downstream `lc_context` dict shape should be identical for the
    `amount` and `currency` fields regardless of which extractor produced
    the LCDocument."""
    ctx_vision = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT).to_lc_context()
    ctx_swift = LCDocument.from_legacy_dict(LEGACY_MT700_FULL_OUTPUT).to_lc_context()
    ctx_iso = LCDocument.from_legacy_dict(LEGACY_ISO20022_OUTPUT).to_lc_context()

    assert ctx_vision["amount"] == ctx_swift["amount"] == ctx_iso["amount"] == 458750.0
    assert ctx_vision["currency"] == ctx_swift["currency"] == ctx_iso["currency"] == "USD"


# =============================================================================
# from_swift_mt700_full — parses the REAL shape parse_mt700_full() returns
# =============================================================================


# A realistic swift_mt700_full.parse_mt700_full() output — matches the
# nested {"fields": {...}, "raw": {...}} shape the parser actually emits.
SWIFT_MT700_FULL_REAL_SHAPE = {
    "message_type": "MT700",
    "raw": {
        "20": "EXP2026BD001",
        "27": "1/1",
        "40A": "IRREVOCABLE",
        "40E": "UCP LATEST VERSION",
        "31C": "260415",
        "31D": "261015USA",
        "50": "GLOBAL IMPORTERS INC.\n1250 HUDSON STREET, NEW YORK, USA",
        "59": "DHAKA KNITWEAR & EXPORTS LTD.\nPLOT 22, DEPZ, SAVAR, DHAKA, BANGLADESH",
        "32B": "USD458750.00",
        "39A": "0",
        "41D": "ANY BANK IN USA\nBY NEGOTIATION",
        "42C": "AT SIGHT",
        "43P": "ALLOWED",
        "43T": "ALLOWED",
        "44E": "CHITTAGONG SEA PORT, BANGLADESH",
        "44F": "NEW YORK, USA",
        "44C": "260930",
        "45A": "GARMENTS FOR EXPORT MARKET",
        "46A": [
            "SIGNED COMMERCIAL INVOICE IN 6 COPIES INDICATING HS CODE, QTY, UNIT PRICE AND TOTAL.",
        ],
        "47A": [
            "EXPORTER BIN: 000334455-0103 AND EXPORTER TIN: 545342112233 MUST APPEAR ON ALL DOCUMENTS.",
        ],
        "48": "21 DAYS FROM SHIPMENT DATE",
        "71B": "ALL BANK CHARGES OUTSIDE BANGLADESH ON APPLICANT ACCOUNT.",
        "57A": "ICBKCNBJ400",
        "78": "DOCUMENTS TO BE FORWARDED TO ICBC TRADE FINANCE, NEW YORK LIAISON.",
    },
    "blocks": {},
    "fields": {
        "reference": "EXP2026BD001",
        "sequence": "1/1",
        "form_of_doc_credit": "IRREVOCABLE",
        "applicable_rules": "UCP LATEST VERSION",
        "date_of_issue": "2026-04-15",  # already ISO in the real parser
        "expiry_details": {
            "expiry_place_and_date": "261015USA",
            "expiry_date_iso": "2026-10-15",
        },
        "applicant": "GLOBAL IMPORTERS INC.\n1250 HUDSON STREET, NEW YORK, USA",
        "beneficiary": "DHAKA KNITWEAR & EXPORTS LTD.\nPLOT 22, DEPZ, SAVAR, DHAKA, BANGLADESH",
        "credit_amount": {"currency": "USD", "amount": 458750.0, "raw": "USD458750.00"},
        "tolerance": "0",
        "max_credit_amt": None,
        "available_with": {"by": "41D", "details": "ANY BANK IN USA\nBY NEGOTIATION"},
        "shipment": {
            "drafts_at": "AT SIGHT",
            "drawee": None,
            "partial_shipments": "ALLOWED",
            "transshipment": "ALLOWED",
        },
        "period_for_presentation": "21 DAYS FROM SHIPMENT DATE",
        "mixed_payment_details": None,
        "deferred_payment_details": None,
        "shipment_details": {
            "place_of_taking_in_charge_dispatch_from": None,
            "port_of_loading_airport_of_departure": "CHITTAGONG SEA PORT, BANGLADESH",
            "port_of_discharge_airport_of_destination": "NEW YORK, USA",
            "place_of_final_destination_for_transport": None,
            "latest_date_of_shipment": "260930",  # raw YYMMDD, not ISO
            "shipment_period": None,
        },
        "description_of_goods": "GARMENTS FOR EXPORT MARKET",
        "docs_required": [
            "SIGNED COMMERCIAL INVOICE IN 6 COPIES INDICATING HS CODE, QTY, UNIT PRICE AND TOTAL.",
        ],
        "additional_conditions": [
            "EXPORTER BIN: 000334455-0103 AND EXPORTER TIN: 545342112233 MUST APPEAR ON ALL DOCUMENTS.",
        ],
        "charges": "ALL BANK CHARGES OUTSIDE BANGLADESH ON APPLICANT ACCOUNT.",
        "reimbursing_bank": None,
        "advising_bank": "ICBKCNBJ400",
        "instructions_to_paying_accepting_negotiating_bank": "DOCUMENTS TO BE FORWARDED TO ICBC TRADE FINANCE, NEW YORK LIAISON.",
        "sender_to_receiver_info": None,
        "lc_classification": {"types": ["Sight"]},
    },
}


def test_from_swift_mt700_full_extracts_lc_number():
    doc = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    assert doc.lc_number == "EXP2026BD001"
    assert doc.source_format == "swift_mt700"
    assert doc.source_message_type == "MT700"


def test_from_swift_mt700_full_handles_concatenated_currency_amount():
    # The 32B raw form is "USD458750.00" — parser splits it into credit_amount.
    doc = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    assert doc.amount is not None
    assert doc.amount.value == Decimal("458750.0")
    assert doc.amount.currency == "USD"


def test_from_swift_mt700_full_splits_expiry_place_from_combined_field():
    # 31D value "261015USA" -> date 2026-10-15 + place "USA"
    doc = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    assert doc.expiry is not None
    assert doc.expiry.date == date(2026, 10, 15)
    assert doc.expiry.place == "USA"


def test_from_swift_mt700_full_parses_yymmdd_latest_shipment():
    doc = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    # shipment_details.latest_date_of_shipment is still raw YYMMDD in the
    # parser output — our coercer handles it.
    assert doc.latest_shipment_date == date(2026, 9, 30)


def test_from_swift_mt700_full_splits_available_with_details():
    doc = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    assert doc.availability is not None
    assert doc.availability.available_with == "ANY BANK IN USA"
    assert doc.availability.available_by == "BY NEGOTIATION"


def test_from_swift_mt700_full_pulls_drafts_from_nested_shipment():
    doc = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    assert doc.drafts is not None
    assert doc.drafts.drafts_at == "AT SIGHT"


def test_from_swift_mt700_full_reads_partial_and_transshipment_from_shipment():
    doc = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    assert doc.partial_shipments == "ALLOWED"
    assert doc.transshipment == "ALLOWED"


def test_from_swift_mt700_full_parses_applicant_as_party_with_address():
    doc = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    assert doc.applicant is not None
    assert doc.applicant.name == "GLOBAL IMPORTERS INC."
    assert doc.applicant.address is not None
    assert "1250 HUDSON STREET" in (doc.applicant.address.raw or "")


def test_from_swift_mt700_full_reads_ports_from_shipment_details():
    doc = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    assert doc.port_of_loading == "CHITTAGONG SEA PORT, BANGLADESH"
    assert doc.port_of_discharge == "NEW YORK, USA"


def test_from_swift_mt700_full_period_for_presentation_pulls_leading_int():
    doc = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    # "21 DAYS FROM SHIPMENT DATE" -> 21
    assert doc.period_for_presentation_days == 21


def test_from_swift_mt700_full_reads_documents_required_list():
    doc = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    assert len(doc.documents_required) == 1
    assert "SIGNED COMMERCIAL INVOICE" in doc.documents_required[0].raw_text


def test_from_swift_mt700_full_confirmation_instructions_is_none_by_design():
    # swift_mt700_full doesn't parse Field 49; adapter explicitly sets None.
    doc = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    assert doc.confirmation_instructions is None


def test_swift_mt700_full_and_vision_llm_produce_equivalent_canonical_lc_number():
    doc_swift_full = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    doc_vision = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    # Same LC, two parsers, identical canonical lc_number.
    assert doc_swift_full.lc_number == doc_vision.lc_number == "EXP2026BD001"


def test_swift_mt700_full_to_lc_context_produces_canonical_keys():
    doc = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    ctx = doc.to_lc_context()
    assert ctx["lc_number"] == "EXP2026BD001"
    assert ctx["amount"] == 458750.0
    assert ctx["currency"] == "USD"
    assert ctx["expiry_date"] == "2026-10-15"
    assert ctx["expiry_place"] == "USA"
    assert ctx["port_of_loading"] == "CHITTAGONG SEA PORT, BANGLADESH"
    assert ctx["period_for_presentation"] == 21
    assert ctx["partial_shipments"] == "ALLOWED"
    assert ctx["transshipment"] == "ALLOWED"
    assert "documents_required" in ctx
    assert "additional_conditions" in ctx


# =============================================================================
# End-to-end: run the real parse_mt700_full on a real MT700 text block and
# prove the chain swift_mt700_full -> LCDocument -> to_lc_context works.
# =============================================================================


REAL_SWIFT_MT700_TEXT = """:27:1/1
:40A:IRREVOCABLE
:20:EXP2026BD001
:31C:260415
:40E:UCP LATEST VERSION
:31D:261015USA
:50:GLOBAL IMPORTERS INC.
1250 HUDSON STREET, NEW YORK, USA
:59:DHAKA KNITWEAR & EXPORTS LTD.
PLOT 22, DEPZ, SAVAR, DHAKA, BANGLADESH
:32B:USD458750.00
:41D:ANY BANK IN USA
BY NEGOTIATION
:42C:AT SIGHT
:43P:ALLOWED
:43T:ALLOWED
:44E:CHITTAGONG SEA PORT, BANGLADESH
:44F:NEW YORK, USA
:44C:260930
:45A:GARMENTS FOR EXPORT MARKET
:46A:SIGNED COMMERCIAL INVOICE IN 6 COPIES INDICATING HS CODE, QTY, UNIT PRICE AND TOTAL.
:47A:EXPORTER BIN: 000334455-0103 AND EXPORTER TIN: 545342112233 MUST APPEAR ON ALL DOCUMENTS.
:48:21 DAYS FROM SHIPMENT DATE
:71B:ALL BANK CHARGES OUTSIDE BANGLADESH ON APPLICANT ACCOUNT.
"""


# =============================================================================
# from_iso20022 — parses a real ISO 20022 tsmt message into canonical shape
# =============================================================================


# An ISO 20022 dict that includes all the fields step 3 now fills in.
ISO20022_POST_STEP3_OUTPUT = {
    "format": "iso20022",
    "schema": "tsmt.014",
    "_detection_confidence": 0.95,
    "_extraction_confidence": 0.9,
    "_extraction_method": "iso20022_xml",
    "number": "EXP2026BD001",
    "sequence_of_total": "1/1",
    "form_of_doc_credit": "IRREVOCABLE",
    "applicable_rules": "UCP600",
    "issue_date": "2026-04-15",
    "period_for_presentation": 21,
    "additional_conditions": [
        "DOCUMENTS MUST BE IN ENGLISH.",
        "INSURANCE MUST COVER 110% OF INVOICE VALUE.",
    ],
    "available_with": {
        "name": "ICBC USA",
        "bic": "ICBKUS33XXX",
        "address": {"country": "USA"},
    },
    "available_by": "NEGOTIATION",
    "amount": {"value": 458750.0, "currency": "USD"},
    "currency": "USD",
    "applicant": {
        "name": "GLOBAL IMPORTERS INC.",
        "address": {
            "street": "1250 HUDSON STREET",
            "city": "NEW YORK",
            "country": "USA",
            "country_code": "US",
        },
        "bic": None,
    },
    "beneficiary": {
        "name": "DHAKA KNITWEAR & EXPORTS LTD.",
        "address": {
            "street": "PLOT 22, DEPZ",
            "city": "SAVAR",
            "country": "BANGLADESH",
            "country_code": "BD",
        },
    },
    "issuing_bank": {"name": "ICBC", "bic": "ICBKCNBJ400"},
    "advising_bank": {"name": "ICBC USA", "bic": "ICBKUS33XXX"},
    "dates": {
        "expiry": "2026-10-15",
        "place_of_expiry": "NEW YORK",
        "latest_shipment": "2026-09-30",
        "issue_date": "2026-04-15",
    },
    "ports": {"loading": "CHITTAGONG SEA PORT, BANGLADESH", "discharge": "NEW YORK, USA"},
    "goods_description": "GARMENTS FOR EXPORT MARKET",
    "documents_required": [
        "SIGNED COMMERCIAL INVOICE IN 6 COPIES.",
        "FULL SET OF CLEAN ON-BOARD BILL OF LADING.",
    ],
    "partial_shipments": "ALLOWED",
    "transshipment": "NOT ALLOWED",
}


def test_from_iso20022_extracts_all_previously_missing_mandatory_fields():
    doc = LCDocument.from_iso20022(ISO20022_POST_STEP3_OUTPUT)
    # The 6 fields step 3 filled in:
    assert doc.sequence_of_total == "1/1"                 # Field 27
    assert doc.issue_date == date(2026, 4, 15)            # Field 31C
    assert doc.applicable_rules == "UCP600"               # Field 40E
    assert doc.availability is not None                   # Field 41a
    assert doc.availability.available_with == "ICBC USA"
    assert doc.availability.available_with_bic == "ICBKUS33XXX"
    assert doc.availability.available_by == "NEGOTIATION"
    assert len(doc.additional_conditions) == 2            # Field 47A
    assert any("INSURANCE MUST COVER" in c for c in doc.additional_conditions)
    assert doc.period_for_presentation_days == 21         # Field 48


def test_from_iso20022_structured_party_with_address():
    doc = LCDocument.from_iso20022(ISO20022_POST_STEP3_OUTPUT)
    assert doc.applicant is not None
    assert doc.applicant.name == "GLOBAL IMPORTERS INC."
    assert doc.applicant.address is not None
    assert doc.applicant.address.street == "1250 HUDSON STREET"
    assert doc.applicant.address.city == "NEW YORK"
    assert doc.applicant.address.country == "USA"


def test_from_iso20022_tags_source_format_and_schema():
    doc = LCDocument.from_iso20022(ISO20022_POST_STEP3_OUTPUT)
    assert doc.source_format == "iso20022"
    assert doc.source_message_type == "tsmt.014"
    assert doc.extraction_confidence == 0.9


def test_from_iso20022_canonical_ports_and_amount():
    doc = LCDocument.from_iso20022(ISO20022_POST_STEP3_OUTPUT)
    assert doc.port_of_loading == "CHITTAGONG SEA PORT, BANGLADESH"
    assert doc.port_of_discharge == "NEW YORK, USA"
    assert doc.amount is not None
    assert doc.amount.value == Decimal("458750.0")
    assert doc.amount.currency == "USD"


def test_four_extractor_outputs_produce_equivalent_canonical_lc_number():
    """Vision LLM, swift_mt700_full, ISO 20022, and legacy-dict paths all
    produce the same canonical lc_number for the same underlying LC."""
    doc_vision = LCDocument.from_vision_llm_output(VISION_LLM_LC_OUTPUT)
    doc_swift = LCDocument.from_swift_mt700_full(SWIFT_MT700_FULL_REAL_SHAPE)
    doc_iso = LCDocument.from_iso20022(ISO20022_POST_STEP3_OUTPUT)
    doc_legacy = LCDocument.from_legacy_dict(LEGACY_ISO20022_OUTPUT)
    assert (
        doc_vision.lc_number
        == doc_swift.lc_number
        == doc_iso.lc_number
        == doc_legacy.lc_number
        == "EXP2026BD001"
    )


# =============================================================================
# End-to-end: run the real iso20022_lc_extractor on a synthetic XML document
# and prove step 3's helper populates all 6 mandatory fields.
# =============================================================================


SYNTHETIC_ISO20022_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:tsmt.014.001.04">
  <IntatnRptr>
    <MsgPgntn>
      <PgNb>1</PgNb>
      <LastPgInd>true</LastPgInd>
    </MsgPgntn>
    <DocCdtDtls>
      <DocCdtId>EXP2026BD001</DocCdtId>
      <DocCdtFrm>
        <Cd>IRREVOCABLE</Cd>
      </DocCdtFrm>
      <LcAmt Ccy="USD">458750.00</LcAmt>
      <Applcnt>
        <Nm>GLOBAL IMPORTERS INC.</Nm>
      </Applcnt>
      <Bnfcry>
        <Nm>DHAKA KNITWEAR &amp; EXPORTS LTD.</Nm>
      </Bnfcry>
    </DocCdtDtls>
    <DtAndPlcOfIsse>
      <Dt>2026-04-15</Dt>
      <Plc>NEW YORK</Plc>
    </DtAndPlcOfIsse>
    <ApplRules>
      <Cd>UCP</Cd>
      <Vrsn>600</Vrsn>
    </ApplRules>
    <AvlblWth>
      <Nm>ICBC USA</Nm>
      <BICFI>ICBKUS33XXX</BICFI>
    </AvlblWth>
    <AvlblBy>
      <Cd>NEGO</Cd>
    </AvlblBy>
    <PresntnPrd>21</PresntnPrd>
    <AddtlCondtns>
      <Txt>DOCUMENTS MUST BE IN ENGLISH.</Txt>
      <Txt>INSURANCE MUST COVER 110% OF INVOICE VALUE.</Txt>
    </AddtlCondtns>
    <TermsAndConds>
      <XpryDt>2026-10-15</XpryDt>
      <XpryPlc>NEW YORK</XpryPlc>
      <LtstShipmntDt>2026-09-30</LtstShipmntDt>
    </TermsAndConds>
    <ShipmntDtls>
      <PortOfLdg>CHITTAGONG SEA PORT</PortOfLdg>
      <PortOfDschg>NEW YORK</PortOfDschg>
    </ShipmntDtls>
  </IntatnRptr>
</Document>
"""


def test_end_to_end_real_iso20022_extractor_populates_all_mandatory_fields():
    iso_path = (
        Path(__file__).resolve().parents[1]
        / "app" / "services" / "extraction" / "iso20022_lc_extractor.py"
    )
    iso_spec = importlib.util.spec_from_file_location("iso20022_lc_extractor", iso_path)
    assert iso_spec is not None and iso_spec.loader is not None
    iso_module = importlib.util.module_from_spec(iso_spec)
    iso_spec.loader.exec_module(iso_module)

    context = iso_module.extract_iso20022_lc_enhanced(SYNTHETIC_ISO20022_XML)
    doc = LCDocument.from_iso20022(context)

    # LC number (existing coverage, sanity check)
    assert doc.lc_number == "EXP2026BD001"

    # The 6 formerly-missing mandatory fields:
    assert doc.sequence_of_total == "1/1"                       # Field 27
    assert doc.issue_date == date(2026, 4, 15)                  # Field 31C
    assert doc.applicable_rules == "UCP600"                     # Field 40E
    assert doc.availability is not None                         # Field 41a
    assert doc.availability.available_with == "ICBC USA"
    assert doc.availability.available_with_bic == "ICBKUS33XXX"
    assert doc.availability.available_by == "NEGOTIATION"
    assert len(doc.additional_conditions) >= 2                  # Field 47A
    assert any("ENGLISH" in c.upper() for c in doc.additional_conditions)
    assert any("110%" in c for c in doc.additional_conditions)
    assert doc.period_for_presentation_days == 21               # Field 48

    # Also verify the existing-coverage fields still work
    assert doc.amount is not None
    assert doc.amount.value == Decimal("458750.00")
    assert doc.amount.currency == "USD"
    assert doc.expiry is not None
    assert doc.expiry.date == date(2026, 10, 15)
    assert doc.expiry.place == "NEW YORK"
    assert doc.latest_shipment_date == date(2026, 9, 30)


def test_end_to_end_real_swift_parser_into_lc_document():
    # Load the real swift_mt700_full module by path to avoid app import chain.
    swift_path = (
        Path(__file__).resolve().parents[1]
        / "app" / "services" / "extraction" / "swift_mt700_full.py"
    )
    swift_spec = importlib.util.spec_from_file_location("swift_mt700_full", swift_path)
    assert swift_spec is not None and swift_spec.loader is not None
    swift_module = importlib.util.module_from_spec(swift_spec)
    swift_spec.loader.exec_module(swift_module)

    parsed = swift_module.parse_mt700_full(REAL_SWIFT_MT700_TEXT)
    doc = LCDocument.from_swift_mt700_full(parsed)

    assert doc.lc_number == "EXP2026BD001"
    assert doc.sequence_of_total == "1/1"
    assert doc.form_of_documentary_credit == "IRREVOCABLE"
    assert doc.applicable_rules == "UCP LATEST VERSION"
    assert doc.issue_date == date(2026, 4, 15)
    assert doc.expiry is not None
    assert doc.expiry.date == date(2026, 10, 15)
    assert doc.expiry.place == "USA"
    assert doc.amount is not None
    assert doc.amount.value == Decimal("458750.0")
    assert doc.amount.currency == "USD"
    assert doc.port_of_loading == "CHITTAGONG SEA PORT, BANGLADESH"
    assert doc.port_of_discharge == "NEW YORK, USA"
    assert doc.latest_shipment_date == date(2026, 9, 30)
    assert doc.period_for_presentation_days == 21
    assert doc.partial_shipments == "ALLOWED"
    assert doc.transshipment == "ALLOWED"
    # 46A contents
    assert len(doc.documents_required) >= 1
    assert any(
        "COMMERCIAL INVOICE" in d.raw_text for d in doc.documents_required
    )
    # 47A contents
    assert any("EXPORTER BIN" in c for c in doc.additional_conditions)
