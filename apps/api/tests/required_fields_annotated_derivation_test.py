"""Tests for the annotated required-field derivation.

Locks down the new ``by_document_type_annotated`` output shape and the
per-field provenance the frontend Extract & Review screen reads to render
source-cited missing-field badges (red "46A #2: <clause text>" vs amber
"standard field for bill_of_lading, not LC-required").

The canonical fixture is the real LC at ``tmp/live-verification-ideal/LC.pdf``
so the tests stay anchored to actual 46A / 47A clause text, not synthetic
data that might accidentally match keywords the real world doesn't use.
"""

from __future__ import annotations

from typing import Dict, List

import pytest

from app.services.extraction.required_fields_derivation import (
    derive_required_fields,
)


# The exact 46A and 47A clauses from tmp/live-verification-ideal/LC.pdf.
# These are the ground truth for the annotated derivation tests — if the
# derivation ever changes its behavior against these clauses we want the
# test to fail and force a conscious re-check against the live LC.
LIVE_LC_46A = [
    "SIGNED COMMERCIAL INVOICE IN 6 COPIES INDICATING HS CODE, QTY, UNIT PRICE AND TOTAL.",
    (
        "FULL SET OF CLEAN ON-BOARD BILL OF LADING MADE OUT TO ORDER OF ISSUING BANK, "
        "MARKED FREIGHT COLLECT, NOTIFY APPLICANT. BL TO SHOW VESSEL NAME, VOYAGE NO., "
        "CONTAINER NO., SEAL NO., GROSS AND NET WEIGHT."
    ),
    "DETAILED PACKING LIST IN 6 COPIES SHOWING CARTON-WISE BREAKDOWN, G.W., N.W., SIZES.",
    "CERTIFICATE OF ORIGIN ISSUED BY EPB/CHAMBER OF COMMERCE, INDICATING COUNTRY OF ORIGIN: BANGLADESH.",
    "SGS/INTERTEK INSPECTION CERTIFICATE CONFIRMING QUALITY, QUANTITY & PACKING.",
    "BENEFICIARY CERTIFICATE CONFIRMING GOODS ARE BRAND NEW AND MANUFACTURED IN 2026.",
    "NON-NEGOTIABLE DOCUMENTS TO BE SENT TO APPLICANT WITHIN 5 DAYS OF SHIPMENT.",
]

LIVE_LC_47A = [
    "DOCUMENTS MUST NOT BE DATED EARLIER THAN LC ISSUE DATE.",
    "ANY CORRECTIONS MUST BE AUTHENTICATED.",
    "THIRD-PARTY DOCUMENTS ACCEPTABLE EXCEPT BILL OF EXCHANGE AND INVOICE.",
    "COUNTRY OF ORIGIN MUST BE PRINTED ON ALL CARTONS IN INDELIBLE INK.",
    "NO ISRAELI FLAG VESSELS PERMITTED.",
    "EXPORTER BIN: 000334455-0103 AND EXPORTER TIN: 545342112233 MUST APPEAR ON ALL DOCUMENTS.",
]

DOC_TYPES_PRESENT = [
    "letter_of_credit",
    "commercial_invoice",
    "bill_of_lading",
    "packing_list",
    "certificate_of_origin",
    "inspection_certificate",
    "beneficiary_certificate",
]


@pytest.fixture
def derived() -> dict:
    return derive_required_fields(
        lc_context={
            "documents_required": LIVE_LC_46A,
            "additional_conditions": LIVE_LC_47A,
        },
        document_types_present=DOC_TYPES_PRESENT,
    )


def _find_record(records: List[dict], field: str) -> dict:
    for record in records:
        if record.get("field") == field:
            return record
    raise AssertionError(f"no record for field {field!r}; saw: {[r.get('field') for r in records]}")


# ---------------------------------------------------------------------------
# Shape of the new output
# ---------------------------------------------------------------------------


def test_derive_returns_both_flat_and_annotated_shapes(derived: dict) -> None:
    assert "by_document_type" in derived
    assert "by_document_type_annotated" in derived
    assert "lc_self_required" in derived
    assert "lc_self_required_annotated" in derived
    assert set(derived["by_document_type"].keys()) == set(
        derived["by_document_type_annotated"].keys()
    )


def test_annotated_records_have_canonical_fields(derived: dict) -> None:
    for doc_type, records in derived["by_document_type_annotated"].items():
        assert isinstance(records, list), f"{doc_type} records is not a list"
        for record in records:
            assert "field" in record
            assert "source_type" in record
            assert "source_refs" in record
            assert "clause_texts" in record
            assert "severity" in record
            assert record["source_type"] in {
                "46a",
                "47a",
                "mt700_mandatory",
                "doc_standard",
            }
            assert record["severity"] in {"required", "conventional"}
            assert isinstance(record["source_refs"], list)
            assert isinstance(record["clause_texts"], list)


# ---------------------------------------------------------------------------
# Provenance correctness — the whole point of Part A
# ---------------------------------------------------------------------------


def test_bill_of_lading_fields_cited_from_46a_clause_2(derived: dict) -> None:
    """Fields explicitly named in 46A #2 ('BL TO SHOW VESSEL NAME, VOYAGE NO.,
    CONTAINER NO., SEAL NO., GROSS AND NET WEIGHT') must cite 46A-2."""
    records = derived["by_document_type_annotated"]["bill_of_lading"]
    for field in ("vessel_name", "voyage_number", "container_number", "seal_number", "gross_weight", "net_weight"):
        rec = _find_record(records, field)
        assert rec["source_type"] == "46a", f"{field} should be 46a-sourced"
        assert "46A-2" in rec["source_refs"], f"{field} should cite 46A-2"
        assert rec["severity"] == "required"
        assert any("BILL OF LADING" in t.upper() for t in rec["clause_texts"])


def test_exporter_bin_tin_cited_from_47a_clause_6(derived: dict) -> None:
    """47A #6 says 'EXPORTER BIN ... MUST APPEAR ON ALL DOCUMENTS'.  Every
    supporting doc (not the LC) should carry exporter_bin / exporter_tin
    with source_type='47a' and source_refs=['47A-6']."""
    for doc_type in ("commercial_invoice", "bill_of_lading", "certificate_of_origin", "packing_list"):
        records = derived["by_document_type_annotated"][doc_type]
        bin_rec = _find_record(records, "exporter_bin")
        tin_rec = _find_record(records, "exporter_tin")
        assert bin_rec["source_type"] == "47a"
        assert tin_rec["source_type"] == "47a"
        assert "47A-6" in bin_rec["source_refs"]
        assert "47A-6" in tin_rec["source_refs"]
        assert bin_rec["severity"] == "required"
        assert tin_rec["severity"] == "required"


def test_bl_number_is_doc_standard_not_46a_required(derived: dict) -> None:
    """The live LC 46A #2 doesn't mention a BL Number explicitly — it names
    vessel/voyage/container/seal/weights.  So bl_number should be flagged
    as a doc_standard convention (amber), not as 46a-required (red).

    This was the key false-positive the user saw live: Bill of Lading
    review screen showing 'BL Number - Missing — required by LC' even
    though no LC clause demands a BL Number."""
    records = derived["by_document_type_annotated"]["bill_of_lading"]
    bl_record = _find_record(records, "bl_number")
    assert bl_record["source_type"] == "doc_standard"
    assert bl_record["severity"] == "conventional"
    assert bl_record["source_refs"] == []


def test_certificate_number_is_doc_standard_on_all_cert_docs(derived: dict) -> None:
    """None of the 46A clauses name a 'certificate number' — they specify
    issuer (EPB/Chamber), content (quality/quantity/packing), or subject
    (brand new goods).  Certificate Number on CoO / Inspection /
    Beneficiary should be amber-conventional."""
    for doc_type in ("certificate_of_origin", "inspection_certificate", "beneficiary_certificate"):
        records = derived["by_document_type_annotated"][doc_type]
        cert_record = _find_record(records, "certificate_number")
        assert cert_record["source_type"] == "doc_standard"
        assert cert_record["severity"] == "conventional"


def test_packing_list_number_is_doc_standard(derived: dict) -> None:
    """46A #3 ('DETAILED PACKING LIST IN 6 COPIES SHOWING CARTON-WISE
    BREAKDOWN, G.W., N.W., SIZES') doesn't name a packing-list number."""
    records = derived["by_document_type_annotated"]["packing_list"]
    pl_record = _find_record(records, "packing_list_number")
    assert pl_record["source_type"] == "doc_standard"
    assert pl_record["severity"] == "conventional"


def test_invoice_hs_code_and_quantity_cited_from_46a_clause_1(derived: dict) -> None:
    """46A #1 explicitly says 'INDICATING HS CODE, QTY, UNIT PRICE AND
    TOTAL' — those four fields should be 46a-required on the invoice."""
    records = derived["by_document_type_annotated"]["commercial_invoice"]
    for field in ("hs_code", "quantity", "unit_price", "amount"):
        rec = _find_record(records, field)
        assert rec["source_type"] == "46a"
        assert "46A-1" in rec["source_refs"]
        assert rec["severity"] == "required"


def test_lc_itself_seeded_with_mt700_mandatory_records(derived: dict) -> None:
    """The LC's own required field list must have source_type='mt700_mandatory'
    — these fields are required by the MT700 spec regardless of clauses."""
    records = derived["by_document_type_annotated"]["letter_of_credit"]
    assert records, "letter_of_credit should have annotated records"
    for record in records:
        assert record["source_type"] == "mt700_mandatory"
        assert record["severity"] == "required"
        assert record["source_refs"]  # always has an MT700 field tag
        assert any("Field" in ref for ref in record["source_refs"])


def test_lc_does_not_require_itself(derived: dict) -> None:
    """The LC must NOT end up with cross-doc applies-to-all records from
    47A — it IS the source of those requirements, not a doc that has to
    satisfy them."""
    records = derived["by_document_type_annotated"]["letter_of_credit"]
    # No record should cite 47A-6 (exporter BIN on all documents) — the
    # LC itself doesn't need to carry exporter_bin.
    for record in records:
        assert "47A-6" not in record.get("source_refs", [])


# ---------------------------------------------------------------------------
# Backward compat — flat keys still work
# ---------------------------------------------------------------------------


def test_flat_by_document_type_contains_same_fields_as_annotated(derived: dict) -> None:
    for doc_type, flat_fields in derived["by_document_type"].items():
        annotated_records = derived["by_document_type_annotated"][doc_type]
        annotated_fields = sorted(r["field"] for r in annotated_records)
        assert sorted(flat_fields) == annotated_fields


def test_evidence_list_preserved(derived: dict) -> None:
    """The existing ``evidence`` list was used by older debugging screens
    and must still be emitted unchanged."""
    assert "evidence" in derived
    assert isinstance(derived["evidence"], list)
    # At minimum we should have evidence entries for 46A-2, 46A-4, 47A-6.
    sources = {e.get("source") for e in derived["evidence"]}
    assert "46A-2" in sources
    assert "46A-4" in sources
    assert "47A-6" in sources


# ---------------------------------------------------------------------------
# Provenance merge semantics — a field demanded by BOTH 46A and 47A
# ---------------------------------------------------------------------------


def test_merge_upgrades_doc_standard_when_clause_later_demands_it() -> None:
    """If a baseline ``doc_standard`` field is later demanded by a clause,
    the record should upgrade to the clause's source_type and severity."""
    result = derive_required_fields(
        lc_context={
            "documents_required": [
                "COMMERCIAL INVOICE SHOWING INVOICE NUMBER AND INVOICE DATE.",
            ],
            "additional_conditions": [],
        },
        document_types_present=["commercial_invoice"],
    )
    records = result["by_document_type_annotated"]["commercial_invoice"]
    inv_num = _find_record(records, "invoice_number")
    # 46A #1 explicitly says "INVOICE NUMBER" — should upgrade from
    # doc_standard to 46a-required.
    assert inv_num["source_type"] == "46a"
    assert inv_num["severity"] == "required"
    assert "46A-1" in inv_num["source_refs"]


def test_carton_marking_clauses_do_not_create_requirements() -> None:
    """47A #4 ('COUNTRY OF ORIGIN MUST BE PRINTED ON ALL CARTONS IN
    INDELIBLE INK') is a packaging instruction, not a data-field
    requirement.  It must not produce any annotated records."""
    result = derive_required_fields(
        lc_context={
            "documents_required": [],
            "additional_conditions": [
                "COUNTRY OF ORIGIN MUST BE PRINTED ON ALL CARTONS IN INDELIBLE INK.",
            ],
        },
        document_types_present=["commercial_invoice"],
    )
    records = result["by_document_type_annotated"]["commercial_invoice"]
    for record in records:
        # No record should cite the carton-marking clause
        assert "47A-1" not in record["source_refs"] or record["source_type"] == "doc_standard"
