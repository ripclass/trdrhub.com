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
