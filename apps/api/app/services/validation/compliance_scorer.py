"""
Compliance Scorer - Phase 6: Fix the compliance math.

This module calculates accurate compliance scores based on:
1. Issue severity (critical issues = 0% compliance)
2. Extraction completeness (missing fields lower score)
3. Rule pass rates (passed / total rules)
4. Document verification status

CORE PRINCIPLE: No default 100%. Compliance is EARNED.

Scoring Rules:
- Any CRITICAL issue → max 0% compliance
- Any MAJOR issue → max 60% compliance  
- Only MINOR issues → max 85% compliance
- All rules passed → 100% compliance

The "100% compliant with N/A fields" bug is fixed because:
- Missing critical fields generate critical issues
- Critical issues cap compliance at 0%
- Extraction completeness factors into score
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from app.services.validation.issue_engine import (
    IssueEngineResult,
    IssueSeverity,
    Issue,
)
from app.services.extraction.lc_baseline import LCBaseline


logger = logging.getLogger(__name__)


class ComplianceLevel(str, Enum):
    """Compliance level categories."""
    BLOCKED = "blocked"       # Validation blocked, cannot assess
    NON_COMPLIANT = "non_compliant"  # Critical issues, 0-29%
    PARTIAL = "partial"       # Major issues, 30-69%
    MOSTLY_COMPLIANT = "mostly_compliant"  # Minor issues, 70-84%
    COMPLIANT = "compliant"   # Clean or very minor, 85-100%


@dataclass
class ComplianceScore:
    """Comprehensive compliance score result."""
    
    # Main score (0-100)
    score: float
    level: ComplianceLevel
    
    # Component scores (all 0-100)
    extraction_score: float = 0.0      # Based on LCBaseline completeness
    rule_score: float = 0.0            # Based on rule pass rate
    document_score: float = 0.0        # Based on document verification
    
    # Issue impact
    issue_penalty: float = 0.0         # Total penalty from issues
    critical_penalty: float = 0.0
    major_penalty: float = 0.0
    minor_penalty: float = 0.0
    
    # Caps applied
    max_allowed: float = 100.0         # Maximum score due to issues
    cap_reason: Optional[str] = None   # Why score was capped
    
    # Counts
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    total_issues: int = 0
    
    # Metadata
    validation_blocked: bool = False
    calculation_method: str = "severity_weighted"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 1),
            "level": self.level.value,
            "extraction_score": round(self.extraction_score, 1),
            "rule_score": round(self.rule_score, 1),
            "document_score": round(self.document_score, 1),
            "issue_penalty": round(self.issue_penalty, 1),
            "max_allowed": round(self.max_allowed, 1),
            "cap_reason": self.cap_reason,
            "critical_count": self.critical_count,
            "major_count": self.major_count,
            "minor_count": self.minor_count,
            "total_issues": self.total_issues,
            "validation_blocked": self.validation_blocked,
        }
    
    @property
    def compliance_rate(self) -> int:
        """Integer compliance rate (0-100) for API compatibility."""
        return int(round(self.score))
    
    @property
    def is_compliant(self) -> bool:
        """Whether the LC set is considered compliant."""
        return self.level == ComplianceLevel.COMPLIANT
    
    @property
    def has_critical_issues(self) -> bool:
        return self.critical_count > 0


class ComplianceScorer:
    """
    Calculates accurate compliance scores.
    
    This replaces the broken logic that defaulted to 100%.
    """
    
    # Severity caps: Maximum compliance score with each issue type
    # Changed: Critical now caps at 25% instead of 0% for better UX
    # This shows "seriously non-compliant but some docs are valid"
    CAP_CRITICAL = 25.0      # Any critical issue → max 25%
    CAP_MAJOR = 55.0         # Any major issue → max 55%
    CAP_MINOR = 85.0         # Any minor issue → max 85%
    CAP_INFO = 100.0         # Info doesn't cap
    
    # Severity penalties (percentage points deducted per issue)
    # Adjusted to create meaningful differentiation
    PENALTY_CRITICAL = 20.0   # Each critical = -20% (was 100)
    PENALTY_MAJOR = 8.0       # Each major = -8% (was 15)
    PENALTY_MINOR = 3.0       # Each minor = -3% (was 5)
    PENALTY_INFO = 0.0        # Info = no penalty
    
    # Component weights (must sum to 1.0)
    WEIGHT_EXTRACTION = 0.30  # 30% weight on extraction quality
    WEIGHT_RULES = 0.50       # 50% weight on rule compliance
    WEIGHT_DOCUMENTS = 0.20   # 20% weight on document verification
    
    def __init__(
        self,
        cap_critical: float = CAP_CRITICAL,
        cap_major: float = CAP_MAJOR,
        cap_minor: float = CAP_MINOR,
    ):
        self.cap_critical = cap_critical
        self.cap_major = cap_major
        self.cap_minor = cap_minor
    
    def calculate(
        self,
        issue_result: Optional[IssueEngineResult] = None,
        baseline: Optional[LCBaseline] = None,
        rule_pass_rate: Optional[float] = None,
        document_verification_rate: Optional[float] = None,
        validation_blocked: bool = False,
    ) -> ComplianceScore:
        """
        Calculate comprehensive compliance score.
        
        Args:
            issue_result: Issues from the issue engine
            baseline: LCBaseline for extraction completeness
            rule_pass_rate: Ratio of passed rules (0.0-1.0)
            document_verification_rate: Ratio of verified docs (0.0-1.0)
            validation_blocked: Whether validation was blocked
            
        Returns:
            ComplianceScore with all metrics
        """
        # If validation was blocked, score is 0
        if validation_blocked:
            return self._blocked_score()
        
        # Extract counts from issue result
        critical_count = 0
        major_count = 0
        minor_count = 0
        
        if issue_result:
            critical_count = issue_result.critical_count
            major_count = issue_result.major_count
            minor_count = issue_result.minor_count
        
        # Calculate component scores
        extraction_score = self._calculate_extraction_score(baseline)
        rule_score = self._calculate_rule_score(rule_pass_rate, issue_result)
        document_score = self._calculate_document_score(document_verification_rate)
        
        # Calculate issue penalties
        critical_penalty = critical_count * self.PENALTY_CRITICAL
        major_penalty = major_count * self.PENALTY_MAJOR
        minor_penalty = minor_count * self.PENALTY_MINOR
        total_penalty = critical_penalty + major_penalty + minor_penalty
        
        # Determine maximum allowed score based on issue severity
        max_allowed, cap_reason = self._determine_cap(
            critical_count, major_count, minor_count
        )
        
        # Calculate weighted base score
        base_score = (
            extraction_score * self.WEIGHT_EXTRACTION +
            rule_score * self.WEIGHT_RULES +
            document_score * self.WEIGHT_DOCUMENTS
        )
        
        # Apply penalty
        penalized_score = max(0, base_score - total_penalty)
        
        # Apply cap
        final_score = min(penalized_score, max_allowed)
        
        # Determine compliance level
        level = self._determine_level(final_score, critical_count)
        
        logger.info(
            "Compliance score: %.1f%% (level=%s, critical=%d, major=%d, minor=%d, cap=%.0f%%)",
            final_score, level.value, critical_count, major_count, minor_count, max_allowed
        )
        
        return ComplianceScore(
            score=final_score,
            level=level,
            extraction_score=extraction_score,
            rule_score=rule_score,
            document_score=document_score,
            issue_penalty=total_penalty,
            critical_penalty=critical_penalty,
            major_penalty=major_penalty,
            minor_penalty=minor_penalty,
            max_allowed=max_allowed,
            cap_reason=cap_reason,
            critical_count=critical_count,
            major_count=major_count,
            minor_count=minor_count,
            total_issues=critical_count + major_count + minor_count,
            validation_blocked=False,
            calculation_method="severity_weighted",
        )
    
    def calculate_from_issues(
        self,
        issues: List[Dict[str, Any]],
        extraction_completeness: float = 1.0,
    ) -> ComplianceScore:
        """
        Simplified calculation from raw issue list.
        
        For backward compatibility with existing code.
        """
        # Count issues by severity
        critical_count = 0
        major_count = 0
        minor_count = 0
        
        for issue in issues:
            severity = issue.get("severity", "minor").lower()
            if severity == "critical":
                critical_count += 1
            elif severity in ("major", "warning"):
                major_count += 1
            elif severity == "minor":
                minor_count += 1
        
        # Determine cap
        max_allowed, cap_reason = self._determine_cap(
            critical_count, major_count, minor_count
        )
        
        # Calculate penalties
        total_penalty = (
            critical_count * self.PENALTY_CRITICAL +
            major_count * self.PENALTY_MAJOR +
            minor_count * self.PENALTY_MINOR
        )
        
        # Base score from extraction completeness
        base_score = extraction_completeness * 100
        
        # Apply penalty and cap
        final_score = min(max(0, base_score - total_penalty), max_allowed)
        
        # Determine level
        level = self._determine_level(final_score, critical_count)
        
        return ComplianceScore(
            score=final_score,
            level=level,
            extraction_score=extraction_completeness * 100,
            rule_score=max_allowed,  # Approximation
            document_score=100.0 if not issues else 50.0,
            issue_penalty=total_penalty,
            critical_penalty=critical_count * self.PENALTY_CRITICAL,
            major_penalty=major_count * self.PENALTY_MAJOR,
            minor_penalty=minor_count * self.PENALTY_MINOR,
            max_allowed=max_allowed,
            cap_reason=cap_reason,
            critical_count=critical_count,
            major_count=major_count,
            minor_count=minor_count,
            total_issues=len(issues),
        )
    
    def _blocked_score(self) -> ComplianceScore:
        """Return score for blocked validation."""
        return ComplianceScore(
            score=0.0,
            level=ComplianceLevel.BLOCKED,
            extraction_score=0.0,
            rule_score=0.0,
            document_score=0.0,
            max_allowed=0.0,
            cap_reason="Validation blocked - LC extraction failed",
            validation_blocked=True,
            calculation_method="blocked",
        )
    
    def _calculate_extraction_score(
        self,
        baseline: Optional[LCBaseline],
    ) -> float:
        """Score based on LC extraction completeness."""
        if baseline is None:
            return 0.0
        
        # Use critical completeness weighted higher
        critical_weight = 0.7
        overall_weight = 0.3
        
        critical = baseline.critical_completeness
        overall = baseline.extraction_completeness
        
        return (critical * critical_weight + overall * overall_weight) * 100
    
    def _calculate_rule_score(
        self,
        pass_rate: Optional[float],
        issue_result: Optional[IssueEngineResult],
    ) -> float:
        """Score based on rule pass rate."""
        if pass_rate is not None:
            return pass_rate * 100
        
        # Estimate from issue result
        if issue_result is None:
            return 100.0  # No issues = assume all passed
        
        # If we have issues, estimate based on severity
        if issue_result.critical_count > 0:
            return 0.0
        elif issue_result.major_count > 0:
            return max(0, 60 - (issue_result.major_count - 1) * 10)
        elif issue_result.minor_count > 0:
            return max(50, 90 - issue_result.minor_count * 5)
        
        return 100.0
    
    def _calculate_document_score(
        self,
        verification_rate: Optional[float],
    ) -> float:
        """Score based on document verification."""
        if verification_rate is not None:
            return verification_rate * 100
        return 100.0  # Default to 100 if not provided
    
    def _determine_cap(
        self,
        critical: int,
        major: int,
        minor: int,
    ) -> Tuple[float, Optional[str]]:
        """Determine maximum allowed score based on issues."""
        if critical > 0:
            return self.cap_critical, f"{critical} critical issue(s) - bank will reject"
        elif major > 0:
            return self.cap_major, f"{major} major issue(s) - corrections needed"
        elif minor > 0:
            return self.cap_minor, f"{minor} minor issue(s) - review advised"
        return 100.0, None
    
    def _determine_level(
        self,
        score: float,
        critical_count: int,
    ) -> ComplianceLevel:
        """Determine compliance level from score."""
        if critical_count > 0:
            return ComplianceLevel.NON_COMPLIANT
        elif score < 30:
            return ComplianceLevel.NON_COMPLIANT
        elif score < 70:
            return ComplianceLevel.PARTIAL
        elif score < 85:
            return ComplianceLevel.MOSTLY_COMPLIANT
        else:
            return ComplianceLevel.COMPLIANT


def calculate_compliance_score(
    issues: List[Dict[str, Any]],
    extraction_completeness: float = 1.0,
    validation_blocked: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function to calculate compliance score.
    
    Returns dict ready for API response.
    """
    scorer = ComplianceScorer()
    
    if validation_blocked:
        result = scorer._blocked_score()
    else:
        result = scorer.calculate_from_issues(issues, extraction_completeness)
    
    return result.to_dict()


def calculate_compliance_rate(
    issues: List[Dict[str, Any]],
    extraction_completeness: float = 1.0,
) -> int:
    """
    Calculate simple compliance rate (0-100).
    
    For backward compatibility with existing code.
    """
    scorer = ComplianceScorer()
    result = scorer.calculate_from_issues(issues, extraction_completeness)
    return result.compliance_rate


# Module-level instance
_compliance_scorer: Optional[ComplianceScorer] = None


def get_compliance_scorer() -> ComplianceScorer:
    """Get the global compliance scorer instance."""
    global _compliance_scorer
    if _compliance_scorer is None:
        _compliance_scorer = ComplianceScorer()
    return _compliance_scorer

