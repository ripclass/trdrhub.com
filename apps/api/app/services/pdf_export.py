"""
PDF Export Service

Generates PDF compliance reports for price verification results.
Uses ReportLab for PDF generation.
"""

import io
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not installed. PDF export will be unavailable.")


def generate_verification_pdf(
    verification_result: Dict[str, Any],
    company_name: Optional[str] = None,
    include_market_details: bool = True,
) -> Optional[bytes]:
    """
    Generate a PDF compliance report for a single price verification.
    
    Args:
        verification_result: The verification result dict from verify_price
        company_name: Optional company name for the header
        include_market_details: Whether to include market data details
        
    Returns:
        PDF bytes or None if generation fails
    """
    if not REPORTLAB_AVAILABLE:
        logger.error("ReportLab not available for PDF generation")
        return None
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=25*mm,
            bottomMargin=20*mm,
        )
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        styles.add(ParagraphStyle(
            name='TRDRTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=12,
            textColor=colors.HexColor('#1a1a2e'),
        ))
        styles.add(ParagraphStyle(
            name='TRDRSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.gray,
            spaceAfter=20,
        ))
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor('#16213e'),
        ))
        styles.add(ParagraphStyle(
            name='VerdictPass',
            parent=styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#22c55e'),
            alignment=TA_CENTER,
        ))
        styles.add(ParagraphStyle(
            name='VerdictWarning',
            parent=styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#eab308'),
            alignment=TA_CENTER,
        ))
        styles.add(ParagraphStyle(
            name='VerdictFail',
            parent=styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#ef4444'),
            alignment=TA_CENTER,
        ))
        
        story = []
        
        # Header
        story.append(Paragraph("TRDR Price Verify", styles['TRDRTitle']))
        story.append(Paragraph("Price Verification Compliance Report", styles['TRDRSubtitle']))
        
        # Report metadata
        report_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        verification_id = verification_result.get("verification_id", "N/A")
        
        meta_data = [
            ["Report Date:", report_date],
            ["Verification ID:", verification_id[:8] + "..." if len(verification_id) > 12 else verification_id],
        ]
        if company_name:
            meta_data.insert(0, ["Company:", company_name])
        
        meta_table = Table(meta_data, colWidths=[80, 200])
        meta_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 20))
        
        # Verdict Banner
        verdict = verification_result.get("verdict", "unknown").upper()
        verdict_reason = verification_result.get("verdict_reason", "")
        
        verdict_style = {
            "PASS": styles['VerdictPass'],
            "WARNING": styles['VerdictWarning'],
            "FAIL": styles['VerdictFail'],
        }.get(verdict, styles['Normal'])
        
        verdict_color = {
            "PASS": colors.HexColor('#dcfce7'),
            "WARNING": colors.HexColor('#fef9c3'),
            "FAIL": colors.HexColor('#fee2e2'),
        }.get(verdict, colors.lightgrey)
        
        verdict_data = [[Paragraph(f"<b>VERDICT: {verdict}</b>", verdict_style)]]
        verdict_table = Table(verdict_data, colWidths=[500])
        verdict_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), verdict_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ]))
        story.append(verdict_table)
        
        if verdict_reason:
            story.append(Spacer(1, 8))
            story.append(Paragraph(verdict_reason, styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Commodity Information
        story.append(Paragraph("Commodity Information", styles['SectionHeader']))
        commodity = verification_result.get("commodity", {})
        
        commodity_data = [
            ["Commodity:", commodity.get("name", "N/A")],
            ["Code:", commodity.get("code", "N/A")],
            ["Category:", commodity.get("category", "N/A").replace("_", " ").title()],
            ["Matched From:", commodity.get("matched_from", "N/A")],
        ]
        
        commodity_table = Table(commodity_data, colWidths=[120, 380])
        commodity_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ]))
        story.append(commodity_table)
        story.append(Spacer(1, 15))
        
        # Price Comparison
        story.append(Paragraph("Price Comparison", styles['SectionHeader']))
        
        doc_price = verification_result.get("document_price", {})
        market_price = verification_result.get("market_price", {})
        variance = verification_result.get("variance", {})
        
        price_data = [
            ["", "Document Price", "Market Price"],
            [
                "Price",
                f"${doc_price.get('normalized_price', 0):,.2f}",
                f"${market_price.get('price', 0):,.2f}",
            ],
            [
                "Unit",
                doc_price.get('normalized_unit', 'N/A'),
                market_price.get('unit', 'N/A'),
            ],
            [
                "Currency",
                doc_price.get('normalized_currency', 'USD'),
                market_price.get('currency', 'USD'),
            ],
        ]
        
        price_table = Table(price_data, colWidths=[100, 200, 200])
        price_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(price_table)
        story.append(Spacer(1, 15))
        
        # Variance Analysis
        story.append(Paragraph("Variance Analysis", styles['SectionHeader']))
        
        variance_percent = variance.get("percent", 0)
        variance_direction = variance.get("direction", "match")
        
        direction_text = {
            "over": "Above Market",
            "under": "Below Market",
            "match": "Market Match",
        }.get(variance_direction, "N/A")
        
        variance_color = colors.HexColor('#22c55e') if abs(variance_percent) < 15 else \
                        colors.HexColor('#eab308') if abs(variance_percent) < 30 else \
                        colors.HexColor('#ef4444')
        
        variance_data = [
            ["Variance Percentage:", f"{variance_percent:+.2f}%"],
            ["Absolute Variance:", f"${variance.get('absolute', 0):,.2f}"],
            ["Direction:", direction_text],
        ]
        
        variance_table = Table(variance_data, colWidths=[150, 350])
        variance_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
            ('TEXTCOLOR', (1, 0), (1, 0), variance_color),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(variance_table)
        story.append(Spacer(1, 15))
        
        # Risk Assessment
        story.append(Paragraph("Risk Assessment", styles['SectionHeader']))
        
        risk = verification_result.get("risk", {})
        risk_level = risk.get("risk_level", "unknown").upper()
        risk_flags = risk.get("risk_flags", [])
        
        risk_color = {
            "LOW": colors.HexColor('#22c55e'),
            "MEDIUM": colors.HexColor('#eab308'),
            "HIGH": colors.HexColor('#f97316'),
            "CRITICAL": colors.HexColor('#ef4444'),
        }.get(risk_level, colors.gray)
        
        risk_data = [
            ["Risk Level:", Paragraph(f"<font color='{risk_color}'><b>{risk_level}</b></font>", styles['Normal'])],
        ]
        
        if risk_flags:
            flags_text = ", ".join([f.replace("_", " ").title() for f in risk_flags])
            risk_data.append(["Risk Flags:", flags_text])
        
        risk_table = Table(risk_data, colWidths=[120, 380])
        risk_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(risk_table)
        
        # TBML Warning if applicable
        if "tbml_risk" in risk_flags:
            story.append(Spacer(1, 10))
            tbml_warning = Paragraph(
                "<b>⚠️ TBML ALERT:</b> This price variance exceeds 50% and may indicate "
                "Trade-Based Money Laundering (TBML). Enhanced due diligence is recommended.",
                ParagraphStyle(
                    name='TBMLWarning',
                    parent=styles['Normal'],
                    fontSize=10,
                    textColor=colors.HexColor('#ef4444'),
                    backColor=colors.HexColor('#fee2e2'),
                    borderPadding=10,
                )
            )
            story.append(tbml_warning)
        
        story.append(Spacer(1, 20))
        
        # Market Data Source (if included)
        if include_market_details:
            story.append(Paragraph("Market Data Source", styles['SectionHeader']))
            
            source_data = [
                ["Data Source:", market_price.get("source", "N/A")],
                ["Price Range:", f"${market_price.get('price_low', 0):,.2f} - ${market_price.get('price_high', 0):,.2f}"],
                ["Fetched At:", market_price.get("fetched_at", "N/A")],
            ]
            
            source_table = Table(source_data, colWidths=[120, 380])
            source_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.gray),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(source_table)
        
        story.append(Spacer(1, 30))
        
        # Footer / Disclaimer
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e5e7eb')))
        story.append(Spacer(1, 10))
        
        disclaimer = Paragraph(
            "<font size=8 color='gray'>"
            "This report is generated by TRDR Price Verify for compliance documentation purposes. "
            "Market prices are indicative and sourced from World Bank, FRED, and other public data. "
            "This report does not constitute financial advice. Please verify with official sources "
            "for critical decisions."
            "</font>",
            styles['Normal']
        )
        story.append(disclaimer)
        
        # Build PDF
        doc.build(story)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Generated PDF report: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"PDF generation error: {e}", exc_info=True)
        return None


def generate_batch_verification_pdf(
    batch_result: Dict[str, Any],
    company_name: Optional[str] = None,
) -> Optional[bytes]:
    """
    Generate a PDF compliance report for batch price verifications.
    
    Args:
        batch_result: The batch verification result dict
        company_name: Optional company name for the header
        
    Returns:
        PDF bytes or None if generation fails
    """
    if not REPORTLAB_AVAILABLE:
        logger.error("ReportLab not available for PDF generation")
        return None
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=25*mm,
            bottomMargin=20*mm,
        )
        
        styles = getSampleStyleSheet()
        
        # Custom styles (same as single verification)
        styles.add(ParagraphStyle(
            name='TRDRTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=12,
            textColor=colors.HexColor('#1a1a2e'),
        ))
        styles.add(ParagraphStyle(
            name='TRDRSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.gray,
            spaceAfter=20,
        ))
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor('#16213e'),
        ))
        
        story = []
        
        # Header
        story.append(Paragraph("TRDR Price Verify", styles['TRDRTitle']))
        story.append(Paragraph("Batch Verification Compliance Report", styles['TRDRSubtitle']))
        
        # Summary
        story.append(Paragraph("Summary", styles['SectionHeader']))
        
        summary = batch_result.get("summary", {})
        
        summary_data = [
            ["Total Items:", str(summary.get("total_items", 0))],
            ["Passed:", str(summary.get("passed", 0))],
            ["Warnings:", str(summary.get("warnings", 0))],
            ["Failed:", str(summary.get("failed", 0))],
            ["Overall Variance:", f"{summary.get('overall_variance_percent', 0):+.2f}%"],
            ["TBML Flags:", str(summary.get("tbml_flags", 0))],
        ]
        
        summary_table = Table(summary_data, colWidths=[150, 350])
        summary_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Results table
        story.append(Paragraph("Item Results", styles['SectionHeader']))
        
        results = batch_result.get("results", [])
        
        if results:
            table_data = [["#", "Commodity", "Doc Price", "Market", "Variance", "Verdict"]]
            
            for i, item in enumerate(results, 1):
                commodity = item.get("commodity", {})
                doc_price = item.get("document_price", {})
                market = item.get("market_price", {})
                variance = item.get("variance", {})
                
                verdict = item.get("verdict", "N/A").upper()
                verdict_color = {
                    "PASS": "#22c55e",
                    "WARNING": "#eab308",
                    "FAIL": "#ef4444",
                }.get(verdict, "#666666")
                
                table_data.append([
                    str(i),
                    commodity.get("name", "N/A")[:25],
                    f"${doc_price.get('normalized_price', 0):,.2f}",
                    f"${market.get('price', 0):,.2f}",
                    f"{variance.get('percent', 0):+.1f}%",
                    Paragraph(f"<font color='{verdict_color}'><b>{verdict}</b></font>", styles['Normal']),
                ])
            
            results_table = Table(table_data, colWidths=[30, 130, 80, 80, 70, 70])
            results_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(results_table)
        
        story.append(Spacer(1, 30))
        
        # Footer
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e5e7eb')))
        story.append(Spacer(1, 10))
        
        disclaimer = Paragraph(
            f"<font size=8 color='gray'>"
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | "
            f"TRDR Price Verify Compliance Report"
            f"</font>",
            styles['Normal']
        )
        story.append(disclaimer)
        
        # Build PDF
        doc.build(story)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Generated batch PDF report: {len(pdf_bytes)} bytes, {len(results)} items")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Batch PDF generation error: {e}", exc_info=True)
        return None


def generate_sar_str_report(
    verification_id: str,
    verification_data: Dict[str, Any],
    company_info: Optional[Dict[str, Any]] = None,
    reporter_info: Optional[Dict[str, Any]] = None,
    report_type: str = "SAR",  # SAR or STR
) -> Optional[bytes]:
    """
    Generate a Suspicious Activity Report (SAR) or Suspicious Transaction Report (STR)
    for TBML (Trade-Based Money Laundering) flagged verifications.
    
    This follows standard SAR/STR format for compliance reporting.
    
    Args:
        verification_id: Unique verification reference
        verification_data: The verification result with TBML flags
        company_info: Reporting entity information
        reporter_info: Person completing the report
        report_type: "SAR" or "STR"
        
    Returns:
        PDF bytes or None if generation fails
    """
    if not REPORTLAB_AVAILABLE:
        logger.error("ReportLab not available for PDF generation")
        return None
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=25*mm,
            bottomMargin=20*mm,
        )
        
        styles = getSampleStyleSheet()
        
        # Custom styles for SAR/STR
        styles.add(ParagraphStyle(
            name='SARTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            textColor=colors.HexColor('#dc2626'),  # Red for urgency
            alignment=TA_CENTER,
        ))
        styles.add(ParagraphStyle(
            name='SARSection',
            parent=styles['Heading2'],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#1a1a2e'),
            backColor=colors.HexColor('#f3f4f6'),
            borderPadding=5,
        ))
        styles.add(ParagraphStyle(
            name='SARField',
            parent=styles['Normal'],
            fontSize=10,
            spaceBefore=3,
            spaceAfter=3,
        ))
        styles.add(ParagraphStyle(
            name='SARWarning',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#dc2626'),
            backColor=colors.HexColor('#fef2f2'),
            borderPadding=10,
        ))
        
        story = []
        
        # Header with warning
        report_title = "SUSPICIOUS ACTIVITY REPORT (SAR)" if report_type == "SAR" else "SUSPICIOUS TRANSACTION REPORT (STR)"
        story.append(Paragraph(f"<b>⚠️ {report_title}</b>", styles['SARTitle']))
        story.append(Paragraph(
            f"<font size=10 color='gray'>Reference: {verification_id} | "
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</font>",
            ParagraphStyle('Centered', parent=styles['Normal'], alignment=TA_CENTER)
        ))
        story.append(Spacer(1, 15))
        
        # Warning banner
        story.append(Paragraph(
            "<b>CONFIDENTIAL - FOR COMPLIANCE USE ONLY</b><br/>"
            "This report documents a potential Trade-Based Money Laundering (TBML) indicator. "
            "Handle in accordance with your institution's AML/CFT policies.",
            styles['SARWarning']
        ))
        story.append(Spacer(1, 20))
        
        # Section 1: Transaction Details
        story.append(Paragraph("1. TRANSACTION DETAILS", styles['SARSection']))
        
        commodity = verification_data.get("commodity", {})
        market = verification_data.get("market_price", {})
        variance = verification_data.get("variance", {})
        risk = verification_data.get("risk", {})
        
        transaction_data = [
            ["Field", "Value"],
            ["Commodity", commodity.get("name", "N/A")],
            ["Commodity Code", commodity.get("code", "N/A")],
            ["Document Price", f"${variance.get('document_price', 0):,.2f} / {commodity.get('unit', 'unit')}"],
            ["Market Price", f"${market.get('price', 0):,.2f} / {commodity.get('unit', 'unit')}"],
            ["Variance", f"{variance.get('percent', 0):.1f}%"],
            ["Risk Level", risk.get("risk_level", "N/A").upper()],
            ["Verdict", verification_data.get("verdict", "N/A").upper()],
            ["Market Source", market.get("source_display", market.get("source", "N/A"))],
        ]
        
        trans_table = Table(transaction_data, colWidths=[150, 300])
        trans_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f3f4f6')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(trans_table)
        story.append(Spacer(1, 15))
        
        # Section 2: Risk Indicators
        story.append(Paragraph("2. RISK INDICATORS (TBML RED FLAGS)", styles['SARSection']))
        
        risk_flags = risk.get("risk_flags", [])
        if risk_flags:
            for flag in risk_flags:
                # Map technical flags to human-readable descriptions
                flag_descriptions = {
                    "over_invoicing": "Over-invoicing: Document price significantly exceeds market value",
                    "under_invoicing": "Under-invoicing: Document price significantly below market value",
                    "tbml_risk": "TBML Risk: Variance exceeds acceptable threshold (>50%)",
                    "unusual_quantity": "Unusual Quantity: Transaction quantity is abnormal for this commodity",
                    "high_variance": "High Variance: Price deviation requires investigation",
                    "critical_variance": "Critical Variance: Extreme price manipulation suspected",
                }
                desc = flag_descriptions.get(flag, flag.replace("_", " ").title())
                story.append(Paragraph(f"• <font color='red'><b>{desc}</b></font>", styles['SARField']))
        else:
            story.append(Paragraph("No specific risk flags identified.", styles['SARField']))
        
        story.append(Spacer(1, 15))
        
        # Section 3: AI Analysis
        if verification_data.get("ai_explanation"):
            story.append(Paragraph("3. AI ANALYSIS", styles['SARSection']))
            story.append(Paragraph(verification_data["ai_explanation"], styles['SARField']))
            story.append(Spacer(1, 15))
        
        # Section 4: Document Context
        story.append(Paragraph("4. DOCUMENT CONTEXT" if not verification_data.get("ai_explanation") else "4. DOCUMENT CONTEXT", styles['SARSection']))
        
        doc_type = verification_data.get("document_type", "Not specified")
        doc_ref = verification_data.get("document_reference", "Not specified")
        origin = verification_data.get("origin_country", "N/A")
        dest = verification_data.get("destination_country", "N/A")
        
        context_data = [
            ["Document Type", doc_type],
            ["Document Reference", doc_ref],
            ["Origin Country", origin],
            ["Destination Country", dest],
        ]
        
        context_table = Table(context_data, colWidths=[150, 300])
        context_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(context_table)
        story.append(Spacer(1, 15))
        
        # Section 5: Reporting Entity
        story.append(Paragraph("5. REPORTING ENTITY", styles['SARSection']))
        
        company_name = company_info.get("name", "Not specified") if company_info else "Not specified"
        company_id = company_info.get("id", "N/A") if company_info else "N/A"
        reporter_name = reporter_info.get("name", "System") if reporter_info else "System"
        reporter_email = reporter_info.get("email", "N/A") if reporter_info else "N/A"
        
        entity_data = [
            ["Company Name", company_name],
            ["Company ID", company_id],
            ["Report Prepared By", reporter_name],
            ["Contact Email", reporter_email],
            ["Report Date", datetime.utcnow().strftime('%Y-%m-%d')],
        ]
        
        entity_table = Table(entity_data, colWidths=[150, 300])
        entity_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(entity_table)
        story.append(Spacer(1, 20))
        
        # Section 6: Recommended Actions
        story.append(Paragraph("6. RECOMMENDED ACTIONS", styles['SARSection']))
        
        actions = [
            "Review transaction documentation and supporting evidence",
            "Verify counterparty details and beneficial ownership",
            "Assess transaction against historical patterns",
            "Escalate to Compliance Officer if suspicion confirmed",
            "File regulatory report if required (FinCEN SAR / Local FIU)",
            "Retain all documentation per retention policy",
        ]
        
        for i, action in enumerate(actions, 1):
            story.append(Paragraph(f"{i}. {action}", styles['SARField']))
        
        story.append(Spacer(1, 30))
        
        # Footer with disclaimer
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#dc2626')))
        story.append(Spacer(1, 10))
        
        disclaimer = Paragraph(
            f"<font size=8 color='gray'>"
            f"This report is generated for internal compliance review purposes. "
            f"The automated analysis should be verified by qualified compliance personnel before any regulatory filing. "
            f"TRDR Price Verify | {report_type} Report | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
            f"</font>",
            ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER)
        )
        story.append(disclaimer)
        
        # Build PDF
        doc.build(story)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Generated {report_type} report for verification {verification_id}: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"SAR/STR generation error: {e}", exc_info=True)
        return None


def generate_tbml_compliance_report(
    verifications: List[Dict[str, Any]],
    company_info: Optional[Dict[str, Any]] = None,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
) -> Optional[bytes]:
    """
    Generate a TBML Compliance Summary Report for all flagged transactions in a period.
    
    This is a periodic summary report for compliance officers.
    
    Args:
        verifications: List of TBML-flagged verification results
        company_info: Reporting entity information
        period_start: Report period start date
        period_end: Report period end date
        
    Returns:
        PDF bytes or None if generation fails
    """
    if not REPORTLAB_AVAILABLE:
        logger.error("ReportLab not available for PDF generation")
        return None
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=25*mm,
            bottomMargin=20*mm,
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        story.append(Paragraph(
            "<b>TBML COMPLIANCE SUMMARY REPORT</b>",
            ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER)
        ))
        
        period_str = ""
        if period_start and period_end:
            period_str = f"{period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')}"
        else:
            period_str = f"As of {datetime.utcnow().strftime('%Y-%m-%d')}"
            
        story.append(Paragraph(
            f"<font size=10 color='gray'>Period: {period_str}</font>",
            ParagraphStyle('Period', parent=styles['Normal'], alignment=TA_CENTER)
        ))
        story.append(Spacer(1, 20))
        
        # Summary Statistics
        story.append(Paragraph("<b>SUMMARY STATISTICS</b>", styles['Heading2']))
        
        total_flagged = len(verifications)
        critical_count = sum(1 for v in verifications if v.get("risk", {}).get("risk_level") == "critical")
        high_count = sum(1 for v in verifications if v.get("risk", {}).get("risk_level") == "high")
        
        summary_data = [
            ["Metric", "Count"],
            ["Total TBML Flagged Transactions", str(total_flagged)],
            ["Critical Risk Level", str(critical_count)],
            ["High Risk Level", str(high_count)],
        ]
        
        summary_table = Table(summary_data, colWidths=[250, 100])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Flagged Transactions List
        if verifications:
            story.append(Paragraph("<b>FLAGGED TRANSACTIONS</b>", styles['Heading2']))
            
            table_data = [["#", "Commodity", "Doc Price", "Market", "Variance", "Risk"]]
            
            for i, v in enumerate(verifications[:50], 1):  # Limit to 50
                commodity = v.get("commodity", {})
                variance_data = v.get("variance", {})
                risk = v.get("risk", {})
                
                table_data.append([
                    str(i),
                    commodity.get("name", "N/A")[:20],
                    f"${variance_data.get('document_price', 0):,.2f}",
                    f"${v.get('market_price', {}).get('price', 0):,.2f}",
                    f"{variance_data.get('percent', 0):.1f}%",
                    risk.get("risk_level", "N/A").upper(),
                ])
            
            txn_table = Table(table_data, colWidths=[30, 120, 80, 80, 70, 60])
            txn_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (2, 1), (4, -1), 'RIGHT'),
                ('ALIGN', (5, 1), (5, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(txn_table)
        
        story.append(Spacer(1, 30))
        
        # Footer
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e5e7eb')))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph(
            f"<font size=8 color='gray'>"
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | "
            f"TRDR Price Verify TBML Compliance Report"
            f"</font>",
            ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER)
        ))
        
        doc.build(story)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Generated TBML compliance report: {len(pdf_bytes)} bytes, {len(verifications)} items")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"TBML compliance report generation error: {e}", exc_info=True)
        return None

