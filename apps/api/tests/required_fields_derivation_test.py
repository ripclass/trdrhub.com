"""Unit tests for required_fields_derivation.

These use the actual clauses from the live-verification-ideal LC.pdf
(MT700) so the test is anchored to a real LC, not a synthetic example.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


# Load the module by path so we don't depend on the full app import chain.
_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "extraction"
    / "required_fields_derivation.py"
)
_spec = importlib.util.spec_from_file_location(
    "required_fields_derivation",
    _MODULE_PATH,
)
assert _spec is not None and _spec.loader is not None
required_fields_derivation = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(required_fields_derivation)

derive_required_fields = required_fields_derivation.derive_required_fields
MT700_MANDATORY_FIELDS = required_fields_derivation.MT700_MANDATORY_FIELDS
MT700_SKELETON_FIELDS = required_fields_derivation.MT700_SKELETON_FIELDS


# Real clauses from the live-verification-ideal LC.pdf (the same file we
# upload through Playwright when testing the pipeline end-to-end).
LIVE_LC_CONTEXT = {
    "documents_required": [
        "SIGNED COMMERCIAL INVOICE IN 6 COPIES INDICATING HS CODE, QTY, UNIT PRICE AND TOTAL.",
        (
            "FULL SET OF CLEAN ON-BOARD BILL OF LADING MADE OUT TO ORDER OF ISSUING BANK, "
            "MARKED FREIGHT COLLECT, NOTIFY APPLICANT. BL TO SHOW VESSEL NAME, VOYAGE NO., "
            "CONTAINER NO., SEAL NO., GROSS AND NET WEIGHT."
        ),
        "DETAILED PACKING LIST IN 6 COPIES SHOWING CARTON-WISE BREAKDOWN, G.W., N.W., SIZES.",
        (
            "CERTIFICATE OF ORIGIN ISSUED BY EPB/CHAMBER OF COMMERCE, INDICATING "
            "COUNTRY OF ORIGIN: BANGLADESH."
        ),
        "SGS/INTERTEK INSPECTION CERTIFICATE CONFIRMING QUALITY, QUANTITY & PACKING.",
        "BENEFICIARY CERTIFICATE CONFIRMING GOODS ARE BRAND NEW AND MANUFACTURED IN 2026.",
        "NON-NEGOTIABLE DOCUMENTS TO BE SENT TO APPLICANT WITHIN 5 DAYS OF SHIPMENT.",
        (
            "ALL DOCUMENTS MUST SHOW LC NO. EXP2026BD001 AND BUYER PURCHASE ORDER "
            "NO. GBE-44592."
        ),
    ],
    "additional_conditions": [
        "DOCUMENTS MUST NOT BE DATED EARLIER THAN LC ISSUE DATE.",
        "ANY CORRECTIONS MUST BE AUTHENTICATED.",
        "THIRD-PARTY DOCUMENTS ACCEPTABLE EXCEPT BILL OF EXCHANGE AND INVOICE.",
        "COUNTRY OF ORIGIN MUST BE PRINTED ON ALL CARTONS IN INDELIBLE INK.",
        "NO ISRAELI FLAG VESSELS PERMITTED.",
        (
            "EXPORTER BIN: 000334455-0103 AND EXPORTER TIN: 545342112233 MUST APPEAR "
            "ON ALL DOCUMENTS."
        ),
        "PAYMENT CHARGE USD 50 WILL BE DEDUCTED IF DOCUMENTS ARE FOUND COMPLIANT.",
    ],
}


def _doc_types_in_live_set():
    return [
        "commercial_invoice",
        "bill_of_lading",
        "packing_list",
        "certificate_of_origin",
        "insurance_certificate",
        "inspection_certificate",
        "beneficiary_certificate",
    ]


def test_lc_self_required_includes_all_mt700_mandatory_fields():
    result = derive_required_fields(lc_context={}, document_types_present=[])
    assert result["lc_self_required"] == list(MT700_MANDATORY_FIELDS)
    assert result["lc_skeleton_required"] == list(MT700_SKELETON_FIELDS)


def test_47a_all_documents_clause_extracts_lc_number_and_po_to_every_doc():
    result = derive_required_fields(
        lc_context=LIVE_LC_CONTEXT,
        document_types_present=_doc_types_in_live_set(),
    )
    applies_to_all = set(result["applies_to_all_supporting_docs"])
    # The "ALL DOCUMENTS MUST SHOW LC NO. EXP2026BD001 AND BUYER PURCHASE
    # ORDER NO. GBE-44592" line should hit both fields.
    assert "lc_number" in applies_to_all
    assert "buyer_purchase_order_number" in applies_to_all
    # And the "EXPORTER BIN: ... MUST APPEAR ON ALL DOCUMENTS" line should
    # hit BIN + TIN.
    assert "exporter_bin" in applies_to_all
    assert "exporter_tin" in applies_to_all


def test_per_doc_requirements_have_cross_doc_fields_applied():
    result = derive_required_fields(
        lc_context=LIVE_LC_CONTEXT,
        document_types_present=_doc_types_in_live_set(),
    )
    by_doc = result["by_document_type"]
    for doc_type in _doc_types_in_live_set():
        assert doc_type in by_doc, f"missing per-doc map for {doc_type}"
        fields = set(by_doc[doc_type])
        # Cross-doc fields should be inherited.
        assert "lc_number" in fields
        assert "buyer_purchase_order_number" in fields
        assert "exporter_bin" in fields
        assert "exporter_tin" in fields


def test_46a_invoice_clause_emits_invoice_specific_fields():
    result = derive_required_fields(
        lc_context=LIVE_LC_CONTEXT,
        document_types_present=["commercial_invoice"],
    )
    invoice_fields = set(result["by_document_type"]["commercial_invoice"])
    # "SIGNED COMMERCIAL INVOICE ... INDICATING HS CODE, QTY, UNIT PRICE AND TOTAL"
    assert "hs_code" in invoice_fields
    assert "quantity" in invoice_fields
    assert "unit_price" in invoice_fields
    # "TOTAL" is canonicalized to `amount` (same field, different label).
    assert "amount" in invoice_fields


def test_46a_bl_clause_emits_bl_specific_fields():
    result = derive_required_fields(
        lc_context=LIVE_LC_CONTEXT,
        document_types_present=["bill_of_lading"],
    )
    bl_fields = set(result["by_document_type"]["bill_of_lading"])
    # "BL TO SHOW VESSEL NAME, VOYAGE NO., CONTAINER NO., SEAL NO., GROSS AND NET WEIGHT"
    assert "vessel_name" in bl_fields
    assert "voyage_number" in bl_fields
    assert "container_number" in bl_fields
    assert "seal_number" in bl_fields
    assert "gross_weight" in bl_fields
    assert "net_weight" in bl_fields


def test_46a_packing_list_clause_emits_packing_specific_fields():
    result = derive_required_fields(
        lc_context=LIVE_LC_CONTEXT,
        document_types_present=["packing_list"],
    )
    packing_fields = set(result["by_document_type"]["packing_list"])
    # "DETAILED PACKING LIST ... CARTON-WISE BREAKDOWN, G.W., N.W., SIZES"
    assert "total_packages" in packing_fields
    assert "gross_weight" in packing_fields
    assert "net_weight" in packing_fields
    assert "size_breakdown" in packing_fields


def test_46a_coo_clause_emits_origin_specific_fields():
    result = derive_required_fields(
        lc_context=LIVE_LC_CONTEXT,
        document_types_present=["certificate_of_origin"],
    )
    coo_fields = set(result["by_document_type"]["certificate_of_origin"])
    # "CERTIFICATE OF ORIGIN ISSUED BY EPB/CHAMBER OF COMMERCE, INDICATING COUNTRY OF ORIGIN"
    assert "country_of_origin" in coo_fields
    assert "issuing_authority" in coo_fields


def test_46a_inspection_clause_emits_inspection_agency():
    result = derive_required_fields(
        lc_context=LIVE_LC_CONTEXT,
        document_types_present=["inspection_certificate"],
    )
    inspection_fields = set(result["by_document_type"]["inspection_certificate"])
    # "SGS/INTERTEK INSPECTION CERTIFICATE CONFIRMING ..."
    assert "inspection_agency" in inspection_fields


def test_evidence_links_each_extracted_field_back_to_its_clause():
    result = derive_required_fields(
        lc_context=LIVE_LC_CONTEXT,
        document_types_present=_doc_types_in_live_set(),
    )
    evidence = result["evidence"]
    assert evidence, "expected at least one evidence entry"
    # The cross-doc BIN/TIN clause should produce an evidence entry tagged
    # scope=all that includes both fields.
    bin_tin_entries = [
        e for e in evidence if "exporter_bin" in (e.get("fields") or []) and e.get("scope") == "all"
    ]
    assert bin_tin_entries, "expected an 'all docs' evidence entry for exporter_bin"
    found_match = any(
        "EXPORTER BIN" in (e.get("text") or "").upper() for e in bin_tin_entries
    )
    assert found_match, "evidence text should reference EXPORTER BIN clause"


def test_empty_lc_context_returns_baselines_only():
    result = derive_required_fields(
        lc_context=None,
        document_types_present=["commercial_invoice"],
    )
    invoice_fields = set(result["by_document_type"]["commercial_invoice"])
    # Without any LC clauses we should at least see the per-doc baseline.
    assert "invoice_number" in invoice_fields
    assert "seller" in invoice_fields
    assert "buyer" in invoice_fields
