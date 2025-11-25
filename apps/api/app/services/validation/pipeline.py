"""
Validation Pipeline v2.0 - Central Orchestrator

This module orchestrates the entire validation flow:
1. LC Extraction → LCBaseline
2. Validation Gate check (blocks if LC extraction fails)
3. Issue generation from missing fields
4. Cross-document validation (UCP600 rules)
5. Compliance scoring (severity-based)
6. Audit trail capture

CORE PRINCIPLE: Validation is BLOCKED if LC extraction fails.
No more "100% compliant with N/A fields".
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import uuid4

from app.services.extraction.lc_baseline import LCBaseline, FieldResult, FieldPriority, ExtractionStatus
from app.services.extraction.lc_extractor_v2 import extract_lc_with_baseline, LCExtractionResult
from app.services.validation.validation_gate import (
    ValidationGate,
    GateResult,
    GateStatus,
    create_blocked_response,
)
from app.services.validation.issue_engine import (
    IssueEngine,
    IssueEngineResult,
    Issue,
    IssueSeverity,
)
from app.services.validation.compliance_scorer import (
    ComplianceScorer,
    ComplianceScore,
    ComplianceLevel,
)
from app.services.validation.crossdoc_validator import (
    CrossDocValidator,
    CrossDocResult,
)
from app.services.validation.audit_logger import (
    ValidationAuditLogger,
    AuditEventType,
    create_audit_logger,
)


logger = logging.getLogger(__name__)


@dataclass
class ValidationInput:
    """Input to the validation pipeline."""
    # Session info
    job_id: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # LC data
    lc_text: Optional[str] = None
    lc_context: Optional[Dict[str, Any]] = None
    
    # Supporting documents
    invoice: Optional[Dict[str, Any]] = None
    bill_of_lading: Optional[Dict[str, Any]] = None
    insurance: Optional[Dict[str, Any]] = None
    certificate_of_origin: Optional[Dict[str, Any]] = None
    packing_list: Optional[Dict[str, Any]] = None
    
    # Document list (raw)
    documents: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    document_tags: Optional[Dict[str, str]] = None
    lc_type: str = "unknown"
    user_type: str = "exporter"


@dataclass
class ValidationOutput:
    """Output from the validation pipeline."""
    # Core results
    job_id: str
    status: str  # "blocked" | "non_compliant" | "partial" | "mostly_compliant" | "compliant"
    validation_blocked: bool
    
    # Scores
    compliance_score: float
    compliance_level: str
    extraction_completeness: float
    critical_completeness: float
    
    # Issues
    issues: List[Dict[str, Any]]
    issue_count: int
    critical_count: int
    major_count: int
    minor_count: int
    
    # Gate result (if blocked)
    gate_result: Optional[Dict[str, Any]] = None
    block_reason: Optional[str] = None
    
    # Baseline data
    lc_baseline: Optional[Dict[str, Any]] = None
    missing_critical_fields: List[str] = field(default_factory=list)
    
    # Cross-doc results
    crossdoc_result: Optional[Dict[str, Any]] = None
    
    # Processing info
    processing_time_seconds: float = 0.0
    processing_time_display: str = ""
    
    # Audit
    audit_trail_id: Optional[str] = None
    
    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format compatible with frontend."""
        return {
            "job_id": self.job_id,
            "jobId": self.job_id,
            
            # Validation status
            "validation_blocked": self.validation_blocked,
            "validation_status": self.status,
            
            # Gate result (always include for frontend state machine)
            "gate_result": self.gate_result or {
                "status": "passed" if not self.validation_blocked else "blocked",
                "can_proceed": not self.validation_blocked,
                "block_reason": self.block_reason,
                "completeness": self.extraction_completeness,
                "critical_completeness": self.critical_completeness,
                "missing_critical": self.missing_critical_fields,
            },
            
            # Processing summary
            "processing_summary": {
                "documents": len(self.issues),  # Will be overwritten by caller
                "verified": 0,
                "warnings": self.major_count + self.minor_count,
                "errors": self.critical_count,
                "discrepancies": self.issue_count,
                "compliance_rate": int(round(self.compliance_score)),
                "processing_time_seconds": round(self.processing_time_seconds, 2),
                "processing_time_display": self.processing_time_display,
                "status_counts": {
                    "success": 0,
                    "warning": self.major_count + self.minor_count,
                    "error": self.critical_count,
                },
            },
            
            # Issues
            "issues": self.issues,
            "issue_cards": self.issues,
            
            # Extraction summary
            "extraction_summary": {
                "completeness": round(self.extraction_completeness * 100, 1),
                "critical_completeness": round(self.critical_completeness * 100, 1),
                "missing_critical": self.missing_critical_fields,
            },
            
            # Analytics (compliance)
            "analytics": {
                "extraction_accuracy": round(self.extraction_completeness * 100),
                "lc_compliance_score": int(round(self.compliance_score)),
                "customs_ready_score": 0 if self.validation_blocked else int(round(self.compliance_score * 0.8)),
                "documents_processed": 0,  # Will be overwritten
                "document_status_distribution": {
                    "success": 0,
                    "warning": self.major_count,
                    "error": self.critical_count,
                },
            },
            
            # Cross-doc results
            "crossdoc_result": self.crossdoc_result,
            
            # LC Baseline
            "lc_baseline": self.lc_baseline,
            
            # Audit
            "audit_trail_id": self.audit_trail_id,
        }


class ValidationPipeline:
    """
    Central validation orchestrator.
    
    Executes the full v2.0 validation flow with proper gating.
    """
    
    def __init__(
        self,
        gate: Optional[ValidationGate] = None,
        issue_engine: Optional[IssueEngine] = None,
        crossdoc_validator: Optional[CrossDocValidator] = None,
        compliance_scorer: Optional[ComplianceScorer] = None,
    ):
        self.gate = gate or ValidationGate()
        self.issue_engine = issue_engine or IssueEngine()
        self.crossdoc_validator = crossdoc_validator or CrossDocValidator()
        self.compliance_scorer = compliance_scorer or ComplianceScorer()
    
    def validate(
        self,
        input_data: ValidationInput,
    ) -> ValidationOutput:
        """
        Execute the full validation pipeline.
        
        Flow:
        1. Start audit trail
        2. Extract LC → LCBaseline
        3. Check validation gate
        4. If blocked → return blocked response
        5. Generate extraction issues
        6. Run cross-document validation
        7. Calculate compliance score
        8. Build final output
        """
        start_time = time.time()
        
        # Initialize audit logger
        audit_logger = create_audit_logger(
            session_id=input_data.session_id,
            job_id=input_data.job_id,
            user_id=input_data.user_id,
        )
        
        # Log validation start
        audit_logger.log_validation_started(
            document_count=len(input_data.documents),
            document_types=[d.get("document_type", "unknown") for d in input_data.documents],
        )
        
        try:
            # Step 1: Extract LC to baseline
            baseline, extraction_result = self._extract_lc(input_data, audit_logger)
            
            # Step 2: Check validation gate
            gate_result = self._check_gate(baseline, extraction_result, audit_logger)
            
            # Step 3: If blocked, return early
            if not gate_result.can_proceed:
                return self._build_blocked_output(
                    input_data,
                    gate_result,
                    baseline,
                    audit_logger,
                    start_time,
                )
            
            # Step 4: Generate extraction issues
            extraction_issues = self._generate_extraction_issues(baseline, audit_logger)
            
            # Step 5: Run cross-document validation
            crossdoc_result = self._run_crossdoc_validation(
                baseline,
                input_data,
                audit_logger,
            )
            
            # Step 6: Combine all issues
            all_issues = self._combine_issues(extraction_issues, crossdoc_result, gate_result)
            
            # Step 7: Calculate compliance score
            score_result = self._calculate_score(
                baseline,
                all_issues,
                gate_result,
                audit_logger,
            )
            
            # Step 8: Build final output
            output = self._build_output(
                input_data,
                baseline,
                gate_result,
                all_issues,
                crossdoc_result,
                score_result,
                audit_logger,
                start_time,
            )
            
            # Log completion
            processing_time = time.time() - start_time
            audit_logger.log_validation_completed(
                status=output.status,
                compliance_score=output.compliance_score,
                issues_count=output.issue_count,
                processing_time_ms=processing_time * 1000,
            )
            
            return output
            
        except Exception as e:
            logger.error(f"Validation pipeline error: {e}", exc_info=True)
            raise
    
    def _extract_lc(
        self,
        input_data: ValidationInput,
        audit_logger: ValidationAuditLogger,
    ) -> Tuple[LCBaseline, Optional[LCExtractionResult]]:
        """Extract LC data to baseline."""
        
        # Try to build baseline from existing context
        if input_data.lc_context:
            baseline = self._build_baseline_from_context(input_data.lc_context)
            return baseline, None
        
        # Extract from raw text
        if input_data.lc_text:
            extraction_result = extract_lc_with_baseline(input_data.lc_text)
            
            # Log field extractions
            for field_result in extraction_result.baseline.get_all_fields():
                if field_result.is_present:
                    audit_logger.log_field_extracted(
                        field_name=field_result.field_name,
                        value=field_result.value,
                        confidence=field_result.confidence,
                    )
                else:
                    audit_logger.log_field_missing(
                        field_name=field_result.field_name,
                        priority=field_result.priority.value,
                        reasoning=f"Field not found in LC text",
                    )
            
            return extraction_result.baseline, extraction_result
        
        # No LC data - return empty baseline
        return LCBaseline(), None
    
    def _build_baseline_from_context(
        self,
        lc_context: Dict[str, Any],
    ) -> LCBaseline:
        """Build LCBaseline from existing extracted context."""
        baseline = LCBaseline()
        
        # Map context fields to baseline
        field_mapping = {
            "number": "lc_number",
            "lc_number": "lc_number",
            "amount": "amount",
            "currency": "currency",
            "applicant": "applicant",
            "beneficiary": "beneficiary",
            "issuing_bank": "issuing_bank",
            "advising_bank": "advising_bank",
            "expiry_date": "expiry_date",
            "issue_date": "issue_date",
            "latest_shipment": "latest_shipment",
            "port_of_loading": "port_of_loading",
            "port_of_discharge": "port_of_discharge",
            "goods_description": "goods_description",
            "description": "goods_description",
            "incoterm": "incoterm",
        }
        
        for context_key, baseline_field in field_mapping.items():
            value = lc_context.get(context_key)
            if value and hasattr(baseline, baseline_field):
                field_result = getattr(baseline, baseline_field)
                if isinstance(field_result, FieldResult):
                    field_result.value = value
                    field_result.is_present = True
                    field_result.status = ExtractionStatus.EXTRACTED
        
        return baseline
    
    def _check_gate(
        self,
        baseline: LCBaseline,
        extraction_result: Optional[LCExtractionResult],
        audit_logger: ValidationAuditLogger,
    ) -> GateResult:
        """Check validation gate."""
        
        if extraction_result:
            gate_result = self.gate.check_from_extraction(extraction_result)
        else:
            gate_result = self.gate.check_from_baseline(baseline)
        
        # Log gate checks
        audit_logger.log_gate_check(
            check_name="lc_number",
            passed=baseline.lc_number.is_present,
            expected="LC reference number",
            actual=str(baseline.lc_number.value) if baseline.lc_number.is_present else "Not found",
            reasoning="LC number is required to identify the credit",
        )
        
        audit_logger.log_gate_check(
            check_name="amount",
            passed=baseline.amount.is_present,
            expected="Credit amount",
            actual=str(baseline.amount.value) if baseline.amount.is_present else "Not found",
            reasoning="Amount is required for invoice validation",
        )
        
        audit_logger.log_gate_check(
            check_name="parties",
            passed=baseline.applicant.is_present or baseline.beneficiary.is_present,
            expected="At least one party (applicant/beneficiary)",
            actual="Found" if (baseline.applicant.is_present or baseline.beneficiary.is_present) else "Neither found",
            reasoning="Party information is required for document matching",
        )
        
        return gate_result
    
    def _generate_extraction_issues(
        self,
        baseline: LCBaseline,
        audit_logger: ValidationAuditLogger,
    ) -> List[Issue]:
        """Generate issues for missing fields."""
        issues = self.issue_engine.generate_extraction_issues(baseline)
        
        # Log issue generation
        for issue in issues:
            audit_logger.log_issue_generated(
                issue_id=issue.id,
                title=issue.title,
                severity=issue.severity.value,
                rule_id=issue.rule,
                reasoning=f"Missing {issue.field_name} field",
            )
        
        return issues
    
    def _run_crossdoc_validation(
        self,
        baseline: LCBaseline,
        input_data: ValidationInput,
        audit_logger: ValidationAuditLogger,
    ) -> CrossDocResult:
        """Run cross-document validation."""
        
        result = self.crossdoc_validator.validate_all(
            lc_baseline=baseline,
            invoice=input_data.invoice,
            bill_of_lading=input_data.bill_of_lading,
            insurance=input_data.insurance,
            certificate_of_origin=input_data.certificate_of_origin,
            packing_list=input_data.packing_list,
        )
        
        # Log crossdoc checks
        for issue in result.issues:
            audit_logger.log_crossdoc_check(
                check_name=issue.rule_id,
                source_doc=issue.source_doc.value,
                target_doc=issue.target_doc.value,
                passed=False,
                expected=issue.expected,
                actual=issue.found,
                reasoning=issue.message,
            )
        
        return result
    
    def _combine_issues(
        self,
        extraction_issues: List[Issue],
        crossdoc_result: CrossDocResult,
        gate_result: GateResult,
    ) -> List[Dict[str, Any]]:
        """Combine all issues into a single list."""
        all_issues = []
        
        # Add extraction issues
        for issue in extraction_issues:
            all_issues.append(issue.to_dict())
        
        # Add crossdoc issues
        for issue in crossdoc_result.issues:
            all_issues.append(issue.to_dict())
        
        # Add gate warning issues (if any)
        for issue in gate_result.warning_issues:
            all_issues.append(issue)
        
        return all_issues
    
    def _calculate_score(
        self,
        baseline: LCBaseline,
        all_issues: List[Dict[str, Any]],
        gate_result: GateResult,
        audit_logger: ValidationAuditLogger,
    ) -> ComplianceScore:
        """Calculate compliance score."""
        
        score_result = self.compliance_scorer.calculate_from_issues(
            all_issues,
            extraction_completeness=baseline.extraction_completeness,
        )
        
        # Log score calculation
        audit_logger.log_score_calculated(
            score=score_result.score,
            components={
                "extraction": score_result.extraction_score,
                "rule": score_result.rule_score,
                "document": score_result.document_score,
            },
            reasoning=f"Based on {score_result.critical_count} critical, {score_result.major_count} major, {score_result.minor_count} minor issues",
        )
        
        if score_result.cap_reason:
            audit_logger.log_score_capped(
                original_score=score_result.extraction_score,
                capped_score=score_result.score,
                cap_reason=score_result.cap_reason,
            )
        
        return score_result
    
    def _build_blocked_output(
        self,
        input_data: ValidationInput,
        gate_result: GateResult,
        baseline: LCBaseline,
        audit_logger: ValidationAuditLogger,
        start_time: float,
    ) -> ValidationOutput:
        """Build output for blocked validation."""
        
        processing_time = time.time() - start_time
        
        # Log blocked
        audit_logger.log_validation_blocked(
            reason=gate_result.block_reason or "LC extraction failed",
            missing_fields=gate_result.missing_critical,
        )
        
        return ValidationOutput(
            job_id=input_data.job_id,
            status="blocked",
            validation_blocked=True,
            compliance_score=0.0,
            compliance_level="blocked",
            extraction_completeness=gate_result.completeness,
            critical_completeness=gate_result.critical_completeness,
            issues=gate_result.get_all_issues(),
            issue_count=len(gate_result.blocking_issues) + len(gate_result.warning_issues),
            critical_count=len(gate_result.blocking_issues),
            major_count=0,
            minor_count=len(gate_result.warning_issues),
            gate_result=gate_result.to_dict(),
            block_reason=gate_result.block_reason,
            lc_baseline=self._baseline_to_dict(baseline),
            missing_critical_fields=gate_result.missing_critical,
            processing_time_seconds=processing_time,
            processing_time_display=self._format_time(processing_time),
            audit_trail_id=audit_logger.trail.trail_id,
        )
    
    def _build_output(
        self,
        input_data: ValidationInput,
        baseline: LCBaseline,
        gate_result: GateResult,
        all_issues: List[Dict[str, Any]],
        crossdoc_result: CrossDocResult,
        score_result: ComplianceScore,
        audit_logger: ValidationAuditLogger,
        start_time: float,
    ) -> ValidationOutput:
        """Build final validation output."""
        
        processing_time = time.time() - start_time
        
        # Determine status from score
        status = score_result.level.value
        
        return ValidationOutput(
            job_id=input_data.job_id,
            status=status,
            validation_blocked=False,
            compliance_score=score_result.score,
            compliance_level=score_result.level.value,
            extraction_completeness=baseline.extraction_completeness,
            critical_completeness=baseline.critical_completeness,
            issues=all_issues,
            issue_count=len(all_issues),
            critical_count=score_result.critical_count,
            major_count=score_result.major_count,
            minor_count=score_result.minor_count,
            gate_result=gate_result.to_dict(),
            block_reason=None,
            lc_baseline=self._baseline_to_dict(baseline),
            missing_critical_fields=[f.field_name for f in baseline.get_missing_critical()],
            crossdoc_result=crossdoc_result.to_dict(),
            processing_time_seconds=processing_time,
            processing_time_display=self._format_time(processing_time),
            audit_trail_id=audit_logger.trail.trail_id,
        )
    
    def _baseline_to_dict(self, baseline: LCBaseline) -> Dict[str, Any]:
        """Convert LCBaseline to dict for API response."""
        return {
            "lc_number": baseline.lc_number.value,
            "lc_type": baseline.lc_type.value,
            "applicant": baseline.applicant.value,
            "beneficiary": baseline.beneficiary.value,
            "issuing_bank": baseline.issuing_bank.value,
            "advising_bank": baseline.advising_bank.value,
            "amount": baseline.amount.value,
            "currency": baseline.currency.value,
            "expiry_date": baseline.expiry_date.value,
            "issue_date": baseline.issue_date.value,
            "latest_shipment": baseline.latest_shipment.value,
            "port_of_loading": baseline.port_of_loading.value,
            "port_of_discharge": baseline.port_of_discharge.value,
            "goods_description": baseline.goods_description.value,
            "incoterm": baseline.incoterm.value,
            "extraction_completeness": round(baseline.extraction_completeness * 100, 1),
            "critical_completeness": round(baseline.critical_completeness * 100, 1),
        }
    
    def _format_time(self, seconds: float) -> str:
        """Format processing time for display."""
        if seconds < 1:
            return f"{int(seconds * 1000)}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"


def run_validation_pipeline(
    job_id: str,
    lc_context: Optional[Dict[str, Any]] = None,
    lc_text: Optional[str] = None,
    invoice: Optional[Dict[str, Any]] = None,
    bill_of_lading: Optional[Dict[str, Any]] = None,
    insurance: Optional[Dict[str, Any]] = None,
    documents: Optional[List[Dict[str, Any]]] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to run the validation pipeline.
    
    Returns API-ready response dict.
    """
    pipeline = ValidationPipeline()
    
    input_data = ValidationInput(
        job_id=job_id,
        session_id=session_id,
        user_id=user_id,
        lc_context=lc_context,
        lc_text=lc_text,
        invoice=invoice,
        bill_of_lading=bill_of_lading,
        insurance=insurance,
        documents=documents or [],
    )
    
    output = pipeline.validate(input_data)
    return output.to_api_response()

