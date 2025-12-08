"""
SME Response Builder (v2)

Transforms the existing validation output into the SME contract format.
This is the bridge between old validation logic and new clean contract.

Version: 2.0
Date: 2024-12-07
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple

# Import the contract types
# Note: In production, these would come from shared-types package
# For now, we define them inline to avoid import path issues

from dataclasses import dataclass, field, asdict
from enum import Enum


# ============================================
# CONTRACT TYPES (mirrored from shared-types)
# ============================================

class VerdictStatus(str, Enum):
    PASS = "PASS"
    FIX_REQUIRED = "FIX_REQUIRED"
    LIKELY_REJECT = "LIKELY_REJECT"
    MISSING_DOCS = "MISSING_DOCS"


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


@dataclass
class LCSummary:
    number: str
    amount: float
    currency: str
    beneficiary: str
    applicant: str
    expiry_date: str
    days_until_expiry: int
    issuing_bank: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Verdict:
    status: VerdictStatus
    headline: str
    subtext: str
    estimated_risk: RiskLevel
    estimated_fee_if_rejected: float
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
    applicable: bool
    type: str
    within_tolerance: bool
    tolerance_amount: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SMEIssue:
    id: str
    title: str
    severity: Severity
    your_document: str
    lc_requires: str
    document_type: str
    document_name: str
    how_to_fix: List[str]
    why_banks_reject: str
    difference: Optional[str] = None
    affected_documents: Optional[List[str]] = None
    ucp_article: Optional[str] = None
    isbp_reference: Optional[str] = None
    lc_clause: Optional[str] = None
    tolerance: Optional[Tolerance] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        if self.tolerance:
            d["tolerance"] = self.tolerance.to_dict()
        return d


@dataclass
class SMEDocument:
    type: str
    name: str
    status: DocumentStatus
    status_note: str
    issues_count: int
    filename: Optional[str] = None
    extraction_confidence: Optional[float] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class SMEMissingDoc:
    type: str
    name: str
    required_by: str
    description: Optional[str] = None
    accepted_issuers: Optional[List[str]] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IssuesGrouped:
    must_fix: List[SMEIssue] = field(default_factory=list)
    should_fix: List[SMEIssue] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "must_fix": [i.to_dict() for i in self.must_fix],
            "should_fix": [i.to_dict() for i in self.should_fix],
        }


@dataclass
class DocumentsGrouped:
    good: List[SMEDocument] = field(default_factory=list)
    has_issues: List[SMEDocument] = field(default_factory=list)
    missing: List[SMEMissingDoc] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "good": [d.to_dict() for d in self.good],
            "has_issues": [d.to_dict() for d in self.has_issues],
            "missing": [m.to_dict() for m in self.missing],
        }


@dataclass
class ProcessingMeta:
    session_id: str
    processed_at: str
    processing_time_seconds: float
    processing_time_display: str
    documents_checked: int
    rules_executed: int
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SMEValidationResponse:
    version: str = "2.0"
    lc_summary: LCSummary = None
    verdict: Verdict = None
    issues: IssuesGrouped = None
    documents: DocumentsGrouped = None
    processing: ProcessingMeta = None
    
    def to_dict(self) -> dict:
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
    return IssuesGrouped(must_fix=must_fix, should_fix=should_fix)


def group_documents(
    documents: List[SMEDocument],
    missing: List[SMEMissingDoc],
) -> DocumentsGrouped:
    """Group documents by status for display"""
    good = [d for d in documents if d.status == DocumentStatus.VERIFIED and d.issues_count == 0]
    has_issues = [d for d in documents if d.issues_count > 0]
    return DocumentsGrouped(good=good, has_issues=has_issues, missing=missing)

logger = logging.getLogger(__name__)


# ============================================
# DOCUMENT TYPE DISPLAY NAMES
# ============================================
DOCUMENT_DISPLAY_NAMES = {
    "letter_of_credit": "Letter of Credit",
    "commercial_invoice": "Commercial Invoice",
    "bill_of_lading": "Bill of Lading",
    "packing_list": "Packing List",
    "certificate_of_origin": "Certificate of Origin",
    "insurance_certificate": "Insurance Certificate",
    "inspection_certificate": "Inspection Certificate",
    "beneficiary_certificate": "Beneficiary Certificate",
    "weight_certificate": "Weight Certificate",
    "phytosanitary_certificate": "Phytosanitary Certificate",
}


def get_display_name(doc_type: str) -> str:
    """Get human-readable document name"""
    return DOCUMENT_DISPLAY_NAMES.get(
        doc_type, 
        doc_type.replace("_", " ").title()
    )


# ============================================
# ISSUE TRANSFORMATION
# ============================================

# Map rule IDs to user-friendly content
ISSUE_CONTENT = {
    "CROSSDOC-AMOUNT-1": {
        "title": "Invoice Amount Exceeds LC",
        "why": "UCP600 Article 18(c) - Invoice amount must not exceed the credit amount",
        "how_to_fix": [
            "Request corrected invoice from supplier showing the LC amount or less",
            "OR request LC amendment to increase the credit amount",
        ],
    },
    "CROSSDOC-VOYAGE-1": {
        "title": "Bill of Lading Missing Voyage Number",
        "why": "LC requires voyage number to be shown on B/L per field 46A",
        "how_to_fix": [
            "Request corrected B/L from the shipping line with voyage number included",
        ],
    },
    "CROSSDOC-WEIGHT-1": {
        "title": "Bill of Lading Missing Weight Information",
        "why": "LC requires gross and net weight to be shown on B/L",
        "how_to_fix": [
            "Request corrected B/L from shipping line with weight information",
        ],
    },
    "CROSSDOC-PO-NUMBER": {
        "title": "Purchase Order Number Missing from Documents",
        "why": "LC Additional Conditions (47A) require PO number on all documents",
        "how_to_fix": [
            "Add the PO number to each document before resubmitting",
            "Contact your buyer for the correct PO number if unclear",
        ],
    },
    "CROSSDOC-BIN": {
        "title": "Exporter BIN Missing from Documents",
        "why": "LC Additional Conditions (47A) require Exporter BIN on all documents",
        "how_to_fix": [
            "Add your Business Identification Number (BIN) to each document",
        ],
    },
    "CROSSDOC-TIN": {
        "title": "Exporter TIN Missing from Documents", 
        "why": "LC Additional Conditions (47A) require Exporter TIN on all documents",
        "how_to_fix": [
            "Add your Tax Identification Number (TIN) to each document",
        ],
    },
    "DOCSET-MISSING-INSPECTION-CERTIFICATE": {
        "title": "Inspection Certificate Not Provided",
        "why": "LC requires inspection certificate per field 46A",
        "how_to_fix": [
            "Arrange inspection with an authorized agency (SGS, Intertek, Bureau Veritas)",
            "Upload the inspection certificate once received",
        ],
    },
    "DOCSET-MISSING-BENEFICIARY-CERTIFICATE": {
        "title": "Beneficiary Certificate Not Provided",
        "why": "LC requires beneficiary certificate per field 46A",
        "how_to_fix": [
            "Prepare a beneficiary certificate as per LC requirements",
            "Sign and stamp with company seal",
        ],
    },
    "LC-EXPIRY-WARNING": {
        "title": "LC Expiry Date Approaching",
        "why": "Documents must be presented before LC expiry per UCP600 Article 6",
        "how_to_fix": [
            "Submit documents immediately to meet the deadline",
            "OR request LC extension from the issuing bank",
        ],
    },
}


def transform_issue(raw_issue: Dict[str, Any]) -> SMEIssue:
    """Transform a raw issue into the SME contract format"""
    
    rule_id = raw_issue.get("rule_id", raw_issue.get("rule", "UNKNOWN"))
    
    # Get pre-defined content or build from raw
    content = ISSUE_CONTENT.get(rule_id, {})
    
    # Determine severity
    raw_severity = (raw_issue.get("severity") or "minor").lower()
    if raw_severity == "critical":
        severity = Severity.CRITICAL
    elif raw_severity == "major":
        severity = Severity.MAJOR
    else:
        severity = Severity.MINOR
    
    # Get document info
    doc_type = raw_issue.get("document_type") or raw_issue.get("target_doc") or "unknown"
    affected_docs = raw_issue.get("affected_documents") or raw_issue.get("affected_document_names") or []
    
    # Build the issue
    return SMEIssue(
        id=rule_id,
        title=content.get("title") or raw_issue.get("title") or raw_issue.get("message", "Issue Found"),
        severity=severity,
        your_document=raw_issue.get("actual") or raw_issue.get("found") or "Not found",
        lc_requires=raw_issue.get("expected") or "As per LC terms",
        difference=raw_issue.get("difference"),
        document_type=doc_type,
        document_name=get_display_name(doc_type),
        affected_documents=affected_docs if affected_docs else None,
        how_to_fix=content.get("how_to_fix") or [raw_issue.get("suggestion", "Review and correct the document")],
        why_banks_reject=content.get("why") or raw_issue.get("ucp_reference") or "Per LC terms and UCP600",
        ucp_article=raw_issue.get("ucp_article"),
        isbp_reference=raw_issue.get("isbp_reference"),
        lc_clause=raw_issue.get("lc_clause") or raw_issue.get("lc_field"),
        tolerance=None,  # TODO: Add tolerance info if applicable
    )


def transform_document(raw_doc: Dict[str, Any], issue_count: int) -> SMEDocument:
    """Transform a raw document summary into the SME contract format"""
    
    doc_type = raw_doc.get("document_type") or raw_doc.get("type") or "unknown"
    raw_status = (raw_doc.get("status") or "success").lower()
    
    if raw_status == "success" or raw_status == "verified":
        status = DocumentStatus.VERIFIED
        status_note = "All required fields present"
    else:
        status = DocumentStatus.HAS_ISSUES
        status_note = f"{issue_count} issue(s) found"
    
    return SMEDocument(
        type=doc_type,
        name=get_display_name(doc_type),
        filename=raw_doc.get("filename") or raw_doc.get("name"),
        status=status,
        status_note=status_note,
        issues_count=issue_count,
        extraction_confidence=raw_doc.get("ocrConfidence") or raw_doc.get("extraction_confidence"),
    )


def transform_missing_doc(raw_missing: Dict[str, Any]) -> SMEMissingDoc:
    """Transform a missing document entry into the SME contract format"""
    
    doc_type = raw_missing.get("document_type") or raw_missing.get("type") or "unknown"
    
    # Extract required_by from rule_id or message
    required_by = raw_missing.get("required_by") or raw_missing.get("lc_clause") or "LC terms"
    rule_id = raw_missing.get("rule_id", "")
    if "46A" in str(rule_id) or "46A" in str(required_by):
        required_by = "LC clause 46A - Documents Required"
    
    return SMEMissingDoc(
        type=doc_type,
        name=get_display_name(doc_type),
        required_by=required_by,
        description=raw_missing.get("description"),
        accepted_issuers=raw_missing.get("accepted_issuers"),
    )


# ============================================
# MAIN BUILDER FUNCTION
# ============================================

def build_sme_response(
    lc_data: Dict[str, Any],
    document_summaries: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
    missing_docs: List[Dict[str, Any]],
    processing_time_seconds: float,
    session_id: str,
    rules_executed: int = 0,
) -> SMEValidationResponse:
    """
    Build the SME validation response from raw validation data.
    
    This is the main entry point for transforming validation results
    into the clean SME contract format.
    """
    
    # =========================================
    # 1. Build LC Summary
    # =========================================
    
    # Parse expiry date
    expiry_str = lc_data.get("expiry_date") or lc_data.get("timeline", {}).get("expiry")
    days_until_expiry = 0
    if expiry_str:
        try:
            if isinstance(expiry_str, str):
                expiry_date = datetime.fromisoformat(expiry_str.replace("Z", "+00:00")).date()
            elif isinstance(expiry_str, date):
                expiry_date = expiry_str
            else:
                expiry_date = None
            
            if expiry_date:
                days_until_expiry = (expiry_date - date.today()).days
        except Exception:
            pass
    
    # Get amount
    amount_data = lc_data.get("amount", {})
    if isinstance(amount_data, dict):
        amount = float(amount_data.get("value", 0) or 0)
        currency = amount_data.get("currency", "USD")
    else:
        amount = float(amount_data or 0)
        currency = lc_data.get("currency", "USD")
    
    # Get party names
    beneficiary_data = lc_data.get("beneficiary", {})
    applicant_data = lc_data.get("applicant", {})
    
    lc_summary = LCSummary(
        number=lc_data.get("number") or lc_data.get("lc_number") or "Unknown",
        amount=amount,
        currency=currency,
        beneficiary=beneficiary_data.get("name", "") if isinstance(beneficiary_data, dict) else str(beneficiary_data or ""),
        applicant=applicant_data.get("name", "") if isinstance(applicant_data, dict) else str(applicant_data or ""),
        expiry_date=expiry_str or "",
        days_until_expiry=days_until_expiry,
        issuing_bank=lc_data.get("issuing_bank") or lc_data.get("advising_bank"),
    )
    
    # =========================================
    # 2. Transform Issues
    # =========================================
    
    sme_issues: List[SMEIssue] = []
    
    # Count issues per document for status tracking
    issues_per_doc: Dict[str, int] = {}
    
    for raw_issue in issues:
        sme_issue = transform_issue(raw_issue)
        sme_issues.append(sme_issue)
        
        # Track issue count per document
        affected = raw_issue.get("affected_documents") or [sme_issue.document_type]
        for doc_type in affected:
            issues_per_doc[doc_type] = issues_per_doc.get(doc_type, 0) + 1
    
    # =========================================
    # 3. Transform Missing Documents  
    # =========================================
    
    sme_missing: List[SMEMissingDoc] = []
    
    for raw_missing in missing_docs:
        sme_missing.append(transform_missing_doc(raw_missing))
    
    # =========================================
    # 4. Transform Document Summaries
    # =========================================
    
    sme_documents: List[SMEDocument] = []
    
    for raw_doc in document_summaries:
        doc_type = raw_doc.get("document_type") or raw_doc.get("type") or "unknown"
        issue_count = issues_per_doc.get(doc_type, 0)
        sme_documents.append(transform_document(raw_doc, issue_count))
    
    # =========================================
    # 5. Calculate Verdict
    # =========================================
    
    verdict = calculate_verdict(sme_issues, sme_missing)
    
    # =========================================
    # 6. Group for Display
    # =========================================
    
    issues_grouped = group_issues(sme_issues)
    documents_grouped = group_documents(sme_documents, sme_missing)
    
    # =========================================
    # 7. Build Processing Metadata
    # =========================================
    
    processing = ProcessingMeta(
        session_id=session_id,
        processed_at=datetime.utcnow().isoformat() + "Z",
        processing_time_seconds=round(processing_time_seconds, 2),
        processing_time_display=f"{processing_time_seconds:.1f} seconds",
        documents_checked=len(document_summaries),
        rules_executed=rules_executed,
    )
    
    # =========================================
    # 8. Assemble Final Response
    # =========================================
    
    return SMEValidationResponse(
        version="2.0",
        lc_summary=lc_summary,
        verdict=verdict,
        issues=issues_grouped,
        documents=documents_grouped,
        processing=processing,
    )


# ============================================
# ADAPTER FOR EXISTING VALIDATE.PY OUTPUT
# ============================================

def adapt_from_structured_result(
    structured_result: Dict[str, Any],
    session_id: str,
) -> SMEValidationResponse:
    """
    Adapt the existing structured_result from validate.py 
    into the new SME contract format.
    
    This is the bridge function that allows gradual migration.
    """
    
    # Extract LC data
    lc_data = structured_result.get("lc_data") or structured_result.get("lc") or {}
    
    # Extract document summaries  
    document_summaries = structured_result.get("documents_structured") or structured_result.get("document_summaries") or []
    
    # Extract all issues
    all_issues = []
    
    # From crossdoc_issues
    crossdoc_issues = structured_result.get("crossdoc_issues") or []
    for issue in crossdoc_issues:
        if isinstance(issue, dict):
            all_issues.append(issue)
    
    # From issues array
    issues_array = structured_result.get("issues") or []
    for issue in issues_array:
        if isinstance(issue, dict):
            all_issues.append(issue)
    
    # Extract missing documents (from DOCSET-MISSING rules)
    missing_docs = []
    regular_issues = []
    
    for issue in all_issues:
        rule_id = issue.get("rule_id") or issue.get("rule") or ""
        if "DOCSET-MISSING" in str(rule_id):
            # This is a missing document, not an issue
            doc_type = rule_id.replace("DOCSET-MISSING-", "").lower().replace("-", "_")
            missing_docs.append({
                "document_type": doc_type,
                "type": doc_type,
                "required_by": issue.get("lc_clause") or "LC terms",
                "rule_id": rule_id,
            })
        else:
            regular_issues.append(issue)
    
    # Get processing time
    processing_summary = structured_result.get("processing_summary") or {}
    processing_time = processing_summary.get("processing_time_seconds") or 0
    
    # Get rules executed
    rules_executed = structured_result.get("rules_executed") or processing_summary.get("rules_executed") or 0
    
    return build_sme_response(
        lc_data=lc_data,
        document_summaries=document_summaries,
        issues=regular_issues,
        missing_docs=missing_docs,
        processing_time_seconds=processing_time,
        session_id=session_id,
        rules_executed=rules_executed,
    )
