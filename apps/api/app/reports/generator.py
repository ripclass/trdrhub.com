"""
PDF report generator using WeasyPrint.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import uuid4
from io import BytesIO
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from .templates import ReportTemplate
from ..rules.models import DocumentValidationSummary
from ..models import Report, ValidationSession, User


def _import_weasyprint():
    """Import WeasyPrint lazily so that missing native deps don't break imports."""
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration

    return HTML, CSS, FontConfiguration


class ReportGenerator:
    """Professional PDF report generator for validation results."""

    def __init__(self):
        self.template = ReportTemplate()
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'lcopilot-documents')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.static_dir = Path(__file__).parent.parent.parent / "static"

        self._weasyprint_ready = False
        self._weasyprint_error: Optional[Exception] = None
        self.HTML = None
        self.CSS = None
        self.font_config = None
        self.professional_css = None

        try:
            self.HTML, self.CSS, FontConfiguration = _import_weasyprint()
            self.font_config = FontConfiguration()
            self.professional_css = self._load_professional_css()
            self._weasyprint_ready = True
        except Exception as exc:  # pragma: no cover - platform specific
            # Keep import-time errors from crashing Windows/dev shells that
            # don't have GTK/Pango. We'll raise a helpful error if report
            # generation is attempted.
            self._weasyprint_error = exc
    
    async def generate_report(
        self,
        summary: DocumentValidationSummary,
        session: ValidationSession,
        user: User,
        languages: List[str] = None,
        report_mode: str = "single"
    ) -> Report:
        """
        Generate PDF report and upload to S3.

        Args:
            summary: Validation results summary
            session: Validation session
            user: User who requested the report
            languages: List of languages for the report (e.g., ["en", "bn"])
            report_mode: "single", "bilingual", or "parallel"

        Returns:
            Report model with S3 information
        """
        from ..utils.i18n import translate, get_language_direction

        # Default to English if no languages specified
        if languages is None:
            languages = ["en"]

        # Prepare session details for the template
        session_details = {
            'user_name': user.full_name,
            'user_email': user.email,
            'session_created_at': session.created_at,
            'processing_time_ms': summary.processing_time_ms,
            'company_name': user.company.name if user.company else "Unknown"
        }

        # Generate report based on mode
        if report_mode == "parallel" and len(languages) > 1:
            # Generate separate PDFs for each language and combine
            pdf_buffer = await self._generate_parallel_report(
                summary, session_details, languages
            )
            filename_suffix = f"_{'-'.join(languages)}_parallel"
        elif report_mode == "bilingual" and len(languages) > 1:
            # Generate side-by-side bilingual PDF
            pdf_buffer = await self._generate_bilingual_report(
                summary, session_details, languages
            )
            filename_suffix = f"_{'-'.join(languages)}_bilingual"
        else:
            # Generate single language PDF
            primary_language = languages[0]
            html_content = self.template.generate_report_html(
                summary=summary,
                session_details=session_details,
                language=primary_language
            )
            pdf_buffer = self._html_to_pdf(html_content, primary_language)
            filename_suffix = f"_{primary_language}"

        # Upload to S3
        report_id = uuid4()
        s3_key = f"reports/{session.id}/{report_id}{filename_suffix}.pdf"

        file_size = await self._upload_to_s3(pdf_buffer, s3_key)

        # Create Report record with language metadata
        report = Report(
            id=report_id,
            validation_session_id=session.id,
            report_version=1,  # TODO: Handle versioning
            s3_key=s3_key,
            file_size=file_size,
            total_discrepancies=summary.failed_rules,
            critical_discrepancies=summary.critical_issues,
            major_discrepancies=summary.major_issues,
            minor_discrepancies=summary.minor_issues,
            generated_by_user_id=user.id,
            metadata={
                "languages": languages,
                "report_mode": report_mode,
                "generated_at": datetime.utcnow().isoformat(),
                "language_count": len(languages)
            }
        )

        return report

    async def _generate_bilingual_report(
        self,
        summary,
        session_details: Dict[str, Any],
        languages: List[str]
    ) -> BytesIO:
        """
        Generate side-by-side bilingual PDF report.

        Args:
            summary: Validation results summary
            session_details: Session metadata
            languages: List of languages (expects exactly 2)

        Returns:
            PDF buffer with bilingual content
        """
        from ..utils.i18n import translate, get_language_direction

        if len(languages) != 2:
            raise ValueError("Bilingual reports require exactly 2 languages")

        primary_lang, secondary_lang = languages[0], languages[1]

        # Generate bilingual HTML template
        bilingual_html = self.template.generate_bilingual_report_html(
            summary=summary,
            session_details=session_details,
            primary_language=primary_lang,
            secondary_language=secondary_lang
        )

        # Generate PDF with enhanced CSS for bilingual layout
        return self._html_to_pdf_bilingual(bilingual_html, languages)

    async def _generate_parallel_report(
        self,
        summary,
        session_details: Dict[str, Any],
        languages: List[str]
    ) -> BytesIO:
        """
        Generate parallel report (separate pages for each language).

        Args:
            summary: Validation results summary
            session_details: Session metadata
            languages: List of languages

        Returns:
            PDF buffer with combined content
        """
        from PyPDF2 import PdfWriter, PdfReader
        import io

        pdf_writer = PdfWriter()

        # Generate PDF for each language
        for language in languages:
            html_content = self.template.generate_report_html(
                summary=summary,
                session_details=session_details,
                language=language
            )

            # Convert to PDF
            single_pdf_buffer = self._html_to_pdf(html_content, language)

            # Read PDF and add pages to writer
            pdf_reader = PdfReader(single_pdf_buffer)
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)

        # Combine all PDFs
        combined_buffer = BytesIO()
        pdf_writer.write(combined_buffer)
        combined_buffer.seek(0)

        return combined_buffer

    def _load_professional_css(self) -> Optional["CSS"]:
        """Load professional CSS with embedded fonts."""

        if not self.CSS:
            return None

        # Path to CSS file
        css_path = self.static_dir / "css" / "reports.css"

        if css_path.exists():
            # Load external CSS file
            return self.CSS(filename=str(css_path))
        else:
            # Fallback inline CSS
            return self.CSS(string="""
            @page {
                size: A4;
                margin: 1.5cm 2cm;
            }

            body {
                font-family: 'Inter', 'Noto Sans Bengali', Arial, sans-serif;
                font-size: 10pt;
                line-height: 1.5;
                color: #1f2937;
            }

            .bangla {
                font-family: 'Noto Sans Bengali', Arial, sans-serif;
                font-feature-settings: "liga" 1, "clig" 1, "kern" 1;
            }
            """)

    def _html_to_pdf(self, html_content: str, language: str = "en") -> BytesIO:
        """Convert HTML content to PDF using WeasyPrint with professional styling."""

        self._ensure_weasyprint()
        try:
            # Create WeasyPrint HTML object with proper base URL
            html_obj = self.HTML(string=html_content, base_url=str(self.static_dir))

            # Generate PDF with professional CSS and font configuration
            pdf_buffer = BytesIO()

            # Use a more compatible approach
            stylesheets = [css for css in [self.professional_css] if css is not None]
            document = html_obj.render(
                stylesheets=stylesheets,
                font_config=self.font_config
            )
            document.write_pdf(pdf_buffer)
            pdf_buffer.seek(0)

            return pdf_buffer

        except Exception as e:
            # Fallback to basic PDF generation without font config
            print(f"Warning: Advanced PDF generation failed, using fallback mode: {str(e)}")

            html_obj = self.HTML(string=html_content, base_url=str(self.static_dir))
            pdf_buffer = BytesIO()
            stylesheets = [css for css in [self.professional_css] if css is not None]
            html_obj.write_pdf(pdf_buffer, stylesheets=stylesheets)
            pdf_buffer.seek(0)
            return pdf_buffer

    def _html_to_pdf_bilingual(self, html_content: str, languages: List[str]) -> BytesIO:
        """Convert bilingual HTML content to PDF with enhanced styling."""
        self._ensure_weasyprint()
        try:
            # Create enhanced CSS for bilingual layout
            bilingual_css = self._get_bilingual_css(languages)

            # Create WeasyPrint HTML object
            html_obj = self.HTML(string=html_content, base_url=str(self.static_dir))

            # Generate PDF with bilingual styling
            pdf_buffer = BytesIO()
            stylesheets = [
                css for css in [self.professional_css, bilingual_css] if css is not None
            ]
            document = html_obj.render(
                stylesheets=stylesheets,
                font_config=self.font_config
            )
            document.write_pdf(pdf_buffer)
            pdf_buffer.seek(0)

            return pdf_buffer

        except Exception as e:
            print(f"Warning: Bilingual PDF generation failed, using fallback: {str(e)}")
            # Fallback to regular PDF generation
            return self._html_to_pdf(html_content, languages[0])

    def _get_bilingual_css(self, languages: List[str]) -> Optional["CSS"]:
        """Generate CSS for bilingual layout."""
        self._ensure_weasyprint()
        from ..utils.i18n import get_language_direction

        # Determine if any language is RTL
        has_rtl = any(get_language_direction(lang) == 'rtl' for lang in languages)

        bilingual_styles = """
        .bilingual-container {
            display: flex;
            width: 100%;
            gap: 20px;
            page-break-inside: avoid;
        }

        .language-column {
            flex: 1;
            padding: 0 10px;
        }

        .language-column.primary {
            border-right: 1px solid #e5e7eb;
        }

        .language-column.secondary {
            font-size: 9pt;
        }

        .rtl-content {
            direction: rtl;
            text-align: right;
        }

        .ltr-content {
            direction: ltr;
            text-align: left;
        }

        .bilingual-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            border-bottom: 2px solid #1f2937;
            padding-bottom: 10px;
        }

        .section-bilingual {
            margin-bottom: 15px;
            border: 1px solid #f3f4f6;
            border-radius: 4px;
            overflow: hidden;
        }

        .section-header-bilingual {
            background-color: #f8fafc;
            padding: 8px 12px;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
        }

        @media print {
            .bilingual-container {
                break-inside: avoid;
            }
        }
        """

        if has_rtl:
            bilingual_styles += """
            .bilingual-container.mixed-direction {
                align-items: flex-start;
            }
            """

        return self.CSS(string=bilingual_styles)

    async def _upload_to_s3(self, pdf_buffer: BytesIO, s3_key: str) -> int:
        """Upload PDF to S3 and return file size."""
        
        try:
            # Get file size
            pdf_buffer.seek(0, 2)  # Seek to end
            file_size = pdf_buffer.tell()
            pdf_buffer.seek(0)  # Reset to beginning
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=pdf_buffer,
                ContentType='application/pdf',
                ServerSideEncryption='AES256',
                Metadata={
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'generator': 'lcopilot-api'
                }
            )
            
            return file_size

        except ClientError as e:
            raise Exception(f"Failed to upload report to S3: {str(e)}")

    def get_font_paths(self) -> Dict[str, str]:
        """Get paths to embedded fonts."""
        fonts_dir = self.static_dir / "fonts"
        return {
            'noto_bengali_regular': str(fonts_dir / "NotoSansBengali-Regular.ttf"),
            'noto_bengali_bold': str(fonts_dir / "NotoSansBengali-Bold.ttf")
        }
    
    def generate_sample_report(self, language: str = "en") -> str:
        """Generate a sample HTML report for testing."""
        from uuid import UUID
        from ..rules.models import (
            DocumentValidationSummary, ValidationResult, ValidationRule,
            ValidationStatus, FieldType, FieldComparison, ExtractedField
        )
        from ..models import DiscrepancySeverity, DocumentType

        # Create sample validation rules and results
        sample_rules = [
            ValidationRule(
                rule_id="FF001",
                rule_name="LC Expiry Date Future" if language == "en" else "এলসি মেয়াদ ভবিষ্যতে",
                description="LC expiry date must be in the future" if language == "en" else "এলসি মেয়াদ ভবিষ্যতে থাকতে হবে",
                field_type=FieldType.DATE,
                severity=DiscrepancySeverity.CRITICAL
            ),
            ValidationRule(
                rule_id="AM002",
                rule_name="Amount Consistency" if language == "en" else "পরিমাণের সামঞ্জস্য",
                description="Invoice amount should not exceed LC amount" if language == "en" else "ইনভয়েস পরিমাণ এলসি পরিমাণ অতিক্রম করা উচিত নয়",
                field_type=FieldType.AMOUNT,
                severity=DiscrepancySeverity.MAJOR
            )
        ]

        sample_results = [
            ValidationResult(
                rule=sample_rules[0],
                status=ValidationStatus.FAILED,
                message="LC has expired on 2023-12-01" if language == "en" else "এলসি ২০২৩-১২-০১ তারিখে মেয়াদ শেষ হয়েছে",
                expected_value="Future date" if language == "en" else "ভবিষ্যৎ তারিখ",
                actual_value="2023-12-01",
                confidence=0.95,
                affected_documents=[DocumentType.LETTER_OF_CREDIT]
            ),
            ValidationResult(
                rule=sample_rules[1],
                status=ValidationStatus.FAILED,
                message="Invoice amount exceeds LC amount" if language == "en" else "ইনভয়েস পরিমাণ এলসি পরিমাণ অতিক্রম করেছে",
                expected_value="≤ $95,000.00",
                actual_value="$100,000.00",
                confidence=0.88,
                affected_documents=[DocumentType.COMMERCIAL_INVOICE, DocumentType.LETTER_OF_CREDIT]
            )
        ]

        sample_comparisons = [
            FieldComparison(
                field_name="Amount" if language == "en" else "পরিমাণ",
                field_type=FieldType.AMOUNT,
                lc_field=ExtractedField(
                    field_name="lc_amount",
                    field_type=FieldType.AMOUNT,
                    value="$95,000.00",
                    confidence=0.95,
                    document_type=DocumentType.LETTER_OF_CREDIT
                ),
                invoice_field=ExtractedField(
                    field_name="invoice_amount",
                    field_type=FieldType.AMOUNT,
                    value="$100,000.00",
                    confidence=0.90,
                    document_type=DocumentType.COMMERCIAL_INVOICE
                ),
                bl_field=ExtractedField(
                    field_name="bl_amount",
                    field_type=FieldType.AMOUNT,
                    value="$100,000.00",
                    confidence=0.92,
                    document_type=DocumentType.BILL_OF_LADING
                ),
                is_consistent=False,
                discrepancies=[]
            ),
            FieldComparison(
                field_name="Goods Description" if language == "en" else "পণ্যের বিবরণ",
                field_type=FieldType.TEXT,
                lc_field=ExtractedField(
                    field_name="goods_description",
                    field_type=FieldType.TEXT,
                    value="Cotton Fabrics",
                    confidence=0.98,
                    document_type=DocumentType.LETTER_OF_CREDIT
                ),
                invoice_field=ExtractedField(
                    field_name="goods_description",
                    field_type=FieldType.TEXT,
                    value="Cotton Fabrics",
                    confidence=0.95,
                    document_type=DocumentType.COMMERCIAL_INVOICE
                ),
                bl_field=ExtractedField(
                    field_name="goods_description",
                    field_type=FieldType.TEXT,
                    value="Cotton Fabrics",
                    confidence=0.93,
                    document_type=DocumentType.BILL_OF_LADING
                ),
                is_consistent=True,
                discrepancies=[]
            )
        ]

        sample_summary = DocumentValidationSummary(
            session_id=UUID('12345678-1234-5678-9012-123456789012'),
            total_rules=8,
            passed_rules=6,
            failed_rules=2,
            warnings=1,
            critical_issues=1,
            major_issues=1,
            minor_issues=0,
            validation_results=sample_results,
            field_comparisons=sample_comparisons,
            processing_time_ms=2150,
            validated_at=datetime.now(timezone.utc)
        )

        session_details = {
            'user_name': 'জন ডো' if language == "bn" else 'John Doe',
            'user_email': 'john.doe@example.com',
            'session_created_at': datetime.now(timezone.utc),
            'processing_time_ms': 2150
        }

        return self.template.generate_report_html(
            summary=sample_summary,
            session_details=session_details,
            language=language
        )

    def generate_sample_pdf(self, language: str = "en", output_path: str = None) -> str:
        """Generate a sample PDF report for testing and save to file."""

        # Generate HTML content
        html_content = self.generate_sample_report(language)

        # Convert to PDF
        pdf_buffer = self._html_to_pdf(html_content, language)

        # Save to file
        if not output_path:
            output_path = f"/tmp/lcopilot_sample_report_{language}.pdf"

        with open(output_path, 'wb') as f:
            f.write(pdf_buffer.getvalue())

        return output_path

    def _ensure_weasyprint(self) -> None:
        """Ensure WeasyPrint is available before attempting to generate PDFs."""
        if not self._weasyprint_ready:
            raise RuntimeError(
                "WeasyPrint is not available in this environment. Install the "
                "platform dependencies (GTK/Pango) or skip PDF generation. "
                f"Original import error: {self._weasyprint_error}"
            )