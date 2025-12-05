"""
Compliance Report PDF Generator

Generates professional vessel due diligence reports for banks.
"""

import io
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    HRFlowable, Image, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app.services.vessel_sanctions import SanctionsResult, get_sanctions_service
from app.services.ais_gap_detection import AISAnalysisResult, get_ais_service

logger = logging.getLogger(__name__)


# Colors
TRDR_BLUE = colors.HexColor("#3b82f6")
TRDR_GREEN = colors.HexColor("#22c55e")
TRDR_RED = colors.HexColor("#ef4444")
TRDR_AMBER = colors.HexColor("#f59e0b")
TRDR_DARK = colors.HexColor("#1e293b")


def get_risk_color(level: str) -> colors.Color:
    """Get color for risk level."""
    if level in ["CLEAR", "LOW"]:
        return TRDR_GREEN
    elif level == "MEDIUM":
        return TRDR_AMBER
    elif level in ["HIGH", "CRITICAL"]:
        return TRDR_RED
    return colors.gray


class ComplianceReportGenerator:
    """
    Generates PDF compliance reports for vessels.
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=TRDR_DARK,
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.gray,
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=TRDR_BLUE,
            spaceBefore=20,
            spaceAfter=10,
            borderColor=TRDR_BLUE,
            borderWidth=1,
            borderPadding=5
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionContent',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='RiskClear',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=TRDR_GREEN,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='RiskHigh',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=TRDR_RED,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.gray,
            alignment=TA_CENTER
        ))
    
    def _create_header(self, report_id: str, vessel_name: str) -> list:
        """Create report header."""
        elements = []
        
        # Title
        elements.append(Paragraph("VESSEL DUE DILIGENCE REPORT", self.styles['ReportTitle']))
        elements.append(Paragraph(
            f"Report ID: {report_id}<br/>Generated: {datetime.utcnow().strftime('%B %d, %Y %H:%M UTC')}",
            self.styles['ReportSubtitle']
        ))
        
        # Vessel info box
        vessel_table = Table([
            ["Vessel Name:", vessel_name],
        ], colWidths=[2*inch, 4*inch])
        vessel_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ]))
        elements.append(vessel_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_executive_summary(
        self, 
        sanctions: Optional[SanctionsResult],
        ais: Optional[AISAnalysisResult]
    ) -> list:
        """Create executive summary section."""
        elements = []
        
        elements.append(Paragraph("EXECUTIVE SUMMARY", self.styles['SectionHeader']))
        
        # Determine overall risk
        sanctions_risk = sanctions.risk_level if sanctions else "N/A"
        ais_risk = ais.risk_level if ais else "N/A"
        
        # Calculate combined risk
        risk_scores = {"CLEAR": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4, "UNKNOWN": 2, "N/A": 2}
        max_risk = max(risk_scores.get(sanctions_risk, 2), risk_scores.get(ais_risk, 2))
        
        overall_risks = {0: "CLEAR", 1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}
        overall_risk = overall_risks[max_risk]
        
        # Summary table
        summary_data = [
            ["Assessment", "Result", "Details"],
            ["Sanctions Screening", sanctions_risk, sanctions.recommendation if sanctions else "Not screened"],
            ["AIS Transmission", ais_risk, ais.recommendation if ais else "Not analyzed"],
            ["OVERALL RISK", overall_risk, "Combined assessment of all factors"]
        ]
        
        summary_table = Table(summary_data, colWidths=[1.5*inch, 1*inch, 3.5*inch])
        
        # Style based on risk
        styles = [
            ('BACKGROUND', (0, 0), (-1, 0), TRDR_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        
        # Color risk cells
        for i, row in enumerate(summary_data[1:], start=1):
            risk = row[1]
            color = get_risk_color(risk)
            styles.append(('BACKGROUND', (1, i), (1, i), color))
            styles.append(('TEXTCOLOR', (1, i), (1, i), colors.white))
            styles.append(('FONTNAME', (1, i), (1, i), 'Helvetica-Bold'))
        
        summary_table.setStyle(TableStyle(styles))
        elements.append(summary_table)
        elements.append(Spacer(1, 15))
        
        # Recommendation box
        if overall_risk in ["CRITICAL", "HIGH"]:
            rec_color = TRDR_RED
            rec_text = "⚠ DO NOT PROCEED without enhanced due diligence and compliance review."
        elif overall_risk == "MEDIUM":
            rec_color = TRDR_AMBER
            rec_text = "⚡ PROCEED WITH CAUTION - Additional monitoring recommended."
        else:
            rec_color = TRDR_GREEN
            rec_text = "✓ CLEAR TO PROCEED - Normal risk profile."
        
        rec_table = Table([[rec_text]], colWidths=[6*inch])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fef3c7") if overall_risk == "MEDIUM" else 
             colors.HexColor("#fee2e2") if overall_risk in ["HIGH", "CRITICAL"] else 
             colors.HexColor("#dcfce7")),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('PADDING', (0, 0), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(rec_table)
        
        return elements
    
    def _create_sanctions_section(self, sanctions: SanctionsResult) -> list:
        """Create sanctions screening section."""
        elements = []
        
        elements.append(Paragraph("SANCTIONS SCREENING", self.styles['SectionHeader']))
        
        # List results
        lists_data = [
            ["Sanctions List", "Result", "Matches"],
            ["OFAC SDN (US Treasury)", "✓ CLEAR" if sanctions.ofac_clear else "⚠ FLAGGED", str(len(sanctions.ofac_hits))],
            ["EU Consolidated Sanctions", "✓ CLEAR" if sanctions.eu_clear else "⚠ FLAGGED", str(len(sanctions.eu_hits))],
            ["UN Security Council", "✓ CLEAR" if sanctions.un_clear else "⚠ FLAGGED", str(len(sanctions.un_hits))],
        ]
        
        lists_table = Table(lists_data, colWidths=[2.5*inch, 1.5*inch, 1*inch])
        styles = [
            ('BACKGROUND', (0, 0), (-1, 0), TRDR_DARK),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ]
        
        for i in range(1, len(lists_data)):
            if "CLEAR" in lists_data[i][1]:
                styles.append(('TEXTCOLOR', (1, i), (1, i), TRDR_GREEN))
            else:
                styles.append(('TEXTCOLOR', (1, i), (1, i), TRDR_RED))
        
        lists_table.setStyle(TableStyle(styles))
        elements.append(lists_table)
        elements.append(Spacer(1, 15))
        
        # Flag assessment
        if sanctions.flag_assessment:
            fa = sanctions.flag_assessment
            elements.append(Paragraph("Flag State Assessment", self.styles['Heading3']))
            
            flag_data = [
                ["Flag State:", f"{fa.flag_state} ({fa.flag_code})"],
                ["Risk Level:", fa.risk_level],
                ["Paris MoU Status:", fa.paris_mou_status.upper()],
                ["Flag of Convenience:", "Yes" if fa.is_flag_of_convenience else "No"],
                ["Notes:", fa.notes],
            ]
            
            flag_table = Table(flag_data, colWidths=[1.5*inch, 4.5*inch])
            flag_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(flag_table)
        
        return elements
    
    def _create_ais_section(self, ais: AISAnalysisResult) -> list:
        """Create AIS analysis section."""
        elements = []
        
        elements.append(Paragraph("AIS TRANSMISSION ANALYSIS", self.styles['SectionHeader']))
        
        # Summary stats
        stats_data = [
            ["Analysis Period:", f"{ais.analysis_period_days} days"],
            ["Total Positions:", str(ais.total_positions)],
            ["Total Gaps Detected:", str(ais.total_gaps)],
            ["Suspicious Gaps (>24h):", str(ais.suspicious_gaps)],
            ["Longest Gap:", f"{ais.longest_gap_hours} hours"],
            ["Risk Score:", f"{ais.overall_risk_score}/100"],
        ]
        
        stats_table = Table(stats_data, colWidths=[2*inch, 4*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 15))
        
        # Gap details
        if ais.gaps:
            elements.append(Paragraph("Detected Gaps", self.styles['Heading3']))
            
            gap_data = [["#", "Start", "Duration", "Distance", "Risk Level"]]
            for i, gap in enumerate(ais.gaps[:5], 1):  # Show first 5 gaps
                gap_data.append([
                    str(i),
                    datetime.fromisoformat(gap.start_time.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M"),
                    f"{gap.duration_hours}h",
                    f"{gap.distance_nm} nm" if gap.distance_nm else "N/A",
                    gap.risk_level
                ])
            
            gap_table = Table(gap_data, colWidths=[0.5*inch, 1.5*inch, 1*inch, 1*inch, 1*inch])
            gap_styles = [
                ('BACKGROUND', (0, 0), (-1, 0), TRDR_DARK),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ]
            
            for i, gap in enumerate(ais.gaps[:5], 1):
                color = get_risk_color(gap.risk_level)
                gap_styles.append(('TEXTCOLOR', (-1, i), (-1, i), color))
                gap_styles.append(('FONTNAME', (-1, i), (-1, i), 'Helvetica-Bold'))
            
            gap_table.setStyle(TableStyle(gap_styles))
            elements.append(gap_table)
        
        # High risk areas
        if ais.high_risk_areas_visited:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("⚠ High-Risk Areas Visited", self.styles['Heading3']))
            for area in ais.high_risk_areas_visited:
                elements.append(Paragraph(f"• {area}", self.styles['SectionContent']))
        
        return elements
    
    def _create_footer(self, report_id: str) -> list:
        """Create report footer with disclaimer."""
        elements = []
        
        elements.append(Spacer(1, 30))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
        elements.append(Spacer(1, 10))
        
        disclaimer = """
        <b>DISCLAIMER:</b> This report is provided for informational purposes only and does not constitute 
        legal, compliance, or financial advice. TRDR Hub makes no representations or warranties regarding 
        the accuracy or completeness of the information contained herein. Users should conduct their own 
        due diligence and consult with appropriate compliance and legal professionals before making 
        any decisions. Sanctions data is sourced from official government databases and updated daily.
        """
        elements.append(Paragraph(disclaimer, self.styles['Footer']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(
            f"Report ID: {report_id} | Generated by TRDR Hub Container Tracker | www.trdrhub.com",
            self.styles['Footer']
        ))
        
        return elements
    
    async def generate_report(
        self,
        vessel_name: str,
        imo: Optional[str] = None,
        mmsi: Optional[str] = None,
        flag_state: Optional[str] = None,
        include_sanctions: bool = True,
        include_ais: bool = True
    ) -> bytes:
        """
        Generate a complete vessel due diligence report.
        
        Returns PDF as bytes.
        """
        report_id = f"VDD-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Get screening results
        sanctions = None
        ais = None
        
        if include_sanctions:
            try:
                service = get_sanctions_service()
                sanctions = await service.screen_vessel(
                    vessel_name=vessel_name,
                    imo=imo,
                    mmsi=mmsi,
                    flag_state=flag_state
                )
            except Exception as e:
                logger.error(f"Error getting sanctions data: {e}")
        
        if include_ais:
            try:
                service = get_ais_service()
                # Use demo data for now
                risk_profile = "low"
                if flag_state and flag_state[:2].upper() in ["IR", "KP", "SY", "CU"]:
                    risk_profile = "high"
                ais = service.generate_demo_analysis(
                    vessel_name=vessel_name,
                    imo=imo,
                    mmsi=mmsi,
                    risk_profile=risk_profile
                )
            except Exception as e:
                logger.error(f"Error getting AIS data: {e}")
        
        # Build PDF
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
        
        # Header
        elements.extend(self._create_header(report_id, vessel_name))
        
        # Executive Summary
        elements.extend(self._create_executive_summary(sanctions, ais))
        
        # Sanctions section
        if sanctions:
            elements.append(PageBreak())
            elements.extend(self._create_sanctions_section(sanctions))
        
        # AIS section
        if ais:
            elements.append(PageBreak())
            elements.extend(self._create_ais_section(ais))
        
        # Footer
        elements.extend(self._create_footer(report_id))
        
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Generated compliance report {report_id} for {vessel_name}")
        
        return pdf_bytes


# Singleton instance
_report_generator: Optional[ComplianceReportGenerator] = None


def get_report_generator() -> ComplianceReportGenerator:
    """Get or create report generator instance."""
    global _report_generator
    if _report_generator is None:
        _report_generator = ComplianceReportGenerator()
    return _report_generator

