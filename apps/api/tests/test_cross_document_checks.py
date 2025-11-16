import sys
from types import ModuleType, SimpleNamespace

import pytest

# The validate router pulls in report generation dependencies (e.g., weasyprint)
# that aren't installed in the lightweight CI/test environment. Provide a cheap stub
# so importing the router for unit tests doesn't fail.
if "weasyprint" not in sys.modules:
    class _WeasyStub:  # pragma: no cover - only used as import shim
        def __init__(self, *args, **kwargs):
            pass

        def write_pdf(self, *args, **kwargs):
            return b""

    weasy_module = ModuleType("weasyprint")
    weasy_module.HTML = _WeasyStub
    weasy_module.CSS = _WeasyStub
    sys.modules["weasyprint"] = weasy_module

    text_module = ModuleType("weasyprint.text")
    fonts_module = ModuleType("weasyprint.text.fonts")
    fonts_module.FontConfiguration = _WeasyStub
    sys.modules["weasyprint.text.fonts"] = fonts_module
    text_module.fonts = fonts_module
    sys.modules["weasyprint.text"] = text_module

from app.services.crossdoc import run_cross_document_checks, build_issue_cards


@pytest.fixture
def sample_crossdoc_payload():
    return {
        "lc": {
            "goods_description": "Refined white sugar, 1000 MT",
            "amount": {"value": "100000"},
            "applicant": "Imran Imports Ltd.",
            "beneficiary": "Global Sugar Traders",
        },
        "invoice": {
            "product_description": "Brown cane sugar, 1200 MT",
            "invoice_amount": "125000",
        },
        "bill_of_lading": {
            "shipper": "Southeast Logistics",
            "consignee": "Oceanic Commodities",
        },
        "documents_presence": {
            "insurance_certificate": {"present": False, "count": 0},
            "packing_list": {"present": True, "count": 1},
        },
        "documents": [
            {"id": "lc-doc", "filename": "LCSET01_01_LC.pdf", "document_type": "letter_of_credit"},
            {"id": "invoice-doc", "filename": "LCSET01_02_Commercial_Invoice.pdf", "document_type": "commercial_invoice"},
            {"id": "bl-doc", "filename": "LCSET01_03_Bill_of_Lading.pdf", "document_type": "bill_of_lading"},
        ],
        "lc_text": (
            "Credit requires full set of insurance policies and mentions insurance coverage twice."
        ),
        "invoice_amount_limit": "110000",
        "invoice_amount_tolerance_value": "10000",
        "invoice_amount_tolerance_percent": 10,
    }


def test_cross_document_checks_emits_all_expected_issues(sample_crossdoc_payload):
    """Smoke test that deterministic cross-doc checks fire when structured data exists."""
    issues = run_cross_document_checks(sample_crossdoc_payload)
    rules = {issue["rule"] for issue in issues}

    expected_rules = {
        "CROSSDOC-GOODS-1",
        "CROSSDOC-AMOUNT-1",
        "CROSSDOC-DOC-1",
        "CROSSDOC-BL-1",
        "CROSSDOC-BL-2",
    }

    for rule in expected_rules:
        assert rule in rules, f"Expected rule {rule} to be emitted. Got {rules}"

    goods_issue = next(issue for issue in issues if issue["rule"] == "CROSSDOC-GOODS-1")
    assert goods_issue["display_card"] is True
    assert goods_issue["expected"].startswith("Refined white sugar")
    assert goods_issue["actual"].startswith("Brown cane sugar")
    assert goods_issue["document_ids"] == ["lc-doc", "invoice-doc"]
    assert goods_issue["documents"][0] == "LCSET01_01_LC.pdf"


def test_issue_cards_render_cross_doc_rules(sample_crossdoc_payload):
    """Ensure cross-doc discrepancies become user-facing issue cards."""
    issues = run_cross_document_checks(sample_crossdoc_payload)
    issue_cards, references = build_issue_cards(issues)

    assert issue_cards, "Cross-doc issues should render as issue cards"
    assert not references, "Cross-doc issues should not fall back to reference bucket"

    ids = {card["id"] for card in issue_cards}
    assert "CROSSDOC-GOODS-1" in ids
    assert "CROSSDOC-AMOUNT-1" in ids

    goods_card = next(card for card in issue_cards if card["id"] == "CROSSDOC-GOODS-1")
    assert goods_card["documentName"] == "LCSET01_01_LC.pdf"

