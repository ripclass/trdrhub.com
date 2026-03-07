from app.services.validation.day1_normalizers import (
    normalize_bin,
    normalize_tin,
    normalize_voyage,
    normalize_weight,
    validate_gross_net_pair,
    normalize_date,
    normalize_issuer,
)


def test_bin_normalize_with_ocr_confusion():
    out = normalize_bin("BIN: 00O1234567890")
    assert out.valid is True
    assert out.normalized == "0001234567890"


def test_bin_invalid_length():
    out = normalize_bin("123456789012")
    assert out.valid is False
    assert out.error_code == "BIN_LENGTH_INVALID"


def test_tin_ocr_chars():
    out = normalize_tin("TIN: 12S45O7891")
    assert out.valid is True
    assert out.normalized == "1254507891"


def test_voyage_canonicalization():
    out = normalize_voyage("Voy No: vyg / ab  123-e")
    assert out.valid is True
    assert out.normalized == "AB-123-E"


def test_weight_mt_to_kg():
    out = normalize_weight("1.25 MT")
    assert out.valid is True
    assert out.unit == "MT"
    assert out.normalized_kg == 1250.0


def test_weight_lb_to_kg_round_3():
    out = normalize_weight("2204.62 lb")
    assert out.valid is True
    assert out.unit == "LB"
    assert out.normalized_kg == 999.999


def test_net_gt_gross_rule():
    gross = normalize_weight("1000 KG")
    net = normalize_weight("1100 KG")
    assert validate_gross_net_pair(gross, net) == "NET_GT_GROSS"


def test_date_slash_to_iso():
    out = normalize_date("07/03/2026")
    assert out.valid is True
    assert out.normalized == "2026-03-07"


def test_date_textual_month_to_iso():
    out = normalize_date("7 Mar 2026")
    assert out.valid is True
    assert out.normalized == "2026-03-07"


def test_invalid_date_rejected():
    out = normalize_date("31/02/2026")
    assert out.valid is False
    assert out.error_code == "DATE_PARSE_INVALID"


def test_issuer_normalization():
    out = normalize_issuer("  Acme Trading   Limited. ")
    assert out.valid is True
    assert out.normalized == "ACME TRADING LTD"
