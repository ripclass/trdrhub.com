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
    additional_conditions: List[str] = field(default_factory=list)
    documents_required: List[str] = field(default_factory=lambda: [
        "Commercial Invoice in triplicate",
        "Full set of clean on board Bills of Lading",
        "Packing List",
        "Certificate of Origin",
        "Insurance Certificate for 110% of invoice value"
    ])


def _default_lc_additional_conditions(data: LCData) -> List[str]:
    return [
        f"Documents must be presented within {data.presentation_period} days after shipment",
        f"All documents must show LC number {data.lc_number}",
    ]


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


def create_lc_pdf(data: LCData, output_path: Path, *, force_text: bool = False):
    """Create a Letter of Credit PDF."""
    additional_conditions = _default_lc_additional_conditions(data)
    if data.additional_conditions:
        additional_conditions.extend(data.additional_conditions)

    if force_text or not HAS_REPORTLAB:
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
{''.join(f"    - {line}" + chr(10) for line in additional_conditions)}
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
    lc_reference_line = (
        f"L/C Reference: {data.lc_reference}\n" if str(data.lc_reference or "").strip() else ""
    )
    content = f"""
COMMERCIAL INVOICE

Invoice Number: {data.invoice_number}
Invoice Date: {data.invoice_date}
{lc_reference_line}

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


def create_insurance_certificate(
    lc: LCData,
    output_path: Path,
    *,
    issue_date: Optional[str] = None,
    currency_override: Optional[str] = None,
    originals_presented: Optional[int] = None,
):
    """Create an Insurance Certificate."""
    insured_amount = lc.amount * 1.1  # 110% coverage
    certificate_date = issue_date or datetime.now().strftime('%Y-%m-%d')
    insurance_currency = currency_override or lc.currency
    originals_lines = ""
    if originals_presented is not None:
        originals_lines = (
            f"\nNumber of Originals: {originals_presented}\n"
            f"Presented Originals: {originals_presented}\n"
        )
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

Sum Insured: {insurance_currency} {insured_amount:,.2f}
(Being 110% of invoice value)

Coverage Type: ICC-A
Coverage: Institute Cargo Clauses (A)
         Institute War Clauses (Cargo)
         Institute Strikes Clauses (Cargo)

Claims Payable in: {lc.port_of_discharge}

This certificate is subject to the terms and conditions of the policy.

Issued by: Bangladesh Insurance Corp.
Date: {certificate_date}

____________________
Authorized Signature
{originals_lines}
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
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)
    
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
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")
    
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
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)
    
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
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")
    
    # Create expected results
    expected = {
        "set_id": set_id,
        "description": "Invoice amount exceeds LC - UCP600 Article 18(b) violation",
        "version": "1.0",
        "expected_compliance_rate": 70.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_final_verdict": "reject",
        "expected_workflow_stage": "validation_results",
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
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")
    
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
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)
    
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
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")
    
    expected = {
        "set_id": set_id,
        "description": "B/L port of discharge doesn't match LC",
        "version": "1.0",
        "expected_compliance_rate": 75.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_final_verdict": "reject",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "port_of_discharge", "expected_value": "Los Angeles", "match_type": "contains", "criticality": "important"},
            {"document_type": "bl", "field_name": "port_of_discharge", "expected_value": "Long Beach", "match_type": "contains", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-BL-002", "severity": "critical", "document_type": "bill", "title_contains": "discharge", "description": "Port of discharge mismatch"}
        ],
        "false_positive_checks": []
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")
    
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
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)
    
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
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")
    
    expected = {
        "set_id": set_id,
        "description": "Late shipment - B/L date after LC latest shipment date",
        "version": "1.0",
        "expected_compliance_rate": 70.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_final_verdict": "reject",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "latest_shipment_date", "expected_value": "2026-02-28", "match_type": "contains", "criticality": "important"},
            {"document_type": "bl", "field_name": "shipped_on_board_date", "expected_value": "2026-03-05", "match_type": "contains", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-BL-003", "severity": "critical", "document_type": "bill", "title_contains": "shipment", "description": "Late shipment"}
        ],
        "false_positive_checks": []
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")
    
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
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)
    
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
        "expected_final_verdict": "reject",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "lc_amount", "expected_value": "150000.00", "match_type": "numeric_tolerance", "tolerance": 0.001, "criticality": "critical"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-INSURANCE-1", "severity": "major", "document_type": "insurance", "title_contains": "coverage", "description": "Insurance coverage insufficient"}
        ],
        "false_positive_checks": []
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")
    
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
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)
    
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
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")
    
    expected = {
        "set_id": set_id,
        "description": "Goods description mismatch - Invoice shows different product",
        "version": "1.0",
        "expected_compliance_rate": 75.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_final_verdict": "reject",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "goods_description", "expected_value": "Cotton", "match_type": "contains", "criticality": "important"},
            {"document_type": "invoice", "field_name": "goods_description", "expected_value": "Polyester", "match_type": "contains", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-INV-003", "severity": "major", "document_type": "invoice", "title_contains": "goods", "description": "Goods description mismatch"}
        ],
        "false_positive_checks": [
            {
                "rule_id": "PRICE-VERIFY-2",
                "description": "Goods mismatch should stay primary without layering a separate price anomaly finding into the documentary lane"
            }
        ]
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")
    
    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_007_missing_insurance_document():
    """Generate Set 007: Insurance required by LC but not uploaded (should fail missing-doc check)."""
    set_id = "set_007_missing_insurance_document"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BD007",
        amount=112500.00,
        currency="USD",
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-007",
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
        bl_number="MSKU2026007890",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="OOCL DHAKA",
        voyage_number="V.2026Q",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,250 KG",
        container_number="OOLU7890123",
        seal_number="SL789012",
        shipped_on_board_date="2026-03-01",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")

    expected = {
        "set_id": set_id,
        "description": "Insurance certificate missing even though the LC requires insurance coverage",
        "version": "1.0",
        "expected_compliance_rate": 80.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_final_verdict": "reject",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "lc_number", "expected_value": "EXP2026BD007", "match_type": "exact", "criticality": "critical"},
            {"document_type": "invoice", "field_name": "invoice_amount", "expected_value": "112500.00", "match_type": "numeric_tolerance", "tolerance": 0.001, "criticality": "critical"},
        ],
        "expected_issues": [
            {"rule_id": "DOCSET-MISSING-INSURANCE-CERTIFICATE", "severity": "major", "document_type": "insurance", "title_contains": "insurance", "description": "Insurance certificate missing"}
        ],
        "false_positive_checks": [
            {
                "rule_id": "CROSSDOC-INSURANCE-1",
                "description": "A missing insurance document should stay a missing-document finding, not degrade into an undervalue finding."
            }
        ],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 5 documents + expected.json")
    return set_id


def generate_set_008_invoice_after_expiry():
    """Generate Set 008: Invoice dated after LC expiry (should fail)."""
    set_id = "set_008_invoice_after_expiry"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BD008",
        amount=91000.00,
        latest_shipment_date="2026-03-10",
        expiry_date="2026-03-20",
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-008",
        invoice_date="2026-03-25",
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
        bl_number="MSKU2026008901",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="ONE CHITTAGONG",
        voyage_number="V.2026R",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,050 KG",
        container_number="ONEU8901234",
        seal_number="SL890123",
        shipped_on_board_date="2026-03-05",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")

    expected = {
        "set_id": set_id,
        "description": "Invoice date falls after the LC expiry date",
        "version": "1.0",
        "expected_compliance_rate": 72.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_final_verdict": "reject",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "expiry_date", "expected_value": "2026-03-20", "match_type": "contains", "criticality": "critical"},
            {"document_type": "invoice", "field_name": "invoice_date", "expected_value": "2026-03-25", "match_type": "contains", "criticality": "critical"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-INV-004", "severity": "critical", "document_type": "invoice", "title_contains": "expiry", "description": "Invoice dated after LC expiry"}
        ],
        "false_positive_checks": [
            {
                "rule_id": "CROSSDOC-INS-002",
                "description": "Pinned insurance dates should keep this fixture focused on invoice-after-expiry only."
            }
        ],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_009_invoice_lc_reference_mismatch():
    """Generate Set 009: Invoice references the wrong LC number (should fail)."""
    set_id = "set_009_invoice_lc_reference_mismatch"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BD009",
        amount=99000.00,
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-009",
        invoice_date="2026-02-18",
        lc_reference="EXP2026BD999",
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
        bl_number="MSKU2026009012",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="COSCO DHAKA",
        voyage_number="V.2026T",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,180 KG",
        container_number="COSU9012345",
        seal_number="SL901234",
        shipped_on_board_date="2026-03-02",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date=invoice.invoice_date)

    expected = {
        "set_id": set_id,
        "description": "Invoice references a different LC number than the credit being used",
        "version": "1.0",
        "expected_compliance_rate": 78.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_final_verdict": "review",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "lc_number", "expected_value": "EXP2026BD009", "match_type": "exact", "criticality": "critical"},
            {"document_type": "invoice", "field_name": "lc_reference", "expected_value": "EXP2026BD999", "match_type": "exact", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-INV-005", "severity": "major", "document_type": "invoice", "title_contains": "reference", "description": "Invoice LC reference mismatch"}
        ],
        "false_positive_checks": [],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_010_invoice_missing_lc_reference():
    """Generate Set 010: Invoice omits LC reference entirely (should fail)."""
    set_id = "set_010_invoice_missing_lc_reference"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BD010",
        amount=87000.00,
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-010",
        invoice_date="2026-02-19",
        lc_reference="",
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
        bl_number="MSKU2026010123",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="WAN HAI EXPRESS",
        voyage_number="V.2026U",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="1,980 KG",
        container_number="WHLU0123456",
        seal_number="SL012345",
        shipped_on_board_date="2026-03-03",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date=invoice.invoice_date)

    expected = {
        "set_id": set_id,
        "description": "Invoice omits the LC reference entirely",
        "version": "1.0",
        "expected_compliance_rate": 82.0,
        "compliance_tolerance": 10.0,
        "expected_status": "warning",
        "expected_final_verdict": "pass",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "lc_number", "expected_value": "EXP2026BD010", "match_type": "exact", "criticality": "critical"},
            {"document_type": "invoice", "field_name": "invoice_number", "expected_value": "INV-2026-010", "match_type": "contains", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-INV-005", "severity": "minor", "document_type": "invoice", "title_contains": "reference", "description": "Invoice missing LC reference"}
        ],
        "false_positive_checks": [],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_011_invoice_issuer_mismatch():
    """Generate Set 011: Invoice issuer does not match LC beneficiary (should fail)."""
    set_id = "set_011_invoice_issuer_mismatch"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BD011",
        amount=118000.00,
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-011",
        invoice_date="2026-02-18",
        lc_reference=lc.lc_number,
        seller_name="Eastern Apparel Sourcing Ltd",
        seller_address="77 Industrial Avenue, Dhaka, Bangladesh",
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
        bl_number="MSKU2026011011",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="MSC DHAKA",
        voyage_number="V.2026V",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,210 KG",
        container_number="MSCU1101122",
        seal_number="SL110112",
        shipped_on_board_date="2026-03-01",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")

    expected = {
        "set_id": set_id,
        "description": "Invoice issuer differs from the beneficiary named in the LC",
        "version": "1.0",
        "expected_compliance_rate": 74.0,
        "compliance_tolerance": 10.0,
        "expected_status": "warning",
        "expected_final_verdict": "review",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "beneficiary", "expected_value": lc.beneficiary_name, "match_type": "contains", "criticality": "critical"},
            {"document_type": "invoice", "field_name": "seller_name", "expected_value": invoice.seller_name, "match_type": "contains", "criticality": "critical"},
        ],
        "expected_issues": [
            {
                "rule_id": "UCP600-18A",
                "severity": "minor",
                "document_type": "invoice",
                "title_contains": "beneficiary",
                "description": "Commercial invoice issuer must match the LC beneficiary",
            }
        ],
        "false_positive_checks": [
            {
                "rule_id": "CROSSDOC-INV-003",
                "description": "Pure issuer mismatch should not also turn into a goods mismatch."
            },
            {
                "rule_id": "CROSSDOC-INV-002",
                "description": "Specific UCP600-18A should suppress the legacy cross-document duplicate."
            },
            {
                "rule_id": "UCP600-18",
                "description": "Specific UCP600-18A should suppress the broad umbrella article."
            }
        ],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_012_bl_shipper_mismatch():
    """Generate Set 012: B/L shipper does not match LC beneficiary (should fail)."""
    set_id = "set_012_bl_shipper_mismatch"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BD012",
        amount=121500.00,
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-012",
        invoice_date="2026-02-20",
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
        bl_number="MSKU2026012012",
        shipper="Eastern Apparel Logistics Ltd",
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="EVER SUMMIT",
        voyage_number="V.2026W",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,260 KG",
        container_number="EGLV1201234",
        seal_number="SL120123",
        shipped_on_board_date="2026-03-02",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")

    expected = {
        "set_id": set_id,
        "description": "Bill of lading shipper differs from the LC beneficiary",
        "version": "1.0",
        "expected_compliance_rate": 78.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_final_verdict": "review",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "beneficiary", "expected_value": lc.beneficiary_name, "match_type": "contains", "criticality": "important"},
            {"document_type": "bill_of_lading", "field_name": "shipper", "expected_value": bl.shipper, "match_type": "contains", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-BL-004", "severity": "major", "document_type": "bill_of_lading", "title_contains": "shipper", "description": "B/L shipper mismatch"}
        ],
        "false_positive_checks": [
            {
                "rule_id": "CROSSDOC-BL-005",
                "description": "A shipper-only mismatch should not also trigger consignee mismatch."
            }
        ],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_013_bl_consignee_mismatch():
    """Generate Set 013: B/L consignee does not match LC applicant (should warn)."""
    set_id = "set_013_bl_consignee_mismatch"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BD013",
        amount=109500.00,
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-013",
        invoice_date="2026-02-22",
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
        bl_number="MSKU2026013013",
        shipper=lc.beneficiary_name,
        consignee="Atlantic Retail Distribution LLC",
        notify_party=lc.applicant_name,
        vessel_name="MAERSK DHAKA",
        voyage_number="V.2026X",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,140 KG",
        container_number="MSKU1301345",
        seal_number="SL130134",
        shipped_on_board_date="2026-03-03",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")

    expected = {
        "set_id": set_id,
        "description": "Bill of lading consignee differs from the applicant named in the LC",
        "version": "1.0",
        "expected_compliance_rate": 84.0,
        "compliance_tolerance": 10.0,
        "expected_status": "warning",
        "expected_final_verdict": "pass",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "applicant", "expected_value": lc.applicant_name, "match_type": "contains", "criticality": "important"},
            {"document_type": "bill_of_lading", "field_name": "consignee", "expected_value": bl.consignee, "match_type": "contains", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-BL-005", "severity": "minor", "document_type": "bill_of_lading", "title_contains": "consignee", "description": "B/L consignee mismatch"}
        ],
        "false_positive_checks": [],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_014_insurance_currency_mismatch():
    """Generate Set 014: Insurance currency does not match LC currency (should fail)."""
    set_id = "set_014_insurance_currency_mismatch"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BD014",
        amount=93000.00,
        currency="USD",
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-014",
        invoice_date="2026-02-24",
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
        bl_number="MSKU2026014014",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="HMM BANGLA",
        voyage_number="V.2026Y",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,090 KG",
        container_number="HMMU1401456",
        seal_number="SL140145",
        shipped_on_board_date="2026-03-02",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(
        lc,
        set_dir / "Insurance_Certificate.pdf",
        issue_date="2026-03-01",
        currency_override="EUR",
    )

    expected = {
        "set_id": set_id,
        "description": "Insurance certificate is issued in a different currency than the LC",
        "version": "1.0",
        "expected_compliance_rate": 79.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_final_verdict": "review",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "currency", "expected_value": "USD", "match_type": "exact", "criticality": "important"},
            {"document_type": "insurance", "field_name": "currency", "expected_value": "EUR", "match_type": "exact", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "UCP600-28D", "severity": "minor", "document_type": "insurance", "title_contains": "currency", "description": "Insurance document currency differs from the LC"}
        ],
        "false_positive_checks": [
            {
                "rule_id": "CROSSDOC-INS-002",
                "description": "Pinned insurance dates should keep this fixture focused on currency mismatch."
            },
            {
                "rule_id": "CROSSDOC-INSURANCE-1",
                "description": "Currency mismatch should not also degrade into insurance undervalue."
            },
            {
                "rule_id": "CROSSDOC-INS-003",
                "description": "Legacy crossdoc insurance currency mismatch should stay suppressed when UCP600-28D is the specific live finding."
            }
        ],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_015_po_number_missing():
    """Generate Set 015: LC requires PO number on all docs but uploaded docs omit it."""
    set_id = "set_015_po_number_missing"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BD015",
        amount=112500.00,
        additional_conditions=[
            "BUYER PURCHASE ORDER NO. GBE-44592 MUST APPEAR ON ALL DOCUMENTS",
        ],
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-015",
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

    bl = BLData(
        bl_number="MSKU2026015015",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="OOCL DHAKA",
        voyage_number="V.2026Z",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,180 KG",
        container_number="OOCL1501567",
        seal_number="SL150156",
        shipped_on_board_date="2026-03-02",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")

    expected = {
        "set_id": set_id,
        "description": "LC 47A requires buyer PO number on all documents, but the uploaded documents omit it",
        "version": "1.0",
        "expected_compliance_rate": 76.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_final_verdict": "review",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "lc_number", "expected_value": lc.lc_number, "match_type": "exact", "criticality": "critical"},
            {"document_type": "invoice", "field_name": "invoice_number", "expected_value": invoice.invoice_number, "match_type": "contains", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-PO-NUMBER", "severity": "critical", "document_type": "invoice", "title_contains": "purchase order", "description": "PO number missing from documents"}
        ],
        "false_positive_checks": [
            {
                "rule_id": "CROSSDOC-BIN",
                "description": "A PO requirement should not also trigger BIN handling."
            },
            {
                "rule_id": "CROSSDOC-TIN",
                "description": "A PO requirement should not also trigger TIN handling."
            }
        ],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_016_exporter_bin_missing():
    """Generate Set 016: LC requires exporter BIN on all docs but uploaded docs omit it."""
    set_id = "set_016_exporter_bin_missing"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BD016",
        amount=108400.00,
        additional_conditions=[
            "EXPORTER BIN: 000334455-0103 MUST APPEAR ON ALL DOCUMENTS",
        ],
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-016",
        invoice_date="2026-02-26",
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
        bl_number="MSKU2026016016",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="CMA CGM DHAKA",
        voyage_number="V.2026AA",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,040 KG",
        container_number="CMAU1601678",
        seal_number="SL160167",
        shipped_on_board_date="2026-03-02",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")

    expected = {
        "set_id": set_id,
        "description": "LC 47A requires exporter BIN on all documents, but the uploaded documents omit it",
        "version": "1.0",
        "expected_compliance_rate": 76.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_final_verdict": "review",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "lc_number", "expected_value": lc.lc_number, "match_type": "exact", "criticality": "critical"},
            {"document_type": "invoice", "field_name": "invoice_number", "expected_value": invoice.invoice_number, "match_type": "contains", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-BIN", "severity": "critical", "document_type": "invoice", "title_contains": "bin", "description": "Exporter BIN missing from documents"}
        ],
        "false_positive_checks": [
            {
                "rule_id": "CROSSDOC-PO-NUMBER",
                "description": "A BIN requirement should not also trigger PO-number handling."
            },
            {
                "rule_id": "CROSSDOC-TIN",
                "description": "A BIN requirement should not also trigger TIN handling."
            }
        ],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_017_exporter_tin_missing():
    """Generate Set 017: LC requires exporter TIN on all docs but uploaded docs omit it."""
    set_id = "set_017_exporter_tin_missing"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BD017",
        amount=116300.00,
        additional_conditions=[
            "EXPORTER TIN: 545342112233 MUST APPEAR ON ALL DOCUMENTS",
        ],
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-017",
        invoice_date="2026-02-27",
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
        bl_number="MSKU2026017017",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="WAN HAI DHAKA",
        voyage_number="V.2026AB",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,150 KG",
        container_number="WHLU1701789",
        seal_number="SL170178",
        shipped_on_board_date="2026-03-02",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")

    expected = {
        "set_id": set_id,
        "description": "LC 47A requires exporter TIN on all documents, but the uploaded documents omit it",
        "version": "1.0",
        "expected_compliance_rate": 76.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_final_verdict": "review",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "lc_number", "expected_value": lc.lc_number, "match_type": "exact", "criticality": "critical"},
            {"document_type": "invoice", "field_name": "invoice_number", "expected_value": invoice.invoice_number, "match_type": "contains", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-TIN", "severity": "critical", "document_type": "invoice", "title_contains": "tin", "description": "Exporter TIN missing from documents"}
        ],
        "false_positive_checks": [
            {
                "rule_id": "CROSSDOC-PO-NUMBER",
                "description": "A TIN requirement should not also trigger PO-number handling."
            },
            {
                "rule_id": "CROSSDOC-BIN",
                "description": "A TIN requirement should not also trigger BIN handling."
            }
        ],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_018_invoice_exact_wording_missing():
    """Generate Set 018: LC requires exact invoice wording that the invoice omits."""
    set_id = "set_018_invoice_exact_wording_missing"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    required_wording = "WE HEREBY CERTIFY GOODS ARE BRAND NEW"
    lc = LCData(
        lc_number="EXP2026BD018",
        amount=119800.00,
        documents_required=[
            f"Commercial Invoice stating exactly {required_wording}",
            "Full set of clean on board Bills of Lading",
            "Packing List",
            "Certificate of Origin",
            "Insurance Certificate for 110% of invoice value",
        ],
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-018",
        invoice_date="2026-02-28",
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
        bl_number="MSKU2026018018",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="COSCO BANGLA",
        voyage_number="V.2026AC",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,125 KG",
        container_number="COSU1801890",
        seal_number="SL180189",
        shipped_on_board_date="2026-03-02",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")

    expected = {
        "set_id": set_id,
        "description": "LC requires exact wording on the commercial invoice, but the invoice omits it",
        "version": "1.0",
        "expected_compliance_rate": 78.0,
        "compliance_tolerance": 10.0,
        "expected_status": "error",
        "expected_final_verdict": "reject",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "lc_number", "expected_value": lc.lc_number, "match_type": "exact", "criticality": "critical"},
            {"document_type": "invoice", "field_name": "invoice_number", "expected_value": invoice.invoice_number, "match_type": "contains", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "CROSSDOC-EXACT-WORDING", "severity": "critical", "document_type": "invoice", "title_contains": "wording", "description": "LC-required wording missing from invoice"}
        ],
        "false_positive_checks": [
            {
                "rule_id": "CROSSDOC-INV-003",
                "description": "A missing wording statement should not also turn into a goods mismatch."
            }
        ],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_019_insurance_originals_mismatch():
    """Generate Set 019: LC requires 2 insurance originals, but only 1 is presented."""
    set_id = "set_019_insurance_originals_mismatch"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BDQ28A",
        amount=101000.00,
        currency="USD",
        port_of_loading="Chittagong, Bangladesh",
        port_of_discharge="New York, USA",
        documents_required=[
            "Commercial Invoice in triplicate",
            "Full set of clean on board Bills of Lading",
            "Packing List",
            "Certificate of Origin",
            "Insurance Certificate in 2 originals",
        ],
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-Q28A",
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
        bl_number="MSKU2026Q28A",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="MAERSK SINGAPORE",
        voyage_number="V.2026E",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,500 KG",
        container_number="MSKU1234567",
        seal_number="SL123456",
        shipped_on_board_date="2026-03-01",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(
        lc,
        set_dir / "Insurance_Certificate.pdf",
        issue_date="2026-03-01",
        originals_presented=1,
    )

    expected = {
        "set_id": set_id,
        "description": "LC requires two insurance originals, but the presentation includes only one original",
        "version": "1.0",
        "expected_compliance_rate": 82.0,
        "compliance_tolerance": 10.0,
        "expected_status": "warning",
        "expected_final_verdict": "review",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {"document_type": "lc", "field_name": "lc_number", "expected_value": lc.lc_number, "match_type": "exact", "criticality": "critical"},
            {"document_type": "invoice", "field_name": "invoice_number", "expected_value": invoice.invoice_number, "match_type": "contains", "criticality": "important"},
        ],
        "expected_issues": [
            {"rule_id": "UCP600-28A", "severity": "minor", "title_contains": "originals", "description": "Insurance originals fewer than LC requirement"}
        ],
        "false_positive_checks": [
            {
                "rule_id": "UCP600-18",
                "description": "Invoice umbrella article should stay suppressed when the specific insurance originals rule is the only surfaced discrepancy."
            },
            {
                "rule_id": "UCP600-20",
                "description": "Transport umbrella article should not leak into the insurance originals-only case."
            },
            {
                "rule_id": "UCP600-28",
                "description": "Insurance umbrella article should stay suppressed when UCP600-28A is the actionable child rule."
            }
        ],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_020_bl_port_of_loading_mismatch():
    """Generate Set 020: B/L port of loading differs from the LC loading port."""
    set_id = "set_020_bl_port_of_loading_mismatch"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BDQ20D",
        amount=103400.00,
        currency="USD",
        port_of_loading="Chittagong, Bangladesh",
        port_of_discharge="New York, USA",
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-Q20D",
        invoice_date="2026-02-18",
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
        bl_number="MSKU2026Q20D",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="MSC DHAKA",
        voyage_number="V.2026F",
        port_of_loading="Mongla, Bangladesh",
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,640 KG",
        container_number="MSKU7654321",
        seal_number="SL765432",
        shipped_on_board_date="2026-03-01",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(
        lc,
        set_dir / "Insurance_Certificate.pdf",
        issue_date="2026-03-01",
    )

    expected = {
        "set_id": set_id,
        "description": "Bill of lading shows a different port of loading than the LC",
        "version": "1.0",
        "expected_compliance_rate": 82.0,
        "compliance_tolerance": 10.0,
        "expected_status": "warning",
        "expected_final_verdict": "review",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {
                "document_type": "lc",
                "field_name": "lc_number",
                "expected_value": lc.lc_number,
                "match_type": "exact",
                "criticality": "critical",
            },
            {
                "document_type": "bill_of_lading",
                "field_name": "bl_number",
                "expected_value": bl.bl_number,
                "match_type": "contains",
                "criticality": "important",
            },
        ],
        "expected_issues": [
            {
                "rule_id": "UCP600-20D",
                "severity": "minor",
                "title_contains": "loading",
                "description": "Bill of lading port of loading differs from the LC",
            }
        ],
        "false_positive_checks": [
            {
                "rule_id": "UCP600-20",
                "description": "The umbrella transport article should stay suppressed when UCP600-20D is the actionable child rule.",
            },
            {
                "rule_id": "CROSSDOC-BL-002",
                "description": "Port of discharge crossdoc mismatch should not fire on a loading-port-only discrepancy.",
            },
            {
                "rule_id": "UCP600-28A",
                "description": "Insurance originals rule should not leak into a clean transport-only discrepancy.",
            },
            {
                "rule_id": "CROSSDOC-BL-001",
                "description": "Legacy crossdoc loading-port mismatch should stay suppressed when UCP600-20D is the specific live finding.",
            },
            {
                "rule_id": "LC-TYPE-UNKNOWN",
                "description": "LC type uncertainty should not surface once a real documentary discrepancy is already present.",
            },
        ],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_022_invoice_buyer_mismatch():
    """Generate Set 022: Invoice buyer differs from LC applicant."""
    set_id = "set_022_invoice_buyer_mismatch"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BDQ18B",
        amount=107800.00,
        currency="USD",
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-Q18B",
        invoice_date="2026-03-01",
        lc_reference=lc.lc_number,
        seller_name=lc.beneficiary_name,
        seller_address=lc.beneficiary_address,
        buyer_name="Atlantic Retail Holdings",
        buyer_address="88 Alternate Buyer Avenue, New York, NY 10002, USA",
        amount=lc.amount,
        currency=lc.currency,
        goods_description=lc.goods_description,
        quantity=lc.quantity,
        unit_price=10.78,
        incoterms=lc.incoterms,
    )
    create_invoice_pdf(invoice, set_dir / "Invoice.pdf")

    bl = BLData(
        bl_number="MSKU2026Q18B",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="MSC DHAKA",
        voyage_number="V.Q18B",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,060 KG",
        container_number="MSCUQ18B01",
        seal_number="SLQ18B1",
        shipped_on_board_date="2026-03-03",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")

    expected = {
        "set_id": set_id,
        "description": "Commercial invoice buyer differs from the applicant named in the LC",
        "version": "1.0",
        "expected_compliance_rate": 82.0,
        "compliance_tolerance": 10.0,
        "expected_status": "warning",
        "expected_final_verdict": "review",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {
                "document_type": "lc",
                "field_name": "applicant",
                "expected_value": lc.applicant_name,
                "match_type": "contains",
                "criticality": "critical",
            },
            {
                "document_type": "invoice",
                "field_name": "buyer_name",
                "expected_value": invoice.buyer_name,
                "match_type": "contains",
                "criticality": "critical",
            },
        ],
        "expected_issues": [
            {
                "rule_id": "UCP600-18B",
                "severity": "minor",
                "document_type": "invoice",
                "title_contains": "applicant",
                "description": "Commercial invoice buyer differs from the LC applicant",
            }
        ],
        "false_positive_checks": [
            {
                "rule_id": "UCP600-18",
                "description": "Invoice umbrella article should stay suppressed when UCP600-18B is the actionable child rule.",
            },
            {
                "rule_id": "UCP600-18A",
                "description": "Invoice issuer rule should not fire when only the buyer/applicant pairing is wrong.",
            },
            {
                "rule_id": "UCP600-18C",
                "description": "Invoice currency rule should not leak into a buyer/applicant-only discrepancy.",
            },
            {
                "rule_id": "UCP600-20",
                "description": "Transport umbrella article should not leak into the invoice buyer-only case.",
            },
            {
                "rule_id": "UCP600-28",
                "description": "Insurance umbrella article should not leak into the invoice buyer-only case.",
            },
            {
                "rule_id": "LC-TYPE-UNKNOWN",
                "description": "LC type uncertainty should not surface once a real documentary discrepancy is already present.",
            },
        ],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

    print(f"[OK] Generated {set_id}: 6 documents + expected.json")
    return set_id


def generate_set_021_invoice_currency_mismatch():
    """Generate Set 021: Invoice currency differs from LC currency."""
    set_id = "set_021_invoice_currency_mismatch"
    set_dir = DOCUMENTS_DIR / set_id
    set_dir.mkdir(parents=True, exist_ok=True)

    lc = LCData(
        lc_number="EXP2026BDQ18C",
        amount=104500.00,
        currency="USD",
    )
    create_lc_pdf(lc, set_dir / "LC.pdf", force_text=True)

    invoice = InvoiceData(
        invoice_number="INV-2026-Q18C",
        invoice_date="2026-03-01",
        lc_reference=lc.lc_number,
        seller_name=lc.beneficiary_name,
        seller_address=lc.beneficiary_address,
        buyer_name=lc.applicant_name,
        buyer_address=lc.applicant_address,
        amount=lc.amount,
        currency="EUR",
        goods_description=lc.goods_description,
        quantity=lc.quantity,
        unit_price=10.45,
        incoterms=lc.incoterms,
    )
    create_invoice_pdf(invoice, set_dir / "Invoice.pdf")

    bl = BLData(
        bl_number="MSKU2026Q18C",
        shipper=lc.beneficiary_name,
        consignee=f"TO ORDER OF {lc.issuing_bank}",
        notify_party=lc.applicant_name,
        vessel_name="MSC DHAKA",
        voyage_number="V.Q18C",
        port_of_loading=lc.port_of_loading,
        port_of_discharge=lc.port_of_discharge,
        goods_description=lc.goods_description,
        gross_weight="2,050 KG",
        container_number="MSCUQ18C01",
        seal_number="SLQ18C1",
        shipped_on_board_date="2026-03-03",
    )
    create_bl_pdf(bl, set_dir / "Bill_of_Lading.pdf")

    create_packing_list(lc, invoice, set_dir / "Packing_List.pdf")
    create_certificate_of_origin(lc, set_dir / "Certificate_of_Origin.pdf")
    create_insurance_certificate(lc, set_dir / "Insurance_Certificate.pdf", issue_date="2026-03-01")

    expected = {
        "set_id": set_id,
        "description": "Commercial invoice is issued in a different currency than the LC",
        "version": "1.0",
        "expected_compliance_rate": 82.0,
        "compliance_tolerance": 10.0,
        "expected_status": "warning",
        "expected_final_verdict": "review",
        "expected_workflow_stage": "validation_results",
        "expected_fields": [
            {
                "document_type": "lc",
                "field_name": "lc_number",
                "expected_value": lc.lc_number,
                "match_type": "exact",
                "criticality": "critical",
            },
            {
                "document_type": "invoice",
                "field_name": "invoice_number",
                "expected_value": invoice.invoice_number,
                "match_type": "contains",
                "criticality": "important",
            },
        ],
        "expected_issues": [
            {
                "rule_id": "UCP600-18C",
                "severity": "minor",
                "document_type": "invoice",
                "title_contains": "currency",
                "description": "Commercial invoice currency differs from the LC",
            }
        ],
        "false_positive_checks": [
            {
                "rule_id": "UCP600-18",
                "description": "Invoice umbrella article should stay suppressed when UCP600-18C is the actionable child rule.",
            },
            {
                "rule_id": "UCP600-20",
                "description": "Transport umbrella article should not leak into the invoice currency-only case.",
            },
            {
                "rule_id": "UCP600-28",
                "description": "Insurance umbrella article should not leak into the invoice currency-only case.",
            },
            {
                "rule_id": "UCP600-28D",
                "description": "Insurance currency rule should not appear when only the invoice currency is wrong.",
            },
            {
                "rule_id": "LC-TYPE-UNKNOWN",
                "description": "LC type uncertainty should not surface once a real documentary discrepancy is already present.",
            },
        ],
    }
    (EXPECTED_DIR / f"{set_id}.json").write_text(json.dumps(expected, indent=2) + "\n")

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
        generate_set_007_missing_insurance_document(),
        generate_set_008_invoice_after_expiry(),
        generate_set_009_invoice_lc_reference_mismatch(),
        generate_set_010_invoice_missing_lc_reference(),
        generate_set_011_invoice_issuer_mismatch(),
        generate_set_012_bl_shipper_mismatch(),
        generate_set_013_bl_consignee_mismatch(),
        generate_set_014_insurance_currency_mismatch(),
        generate_set_015_po_number_missing(),
        generate_set_016_exporter_bin_missing(),
        generate_set_017_exporter_tin_missing(),
        generate_set_018_invoice_exact_wording_missing(),
        generate_set_019_insurance_originals_mismatch(),
        generate_set_020_bl_port_of_loading_mismatch(),
        generate_set_021_invoice_currency_mismatch(),
        generate_set_022_invoice_buyer_mismatch(),
    ]
    
    print("\n" + "=" * 60)
    print(f"Generated {len(sets)} test sets:")
    for s in sets:
        print(f"  - {s}")
    print("=" * 60)
    
    return sets


if __name__ == "__main__":
    main()

