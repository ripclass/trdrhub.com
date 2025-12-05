"""
Document Generator Service

Generates 15+ PDF shipping documents:
- Commercial Invoice (pre-filled from LC)
- Packing List (detailed carton breakdown)
- Certificate of Origin (basic format)
- Bill of Lading Draft (for carrier review)
- Bill of Exchange (draft/tenor)
- Beneficiary Certificate (LC attestation)
- Weight Certificate (auto-calculated)
- Inspection Certificate (PSI report)
- Insurance Certificate (marine cargo)
- Shipping Instructions (for forwarder)

Plus preferential origin certificates (separate service):
- GSP Form A
- EUR.1
- RCEP (coming soon)
"""

import io
import uuid
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.models.doc_generator import DocumentSet, DocumentLineItem, DocumentType

logger = logging.getLogger(__name__)


# ============== Styling ==============

def get_styles() -> Dict[str, ParagraphStyle]:
    """Get custom styles for documents"""
    styles = getSampleStyleSheet()
    
    # Document title
    styles.add(ParagraphStyle(
        name='DocTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=colors.black,
        fontName='Helvetica-Bold'
    ))
    
    # Section header
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.black
    ))
    
    # Normal text
    styles.add(ParagraphStyle(
        name='DocNormal',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        leading=12
    ))
    
    # Small text
    styles.add(ParagraphStyle(
        name='DocSmall',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica',
        leading=10
    ))
    
    # Bold text
    styles.add(ParagraphStyle(
        name='DocBold',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold'
    ))
    
    # Right aligned
    styles.add(ParagraphStyle(
        name='DocRight',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        alignment=TA_RIGHT
    ))
    
    # Center aligned
    styles.add(ParagraphStyle(
        name='DocCenter',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        alignment=TA_CENTER
    ))
    
    return styles


def number_to_words(n: float) -> str:
    """Convert number to words (for amounts)"""
    ones = ['', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE',
            'TEN', 'ELEVEN', 'TWELVE', 'THIRTEEN', 'FOURTEEN', 'FIFTEEN', 'SIXTEEN',
            'SEVENTEEN', 'EIGHTEEN', 'NINETEEN']
    tens = ['', '', 'TWENTY', 'THIRTY', 'FORTY', 'FIFTY', 'SIXTY', 'SEVENTY', 'EIGHTY', 'NINETY']
    
    def convert_hundreds(num):
        if num == 0:
            return ''
        elif num < 20:
            return ones[num]
        elif num < 100:
            return tens[num // 10] + ('' if num % 10 == 0 else ' ' + ones[num % 10])
        else:
            return ones[num // 100] + ' HUNDRED' + ('' if num % 100 == 0 else ' ' + convert_hundreds(num % 100))
    
    if n == 0:
        return 'ZERO'
    
    num = int(n)
    result = []
    
    if num >= 1000000:
        result.append(convert_hundreds(num // 1000000) + ' MILLION')
        num %= 1000000
    
    if num >= 1000:
        result.append(convert_hundreds(num // 1000) + ' THOUSAND')
        num %= 1000
    
    if num > 0:
        result.append(convert_hundreds(num))
    
    # Add cents
    cents = int(round((n - int(n)) * 100))
    if cents > 0:
        return ' '.join(result) + f' AND {cents}/100'
    
    return ' '.join(result) + ' ONLY'


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount with currency"""
    return f"{currency} {amount:,.2f}"


# ============== Commercial Invoice ==============

class CommercialInvoiceGenerator:
    """Generate Commercial Invoice PDF"""
    
    def __init__(self, doc_set: DocumentSet):
        self.doc_set = doc_set
        self.styles = get_styles()
    
    def generate(self) -> bytes:
        """Generate PDF and return as bytes"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        elements = []
        
        # Title
        elements.append(Paragraph("COMMERCIAL INVOICE", self.styles['DocTitle']))
        elements.append(Spacer(1, 10))
        
        # Invoice details header
        invoice_info = [
            ["Invoice No:", self.doc_set.invoice_number or "-", "Date:", self._format_date(self.doc_set.invoice_date)],
            ["L/C No:", self.doc_set.lc_number or "-", "L/C Date:", self._format_date(self.doc_set.lc_date)],
        ]
        
        info_table = Table(invoice_info, colWidths=[1.2*inch, 2*inch, 1*inch, 2*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 15))
        
        # Parties section
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
        elements.append(Spacer(1, 10))
        
        parties_data = [
            ["SELLER/BENEFICIARY:", "BUYER/APPLICANT:"],
            [self.doc_set.beneficiary_name, self.doc_set.applicant_name],
            [self.doc_set.beneficiary_address or "", self.doc_set.applicant_address or ""],
        ]
        
        parties_table = Table(parties_data, colWidths=[3.2*inch, 3.2*inch])
        parties_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(parties_table)
        elements.append(Spacer(1, 10))
        
        # Notify party
        if self.doc_set.notify_party_name:
            elements.append(Paragraph(f"<b>NOTIFY PARTY:</b> {self.doc_set.notify_party_name}", self.styles['DocNormal']))
            if self.doc_set.notify_party_address:
                elements.append(Paragraph(self.doc_set.notify_party_address, self.styles['DocSmall']))
            elements.append(Spacer(1, 10))
        
        # Shipping details
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("SHIPPING DETAILS", self.styles['SectionHeader']))
        
        shipping_data = [
            ["Vessel:", self.doc_set.vessel_name or "-", "Voyage:", self.doc_set.voyage_number or "-"],
            ["Port of Loading:", self.doc_set.port_of_loading or "-", "Port of Discharge:", self.doc_set.port_of_discharge or "-"],
            ["Container:", self.doc_set.container_number or "-", "Seal:", self.doc_set.seal_number or "-"],
            ["B/L No:", self.doc_set.bl_number or "-", "B/L Date:", self._format_date(self.doc_set.bl_date)],
        ]
        
        shipping_table = Table(shipping_data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 2*inch])
        shipping_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(shipping_table)
        elements.append(Spacer(1, 15))
        
        # Terms
        if self.doc_set.incoterms:
            elements.append(Paragraph(
                f"<b>DELIVERY TERMS:</b> {self.doc_set.incoterms} {self.doc_set.incoterms_place or ''}",
                self.styles['DocNormal']
            ))
            elements.append(Spacer(1, 10))
        
        # Goods table
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("DESCRIPTION OF GOODS", self.styles['SectionHeader']))
        
        # Build goods table
        goods_header = ["Item", "Description", "HS Code", "Qty", "Unit", "Unit Price", "Amount"]
        goods_data = [goods_header]
        
        total_qty = 0
        total_amount = Decimal("0")
        currency = self.doc_set.lc_currency or "USD"
        
        for item in sorted(self.doc_set.line_items, key=lambda x: x.line_number):
            amount = item.total_price or (Decimal(str(item.quantity)) * Decimal(str(item.unit_price or 0)))
            total_qty += item.quantity
            total_amount += Decimal(str(amount))
            
            goods_data.append([
                str(item.line_number),
                item.description[:50] + "..." if len(item.description) > 50 else item.description,
                item.hs_code or "-",
                f"{item.quantity:,}",
                item.unit or "PCS",
                f"{float(item.unit_price or 0):,.2f}",
                f"{float(amount):,.2f}"
            ])
        
        # Total row
        goods_data.append(["", "TOTAL", "", f"{total_qty:,}", "", "", f"{float(total_amount):,.2f}"])
        
        col_widths = [0.4*inch, 2.5*inch, 0.7*inch, 0.7*inch, 0.5*inch, 0.8*inch, 0.9*inch]
        goods_table = Table(goods_data, colWidths=col_widths)
        goods_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('PADDING', (0, 0), (-1, -1), 4),
            # Alignment
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
            ('ALIGN', (5, 1), (-1, -1), 'RIGHT'),
            # Total row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ]))
        elements.append(goods_table)
        elements.append(Spacer(1, 15))
        
        # Totals section
        elements.append(Paragraph(
            f"<b>TOTAL VALUE:</b> {currency} {float(total_amount):,.2f}",
            self.styles['DocBold']
        ))
        elements.append(Paragraph(
            f"<b>SAY:</b> {currency} {number_to_words(float(total_amount))}",
            self.styles['DocNormal']
        ))
        elements.append(Spacer(1, 10))
        
        # Packing details
        packing_text = []
        if self.doc_set.total_cartons:
            packing_text.append(f"Total Cartons: {self.doc_set.total_cartons:,}")
        if self.doc_set.gross_weight_kg:
            packing_text.append(f"Gross Weight: {float(self.doc_set.gross_weight_kg):,.2f} KG")
        if self.doc_set.net_weight_kg:
            packing_text.append(f"Net Weight: {float(self.doc_set.net_weight_kg):,.2f} KG")
        
        if packing_text:
            elements.append(Paragraph(" | ".join(packing_text), self.styles['DocNormal']))
            elements.append(Spacer(1, 10))
        
        # Shipping marks
        if self.doc_set.shipping_marks:
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
            elements.append(Spacer(1, 5))
            elements.append(Paragraph("SHIPPING MARKS:", self.styles['SectionHeader']))
            elements.append(Paragraph(self.doc_set.shipping_marks.replace("\n", "<br/>"), self.styles['DocSmall']))
            elements.append(Spacer(1, 10))
        
        # Country of origin
        if self.doc_set.country_of_origin:
            elements.append(Paragraph(f"COUNTRY OF ORIGIN: {self.doc_set.country_of_origin.upper()}", self.styles['DocBold']))
            elements.append(Spacer(1, 10))
        
        # Certification
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("WE CERTIFY THAT THIS INVOICE IS TRUE AND CORRECT", self.styles['DocCenter']))
        elements.append(Spacer(1, 30))
        
        # Signature
        elements.append(Paragraph(f"For {self.doc_set.beneficiary_name}", self.styles['DocNormal']))
        elements.append(Spacer(1, 25))
        elements.append(Paragraph("_" * 30, self.styles['DocNormal']))
        elements.append(Paragraph("Authorized Signature", self.styles['DocSmall']))
        
        # Build PDF
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _format_date(self, d) -> str:
        """Format date for display"""
        if d is None:
            return "-"
        if hasattr(d, 'strftime'):
            return d.strftime("%d %b %Y")
        return str(d)


# ============== Packing List ==============

class PackingListGenerator:
    """Generate Packing List PDF"""
    
    def __init__(self, doc_set: DocumentSet):
        self.doc_set = doc_set
        self.styles = get_styles()
    
    def generate(self) -> bytes:
        """Generate PDF and return as bytes"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        elements = []
        
        # Title
        elements.append(Paragraph("PACKING LIST", self.styles['DocTitle']))
        elements.append(Spacer(1, 10))
        
        # Reference info
        ref_info = [
            ["Invoice No:", self.doc_set.invoice_number or "-", "Date:", self._format_date(self.doc_set.invoice_date)],
            ["L/C No:", self.doc_set.lc_number or "-", "L/C Date:", self._format_date(self.doc_set.lc_date)],
        ]
        
        ref_table = Table(ref_info, colWidths=[1.2*inch, 2*inch, 1*inch, 2*inch])
        ref_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(ref_table)
        elements.append(Spacer(1, 15))
        
        # Parties
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
        elements.append(Spacer(1, 10))
        
        parties_data = [
            ["SELLER:", "BUYER:"],
            [self.doc_set.beneficiary_name, self.doc_set.applicant_name],
            [self.doc_set.beneficiary_address or "", self.doc_set.applicant_address or ""],
        ]
        
        parties_table = Table(parties_data, colWidths=[3.2*inch, 3.2*inch])
        parties_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(parties_table)
        elements.append(Spacer(1, 10))
        
        # Shipping details
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
        elements.append(Spacer(1, 10))
        
        shipping_data = [
            ["Vessel:", self.doc_set.vessel_name or "-", "Container:", self.doc_set.container_number or "-"],
            ["Port of Loading:", self.doc_set.port_of_loading or "-", "Port of Discharge:", self.doc_set.port_of_discharge or "-"],
        ]
        
        shipping_table = Table(shipping_data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 2*inch])
        shipping_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(shipping_table)
        elements.append(Spacer(1, 15))
        
        # Packing details table
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("PACKING DETAILS", self.styles['SectionHeader']))
        
        # Build packing table
        packing_header = ["Item", "Description", "Qty", "Unit", "Cartons", "Gross Wt (KG)", "Net Wt (KG)"]
        packing_data = [packing_header]
        
        total_qty = 0
        total_cartons = 0
        total_gross = Decimal("0")
        total_net = Decimal("0")
        
        for item in sorted(self.doc_set.line_items, key=lambda x: x.line_number):
            total_qty += item.quantity
            total_cartons += item.cartons or 0
            total_gross += Decimal(str(item.gross_weight_kg or 0))
            total_net += Decimal(str(item.net_weight_kg or 0))
            
            packing_data.append([
                str(item.line_number),
                item.description[:40] + "..." if len(item.description) > 40 else item.description,
                f"{item.quantity:,}",
                item.unit or "PCS",
                str(item.cartons or "-"),
                f"{float(item.gross_weight_kg or 0):,.2f}" if item.gross_weight_kg else "-",
                f"{float(item.net_weight_kg or 0):,.2f}" if item.net_weight_kg else "-",
            ])
        
        # Total row
        packing_data.append([
            "", "TOTAL", f"{total_qty:,}", "",
            str(total_cartons) if total_cartons else "-",
            f"{float(total_gross):,.2f}",
            f"{float(total_net):,.2f}"
        ])
        
        col_widths = [0.4*inch, 2.5*inch, 0.7*inch, 0.5*inch, 0.7*inch, 0.8*inch, 0.8*inch]
        packing_table = Table(packing_data, colWidths=col_widths)
        packing_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('PADDING', (0, 0), (-1, -1), 4),
            # Alignment
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            # Total row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ]))
        elements.append(packing_table)
        elements.append(Spacer(1, 15))
        
        # Summary
        if self.doc_set.cbm:
            elements.append(Paragraph(f"<b>Total CBM:</b> {float(self.doc_set.cbm):,.3f} m³", self.styles['DocNormal']))
        
        # Shipping marks
        if self.doc_set.shipping_marks:
            elements.append(Spacer(1, 10))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
            elements.append(Spacer(1, 5))
            elements.append(Paragraph("SHIPPING MARKS:", self.styles['SectionHeader']))
            elements.append(Paragraph(self.doc_set.shipping_marks.replace("\n", "<br/>"), self.styles['DocSmall']))
        
        # Certification
        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
        elements.append(Spacer(1, 15))
        elements.append(Paragraph("WE CERTIFY THAT THIS PACKING LIST IS TRUE AND CORRECT", self.styles['DocCenter']))
        elements.append(Spacer(1, 30))
        
        # Signature
        elements.append(Paragraph(f"For {self.doc_set.beneficiary_name}", self.styles['DocNormal']))
        elements.append(Spacer(1, 25))
        elements.append(Paragraph("_" * 30, self.styles['DocNormal']))
        elements.append(Paragraph("Authorized Signature", self.styles['DocSmall']))
        
        # Build PDF
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _format_date(self, d) -> str:
        """Format date for display"""
        if d is None:
            return "-"
        if hasattr(d, 'strftime'):
            return d.strftime("%d %b %Y")
        return str(d)


# ============== Beneficiary Certificate ==============

class BeneficiaryCertificateGenerator:
    """Generate Beneficiary Certificate PDF"""
    
    def __init__(self, doc_set: DocumentSet, certification_text: str = None):
        self.doc_set = doc_set
        self.styles = get_styles()
        self.certification_text = certification_text or self._default_certification()
    
    def _default_certification(self) -> str:
        """Default certification text"""
        return f"""We, {self.doc_set.beneficiary_name}, the beneficiary under the above-referenced Letter of Credit, 
hereby certify that all documents submitted for negotiation/payment are genuine and that all 
terms and conditions of the Letter of Credit have been fully complied with.

We further certify that the goods described in the documents have been shipped as per the 
terms of the Letter of Credit and that the documents presented are true and correct in 
every respect.

This certificate is issued in accordance with the requirements of Letter of Credit 
No. {self.doc_set.lc_number or '[LC NUMBER]'} dated {self._format_date(self.doc_set.lc_date)}."""
    
    def generate(self) -> bytes:
        """Generate PDF and return as bytes"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        elements = []
        
        # Title
        elements.append(Paragraph("BENEFICIARY'S CERTIFICATE", self.styles['DocTitle']))
        elements.append(Spacer(1, 20))
        
        # Reference
        elements.append(Paragraph(f"<b>Date:</b> {self._format_date(self.doc_set.invoice_date or datetime.now())}", self.styles['DocNormal']))
        elements.append(Paragraph(f"<b>L/C No:</b> {self.doc_set.lc_number or '-'}", self.styles['DocNormal']))
        elements.append(Paragraph(f"<b>Invoice No:</b> {self.doc_set.invoice_number or '-'}", self.styles['DocNormal']))
        elements.append(Spacer(1, 20))
        
        # To
        elements.append(Paragraph("<b>TO:</b>", self.styles['DocBold']))
        elements.append(Paragraph(self.doc_set.issuing_bank or self.doc_set.applicant_name, self.styles['DocNormal']))
        elements.append(Spacer(1, 20))
        
        # Certification
        elements.append(Paragraph("<b>CERTIFICATION:</b>", self.styles['SectionHeader']))
        elements.append(Spacer(1, 10))
        
        # Add certification text as justified paragraphs
        cert_style = ParagraphStyle(
            name='Certification',
            parent=self.styles['DocNormal'],
            alignment=TA_JUSTIFY,
            leading=14
        )
        elements.append(Paragraph(self.certification_text, cert_style))
        elements.append(Spacer(1, 30))
        
        # Signature
        elements.append(Paragraph(f"For and on behalf of", self.styles['DocNormal']))
        elements.append(Paragraph(f"<b>{self.doc_set.beneficiary_name}</b>", self.styles['DocBold']))
        if self.doc_set.beneficiary_address:
            elements.append(Paragraph(self.doc_set.beneficiary_address, self.styles['DocSmall']))
        elements.append(Spacer(1, 40))
        
        elements.append(Paragraph("_" * 35, self.styles['DocNormal']))
        elements.append(Paragraph("Authorized Signature", self.styles['DocSmall']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Name: _______________________", self.styles['DocSmall']))
        elements.append(Paragraph("Title: _______________________", self.styles['DocSmall']))
        elements.append(Paragraph("Date: _______________________", self.styles['DocSmall']))
        
        # Build PDF
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _format_date(self, d) -> str:
        """Format date for display"""
        if d is None:
            return datetime.now().strftime("%d %b %Y")
        if hasattr(d, 'strftime'):
            return d.strftime("%d %b %Y")
        return str(d)


# ============== Bill of Exchange ==============

class BillOfExchangeGenerator:
    """Generate Bill of Exchange (Draft) PDF"""
    
    def __init__(self, doc_set: DocumentSet):
        self.doc_set = doc_set
        self.styles = get_styles()
    
    def generate(self) -> bytes:
        """Generate PDF and return as bytes"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        elements = []
        
        # Title
        elements.append(Paragraph("BILL OF EXCHANGE", self.styles['DocTitle']))
        elements.append(Spacer(1, 15))
        
        # Amount and reference
        currency = self.doc_set.lc_currency or "USD"
        amount = float(self.doc_set.total_amount)
        
        elements.append(Paragraph(f"<b>No.:</b> {self.doc_set.invoice_number or '-'}", self.styles['DocRight']))
        elements.append(Paragraph(
            f"<b>Amount:</b> {currency} {amount:,.2f}",
            self.styles['DocRight']
        ))
        elements.append(Spacer(1, 20))
        
        # Tenor
        tenor = self.doc_set.draft_tenor or "AT SIGHT"
        elements.append(Paragraph(f"<b>{tenor}</b>", self.styles['DocBold']))
        elements.append(Spacer(1, 10))
        
        # Body
        body_text = f"""
        For value received, pay this FIRST OF EXCHANGE (second of exchange unpaid) to the order of 
        <b>{self.doc_set.beneficiary_name}</b> the sum of <b>{currency} {number_to_words(amount)}</b> 
        ({currency} {amount:,.2f}).
        
        Drawn under Letter of Credit No. <b>{self.doc_set.lc_number or '[LC NUMBER]'}</b> 
        dated {self._format_date(self.doc_set.lc_date)}.
        """
        
        body_style = ParagraphStyle(
            name='BillBody',
            parent=self.styles['DocNormal'],
            alignment=TA_JUSTIFY,
            leading=16,
            fontSize=10
        )
        elements.append(Paragraph(body_text, body_style))
        elements.append(Spacer(1, 20))
        
        # Drawee
        elements.append(Paragraph("<b>TO (DRAWEE):</b>", self.styles['SectionHeader']))
        drawee = self.doc_set.drawee_name or self.doc_set.issuing_bank or "[ISSUING BANK NAME]"
        elements.append(Paragraph(drawee, self.styles['DocNormal']))
        if self.doc_set.drawee_address:
            elements.append(Paragraph(self.doc_set.drawee_address, self.styles['DocSmall']))
        elements.append(Spacer(1, 30))
        
        # Drawer signature
        elements.append(HRFlowable(width="50%", thickness=0.5, color=colors.black))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"<b>DRAWER:</b> {self.doc_set.beneficiary_name}", self.styles['DocNormal']))
        elements.append(Spacer(1, 30))
        elements.append(Paragraph("_" * 35, self.styles['DocNormal']))
        elements.append(Paragraph("Authorized Signature", self.styles['DocSmall']))
        
        # Build PDF
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _format_date(self, d) -> str:
        """Format date for display"""
        if d is None:
            return "-"
        if hasattr(d, 'strftime'):
            return d.strftime("%d %b %Y")
        return str(d)


# ============== Certificate of Origin ==============

class CertificateOfOriginGenerator:
    """
    Generate Certificate of Origin PDF.
    
    Standard format accepted by most chambers of commerce.
    """
    
    def __init__(self, doc_set: DocumentSet):
        self.doc_set = doc_set
        self.styles = get_styles()
    
    def generate(self) -> bytes:
        """Generate PDF and return as bytes"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        elements = []
        
        # Header with title
        elements.append(Paragraph("CERTIFICATE OF ORIGIN", self.styles['DocTitle']))
        elements.append(Spacer(1, 5))
        
        # Reference numbers
        ref_data = [
            ["Certificate No:", f"COO-{self._get_ref_number()}", "Date:", self._format_date(self.doc_set.invoice_date)],
            ["Invoice No:", self.doc_set.invoice_number or "-", "L/C No:", self.doc_set.lc_number or "-"],
        ]
        
        ref_table = Table(ref_data, colWidths=[1.2*inch, 2*inch, 1*inch, 2*inch])
        ref_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(ref_table)
        elements.append(Spacer(1, 15))
        
        # Main content - Box structure
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
        
        # Box 1 & 2: Exporter and Consignee
        parties_data = [
            ["1. EXPORTER (Name, full address, country)", "2. CONSIGNEE (Name, full address, country)"],
            [
                f"{self.doc_set.beneficiary_name}\n{self.doc_set.beneficiary_address or ''}\n{self.doc_set.beneficiary_country or ''}",
                f"{self.doc_set.applicant_name}\n{self.doc_set.applicant_address or ''}\n{self.doc_set.applicant_country or ''}"
            ],
        ]
        
        parties_table = Table(parties_data, colWidths=[3.2*inch, 3.2*inch])
        parties_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, 1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ]))
        elements.append(parties_table)
        
        # Box 3: Transport details
        transport_header = Table(
            [["3. MEANS OF TRANSPORT AND ROUTE (as far as known)"]],
            colWidths=[6.4*inch]
        )
        transport_header.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(transport_header)
        
        transport_content = f"""
        Vessel: {self.doc_set.vessel_name or '-'}  |  Voyage: {self.doc_set.voyage_number or '-'}
        From: {self.doc_set.port_of_loading or '-'}  |  To: {self.doc_set.port_of_discharge or '-'}
        B/L No: {self.doc_set.bl_number or '-'}  |  B/L Date: {self._format_date(self.doc_set.bl_date)}
        """
        transport_body = Table([[transport_content.strip()]], colWidths=[6.4*inch])
        transport_body.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(transport_body)
        
        # Box 4: Country of Origin
        origin_country = self.doc_set.country_of_origin or self.doc_set.beneficiary_country or "-"
        origin_data = [
            ["4. COUNTRY OF ORIGIN", f"{origin_country.upper()}"]
        ]
        origin_table = Table(origin_data, colWidths=[3.2*inch, 3.2*inch])
        origin_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#f1f5f9")),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(origin_table)
        
        # Box 5: Goods description
        goods_header = Table(
            [["5. MARKS AND NUMBERS", "6. DESCRIPTION OF GOODS", "7. QTY", "8. WEIGHT"]],
            colWidths=[1.5*inch, 2.5*inch, 1*inch, 1.4*inch]
        )
        goods_header.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(goods_header)
        
        # Build goods rows
        goods_data = []
        for item in sorted(self.doc_set.line_items, key=lambda x: x.line_number):
            hs_note = f"\nHS: {item.hs_code}" if item.hs_code else ""
            goods_data.append([
                self.doc_set.shipping_marks or "N/M",
                f"{item.description}{hs_note}",
                f"{item.quantity:,} {item.unit or 'PCS'}",
                f"{float(item.gross_weight_kg or 0):,.2f} KG" if item.gross_weight_kg else "-"
            ])
        
        # Add total row
        total_qty = self.doc_set.total_quantity
        total_weight = float(self.doc_set.gross_weight_kg or 0)
        goods_data.append([
            "",
            "TOTAL",
            f"{total_qty:,}",
            f"{total_weight:,.2f} KG"
        ])
        
        goods_table = Table(goods_data, colWidths=[1.5*inch, 2.5*inch, 1*inch, 1.4*inch])
        goods_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            # Total row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ]))
        elements.append(goods_table)
        elements.append(Spacer(1, 10))
        
        # Certification statement
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black))
        elements.append(Spacer(1, 10))
        
        cert_text = f"""
        <b>DECLARATION BY THE EXPORTER</b><br/><br/>
        The undersigned hereby declares that the above details and statements are correct, 
        that all the goods were produced in <b>{origin_country.upper()}</b> and that they 
        comply with the origin requirements specified for those goods in the relevant trade 
        agreement. The undersigned undertakes to submit, at the request of the appropriate 
        authorities, any supporting evidence which these authorities may require.
        """
        
        cert_style = ParagraphStyle(
            name='CertText',
            parent=self.styles['DocNormal'],
            fontSize=8,
            leading=12,
            alignment=TA_JUSTIFY
        )
        elements.append(Paragraph(cert_text, cert_style))
        elements.append(Spacer(1, 15))
        
        # Signature boxes
        sig_data = [
            ["EXPORTER'S SIGNATURE", "CHAMBER OF COMMERCE CERTIFICATION"],
            [
                f"\n\nFor: {self.doc_set.beneficiary_name}\n\n_______________________\nAuthorized Signatory\n\nDate: {self._format_date(self.doc_set.invoice_date)}\n\nPlace: {self.doc_set.beneficiary_country or '_______'}",
                "\n\nWe hereby certify that the declaration by the exporter is correct.\n\n_______________________\nAuthorized Signature\n\nDate: _______________\n\nStamp:"
            ],
        ]
        
        sig_table = Table(sig_data, colWidths=[3.2*inch, 3.2*inch])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, 1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ]))
        elements.append(sig_table)
        
        # Build PDF
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _format_date(self, d) -> str:
        """Format date for display"""
        if d is None:
            return datetime.now().strftime("%d %b %Y")
        if hasattr(d, 'strftime'):
            return d.strftime("%d %b %Y")
        return str(d)
    
    def _get_ref_number(self) -> str:
        """Generate a reference number"""
        if self.doc_set.invoice_number:
            return self.doc_set.invoice_number.replace("/", "-")
        return datetime.now().strftime("%Y%m%d-%H%M")


# ============== Bill of Lading Draft ==============

class BillOfLadingDraftGenerator:
    """
    Generate Bill of Lading Draft PDF.
    
    Standard layout for carrier/shipper review before final B/L issuance.
    """
    
    def __init__(self, doc_set: DocumentSet):
        self.doc_set = doc_set
        self.styles = get_styles()
        self.page_width, self.page_height = A4
    
    def generate(self) -> bytes:
        """Generate PDF and return as bytes"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=40, leftMargin=40,
            topMargin=40, bottomMargin=40
        )
        
        elements = []
        
        # Watermark-style header
        elements.append(Paragraph("DRAFT - FOR APPROVAL ONLY", ParagraphStyle(
            'Draft',
            parent=self.styles['DocTitle'],
            textColor=colors.red,
            fontSize=12
        )))
        elements.append(Spacer(1, 10))
        
        # Title
        elements.append(Paragraph("BILL OF LADING", self.styles['DocTitle']))
        elements.append(Spacer(1, 20))
        
        # B/L Reference
        ref_data = [
            ["B/L No.", self.doc_set.bl_number or "TO BE ASSIGNED"],
            ["Date", self.doc_set.bl_date.strftime("%Y-%m-%d") if self.doc_set.bl_date else datetime.now().strftime("%Y-%m-%d")],
        ]
        ref_table = Table(ref_data, colWidths=[100, 200])
        ref_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(ref_table)
        elements.append(Spacer(1, 15))
        
        # Shipper (Beneficiary)
        elements.append(Paragraph("SHIPPER", self.styles['SectionHeader']))
        shipper_text = f"{self.doc_set.beneficiary_name or ''}"
        if self.doc_set.beneficiary_address:
            shipper_text += f"<br/>{self.doc_set.beneficiary_address}"
        elements.append(Paragraph(shipper_text, self.styles['DocNormal']))
        elements.append(Spacer(1, 10))
        
        # Consignee
        elements.append(Paragraph("CONSIGNEE", self.styles['SectionHeader']))
        consignee_text = f"{self.doc_set.applicant_name or 'TO ORDER'}"
        if self.doc_set.applicant_address:
            consignee_text += f"<br/>{self.doc_set.applicant_address}"
        elements.append(Paragraph(consignee_text, self.styles['DocNormal']))
        elements.append(Spacer(1, 10))
        
        # Notify Party
        elements.append(Paragraph("NOTIFY PARTY", self.styles['SectionHeader']))
        notify_text = self.doc_set.notify_party_name or "SAME AS CONSIGNEE"
        if self.doc_set.notify_party_address:
            notify_text += f"<br/>{self.doc_set.notify_party_address}"
        elements.append(Paragraph(notify_text, self.styles['DocNormal']))
        elements.append(Spacer(1, 15))
        
        # Vessel & Voyage
        vessel_data = [
            ["Vessel", self.doc_set.vessel_name or ""],
            ["Voyage No.", self.doc_set.voyage_number or ""],
            ["Port of Loading", self.doc_set.port_of_loading or ""],
            ["Port of Discharge", self.doc_set.port_of_discharge or ""],
            ["Final Destination", self.doc_set.final_destination or ""],
        ]
        vessel_table = Table(vessel_data, colWidths=[120, 350])
        vessel_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(vessel_table)
        elements.append(Spacer(1, 15))
        
        # Container Details
        if self.doc_set.container_number or self.doc_set.seal_number:
            elements.append(Paragraph("CONTAINER DETAILS", self.styles['SectionHeader']))
            container_data = [
                ["Container No.", self.doc_set.container_number or ""],
                ["Seal No.", self.doc_set.seal_number or ""],
            ]
            container_table = Table(container_data, colWidths=[120, 350])
            container_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(container_table)
            elements.append(Spacer(1, 15))
        
        # Goods Description
        elements.append(Paragraph("PARTICULARS OF GOODS", self.styles['SectionHeader']))
        
        # Build goods table
        goods_header = ["Marks & Numbers", "Description", "Packages", "Gross Wt (KG)"]
        goods_data = [goods_header]
        
        marks = self.doc_set.shipping_marks or "N/M"
        
        if self.doc_set.line_items:
            for item in self.doc_set.line_items:
                goods_data.append([
                    marks,
                    item.description[:80] if item.description else "",
                    f"{item.cartons or ''} CTNS" if item.cartons else str(item.quantity or ""),
                    f"{float(item.gross_weight_kg):.2f}" if item.gross_weight_kg else ""
                ])
        else:
            goods_data.append([marks, "AS PER COMMERCIAL INVOICE", "", ""])
        
        # Totals row
        total_cartons = self.doc_set.total_cartons or sum(i.cartons or 0 for i in (self.doc_set.line_items or []))
        total_gross = self.doc_set.gross_weight_kg or sum(float(i.gross_weight_kg or 0) for i in (self.doc_set.line_items or []))
        goods_data.append(["", "TOTAL", f"{total_cartons} CTNS", f"{float(total_gross):.2f}"])
        
        col_widths = [100, 220, 80, 80]
        goods_table = Table(goods_data, colWidths=col_widths)
        goods_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0e0e0')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(goods_table)
        elements.append(Spacer(1, 20))
        
        # Freight & Charges
        elements.append(Paragraph("FREIGHT & CHARGES", self.styles['SectionHeader']))
        freight_text = "FREIGHT PREPAID" if self.doc_set.incoterms in ["CIF", "CFR", "CIP", "CPT", "DAP", "DDP"] else "FREIGHT COLLECT"
        elements.append(Paragraph(freight_text, self.styles['DocNormal']))
        elements.append(Spacer(1, 20))
        
        # Draft Notice
        draft_notice = """
        <b>DRAFT NOTICE:</b> This is a draft Bill of Lading for review purposes only. 
        It is not a valid transport document. Please review all details carefully and 
        confirm any corrections before the final B/L is issued by the carrier.
        """
        elements.append(Paragraph(draft_notice, ParagraphStyle(
            'Notice',
            parent=self.styles['DocSmall'],
            backColor=colors.HexColor('#fff3cd'),
            borderPadding=10,
            borderColor=colors.HexColor('#ffc107'),
            borderWidth=1,
        )))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


# ============== Weight Certificate ==============

class WeightCertificateGenerator:
    """
    Generate Weight Certificate PDF.
    
    Auto-calculated from packing list details with official certification text.
    """
    
    def __init__(self, doc_set: DocumentSet):
        self.doc_set = doc_set
        self.styles = get_styles()
    
    def generate(self) -> bytes:
        """Generate PDF and return as bytes"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=50, leftMargin=50,
            topMargin=50, bottomMargin=50
        )
        
        elements = []
        
        # Company letterhead if available
        if self.doc_set.company_logo_url:
            elements.append(Spacer(1, 20))
        
        # Title
        elements.append(Paragraph("WEIGHT CERTIFICATE", self.styles['DocTitle']))
        elements.append(Spacer(1, 10))
        
        # Certificate Number and Date
        cert_no = f"WT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
        ref_data = [
            ["Certificate No.", cert_no],
            ["Date", datetime.now().strftime("%B %d, %Y")],
            ["Invoice No.", self.doc_set.invoice_number or ""],
            ["LC No.", self.doc_set.lc_number or ""],
        ]
        ref_table = Table(ref_data, colWidths=[120, 350])
        ref_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(ref_table)
        elements.append(Spacer(1, 20))
        
        # We Hereby Certify
        elements.append(Paragraph("WE HEREBY CERTIFY THAT:", self.styles['SectionHeader']))
        elements.append(Spacer(1, 10))
        
        # Shipment Details
        shipment_text = f"""
        The goods shipped under Invoice No. <b>{self.doc_set.invoice_number or 'N/A'}</b> 
        dated <b>{self.doc_set.invoice_date.strftime('%B %d, %Y') if self.doc_set.invoice_date else 'N/A'}</b>
        from <b>{self.doc_set.beneficiary_name or ''}</b>
        to <b>{self.doc_set.applicant_name or ''}</b>
        have been weighed and the weights are as stated below:
        """
        elements.append(Paragraph(shipment_text, self.styles['DocNormal']))
        elements.append(Spacer(1, 15))
        
        # Weight Details Table
        weight_header = ["Description", "No. of Packages", "Gross Weight (KG)", "Net Weight (KG)"]
        weight_data = [weight_header]
        
        total_packages = 0
        total_gross = Decimal('0')
        total_net = Decimal('0')
        
        if self.doc_set.line_items:
            for item in self.doc_set.line_items:
                packages = item.cartons or item.quantity or 0
                gross = item.gross_weight_kg or Decimal('0')
                net = item.net_weight_kg or Decimal('0')
                
                total_packages += packages
                total_gross += gross
                total_net += net
                
                weight_data.append([
                    (item.description or "")[:50],
                    str(packages),
                    f"{float(gross):,.3f}",
                    f"{float(net):,.3f}"
                ])
        else:
            total_packages = self.doc_set.total_cartons or 0
            total_gross = self.doc_set.gross_weight_kg or Decimal('0')
            total_net = self.doc_set.net_weight_kg or Decimal('0')
            weight_data.append([
                "As per Commercial Invoice",
                str(total_packages),
                f"{float(total_gross):,.3f}",
                f"{float(total_net):,.3f}"
            ])
        
        # Totals
        weight_data.append([
            "TOTAL",
            str(total_packages),
            f"{float(total_gross):,.3f}",
            f"{float(total_net):,.3f}"
        ])
        
        weight_table = Table(weight_data, colWidths=[200, 80, 100, 100])
        weight_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e8e8')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(weight_table)
        elements.append(Spacer(1, 20))
        
        # Weight Summary in Words
        elements.append(Paragraph("WEIGHT SUMMARY:", self.styles['SectionHeader']))
        summary_data = [
            ["Total Gross Weight:", f"{float(total_gross):,.3f} KG", f"({number_to_words(float(total_gross))} KILOGRAMS)"],
            ["Total Net Weight:", f"{float(total_net):,.3f} KG", f"({number_to_words(float(total_net))} KILOGRAMS)"],
        ]
        summary_table = Table(summary_data, colWidths=[120, 100, 260])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 25))
        
        # Certification
        certification = """
        We certify that the above weights are correct and were determined by weighing on 
        calibrated scales. This certificate is issued at the request of the shipper and 
        reflects the actual weights of the merchandise at the time of shipment.
        """
        elements.append(Paragraph(certification, self.styles['DocNormal']))
        elements.append(Spacer(1, 30))
        
        # Signature
        elements.append(Paragraph(f"For and on behalf of", self.styles['DocNormal']))
        elements.append(Paragraph(f"<b>{self.doc_set.beneficiary_name or ''}</b>", self.styles['DocBold']))
        elements.append(Spacer(1, 25))
        elements.append(Paragraph("_" * 40, self.styles['DocNormal']))
        elements.append(Paragraph(self.doc_set.company_signatory_name or "Authorized Signatory", self.styles['DocSmall']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


# ============== Insurance Certificate ==============

class InsuranceCertificateGenerator:
    """
    Generate Insurance Certificate PDF.
    
    Marine cargo insurance certificate format.
    """
    
    def __init__(self, doc_set: DocumentSet):
        self.doc_set = doc_set
        self.styles = get_styles()
    
    def generate(self) -> bytes:
        """Generate PDF and return as bytes"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=50, leftMargin=50,
            topMargin=50, bottomMargin=50
        )
        
        elements = []
        
        # Title
        elements.append(Paragraph("CERTIFICATE OF INSURANCE", self.styles['DocTitle']))
        elements.append(Paragraph("Marine Cargo Policy", self.styles['DocCenter']))
        elements.append(Spacer(1, 20))
        
        # Certificate Number
        cert_no = f"INS-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
        elements.append(Paragraph(f"Certificate No: <b>{cert_no}</b>", self.styles['DocRight']))
        elements.append(Paragraph(f"Date: <b>{datetime.now().strftime('%B %d, %Y')}</b>", self.styles['DocRight']))
        elements.append(Spacer(1, 15))
        
        # Declaration
        declaration = """
        <b>THIS IS TO CERTIFY</b> that the undermentioned cargo is insured under 
        Marine Cargo Open Policy and is subject to Institute Cargo Clauses (A) 
        with Institute War Clauses (Cargo) and Institute Strikes Clauses (Cargo).
        """
        elements.append(Paragraph(declaration, self.styles['DocNormal']))
        elements.append(Spacer(1, 15))
        
        # Policy Details
        total_amount = float(self.doc_set.lc_amount or sum(float(i.total_price or 0) for i in (self.doc_set.line_items or [])))
        insured_amount = total_amount * 1.10  # 110% CIF value
        
        policy_data = [
            ["Insured:", self.doc_set.beneficiary_name or ""],
            ["Invoice No.:", self.doc_set.invoice_number or ""],
            ["LC No.:", self.doc_set.lc_number or ""],
            ["Sum Insured:", f"{self.doc_set.lc_currency or 'USD'} {insured_amount:,.2f} (110% of CIF Value)"],
        ]
        policy_table = Table(policy_data, colWidths=[100, 380])
        policy_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(policy_table)
        elements.append(Spacer(1, 15))
        
        # Shipment Details
        elements.append(Paragraph("SHIPMENT DETAILS:", self.styles['SectionHeader']))
        shipment_data = [
            ["Vessel:", self.doc_set.vessel_name or "ANY APPROVED VESSEL"],
            ["Voyage:", self.doc_set.voyage_number or ""],
            ["From:", self.doc_set.port_of_loading or ""],
            ["To:", self.doc_set.port_of_discharge or ""],
            ["Final Destination:", self.doc_set.final_destination or self.doc_set.port_of_discharge or ""],
            ["B/L No.:", self.doc_set.bl_number or ""],
            ["B/L Date:", self.doc_set.bl_date.strftime('%Y-%m-%d') if self.doc_set.bl_date else ""],
        ]
        shipment_table = Table(shipment_data, colWidths=[120, 360])
        shipment_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(shipment_table)
        elements.append(Spacer(1, 15))
        
        # Goods Description
        elements.append(Paragraph("DESCRIPTION OF GOODS:", self.styles['SectionHeader']))
        goods_desc = []
        if self.doc_set.line_items:
            for item in self.doc_set.line_items[:5]:  # Limit to 5 items
                goods_desc.append(f"• {item.description}")
        else:
            goods_desc.append("As per Commercial Invoice")
        elements.append(Paragraph("<br/>".join(goods_desc), self.styles['DocNormal']))
        
        # Packing & Marks
        if self.doc_set.shipping_marks:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(f"<b>Marks & Numbers:</b> {self.doc_set.shipping_marks}", self.styles['DocNormal']))
        
        elements.append(Spacer(1, 15))
        
        # Coverage & Claims
        coverage_text = """
        <b>COVERAGE:</b> Institute Cargo Clauses (A) - All Risks<br/>
        <b>WAR RISKS:</b> Institute War Clauses (Cargo)<br/>
        <b>STRIKES:</b> Institute Strikes Clauses (Cargo)<br/><br/>
        <b>CLAIMS:</b> In the event of loss or damage which may result in a claim under this 
        Certificate, immediate notice should be given to the nearest agent of the underwriters 
        and a survey arranged before delivery is taken.
        """
        elements.append(Paragraph(coverage_text, self.styles['DocNormal']))
        elements.append(Spacer(1, 20))
        
        # Claims Payable
        elements.append(Paragraph(
            f"<b>CLAIMS PAYABLE TO:</b> {self.doc_set.beneficiary_name or ''}", 
            self.styles['DocNormal']
        ))
        if self.doc_set.issuing_bank:
            elements.append(Paragraph(
                f"<b>OR ENDORSEE BANK:</b> {self.doc_set.issuing_bank}", 
                self.styles['DocNormal']
            ))
        elements.append(Spacer(1, 25))
        
        # Signature
        elements.append(Paragraph("For and on behalf of the Insurers", self.styles['DocCenter']))
        elements.append(Spacer(1, 25))
        elements.append(Paragraph("_" * 40, self.styles['DocCenter']))
        elements.append(Paragraph("Authorized Signatory", self.styles['DocCenter']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


# ============== Shipping Instructions ==============

class ShippingInstructionsGenerator:
    """
    Generate Shipping Instructions PDF.
    
    Document sent to freight forwarder/carrier with shipment details.
    """
    
    def __init__(self, doc_set: DocumentSet):
        self.doc_set = doc_set
        self.styles = get_styles()
    
    def generate(self) -> bytes:
        """Generate PDF and return as bytes"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=40, leftMargin=40,
            topMargin=40, bottomMargin=40
        )
        
        elements = []
        
        # Header
        elements.append(Paragraph("SHIPPING INSTRUCTIONS", self.styles['DocTitle']))
        elements.append(Spacer(1, 5))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.black))
        elements.append(Spacer(1, 10))
        
        # Date and Reference
        ref_text = f"Date: {datetime.now().strftime('%B %d, %Y')}"
        if self.doc_set.invoice_number:
            ref_text += f" | Ref: {self.doc_set.invoice_number}"
        elements.append(Paragraph(ref_text, self.styles['DocRight']))
        elements.append(Spacer(1, 15))
        
        # Shipper Details (Beneficiary)
        elements.append(Paragraph("1. SHIPPER (EXPORTER)", self.styles['SectionHeader']))
        shipper_text = f"""
        <b>{self.doc_set.beneficiary_name or ''}</b><br/>
        {self.doc_set.beneficiary_address or ''}<br/>
        {self.doc_set.beneficiary_country or ''}<br/>
        Contact: {self.doc_set.company_contact_email or ''} / {self.doc_set.company_contact_phone or ''}
        """
        elements.append(Paragraph(shipper_text, self.styles['DocNormal']))
        elements.append(Spacer(1, 10))
        
        # Consignee
        elements.append(Paragraph("2. CONSIGNEE", self.styles['SectionHeader']))
        consignee_text = f"""
        <b>{self.doc_set.applicant_name or ''}</b><br/>
        {self.doc_set.applicant_address or ''}<br/>
        {self.doc_set.applicant_country or ''}
        """
        elements.append(Paragraph(consignee_text, self.styles['DocNormal']))
        elements.append(Spacer(1, 10))
        
        # Notify Party
        elements.append(Paragraph("3. NOTIFY PARTY", self.styles['SectionHeader']))
        notify_text = self.doc_set.notify_party_name or "SAME AS CONSIGNEE"
        if self.doc_set.notify_party_address:
            notify_text += f"<br/>{self.doc_set.notify_party_address}"
        elements.append(Paragraph(notify_text, self.styles['DocNormal']))
        elements.append(Spacer(1, 15))
        
        # Shipment Details
        elements.append(Paragraph("4. SHIPMENT DETAILS", self.styles['SectionHeader']))
        shipment_data = [
            ["Port of Loading:", self.doc_set.port_of_loading or "", "ETD:", ""],
            ["Port of Discharge:", self.doc_set.port_of_discharge or "", "ETA:", ""],
            ["Final Destination:", self.doc_set.final_destination or "", "", ""],
            ["Incoterms:", f"{self.doc_set.incoterms or ''} {self.doc_set.incoterms_place or ''}", "", ""],
        ]
        shipment_table = Table(shipment_data, colWidths=[100, 180, 50, 140])
        shipment_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(shipment_table)
        elements.append(Spacer(1, 15))
        
        # Cargo Details
        elements.append(Paragraph("5. CARGO DETAILS", self.styles['SectionHeader']))
        cargo_header = ["Description", "Qty", "Packages", "Gross Wt (KG)", "CBM"]
        cargo_data = [cargo_header]
        
        total_pkgs = 0
        total_gross = Decimal('0')
        total_cbm = self.doc_set.cbm or Decimal('0')
        
        if self.doc_set.line_items:
            for item in self.doc_set.line_items[:8]:  # Limit rows
                pkgs = item.cartons or 0
                gross = item.gross_weight_kg or Decimal('0')
                total_pkgs += pkgs
                total_gross += gross
                
                cargo_data.append([
                    (item.description or "")[:40],
                    str(item.quantity or ""),
                    f"{pkgs} CTNS",
                    f"{float(gross):,.2f}",
                    ""
                ])
        
        cargo_data.append([
            "TOTAL", "", f"{total_pkgs} CTNS", f"{float(total_gross):,.2f}", f"{float(total_cbm):,.3f}" if total_cbm else ""
        ])
        
        cargo_table = Table(cargo_data, colWidths=[180, 50, 70, 90, 60])
        cargo_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0e0e0')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(cargo_table)
        elements.append(Spacer(1, 15))
        
        # Container Info
        if self.doc_set.container_number:
            elements.append(Paragraph("6. CONTAINER REQUIREMENTS", self.styles['SectionHeader']))
            elements.append(Paragraph(f"Container No: {self.doc_set.container_number}", self.styles['DocNormal']))
            if self.doc_set.seal_number:
                elements.append(Paragraph(f"Seal No: {self.doc_set.seal_number}", self.styles['DocNormal']))
            elements.append(Spacer(1, 10))
        
        # Shipping Marks
        elements.append(Paragraph("7. SHIPPING MARKS", self.styles['SectionHeader']))
        marks = self.doc_set.shipping_marks or "N/M"
        elements.append(Paragraph(marks.replace("\n", "<br/>"), self.styles['DocNormal']))
        elements.append(Spacer(1, 15))
        
        # Special Instructions
        elements.append(Paragraph("8. SPECIAL INSTRUCTIONS", self.styles['SectionHeader']))
        instructions = self.doc_set.remarks or "NIL"
        elements.append(Paragraph(instructions, self.styles['DocNormal']))
        elements.append(Spacer(1, 15))
        
        # Documents Required
        elements.append(Paragraph("9. DOCUMENTS REQUIRED", self.styles['SectionHeader']))
        docs_required = """
        □ Bill of Lading (Original x 3)<br/>
        □ Commercial Invoice<br/>
        □ Packing List<br/>
        □ Certificate of Origin<br/>
        □ Insurance Certificate<br/>
        □ Other: _________________
        """
        elements.append(Paragraph(docs_required, self.styles['DocNormal']))
        elements.append(Spacer(1, 20))
        
        # Signature
        elements.append(Paragraph("Authorized by:", self.styles['DocNormal']))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("_" * 40 + "                    Date: " + "_" * 20, self.styles['DocNormal']))
        elements.append(Paragraph(self.doc_set.company_signatory_name or "Name & Title", self.styles['DocSmall']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


# ============== Inspection Certificate ==============

class InspectionCertificateGenerator:
    """
    Generate Inspection Certificate PDF.
    
    Quality/quantity inspection certification document.
    """
    
    def __init__(self, doc_set: DocumentSet):
        self.doc_set = doc_set
        self.styles = get_styles()
    
    def generate(self) -> bytes:
        """Generate PDF and return as bytes"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=50, leftMargin=50,
            topMargin=50, bottomMargin=50
        )
        
        elements = []
        
        # Title
        elements.append(Paragraph("INSPECTION CERTIFICATE", self.styles['DocTitle']))
        elements.append(Spacer(1, 5))
        elements.append(Paragraph("Pre-Shipment Inspection Report", self.styles['DocCenter']))
        elements.append(Spacer(1, 20))
        
        # Certificate Number
        cert_no = f"PSI-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
        elements.append(Paragraph(f"<b>Certificate No:</b> {cert_no}", self.styles['DocRight']))
        elements.append(Paragraph(f"<b>Date of Inspection:</b> {datetime.now().strftime('%B %d, %Y')}", self.styles['DocRight']))
        elements.append(Spacer(1, 15))
        
        # Parties
        parties_data = [
            ["Seller/Exporter:", self.doc_set.beneficiary_name or ""],
            ["Buyer/Importer:", self.doc_set.applicant_name or ""],
            ["Invoice No.:", self.doc_set.invoice_number or ""],
            ["Invoice Date:", self.doc_set.invoice_date.strftime('%Y-%m-%d') if self.doc_set.invoice_date else ""],
            ["LC No.:", self.doc_set.lc_number or ""],
            ["PO/Contract No.:", self.doc_set.po_number or ""],
        ]
        parties_table = Table(parties_data, colWidths=[120, 360])
        parties_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(parties_table)
        elements.append(Spacer(1, 15))
        
        # Inspection Details
        elements.append(Paragraph("INSPECTION DETAILS", self.styles['SectionHeader']))
        inspection_data = [
            ["Place of Inspection:", self.doc_set.port_of_loading or self.doc_set.beneficiary_country or ""],
            ["Inspection Type:", "Pre-Shipment Inspection (PSI)"],
            ["Sampling Method:", "Random Sampling per AQL 2.5"],
        ]
        insp_table = Table(inspection_data, colWidths=[120, 360])
        insp_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(insp_table)
        elements.append(Spacer(1, 15))
        
        # Goods Inspected
        elements.append(Paragraph("GOODS INSPECTED", self.styles['SectionHeader']))
        
        goods_header = ["Item", "Description", "Qty Ordered", "Qty Inspected", "Result"]
        goods_data = [goods_header]
        
        if self.doc_set.line_items:
            for i, item in enumerate(self.doc_set.line_items[:10], 1):
                goods_data.append([
                    str(i),
                    (item.description or "")[:40],
                    str(item.quantity or ""),
                    str(item.quantity or ""),
                    "PASS"
                ])
        else:
            goods_data.append(["1", "As per Commercial Invoice", "", "", "PASS"])
        
        goods_table = Table(goods_data, colWidths=[30, 200, 70, 80, 60])
        goods_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e0e0e0')),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(goods_table)
        elements.append(Spacer(1, 15))
        
        # Inspection Results
        elements.append(Paragraph("INSPECTION RESULTS", self.styles['SectionHeader']))
        
        results_data = [
            ["QUANTITY CHECK", "✓ SATISFACTORY"],
            ["QUALITY CHECK", "✓ SATISFACTORY"],
            ["PACKING CHECK", "✓ SATISFACTORY"],
            ["MARKING CHECK", "✓ SATISFACTORY"],
            ["DOCUMENTATION", "✓ SATISFACTORY"],
        ]
        results_table = Table(results_data, colWidths=[200, 250])
        results_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#d4edda')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(results_table)
        elements.append(Spacer(1, 15))
        
        # Conclusion
        elements.append(Paragraph("CONCLUSION", self.styles['SectionHeader']))
        conclusion = """
        Based on the inspection conducted, we hereby certify that the goods described above 
        were found to be in conformity with the specifications, quality standards, and 
        requirements as stated in the purchase order/contract/LC. The goods are considered 
        <b>FIT FOR SHIPMENT</b>.
        """
        elements.append(Paragraph(conclusion, self.styles['DocNormal']))
        elements.append(Spacer(1, 15))
        
        # Remarks
        elements.append(Paragraph("REMARKS:", self.styles['SectionHeader']))
        elements.append(Paragraph("NIL", self.styles['DocNormal']))
        elements.append(Spacer(1, 25))
        
        # Signature
        elements.append(Paragraph("CERTIFIED BY:", self.styles['DocNormal']))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("_" * 40, self.styles['DocNormal']))
        elements.append(Paragraph("Inspector Name & Signature", self.styles['DocSmall']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("_" * 40, self.styles['DocNormal']))
        elements.append(Paragraph("Company Stamp", self.styles['DocSmall']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()


# ============== Main Generator Service ==============

class DocumentGeneratorService:
    """Main service for generating shipping documents"""
    
    def generate_document(
        self, 
        doc_set: DocumentSet, 
        doc_type: DocumentType,
        **kwargs
    ) -> Tuple[bytes, str]:
        """
        Generate a single document.
        
        Returns: (pdf_bytes, filename)
        """
        generators = {
            # Core Documents
            DocumentType.COMMERCIAL_INVOICE: CommercialInvoiceGenerator,
            DocumentType.PACKING_LIST: PackingListGenerator,
            DocumentType.BENEFICIARY_CERTIFICATE: BeneficiaryCertificateGenerator,
            DocumentType.BILL_OF_EXCHANGE: BillOfExchangeGenerator,
            DocumentType.CERTIFICATE_OF_ORIGIN: CertificateOfOriginGenerator,
            # Shipping Documents
            DocumentType.BILL_OF_LADING_DRAFT: BillOfLadingDraftGenerator,
            DocumentType.SHIPPING_INSTRUCTIONS: ShippingInstructionsGenerator,
            # Certificates
            DocumentType.WEIGHT_CERTIFICATE: WeightCertificateGenerator,
            DocumentType.INSPECTION_CERTIFICATE: InspectionCertificateGenerator,
            # Insurance
            DocumentType.INSURANCE_CERTIFICATE: InsuranceCertificateGenerator,
        }
        
        generator_class = generators.get(doc_type)
        if not generator_class:
            raise ValueError(f"Unsupported document type: {doc_type}")
        
        generator = generator_class(doc_set, **kwargs) if kwargs else generator_class(doc_set)
        pdf_bytes = generator.generate()
        
        # Generate filename
        safe_lc = (doc_set.lc_number or "DRAFT").replace("/", "-").replace(" ", "_")
        type_name = doc_type.value.replace("_", "-")
        filename = f"{type_name}_{safe_lc}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        logger.info(f"Generated {doc_type.value} for {doc_set.lc_number}: {len(pdf_bytes)} bytes")
        
        return pdf_bytes, filename
    
    def generate_all(
        self, 
        doc_set: DocumentSet, 
        doc_types: List[DocumentType] = None
    ) -> Dict[DocumentType, Tuple[bytes, str]]:
        """
        Generate multiple documents.
        
        Returns: {doc_type: (pdf_bytes, filename)}
        """
        if doc_types is None:
            doc_types = [
                DocumentType.COMMERCIAL_INVOICE,
                DocumentType.PACKING_LIST,
            ]
        
        results = {}
        for doc_type in doc_types:
            try:
                pdf_bytes, filename = self.generate_document(doc_set, doc_type)
                results[doc_type] = (pdf_bytes, filename)
            except Exception as e:
                logger.error(f"Error generating {doc_type.value}: {e}")
        
        return results


# Singleton instance
_doc_generator_service: Optional[DocumentGeneratorService] = None


def get_document_generator() -> DocumentGeneratorService:
    """Get or create document generator service"""
    global _doc_generator_service
    if _doc_generator_service is None:
        _doc_generator_service = DocumentGeneratorService()
    return _doc_generator_service

