"""
Verdict Calculator

Calculates bank submission verdict based on issues.
"""

from typing import List, Dict, Any
from ..core.types import (
    Issue, Verdict, VerdictStatus, IssueSeverity,
    IssueSummary, ActionItem, SanctionsStatus
)


class VerdictCalculator:
    """
    Calculate bank submission verdict.
    
    SUBMIT: Ready to submit, no issues or minor only
    CAUTION: Some issues but likely to pass
    HOLD: Significant issues, review needed
    REJECT: Will definitely be rejected
    """
    
    # Typical discrepancy fees by region
    DISCREPANCY_FEES = {
        "default": 75,  # USD per discrepancy
        "asia": 50,
        "europe": 100,
        "us": 150,
    }
    
    def calculate(
        self,
        issues: List[Issue],
        sanctions_status: SanctionsStatus,
        extraction_confidence: float = 1.0,
    ) -> Verdict:
        """Calculate verdict from issues."""
        
        # Count issues by severity
        summary = IssueSummary(
            critical=sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL),
            major=sum(1 for i in issues if i.severity == IssueSeverity.MAJOR),
            minor=sum(1 for i in issues if i.severity == IssueSeverity.MINOR),
            info=sum(1 for i in issues if i.severity == IssueSeverity.INFO),
        )
        
        # Determine verdict
        status, message, recommendation = self._determine_verdict(
            summary, sanctions_status, extraction_confidence
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            summary, sanctions_status, extraction_confidence
        )
        
        # Generate action items
        action_items = self._generate_action_items(issues)
        
        # Estimate discrepancy fee
        fee = self._estimate_fee(summary)
        
        # Can submit?
        can_submit = status in [VerdictStatus.SUBMIT, VerdictStatus.CAUTION]
        will_reject = status == VerdictStatus.REJECT
        
        return Verdict(
            status=status,
            message=message,
            recommendation=recommendation,
            confidence=confidence,
            can_submit_to_bank=can_submit,
            will_be_rejected=will_reject,
            estimated_discrepancy_fee=fee,
            issue_summary=summary,
            action_items=action_items,
        )
    
    def _determine_verdict(
        self,
        summary: IssueSummary,
        sanctions: SanctionsStatus,
        confidence: float,
    ) -> tuple[VerdictStatus, str, str]:
        """Determine verdict status."""
        
        # Sanctions block
        if sanctions.status == "blocked":
            return (
                VerdictStatus.REJECT,
                "Sanctions match detected - cannot proceed",
                "Obtain compliance clearance before any further action"
            )
        
        # Critical issues = rejection
        if summary.critical > 0:
            return (
                VerdictStatus.REJECT,
                f"{summary.critical} critical discrepanc{'y' if summary.critical == 1 else 'ies'} found",
                "Address all critical issues before submission to avoid rejection and fees"
            )
        
        # Multiple major issues = hold
        if summary.major >= 3:
            return (
                VerdictStatus.HOLD,
                f"{summary.major} major issues require attention",
                "Review and correct major issues - high rejection risk"
            )
        
        # Some major issues = caution
        if summary.major > 0:
            return (
                VerdictStatus.CAUTION,
                f"{summary.major} issue{'s' if summary.major > 1 else ''} may cause discrepancy",
                "Consider correcting before submission to avoid potential fees"
            )
        
        # Minor issues only
        if summary.minor > 0:
            return (
                VerdictStatus.SUBMIT,
                f"Ready to submit ({summary.minor} minor note{'s' if summary.minor > 1 else ''})",
                "Documents are compliant - minor notes for your reference"
            )
        
        # Low extraction confidence
        if confidence < 0.8:
            return (
                VerdictStatus.CAUTION,
                "Ready but extraction confidence is low",
                "Review extracted data carefully before submission"
            )
        
        # All clear
        return (
            VerdictStatus.SUBMIT,
            "Documents are compliant - ready to submit",
            "No discrepancies found - proceed with presentation"
        )
    
    def _calculate_confidence(
        self,
        summary: IssueSummary,
        sanctions: SanctionsStatus,
        extraction_confidence: float,
    ) -> float:
        """Calculate verdict confidence."""
        
        # Start with extraction confidence
        base = extraction_confidence
        
        # Reduce for sanctions uncertainty
        if sanctions.status == "potential_match":
            base *= 0.8
        
        # Reduce for many issues (might have missed some)
        if summary.total > 5:
            base *= 0.9
        
        return round(min(1.0, base), 2)
    
    def _generate_action_items(
        self,
        issues: List[Issue],
    ) -> List[ActionItem]:
        """Generate prioritized action items."""
        items = []
        
        # Critical first
        for issue in issues:
            if issue.severity == IssueSeverity.CRITICAL:
                items.append(ActionItem(
                    priority="critical",
                    issue=issue.title,
                    action=issue.suggestion,
                ))
        
        # Then major
        for issue in issues:
            if issue.severity == IssueSeverity.MAJOR:
                items.append(ActionItem(
                    priority="high",
                    issue=issue.title,
                    action=issue.suggestion,
                ))
        
        # Limit to top 5
        return items[:5]
    
    def _estimate_fee(self, summary: IssueSummary) -> float:
        """Estimate potential discrepancy fees."""
        base_fee = self.DISCREPANCY_FEES["default"]
        
        # Critical and major issues typically incur fees
        discrepancy_count = summary.critical + summary.major
        
        return discrepancy_count * base_fee

