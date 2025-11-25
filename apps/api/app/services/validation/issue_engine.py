"""
Issue Engine - Phase 5: Auto-generate issues from missing fields.

This module generates validation issues automatically from:
1. Missing LC fields (from LCBaseline)
2. External rule execution (from Rules Engine)
3. Cross-document validation failures

The Issue Engine ensures that:
- Every missing critical field generates a critical issue
- Every missing required field generates a major issue
- Issues have proper Expected/Found/Suggestion messaging
- Issues are linked to relevant documents
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import datetime

from app.services.extraction.lc_baseline import (
    LCBaseline,
    FieldResult,
    FieldPriority,
    ExtractionStatus,
)
from app.rules.external.rule_executor import RuleExecutor, ExecutionSummary
from app.rules.external.rule_schema import RuleCategory


logger = logging.getLogger(__name__)


class IssueSeverity(str, Enum):
    """Issue severity levels."""
    CRITICAL = "critical"  # Blocks compliance, must fix
    MAJOR = "major"        # Serious, likely bank rejection
    MINOR = "minor"        # Warning, should review
    INFO = "info"          # Informational only


class IssueSource(str, Enum):
    """Source of the issue."""
    EXTRACTION = "extraction"   # Missing/invalid field extraction
    GATE = "gate"              # Validation gate failure
    RULE = "rule"              # External rule violation
    CROSSDOC = "crossdoc"      # Cross-document mismatch
    MANUAL = "manual"          # Manually added


@dataclass
class Issue:
    """A validation issue."""
    id: str
    rule: str
    title: str
    severity: IssueSeverity
    message: str
    expected: str
    actual: str
    suggestion: str
    
    # Document references
    documents: List[str] = field(default_factory=list)
    document_names: List[str] = field(default_factory=list)
    document_ids: List[str] = field(default_factory=list)
    
    # Metadata
    source: IssueSource = IssueSource.EXTRACTION
    field_name: Optional[str] = None
    ruleset_domain: str = "icc.lcopilot"
    
    # Display options
    display_card: bool = True
    blocks_validation: bool = False
    auto_generated: bool = True
    
    # Compliance references
    ucp_reference: Optional[str] = None
    isbp_reference: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "rule": self.rule,
            "title": self.title,
            "severity": self.severity.value,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual,
            "suggestion": self.suggestion,
            "documents": self.documents,
            "document_names": self.document_names,
            "document_ids": self.document_ids,
            "source": self.source.value,
            "field_name": self.field_name,
            "ruleset_domain": self.ruleset_domain,
            "display_card": self.display_card,
            "blocks_validation": self.blocks_validation,
            "auto_generated": self.auto_generated,
            "ucp_reference": self.ucp_reference,
            "isbp_reference": self.isbp_reference,
            "passed": False,  # Issues are always failed checks
        }


@dataclass
class IssueEngineResult:
    """Result from the issue engine."""
    issues: List[Issue]
    
    # Counts by severity
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    info_count: int = 0
    
    # Counts by source
    extraction_count: int = 0
    rule_count: int = 0
    crossdoc_count: int = 0
    
    # Summary
    total_count: int = 0
    has_blocking_issues: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_count": self.total_count,
            "critical_count": self.critical_count,
            "major_count": self.major_count,
            "minor_count": self.minor_count,
            "info_count": self.info_count,
            "extraction_count": self.extraction_count,
            "rule_count": self.rule_count,
            "crossdoc_count": self.crossdoc_count,
            "has_blocking_issues": self.has_blocking_issues,
            "issues": [i.to_dict() for i in self.issues],
        }
    
    def get_issues_by_severity(self, severity: IssueSeverity) -> List[Issue]:
        return [i for i in self.issues if i.severity == severity]
    
    def get_blocking_issues(self) -> List[Issue]:
        return [i for i in self.issues if i.blocks_validation]


# Field descriptions for human-readable messages
FIELD_DESCRIPTIONS = {
    "lc_number": {
        "name": "LC Reference Number",
        "expected": "LC reference/document number (SWIFT tag :20:)",
        "ucp_ref": "UCP600 Article 1",
    },
    "lc_type": {
        "name": "LC Type",
        "expected": "Letter of Credit type (irrevocable, transferable, etc.)",
        "ucp_ref": "UCP600 Article 3",
    },
    "applicant": {
        "name": "Applicant",
        "expected": "Applicant name and address (SWIFT tag :50:)",
        "ucp_ref": "UCP600 Article 14(k)",
    },
    "beneficiary": {
        "name": "Beneficiary",
        "expected": "Beneficiary name and address (SWIFT tag :59:)",
        "ucp_ref": "UCP600 Article 14(k)",
    },
    "issuing_bank": {
        "name": "Issuing Bank",
        "expected": "Issuing bank name and SWIFT/BIC code",
        "ucp_ref": "UCP600 Article 2",
    },
    "advising_bank": {
        "name": "Advising Bank",
        "expected": "Advising bank name and SWIFT/BIC code",
        "ucp_ref": "UCP600 Article 9",
    },
    "amount": {
        "name": "Credit Amount",
        "expected": "Credit amount with currency (SWIFT tag :32B:)",
        "ucp_ref": "UCP600 Article 18",
    },
    "expiry_date": {
        "name": "Expiry Date",
        "expected": "LC expiry date in YYYY-MM-DD format (SWIFT tag :31D:)",
        "ucp_ref": "UCP600 Article 6(d)",
    },
    "issue_date": {
        "name": "Issue Date",
        "expected": "LC issue date in YYYY-MM-DD format (SWIFT tag :31C:)",
        "ucp_ref": "UCP600 Article 6",
    },
    "latest_shipment": {
        "name": "Latest Shipment Date",
        "expected": "Latest date for shipment (SWIFT tag :44C:)",
        "ucp_ref": "UCP600 Article 6(c)",
    },
    "port_of_loading": {
        "name": "Port of Loading",
        "expected": "Port/place of loading (SWIFT tag :44E:)",
        "ucp_ref": "UCP600 Article 20",
    },
    "port_of_discharge": {
        "name": "Port of Discharge",
        "expected": "Port/place of discharge (SWIFT tag :44F:)",
        "ucp_ref": "UCP600 Article 20",
    },
    "incoterm": {
        "name": "Incoterm",
        "expected": "Trade term (FOB, CIF, CFR, etc.)",
        "ucp_ref": None,
    },
    "goods_description": {
        "name": "Goods Description",
        "expected": "Description of goods/services (SWIFT tag :45A:)",
        "ucp_ref": "UCP600 Article 18(c)",
    },
    "documents_required": {
        "name": "Documents Required",
        "expected": "List of required documents (SWIFT tag :46A:)",
        "ucp_ref": "UCP600 Article 14",
    },
    "ucp_reference": {
        "name": "UCP Reference",
        "expected": "Applicable rules reference (SWIFT tag :40E:)",
        "ucp_ref": "UCP600 Article 1",
    },
    "additional_conditions": {
        "name": "Additional Conditions",
        "expected": "Additional conditions/clauses (SWIFT tag :47A:)",
        "ucp_ref": "UCP600 Article 14",
    },
}


class IssueEngine:
    """
    Engine for generating validation issues.
    
    Combines:
    1. Extraction issues from LCBaseline missing fields
    2. Rule issues from external rules engine
    3. Cross-document issues from crossdoc validation
    """
    
    def __init__(
        self,
        rule_executor: Optional[RuleExecutor] = None,
    ):
        self.rule_executor = rule_executor or RuleExecutor()
    
    def generate_all_issues(
        self,
        baseline: LCBaseline,
        context: Dict[str, Any],
        include_extraction: bool = True,
        include_rules: bool = True,
        rule_categories: Optional[List[RuleCategory]] = None,
    ) -> IssueEngineResult:
        """
        Generate all issues from baseline and rules.
        
        Args:
            baseline: LCBaseline with extraction results
            context: Validation context for rule execution
            include_extraction: Include extraction issues
            include_rules: Include rule-based issues
            rule_categories: Filter rules by category
            
        Returns:
            IssueEngineResult with all generated issues
        """
        all_issues: List[Issue] = []
        
        # 1. Generate extraction issues from missing fields
        if include_extraction:
            extraction_issues = self.generate_extraction_issues(baseline)
            all_issues.extend(extraction_issues)
        
        # 2. Execute rules and generate rule issues
        if include_rules:
            rule_issues = self.generate_rule_issues(context, rule_categories)
            all_issues.extend(rule_issues)
        
        # Build result with counts
        result = self._build_result(all_issues)
        
        logger.info(
            "Issue engine generated %d issues: critical=%d, major=%d, minor=%d",
            result.total_count, result.critical_count, result.major_count, result.minor_count
        )
        
        return result
    
    def generate_extraction_issues(
        self,
        baseline: LCBaseline,
    ) -> List[Issue]:
        """
        Generate issues for missing LC fields.
        
        This ensures every missing critical/required field has an issue.
        """
        issues: List[Issue] = []
        
        for field_result in baseline.get_all_fields():
            if field_result.is_present:
                continue
            
            # Skip optional fields
            if field_result.priority == FieldPriority.OPTIONAL:
                continue
            
            issue = self._create_extraction_issue(field_result)
            if issue:
                issues.append(issue)
        
        return issues
    
    def generate_rule_issues(
        self,
        context: Dict[str, Any],
        categories: Optional[List[RuleCategory]] = None,
    ) -> List[Issue]:
        """
        Execute rules and generate issues from violations.
        """
        # Execute rules
        execution_result = self.rule_executor.execute_all_rules(context, categories)
        
        # Convert rule issues to Issue objects
        issues: List[Issue] = []
        
        for rule_issue in execution_result.issues:
            issue = self._convert_rule_issue(rule_issue)
            if issue:
                issues.append(issue)
        
        return issues
    
    def _create_extraction_issue(
        self,
        field_result: FieldResult,
    ) -> Optional[Issue]:
        """Create an issue for a missing field."""
        field_name = field_result.field_name
        field_info = FIELD_DESCRIPTIONS.get(field_name, {})
        
        # Determine severity based on priority
        if field_result.priority == FieldPriority.CRITICAL:
            severity = IssueSeverity.CRITICAL
            blocks = True
        elif field_result.priority == FieldPriority.REQUIRED:
            severity = IssueSeverity.MAJOR
            blocks = False
        elif field_result.priority == FieldPriority.IMPORTANT:
            severity = IssueSeverity.MINOR
            blocks = False
        else:
            return None  # Skip optional
        
        human_name = field_info.get("name", field_name.replace("_", " ").title())
        expected = field_info.get("expected", f"{human_name} value")
        ucp_ref = field_info.get("ucp_ref")
        
        # Build actual value based on status
        if field_result.status == ExtractionStatus.MISSING:
            actual = "Not found in document"
        elif field_result.status == ExtractionStatus.INVALID:
            actual = f"Invalid value: {field_result.error or 'parse error'}"
        elif field_result.status == ExtractionStatus.PARTIAL:
            actual = f"Partially extracted: {field_result.value}"
        else:
            actual = "Not extracted"
        
        # Build suggestion
        if field_result.status == ExtractionStatus.MISSING:
            suggestion = (
                f"Ensure the LC document contains a visible {human_name} field. "
                f"If using SWIFT format, check for the appropriate tag."
            )
        else:
            suggestion = (
                f"Verify the {human_name} is clearly visible in the document. "
                f"Consider re-scanning with higher quality."
            )
        
        return Issue(
            id=f"extraction-{field_name}",
            rule=f"LC-MISSING-{field_name.upper()}",
            title=f"Missing {human_name}",
            severity=severity,
            message=(
                f"The {human_name} could not be extracted from the Letter of Credit. "
                f"This field is {field_result.priority.value} for validation."
            ),
            expected=expected,
            actual=actual,
            suggestion=suggestion,
            documents=["Letter of Credit"],
            document_names=["Letter of Credit"],
            source=IssueSource.EXTRACTION,
            field_name=field_name,
            ruleset_domain="icc.lcopilot.extraction",
            display_card=True,
            blocks_validation=blocks,
            ucp_reference=ucp_ref,
        )
    
    def _convert_rule_issue(
        self,
        rule_issue: Dict[str, Any],
    ) -> Optional[Issue]:
        """Convert a rule engine issue to an Issue object."""
        severity_str = rule_issue.get("severity", "minor").lower()
        if severity_str == "critical":
            severity = IssueSeverity.CRITICAL
        elif severity_str in ("major", "warning"):
            severity = IssueSeverity.MAJOR
        elif severity_str == "minor":
            severity = IssueSeverity.MINOR
        else:
            severity = IssueSeverity.INFO
        
        # Determine source from ruleset_domain
        domain = rule_issue.get("ruleset_domain", "")
        if "extraction" in domain:
            source = IssueSource.EXTRACTION
        elif "crossdoc" in domain:
            source = IssueSource.CROSSDOC
        else:
            source = IssueSource.RULE
        
        return Issue(
            id=rule_issue.get("rule", "unknown"),
            rule=rule_issue.get("rule", "unknown"),
            title=rule_issue.get("title", "Rule Violation"),
            severity=severity,
            message=rule_issue.get("message", ""),
            expected=str(rule_issue.get("expected", "")),
            actual=str(rule_issue.get("actual", "")),
            suggestion=rule_issue.get("suggestion", "Review and correct the discrepancy."),
            documents=rule_issue.get("documents", []),
            document_names=rule_issue.get("document_names", []),
            document_ids=rule_issue.get("document_ids", []),
            source=source,
            ruleset_domain=domain,
            display_card=rule_issue.get("display_card", True),
            blocks_validation=rule_issue.get("blocks_validation", False),
            ucp_reference=rule_issue.get("ucp_reference"),
            isbp_reference=rule_issue.get("isbp_reference"),
        )
    
    def _build_result(
        self,
        issues: List[Issue],
    ) -> IssueEngineResult:
        """Build IssueEngineResult from issues list."""
        # Count by severity
        critical = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        major = sum(1 for i in issues if i.severity == IssueSeverity.MAJOR)
        minor = sum(1 for i in issues if i.severity == IssueSeverity.MINOR)
        info = sum(1 for i in issues if i.severity == IssueSeverity.INFO)
        
        # Count by source
        extraction = sum(1 for i in issues if i.source == IssueSource.EXTRACTION)
        rule = sum(1 for i in issues if i.source == IssueSource.RULE)
        crossdoc = sum(1 for i in issues if i.source == IssueSource.CROSSDOC)
        
        # Check for blocking issues
        has_blocking = any(i.blocks_validation for i in issues)
        
        return IssueEngineResult(
            issues=issues,
            critical_count=critical,
            major_count=major,
            minor_count=minor,
            info_count=info,
            extraction_count=extraction,
            rule_count=rule,
            crossdoc_count=crossdoc,
            total_count=len(issues),
            has_blocking_issues=has_blocking,
        )


def generate_issues_from_baseline(
    baseline: LCBaseline,
) -> List[Dict[str, Any]]:
    """
    Convenience function to generate issues from LCBaseline.
    
    Returns list of issue dicts ready for API response.
    """
    engine = IssueEngine()
    result = engine.generate_extraction_issues(baseline)
    return [issue.to_dict() for issue in result]


def generate_all_issues(
    baseline: LCBaseline,
    context: Dict[str, Any],
) -> IssueEngineResult:
    """
    Convenience function to generate all issues.
    """
    engine = IssueEngine()
    return engine.generate_all_issues(baseline, context)


# Module-level instance
_issue_engine: Optional[IssueEngine] = None


def get_issue_engine() -> IssueEngine:
    """Get the global issue engine instance."""
    global _issue_engine
    if _issue_engine is None:
        _issue_engine = IssueEngine()
    return _issue_engine

