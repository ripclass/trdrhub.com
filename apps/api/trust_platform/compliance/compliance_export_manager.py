"""
LCopilot Compliance Export Manager

Bank-auditable compliance exports with:
- Timestamped validation logs
- Immutable audit trails
- Multiple export formats (JSON/CSV/PDF)
- Tier-based retention (90d SMEs, 1y Pro, 7y Enterprise)
- Regulatory compliance features
"""

import boto3
import json
import logging
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import yaml
import pandas as pd
import csv
from io import StringIO, BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import base64

logger = logging.getLogger(__name__)

@dataclass
class ComplianceRecord:
    record_id: str
    timestamp: datetime
    customer_id: str
    lc_reference_number: str
    validation_request_id: str

    # LC Validation Details
    validation_result: str  # "pass", "fail", "warning"
    processing_time_ms: int
    accuracy_score: float

    # Compliance Checks
    ucp600_compliance: bool
    ucp600_violations: List[str]
    ucp600_score: float  # UCP600 compliance score (0-100)
    isbp_compliance: bool
    isbp_discrepancies: List[str]
    isbp_score: float  # ISBP compliance score (0-100)
    overall_compliance_score: float  # Combined compliance score (0-100)

    # Document Analysis
    documents_analyzed: List[str]
    discrepancy_flags: List[str]
    risk_assessment: str  # "low", "medium", "high"

    # System Information
    reviewer_id: str  # Human reviewer or "SYSTEM_AUTO"
    system_version: str
    validation_engine_version: str
    rule_set_version: str

    # Audit Trail
    request_source: str  # API, Portal, Batch, etc.
    client_ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None

    # Bank-Specific Fields
    correspondent_bank: Optional[str] = None
    issuing_bank: Optional[str] = None
    trade_finance_reference: Optional[str] = None
    regulatory_classification: Optional[str] = None

@dataclass
class ComplianceExportConfig:
    customer_id: str
    tier: str
    business_type: str

    # Retention & Access
    retention_days: int
    export_formats: List[str]  # ["json", "csv", "pdf"]
    encryption_required: bool
    immutable_storage: bool

    # Bank Compliance Features
    audit_trail_enabled: bool
    digital_signature_required: bool
    regulatory_reporting: bool

    # Export Controls
    max_records_per_export: int
    export_frequency_limit: str  # "daily", "weekly", "monthly"
    access_logging: bool

@dataclass
class ComplianceExportResult:
    export_id: str
    customer_id: str
    export_format: str
    record_count: int
    file_size_bytes: int

    # File Information
    s3_bucket: str
    s3_key: str
    presigned_url: str
    expiry_time: datetime

    # Integrity & Security
    file_hash_sha256: str
    digital_signature: Optional[str] = None
    encryption_status: str = "encrypted"

    # Metadata
    generated_at: datetime
    exported_by: str
    export_criteria: Dict[str, Any]

class ComplianceExportManager:
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.s3 = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')
        self.kms = boto3.client('kms')

        # Load trust configuration
        self.config_path = Path(__file__).parent.parent / "config" / "trust_config.yaml"
        self.trust_config = self._load_trust_config()

        # S3 buckets for compliance data
        self.compliance_bucket = f"lcopilot-compliance-exports-{environment}"
        self.audit_logs_bucket = f"lcopilot-audit-logs-{environment}"

        # DynamoDB table for compliance records
        self.compliance_table_name = f"lcopilot-compliance-records-{environment}"
        self.compliance_table = self.dynamodb.Table(self.compliance_table_name)

        # KMS key for encryption
        self.kms_key_id = f"alias/lcopilot-compliance-{environment}"

        # Load signing keys for audit compliance
        self.signing_key = self._load_or_generate_signing_key()

        # PDF styles
        self.styles = getSampleStyleSheet()

    def _load_trust_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Trust config not found at {self.config_path}")
            return {}

    def _load_or_generate_signing_key(self) -> rsa.RSAPrivateKey:
        """Load or generate RSA key for digital signatures"""
        try:
            # In production, load from secure key store
            return rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
        except Exception as e:
            logger.error(f"Failed to load signing key: {str(e)}")
            return None

    def get_compliance_config(self, customer_id: str) -> ComplianceExportConfig:
        """Get compliance export configuration based on customer tier"""
        customer_data = self.trust_config.get('customers', {}).get(customer_id, {})
        tier = customer_data.get('tier', 'free')
        business_type = customer_data.get('business_type', 'trader')

        # Tier-based retention policies
        retention_policies = {
            'free': 90,      # 90 days for SMEs
            'pro': 365,      # 1 year for active traders
            'enterprise': 2555  # 7 years for banks/large corps
        }

        # Tier-based features
        if tier == 'free':
            export_formats = []  # No compliance exports for free tier
            max_records = 0
            encryption = False
            audit_trail = False
            digital_sig = False
        elif tier == 'pro':
            export_formats = ["json", "csv"]
            max_records = 10000
            encryption = True
            audit_trail = True
            digital_sig = False
        else:  # enterprise
            export_formats = ["json", "csv", "pdf"]
            max_records = -1  # unlimited
            encryption = True
            audit_trail = True
            digital_sig = True

        config = ComplianceExportConfig(
            customer_id=customer_id,
            tier=tier,
            business_type=business_type,
            retention_days=retention_policies[tier],
            export_formats=export_formats,
            encryption_required=encryption,
            immutable_storage=tier == 'enterprise',
            audit_trail_enabled=audit_trail,
            digital_signature_required=digital_sig,
            regulatory_reporting=tier == 'enterprise' and business_type == 'bank',
            max_records_per_export=max_records,
            export_frequency_limit='daily' if tier == 'pro' else 'unlimited',
            access_logging=True
        )

        return config

    def store_compliance_record(self, record: ComplianceRecord) -> bool:
        """Store compliance record in DynamoDB with immutable audit trail"""
        try:
            # Generate immutable record hash
            record_hash = self._calculate_record_hash(record)

            # Store in DynamoDB
            item = {
                'record_id': record.record_id,
                'customer_id': record.customer_id,
                'timestamp': record.timestamp.isoformat(),
                'lc_reference_number': record.lc_reference_number,
                'validation_request_id': record.validation_request_id,

                # Validation results
                'validation_result': record.validation_result,
                'processing_time_ms': record.processing_time_ms,
                'accuracy_score': record.accuracy_score,

                # Compliance data
                'ucp600_compliance': record.ucp600_compliance,
                'ucp600_violations': record.ucp600_violations,
                'ucp600_score': record.ucp600_score,
                'isbp_compliance': record.isbp_compliance,
                'isbp_discrepancies': record.isbp_discrepancies,
                'isbp_score': record.isbp_score,
                'overall_compliance_score': record.overall_compliance_score,

                # Analysis details
                'documents_analyzed': record.documents_analyzed,
                'discrepancy_flags': record.discrepancy_flags,
                'risk_assessment': record.risk_assessment,

                # System metadata
                'reviewer_id': record.reviewer_id,
                'system_version': record.system_version,
                'validation_engine_version': record.validation_engine_version,
                'rule_set_version': record.rule_set_version,

                # Audit trail
                'request_source': record.request_source,
                'client_ip_address': record.client_ip_address,
                'user_agent': record.user_agent,
                'session_id': record.session_id,

                # Banking fields
                'correspondent_bank': record.correspondent_bank,
                'issuing_bank': record.issuing_bank,
                'trade_finance_reference': record.trade_finance_reference,
                'regulatory_classification': record.regulatory_classification,

                # Integrity
                'record_hash': record_hash,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'ttl': int((datetime.now() + timedelta(days=self._get_retention_days(record.customer_id))).timestamp())
            }

            # Add to DynamoDB
            self.compliance_table.put_item(Item=item)

            # Log access for audit trail
            self._log_compliance_access(record.customer_id, 'STORE', record.record_id)

            logger.info(f"Stored compliance record: {record.record_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store compliance record: {str(e)}")
            return False

    def _calculate_record_hash(self, record: ComplianceRecord) -> str:
        """Calculate immutable hash for compliance record integrity"""
        # Create canonical representation
        record_dict = asdict(record)

        # Sort keys for consistent hashing
        canonical_json = json.dumps(record_dict, sort_keys=True, default=str)

        # Calculate SHA-256 hash
        record_hash = hashlib.sha256(canonical_json.encode()).hexdigest()

        return record_hash

    def _get_retention_days(self, customer_id: str) -> int:
        """Get retention period for customer"""
        customer_data = self.trust_config.get('customers', {}).get(customer_id, {})
        tier = customer_data.get('tier', 'free')

        retention_map = {'free': 90, 'pro': 365, 'enterprise': 2555}
        return retention_map[tier]

    def query_compliance_records(self, customer_id: str, start_date: datetime,
                                end_date: datetime, filters: Optional[Dict] = None) -> List[ComplianceRecord]:
        """Query compliance records for export"""
        try:
            # Build query parameters
            key_condition = f"customer_id = :customer_id AND #ts BETWEEN :start_date AND :end_date"

            expression_values = {
                ':customer_id': customer_id,
                ':start_date': start_date.isoformat(),
                ':end_date': end_date.isoformat()
            }

            expression_names = {
                '#ts': 'timestamp'
            }

            # Add filters if provided
            filter_expression = None
            if filters:
                filter_parts = []

                if 'validation_result' in filters:
                    filter_parts.append("validation_result = :validation_result")
                    expression_values[':validation_result'] = filters['validation_result']

                if 'risk_assessment' in filters:
                    filter_parts.append("risk_assessment = :risk_assessment")
                    expression_values[':risk_assessment'] = filters['risk_assessment']

                if 'ucp600_compliance' in filters:
                    filter_parts.append("ucp600_compliance = :ucp600_compliance")
                    expression_values[':ucp600_compliance'] = filters['ucp600_compliance']

                if filter_parts:
                    filter_expression = ' AND '.join(filter_parts)

            # Query DynamoDB
            query_params = {
                'IndexName': 'CustomerTimestampIndex',  # GSI on customer_id and timestamp
                'KeyConditionExpression': key_condition,
                'ExpressionAttributeNames': expression_names,
                'ExpressionAttributeValues': expression_values
            }

            if filter_expression:
                query_params['FilterExpression'] = filter_expression

            response = self.compliance_table.query(**query_params)

            # Convert to ComplianceRecord objects
            records = []
            for item in response['Items']:
                record = ComplianceRecord(
                    record_id=item['record_id'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    customer_id=item['customer_id'],
                    lc_reference_number=item['lc_reference_number'],
                    validation_request_id=item['validation_request_id'],
                    validation_result=item['validation_result'],
                    processing_time_ms=int(item['processing_time_ms']),
                    accuracy_score=float(item['accuracy_score']),
                    ucp600_compliance=item['ucp600_compliance'],
                    ucp600_violations=item['ucp600_violations'],
                    ucp600_score=float(item['ucp600_score']),
                    isbp_compliance=item['isbp_compliance'],
                    isbp_discrepancies=item['isbp_discrepancies'],
                    isbp_score=float(item['isbp_score']),
                    overall_compliance_score=float(item['overall_compliance_score']),
                    documents_analyzed=item['documents_analyzed'],
                    discrepancy_flags=item['discrepancy_flags'],
                    risk_assessment=item['risk_assessment'],
                    reviewer_id=item['reviewer_id'],
                    system_version=item['system_version'],
                    validation_engine_version=item['validation_engine_version'],
                    rule_set_version=item['rule_set_version'],
                    request_source=item['request_source'],
                    client_ip_address=item.get('client_ip_address'),
                    user_agent=item.get('user_agent'),
                    session_id=item.get('session_id'),
                    correspondent_bank=item.get('correspondent_bank'),
                    issuing_bank=item.get('issuing_bank'),
                    trade_finance_reference=item.get('trade_finance_reference'),
                    regulatory_classification=item.get('regulatory_classification')
                )
                records.append(record)

            # Log access for audit trail
            self._log_compliance_access(customer_id, 'QUERY', f"{len(records)}_records")

            logger.info(f"Queried {len(records)} compliance records for {customer_id}")
            return records

        except Exception as e:
            logger.error(f"Failed to query compliance records: {str(e)}")
            return []

    def export_compliance_data(self, customer_id: str, start_date: datetime,
                             end_date: datetime, export_format: str,
                             filters: Optional[Dict] = None) -> ComplianceExportResult:
        """Export compliance data in specified format"""

        # Get customer configuration
        config = self.get_compliance_config(customer_id)

        # Check if customer has access to compliance exports
        if export_format not in config.export_formats:
            raise ValueError(f"Export format '{export_format}' not available for {config.tier} tier")

        # Query compliance records
        records = self.query_compliance_records(customer_id, start_date, end_date, filters)

        if not records:
            raise ValueError("No compliance records found for the specified criteria")

        # Apply record limits
        if config.max_records_per_export > 0 and len(records) > config.max_records_per_export:
            records = records[:config.max_records_per_export]

        # Generate export
        export_id = f"export_{customer_id}_{int(datetime.now().timestamp())}"

        try:
            if export_format == "json":
                result = self._export_json(records, customer_id, export_id, config)
            elif export_format == "csv":
                result = self._export_csv(records, customer_id, export_id, config)
            elif export_format == "pdf":
                result = self._export_pdf(records, customer_id, export_id, config)
            else:
                raise ValueError(f"Unsupported export format: {export_format}")

            # Log export activity
            self._log_compliance_access(customer_id, 'EXPORT',
                                       f"{export_format}_{len(records)}_records")

            return result

        except Exception as e:
            logger.error(f"Failed to export compliance data: {str(e)}")
            raise

    def _export_json(self, records: List[ComplianceRecord], customer_id: str,
                    export_id: str, config: ComplianceExportConfig) -> ComplianceExportResult:
        """Export compliance records as JSON"""

        # Convert records to dictionaries
        records_data = []
        for record in records:
            record_dict = asdict(record)
            # Convert datetime to ISO format
            record_dict['timestamp'] = record.timestamp.isoformat()
            records_data.append(record_dict)

        # Create export structure
        export_data = {
            "export_metadata": {
                "export_id": export_id,
                "customer_id": customer_id,
                "export_format": "json",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "record_count": len(records),
                "tier": config.tier,
                "business_type": config.business_type
            },
            "compliance_records": records_data
        }

        # Convert to JSON
        json_content = json.dumps(export_data, indent=2, default=str)
        json_bytes = json_content.encode('utf-8')

        # Upload to S3
        s3_key = f"compliance-exports/{customer_id}/{export_id}.json"
        file_hash = hashlib.sha256(json_bytes).hexdigest()

        # Add digital signature if required
        digital_signature = None
        if config.digital_signature_required and self.signing_key:
            digital_signature = self._sign_export_data(json_bytes)

        self.s3.put_object(
            Bucket=self.compliance_bucket,
            Key=s3_key,
            Body=json_bytes,
            ContentType='application/json',
            ServerSideEncryption='aws:kms' if config.encryption_required else 'AES256',
            SSEKMSKeyId=self.kms_key_id if config.encryption_required else None,
            Metadata={
                'export-id': export_id,
                'customer-id': customer_id,
                'record-count': str(len(records)),
                'file-hash': file_hash,
                'digital-signature': digital_signature or '',
                'export-format': 'json'
            }
        )

        # Generate presigned URL
        presigned_url = self.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.compliance_bucket, 'Key': s3_key},
            ExpiresIn=86400  # 24 hours
        )

        return ComplianceExportResult(
            export_id=export_id,
            customer_id=customer_id,
            export_format="json",
            record_count=len(records),
            file_size_bytes=len(json_bytes),
            s3_bucket=self.compliance_bucket,
            s3_key=s3_key,
            presigned_url=presigned_url,
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=24),
            file_hash_sha256=file_hash,
            digital_signature=digital_signature,
            encryption_status="encrypted" if config.encryption_required else "unencrypted",
            generated_at=datetime.now(timezone.utc),
            exported_by="system",
            export_criteria={
                'start_date': records[0].timestamp.isoformat(),
                'end_date': records[-1].timestamp.isoformat(),
                'record_count': len(records)
            }
        )

    def _export_csv(self, records: List[ComplianceRecord], customer_id: str,
                   export_id: str, config: ComplianceExportConfig) -> ComplianceExportResult:
        """Export compliance records as CSV"""

        # Create CSV content
        output = StringIO()

        # Define CSV columns
        fieldnames = [
            'record_id', 'timestamp', 'customer_id', 'lc_reference_number',
            'validation_request_id', 'validation_result', 'processing_time_ms',
            'accuracy_score', 'ucp600_compliance', 'ucp600_violations', 'ucp600_score',
            'isbp_compliance', 'isbp_discrepancies', 'isbp_score',
            'overall_compliance_score', 'documents_analyzed',
            'discrepancy_flags', 'risk_assessment', 'reviewer_id',
            'system_version', 'validation_engine_version', 'rule_set_version',
            'request_source', 'client_ip_address', 'user_agent', 'session_id',
            'correspondent_bank', 'issuing_bank', 'trade_finance_reference',
            'regulatory_classification'
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        # Write records
        for record in records:
            record_dict = asdict(record)
            # Convert lists to strings for CSV
            for key, value in record_dict.items():
                if isinstance(value, list):
                    record_dict[key] = ';'.join(str(v) for v in value)
                elif isinstance(value, datetime):
                    record_dict[key] = value.isoformat()

            writer.writerow(record_dict)

        csv_content = output.getvalue()
        csv_bytes = csv_content.encode('utf-8')

        # Upload to S3
        s3_key = f"compliance-exports/{customer_id}/{export_id}.csv"
        file_hash = hashlib.sha256(csv_bytes).hexdigest()

        # Add digital signature if required
        digital_signature = None
        if config.digital_signature_required and self.signing_key:
            digital_signature = self._sign_export_data(csv_bytes)

        self.s3.put_object(
            Bucket=self.compliance_bucket,
            Key=s3_key,
            Body=csv_bytes,
            ContentType='text/csv',
            ServerSideEncryption='aws:kms' if config.encryption_required else 'AES256',
            SSEKMSKeyId=self.kms_key_id if config.encryption_required else None,
            Metadata={
                'export-id': export_id,
                'customer-id': customer_id,
                'record-count': str(len(records)),
                'file-hash': file_hash,
                'digital-signature': digital_signature or '',
                'export-format': 'csv'
            }
        )

        # Generate presigned URL
        presigned_url = self.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.compliance_bucket, 'Key': s3_key},
            ExpiresIn=86400
        )

        return ComplianceExportResult(
            export_id=export_id,
            customer_id=customer_id,
            export_format="csv",
            record_count=len(records),
            file_size_bytes=len(csv_bytes),
            s3_bucket=self.compliance_bucket,
            s3_key=s3_key,
            presigned_url=presigned_url,
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=24),
            file_hash_sha256=file_hash,
            digital_signature=digital_signature,
            encryption_status="encrypted" if config.encryption_required else "unencrypted",
            generated_at=datetime.now(timezone.utc),
            exported_by="system",
            export_criteria={
                'start_date': records[0].timestamp.isoformat(),
                'end_date': records[-1].timestamp.isoformat(),
                'record_count': len(records)
            }
        )

    def _export_pdf(self, records: List[ComplianceRecord], customer_id: str,
                   export_id: str, config: ComplianceExportConfig) -> ComplianceExportResult:
        """Export compliance records as bank-auditable PDF"""

        if config.tier != 'enterprise':
            raise ValueError("PDF export is only available for Enterprise tier")

        # Create PDF document
        filename = f"compliance_export_{export_id}.pdf"
        pdf_path = f"/tmp/{filename}"

        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        story = []

        # Header
        customer_data = self.trust_config.get('customers', {}).get(customer_id, {})
        company_name = customer_data.get('company_name', 'Customer')

        story.append(Paragraph("Letter of Credit Compliance Export", self.styles['Title']))
        story.append(Paragraph(f"Bank: {company_name}", self.styles['Heading2']))
        story.append(Paragraph(f"Export ID: {export_id}", self.styles['Normal']))
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}", self.styles['Normal']))
        story.append(Paragraph(f"Record Count: {len(records):,}", self.styles['Normal']))
        story.append(Spacer(1, 0.25*72))  # 0.25 inch space

        # Compliance Summary Table
        story.append(Paragraph("Compliance Summary", self.styles['Heading2']))

        # Calculate summary statistics
        total_records = len(records)
        passed_validations = len([r for r in records if r.validation_result == 'pass'])
        failed_validations = len([r for r in records if r.validation_result == 'fail'])
        ucp600_compliant = len([r for r in records if r.ucp600_compliance])
        isbp_compliant = len([r for r in records if r.isbp_compliance])

        summary_data = [
            ['Metric', 'Count', 'Percentage'],
            ['Total Records', f"{total_records:,}", '100.0%'],
            ['Validations Passed', f"{passed_validations:,}", f"{(passed_validations/total_records*100):.1f}%"],
            ['Validations Failed', f"{failed_validations:,}", f"{(failed_validations/total_records*100):.1f}%"],
            ['UCP600 Compliant', f"{ucp600_compliant:,}", f"{(ucp600_compliant/total_records*100):.1f}%"],
            ['ISBP Compliant', f"{isbp_compliant:,}", f"{(isbp_compliant/total_records*100):.1f}%"]
        ]

        summary_table = Table(summary_data, colWidths=[2.5*72, 1*72, 1*72])  # 72 points per inch
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(summary_table)
        story.append(Spacer(1, 0.25*72))

        # Detailed Records (first 100 for PDF space constraints)
        story.append(Paragraph("Detailed Records (First 100)", self.styles['Heading2']))

        detail_data = [['Record ID', 'Timestamp', 'LC Reference', 'Result', 'UCP600', 'ISBP', 'Score']]

        for record in records[:100]:  # Limit to first 100 records for PDF
            detail_data.append([
                record.record_id[:12] + '...',  # Truncate long IDs
                record.timestamp.strftime('%Y-%m-%d %H:%M'),
                record.lc_reference_number[:15] + '...',
                record.validation_result.upper(),
                f"{record.ucp600_score:.1f}%",
                f"{record.isbp_score:.1f}%",
                f"{record.overall_compliance_score:.1f}%"
            ])

        detail_table = Table(detail_data, colWidths=[1*72, 0.9*72, 1.2*72, 0.6*72, 0.6*72, 0.6*72, 0.6*72])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER')
        ]))

        story.append(detail_table)
        story.append(Spacer(1, 0.25*72))

        # Digital Signature for Enterprise
        if config.digital_signature_required and self.signing_key:
            story.append(Paragraph("Audit Verification", self.styles['Heading2']))
            story.append(Paragraph("This document has been digitally signed for audit compliance.", self.styles['Normal']))
            story.append(Paragraph("Signature Algorithm: RSA-2048 with SHA-256", self.styles['Normal']))
            story.append(Paragraph(f"Document Hash: SHA-256", self.styles['Normal']))

        # Build PDF
        doc.build(story)

        # Read PDF content
        with open(pdf_path, 'rb') as pdf_file:
            pdf_bytes = pdf_file.read()

        # Upload to S3
        s3_key = f"compliance-exports/{customer_id}/{export_id}.pdf"
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()

        # Add digital signature if required
        digital_signature = None
        if config.digital_signature_required and self.signing_key:
            digital_signature = self._sign_export_data(pdf_bytes)

        self.s3.put_object(
            Bucket=self.compliance_bucket,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType='application/pdf',
            ServerSideEncryption='aws:kms' if config.encryption_required else 'AES256',
            SSEKMSKeyId=self.kms_key_id if config.encryption_required else None,
            Metadata={
                'export-id': export_id,
                'customer-id': customer_id,
                'record-count': str(len(records)),
                'file-hash': file_hash,
                'digital-signature': digital_signature or '',
                'export-format': 'pdf'
            }
        )

        # Generate presigned URL
        presigned_url = self.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.compliance_bucket, 'Key': s3_key},
            ExpiresIn=86400
        )

        return ComplianceExportResult(
            export_id=export_id,
            customer_id=customer_id,
            export_format="pdf",
            record_count=len(records),
            file_size_bytes=len(pdf_bytes),
            s3_bucket=self.compliance_bucket,
            s3_key=s3_key,
            presigned_url=presigned_url,
            expiry_time=datetime.now(timezone.utc) + timedelta(hours=24),
            file_hash_sha256=file_hash,
            digital_signature=digital_signature,
            encryption_status="encrypted" if config.encryption_required else "unencrypted",
            generated_at=datetime.now(timezone.utc),
            exported_by="system",
            export_criteria={
                'start_date': records[0].timestamp.isoformat(),
                'end_date': records[-1].timestamp.isoformat(),
                'record_count': len(records)
            }
        )

    def _sign_export_data(self, data_bytes: bytes) -> str:
        """Generate digital signature for export data"""
        if not self.signing_key:
            return ""

        try:
            signature = self.signing_key.sign(
                data_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            # Return base64 encoded signature
            return base64.b64encode(signature).decode('utf-8')

        except Exception as e:
            logger.error(f"Failed to sign export data: {str(e)}")
            return ""

    def _log_compliance_access(self, customer_id: str, action: str, details: str):
        """Log compliance data access for audit trail"""
        try:
            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'customer_id': customer_id,
                'action': action,
                'details': details,
                'source_ip': 'system',  # Would be actual IP in production
                'user_id': 'system'
            }

            # Store in audit logs
            log_key = f"audit-logs/{customer_id}/{datetime.now().strftime('%Y/%m/%d')}/{int(datetime.now().timestamp())}.json"

            self.s3.put_object(
                Bucket=self.audit_logs_bucket,
                Key=log_key,
                Body=json.dumps(log_entry),
                ContentType='application/json'
            )

        except Exception as e:
            logger.error(f"Failed to log compliance access: {str(e)}")

    def verify_export_integrity(self, export_result: ComplianceExportResult) -> bool:
        """Verify the integrity of an exported file"""
        try:
            # Download file from S3
            response = self.s3.get_object(
                Bucket=export_result.s3_bucket,
                Key=export_result.s3_key
            )

            file_content = response['Body'].read()

            # Calculate hash
            calculated_hash = hashlib.sha256(file_content).hexdigest()

            # Compare with stored hash
            integrity_verified = calculated_hash == export_result.file_hash_sha256

            logger.info(f"Export integrity verification for {export_result.export_id}: {integrity_verified}")

            return integrity_verified

        except Exception as e:
            logger.error(f"Failed to verify export integrity: {str(e)}")
            return False

def main():
    """Demo compliance export functionality"""
    manager = ComplianceExportManager()

    print("=== LCopilot Compliance Export Demo ===")

    # Create sample compliance records
    sample_records = []
    for i in range(10):
        record = ComplianceRecord(
            record_id=f"rec_{int(datetime.now().timestamp())}_{i}",
            timestamp=datetime.now(timezone.utc) - timedelta(days=i),
            customer_id="enterprise-bank-001",
            lc_reference_number=f"LC2024{1000+i:04d}",
            validation_request_id=f"req_{int(datetime.now().timestamp())}_{i}",
            validation_result="pass" if i % 3 != 0 else "fail",
            processing_time_ms=2500 + (i * 100),
            accuracy_score=0.995 - (i * 0.001),
            ucp600_compliance=i % 3 != 0,
            ucp600_violations=[] if i % 3 != 0 else ["Missing signature"],
            ucp600_score=95.5 - (i * 0.5) if i % 3 != 0 else 72.3,
            isbp_compliance=i % 4 != 0,
            isbp_discrepancies=[] if i % 4 != 0 else ["Date format"],
            isbp_score=92.1 - (i * 0.3) if i % 4 != 0 else 68.7,
            overall_compliance_score=((95.5 - (i * 0.5)) + (92.1 - (i * 0.3))) / 2 if i % 2 != 0 else 70.5,
            documents_analyzed=["LC", "Invoice", "BL"],
            discrepancy_flags=[] if i % 3 != 0 else ["signature_missing"],
            risk_assessment="low" if i % 3 != 0 else "medium",
            reviewer_id="SYSTEM_AUTO",
            system_version="2.1.0",
            validation_engine_version="1.5.3",
            rule_set_version="UCP600-2024.1",
            request_source="API",
            correspondent_bank="FIRST_INTL_BANK",
            issuing_bank="TRADE_FINANCE_BANK",
            trade_finance_reference=f"TF2024{2000+i:04d}",
            regulatory_classification="STANDARD_LC"
        )
        sample_records.append(record)

    # Store sample records
    print(f"Storing {len(sample_records)} sample compliance records...")
    for record in sample_records:
        manager.store_compliance_record(record)

    # Test different export formats
    customer_id = "enterprise-bank-001"
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)

    for export_format in ["json", "csv", "pdf"]:
        print(f"\n--- Testing {export_format.upper()} Export ---")

        try:
            export_result = manager.export_compliance_data(
                customer_id, start_date, end_date, export_format
            )

            print(f"Export ID: {export_result.export_id}")
            print(f"Record Count: {export_result.record_count}")
            print(f"File Size: {export_result.file_size_bytes:,} bytes")
            print(f"Download URL: {export_result.presigned_url[:50]}...")
            print(f"File Hash: {export_result.file_hash_sha256[:16]}...")
            print(f"Encryption: {export_result.encryption_status}")

            # Verify integrity
            integrity_verified = manager.verify_export_integrity(export_result)
            print(f"Integrity Verified: {integrity_verified}")

        except Exception as e:
            print(f"Export failed: {str(e)}")

if __name__ == "__main__":
    main()