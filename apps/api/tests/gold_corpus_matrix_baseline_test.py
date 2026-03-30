from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXPECTED_DIR = ROOT / "gold_corpus" / "expected"


def _load_expected(name: str) -> dict:
    return json.loads((EXPECTED_DIR / name).read_text(encoding="utf-8"))


def _rule_ids(payload: dict) -> list[str]:
    return [str(item.get("rule_id") or "").strip() for item in payload.get("expected_issues", [])]


def _false_positive_rule_ids(payload: dict) -> set[str]:
    return {
        str(item.get("rule_id") or "").strip()
        for item in payload.get("false_positive_checks", [])
        if str(item.get("rule_id") or "").strip()
    }


def test_gold_corpus_expected_matrix_matches_live_locked_baseline() -> None:
    expected_rule_matrix = {
        "set_001_synthetic_bd.json": [],
        "set_002_amount_mismatch.json": ["CROSSDOC-AMOUNT-1"],
        "set_003_port_mismatch.json": ["CROSSDOC-BL-002"],
        "set_004_late_shipment.json": ["CROSSDOC-BL-003"],
        "set_005_insurance_undervalue.json": ["CROSSDOC-INSURANCE-1"],
        "set_006_goods_mismatch.json": ["CROSSDOC-INV-003"],
        "set_007_missing_insurance_document.json": ["CROSSDOC-DOC-1"],
        "set_008_invoice_after_expiry.json": ["CROSSDOC-INV-004"],
        "set_009_invoice_lc_reference_mismatch.json": ["CROSSDOC-INV-005"],
        "set_010_invoice_missing_lc_reference.json": ["CROSSDOC-INV-005"],
    }

    for filename, expected_rules in expected_rule_matrix.items():
        payload = _load_expected(filename)
        assert _rule_ids(payload) == expected_rules


def test_gold_corpus_false_positive_guards_cover_retired_noise() -> None:
    clean_set = _load_expected("set_001_synthetic_bd.json")
    clean_false_positives = _false_positive_rule_ids(clean_set)
    assert {
        "PRICE-VERIFY-1",
        "SANCTIONS-PARTY-1",
        "CROSSDOC-LC-002",
        "CROSSDOC-TIMING-001",
    }.issubset(clean_false_positives)

    goods_set = _load_expected("set_006_goods_mismatch.json")
    goods_false_positives = _false_positive_rule_ids(goods_set)
    assert "PRICE-VERIFY-2" in goods_false_positives

    missing_insurance_set = _load_expected("set_007_missing_insurance_document.json")
    missing_insurance_false_positives = _false_positive_rule_ids(missing_insurance_set)
    assert "CROSSDOC-INSURANCE-1" in missing_insurance_false_positives
