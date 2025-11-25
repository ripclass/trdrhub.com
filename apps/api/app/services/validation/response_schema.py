"""
Validation Response Schema - Phase B: API Response Schema Alignment

Defines the contract between backend validation pipeline and frontend consumers.
This ensures the frontend can correctly parse and display validation results.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class GateResultSchema:
    """Gate check result - determines if validation can proceed."""
    status: str  # "passed" | "blocked" | "warning"
    can_proceed: bool
    block_reason: Optional[str] = None
    completeness: float = 0.0  # 0-1 scale
    critical_completeness: float = 0.0  # 0-1 scale
    missing_critical: List[str] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    blocking_issues: List[Dict[str, Any]] = field(default_factory=list)
    warning_issues: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "can_proceed": self.can_proceed,
            "block_reason": self.block_reason,
            "completeness": round(self.completeness * 100, 1),  # Convert to percentage
            "critical_completeness": round(self.critical_completeness * 100, 1),
            "missing_critical": self.missing_critical,
            "missing_required": self.missing_required,
            "blocking_issues": self.blocking_issues,
            "warning_issues": self.warning_issues,
        }


@dataclass
class ExtractionSummarySchema:
    """Summary of LC extraction quality."""
    completeness: float  # 0-100 percentage
    critical_completeness: float  # 0-100 percentage
    missing_critical: List[str] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    total_fields: int = 0
    extracted_fields: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "completeness": round(self.completeness, 1),
            "critical_completeness": round(self.critical_completeness, 1),
            "missing_critical": self.missing_critical,
            "missing_required": self.missing_required,
            "total_fields": self.total_fields,
            "extracted_fields": self.extracted_fields,
        }


@dataclass
class LCBaselineSchema:
    """Structured LC baseline data for frontend display."""
    lc_number: Optional[str] = None
    lc_type: Optional[str] = None
    applicant: Optional[str] = None
    beneficiary: Optional[str] = None
    issuing_bank: Optional[str] = None
    advising_bank: Optional[str] = None
    amount: Optional[str] = None
    currency: Optional[str] = None
    expiry_date: Optional[str] = None
    issue_date: Optional[str] = None
    latest_shipment: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    goods_description: Optional[str] = None
    incoterm: Optional[str] = None
    extraction_completeness: float = 0.0  # 0-100 percentage
    critical_completeness: float = 0.0  # 0-100 percentage
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "lc_number": self.lc_number,
            "lc_type": self.lc_type,
            "applicant": self.applicant,
            "beneficiary": self.beneficiary,
            "issuing_bank": self.issuing_bank,
            "advising_bank": self.advising_bank,
            "amount": self.amount,
            "currency": self.currency,
            "expiry_date": self.expiry_date,
            "issue_date": self.issue_date,
            "latest_shipment": self.latest_shipment,
            "port_of_loading": self.port_of_loading,
            "port_of_discharge": self.port_of_discharge,
            "goods_description": self.goods_description,
            "incoterm": self.incoterm,
            "extraction_completeness": round(self.extraction_completeness, 1),
            "critical_completeness": round(self.critical_completeness, 1),
        }


@dataclass
class IssueSchema:
    """Single validation issue."""
    id: str
    rule: str
    title: str
    severity: str  # "critical" | "major" | "minor" | "info"
    message: str
    expected: str
    found: str  # Also known as 'actual'
    suggested_fix: str
    documents: List[str] = field(default_factory=list)
    ucp_reference: Optional[str] = None
    isbp_reference: Optional[str] = None
    field: Optional[str] = None
    blocks_validation: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rule": self.rule,
            "title": self.title,
            "severity": self.severity,
            "message": self.message,
            "description": self.message,  # Alias for frontend
            "expected": self.expected,
            "found": self.found,
            "actual": self.found,  # Alias for frontend
            "suggested_fix": self.suggested_fix,
            "documents": self.documents,
            "ucp_reference": self.ucp_reference,
            "isbp_reference": self.isbp_reference,
            "field": self.field,
            "blocks_validation": self.blocks_validation,
        }


@dataclass
class AnalyticsSchema:
    """Analytics data for the validation."""
    extraction_accuracy: int = 0  # 0-100
    lc_compliance_score: int = 0  # 0-100
    compliance_level: str = "non_compliant"
    compliance_cap_reason: Optional[str] = None
    customs_ready_score: int = 0  # 0-100
    documents_processed: int = 0
    document_status_distribution: Dict[str, int] = field(default_factory=lambda: {
        "success": 0,
        "warning": 0,
        "error": 0,
    })
    issue_counts: Dict[str, int] = field(default_factory=lambda: {
        "critical": 0,
        "major": 0,
        "minor": 0,
    })
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "extraction_accuracy": self.extraction_accuracy,
            "lc_compliance_score": self.lc_compliance_score,
            "compliance_level": self.compliance_level,
            "compliance_cap_reason": self.compliance_cap_reason,
            "customs_ready_score": self.customs_ready_score,
            "documents_processed": self.documents_processed,
            "document_status_distribution": self.document_status_distribution,
            "issue_counts": self.issue_counts,
        }


@dataclass
class ProcessingSummarySchema:
    """Summary of validation processing."""
    documents: int = 0
    verified: int = 0
    warnings: int = 0
    errors: int = 0
    discrepancies: int = 0
    compliance_rate: int = 0  # 0-100
    processing_time_seconds: float = 0.0
    processing_time_display: str = ""
    status_counts: Dict[str, int] = field(default_factory=lambda: {
        "success": 0,
        "warning": 0,
        "error": 0,
    })
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "documents": self.documents,
            "verified": self.verified,
            "warnings": self.warnings,
            "errors": self.errors,
            "discrepancies": self.discrepancies,
            "compliance_rate": self.compliance_rate,
            "processing_time_seconds": round(self.processing_time_seconds, 2),
            "processing_time_display": self.processing_time_display,
            "status_counts": self.status_counts,
            # Frontend compatibility fields
            "total_documents": self.documents,
            "successful_extractions": self.verified,
            "failed_extractions": self.errors,
            "total_issues": self.discrepancies,
        }


@dataclass
class ValidationResponseSchema:
    """
    Complete validation response schema.
    
    This is the contract between backend and frontend.
    The frontend expects all these fields to be present in structured_result.
    """
    # Job identification
    job_id: str
    
    # V2 validation status
    validation_blocked: bool = False
    validation_status: str = "non_compliant"
    
    # Gate result (always present)
    gate_result: Optional[GateResultSchema] = None
    
    # Extraction metrics
    extraction_summary: Optional[ExtractionSummarySchema] = None
    
    # LC baseline (structured LC data)
    lc_baseline: Optional[LCBaselineSchema] = None
    
    # Processing summary
    processing_summary: Optional[ProcessingSummarySchema] = None
    
    # Issues
    issues: List[IssueSchema] = field(default_factory=list)
    
    # Analytics
    analytics: Optional[AnalyticsSchema] = None
    
    # Document list
    documents_structured: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timeline
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    
    # Legacy fields
    version: str = "structured_result_v1"
    lc_type: Optional[str] = None
    lc_structured: Optional[Dict[str, Any]] = None
    customs_pack: Optional[Dict[str, Any]] = None
    ai_enrichment: Optional[Dict[str, Any]] = None
    
    # Audit
    audit_trail_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result = {
            "version": self.version,
            
            # V2 fields
            "validation_blocked": self.validation_blocked,
            "validation_status": self.validation_status,
            "gate_result": self.gate_result.to_dict() if self.gate_result else None,
            "extraction_summary": self.extraction_summary.to_dict() if self.extraction_summary else None,
            "lc_baseline": self.lc_baseline.to_dict() if self.lc_baseline else None,
            
            # Standard fields
            "processing_summary": self.processing_summary.to_dict() if self.processing_summary else None,
            "issues": [i.to_dict() if hasattr(i, 'to_dict') else i for i in self.issues],
            "analytics": self.analytics.to_dict() if self.analytics else None,
            "documents_structured": self.documents_structured,
            "timeline": self.timeline,
            
            # Legacy fields
            "lc_type": self.lc_type,
            "lc_structured": self.lc_structured,
            "customs_pack": self.customs_pack,
            "ai_enrichment": self.ai_enrichment,
            
            # Audit
            "audit_trail_id": self.audit_trail_id,
        }
        
        return result
    
    @classmethod
    def from_pipeline_output(cls, output: "ValidationOutput") -> "ValidationResponseSchema":
        """Create schema from ValidationOutput."""
        from app.services.validation.pipeline import ValidationOutput
        
        gate = GateResultSchema(
            status="blocked" if output.validation_blocked else "passed",
            can_proceed=not output.validation_blocked,
            block_reason=output.block_reason,
            completeness=output.extraction_completeness / 100,  # Convert to 0-1
            critical_completeness=output.critical_completeness / 100,
            missing_critical=output.missing_critical_fields,
        )
        
        extraction = ExtractionSummarySchema(
            completeness=output.extraction_completeness,
            critical_completeness=output.critical_completeness,
            missing_critical=output.missing_critical_fields,
        )
        
        analytics = AnalyticsSchema(
            extraction_accuracy=int(round(output.extraction_completeness)),
            lc_compliance_score=int(round(output.compliance_score)),
            compliance_level=output.compliance_level,
            issue_counts={
                "critical": output.critical_count,
                "major": output.major_count,
                "minor": output.minor_count,
            }
        )
        
        summary = ProcessingSummarySchema(
            discrepancies=output.issue_count,
            compliance_rate=int(round(output.compliance_score)),
            processing_time_seconds=output.processing_time_seconds,
            processing_time_display=output.processing_time_display,
            errors=output.critical_count,
            warnings=output.major_count + output.minor_count,
        )
        
        return cls(
            job_id=output.job_id,
            validation_blocked=output.validation_blocked,
            validation_status=output.status,
            gate_result=gate,
            extraction_summary=extraction,
            processing_summary=summary,
            issues=output.issues,  # Already list of dicts
            analytics=analytics,
            audit_trail_id=output.audit_trail_id,
        )


def build_v2_structured_result(
    existing_result: Dict[str, Any],
    gate_result: Optional[Dict[str, Any]] = None,
    baseline: Optional[Dict[str, Any]] = None,
    compliance_score: float = 0.0,
    compliance_level: str = "non_compliant",
    compliance_cap_reason: Optional[str] = None,
    validation_blocked: bool = False,
) -> Dict[str, Any]:
    """
    Merge v2 validation data into existing structured_result.
    
    This is a helper for Phase A integration - it merges v2 fields
    into the existing Option-E structured_result without breaking
    backward compatibility.
    """
    result = dict(existing_result)
    
    # Add v2 fields
    result["validation_blocked"] = validation_blocked
    result["validation_status"] = "blocked" if validation_blocked else compliance_level
    
    if gate_result:
        result["gate_result"] = gate_result
    
    if baseline:
        result["lc_baseline"] = baseline
        
    # Add extraction summary from gate result
    if gate_result:
        result["extraction_summary"] = {
            "completeness": gate_result.get("completeness", 0),
            "critical_completeness": gate_result.get("critical_completeness", 0),
            "missing_critical": gate_result.get("missing_critical", []),
            "missing_required": gate_result.get("missing_required", []),
        }
    
    # Update analytics with v2 scoring
    if "analytics" not in result:
        result["analytics"] = {}
    
    result["analytics"]["lc_compliance_score"] = int(round(compliance_score))
    result["analytics"]["compliance_level"] = compliance_level
    if compliance_cap_reason:
        result["analytics"]["compliance_cap_reason"] = compliance_cap_reason
    
    # Update processing_summary compliance_rate
    if "processing_summary" not in result:
        result["processing_summary"] = {}
    result["processing_summary"]["compliance_rate"] = int(round(compliance_score))
    
    return result

