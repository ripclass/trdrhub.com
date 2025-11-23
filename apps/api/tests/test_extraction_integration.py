"""
Integration tests for LC extraction pipeline (Options B + C + D).

Tests:
- processing_summary.documents_found
- goods_46a_parser
- swift_mt700_full parser
"""

import pytest
from app.services.extraction.lc_extractor import extract_lc_structured
from app.services.extraction.goods_46a_parser import parse_goods_46a
from app.services.extraction.swift_mt700_full import parse_mt700_full


# Sample MT700 message
SAMPLE_MT700 = """
:20:REF12345
:27:1/1
:40A:IRREVOCABLE TRANSFERABLE
:40E:UCP LATEST VERSION
:31C:250101
:31D:DHKA 250331
:50:/123456
APPLICANT NAME LTD
123 Main Street
Dhaka, Bangladesh
:59:/987654
BENEFICIARY COMPANY INC
456 Trade Avenue
Los Angeles, USA
:32B:USD123456.78
:41A:ABCDUS33
:44A:DHAKA
:44E:CHITTAGONG PORT
:44F:LOS ANGELES PORT
:44C:250228
:45A:
1) 10,000 PCS 100% Cotton T-Shirts, Size M-XL, White/Black mixed (HS CODE 61091000)
2) 5,000 CTNS Packing materials
:46A:1) SIGNED COMMERCIAL INVOICE
2) PACKING LIST
3) BILL OF LADING
:47A:1) DOCUMENTS MUST NOT BE DATED EARLIER THAN LC ISSUE DATE.
2) ALL BANKING CHARGES OUTSIDE APPLICANT'S COUNTRY ARE FOR BENEFICIARY'S ACCOUNT.
:71B:ALL BANKING CHARGES OUTSIDE APPLICANT'S COUNTRY ARE FOR BENEFICIARY'S ACCOUNT
:48:21 DAYS AFTER SHIPMENT
:72:/ACC/Handle carefully
"""

# Sample 46A goods description
SAMPLE_46A_GOODS = """
1) 10,000 PCS 100% Cotton T-Shirts, Size M-XL, White/Black mixed (HS CODE 61091000)
2) 5,000 CTNS Packing materials
3) 500 KG Cotton fabric samples
"""


def test_mt700_full_parser():
    """Test full MT700 parser extracts all fields correctly."""
    result = parse_mt700_full(SAMPLE_MT700)
    
    assert result["message_type"] == "MT700"
    assert "fields" in result
    assert "raw" in result
    
    fields = result["fields"]
    
    # Core fields
    assert fields["reference"] == "REF12345"
    assert fields["form_of_doc_credit"] == "IRREVOCABLE TRANSFERABLE"
    assert fields["applicable_rules"] == "UCP LATEST VERSION"
    
    # Dates
    assert fields["date_of_issue"] == "2025-01-01"
    assert fields["expiry_details"]["expiry_date_iso"] == "2025-03-31"
    
    # Amount
    assert fields["credit_amount"]["currency"] == "USD"
    assert fields["credit_amount"]["amount"] == 123456.78
    
    # Parties
    assert "APPLICANT NAME" in fields["applicant"]
    assert "BENEFICIARY COMPANY" in fields["beneficiary"]
    
    # Shipment details (handle list values for repeatable tags)
    pol = fields["shipment_details"]["port_of_loading_airport_of_departure"]
    pod = fields["shipment_details"]["port_of_discharge_airport_of_destination"]
    latest = fields["shipment_details"]["latest_date_of_shipment"]
    
    if isinstance(pol, list):
        assert pol[0] == "CHITTAGONG PORT"
    else:
        assert pol == "CHITTAGONG PORT"
    
    if isinstance(pod, list):
        assert pod[0] == "LOS ANGELES PORT"
    else:
        assert pod == "LOS ANGELES PORT"
    
    if isinstance(latest, list):
        assert latest[0] == "250228"
    else:
        assert latest == "250228"
    
    # LC Classification
    assert "lc_classification" in fields
    types = fields["lc_classification"]["types"]
    assert "Transferable" in types
    # Note: Sight/Usance classification depends on payment terms (42C/42P/42M)
    # This sample doesn't have explicit payment terms, so we just verify classification exists
    assert isinstance(types, list)
    assert len(types) > 0


def test_goods_46a_parser():
    """Test goods parser extracts structured items."""
    items = parse_goods_46a(SAMPLE_46A_GOODS)
    
    assert len(items) >= 3
    
    # First item should have quantity and HS code
    item1 = items[0]
    assert item1["line_no"] == 1
    assert item1["quantity"]["value"] == 10000.0
    assert item1["quantity"]["unit"] == "PCS"
    assert item1["hs_code"] == "61091000"
    assert "Cotton T-Shirts" in item1["description"]
    
    # Second item
    item2 = items[1]
    assert item2["quantity"]["value"] == 5000.0
    assert item2["quantity"]["unit"] == "CTNS"
    
    # Third item
    item3 = items[2]
    assert item3["quantity"]["value"] == 500.0
    assert item3["quantity"]["unit"] == "KG"


def test_lc_extractor_integration():
    """Test full LC extraction pipeline."""
    result = extract_lc_structured(SAMPLE_MT700)
    
    # MT700 fields should be present
    assert "mt700" in result
    assert result["mt700"]["reference"] == "REF12345"
    
    # Goods should be parsed
    assert "goods" in result
    assert len(result["goods"]) > 0
    
    # Goods summary
    assert "goods_summary" in result
    summary = result["goods_summary"]
    assert summary["items"] > 0
    assert summary["total_quantity"] > 0
    
    # LC type classification
    assert "lc_type" in result
    assert "types" in result["lc_type"]


def test_processing_summary_documents_found():
    """Test that processing_summary includes documents_found field."""
    # This would be tested in validate.py integration
    # For now, just verify the field exists in the return structure
    from app.routers.validate import _build_processing_summary
    
    summaries = [
        {"name": "Doc1", "status": "success"},
        {"name": "Doc2", "status": "warning"},
    ]
    
    result = _build_processing_summary(summaries, 1.5, 0)
    
    assert "documents" in result
    assert "documents_found" in result
    assert result["documents"] == result["documents_found"]
    assert result["documents_found"] == 2


if __name__ == "__main__":
    # Quick smoke test
    print("Testing MT700 parser...")
    test_mt700_full_parser()
    print("✓ MT700 parser OK")
    
    print("\nTesting goods parser...")
    test_goods_46a_parser()
    print("✓ Goods parser OK")
    
    print("\nTesting LC extractor integration...")
    test_lc_extractor_integration()
    print("✓ LC extractor integration OK")
    
    print("\nTesting processing_summary...")
    test_processing_summary_documents_found()
    print("✓ Processing summary OK")
    
    print("\n✅ All tests passed!")

