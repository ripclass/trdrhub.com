"""
Professional HTML template generator for PDF reports using Jinja2.
"""

import os
from typing import Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    Environment = None
    FileSystemLoader = None

from ..rules.models import DocumentValidationSummary, ValidationResult, FieldComparison


class ReportTemplate:
    """Professional template generator for validation reports."""

    def __init__(self):
        # Get the template directory path
        self.template_dir = Path(__file__).parent.parent.parent / "templates" / "reports"
        self.static_dir = Path(__file__).parent.parent.parent / "static"

        # Initialize Jinja2 environment if available
        if JINJA2_AVAILABLE:
            self.env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=select_autoescape(['html', 'xml'])
            )
        else:
            self.env = None
    
    def generate_report_html(
        self,
        summary: DocumentValidationSummary,
        session_details: Dict[str, Any],
        language: str = "en"
    ) -> str:
        """Generate complete HTML report using Jinja2 template."""

        # Get labels for the specified language
        labels = self._get_labels(language)

        # Prepare template context
        context = self._prepare_template_context(summary, session_details, labels, language)

        # Use Jinja2 template if available, otherwise fallback to simple template
        if self.env:
            template = self.env.get_template('report_template.html')
            return template.render(**context)
        else:
            # Fallback to simple string template
            return self._generate_fallback_html(context)

    def generate_bilingual_report_html(
        self,
        summary: DocumentValidationSummary,
        session_details: Dict[str, Any],
        primary_language: str = "en",
        secondary_language: str = "bn"
    ) -> str:
        """Generate bilingual HTML report with side-by-side languages."""
        from ..utils.i18n import translate, get_language_direction

        # Prepare contexts for both languages
        primary_labels = self._get_labels_with_translation(primary_language)
        secondary_labels = self._get_labels_with_translation(secondary_language)

        primary_context = self._prepare_template_context(
            summary, session_details, primary_labels, primary_language
        )
        secondary_context = self._prepare_template_context(
            summary, session_details, secondary_labels, secondary_language
        )

        # Determine text directions
        primary_direction = get_language_direction(primary_language)
        secondary_direction = get_language_direction(secondary_language)

        # Create bilingual context
        bilingual_context = {
            'primary': primary_context,
            'secondary': secondary_context,
            'primary_direction': primary_direction,
            'secondary_direction': secondary_direction,
            'has_mixed_direction': primary_direction != secondary_direction,
            'summary': summary,
            'session_details': session_details
        }

        # Use Jinja2 template if available
        if self.env:
            try:
                template = self.env.get_template('bilingual_report_template.html')
                return template.render(**bilingual_context)
            except Exception:
                # Fallback to generated bilingual template
                return self._generate_bilingual_fallback_html(bilingual_context)
        else:
            return self._generate_bilingual_fallback_html(bilingual_context)

    def _get_labels_with_translation(self, language: str) -> Dict[str, str]:
        """Get labels using the translation system."""
        from ..utils.i18n import translate

        try:
            return {
                'report_title': translate('report.title', language),
                'subtitle': translate('report.subtitle', language),
                'generated_on': translate('report.generated_on', language),
                'generated_by': translate('report.generated_by', language),
                'company': translate('report.company', language),
                'session_id': translate('report.session_id', language),
                'executive_summary': translate('report.executive_summary', language),
                'document_summary': translate('report.document_summary', language),
                'validation_results': translate('report.validation_results', language),
                'discrepancies': translate('report.discrepancies', language),
                'recommendations': translate('report.recommendations', language),
                'total_checks': translate('validation.total_checks', language),
                'passed_checks': translate('validation.passed_checks', language),
                'failed_checks': translate('validation.failed_checks', language),
                'accuracy_score': translate('validation.accuracy_score', language),
                'compliance_rating': translate('validation.compliance_rating', language),
                'risk_assessment': translate('validation.risk_assessment', language),
                'valid': translate('status.valid', language),
                'invalid': translate('status.invalid', language),
                'warning': translate('status.warning', language),
                'passed': translate('status.passed', language),
                'failed': translate('status.failed', language)
            }
        except Exception as e:
            # Fallback to hardcoded labels if translation fails
            return self._get_labels(language)

    def _generate_bilingual_fallback_html(self, context: Dict[str, Any]) -> str:
        """Generate bilingual HTML as fallback when template is not available."""
        primary = context['primary']
        secondary = context['secondary']
        summary = context['summary']

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>LCopilot - Bilingual Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .bilingual-container {{ display: flex; gap: 20px; }}
                .language-column {{ flex: 1; padding: 0 10px; }}
                .language-column.primary {{ border-right: 1px solid #ccc; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .section {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; }}
                .rtl-content {{ direction: rtl; text-align: right; }}
                .ltr-content {{ direction: ltr; text-align: left; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>LCopilot - Letter of Credit Validation Report</h1>
                <h2>LC رپورٹ | এলসি রিপোর্ট | LC التقرير</h2>
            </div>

            <div class="bilingual-container">
                <div class="language-column primary">
                    <div class="{'rtl-content' if context['primary_direction'] == 'rtl' else 'ltr-content'}">
                        <h2>{primary['labels']['report_title']}</h2>
                        <div class="section">
                            <h3>{primary['labels']['validation_results']}</h3>
                            <p>{primary['labels']['total_checks']}: {summary.total_rules}</p>
                            <p>{primary['labels']['passed_checks']}: {summary.passed_rules}</p>
                            <p>{primary['labels']['failed_checks']}: {summary.failed_rules}</p>
                        </div>
                    </div>
                </div>

                <div class="language-column secondary">
                    <div class="{'rtl-content' if context['secondary_direction'] == 'rtl' else 'ltr-content'}">
                        <h2>{secondary['labels']['report_title']}</h2>
                        <div class="section">
                            <h3>{secondary['labels']['validation_results']}</h3>
                            <p>{secondary['labels']['total_checks']}: {summary.total_rules}</p>
                            <p>{secondary['labels']['passed_checks']}: {summary.passed_rules}</p>
                            <p>{secondary['labels']['failed_checks']}: {summary.failed_rules}</p>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    def _prepare_template_context(
        self,
        summary: DocumentValidationSummary,
        session_details: Dict[str, Any],
        labels: Dict[str, str],
        language: str
    ) -> Dict[str, Any]:
        """Prepare the template context with all necessary data."""

        # Get failed validation results
        failed_results = [r for r in summary.validation_results if r.status.value == "failed"]

        # Format timestamps
        generated_at = summary.validated_at.strftime('%B %d, %Y at %H:%M UTC')
        generated_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        # Prepare paths
        css_path = str(self.static_dir / "css" / "reports.css")
        logo_path = str(self.static_dir / "images" / "lcopilot-logo.svg")
        fonts_path = str(self.static_dir / "fonts")

        return {
            'summary': summary,
            'session_details': session_details,
            'labels': labels,
            'language': language,
            'failed_results': failed_results,
            'generated_at': generated_at,
            'generated_timestamp': generated_timestamp,
            'css_path': css_path,
            'logo_path': logo_path,
            'fonts_path': fonts_path,
            # Template filters
            'round': round,
        }
    
    def _generate_fallback_html(self, context: Dict[str, Any]) -> str:
        """Generate HTML using simple string formatting as fallback."""

        # Simple fallback template for when Jinja2 is not available
        html = f"""
        <!DOCTYPE html>
        <html lang="{context['language']}">
        <head>
            <meta charset="UTF-8">
            <title>{context['labels']['report_title']} - LCopilot</title>
            <style>/* Basic fallback styles */</style>
        </head>
        <body class="{'bangla' if context['language'] == 'bn' else ''}">
            <h1>LCopilot - {context['labels']['report_title']}</h1>
            <p>Session: {context['summary'].session_id}</p>
            <p>Generated: {context['generated_at']}</p>
            <p>Status: {context['summary'].passed_rules} passed, {context['summary'].failed_rules} failed</p>
            <p>This is a fallback template. Please install Jinja2 for full template support.</p>
        </body>
        </html>
        """

        return html
    
    def _get_labels(self, language: str) -> Dict[str, str]:
        """Get localized labels for the report."""
        if language == "bn":
            return {
                'report_title': 'এলসি যাচাইকরণ প্রতিবেদন',
                'session_id': 'সেশন আইডি',
                'generated_on': 'প্রস্তুতকৃত তারিখ',
                'processed_by': 'প্রক্রিয়াকারী',
                'processing_time': 'প্রক্রিয়াকরণ সময়',
                'validation_summary': 'যাচাইকরণ সারাংশ',
                'severity_breakdown': 'তীব্রতা বিভাজন',
                'passed_rules': 'উত্তীর্ণ নিয়ম',
                'failed_rules': 'অনুত্তীর্ণ নিয়ম',
                'warnings': 'সতর্কতা',
                'critical_issues': 'গুরুত্বপূর্ণ সমস্যা',
                'major_issues': 'প্রধান সমস্যা',
                'minor_issues': 'ছোট সমস্যা',
                'rules_passed_desc': 'সফলভাবে যাচাইকৃত নিয়ম',
                'rules_failed_desc': 'ব্যর্থ হওয়া নিয়ম',
                'warnings_desc': 'পর্যালোচনা প্রয়োজন',
                'discrepancies': 'বিসংগতি',
                'discrepancies_found': 'পাওয়া বিসংগতিসমূহ',
                'no_discrepancies': 'কোনো বিসংগতি পাওয়া যায়নি।',
                'no_discrepancies_title': 'কোনো বিসংগতি নেই!',
                'no_discrepancies_message': 'সকল যাচাইকরণ নিয়ম সফলভাবে পাস করেছে।',
                'expected': 'প্রত্যাশিত',
                'actual': 'প্রকৃত',
                'expected_value': 'প্রত্যাশিত মান',
                'actual_value': 'প্রকৃত মান',
                'confidence': 'আস্থা',
                'critical': 'গুরুত্বপূর্ণ',
                'major': 'প্রধান',
                'minor': 'ছোট',
                'cross_check_matrix': 'ক্রস-চেক ম্যাট্রিক্স',
                'matrix_description': 'বিভিন্ন নথিতে ক্ষেত্রের মানের তুলনা',
                'field_name': 'ক্ষেত্রের নাম',
                'letter_of_credit': 'এলসি',
                'commercial_invoice': 'বাণিজ্যিক ইনভয়েস',
                'bill_of_lading': 'পরিবহন রসিদ',
                'consistency_status': 'সামঞ্জস্য অবস্থা',
                'status': 'অবস্থা',
                'consistent': 'সামঞ্জস্যপূর্ণ',
                'inconsistent': 'অসামঞ্জস্যপূর্ণ',
                'not_available': 'উপলব্ধ নয়',
                'generated_by': 'প্রস্তুতকারী',
                'ai_powered': 'এআই চালিত এলসি যাচাইকরণ প্ল্যাটফর্ম',
                'disclaimer': 'এই প্রতিবেদনটি স্বয়ংক্রিয় যাচাইয়ের জন্য। চূড়ান্ত সিদ্ধান্তের জন্য বিশেষজ্ঞের পরামর্শ নিন।',
                'report_generated_at': 'প্রতিবেদন তৈরির সময়',
                'report_version': 'প্রতিবেদনের সংস্করণ',
                'verified_by': 'যাচাইকারী',
                'date': 'তারিখ',
                # Document type labels
                'doc_letter_of_credit': 'এলসি',
                'doc_commercial_invoice': 'বাণিজ্যিক ইনভয়েস',
                'doc_bill_of_lading': 'পরিবহন রসিদ',
                'doc_packing_list': 'প্যাকিং তালিকা',
            }
        else:
            return {
                'report_title': 'Letter of Credit Validation Report',
                'session_id': 'Session ID',
                'generated_on': 'Generated on',
                'processed_by': 'Processed by',
                'processing_time': 'Processing Time',
                'validation_summary': 'Validation Summary',
                'severity_breakdown': 'Severity Breakdown',
                'passed_rules': 'Passed Rules',
                'failed_rules': 'Failed Rules',
                'warnings': 'Warnings',
                'critical_issues': 'Critical Issues',
                'major_issues': 'Major Issues',
                'minor_issues': 'Minor Issues',
                'rules_passed_desc': 'Rules successfully validated',
                'rules_failed_desc': 'Rules that failed validation',
                'warnings_desc': 'Items requiring review',
                'discrepancies': 'Discrepancies',
                'discrepancies_found': 'Discrepancies Found',
                'no_discrepancies': 'No discrepancies found.',
                'no_discrepancies_title': 'No Discrepancies Found!',
                'no_discrepancies_message': 'All validation rules passed successfully.',
                'expected': 'Expected',
                'actual': 'Actual',
                'expected_value': 'Expected Value',
                'actual_value': 'Actual Value',
                'confidence': 'Confidence',
                'critical': 'Critical',
                'major': 'Major',
                'minor': 'Minor',
                'cross_check_matrix': 'Cross-Check Matrix',
                'matrix_description': 'Comparison of field values across documents',
                'field_name': 'Field Name',
                'letter_of_credit': 'Letter of Credit',
                'commercial_invoice': 'Commercial Invoice',
                'bill_of_lading': 'Bill of Lading',
                'consistency_status': 'Consistency Status',
                'status': 'Status',
                'consistent': 'Consistent',
                'inconsistent': 'Inconsistent',
                'not_available': 'N/A',
                'generated_by': 'Generated by',
                'ai_powered': 'AI-powered LC validation platform',
                'disclaimer': 'This report is for automated validation purposes. Consult experts for final decisions.',
                'report_generated_at': 'Report generated at',
                'report_version': 'Report version',
                'verified_by': 'Verified by',
                'date': 'Date',
                # Document type labels
                'doc_letter_of_credit': 'LC',
                'doc_commercial_invoice': 'Invoice',
                'doc_bill_of_lading': 'B/L',
                'doc_packing_list': 'Packing List',
            }
    
    
    
    
