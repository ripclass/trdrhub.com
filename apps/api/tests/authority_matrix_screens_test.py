"""Authority-matrix items 4+5 — presence + semantic screens (2026-06-12).

Item 4: a deterministic "(missing)" finding contradicted by the
extraction payload is an alias gap (our plumbing), not the customer's
discrepancy — demoted to advisory + authority_presence_conflict event.
Genuinely-missing refs keep their severity.

Item 5: semantic-class strict-equality comparisons where one value
contains the other after normalization (name-with-address, fuller goods
description) are demoted to advisory; real semantic mismatches keep
severity and are excluded from the auto-confirm bypass (classification
test here; the routing predicate lives in validation_execution).

Fixtures mirror the live 2026-06-12 US-VN smoke findings.
"""

from app.services.validation.authority_matrix import (
    build_extracted_lookup,
    classify_finding,
    missing_refs,
    screen_presence_findings,
    screen_semantic_findings,
)


def _meridian() -> dict:
    return {
        "rule": "UCP600-18A",
        "title": "Invoice buyer does not match LC applicant",
        "message": "'invoice.buyer_name' ('MERIDIAN HOME GOODS LLC') does not match 'lc.applicant_name' ('MERIDIAN HOME GOODS LLC, 2201 HARBOR BLVD, COSTA MESA')",
        "expected": "lc.applicant_name = MERIDIAN HOME GOODS LLC, 2201 HARBOR BLVD, COSTA MESA",
        "found": "invoice.buyer_name = MERIDIAN HOME GOODS LLC",
        "severity": "major",
        "documents": ["invoice", "lc"],
    }


def _carrier_missing() -> dict:
    return {
        "rule": "ISBP745-E5",
        "title": "Required field 'bill_of_lading.carrier_name' is missing",
        "message": "Required field 'bill_of_lading.carrier_name' is missing",
        "severity": "major",
        "documents": ["bl"],
    }


def _insurance_currency_missing() -> dict:
    return {
        "rule": "CROSSDOC-INS-LC-2",
        "title": "Insurance currency mismatch",
        "message": "'insurance_doc.currency_code' (missing) does not match 'lc.currency_code' ('USD')",
        "severity": "major",
        "documents": ["insurance_doc", "lc"],
    }


# ---- classification --------------------------------------------------------


def test_missing_marker_classifies_presence_payload():
    assert classify_finding(_carrier_missing()) == "presence_payload"
    assert classify_finding(_insurance_currency_missing()) == "presence_payload"
    assert missing_refs(_carrier_missing()) == {("bl", "carrier_name")}


def test_two_sided_party_comparison_classifies_semantic():
    assert classify_finding(_meridian()) == "semantic"


def test_arithmetic_still_beats_presence():
    f = {
        "rule": "CROSSDOC-INV-MATH-001",
        "message": "'invoice.computed_total' (missing) does not match stated total",
    }
    assert classify_finding(f) == "arithmetic"


# ---- item 4: presence screen ----------------------------------------------


def test_presence_conflict_demotes_to_advisory_with_event():
    lookup = build_extracted_lookup({
        "bill_of_lading": {"carrier": "MAERSK LINE A/S", "vessel": "EMMA"},
    })
    events = []
    out = screen_presence_findings([_carrier_missing()], lookup, events_out=events)
    assert out[0]["severity"] == "advisory"
    assert out[0]["needs_review"] is True
    assert out[0]["_authority_presence_conflict"][0]["extracted_under"] == "carrier"
    assert events[0]["event"] == "authority_presence_conflict"
    assert events[0]["severity_from"] == "major"


def test_genuinely_missing_field_keeps_severity():
    lookup = build_extracted_lookup({
        "bill_of_lading": {"vessel": "EMMA", "voyage": "12W"},  # no carrier anywhere
    })
    events = []
    out = screen_presence_findings([_carrier_missing()], lookup, events_out=events)
    assert out[0]["severity"] == "major"
    assert events == []


def test_suffix_token_match_currency_code():
    lookup = build_extracted_lookup({
        "insurance_certificate": {"currency": "USD", "policy_number": "GDI-1"},
    })
    events = []
    out = screen_presence_findings([_insurance_currency_missing()], lookup, events_out=events)
    assert out[0]["severity"] == "advisory"
    assert events[0]["contradicted"][0]["doc"] == "insurance_doc"


def test_mixed_refs_one_genuinely_missing_keeps_severity():
    f = {
        "rule": "X-1",
        "message": "'bl.carrier_name' (missing) and 'bl.original_set' (missing)",
        "severity": "major",
    }
    lookup = build_extracted_lookup({"bill_of_lading": {"carrier": "MAERSK"}})
    events = []
    out = screen_presence_findings([f], lookup, events_out=events)
    assert out[0]["severity"] == "major"  # original_set really absent — conservative
    assert events == []


def test_doc_scoped_equivalent_invoice_issuer_is_beneficiary():
    f = {
        "rule": "CROSSDOC-INV-LC-4",
        "message": "'invoice.issuer_name' (missing) does not match 'lc.beneficiary_name' ('HAI LONG FURNITURE')",
        "severity": "major",
    }
    lookup = build_extracted_lookup({
        "invoice": {"beneficiary": "HAI LONG FURNITURE EXPORT JSC", "amount": 414000},
    })
    events = []
    out = screen_presence_findings([f], lookup, events_out=events)
    assert out[0]["severity"] == "advisory"
    assert events[0]["contradicted"][0]["extracted_under"] == "beneficiary"


def test_equivalents_are_doc_scoped_not_global():
    # An inspection cert's issuer is the inspection company — extraction
    # having a "beneficiary" key must NOT satisfy issuer_name there.
    f = {
        "rule": "X-2",
        "message": "'inspection.issuer_name' (missing)",
        "severity": "major",
    }
    lookup = build_extracted_lookup({
        "inspection_certificate": {"beneficiary": "SOMEONE", "result": "PASSED"},
    })
    events = []
    out = screen_presence_findings([f], lookup, events_out=events)
    assert out[0]["severity"] == "major"
    assert events == []


def test_non_presence_findings_untouched():
    events = []
    out = screen_presence_findings([_meridian()], {}, events_out=events)
    assert out[0]["severity"] == "major"
    assert events == []


# ---- item 5: semantic screen -----------------------------------------------


def test_meridian_containment_demoted_to_advisory():
    events = []
    out = screen_semantic_findings([_meridian()], events_out=events)
    assert out[0]["severity"] == "advisory"
    assert out[0]["ai_assessed"] is True
    assert events[0]["event"] == "authority_semantic_demote"
    assert events[0]["relation"] == "containment"


def test_real_party_mismatch_keeps_severity():
    f = dict(_meridian())
    f["found"] = "invoice.buyer_name = PACIFIC TRADING COMPANY INC"
    events = []
    out = screen_semantic_findings([f], events_out=events)
    assert out[0]["severity"] == "major"
    assert events == []


def test_short_values_never_demoted():
    f = dict(_meridian())
    f["expected"] = "lc.applicant_name = ACME"
    f["found"] = "invoice.buyer_name = ACME LLC"
    events = []
    out = screen_semantic_findings([f], events_out=events)
    assert out[0]["severity"] == "major"  # shorter side under 8 chars — too risky
    assert events == []


def test_one_sided_semantic_finding_untouched():
    f = {
        "rule": "UCP600-18A",
        "message": "'invoice.buyer_name' (missing) does not match 'lc.applicant_name' ('X CORP')",
        "severity": "major",
    }
    # classified presence_payload, not semantic — semantic screen skips it
    events = []
    out = screen_semantic_findings([f], events_out=events)
    assert out[0]["severity"] == "major"
    assert events == []


def test_goods_description_fuller_invoice_text_demoted():
    f = {
        "rule": "UCP600-18C",
        "title": "Goods description mismatch",
        "message": "'invoice.goods_description' does not match 'lc.goods_description'",
        "expected": "lc.goods_description = SOLID OAK DINING FURNITURE",
        "found": "invoice.goods_description = SOLID OAK DINING FURNITURE, 6-PIECE SETS, FSC CERTIFIED",
        "severity": "major",
    }
    events = []
    out = screen_semantic_findings([f], events_out=events)
    assert out[0]["severity"] == "advisory"
    assert events[0]["event"] == "authority_semantic_demote"


def _incoterm_finding(invoice_term: str, lc_term: str) -> dict:
    return {
        "rule": "ISBP821-C9",
        "title": "Incoterm mismatch",
        "message": f"'invoice.incoterm' ('{invoice_term}') does not match 'lc.incoterm' ('{lc_term}')",
        "expected": f"lc.incoterm = {lc_term}",
        "found": f"invoice.incoterm = {invoice_term}",
        "severity": "major",
        "documents": ["invoice", "lc"],
    }


def test_incoterm_code_vs_code_plus_place_demoted():
    # Live ISBP821-C9 false positive (DE-CN + BD-CN, 2026-06-12): the
    # invoice's "FCA SHANGHAI (INCOTERMS 2020)" is MORE correct than the
    # LC's bare "FCA" — the named place is mandatory under Incoterms.
    events = []
    out = screen_semantic_findings(
        [_incoterm_finding("FCA SHANGHAI (INCOTERMS 2020)", "FCA")], events_out=events,
    )
    assert out[0]["severity"] == "advisory"
    assert events[0]["relation"] == "incoterm_code_prefix"

    events = []
    out = screen_semantic_findings(
        [_incoterm_finding("CFR CHATTOGRAM (INCOTERMS 2020)", "CFR")], events_out=events,
    )
    assert out[0]["severity"] == "advisory"


def test_real_incoterm_mismatch_keeps_severity():
    events = []
    out = screen_semantic_findings(
        [_incoterm_finding("CIF LONG BEACH", "FOB")], events_out=events,
    )
    assert out[0]["severity"] == "major"  # FOB vs CIF — genuinely different terms
    assert events == []


def test_incoterm_code_prefix_requires_word_boundary():
    # "FCASTLE ROAD" must not satisfy "FCA" — prefix needs the space.
    events = []
    out = screen_semantic_findings(
        [_incoterm_finding("FCASTLE ROAD", "FCA")], events_out=events,
    )
    assert out[0]["severity"] == "major"
    assert events == []
