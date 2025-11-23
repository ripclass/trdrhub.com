"""
Unit tests for LC extractor with MT700 full parser and goods 46A parser.

Tests Option E components:
- MT700 full parser integration
- Goods 46A parser integration
- LC type classification
"""

import pytest
from app.services.extraction.lc_extractor import extract_lc_structured

SAMPLE_MT700 = """
:20:REF12345
:27:1/1
:40A:IRREVOCABLE TRANSFERABLE
:40E:UCP LATEST VERSION
:31C:250101
:31D:DHKA 250331
:50:/123456
APPLICANT NAME LINE 1
APPLICANT ADDRESS LINE 2
:59:/987654
BENEFICIARY NAME LINE 1
BENEFICIARY ADDRESS LINE 2
:32B:USD123456.78
:41A:ABCDUS33
:44A:DHAKA
:44E:CHITTAGONG PORT
:44F:LOS ANGELES PORT
:44C:250228
:45A:100% Cotton T-Shirts
:46A:SIGNED COMMERCIAL INVOICE
:47A:UCP 600 LATEST
:71B:ALL BANK CHARGES AS PER LC
:48:21 DAYS AFTER SHIPMENT
:72:/ACC/Handle carefully
"""

SAMPLE_46A_GOODS = """
:46A:
1) 10000 pcs Cotton T-shirts, white + black mixed (HS 610910)
2) 5000 pcs Men's Denim Jeans (HS:620342)
3) 2500 pcs Ladies Tops, assorted colors HS Code 610690
:47A:
"""


def test_mt700_full_parses_reference():
    """Test MT700 full parser extracts reference number."""
    out = extract_lc_structured(SAMPLE_MT700)
    assert "mt700" in out
    assert out["mt700"]["reference"] == "REF12345"


def test_mt700_parses_amount():
    """Test MT700 full parser extracts currency and amount."""
    out = extract_lc_structured(SAMPLE_MT700)
    assert "mt700" in out
    amt = out["mt700"]["credit_amount"]
    assert amt["currency"] == "USD"
    assert amt["amount"] == 123456.78


def test_mt700_lc_type_classification():
    """Test LC type classification detects Transferable/Sight."""
    out = extract_lc_structured(SAMPLE_MT700)
    assert "lc_type" in out
    lc_type = out["lc_type"]["types"]
    assert "Transferable" in lc_type or "Sight" in lc_type


def test_goods_46a_parsing():
    """Test goods 46A parser extracts structured items with quantities and HS codes."""
    out = extract_lc_structured(SAMPLE_46A_GOODS)
    assert "goods" in out
    goods = out["goods"]
    assert len(goods) == 3
    
    # First item should have quantity and HS code
    assert goods[0]["quantity"]["unit"] == "PCS"
    assert goods[0]["quantity"]["value"] == 10000.0
    assert goods[0]["hs_code"] == "610910"
    
    # Second item
    assert goods[1]["quantity"]["value"] == 5000.0
    assert goods[1]["hs_code"] == "620342"
    
    # Third item
    assert goods[2]["quantity"]["value"] == 2500.0
    assert goods[2]["hs_code"] == "610690"


def test_goods_summary_generated():
    """Test goods_summary is generated with totals."""
    out = extract_lc_structured(SAMPLE_46A_GOODS)
    assert "goods_summary" in out
    summary = out["goods_summary"]
    assert summary["items"] == 3
    assert summary["total_quantity"] == 17500.0  # 10000 + 5000 + 2500
    assert "PCS" in summary["units"]


def test_mt700_dates_parsed():
    """Test MT700 parser extracts and normalizes dates."""
    out = extract_lc_structured(SAMPLE_MT700)
    assert "mt700" in out
    fields = out["mt700"]
    assert fields["date_of_issue"] == "2025-01-01"
    assert fields["expiry_details"]["expiry_date_iso"] == "2025-03-31"


def test_mt700_shipment_details():
    """Test MT700 parser extracts shipment ports and dates."""
    out = extract_lc_structured(SAMPLE_MT700)
    assert "mt700" in out
    shipment = out["mt700"]["shipment_details"]
    pol = shipment["port_of_loading_airport_of_departure"]
    pod = shipment["port_of_discharge_airport_of_destination"]
    # Handle both string and list values (repeatable tags)
    if isinstance(pol, list):
        assert pol[0] == "CHITTAGONG PORT"
    else:
        assert pol == "CHITTAGONG PORT"
    if isinstance(pod, list):
        assert pod[0] == "LOS ANGELES PORT"
    else:
        assert pod == "LOS ANGELES PORT"
    latest_shipment = shipment["latest_date_of_shipment"]
    if isinstance(latest_shipment, list):
        assert latest_shipment[0] == "250228"
    else:
        assert latest_shipment == "250228"


def test_full_integration_sample():
    """Test full integration with realistic LC bundle."""
    full_lc = """
:20:LC2025XYZ01
:27:1/1
:40A:IRREVOCABLE
:40E:UCP600 LATEST
:31C:250101
:31D:DHAKA 250401
:50:/998877
ABC BUYER CORPORATION
123 TRADE STREET
SHANGHAI, CHINA
:59:/445566
XYZ GARMENTS LTD
135/2 MIRPUR
DHAKA, BANGLADESH
:32B:USD256000.00
:41A:ABCDBDDH
:44A:CHITTAGONG, BANGLADESH
:44E:SHANGHAI PORT
:44F:LOS ANGELES PORT
:44C:250315
:45A:
1) 10000 pcs Cotton T-shirts, mixed colors (HS 610910)
2) 5000 pcs Men's Denim Jeans (HS:620342)
3) 2500 pcs Ladies Tops HS Code 610690
:46A:
SIGNED COMMERCIAL INVOICE IN 1 ORIGINAL + 3 COPIES
PACKING LIST
CERTIFICATE OF ORIGIN ISSUED BY CHAMBER OF COMMERCE
:47A:
UCP 600 APPLICABLE.
PARTIAL SHIPMENTS ALLOWED.
:71B:ALL BANKING CHARGES OUTSIDE APPLICANT'S COUNTRY ARE FOR BENEFICIARY'S ACCOUNT
:48:21 DAYS AFTER SHIPMENT
:72:/ACC/Ensure inspection certificate attached
"""
    out = extract_lc_structured(full_lc)
    
    # MT700 fields
    assert out["mt700"]["reference"] == "LC2025XYZ01"
    assert out["mt700"]["credit_amount"]["currency"] == "USD"
    assert out["mt700"]["credit_amount"]["amount"] == 256000.00
    
    # Goods parsing
    assert len(out["goods"]) >= 3
    assert out["goods_summary"]["items"] >= 3
    
    # LC type
    assert "lc_type" in out
    assert isinstance(out["lc_type"]["types"], list)

