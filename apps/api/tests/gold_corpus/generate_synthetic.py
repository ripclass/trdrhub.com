#!/usr/bin/env python3
"""
Generate synthetic test documents for gold corpus.

Creates PDF documents with controlled content for testing extraction and validation.
Each document set is designed to test specific scenarios.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

# Use reportlab if available, otherwise create placeholder files
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("Warning: reportlab not installed. Install with: pip install reportlab")

CORPUS_DIR = Path(__file__).parent
DOCUMENTS_DIR = CORPUS_DIR / "documents"
EXPECTED_DIR = CORPUS_DIR / "expected"


@dataclass
class LCData:
    """Data for a Letter of Credit."""
    lc_number: str
    lc_type: str = "irrevocable"
    payment_type: str = "sight"
    amount: float = 125000.00
    currency: str = "USD"
    applicant_name: str = "Global Trade Corp"
    applicant_address: str = "123 Commerce Street, New York, NY 10001, USA"
    beneficiary_name: str = "Bangladesh Export Ltd"
    beneficiary_address: str = "45 Export Zone, Chittagong, Bangladesh"
    issuing_bank: str = "Standard Chartered Bank"
    issuing_bank_swift: str = "SCBLBDDX"
    advising_bank: str = "HSBC Bangladesh"
    advising_bank_swift: str = "HSBCBDDH"
    port_of_loading: str = "Chittagong, Bangladesh"
    port_of_discharge: str = "New York, USA"
    goods_description: str = "100% Cotton T-Shirts, HS Code 6109.10"
    quantity: str = "10,000 pieces"
    unit_price: float = 12.50
    incoterms: str = "FOB Chittagong"
    latest_shipment_date: str = "2026-03-15"
    expiry_date: str = "2026-03-31"
    presentation_period: int = 21
    partial_shipments: str = "Allowed"
    transhipment: str = "Allowed"
    documents_required: List[str] = field(default_factory=lambda: [
        "Commercial Invoice in triplicate",
        "Full set of clean on board Bills of Lading",
        "Packing List",
        "Certificate of Origin",
        "Insurance Certificate for 110% of invoice value"
    ])


@dataclass 
class InvoiceData:
    """Data for Commercial Invoice."""
    invoice_number: str
    invoice_date: str
    lc_reference: str
    seller_name: str
    seller_address: str
    buyer_name: str
    buyer_address: str
    amount: float
    currency: str
    goods_description: str
    quantity: str
    unit_price: float
    incoterms: str


@dataclass
class BLData:
    """Data for Bill of Lading."""
    bl_number: str
    shipper: str
    consignee: str
    notify_party: str
    vessel_name: str
    voyage_number: str
    port_of_loading: str
    port_of_discharge: str
    goods_description: str
    gross_weight: str
    container_number: str
    seal_number: str
    shipped_on_board_date: str
    freight_terms: str = "Freight Prepaid"


def create_lc_pdf(data: LCData, output_path: Path):
    """Create a Letter of Credit PDF."""
    if not HAS_REPORTLAB:
        # Create a text placeholder
        content = f"""
IRREVOCABLE DOCUMENTARY CREDIT
MT700 FORMAT

Field 27: Sequence of Total: 1/1
Field 40A: Form of Documentary Credit: {data.lc_type.upper()}
Field 20: Documentary Credit Number: {data.lc_number}
Field 31C: Date of Issue: {datetime.now().strftime('%Y-%m-%d')}
Field 40E: Applicable Rules: UCP LATEST VERSION
Field 31D: Date and Place of Expiry: {data.expiry_date} {data.port_of_discharge}
Field 50: Applicant: {data.applicant_name}
         {data.applicant_address}
Field 59: Beneficiary: {data.beneficiary_name}
          {data.beneficiary_address}
Field 32B: Currency Code, Amount: {data.currency} {data.amount:,.2f}
Field 41D: Available With/By: {data.advising_bank} BY NEGOTIATION
Field 42C: Drafts at: {data.payment_type.upper()}
Field 43P: Partial Shipments: {data.partial_shipments.upper()}
Field 43T: Transhipment: {data.transhipment.upper()}
Field 44E: Port of Loading: {data.port_of_loading}
Field 44F: Port of Discharge: {data.port_of_discharge}
Field 44C: Latest Date of Shipment: {data.latest_shipment_date}
Field 45A: Description of Goods:
    {data.goods_description}
    Quantity: {data.quantity}
    Unit Price: {data.currency} {data.unit_price:.2f}
    Total: {data.currency} {data.amount:,.2f}
    Terms: {data.incoterms}
Field 46A: Documents Required:
{''.join(f"    - {doc}" + chr(10) for doc in data.documents_required)}
Field 47A: Additional Conditions:
    - Documents must be presented within {data.presentation_period} days after shipment
    - All documents must show LC number {data.lc_number}
Field 71B: Charges: All banking charges outside issuing bank are for beneficiary
Field 48: Period for Presentation: {data.presentation_period} days
Field 49: Confirmation Instructions: WITHOUT
Field 52A: Issuing Bank: {data.issuing_bank}
          SWIFT: {data.issuing_bank_swift}
"""
        output_path.write_text(content)
        return
    
    # Create PDF with reportlab
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=14, alignment=1)
    story.append(Paragraph("IRREVOCABLE DOCUMENTARY CREDIT", title_style))
    story.append(Paragraph(f"LC Number: {data.lc_number}", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    # Add LC details as table
    lc_data = [
        ["Form of Credit:", f"{data.lc_type.upper()} {data.payment_type.upper()}"],
        ["Date of Issue:", datetime.now().strftime('%Y-%m-%d')],
        ["Date of Expiry:", data.expiry_date],
        ["Applicant:", f"{data.applicant_name}\n{data.applicant_address}"],
        ["Beneficiary:", f"{data.beneficiary_name}\n{data.beneficiary_address}"],
        ["Amount:", f"{data.currency} {data.amount:,.2f}"],
        ["Issuing Bank:", f"{data.issuing_bank}\n{data.issuing_bank_swift}"],
        ["Port of Loading:", data.port_of_loading],
        ["Port of Discharge:", data.port_of_discharge],
        ["Latest Shipment:", data.latest_shipment_date],
        ["Goods:", f"{data.goods_description}\n{data.quantity} @ {data.currency} {data.unit_price:.2f}"],
        ["Terms:", data.incoterms],
    ]
    
    table = Table(lc_data, colWidths=[150, 350])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(table)
    
    doc.build(story)


def create_invoice_pdf(data: InvoiceData, output_path: Path):
    """Create a Commercial Invoice PDF."""
    content = f"""
COMMERCIAL INVOICE

Invoice Number: {data.invoice_number}
Invoice Date: {data.invoice_date}
L/C Reference: {data.lc_reference}

SELLER:
{data.seller_name}
{data.seller_address}

BUYER:
{data.buyer_name}
{data.buyer_address}

DESCRIPTION OF GOODS:
{data.goods_description}

Quantity: {data.quantity}
Unit Price: {data.currency} {data.unit_price:.2f}

TOTAL AMOUNT: {data.currency} {data.amount:,.2f}

Terms: {data.incoterms}

We certify that the goods are of {data.seller_name.split()[0]} origin.

Authorized Signature: ____________________
Date: {data.invoice_date}
"""
    output_path.write_text(content)


def create_bl_pdf(data: BLData, output_path: Path):
    """Create a Bill of Lading PDF."""
    content = f"""
BILL OF LADING
(Original)

B/L Number: {data.bl_number}

Shipper:
{data.shipper}

Consignee:
{data.consignee}

Notify Party:
{data.notify_party}

Vessel: {data.vessel_name}
Voyage: {data.voyage_number}

Port of Loading: {data.port_of_loading}
Port of Discharge: {data.port_of_discharge}

PARTICULARS FURNISHED BY SHIPPER:
Description of Goods: {data.goods_description}
Gross Weight: {data.gross_weight}
Container No: {data.container_number}
Seal No: {data.seal_number}

Freight: {data.freight_terms}

SHIPPED ON BOARD
Date: {data.shipped_on_board_date}

"CLEAN ON BOARD"

For the Master,
As Agent for the Carrier

____________________
Authorized Signature
"""
    output_path.write_text(content)


def create_packing_list(lc: LCData, invoice: InvoiceData, output_path: Path):
    """Create a Packing List."""
    content = f"""
PACKING LIST

Reference: {invoice.invoice_number}
L/C Number: {lc.lc_number}
Date: {invoice.invoice_date}

Shipper:
{lc.beneficiary_name}
{lc.beneficiary_address}

Consignee:
{lc.applicant_name}
{lc.applicant_address}

PACKING DETAILS:

Description: {lc.goods_description}
Total Quantity: {lc.quantity}

Package Details:
- Cartons: 500
- Pieces per Carton: 20
- Total Pieces: 10,000

Gross Weight: 2,500 KG
Net Weight: 2,200 KG
Total Volume: 15 CBM

Marks and Numbers:
{lc.lc_number}
MADE IN BANGLADESH
C/NO 1-500

We certify this packing list is true and correct.

Authorized Signature: ____________________
"""
    output_path.write_text(content)


def create_certificate_of_origin(lc: LCData, output_path: Path):
    """Create a Certificate of Origin."""
    content = f"""
CERTIFICATE OF ORIGIN

Certificate No: COO-{lc.lc_number}

The undersigned hereby certifies that the goods described below originate from:

BANGLADESH

Exporter:
{lc.beneficiary_name}
{lc.beneficiary_address}

Consignee:
{lc.applicant_name}
{lc.applicant_address}

Description of Goods:
{lc.goods_description}

Quantity: {lc.quantity}
HS Code: 6109.10

Country of Origin: BANGLADESH

This is to certify that the above goods are the product of Bangladesh.

Issued by: Bangladesh Export Promotion Bureau
Date: {datetime.now().strftime('%Y-%m-%d')}

Chamber Stamp: [STAMP]

____________________
Authorized Signature
"""
    output_path.write_text(content)


def create_insurance_certificate(lc: LCData, output_path: Path):
    """Create an Insurance Certificate."""
    insured_amount = lc.amount * 1.1  # 110% coverage
    content = f"""
INSURANCE CERTIFICATE

Certificate No: INS-{lc.lc_number}
Policy No: MCP-2026-001234

This is to certify that the following goods are insured under the above policy:

Insured:
{lc.beneficiary_name}

Goods:
{lc.goods_description}
Quantity: {lc.quantity}

Vessel: [To be declared]
From: {lc.port_of_loading}
To: {lc.port_of_discharge}

Sum Insured: {lc.currency} {insured_amount:,.2f}
(Being 110% of invoice value)

Coverage: Institute Cargo Clauses (A)
         Institute War Clauses (Cargo)
         Institute Strikes Clauses (Cargo)

Claims Payable in: {lc.port_of_discharge}

This certificate is subject to the terms and conditions of the policy.

Issued by: Bangladesh Insurance Corp.
Date: {datetime.now().strftime('%Y-%m-%d')}

____________________
Authorized Signature
"""
    output_path.write_text(content)


def generate_set_001_synthetic_bd():
    """Generate Set 001: Standard Bangladesh Export LC (clean, should pass)."""
    set_id = "set_001_synthetic_bd"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)
    
    # LC data
    lc = LCData(
        lc_number="EXP2026BD001",
        amount=125000.00,
        currency="USD",
        port_of_loading="Chittagong, Bangladesh",  # Will test alias matching
        port_of_discharge="New York, USA",
    )
    
    # Create documents
    create_lc_pdf(lc, set_dir / "LC.pdf")
    
    invoice = InvoiceData(
        invoice_number="INV-2026-001",
        invoice_date="2026-02-15",
        lc_reference=lc.lc_number,
        seller_name=lc.beneficiary_name,
        seller_address=lc.beneficiary_address,
        buyer_name=lc.applicant_name,
        buyer_address=lc.applicant_address,
        amount=lc.amount,  # Exact match
        currency=lc.currency,
        goods_description=lc.goods_description,
        quantity=lc.quantity,
        unit_price=lc.unit_price,
        incoterms=lc.incoterms,
    )
    create_invoice_pdf(invoice, set_dir / "Invoice.pdf")
    
    bl = BLData(
        bl_number="MSKU2026001234",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="MAERSK SINGAPORE",
        voyage_number="V.2026E",
        port_of_loading="Chattogram",  # Alias of Chittagong - tests port matching
        port_of_discharge="New York",
        goods_description=lc.goods_description,
        gross_weight="2,500 KG",
        container_number="MSKU1234567",
        seal_number="SL123456",
        shipped_on_board_date="2026-03-01",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")
    
    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf")
    
    print(f"[OK] Generated {set_id}: 6 documents")
    return set_id


def generate_set_002_amount_mismatch():
    """Generate Set 002: Invoice amount exceeds LC (should fail)."""
    set_id = "set_002_amount_mismatch"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)
    
    lc = LCData(
        lc_number="EXP2026BD002",
        amount=100000.00,
        currency="USD",
    )
    create_lc_pdf(lc, set_dir / "LC.pdf")
    
    # Invoice exceeds LC amount (UCP600 violation)
    invoice = InvoiceData(
        invoice_number="INV-2026-002",
        invoice_date="2026-02-15",
        lc_reference=lc.lc_number,
        seller_name=lc.beneficiary_name,
        seller_address=lc.beneficiary_address,
        buyer_name=lc.applicant_name,
        buyer_address=lc.applicant_address,
        amount=105000.00,  # Exceeds LC by 5%
        currency=lc.currency,
        goods_description=lc.goods_description,
        quantity=lc.quantity,
        unit_price=lc.unit_price,
        incoterms=lc.incoterms,
    )
    create_invoice_pdf(invoice, set_dir / "Invoice.pdf")
    
    bl = BLData(
        bl_number="MSKU2026002345",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="MAERSK SINGAPORE",
        voyage_number="V.2026E",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,000 KG",
        container_number="MSKU2345678",
        seal_number="SL234567",
        shipped_on_board_date="2026-03-01",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")
    
    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf")
    
    # Create expected results
    expected = {
        "set_id": set_id,
        "description": "Invoice amount exceeds LC - UCP600 Article 18(b) violation",
        "version": "1.0",
        "expected_compliance_rate": 70.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_fields": [
            {"document_type": "lc", "field_name": "lc_number", "expected_value": "EXP2026BD002", "match_type": "exact", "criticality": "critical"},
            {"document_type": "lc", "field_name": "lc_amount", "expected_value": "100000.00", "match_type": "numeric_tolerance", "tolerance": 0.001, "criticality": "critical"},
            {"document_type": "invoice", "field_name": "invoice_amount", "expected_value": "105000.00", "match_type": "numeric_tolerance", "tolerance": 0.001, "criticality": "critical"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-AMOUNT-1", "severity": "critical", "document_type": "invoice", "title_contains": "amount", "description": "Invoice exceeds LC amount"}
        ],
        "false_positive_checks": []
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2))
    
    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_003_port_mismatch():
    """Generate Set 003: B/L port doesn't match LC (should fail)."""
    set_id = "set_003_port_mismatch"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)
    
    lc = LCData(
        lc_number="EXP2026BD003",
        amount=80000.00,
        port_of_loading="Chittagong, Bangladesh",
        port_of_discharge="Los Angeles, USA",
    )
    create_lc_pdf(lc, set_dir / "LC.pdf")
    
    invoice = InvoiceData(
        invoice_number="INV-2026-003",
        invoice_date="2026-02-15",
        lc_reference=lc.lc_number,
        seller_name=lc.beneficiary_name,
        seller_address=lc.beneficiary_address,
        buyer_name=lc.applicant_name,
        buyer_address=lc.applicant_address,
        amount=lc.amount,
        currency=lc.currency,
        goods_description=lc.goods_description,
        quantity=lc.quantity,
        unit_price=lc.unit_price,
        incoterms=lc.incoterms,
    )
    create_invoice_pdf(invoice, set_dir / "Invoice.pdf")
    
    # B/L has WRONG port of discharge
    bl = BLData(
        bl_number="MSKU2026003456",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="MAERSK PACIFIC",
        voyage_number="V.2026W",
        port_of_loading=lc.port_of_loading,
        port_of_discharge="Long Beach, USA",  # Wrong! LC says Los Angeles
        goods_description=lc.goods_description,
        gross_weight="1,600 KG",
        container_number="MSKU3456789",
        seal_number="SL345678",
        shipped_on_board_date="2026-03-01",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")
    
    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf")
    
    expected = {
        "set_id": set_id,
        "description": "B/L port of discharge doesn't match LC",
        "version": "1.0",
        "expected_compliance_rate": 75.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_fields": [
            {"document_type": "lc", "field_name": "port_of_discharge", "expected_value": "Los Angeles", "match_type": "contains", "criticality": "important"},
            {"document_type": "bl", "field_name": "port_of_discharge", "expected_value": "Long Beach", "match_type": "contains", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-PORT-1", "severity": "major", "document_type": "bl", "title_contains": "port", "description": "Port mismatch"}
        ],
        "false_positive_checks": []
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2))
    
    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_004_late_shipment():
    """Generate Set 004: B/L date after LC latest shipment date (should fail)."""
    set_id = "set_004_late_shipment"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)
    
    lc = LCData(
        lc_number="EXP2026BD004",
        amount=95000.00,
        latest_shipment_date="2026-02-28",
        expiry_date="2026-03-15",
    )
    create_lc_pdf(lc, set_dir / "LC.pdf")
    
    invoice = InvoiceData(
        invoice_number="INV-2026-004",
        invoice_date="2026-02-25",
        lc_reference=lc.lc_number,
        seller_name=lc.beneficiary_name,
        seller_address=lc.beneficiary_address,
        buyer_name=lc.applicant_name,
        buyer_address=lc.applicant_address,
        amount=lc.amount,
        currency=lc.currency,
        goods_description=lc.goods_description,
        quantity=lc.quantity,
        unit_price=lc.unit_price,
        incoterms=lc.incoterms,
    )
    create_invoice_pdf(invoice, set_dir / "Invoice.pdf")
    
    # B/L shipped AFTER latest shipment date
    bl = BLData(
        bl_number="MSKU2026004567",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="EVERGREEN ASIA",
        voyage_number="V.2026N",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="1,900 KG",
        container_number="EGHU4567890",
        seal_number="SL456789",
        shipped_on_board_date="2026-03-05",  # LATE! After Feb 28
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")
    
    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf")
    
    expected = {
        "set_id": set_id,
        "description": "Late shipment - B/L date after LC latest shipment date",
        "version": "1.0",
        "expected_compliance_rate": 70.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_fields": [
            {"document_type": "lc", "field_name": "latest_shipment_date", "expected_value": "2026-02-28", "match_type": "contains", "criticality": "important"},
            {"document_type": "bl", "field_name": "shipped_on_board_date", "expected_value": "2026-03-05", "match_type": "contains", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-DATE-1", "severity": "critical", "document_type": "bl", "title_contains": "shipment", "description": "Late shipment"}
        ],
        "false_positive_checks": []
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2))
    
    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_005_insurance_undervalue():
    """Generate Set 005: Insurance less than 110% (should fail)."""
    set_id = "set_005_insurance_undervalue"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)
    
    lc = LCData(
        lc_number="EXP2026BD005",
        amount=150000.00,
    )
    create_lc_pdf(lc, set_dir / "LC.pdf")
    
    invoice = InvoiceData(
        invoice_number="INV-2026-005",
        invoice_date="2026-02-15",
        lc_reference=lc.lc_number,
        seller_name=lc.beneficiary_name,
        seller_address=lc.beneficiary_address,
        buyer_name=lc.applicant_name,
        buyer_address=lc.applicant_address,
        amount=lc.amount,
        currency=lc.currency,
        goods_description=lc.goods_description,
        quantity=lc.quantity,
        unit_price=lc.unit_price,
        incoterms=lc.incoterms,
    )
    create_invoice_pdf(invoice, set_dir / "Invoice.pdf")
    
    bl = BLData(
        bl_number="MSKU2026005678",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="CMA CGM MARCO POLO",
        voyage_number="V.2026S",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="3,000 KG",
        container_number="CMAU5678901",
        seal_number="SL567890",
        shipped_on_board_date="2026-03-01",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")
    
    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    
    # Insurance at only 100% instead of 110%
    insurance_content = f"""
INSURANCE CERTIFICATE

Certificate No: INS-{lc.lc_number}
Policy No: MCP-2026-005678

Sum Insured: {lc.currency} {lc.amount:,.2f}
(Being 100% of invoice value - INSUFFICIENT)

This is less than the required 110% coverage per UCP600.
"""
    (set_dir / "Insurance_Certificate.pdf").write_text(insurance_content)
    
    expected = {
        "set_id": set_id,
        "description": "Insurance undervalue - less than 110% required by UCP600",
        "version": "1.0",
        "expected_compliance_rate": 80.0,
        "compliance_tolerance": 10.0,
        "expected_status": "warning",
        "expected_fields": [
            {"document_type": "lc", "field_name": "lc_amount", "expected_value": "150000.00", "match_type": "numeric_tolerance", "tolerance": 0.001, "criticality": "critical"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-INSURANCE-1", "severity": "major", "document_type": "insurance", "title_contains": "coverage", "description": "Insurance coverage insufficient"}
        ],
        "false_positive_checks": []
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2))
    
    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_006_goods_mismatch():
    """Generate Set 006: Goods description mismatch between docs (should fail)."""
    set_id = "set_006_goods_mismatch"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)
    
    lc = LCData(
        lc_number="EXP2026BD006",
        amount=88000.00,
        goods_description="100% Cotton T-Shirts, HS Code 6109.10",
    )
    create_lc_pdf(lc, set_dir / "LC.pdf")
    
    # Invoice has DIFFERENT goods
    invoice = InvoiceData(
        invoice_number="INV-2026-006",
        invoice_date="2026-02-15",
        lc_reference=lc.lc_number,
        seller_name=lc.beneficiary_name,
        seller_address=lc.beneficiary_address,
        buyer_name=lc.applicant_name,
        buyer_address=lc.applicant_address,
        amount=lc.amount,
        currency=lc.currency,
        goods_description="Polyester Blend T-Shirts, HS Code 6109.90",  # WRONG!
        quantity=lc.quantity,
        unit_price=lc.unit_price,
        incoterms=lc.incoterms,
    )
    create_invoice_pdf(invoice, set_dir / "Invoice.pdf")
    
    bl = BLData(
        bl_number="MSKU2026006789",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="HAPAG LLOYD EXPRESS",
        voyage_number="V.2026E",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,  # B/L matches LC
        gross_weight="1,760 KG",
        container_number="HLCU6789012",
        seal_number="SL678901",
        shipped_on_board_date="2026-03-01",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")
    
    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf")
    
    expected = {
        "set_id": set_id,
        "description": "Goods description mismatch - Invoice shows different product",
        "version": "1.0",
        "expected_compliance_rate": 75.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_fields": [
            {"document_type": "lc", "field_name": "goods_description", "expected_value": "Cotton", "match_type": "contains", "criticality": "important"},
            {"document_type": "invoice", "field_name": "goods_description", "expected_value": "Polyester", "match_type": "contains", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-GOODS-1", "severity": "critical", "document_type": "invoice", "title_contains": "goods", "description": "Goods description mismatch"}
        ],
        "false_positive_checks": []
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2))
    
    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def main():
    """Generate all synthetic test sets."""
    print("=" * 60)
    print("GENERATING SYNTHETIC TEST SETS")
    print("=" * 60)
    
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    
    sets = [
        generate_set_001_synthetic_bd(),
        generate_set_002_amount_mismatch(),
        generate_set_003_port_mismatch(),
        generate_set_004_late_shipment(),
        generate_set_005_insurance_undervalue(),
        generate_set_006_goods_mismatch(),
    ]
    
    print("\n" + "=" * 60)
    print(f"Generated {len(sets)} test sets:")
    for s in sets:
        print(f"  - {s}")
    print("=" * 60)
    
    return sets


if __name__ == "__main__":
    main()

