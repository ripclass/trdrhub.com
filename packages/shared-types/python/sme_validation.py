"""
SME Validation Response Contract (Python)

THE LAW: Backend MUST produce this. Frontend MUST consume this.

This contract defines exactly what an SME/Corporation user sees
after uploading their LC document set for validation.

Version: 2.0
Date: 2024-12-07
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Literal
from datetime import datetime, date
from enum import Enum


# ============================================
# ENUMS
# ============================================

class VerdictStatus(str, Enum):
    PASS = "PASS"                    # All good, ready to submit
    FIX_REQUIRED = "FIX_REQUIRED"    # Has issues that need fixing
    LIKELY_REJECT = "LIKELY_REJECT"  # Critical issues, bank will likely reject
    MISSING_DOCS = "MISSING_DOCS"    # Required documents not uploaded


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class DocumentStatus(str, Enum):
    VERIFIED = "verified"
    HAS_ISSUES = "has_issues"


# ============================================
# DATA CLASSES
# ============================================

@dataclass
class LCSummary:
    """LC Header Information"""
    number: str                      # "EXP2026BD001"
    amount: float                    # 450000.00
    currency: str                    # "USD"
    beneficiary: str                 # "Bangladesh Garments Ltd"
    applicant: str                   # "Global Importers Inc"
    expiry_date: str                 # "2026-03-15" (ISO date string)
    days_until_expiry: int           # 45 (negative if expired)
    issuing_bank: Optional[str] = None  # "ICBC Shanghai"
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Verdict:
    """The Big Answer - What SME Cares About Most"""
    status: VerdictStatus
    headline: str                    # "FIX 3 ISSUES BEFORE SUBMITTING"
    subtext: str                     # "Bank will likely REJECT..."
    estimated_risk: RiskLevel
    estimated_fee_if_rejected: float  # 75.00
    total_issues: int
    critical_count: int
    major_count: int
    minor_count: int
    missing_docs_count: int
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["estimated_risk"] = self.estimated_risk.value
        return d


@dataclass
class Tolerance:
    """Tolerance Information for an Issue"""
    applicable: bool
    type: str                        # "5% quantity tolerance"
    within_tolerance: bool
    tolerance_amount: Optional[str] = None  # "±5%"
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SMEIssue:
    """Single Issue - Written for SME Understanding"""
    id: str                          # "CROSSDOC-AMOUNT-1"
    title: str                       # "Invoice Amount Exceeds LC"
    severity: Severity
    your_document: str               # "USD 458,750.00"
    lc_requires: str                 # "USD 450,000.00"
    document_type: str               # "commercial_invoice"
    document_name: str               # "Commercial Invoice"
    how_to_fix: List[str]            # ["Request corrected invoice..."]
    why_banks_reject: str            # "UCP600 Article 18(c) - ..."
    difference: Optional[str] = None  # "Over by USD 8,750.00 (1.9%)"
    affected_documents: Optional[List[str]] = None  # For multi-doc issues
    ucp_article: Optional[str] = None  # "18(c)"
    isbp_reference: Optional[str] = None  # "C1"
    lc_clause: Optional[str] = None  # "47A(6)"
    tolerance: Optional[Tolerance] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        if self.tolerance:
            d["tolerance"] = self.tolerance.to_dict()
        return d


@dataclass
class SMEDocument:
    """Document that was checked"""
    type: str                        # "letter_of_credit"
    name: str                        # "Letter of Credit"
    status: DocumentStatus
    status_note: str                 # "All required fields present"
    issues_count: int                # 0
    filename: Optional[str] = None   # "LC.pdf"
    extraction_confidence: Optional[float] = None  # 0.95
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class SMEMissingDoc:
    """Document that's required but not uploaded"""
    type: str                        # "inspection_certificate"
    name: str                        # "Inspection Certificate"
    required_by: str                 # "LC clause 46A-5"
    description: Optional[str] = None  # "Third-party inspection certificate"
    accepted_issuers: Optional[List[str]] = None  # ["SGS", "Intertek"]
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IssuesGrouped:
    """Issues grouped by severity"""
    must_fix: List[SMEIssue] = field(default_factory=list)    # critical + major
    should_fix: List[SMEIssue] = field(default_factory=list)  # minor
    
    def to_dict(self) -> dict:
        return {
            "must_fix": [i.to_dict() for i in self.must_fix],
            "should_fix": [i.to_dict() for i in self.should_fix],
        }


@dataclass
class DocumentsGrouped:
    """Documents grouped by status"""
    good: List[SMEDocument] = field(default_factory=list)        # ✅ verified
    has_issues: List[SMEDocument] = field(default_factory=list)  # ⚠️ has issues
    missing: List[SMEMissingDoc] = field(default_factory=list)   # ❌ not uploaded
    
    def to_dict(self) -> dict:
        return {
            "good": [d.to_dict() for d in self.good],
            "has_issues": [d.to_dict() for d in self.has_issues],
            "missing": [m.to_dict() for m in self.missing],
        }


@dataclass
class ProcessingMeta:
    """Processing metadata"""
    session_id: str
    processed_at: str                # ISO timestamp
    processing_time_seconds: float
    processing_time_display: str     # "35.6 seconds"
    documents_checked: int
    rules_executed: int
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SMEValidationResponse:
    """
    THE COMPLETE RESPONSE
    
    This is the contract. Backend produces it. Frontend consumes it.
    """
    version: str = "2.0"
    lc_summary: LCSummary = None
    verdict: Verdict = None
    issues: IssuesGrouped = None
    documents: DocumentsGrouped = None
    processing: ProcessingMeta = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "version": self.version,
            "lc_summary": self.lc_summary.to_dict() if self.lc_summary else None,
            "verdict": self.verdict.to_dict() if self.verdict else None,
            "issues": self.issues.to_dict() if self.issues else None,
            "documents": self.documents.to_dict() if self.documents else None,
            "processing": self.processing.to_dict() if self.processing else None,
        }


# ============================================
# HELPER FUNCTIONS
# ============================================

def calculate_verdict(
    issues: List[SMEIssue],
    missing_docs: List[SMEMissingDoc],
) -> Verdict:
    """Calculate the verdict based on issues and missing docs"""
    
    critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
    major_count = sum(1 for i in issues if i.severity == Severity.MAJOR)
    minor_count = sum(1 for i in issues if i.severity == Severity.MINOR)
    missing_count = len(missing_docs)
    total_issues = len(issues)
    
    # Determine status
    if missing_count > 0:
        status = VerdictStatus.MISSING_DOCS
        headline = f"UPLOAD {missing_count} MISSING DOCUMENT{'S' if missing_count > 1 else ''}"
        subtext = "Required documents are missing. Upload them before submitting to bank."
        risk = RiskLevel.HIGH
    elif critical_count > 0:
        status = VerdictStatus.LIKELY_REJECT
        headline = f"FIX {critical_count + major_count} CRITICAL ISSUE{'S' if critical_count + major_count > 1 else ''}"
        subtext = "Bank will likely REJECT your documents. Fix these issues to avoid discrepancy fees."
        risk = RiskLevel.HIGH
    elif major_count > 0:
        status = VerdictStatus.FIX_REQUIRED
        headline = f"FIX {major_count} ISSUE{'S' if major_count > 1 else ''} BEFORE SUBMITTING"
        subtext = "These issues may cause rejection. Recommended to fix before bank submission."
        risk = RiskLevel.MEDIUM
    elif minor_count > 0:
        status = VerdictStatus.FIX_REQUIRED
        headline = f"REVIEW {minor_count} MINOR ISSUE{'S' if minor_count > 1 else ''}"
        subtext = "Minor issues found. Bank may overlook these, but consider fixing for safety."
        risk = RiskLevel.LOW
    else:
        status = VerdictStatus.PASS
        headline = "READY TO SUBMIT"
        subtext = "Your documents appear compliant with LC terms. Good to go!"
        risk = RiskLevel.LOW
    
    # Calculate estimated fee
    estimated_fee = 0.0
    if critical_count > 0 or major_count > 0:
        estimated_fee = 75.0 + (critical_count * 25.0) + (major_count * 10.0)
    
    return Verdict(
        status=status,
        headline=headline,
        subtext=subtext,
        estimated_risk=risk,
        estimated_fee_if_rejected=estimated_fee,
        total_issues=total_issues,
        critical_count=critical_count,
        major_count=major_count,
        minor_count=minor_count,
        missing_docs_count=missing_count,
    )


def group_issues(issues: List[SMEIssue]) -> IssuesGrouped:
    """Group issues by severity for display"""
    must_fix = [i for i in issues if i.severity in (Severity.CRITICAL, Severity.MAJOR)]
    should_fix = [i for i in issues if i.severity == Severity.MINOR]
    
    return IssuesGrouped(
        must_fix=must_fix,
        should_fix=should_fix,
    )


def group_documents(
    documents: List[SMEDocument],
    missing: List[SMEMissingDoc],
) -> DocumentsGrouped:
    """Group documents by status for display"""
    good = [d for d in documents if d.status == DocumentStatus.VERIFIED and d.issues_count == 0]
    has_issues = [d for d in documents if d.issues_count > 0]
    
    return DocumentsGrouped(
        good=good,
        has_issues=has_issues,
        missing=missing,
    )
