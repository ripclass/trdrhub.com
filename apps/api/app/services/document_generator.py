"""
Document Generator Service

Generates PDF shipping documents:
- Commercial Invoice
- Packing List
- Beneficiary Certificate
- Bill of Exchange
- Certificate of Origin
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
            DocumentType.COMMERCIAL_INVOICE: CommercialInvoiceGenerator,
            DocumentType.PACKING_LIST: PackingListGenerator,
            DocumentType.BENEFICIARY_CERTIFICATE: BeneficiaryCertificateGenerator,
            DocumentType.BILL_OF_EXCHANGE: BillOfExchangeGenerator,
            DocumentType.CERTIFICATE_OF_ORIGIN: CertificateOfOriginGenerator,
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

