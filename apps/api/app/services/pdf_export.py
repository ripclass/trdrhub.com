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

