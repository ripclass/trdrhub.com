from app.services.validation.day1_retrieval_guard import (
    evaluate_anchor_evidence,
    apply_anchor_evidence_floor,
)


def test_anchor_evidence_detects_hits():
    text = "TIN: 1234567890\nVoyage No: 118E\nGross Weight: 10 KG\nIssued by: ACME"
    checks = evaluate_anchor_evidence(text)
    assert checks["tin"].has_evidence is True
    assert checks["voyage"].has_evidence is True
    assert checks["gross_weight"].has_evidence is True
    assert checks["issuer"].has_evidence is True


def test_apply_anchor_floor_abstains_without_anchor():
    text = "Random text without field anchors"
    raw = {
        "tin": "1234567890",
        "voyage": "118E",
        "gross_weight": "10 KG",
        "issuer": "ACME LTD",
    }
    filtered, errors, scores = apply_anchor_evidence_floor(raw, text)
    assert filtered["tin"] is None
    assert filtered["voyage"] is None
    assert filtered["gross_weight"] is None
    assert filtered["issuer"] is None
    assert "RET_NO_HIT" in errors
    assert "tin" in scores


def test_apply_anchor_floor_keeps_when_evidence_present():
    text = "TIN: 1234567890\nGross Weight: 10 KG"
    raw = {"tin": "1234567890", "gross_weight": "10 KG"}
    filtered, errors, _ = apply_anchor_evidence_floor(raw, text)
    assert filtered["tin"] == "1234567890"
    assert filtered["gross_weight"] == "10 KG"
    assert errors == []
