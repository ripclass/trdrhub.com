"""Authority-matrix item 3 — reconciliation/dedup pass (2026-06-12).

For arithmetic and dates the deterministic layer is authoritative: an
AI finding about a fact the deterministic engine already raised is
dropped (with an authority_dedup event). Matching is conservative —
class + document overlap (+ date-field token overlap for dates) — so a
miss keeps both copies for the veto rather than hiding a discrepancy.
"""

from app.services.validation.authority_matrix import (
    classify_finding,
    reconcile_findings,
)


def _ai_arith() -> dict:
    return {
        "rule": "AI-INV-ARITHMETIC",
        "title": "Invoice line items do not sum to stated total",
        "message": "Sum of line items 459000.00 does not equal the stated total 397050.00",
        "severity": "major",
        "documents": ["commercial_invoice"],
    }


def _det_arith() -> dict:
    return {
        "rule": "CROSSDOC-INV-MATH-001",
        "title": "Invoice arithmetic check failed",
        "message": "Computed check failed: 'invoice.quantity' (30000.0) * 'invoice.unit_price' (15.3) = 459000.0, but 'invoice.total_amount' is 397050.0",
        "severity": "fail",
        "documents": ["invoice"],
    }


def _ai_semantic() -> dict:
    return {
        "rule": "AI-EXAMINER-3",
        "title": "Goods description does not correspond to LC",
        "message": "Invoice describes 'oak furniture' but LC clause 45A requires 'teak furniture'",
        "severity": "major",
        "documents": ["commercial_invoice"],
    }


# ---- classification --------------------------------------------------------


def test_classify_arithmetic_both_sources():
    assert classify_finding(_ai_arith()) == "arithmetic"
    assert classify_finding(_det_arith()) == "arithmetic"


def test_classify_dates_by_rule_and_field():
    assert classify_finding({"rule": "UCP600-14C-PRESENTATION-PERIOD", "title": "x"}) == "dates"
    assert (
        classify_finding({
            "rule": "CROSSDOC-BL-LC-2",
            "message": "'bl.on_board_date' (2026-10-02) is after 'lc.latest_shipment_date' (2026-09-30)",
        })
        == "dates"
    )


def test_classify_semantic_is_other_in_v1():
    assert classify_finding(_ai_semantic()) == "other"


# ---- reconciliation --------------------------------------------------------


def test_arithmetic_dedup_drops_ai_copy_and_logs():
    events = []
    kept = reconcile_findings([_ai_arith()], [_det_arith()], events_out=events)
    assert kept == []
    assert len(events) == 1
    assert events[0]["event"] == "authority_dedup"
    assert events[0]["class"] == "arithmetic"
    assert events[0]["dropped_rule"] == "AI-INV-ARITHMETIC"
    assert events[0]["kept_rule"] == "CROSSDOC-INV-MATH-001"


def test_no_det_counterpart_keeps_ai_finding():
    events = []
    kept = reconcile_findings([_ai_arith()], [], events_out=events)
    assert len(kept) == 1
    assert events == []


def test_semantic_class_never_deduped():
    events = []
    kept = reconcile_findings([_ai_semantic()], [_det_arith()], events_out=events)
    assert len(kept) == 1
    assert events == []


def test_disjoint_documents_keeps_both():
    ai = dict(_ai_arith(), documents=["packing_list"], rule="AI-PL-ARITHMETIC",
              message="Sum of line items mismatch on the packing list")
    events = []
    kept = reconcile_findings([ai], [_det_arith()], events_out=events)
    # invoice (det) vs packing_list (ai) — no doc overlap, both survive
    assert len(kept) == 1
    assert events == []


def test_dates_dedup_requires_field_token_overlap():
    ai = {
        "rule": "AI-EXAMINER-5",
        "title": "Late shipment",
        "message": "'bl.on_board_date' (2026-10-02) is after 'lc.latest_shipment_date' (2026-09-30)",
        "documents": ["bill_of_lading"],
    }
    det_same_fact = {
        "rule": "UCP600-31-LATE-SHIPMENT",
        "message": "'bl.on_board_date' (2026-10-02) exceeds 'lc.latest_shipment_date' (2026-09-30)",
        "documents": ["bl"],
    }
    det_other_date = {
        "rule": "UCP600-14C-PRESENTATION-PERIOD",
        "message": "'presentation.presentation_date' is beyond 'lc.expiry_date'",
        "documents": ["bl"],
    }
    events = []
    kept = reconcile_findings([ai], [det_other_date], events_out=events)
    assert len(kept) == 1  # different date fact — both survive
    assert events == []

    events = []
    kept = reconcile_findings([ai], [det_same_fact], events_out=events)
    assert kept == []  # same date fact — deterministic wins
    assert events[0]["event"] == "authority_dedup"
    assert events[0]["class"] == "dates"


def test_det_findings_never_touched():
    det = [_det_arith()]
    reconcile_findings([_ai_arith()], det)
    assert det == [_det_arith()]


def test_non_dict_entries_pass_through():
    kept = reconcile_findings(["not-a-dict"], [_det_arith()])
    assert kept == ["not-a-dict"]
