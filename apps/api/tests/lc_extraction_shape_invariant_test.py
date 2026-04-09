"""LC extraction shape invariant test.

Locks down the end-to-end shape contract from raw LLM output all the way to
the intake card and Extract & Review screen. Would have caught the
``{value, confidence}`` wrapper leak fixed in commit 8cc27c7a on the first
PR — that bug slipped through for 3 weeks because the ``_wrap_ai_result_with_default_confidence``
helper was silently producing dict-shaped payloads and downstream shaping
code in ``_shape_lc_financial_payload`` only had explicit unwrap branches for
applicant / beneficiary / amount.

The contract under test:

    realistic vision-LLM output (flat scalars per _MT700_ONE_SHOT_EXAMPLE)
        → _wrap_ai_result_with_default_confidence   (sidecar feeder)
        → _build_default_field_details_from_wrapped_result  (build confidence sidecar)
        → _unwrap_confidence_scalars_in_place       (flatten payload)
        → _shape_lc_financial_payload               (downstream unwrap branches)
        → LCDocument.from_legacy_dict               (canonical round trip)
        → LCDocument.to_lc_context                  (re-emit legacy shape)
        → build_lc_intake_summary                   (intake card data)

At every hop we assert the 9 MT700 skeleton fields are SCALARS (str / float /
int / list), not dicts. If any step re-introduces a dict shape for a scalar
field, the test fails loudly.

The 9 skeleton fields (per reference_mt700_field_priority.md):

    lc_number           (Field 20)
    amount              (Field 32B, paired with currency)
    currency            (Field 32B currency code)
    applicant           (Field 50)
    beneficiary         (Field 59)
    goods_description   (Field 45A)
    documents_required  (Field 46A — list of strings)
    expiry_date         (Field 31D)
    latest_shipment_date (Field 44C)
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from app.routers.validation.lc_intake import build_lc_intake_summary
from app.services.extraction.ai_first_extractor import (
    _build_default_field_details_from_wrapped_result,
    _unwrap_confidence_scalars_in_place,
    _wrap_ai_result_with_default_confidence,
)
from app.services.extraction.launch_pipeline import _shape_lc_financial_payload
from app.services.extraction.lc_document import LCDocument


# Fields the vision LLM returns at the top level as scalar strings, per the
# _MT700_ONE_SHOT_EXAMPLE in multimodal_document_extractor.py.  If a new
# field gets added to the one-shot example, add it here too.
_TOP_LEVEL_SCALAR_FIELDS = (
    "lc_number",
    "form_of_documentary_credit",
    "currency",
    "issue_date",
    "expiry_date",
    "latest_shipment_date",
    "goods_description",
    "partial_shipments",
    "transshipment",
)


def _realistic_vision_llm_output() -> Dict[str, Any]:
    """Emulate what the L2/L3 vision LLM returns for a real MT700 LC.

    Follows the structure of _MT700_ONE_SHOT_EXAMPLE literally:
        - scalars at top level for lc_number, form_of_documentary_credit,
          issue_date, expiry_date, currency, latest_shipment_date, etc.
        - amount as a scalar number
        - applicant / beneficiary as scalar strings (not nested objects)
        - documents_required as an array of strings
    """
    return {
        "lc_number": "EXP2026BD001",
        "sequence_of_total": "1/1",
        "form_of_documentary_credit": "IRREVOCABLE",
        "issue_date": "2026-04-15",
        "applicable_rules": "UCP LATEST VERSION",
        "expiry_date": "2026-10-15",
        "expiry_place": "DHAKA",
        "applicant": "GLOBAL IMPORTERS INC., 1250 HUDSON STREET, NEW YORK, USA",
        "beneficiary": "DHAKA KNITWEAR & EXPORTS LTD., PLOT 22, DEPZ, SAVAR, DHAKA, BANGLADESH",
        "amount": 250000.00,
        "currency": "USD",
        "amount_tolerance": "5/5",
        "available_with": "ANY BANK",
        "available_by": "NEGOTIATION",
        "partial_shipments": "ALLOWED",
        "transshipment": "NOT ALLOWED",
        "port_of_loading": "CHATTOGRAM, BANGLADESH",
        "port_of_discharge": "NEW YORK, USA",
        "latest_shipment_date": "2026-08-30",
        "goods_description": "READY-MADE GARMENTS AS PER PROFORMA INVOICE GBE-44592",
        "documents_required": [
            "COMMERCIAL INVOICE IN 6 COPIES",
            "FULL SET CLEAN ON-BOARD BILL OF LADING",
            "PACKING LIST IN 6 COPIES",
            "CERTIFICATE OF ORIGIN",
        ],
        "additional_conditions": [
            "ALL DOCUMENTS MUST SHOW LC NO. EXP2026BD001",
            "EXPORTER BIN: 000334455-0103 AND EXPORTER TIN: 545342112233 MUST APPEAR ON ALL DOCUMENTS",
        ],
        "period_for_presentation": 21,
        "confirmation_instructions": "WITHOUT",
    }


def _assert_scalar(value: Any, field_name: str, *, stage: str) -> None:
    """Fail if a field that should be a scalar is a dict (shape leak)."""
    assert not isinstance(value, dict), (
        f"{stage}: field {field_name!r} leaked as a dict: {value!r} — "
        f"this is the {{value, confidence}} wrapper bug (see commit 8cc27c7a). "
        f"Downstream rendering will show this as a jsonish Python repr string."
    )


# ---------------------------------------------------------------------------
# Stage 1: wrap → build field_details → unwrap
# ---------------------------------------------------------------------------


def test_stage_1_wrap_build_sidecar_unwrap_round_trip() -> None:
    """After the sidecar is built and the payload is unwrapped, scalar fields
    must be scalars again."""
    parsed = _realistic_vision_llm_output()

    wrapped = _wrap_ai_result_with_default_confidence(parsed, default_confidence=0.82)
    field_details = _build_default_field_details_from_wrapped_result(
        wrapped, source="test", raw_text=""
    )
    _unwrap_confidence_scalars_in_place(wrapped)

    # Main payload: every scalar field must be a scalar again
    for field in _TOP_LEVEL_SCALAR_FIELDS:
        if field in wrapped:
            _assert_scalar(wrapped[field], field, stage="after unwrap")

    # Lists stay lists, not dicts
    assert isinstance(wrapped["documents_required"], list)
    assert isinstance(wrapped["additional_conditions"], list)

    # Sidecar still carries confidence for every field (wrap contract preserved)
    for field in _TOP_LEVEL_SCALAR_FIELDS:
        if field in wrapped and field in field_details:
            assert field_details[field].get("confidence") == 0.82, (
                f"field_details sidecar lost confidence for {field!r}"
            )


# ---------------------------------------------------------------------------
# Stage 2: _shape_lc_financial_payload flattening
# ---------------------------------------------------------------------------


def test_stage_2_shape_lc_financial_payload_keeps_scalars_scalar() -> None:
    """The shaping function should produce scalar strings / numbers / lists
    for every MT700 skeleton field."""
    parsed = _realistic_vision_llm_output()
    wrapped = _wrap_ai_result_with_default_confidence(parsed, default_confidence=0.82)
    _build_default_field_details_from_wrapped_result(wrapped, source="test", raw_text="")
    _unwrap_confidence_scalars_in_place(wrapped)

    shaped = _shape_lc_financial_payload(
        wrapped,
        lc_subtype="sight_irrevocable_export",
        raw_text="",
        source_type="letter_of_credit",
        lc_format="mt700",
        allow_text_backfill=False,
    )

    # 9 skeleton fields — none should be a dict
    skeleton = [
        "lc_number",
        "amount",
        "currency",
        "applicant",
        "beneficiary",
        "goods_description",
        "documents_required",
        "expiry_date",
        "latest_shipment_date",
    ]
    for field in skeleton:
        assert field in shaped, f"skeleton field {field!r} missing from shaped payload"
        _assert_scalar(shaped[field], field, stage="after _shape_lc_financial_payload")

    # Specific type assertions
    assert isinstance(shaped["lc_number"], str)
    assert shaped["lc_number"] == "EXP2026BD001"
    assert isinstance(shaped["applicant"], str)
    assert "GLOBAL IMPORTERS" in shaped["applicant"]
    assert isinstance(shaped["beneficiary"], str)
    assert "DHAKA KNITWEAR" in shaped["beneficiary"]
    # amount may be int or float depending on normalization
    assert isinstance(shaped["amount"], (int, float))
    assert shaped["amount"] == 250000
    assert shaped["currency"] == "USD"
    assert isinstance(shaped["documents_required"], list)
    assert all(isinstance(d, str) for d in shaped["documents_required"])


# ---------------------------------------------------------------------------
# Stage 3: LCDocument round trip
# ---------------------------------------------------------------------------


def test_stage_3_lc_document_round_trip_preserves_scalars() -> None:
    """LCDocument.from_legacy_dict → to_lc_context must produce scalar values."""
    parsed = _realistic_vision_llm_output()
    wrapped = _wrap_ai_result_with_default_confidence(parsed, default_confidence=0.82)
    _build_default_field_details_from_wrapped_result(wrapped, source="test", raw_text="")
    _unwrap_confidence_scalars_in_place(wrapped)

    shaped = _shape_lc_financial_payload(
        wrapped,
        lc_subtype="sight_irrevocable_export",
        raw_text="",
        source_type="letter_of_credit",
        lc_format="mt700",
        allow_text_backfill=False,
    )

    lc_doc = LCDocument.from_legacy_dict(shaped)
    ctx = lc_doc.to_lc_context()

    # Scalar keys on the re-emitted legacy context
    for field in ("lc_number", "applicant", "beneficiary", "goods_description"):
        if field in ctx:
            _assert_scalar(ctx[field], field, stage="after to_lc_context")
            assert isinstance(ctx[field], str), (
                f"{field!r} should be str in lc_context, got {type(ctx[field]).__name__}"
            )

    assert ctx.get("lc_number") == "EXP2026BD001"
    assert "GLOBAL IMPORTERS" in ctx.get("applicant", "")
    assert "DHAKA KNITWEAR" in ctx.get("beneficiary", "")


# ---------------------------------------------------------------------------
# Stage 4: build_lc_intake_summary (what the intake card actually renders)
# ---------------------------------------------------------------------------


def test_stage_4_intake_summary_is_scalar_only() -> None:
    """The intake card reads from build_lc_intake_summary — EVERY value in
    the returned summary must be a scalar, not a dict, not a wrapper, not a
    JSON-repr string like \"{'value': 'X', 'confidence': 0.82}\".
    """
    parsed = _realistic_vision_llm_output()
    wrapped = _wrap_ai_result_with_default_confidence(parsed, default_confidence=0.82)
    _build_default_field_details_from_wrapped_result(wrapped, source="test", raw_text="")
    _unwrap_confidence_scalars_in_place(wrapped)

    shaped = _shape_lc_financial_payload(
        wrapped,
        lc_subtype="sight_irrevocable_export",
        raw_text="",
        source_type="letter_of_credit",
        lc_format="mt700",
        allow_text_backfill=False,
    )

    summary = build_lc_intake_summary(shaped)

    for key, value in summary.items():
        _assert_scalar(value, key, stage="intake_summary")
        # Also guard against the specific symptom of the fixed bug:
        if isinstance(value, str):
            assert not value.startswith("{'value':"), (
                f"{key!r} rendered as Python dict repr string: {value!r} — "
                f"the unwrap is missing somewhere upstream"
            )
            assert not value.startswith('{"value":'), (
                f"{key!r} rendered as JSON wrapper string: {value!r} — "
                f"the unwrap is missing somewhere upstream"
            )

    # Positive assertions on expected values
    assert summary.get("lc_number") == "EXP2026BD001"
    assert summary.get("currency") == "USD"


# ---------------------------------------------------------------------------
# Stage 5: regression guard — simulate a hostile wrapper leak
# ---------------------------------------------------------------------------


def test_regression_hostile_wrapper_leak_is_caught_by_shape_stage() -> None:
    """If someone forgets to call _unwrap_confidence_scalars_in_place and
    the wrapped dict reaches _shape_lc_financial_payload, the shape function
    should still produce scalar values for applicant / beneficiary / amount
    via its explicit dict-unwrap branches. lc_number and other fields will
    NOT be unwrapped by the shape function — this test documents the current
    behavior as a backstop so anyone who re-introduces the leak sees the
    failure loudly.
    """
    parsed = _realistic_vision_llm_output()
    wrapped = _wrap_ai_result_with_default_confidence(parsed, default_confidence=0.82)
    # Deliberately SKIP _unwrap_confidence_scalars_in_place to simulate the
    # bug state.
    shaped = _shape_lc_financial_payload(
        wrapped,
        lc_subtype="sight_irrevocable_export",
        raw_text="",
        source_type="letter_of_credit",
        lc_format="mt700",
        allow_text_backfill=False,
    )

    # _shape_lc_financial_payload DOES unwrap applicant / beneficiary / amount
    # via isinstance(dict) branches — so those come out clean even without
    # the helper.
    assert isinstance(shaped.get("applicant"), str), (
        "regression: _shape_lc_financial_payload lost its applicant unwrap branch"
    )
    assert isinstance(shaped.get("beneficiary"), str), (
        "regression: _shape_lc_financial_payload lost its beneficiary unwrap branch"
    )
    assert isinstance(shaped.get("amount"), (int, float)), (
        "regression: _shape_lc_financial_payload lost its amount unwrap branch"
    )

    # But lc_number and form_of_documentary_credit DO leak as dicts when the
    # unwrap is skipped — this is expected today and is what the
    # _unwrap_confidence_scalars_in_place helper fixes.  If someone adds a
    # safety-net unwrap in _shape_lc_financial_payload in the future, this
    # expectation should be flipped to "is str".
    assert isinstance(shaped.get("lc_number"), dict), (
        "If this assertion flips to ‘scalar’, either someone added a safety "
        "net unwrap in _shape_lc_financial_payload (great! flip the assertion) "
        "or the wrap helper has changed behavior (investigate)."
    )
