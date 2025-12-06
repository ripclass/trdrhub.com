"""
LCopilot V2 - Core Types

Matches packages/shared-types/src/lcopilot-v2.ts for frontend/backend alignment.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime


# ============================================================================
# ENUMS
# ============================================================================

class DocumentType(str, Enum):
    """Supported document types."""
    LETTER_OF_CREDIT = "letter_of_credit"
    MT700 = "mt700"
    COMMERCIAL_INVOICE = "commercial_invoice"
    BILL_OF_LADING = "bill_of_lading"
    PACKING_LIST = "packing_list"
    INSURANCE_CERTIFICATE = "insurance_certificate"
    CERTIFICATE_OF_ORIGIN = "certificate_of_origin"
    INSPECTION_CERTIFICATE = "inspection_certificate"
    WEIGHT_CERTIFICATE = "weight_certificate"
    FUMIGATION_CERTIFICATE = "fumigation_certificate"
    PHYTOSANITARY_CERTIFICATE = "phytosanitary_certificate"
    BENEFICIARY_CERTIFICATE = "beneficiary_certificate"
    DRAFT = "draft"
    UNKNOWN = "unknown"


class DocumentQuality(str, Enum):
    """Document quality categories."""
    EXCELLENT = "excellent"  # >90% OCR confidence
    GOOD = "good"            # 80-90%
    MEDIUM = "medium"        # 60-80%
    POOR = "poor"            # 40-60%
    VERY_POOR = "very_poor"  # <40%


class RegionType(str, Enum):
    """Detected page regions."""
    TEXT = "text"
    TABLE = "table"
    HANDWRITING = "handwriting"
    SIGNATURE = "signature"
    STAMP = "stamp"
    LOGO = "logo"
    BARCODE = "barcode"
    QR_CODE = "qr_code"


class IssueSeverity(str, Enum):
    """Issue severity levels."""
    CRITICAL = "critical"  # Will cause rejection
    MAJOR = "major"        # High risk of rejection
    MINOR = "minor"        # May cause discrepancy
    INFO = "info"          # Informational only


class VerdictStatus(str, Enum):
    """Bank verdict statuses."""
    SUBMIT = "SUBMIT"    # Ready to submit
    CAUTION = "CAUTION"  # Submit with care
    HOLD = "HOLD"        # Do not submit yet
    REJECT = "REJECT"    # Will be rejected


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Bounds:
    """Region bounding box."""
    x: float
    y: float
    width: float
    height: float


@dataclass
class PageRegion:
    """Detected region on a page."""
    type: RegionType
    bounds: Bounds
    content: Optional[str]
    confidence: float
    page_number: int


@dataclass
class FieldConfidence:
    """Extracted field with confidence metadata."""
    value: Any
    confidence: float
    source: str  # 'ensemble', 'gpt', 'claude', 'gemini'
    provider_agreement: float  # 0.33, 0.66, 1.0
    needs_review: bool
    alternatives: Optional[List[Any]] = None
    review_reason: Optional[str] = None


@dataclass
class Citations:
    """UCP600/ISBP745 citations for issues."""
    ucp600: List[str] = field(default_factory=list)
    isbp745: List[str] = field(default_factory=list)
    urc522: List[str] = field(default_factory=list)
    urr725: List[str] = field(default_factory=list)
    swift: List[str] = field(default_factory=list)
    
    def format(self) -> str:
        """Format citations as readable string."""
        parts = []
        if self.ucp600:
            parts.append(f"UCP600 {', '.join(self.ucp600)}")
        if self.isbp745:
            parts.append(f"ISBP745 {', '.join(self.isbp745)}")
        if self.urc522:
            parts.append(f"URC522 {', '.join(self.urc522)}")
        if self.swift:
            parts.append(f"SWIFT {', '.join(self.swift)}")
        return "; ".join(parts)
    
    def to_dict(self) -> Dict[str, List[str]]:
        """Convert to dictionary."""
        return {
            "ucp600": self.ucp600,
            "isbp745": self.isbp745,
            "urc522": self.urc522,
            "urr725": self.urr725,
            "swift": self.swift,
        }


@dataclass
class Issue:
    """Validation issue with citations."""
    id: str
    rule_id: str
    title: str
    severity: IssueSeverity
    citations: Citations
    
    # Messages
    bank_message: str  # For bank examiner
    explanation: str   # For user
    
    # Discrepancy details
    expected: str
    found: str
    suggestion: str
    
    # Source documents
    documents: List[str]
    document_ids: List[str]
    
    # Amendment info
    can_amend: bool
    amendment_cost: Optional[float] = None
    amendment_days: Optional[int] = None
    
    # Confidence
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "id": self.id,
            "ruleId": self.rule_id,
            "title": self.title,
            "severity": self.severity.value,
            "citations": self.citations.to_dict(),
            "bankMessage": self.bank_message,
            "explanation": self.explanation,
            "expected": self.expected,
            "found": self.found,
            "suggestion": self.suggestion,
            "documents": self.documents,
            "documentIds": self.document_ids,
            "canAmend": self.can_amend,
            "amendmentCost": self.amendment_cost,
            "amendmentDays": self.amendment_days,
            "confidence": self.confidence,
        }


@dataclass
class IssueSummary:
    """Summary of issues by severity."""
    critical: int = 0
    major: int = 0
    minor: int = 0
    info: int = 0
    
    @property
    def total(self) -> int:
        return self.critical + self.major + self.minor + self.info
    
    def to_dict(self) -> Dict[str, int]:
        return {
            "critical": self.critical,
            "major": self.major,
            "minor": self.minor,
            "info": self.info,
            "total": self.total,
        }


@dataclass
class ActionItem:
    """Required action for user."""
    priority: str  # 'critical', 'high', 'medium', 'low'
    issue: str
    action: str


@dataclass
class Verdict:
    """Bank submission verdict."""
    status: VerdictStatus
    message: str
    recommendation: str
    confidence: float
    can_submit_to_bank: bool
    will_be_rejected: bool
    estimated_discrepancy_fee: float
    issue_summary: IssueSummary
    action_items: List[ActionItem]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.message,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "canSubmitToBank": self.can_submit_to_bank,
            "willBeRejected": self.will_be_rejected,
            "estimatedDiscrepancyFee": self.estimated_discrepancy_fee,
            "issueSummary": self.issue_summary.to_dict(),
            "actionItems": [
                {"priority": a.priority, "issue": a.issue, "action": a.action}
                for a in self.action_items
            ],
        }


@dataclass
class Amendment:
    """LC amendment draft."""
    id: str
    issue_id: str
    field_tag: str
    field_name: str
    current_value: str
    proposed_value: str
    mt707_text: str
    iso20022_xml: Optional[str]
    narrative: str
    estimated_fee_usd: float
    processing_days: int
    formats_available: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "issueId": self.issue_id,
            "field": {
                "tag": self.field_tag,
                "name": self.field_name,
                "current": self.current_value,
                "proposed": self.proposed_value,
            },
            "mt707Text": self.mt707_text,
            "iso20022Xml": self.iso20022_xml,
            "narrative": self.narrative,
            "estimatedFeeUsd": self.estimated_fee_usd,
            "processingDays": self.processing_days,
            "formatsAvailable": self.formats_available,
        }


@dataclass
class DocumentQualityInfo:
    """Document quality metrics."""
    overall: float
    ocr_confidence: float
    category: DocumentQuality


@dataclass
class DocumentRegions:
    """Detected regions in document."""
    has_handwriting: bool
    has_signatures: bool
    has_stamps: bool
    handwriting_count: int
    signature_count: int
    stamp_count: int
    details: List[PageRegion] = field(default_factory=list)


@dataclass
class DocumentResult:
    """Processed document result."""
    id: str
    filename: str
    document_type: DocumentType
    quality: DocumentQualityInfo
    regions: DocumentRegions
    extracted: Dict[str, FieldConfidence]
    processing_time_ms: int
    pages_processed: int
    status: str  # 'success', 'partial', 'failed'
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "documentType": self.document_type.value,
            "quality": {
                "overall": self.quality.overall,
                "ocrConfidence": self.quality.ocr_confidence,
                "category": self.quality.category.value,
            },
            "regions": {
                "hasHandwriting": self.regions.has_handwriting,
                "hasSignatures": self.regions.has_signatures,
                "hasStamps": self.regions.has_stamps,
                "handwritingCount": self.regions.handwriting_count,
                "signatureCount": self.regions.signature_count,
                "stampCount": self.regions.stamp_count,
            },
            "extracted": {
                k: {
                    "value": v.value,
                    "confidence": v.confidence,
                    "source": v.source,
                    "providerAgreement": v.provider_agreement,
                    "needsReview": v.needs_review,
                }
                for k, v in self.extracted.items()
            },
            "processingTimeMs": self.processing_time_ms,
            "pagesProcessed": self.pages_processed,
            "status": self.status,
            "errors": self.errors,
        }


@dataclass
class SanctionsMatch:
    """Sanctions screening match."""
    party: str
    party_type: str
    list_name: str
    match_score: float
    match_type: str  # 'exact', 'fuzzy', 'alias'
    sanction_programs: List[str]


@dataclass
class SanctionsStatus:
    """Sanctions screening result."""
    screened: bool
    parties_screened: int
    matches_found: int
    status: str  # 'clear', 'potential_match', 'match', 'blocked'
    matches: List[SanctionsMatch] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "screened": self.screened,
            "partiesScreened": self.parties_screened,
            "matchesFound": self.matches_found,
            "status": self.status,
            "matches": [
                {
                    "party": m.party,
                    "partyType": m.party_type,
                    "listName": m.list_name,
                    "matchScore": m.match_score,
                    "matchType": m.match_type,
                    "sanctionPrograms": m.sanction_programs,
                }
                for m in self.matches
            ],
        }


@dataclass
class ComplianceInfo:
    """Compliance scores."""
    sanctions_status: SanctionsStatus
    ucp_compliance: float  # 0-100
    isbp_compliance: float  # 0-100
    overall_score: float  # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sanctionsStatus": self.sanctions_status.to_dict(),
            "ucpCompliance": self.ucp_compliance,
            "isbpCompliance": self.isbp_compliance,
            "overallScore": self.overall_score,
        }


@dataclass
class QualityMetrics:
    """Overall quality metrics."""
    overall_confidence: float
    fields_needing_review: List[str]
    poor_quality_documents: List[str]
    handwriting_detected: bool
    providers_used: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "overallConfidence": self.overall_confidence,
            "fieldsNeedingReview": self.fields_needing_review,
            "poorQualityDocuments": self.poor_quality_documents,
            "handwritingDetected": self.handwriting_detected,
            "providersUsed": self.providers_used,
        }


@dataclass
class AuditInfo:
    """Audit trail information."""
    rules_evaluated: int
    rules_passed: int
    rules_failed: int
    cross_doc_checks: int
    ai_providers_used: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rulesEvaluated": self.rules_evaluated,
            "rulesPassed": self.rules_passed,
            "rulesFailed": self.rules_failed,
            "crossDocChecks": self.cross_doc_checks,
            "aiProvidersUsed": self.ai_providers_used,
        }


@dataclass
class LCopilotV2Response:
    """Complete V2 validation response."""
    session_id: str
    version: str = "v2"
    processing_time_seconds: float = 0.0
    
    verdict: Optional[Verdict] = None
    documents: List[DocumentResult] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)
    amendments: List[Amendment] = field(default_factory=list)
    
    extracted_data: Dict[str, Dict[str, FieldConfidence]] = field(default_factory=dict)
    compliance: Optional[ComplianceInfo] = None
    quality: Optional[QualityMetrics] = None
    audit: Optional[AuditInfo] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        result = {
            "sessionId": self.session_id,
            "version": self.version,
            "processingTimeSeconds": self.processing_time_seconds,
        }
        
        if self.verdict:
            result["verdict"] = self.verdict.to_dict()
        
        result["documents"] = [d.to_dict() for d in self.documents]
        result["issues"] = [i.to_dict() for i in self.issues]
        result["amendments"] = [a.to_dict() for a in self.amendments]
        
        # Extracted data
        result["extractedData"] = {}
        for doc_type, fields in self.extracted_data.items():
            result["extractedData"][doc_type] = {
                k: {
                    "value": v.value,
                    "confidence": v.confidence,
                    "source": v.source,
                    "providerAgreement": v.provider_agreement,
                    "needsReview": v.needs_review,
                }
                for k, v in fields.items()
            }
        
        if self.compliance:
            result["compliance"] = self.compliance.to_dict()
        
        if self.quality:
            result["quality"] = self.quality.to_dict()
        
        if self.audit:
            result["audit"] = self.audit.to_dict()
        
        return result

