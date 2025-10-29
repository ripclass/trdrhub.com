#!/usr/bin/env python3
"""
Output Layer for LCopilot Compliance Results
Converts technical compliance results into SME-friendly plain English
and bank-specific formal language for different audiences.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class OutputLayer:
    """Main output layer class for formatting compliance results"""

    def __init__(self):
        self.mode = OutputMode.PLAIN_ENGLISH

    def to_plain_english(self, compliance_result: Dict[str, Any]) -> str:
        """Convert compliance result to plain English summary"""
        # Simple mock implementation for demo
        score = compliance_result.get('compliance_score', 0) * 100
        failed_rules = [r for r in compliance_result.get('validated_rules', []) if r.get('status') == 'fail']

        summary = f"Your LC scored {score:.1f}% compliance.\n\n"

        if score >= 80:
            summary += "✅ Great news! Your LC is highly compliant and should process smoothly.\n\n"
        elif score >= 60:
            summary += "⚠️ Your LC is moderately compliant but has some issues that need attention.\n\n"
        else:
            summary += "❌ Your LC has significant compliance issues that must be addressed.\n\n"

        if failed_rules:
            summary += "Issues found:\n"
            for rule in failed_rules:
                summary += f"• {rule.get('description', 'Unknown issue')}: {rule.get('details', 'No details available')}\n"
                if rule.get('suggested_fix'):
                    summary += f"  → Fix: {rule.get('suggested_fix')}\n"

        return summary

    def to_bank_style(self, compliance_result: Dict[str, Any], bank: str = "default") -> str:
        """Convert compliance result to formal banking language"""
        return format_to_bank_style(compliance_result, bank)

    def to_sme_summary(self, compliance_result: Dict[str, Any]) -> str:
        """Convert compliance result to SME-friendly summary"""
        return format_to_sme_summary(compliance_result)


class OutputMode(Enum):
    PLAIN_ENGLISH = "plain_english"
    BANK_FORMAL = "bank_formal"
    TECHNICAL = "technical"
    SME_SUMMARY = "sme_summary"


class SeverityLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OutputFormatter:
    """Formats compliance results for different audiences"""

    def __init__(self):
        # Templates for different output modes
        self.templates = {
            "score_excellent": {
                OutputMode.PLAIN_ENGLISH: "✅ Excellent! Your Letter of Credit is fully compliant.",
                OutputMode.BANK_FORMAL: "The presented Letter of Credit meets all regulatory requirements.",
                OutputMode.SME_SUMMARY: "Your LC is ready to process - no issues found."
            },
            "score_good": {
                OutputMode.PLAIN_ENGLISH: "✅ Good! Your LC is mostly compliant with minor warnings.",
                OutputMode.BANK_FORMAL: "The Letter of Credit is acceptable with minor advisory notes.",
                OutputMode.SME_SUMMARY: "Your LC will process smoothly with minor recommendations."
            },
            "score_fair": {
                OutputMode.PLAIN_ENGLISH: "⚠️ Your LC has some issues that should be addressed.",
                OutputMode.BANK_FORMAL: "The Letter of Credit contains discrepancies requiring attention.",
                OutputMode.SME_SUMMARY: "Your LC needs some fixes before processing."
            },
            "score_poor": {
                OutputMode.PLAIN_ENGLISH: "❌ Your LC has serious problems that must be fixed.",
                OutputMode.BANK_FORMAL: "The Letter of Credit is rejected due to critical discrepancies.",
                OutputMode.SME_SUMMARY: "Your LC has major issues that will prevent processing."
            }
        }

        # Bank-specific terminology
        self.bank_terminology = {
            "standard_chartered": {
                "rejection_phrase": "Document discrepancy noted under UCP 600 guidelines",
                "approval_phrase": "Documents appear in order for negotiation",
                "warning_phrase": "Advisory notice for future presentations"
            },
            "hsbc": {
                "rejection_phrase": "Discrepancy identified - presentation does not comply",
                "approval_phrase": "Complying presentation received",
                "warning_phrase": "Attention required for compliance enhancement"
            },
            "default": {
                "rejection_phrase": "Document discrepancy identified",
                "approval_phrase": "Documents comply with LC terms",
                "warning_phrase": "Minor compliance advisory noted"
            }
        }

        # SME-friendly explanations
        self.sme_explanations = {
            "date_logic": "The dates in your LC don't make sense - shipment date should be before expiry date",
            "amount_limit": "The invoice amount is higher than what's allowed in your LC",
            "missing_documents": "Some required documents are not specified in your LC",
            "address_format": "The addresses need to be more complete for bank processing",
            "currency_mismatch": "The currency should be consistent throughout your LC",
            "hs_code_invalid": "The product classification code (HS code) needs to be corrected",
            "presentation_period": "The time allowed for presenting documents should be 21 days or less",
            "insurance_coverage": "Insurance coverage should be 110% of the shipment value",
            "certificate_origin": "Certificate of origin requirements need to specify the issuing authority"
        }

    def to_plain_english(self, compliance_result: Dict[str, Any]) -> str:
        """Convert compliance result to plain English for SMEs"""
        output = []

        # Overall assessment
        score = compliance_result.get("compliance_score", 0.0)
        overall_assessment = self._get_score_assessment(score, OutputMode.PLAIN_ENGLISH)
        output.append(overall_assessment)
        output.append("")

        # Compliance score explanation
        score_percentage = int(score * 100)
        output.append(f"📊 **Compliance Score: {score_percentage}%**")

        if score >= 0.9:
            output.append("Your LC meets all international banking standards!")
        elif score >= 0.7:
            output.append("Your LC is in good shape with room for minor improvements.")
        elif score >= 0.5:
            output.append("Your LC needs some attention to avoid processing delays.")
        else:
            output.append("Your LC requires significant changes before it can be processed.")

        output.append("")

        # Issues breakdown in plain language
        violations = compliance_result.get("validated_rules", [])
        if violations:
            critical_issues = [v for v in violations if v.get("status", "").lower() == "fail" and v.get("severity") in ["critical", "high"]]
            warnings = [v for v in violations if v.get("status", "").lower() in ["warning", "fail"] and v.get("severity") in ["medium", "low"]]

            if critical_issues:
                output.append("🚨 **Critical Issues (Must Fix):**")
                for issue in critical_issues:
                    explanation = self._translate_to_plain_english(issue)
                    output.append(f"• {explanation}")
                output.append("")

            if warnings:
                output.append("⚠️ **Recommendations (Should Fix):**")
                for warning in warnings[:5]:  # Limit to top 5 warnings
                    explanation = self._translate_to_plain_english(warning)
                    output.append(f"• {explanation}")
                output.append("")

        # Free tier upsell
        if compliance_result.get("upsell_triggered", False):
            output.append("🎯 **Unlock Full Analysis**")
            output.append("You've used your free compliance checks. Upgrade to Pro for:")
            output.append("• Unlimited LC validations")
            output.append("• Detailed compliance reports")
            output.append("• Priority customer support")
            output.append("• Evidence packs for bank submissions")
            output.append("")

        # Next steps
        output.append("📋 **What to do next:**")
        if score >= 0.9:
            output.append("• Your LC is ready to submit to the bank")
            output.append("• Keep a copy of this analysis for your records")
        elif score >= 0.7:
            output.append("• Review the recommendations above")
            output.append("• Make minor adjustments if needed")
            output.append("• Your LC should process smoothly")
        else:
            output.append("• Fix the critical issues listed above")
            output.append("• Re-check your LC after making changes")
            output.append("• Consider consulting with your trade finance advisor")

        return "\n".join(output)

    def to_bank_style(self, compliance_result: Dict[str, Any], bank: str = "default") -> str:
        """Convert compliance result to formal bank language"""
        output = []

        # Bank header
        bank_name = bank.replace("_", " ").title()
        output.append(f"**{bank_name} Letter of Credit Examination Report**")
        output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        output.append("")

        # Overall determination
        score = compliance_result.get("compliance_score", 0.0)
        overall_status = compliance_result.get("overall_status", "UNKNOWN")

        bank_terms = self.bank_terminology.get(bank, self.bank_terminology["default"])

        if score >= 0.9 and overall_status != "FAIL":
            output.append(f"**DETERMINATION: COMPLYING PRESENTATION**")
            output.append(bank_terms["approval_phrase"])
        elif score >= 0.5:
            output.append(f"**DETERMINATION: DISCREPANT PRESENTATION**")
            output.append(bank_terms["rejection_phrase"])
        else:
            output.append(f"**DETERMINATION: NON-COMPLYING PRESENTATION**")
            output.append(bank_terms["rejection_phrase"])

        output.append("")

        # Document examination details
        output.append("**EXAMINATION DETAILS:**")
        output.append(f"• Total rules examined: {compliance_result.get('total_rules_checked', 0)}")
        output.append(f"• Rules passed: {compliance_result.get('rules_passed', 0)}")
        output.append(f"• Rules failed: {compliance_result.get('rules_failed', 0)}")
        output.append(f"• Compliance score: {score:.3f}")
        output.append("")

        # Specific discrepancies
        violations = compliance_result.get("validated_rules", [])
        if violations:
            critical_issues = [v for v in violations if v.get("status", "").lower() == "fail"]
            warnings = [v for v in violations if v.get("status", "").lower() == "warning"]

            if critical_issues:
                output.append("**DISCREPANCIES NOTED:**")
                for i, issue in enumerate(critical_issues, 1):
                    rule_ref = issue.get("rule_number", issue.get("rule_id", ""))
                    details = issue.get("details", "Compliance issue identified")
                    bank_impact = issue.get("bank_impact", "")

                    output.append(f"{i}. **{rule_ref}**: {details}")
                    if bank_impact:
                        output.append(f"   Impact: {bank_impact}")

                output.append("")

            if warnings:
                output.append("**ADVISORY NOTICES:**")
                for warning in warnings:
                    rule_ref = warning.get("rule_number", warning.get("rule_id", ""))
                    details = warning.get("details", "Advisory notice")
                    output.append(f"• **{rule_ref}**: {details}")
                output.append("")

        # Regulatory framework
        output.append("**REGULATORY FRAMEWORK:**")
        rule_versions = compliance_result.get("rule_versions", {})
        if rule_versions:
            for standard, version in rule_versions.items():
                output.append(f"• {standard.upper()}: Version {version}")
        else:
            output.append("• UCP 600 (Uniform Customs and Practice for Documentary Credits)")
            output.append("• ISBP (International Standard Banking Practice)")

        output.append("")

        # Bank-specific footer
        tier_used = compliance_result.get("tier_used", "unknown")
        engine_version = compliance_result.get("engine_version", "unknown")

        output.append("**SYSTEM INFORMATION:**")
        output.append(f"• Examination tier: {tier_used.upper()}")
        output.append(f"• Engine version: {engine_version}")
        output.append(f"• Validation timestamp: {compliance_result.get('validation_timestamp', 'N/A')}")

        if compliance_result.get("upsell_triggered", False):
            output.append("")
            output.append("**NOTE:** Full examination requires Pro or Enterprise tier subscription.")

        return "\n".join(output)

    def to_sme_summary(self, compliance_result: Dict[str, Any]) -> str:
        """Convert to brief SME summary for dashboard display"""
        score = compliance_result.get("compliance_score", 0.0)
        violations = compliance_result.get("validated_rules", [])

        failed_rules = len([v for v in violations if v.get("status", "").lower() == "fail"])
        warning_rules = len([v for v in violations if v.get("status", "").lower() == "warning"])

        summary = []

        # Quick status
        if score >= 0.9 and failed_rules == 0:
            summary.append("✅ **Ready to Submit** - No critical issues found")
        elif score >= 0.7:
            summary.append("⚠️ **Minor Issues** - Mostly compliant, few recommendations")
        elif score >= 0.5:
            summary.append("🔄 **Needs Attention** - Several issues to resolve")
        else:
            summary.append("❌ **Major Problems** - Significant changes required")

        # Quick stats
        summary.append(f"**Score:** {int(score * 100)}% | **Issues:** {failed_rules} critical, {warning_rules} minor")

        # Top issue if any
        if failed_rules > 0:
            top_issue = next((v for v in violations if v.get("status", "").lower() == "fail"), None)
            if top_issue:
                explanation = self._translate_to_plain_english(top_issue, brief=True)
                summary.append(f"**Top Issue:** {explanation}")

        # Upsell
        if compliance_result.get("upsell_triggered", False):
            summary.append("🎯 **Upgrade for unlimited checks and detailed reports**")

        return "\n".join(summary)

    def _get_score_assessment(self, score: float, mode: OutputMode) -> str:
        """Get overall assessment based on score"""
        if score >= 0.9:
            return self.templates["score_excellent"][mode]
        elif score >= 0.7:
            return self.templates["score_good"][mode]
        elif score >= 0.5:
            return self.templates["score_fair"][mode]
        else:
            return self.templates["score_poor"][mode]

    def _translate_to_plain_english(self, violation: Dict[str, Any], brief: bool = False) -> str:
        """Translate technical violation to plain English"""
        rule_id = violation.get("rule_id", "").lower()
        details = violation.get("details", "")
        suggested_fix = violation.get("suggested_fix", "")

        # Try to match common patterns
        for pattern, explanation in self.sme_explanations.items():
            if pattern in rule_id or pattern in details.lower():
                if brief:
                    return explanation
                return f"{explanation}. {suggested_fix}" if suggested_fix else explanation

        # Fallback to simplified technical details
        simplified_details = details.replace("UCP600", "banking rules").replace("ISBP", "document standards")

        if brief:
            return simplified_details[:100] + "..." if len(simplified_details) > 100 else simplified_details

        result = simplified_details
        if suggested_fix:
            result += f" **Fix:** {suggested_fix}"

        return result

    def format_for_email(self, compliance_result: Dict[str, Any], recipient_type: str = "sme") -> Dict[str, str]:
        """Format compliance result for email delivery"""
        if recipient_type == "bank":
            subject = f"LC Examination Report - {compliance_result.get('lc_reference', 'Unknown')}"
            body = self.to_bank_style(compliance_result)
        else:
            score = compliance_result.get("compliance_score", 0.0)
            lc_ref = compliance_result.get("lc_reference", "Your LC")

            if score >= 0.9:
                subject = f"✅ {lc_ref} - Ready to Submit"
            elif score >= 0.7:
                subject = f"⚠️ {lc_ref} - Minor Issues Found"
            else:
                subject = f"❌ {lc_ref} - Action Required"

            body = self.to_plain_english(compliance_result)

        return {
            "subject": subject,
            "body": body,
            "html": self._convert_to_html(body)
        }

    def _convert_to_html(self, text: str) -> str:
        """Convert markdown-style text to HTML for email"""
        html = text.replace("\n", "<br>\n")
        html = html.replace("**", "<strong>").replace("**", "</strong>")
        html = html.replace("✅", "✅").replace("❌", "❌").replace("⚠️", "⚠️")
        html = html.replace("• ", "• ")

        return f"<div style='font-family: Arial, sans-serif; line-height: 1.6;'>{html}</div>"


def to_plain_english(compliance_result: Dict[str, Any]) -> str:
    """
    Convert compliance result to plain English for SMEs

    Args:
        compliance_result: Dictionary containing compliance validation results

    Returns:
        String formatted in plain English for SME consumption
    """
    formatter = OutputFormatter()
    return formatter.to_plain_english(compliance_result)


def to_bank_style(compliance_result: Dict[str, Any], bank: str = "default") -> str:
    """
    Convert compliance result to formal bank language

    Args:
        compliance_result: Dictionary containing compliance validation results
        bank: Bank identifier for specific terminology (default, hsbc, standard_chartered)

    Returns:
        String formatted in formal banking language
    """
    formatter = OutputFormatter()
    return formatter.to_bank_style(compliance_result, bank)


def to_sme_summary(compliance_result: Dict[str, Any]) -> str:
    """
    Convert compliance result to brief SME summary

    Args:
        compliance_result: Dictionary containing compliance validation results

    Returns:
        Brief summary string for dashboard display
    """
    formatter = OutputFormatter()
    return formatter.to_sme_summary(compliance_result)


def demo_output_formats():
    """Demonstrate different output formats"""
    # Sample compliance result
    sample_result = {
        "lc_reference": "LC2024-DEMO-001",
        "compliance_score": 0.75,
        "overall_status": "WARNING",
        "total_rules_checked": 15,
        "rules_passed": 10,
        "rules_failed": 2,
        "rules_warnings": 3,
        "validated_rules": [
            {
                "rule_id": "UCP600-6",
                "rule_number": "UCP600-6",
                "status": "fail",
                "severity": "high",
                "details": "Expiry place not specified in Letter of Credit",
                "suggested_fix": "Add expiry place such as 'counters of issuing bank'",
                "bank_impact": "LC may be rejected for incomplete terms"
            },
            {
                "rule_id": "BD-002",
                "rule_number": "BD-002",
                "status": "warning",
                "severity": "medium",
                "details": "Currency consistency - EUR not standard for Bangladesh imports",
                "suggested_fix": "Consider using USD for better processing",
                "trade_impact": "May cause foreign exchange complications"
            }
        ],
        "validation_timestamp": "2024-01-15T10:30:00Z",
        "engine_version": "2.0.0",
        "tier_used": "pro"
    }

    formatter = OutputFormatter()

    print("=" * 60)
    print("PLAIN ENGLISH FORMAT (for SMEs)")
    print("=" * 60)
    print(formatter.to_plain_english(sample_result))

    print("\n" + "=" * 60)
    print("BANK FORMAL FORMAT")
    print("=" * 60)
    print(formatter.to_bank_style(sample_result))

    print("\n" + "=" * 60)
    print("SME SUMMARY FORMAT (for dashboard)")
    print("=" * 60)
    print(formatter.to_sme_summary(sample_result))

    print("\n" + "=" * 60)
    print("EMAIL FORMAT")
    print("=" * 60)
    email_format = formatter.format_for_email(sample_result, "sme")
    print(f"Subject: {email_format['subject']}")
    print(f"Body: {email_format['body'][:200]}...")


if __name__ == "__main__":
    demo_output_formats()