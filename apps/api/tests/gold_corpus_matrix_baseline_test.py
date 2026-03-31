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
        "set_007_missing_insurance_document.json": ["DOCSET-MISSING-INSURANCE-CERTIFICATE"],
        "set_008_invoice_after_expiry.json": ["CROSSDOC-INV-004"],
        "set_009_invoice_lc_reference_mismatch.json": ["CROSSDOC-INV-005"],
        "set_010_invoice_missing_lc_reference.json": ["CROSSDOC-INV-005"],
        "set_011_invoice_issuer_mismatch.json": ["CROSSDOC-INV-002"],
        "set_012_bl_shipper_mismatch.json": ["CROSSDOC-BL-004"],
        "set_013_bl_consignee_mismatch.json": ["CROSSDOC-BL-005"],
        "set_014_insurance_currency_mismatch.json": ["CROSSDOC-INS-003"],
        "set_015_po_number_missing.json": ["CROSSDOC-PO-NUMBER"],
        "set_016_exporter_bin_missing.json": ["CROSSDOC-BIN"],
        "set_017_exporter_tin_missing.json": ["CROSSDOC-TIN"],
    }

    for filename, expected_rules in expected_rule_matrix.items():
        payload = _load_expected(filename)
        assert _rule_ids(payload) == expected_rules


def test_gold_corpus_expected_contract_outcomes_match_live_locked_baseline() -> None:
    expected_contract_matrix = {
        "set_001_synthetic_bd.json": {"final_verdict": "pass", "workflow_stage": "validation_results"},
        "set_002_amount_mismatch.json": {"final_verdict": "reject", "workflow_stage": "validation_results"},
        "set_003_port_mismatch.json": {"final_verdict": "reject", "workflow_stage": "validation_results"},
        "set_004_late_shipment.json": {"final_verdict": "reject", "workflow_stage": "validation_results"},
        "set_005_insurance_undervalue.json": {"final_verdict": "review", "workflow_stage": "validation_results"},
        "set_006_goods_mismatch.json": {"final_verdict": "review", "workflow_stage": "validation_results"},
        "set_007_missing_insurance_document.json": {"final_verdict": "review", "workflow_stage": "validation_results"},
        "set_008_invoice_after_expiry.json": {"final_verdict": "reject", "workflow_stage": "validation_results"},
        "set_009_invoice_lc_reference_mismatch.json": {"final_verdict": "review", "workflow_stage": "validation_results"},
        "set_010_invoice_missing_lc_reference.json": {"final_verdict": "pass", "workflow_stage": "validation_results"},
        "set_011_invoice_issuer_mismatch.json": {"final_verdict": "reject", "workflow_stage": "validation_results"},
        "set_012_bl_shipper_mismatch.json": {"final_verdict": "review", "workflow_stage": "validation_results"},
        "set_013_bl_consignee_mismatch.json": {"final_verdict": "pass", "workflow_stage": "validation_results"},
        "set_014_insurance_currency_mismatch.json": {"final_verdict": "review", "workflow_stage": "validation_results"},
        "set_015_po_number_missing.json": {"final_verdict": "review", "workflow_stage": "validation_results"},
        "set_016_exporter_bin_missing.json": {"final_verdict": "review", "workflow_stage": "validation_results"},
        "set_017_exporter_tin_missing.json": {"final_verdict": "review", "workflow_stage": "validation_results"},
    }

    for filename, expected in expected_contract_matrix.items():
        payload = _load_expected(filename)
        assert payload.get("expected_final_verdict") == expected["final_verdict"]
        assert payload.get("expected_workflow_stage") == expected["workflow_stage"]


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

    invoice_after_expiry_set = _load_expected("set_008_invoice_after_expiry.json")
    invoice_after_expiry_false_positives = _false_positive_rule_ids(invoice_after_expiry_set)
    assert "CROSSDOC-INS-002" in invoice_after_expiry_false_positives

    shipper_mismatch_set = _load_expected("set_012_bl_shipper_mismatch.json")
    shipper_mismatch_false_positives = _false_positive_rule_ids(shipper_mismatch_set)
    assert "CROSSDOC-BL-005" in shipper_mismatch_false_positives

    insurance_currency_set = _load_expected("set_014_insurance_currency_mismatch.json")
    insurance_currency_false_positives = _false_positive_rule_ids(insurance_currency_set)
    assert {"CROSSDOC-INS-002", "CROSSDOC-INSURANCE-1"}.issubset(insurance_currency_false_positives)

    po_set = _load_expected("set_015_po_number_missing.json")
    po_false_positives = _false_positive_rule_ids(po_set)
    assert {"CROSSDOC-BIN", "CROSSDOC-TIN"}.issubset(po_false_positives)

    bin_set = _load_expected("set_016_exporter_bin_missing.json")
    bin_false_positives = _false_positive_rule_ids(bin_set)
    assert {"CROSSDOC-PO-NUMBER", "CROSSDOC-TIN"}.issubset(bin_false_positives)

    tin_set = _load_expected("set_017_exporter_tin_missing.json")
    tin_false_positives = _false_positive_rule_ids(tin_set)
    assert {"CROSSDOC-PO-NUMBER", "CROSSDOC-BIN"}.issubset(tin_false_positives)
