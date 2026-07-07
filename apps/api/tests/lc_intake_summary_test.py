"""Regression tests for build_lc_intake_summary payload-shape tolerance.

The LC intake card reads whatever shape the winning extractor emitted:
- ISO 20022 structured path: amount = {"value": float, "currency": str}
- Legacy/AI paths: amount = {"amount": ..., "currency": ...} or flat scalars

Found live 2026-07-06 (Turkey tsmt.001): the ISO dict's "value" key was not
read, so the intake card showed a currency with no amount.
"""

from app.routers.validation.lc_intake import build_lc_intake_summary


def test_iso20022_amount_value_key_survives():
    summary = build_lc_intake_summary(
        {
            "number": "ISO-TUR-2026-039",
            "amount": {"value": 132750.0, "currency": "USD"},
        }
    )
    assert summary["amount"] == 132750.0
    assert summary["currency"] == "USD"
    assert summary["lc_number"] == "ISO-TUR-2026-039"


def test_legacy_amount_dict_shape_still_works():
    summary = build_lc_intake_summary(
        {
            "number": "IBBLBDCN2026041",
            "amount": {"amount": 184250.0, "currency": "USD"},
        }
    )
    assert summary["amount"] == 184250.0
    assert summary["currency"] == "USD"


def test_flat_scalar_amount_still_works():
    summary = build_lc_intake_summary(
        {
            "number": "LC-FLAT-1",
            "amount": 99000.5,
            "currency": "EUR",
        }
    )
    assert summary["amount"] == 99000.5
    assert summary["currency"] == "EUR"
