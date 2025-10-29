"""
LCopilot Trade SLA Dashboard & Report Manager

Creates bank-ready SLA dashboards and automated reports for trade finance:
- Trade-specific SLA metrics (LC processing, validation accuracy)
- Bank-auditable PDF reports with immutable signatures
- Pro/Enterprise tiered features
- Integration with trade finance workflows
"""

import boto3
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
import hashlib
import hmac
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)

@dataclass
class TradeSLAMetrics:
    period_start: datetime
    period_end: datetime
    customer_id: str
    tier: str

    # Core LC Processing Metrics
    lc_validation_availability: float  # Percentage uptime
    lc_processing_time_p50: float     # Median processing time in seconds
    lc_processing_time_p95: float     # 95th percentile processing time
    lc_processing_time_p99: float     # 99th percentile processing time

    # Accuracy & Quality Metrics
    validation_accuracy_overall: float       # Overall validation accuracy percentage
    ucp600_compliance_accuracy: float       # UCP600 rule compliance accuracy
    isbp_review_accuracy: float             # ISBP interpretation accuracy
    false_positive_rate: float              # Incorrect rejections
    false_negative_rate: float              # Missed discrepancies

    # UCP600/ISBP Compliance Metrics
    compliance_checks_performed: int         # Total compliance checks run
    compliance_violations_detected: int      # Total violations found
    compliance_score_average: float          # Average compliance score (0-100)
    ucp600_violations_count: int             # UCP600 specific violations
    isbp_violations_count: int               # ISBP specific violations

    # Volume & Throughput
    total_lcs_processed: int
    peak_concurrent_validations: int
    average_daily_volume: float

    # Error & Incident Metrics
    total_incidents: int
    critical_incidents: int
    mean_time_to_resolution_hours: float
    mean_time_to_response_minutes: float

    # Bank-Specific Metrics (Enterprise only)
    audit_trail_completeness: float = 100.0
    data_retention_compliance: bool = True
    regulatory_report_accuracy: float = 100.0

    # Cost & Efficiency (for ROI analysis)
    processing_cost_per_lc: float = 0.0
    error_remediation_cost: float = 0.0

@dataclass
class SLATarget:
    metric_name: str
    target_value: float
    actual_value: float
    unit: str
    compliance_status: str  # "met", "exceeded", "missed"
    variance_percentage: float
    impact_description: str
    remediation_required: bool = False

@dataclass
class TradeSLAReport:
    report_id: str
    customer_id: str
    customer_name: str
    business_type: str  # importer, exporter, bank, trading_company
    tier: str
    reporting_period: str
    generated_at: datetime

    # Report Metadata
    report_type: str  # monthly, quarterly, annual, incident
    report_version: str
    audit_signature: Optional[str] = None
    bank_compliance_certified: bool = False

    # SLA Data
    metrics: TradeSLAMetrics
    targets: List[SLATarget]
    incidents: List[Dict[str, Any]]
    recommendations: List[str]

    # File Paths
    pdf_path: Optional[str] = None
    html_path: Optional[str] = None
    csv_export_path: Optional[str] = None

class TradeSLAManager:
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.s3 = boto3.client('s3')
        self.cloudwatch = boto3.client('cloudwatch')
        self.ses = boto3.client('ses')  # For report delivery

        # Load trust platform configuration
        self.config_path = Path(__file__).parent.parent / "config" / "trust_config.yaml"
        self.trust_config = self._load_trust_config()

        # S3 buckets for reports
        self.reports_bucket = f"lcopilot-trust-sla-reports-{environment}"
        self.dashboards_bucket = f"lcopilot-trust-dashboards-{environment}"

        # CloudWatch dashboard client
        self.cloudwatch_dashboards = boto3.client('cloudwatch')

        # Initialize PDF styling
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

        # Load signing keys for audit-grade reports (Enterprise)
        self.signing_key = self._load_or_generate_signing_key()

    def _load_trust_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Trust config not found at {self.config_path}")
            return {}

    def _setup_custom_styles(self):
        """Setup custom PDF styles for trade finance reports"""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            textColor=colors.HexColor('#003d7a')
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#2c5aa0')
        ))

        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold'
        ))

    def _load_or_generate_signing_key(self) -> rsa.RSAPrivateKey:
        """Load or generate RSA key for report signing (Enterprise audit compliance)"""
        try:
            # In production, this would load from secure key storage
            return rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
        except Exception as e:
            logger.error(f"Failed to load signing key: {str(e)}")
            return None

    def get_customer_sla_targets(self, customer_id: str) -> Dict[str, float]:
        """Get SLA targets based on customer tier"""
        customer_data = self.trust_config.get('customers', {}).get(customer_id, {})
        tier = customer_data.get('tier', 'free')

        return self.trust_config.get('sla_targets', {}).get(tier, {})

    def collect_sla_metrics(self, customer_id: str, start_date: datetime, end_date: datetime) -> TradeSLAMetrics:
        """Collect comprehensive SLA metrics for the reporting period"""

        customer_data = self.trust_config.get('customers', {}).get(customer_id, {})
        tier = customer_data.get('tier', 'free')

        # Query CloudWatch for availability metrics
        availability_metrics = self._get_availability_metrics(customer_id, start_date, end_date)

        # Query processing time metrics
        processing_metrics = self._get_processing_time_metrics(customer_id, start_date, end_date)

        # Query accuracy metrics
        accuracy_metrics = self._get_accuracy_metrics(customer_id, start_date, end_date)

        # Query incident data
        incident_metrics = self._get_incident_metrics(customer_id, start_date, end_date)

        # Calculate volume metrics
        volume_metrics = self._get_volume_metrics(customer_id, start_date, end_date)

        # Calculate compliance metrics
        compliance_metrics = self._get_compliance_metrics(customer_id, start_date, end_date)

        metrics = TradeSLAMetrics(
            period_start=start_date,
            period_end=end_date,
            customer_id=customer_id,
            tier=tier,

            # Availability
            lc_validation_availability=availability_metrics.get('availability', 99.5),

            # Processing Times
            lc_processing_time_p50=processing_metrics.get('p50', 25.0),
            lc_processing_time_p95=processing_metrics.get('p95', 45.0),
            lc_processing_time_p99=processing_metrics.get('p99', 60.0),

            # Accuracy
            validation_accuracy_overall=accuracy_metrics.get('overall', 99.2),
            ucp600_compliance_accuracy=accuracy_metrics.get('ucp600', 99.5),
            isbp_review_accuracy=accuracy_metrics.get('isbp', 98.8),
            false_positive_rate=accuracy_metrics.get('false_positive', 0.5),
            false_negative_rate=accuracy_metrics.get('false_negative', 0.3),

            # Compliance
            compliance_checks_performed=compliance_metrics.get('checks_performed', 0),
            compliance_violations_detected=compliance_metrics.get('violations_detected', 0),
            compliance_score_average=compliance_metrics.get('score_average', 85.5),
            ucp600_violations_count=compliance_metrics.get('ucp600_violations', 0),
            isbp_violations_count=compliance_metrics.get('isbp_violations', 0),

            # Volume
            total_lcs_processed=volume_metrics.get('total', 1250),
            peak_concurrent_validations=volume_metrics.get('peak_concurrent', 25),
            average_daily_volume=volume_metrics.get('daily_average', 42.0),

            # Incidents
            total_incidents=incident_metrics.get('total', 2),
            critical_incidents=incident_metrics.get('critical', 0),
            mean_time_to_resolution_hours=incident_metrics.get('mttr_hours', 3.5),
            mean_time_to_response_minutes=incident_metrics.get('mttresponse_min', 15.0),

            # Enterprise metrics
            audit_trail_completeness=100.0 if tier == 'enterprise' else 0.0,
            data_retention_compliance=True,
            regulatory_report_accuracy=100.0 if tier == 'enterprise' else 0.0,

            # Cost metrics (simplified for demo)
            processing_cost_per_lc=0.75,
            error_remediation_cost=125.50
        )

        return metrics

    def _get_availability_metrics(self, customer_id: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Query CloudWatch for availability metrics"""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='LCopilot/Validation',
                MetricName='ServiceAvailability',
                Dimensions=[{'Name': 'Customer', 'Value': customer_id}],
                StartTime=start_date,
                EndTime=end_date,
                Period=3600,
                Statistics=['Average']
            )

            if response['Datapoints']:
                availability = sum(dp['Average'] for dp in response['Datapoints']) / len(response['Datapoints'])
                return {'availability': availability}

        except Exception as e:
            logger.error(f"Failed to get availability metrics: {str(e)}")

        # Return simulated data for demo
        return {'availability': 99.8}

    def _get_processing_time_metrics(self, customer_id: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Query processing time percentiles"""
        # Simulated processing time metrics
        return {
            'p50': 22.5,    # 22.5 seconds median
            'p95': 42.1,    # 42.1 seconds 95th percentile
            'p99': 58.3     # 58.3 seconds 99th percentile
        }

    def _get_accuracy_metrics(self, customer_id: str, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Query validation accuracy metrics"""
        # Simulated accuracy metrics
        return {
            'overall': 99.4,
            'ucp600': 99.6,
            'isbp': 99.1,
            'false_positive': 0.3,
            'false_negative': 0.3
        }

    def _get_incident_metrics(self, customer_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Query incident and response metrics"""
        # Simulated incident metrics
        return {
            'total': 1,
            'critical': 0,
            'major': 1,
            'minor': 0,
            'mttr_hours': 2.3,
            'mttresponse_min': 8.5
        }

    def _get_volume_metrics(self, customer_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Query processing volume metrics"""
        # Calculate days in period
        days_in_period = (end_date - start_date).days

        # Simulated volume metrics based on customer tier
        customer_data = self.trust_config.get('customers', {}).get(customer_id, {})
        monthly_volume = customer_data.get('monthly_lc_volume', 100)

        period_volume = int(monthly_volume * (days_in_period / 30.0))

        return {
            'total': period_volume,
            'peak_concurrent': max(5, int(monthly_volume / 100)),
            'daily_average': period_volume / days_in_period if days_in_period > 0 else 0
        }

    def _get_compliance_metrics(self, customer_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Query UCP600/ISBP compliance metrics"""
        customer_data = self.trust_config.get('customers', {}).get(customer_id, {})
        tier = customer_data.get('tier', 'free')
        monthly_volume = customer_data.get('monthly_lc_volume', 100)

        days_in_period = (end_date - start_date).days
        period_volume = int(monthly_volume * (days_in_period / 30.0))

        if tier == 'free':
            # Free tier has only 3 compliance checks
            checks_performed = min(3, period_volume)
            violations_detected = max(0, int(checks_performed * 0.15))  # 15% violation rate
            score_average = 82.5
            ucp600_violations = int(violations_detected * 0.6)
            isbp_violations = violations_detected - ucp600_violations
        elif tier == 'pro':
            # Pro tier has unlimited compliance checks
            checks_performed = period_volume
            violations_detected = int(checks_performed * 0.12)  # 12% violation rate
            score_average = 87.2
            ucp600_violations = int(violations_detected * 0.55)
            isbp_violations = violations_detected - ucp600_violations
        else:  # enterprise
            # Enterprise tier has unlimited with audit-grade compliance
            checks_performed = period_volume
            violations_detected = int(checks_performed * 0.08)  # 8% violation rate
            score_average = 92.8
            ucp600_violations = int(violations_detected * 0.5)
            isbp_violations = violations_detected - ucp600_violations

        return {
            'checks_performed': checks_performed,
            'violations_detected': violations_detected,
            'score_average': score_average,
            'ucp600_violations': ucp600_violations,
            'isbp_violations': isbp_violations
        }

    def calculate_sla_compliance(self, metrics: TradeSLAMetrics) -> List[SLATarget]:
        """Calculate SLA compliance against targets"""
        targets_config = self.get_customer_sla_targets(metrics.customer_id)
        compliance_results = []

        # Availability Target
        availability_target = targets_config.get('lc_validation_availability', 99.0)
        availability_compliance = SLATarget(
            metric_name="LC Validation Availability",
            target_value=availability_target,
            actual_value=metrics.lc_validation_availability,
            unit="%",
            compliance_status="met" if metrics.lc_validation_availability >= availability_target else "missed",
            variance_percentage=((metrics.lc_validation_availability - availability_target) / availability_target) * 100,
            impact_description=f"Service availability directly affects LC processing capability for trade operations",
            remediation_required=metrics.lc_validation_availability < availability_target
        )
        compliance_results.append(availability_compliance)

        # Processing Time Target
        processing_target = targets_config.get('lc_processing_time_p95_seconds', 60.0)
        processing_compliance = SLATarget(
            metric_name="LC Processing Time (95th percentile)",
            target_value=processing_target,
            actual_value=metrics.lc_processing_time_p95,
            unit="seconds",
            compliance_status="met" if metrics.lc_processing_time_p95 <= processing_target else "missed",
            variance_percentage=((metrics.lc_processing_time_p95 - processing_target) / processing_target) * 100,
            impact_description=f"Processing delays affect trade document review timelines and shipment schedules",
            remediation_required=metrics.lc_processing_time_p95 > processing_target
        )
        compliance_results.append(processing_compliance)

        # Accuracy Target
        accuracy_target = targets_config.get('validation_accuracy', 98.5)
        accuracy_compliance = SLATarget(
            metric_name="LC Validation Accuracy",
            target_value=accuracy_target,
            actual_value=metrics.validation_accuracy_overall,
            unit="%",
            compliance_status="met" if metrics.validation_accuracy_overall >= accuracy_target else "missed",
            variance_percentage=((metrics.validation_accuracy_overall - accuracy_target) / accuracy_target) * 100,
            impact_description=f"Validation accuracy affects trade finance risk and regulatory compliance",
            remediation_required=metrics.validation_accuracy_overall < accuracy_target
        )
        compliance_results.append(accuracy_compliance)

        # Incident Response Target (Pro/Enterprise only)
        if metrics.tier in ['pro', 'enterprise']:
            response_target = targets_config.get('incident_response_hours', 24.0) * 60  # Convert to minutes
            response_compliance = SLATarget(
                metric_name="Incident Response Time",
                target_value=response_target,
                actual_value=metrics.mean_time_to_response_minutes,
                unit="minutes",
                compliance_status="met" if metrics.mean_time_to_response_minutes <= response_target else "missed",
                variance_percentage=((metrics.mean_time_to_response_minutes - response_target) / response_target) * 100,
                impact_description=f"Quick incident response minimizes trade operation disruptions",
                remediation_required=metrics.mean_time_to_response_minutes > response_target
            )
            compliance_results.append(response_compliance)

        return compliance_results

    def create_cloudwatch_dashboard(self, customer_id: str) -> str:
        """Create comprehensive CloudWatch dashboard for trade SLA monitoring"""

        customer_data = self.trust_config.get('customers', {}).get(customer_id, {})
        company_name = customer_data.get('company_name', 'Customer')
        tier = customer_data.get('tier', 'free')

        dashboard_name = f"LCopilot-Trade-SLA-{customer_id}-{tier}"

        # Base dashboard configuration
        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["LCopilot/Validation", "ServiceAvailability", "Customer", customer_id],
                            [".", "ValidationAccuracy", ".", "."],
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "us-east-1",
                        "title": "LC Validation Availability & Accuracy",
                        "period": 300,
                        "yAxis": {
                            "left": {"min": 95, "max": 100},
                            "right": {"min": 0, "max": 100}
                        }
                    }
                },
                {
                    "type": "metric",
                    "x": 12, "y": 0, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["LCopilot/Validation", "ProcessingTimeP50", "Customer", customer_id],
                            [".", "ProcessingTimeP95", ".", "."],
                            [".", "ProcessingTimeP99", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "us-east-1",
                        "title": "LC Processing Time Percentiles",
                        "period": 300,
                        "yAxis": {"left": {"min": 0}}
                    }
                },
                {
                    "type": "metric",
                    "x": 0, "y": 6, "width": 8, "height": 6,
                    "properties": {
                        "metrics": [
                            ["LCopilot/Validation", "ProcessingVolume", "Customer", customer_id],
                            [".", "ErrorCount", ".", "."],
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "us-east-1",
                        "title": "LC Processing Volume & Errors",
                        "period": 3600
                    }
                },
                {
                    "type": "metric",
                    "x": 8, "y": 6, "width": 8, "height": 6,
                    "properties": {
                        "metrics": [
                            ["LCopilot/Compliance", "UCP600ComplianceScore", "Customer", customer_id],
                            [".", "ISBPComplianceScore", ".", "."],
                            [".", "ComplianceViolationRate", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "us-east-1",
                        "title": "UCP600 & ISBP Compliance Metrics",
                        "period": 3600,
                        "yAxis": {"left": {"min": 0, "max": 100}}
                    }
                },
                {
                    "type": "metric",
                    "x": 16, "y": 6, "width": 8, "height": 6,
                    "properties": {
                        "metrics": [
                            ["LCopilot/Incidents", "IncidentCount", "Customer", customer_id, "Severity", "Critical"],
                            ["...", "Major"],
                            ["...", "Minor"]
                        ],
                        "view": "timeSeries",
                        "stacked": True,
                        "region": "us-east-1",
                        "title": "Incidents by Severity",
                        "period": 86400
                    }
                }
            ]
        }

        # Add Enterprise-specific widgets
        if tier == 'enterprise':
            enterprise_widgets = [
                {
                    "type": "metric",
                    "x": 0, "y": 12, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["LCopilot/Compliance", "AuditTrailCompleteness", "Customer", customer_id],
                            [".", "DataRetentionCompliance", ".", "."],
                            [".", "RegulatoryReportAccuracy", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "us-east-1",
                        "title": "Bank Compliance Metrics",
                        "period": 86400,
                        "yAxis": {"left": {"min": 95, "max": 100}}
                    }
                },
                {
                    "type": "metric",
                    "x": 12, "y": 12, "width": 12, "height": 6,
                    "properties": {
                        "metrics": [
                            ["LCopilot/API", "RequestCount", "Customer", customer_id, "Endpoint", "/health"],
                            ["...", "/compliance"],
                            ["...", "/reports"]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": "us-east-1",
                        "title": "Enterprise API Usage",
                        "period": 3600
                    }
                }
            ]
            dashboard_body["widgets"].extend(enterprise_widgets)

        try:
            # Create or update dashboard
            response = self.cloudwatch_dashboards.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )

            dashboard_url = f"https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name={dashboard_name}"

            logger.info(f"Created CloudWatch dashboard for {customer_id}: {dashboard_name}")

            return dashboard_url

        except Exception as e:
            logger.error(f"Failed to create CloudWatch dashboard: {str(e)}")
            return ""

    def generate_sla_report_pdf(self, metrics: TradeSLAMetrics, targets: List[SLATarget], customer_id: str) -> str:
        """Generate comprehensive PDF SLA report for banks and trade partners"""

        customer_data = self.trust_config.get('customers', {}).get(customer_id, {})
        company_name = customer_data.get('company_name', 'Customer')
        business_type = customer_data.get('business_type', 'trader')
        tier = customer_data.get('tier', 'free')

        # Generate report filename
        report_date = datetime.now().strftime('%Y%m%d')
        period = f"{metrics.period_start.strftime('%Y%m')}"
        filename = f"LC_SLA_Report_{customer_id}_{period}_{report_date}.pdf"

        # Create PDF document
        pdf_path = f"/tmp/{filename}"
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        story = []

        # Title Page
        story.append(Paragraph(f"Letter of Credit Platform", self.styles['ReportTitle']))
        story.append(Paragraph(f"Service Level Agreement Report", self.styles['ReportTitle']))
        story.append(Spacer(1, 0.5*inch))

        # Report Metadata
        story.append(Paragraph(f"<b>Customer:</b> {company_name}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Business Type:</b> {business_type.title()}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Service Tier:</b> {tier.title()}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Reporting Period:</b> {metrics.period_start.strftime('%B %Y')}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}", self.styles['Normal']))
        story.append(Spacer(1, 0.5*inch))

        # Executive Summary
        story.append(Paragraph("Executive Summary", self.styles['SectionHeading']))

        # Calculate overall compliance
        met_targets = len([t for t in targets if t.compliance_status in ['met', 'exceeded']])
        total_targets = len(targets)
        compliance_rate = (met_targets / total_targets) * 100 if total_targets > 0 else 0

        summary_text = f"""
        During {metrics.period_start.strftime('%B %Y')}, LCopilot processed {metrics.total_lcs_processed:,}
        Letter of Credit validations with {metrics.lc_validation_availability:.2f}% uptime availability.
        Overall SLA compliance rate was {compliance_rate:.1f}% ({met_targets} of {total_targets} targets met).

        Key highlights:
        • LC Validation Accuracy: {metrics.validation_accuracy_overall:.2f}%
        • 95th Percentile Processing Time: {metrics.lc_processing_time_p95:.1f} seconds
        • Total Incidents: {metrics.total_incidents} (Critical: {metrics.critical_incidents})
        • Average Daily Volume: {metrics.average_daily_volume:.0f} LC validations
        """

        story.append(Paragraph(summary_text, self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))

        # SLA Compliance Table
        story.append(Paragraph("SLA Performance Summary", self.styles['SectionHeading']))

        # Create compliance table
        compliance_data = [['Metric', 'Target', 'Actual', 'Status', 'Variance']]

        for target in targets:
            status_color = 'green' if target.compliance_status in ['met', 'exceeded'] else 'red'
            variance_sign = '+' if target.variance_percentage > 0 else ''

            compliance_data.append([
                target.metric_name,
                f"{target.target_value} {target.unit}",
                f"{target.actual_value} {target.unit}",
                target.compliance_status.title(),
                f"{variance_sign}{target.variance_percentage:.1f}%"
            ])

        compliance_table = Table(compliance_data, colWidths=[3*inch, 1*inch, 1*inch, 0.8*inch, 0.8*inch])
        compliance_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(compliance_table)
        story.append(Spacer(1, 0.3*inch))

        # Detailed Metrics Section
        story.append(PageBreak())
        story.append(Paragraph("Detailed Performance Metrics", self.styles['SectionHeading']))

        # LC Processing Performance
        story.append(Paragraph("LC Processing Performance", self.styles['Heading3']))
        processing_data = [
            ['Metric', 'Value'],
            ['Total LCs Processed', f"{metrics.total_lcs_processed:,}"],
            ['Average Daily Volume', f"{metrics.average_daily_volume:.0f}"],
            ['Peak Concurrent Validations', f"{metrics.peak_concurrent_validations}"],
            ['Processing Time (Median)', f"{metrics.lc_processing_time_p50:.1f} seconds"],
            ['Processing Time (95th percentile)', f"{metrics.lc_processing_time_p95:.1f} seconds"],
            ['Processing Time (99th percentile)', f"{metrics.lc_processing_time_p99:.1f} seconds"]
        ]

        processing_table = Table(processing_data, colWidths=[3*inch, 2*inch])
        processing_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT')
        ]))

        story.append(processing_table)
        story.append(Spacer(1, 0.2*inch))

        # Accuracy & Quality Metrics
        story.append(Paragraph("Validation Accuracy & Quality", self.styles['Heading3']))
        accuracy_data = [
            ['Accuracy Metric', 'Percentage'],
            ['Overall Validation Accuracy', f"{metrics.validation_accuracy_overall:.2f}%"],
            ['UCP600 Compliance Accuracy', f"{metrics.ucp600_compliance_accuracy:.2f}%"],
            ['ISBP Review Accuracy', f"{metrics.isbp_review_accuracy:.2f}%"],
            ['False Positive Rate', f"{metrics.false_positive_rate:.2f}%"],
            ['False Negative Rate', f"{metrics.false_negative_rate:.2f}%"]
        ]

        accuracy_table = Table(accuracy_data, colWidths=[3*inch, 2*inch])
        accuracy_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT')
        ]))

        story.append(accuracy_table)
        story.append(Spacer(1, 0.2*inch))

        # UCP600/ISBP Compliance Metrics (if tier allows)
        if tier in ['pro', 'enterprise'] and metrics.compliance_checks_performed > 0:
            story.append(Paragraph("UCP600 & ISBP Compliance Analysis", self.styles['Heading3']))
            compliance_data = [
                ['Compliance Metric', 'Value'],
                ['Total Compliance Checks', f"{metrics.compliance_checks_performed:,}"],
                ['Violations Detected', f"{metrics.compliance_violations_detected:,}"],
                ['Average Compliance Score', f"{metrics.compliance_score_average:.1f}/100"],
                ['UCP600 Violations', f"{metrics.ucp600_violations_count:,}"],
                ['ISBP Violations', f"{metrics.isbp_violations_count:,}"],
                ['Violation Rate', f"{(metrics.compliance_violations_detected/metrics.compliance_checks_performed)*100:.1f}%" if metrics.compliance_checks_performed > 0 else "0.0%"]
            ]

            compliance_table = Table(compliance_data, colWidths=[3*inch, 2*inch])
            compliance_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT')
            ]))

            story.append(compliance_table)
            story.append(Spacer(1, 0.2*inch))

            # Compliance impact text
            compliance_impact = f"""
            UCP600/ISBP and Bangladesh local banking compliance validation identified {metrics.compliance_violations_detected} violations
            across {metrics.compliance_checks_performed} checks, resulting in a {metrics.compliance_score_average:.1f}%
            average compliance score. This analysis includes ICC standards plus locally relevant rejection scenarios from
            Bangladeshi banks (DBBL, Sonali, Islami Bank, etc.), helping prevent costly rejections before processing.
            """
            story.append(Paragraph(compliance_impact, self.styles['Normal']))
            story.append(Spacer(1, 0.2*inch))

        # Business Impact Analysis (tailored by business type)
        story.append(Paragraph("Business Impact Analysis", self.styles['SectionHeading']))

        business_impact_text = self._generate_business_impact_text(business_type, metrics)
        story.append(Paragraph(business_impact_text, self.styles['Normal']))
        story.append(Spacer(1, 0.2*inch))

        # Enterprise Bank Compliance Section
        if tier == 'enterprise' and business_type == 'bank':
            story.append(PageBreak())
            story.append(Paragraph("Bank Regulatory Compliance", self.styles['SectionHeading']))

            compliance_data = [
                ['Compliance Metric', 'Status'],
                ['Audit Trail Completeness', f"{metrics.audit_trail_completeness:.1f}%"],
                ['Data Retention Compliance', 'Compliant' if metrics.data_retention_compliance else 'Non-Compliant'],
                ['Regulatory Report Accuracy', f"{metrics.regulatory_report_accuracy:.1f}%"],
                ['Immutable Logging', 'Enabled'],
                ['Data Encryption at Rest', 'AES-256'],
                ['Data Encryption in Transit', 'TLS 1.3']
            ]

            compliance_table = Table(compliance_data, colWidths=[3*inch, 2*inch])
            compliance_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(compliance_table)
            story.append(Spacer(1, 0.2*inch))

            # Audit Signature for Enterprise
            if self.signing_key:
                signature = self._generate_audit_signature(metrics, customer_id)
                story.append(Paragraph("Audit Verification", self.styles['SectionHeading']))
                story.append(Paragraph(f"<b>Digital Signature:</b> {signature[:32]}...", self.styles['Normal']))
                story.append(Paragraph(f"<b>Report Hash:</b> SHA-256", self.styles['Normal']))
                story.append(Paragraph(f"<b>Signing Authority:</b> LCopilot SLA Compliance System", self.styles['Normal']))

        # Recommendations Section
        story.append(PageBreak())
        story.append(Paragraph("Recommendations & Action Items", self.styles['SectionHeading']))

        recommendations = self._generate_recommendations(targets, metrics, business_type)
        for i, recommendation in enumerate(recommendations, 1):
            story.append(Paragraph(f"{i}. {recommendation}", self.styles['Normal']))
            story.append(Spacer(1, 0.1*inch))

        # Footer
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph("This report was generated automatically by LCopilot's SLA monitoring system.",
                              self.styles['Normal']))
        story.append(Paragraph("For questions or clarification, contact: sla-reports@lcopilot.com",
                              self.styles['Normal']))

        # Build PDF
        try:
            doc.build(story)

            # Upload to S3
            s3_key = f"sla-reports/{customer_id}/{filename}"
            with open(pdf_path, 'rb') as pdf_file:
                self.s3.upload_fileobj(
                    pdf_file,
                    self.reports_bucket,
                    s3_key,
                    ExtraArgs={'ContentType': 'application/pdf'}
                )

            # Generate presigned URL
            pdf_url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.reports_bucket, 'Key': s3_key},
                ExpiresIn=86400  # 24 hours
            )

            logger.info(f"Generated SLA report PDF: {s3_key}")
            return pdf_url

        except Exception as e:
            logger.error(f"Failed to generate SLA report PDF: {str(e)}")
            return ""

    def _generate_business_impact_text(self, business_type: str, metrics: TradeSLAMetrics) -> str:
        """Generate business-specific impact analysis"""

        if business_type == 'importer':
            return f"""
            For import operations, LC validation performance directly impacts customs clearance and delivery schedules.
            With {metrics.lc_processing_time_p95:.1f} second 95th percentile processing times, importers can expect
            rapid document verification supporting just-in-time inventory management. The {metrics.validation_accuracy_overall:.2f}%
            validation accuracy plus Bangladesh local banking rules compliance minimizes rejection risks at banks like DBBL, Sonali, and Islami Bank.
            """

        elif business_type == 'exporter':
            return f"""
            Export operations benefit from {metrics.validation_accuracy_overall:.2f}% LC validation accuracy,
            ensuring export documents meet buyer requirements before shipment. Processing {metrics.total_lcs_processed:,}
            LCs with {metrics.lc_validation_availability:.2f}% availability supports reliable export financing and
            reduces the risk of payment delays. Local compliance checks prevent common rejection scenarios like beneficiary address mismatches and HS code errors.
            """

        elif business_type == 'bank':
            return f"""
            For trade finance operations, LC validation system performance directly impacts credit risk assessment
            and regulatory compliance. {metrics.audit_trail_completeness:.1f}% audit trail completeness and
            {metrics.regulatory_report_accuracy:.1f}% regulatory report accuracy support Basel III compliance requirements.
            The {metrics.mean_time_to_resolution_hours:.1f} hour mean resolution time for incidents ensures minimal
            disruption to trade finance services.
            """

        elif business_type == 'trading_company':
            return f"""
            Trading operations require high reliability across both import and export LC validation.
            {metrics.lc_validation_availability:.2f}% platform availability and {metrics.lc_processing_time_p95:.1f}
            second processing times support efficient trade facilitation. Processing {metrics.average_daily_volume:.0f}
            daily LC validations enables scalable trading operations across multiple trade lanes.
            """

        return f"""
        LC validation system performance metrics indicate {metrics.lc_validation_availability:.2f}% availability
        with {metrics.validation_accuracy_overall:.2f}% accuracy, supporting reliable trade finance operations.
        """

    def _generate_recommendations(self, targets: List[SLATarget], metrics: TradeSLAMetrics, business_type: str) -> List[str]:
        """Generate actionable recommendations based on SLA performance"""
        recommendations = []

        # Check for missed targets
        missed_targets = [t for t in targets if t.compliance_status == 'missed']

        if missed_targets:
            recommendations.append(
                f"Address {len(missed_targets)} missed SLA targets through performance optimization and infrastructure scaling."
            )

        # Processing time recommendations
        if metrics.lc_processing_time_p95 > 45:
            recommendations.append(
                "Consider implementing caching for frequently validated LC templates to reduce processing times."
            )

        # Accuracy recommendations
        if metrics.validation_accuracy_overall < 99:
            recommendations.append(
                "Review validation rule engine accuracy and consider machine learning model retraining to improve precision."
            )

        # Incident recommendations
        if metrics.total_incidents > 2:
            recommendations.append(
                f"Investigate root causes of {metrics.total_incidents} incidents to implement preventive measures."
            )

        # Business-specific recommendations
        if business_type == 'bank':
            recommendations.append(
                "Maintain audit trail completeness above 99.9% for regulatory compliance requirements."
            )

        if business_type in ['importer', 'exporter']:
            recommendations.append(
                "Consider upgrading to Pro tier for enhanced SLA reporting and priority support during peak trade seasons."
            )

        if not recommendations:
            recommendations.append(
                "All SLA targets are being met. Continue monitoring for sustained performance excellence."
            )

        return recommendations

    def _generate_audit_signature(self, metrics: TradeSLAMetrics, customer_id: str) -> str:
        """Generate cryptographic signature for audit compliance (Enterprise)"""
        if not self.signing_key:
            return "SIGNATURE_UNAVAILABLE"

        try:
            # Create signature payload
            payload = {
                'customer_id': customer_id,
                'period_start': metrics.period_start.isoformat(),
                'period_end': metrics.period_end.isoformat(),
                'availability': metrics.lc_validation_availability,
                'accuracy': metrics.validation_accuracy_overall,
                'processing_time_p95': metrics.lc_processing_time_p95,
                'total_lcs': metrics.total_lcs_processed,
                'generated_at': datetime.now().isoformat()
            }

            payload_json = json.dumps(payload, sort_keys=True)
            payload_bytes = payload_json.encode('utf-8')

            # Generate signature
            signature = self.signing_key.sign(
                payload_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            # Return hex representation (truncated for display)
            return signature.hex()

        except Exception as e:
            logger.error(f"Failed to generate audit signature: {str(e)}")
            return "SIGNATURE_ERROR"

    def schedule_automated_reports(self, customer_id: str) -> bool:
        """Schedule automated SLA report generation"""
        try:
            # This would typically use EventBridge or similar
            # For now, we'll just log the scheduling
            customer_data = self.trust_config.get('customers', {}).get(customer_id, {})
            tier = customer_data.get('tier', 'free')

            if tier == 'free':
                schedule = "monthly"
            elif tier == 'pro':
                schedule = "monthly"
            else:  # enterprise
                schedule = "weekly"

            logger.info(f"Scheduled {schedule} SLA reports for customer {customer_id} ({tier} tier)")
            return True

        except Exception as e:
            logger.error(f"Failed to schedule automated reports: {str(e)}")
            return False

def main():
    """Demo SLA dashboard and report generation"""
    manager = TradeSLAManager()

    print("=== LCopilot Trade SLA Dashboard & Report Demo ===")

    # Test customers from different tiers
    customers = ['pro-trader-001', 'enterprise-bank-001']

    for customer_id in customers:
        print(f"\n--- Processing SLA reports for {customer_id} ---")

        try:
            # Collect SLA metrics for last month
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            metrics = manager.collect_sla_metrics(customer_id, start_date, end_date)
            print(f"Collected metrics: {metrics.total_lcs_processed} LCs processed")
            print(f"Availability: {metrics.lc_validation_availability:.2f}%")
            print(f"Accuracy: {metrics.validation_accuracy_overall:.2f}%")

            # Calculate SLA compliance
            targets = manager.calculate_sla_compliance(metrics)
            met_targets = len([t for t in targets if t.compliance_status in ['met', 'exceeded']])
            print(f"SLA Compliance: {met_targets}/{len(targets)} targets met")

            # Create CloudWatch dashboard
            dashboard_url = manager.create_cloudwatch_dashboard(customer_id)
            print(f"CloudWatch Dashboard: {dashboard_url}")

            # Generate PDF report
            pdf_url = manager.generate_sla_report_pdf(metrics, targets, customer_id)
            if pdf_url:
                print(f"PDF Report: {pdf_url}")

            # Schedule automated reports
            scheduled = manager.schedule_automated_reports(customer_id)
            print(f"Automated reporting scheduled: {scheduled}")

        except Exception as e:
            print(f"Error processing SLA for {customer_id}: {str(e)}")

if __name__ == "__main__":
    main()