"""
Audit Logger - Phase 9: Auditability & Test Suite

This module provides comprehensive audit logging for all validation decisions.
Every validation action is logged with:
- What was checked
- What was expected
- What was found
- Why the decision was made
- Who/what initiated it
- When it happened

This ensures bank-grade auditability for compliance reviews.
"""

from __future__ import annotations

import logging
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum


logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""
    # Validation lifecycle
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    VALIDATION_BLOCKED = "validation_blocked"
    VALIDATION_ERROR = "validation_error"
    
    # Gate checks
    GATE_CHECK_STARTED = "gate_check_started"
    GATE_CHECK_PASSED = "gate_check_passed"
    GATE_CHECK_FAILED = "gate_check_failed"
    
    # Extraction
    EXTRACTION_STARTED = "extraction_started"
    EXTRACTION_COMPLETED = "extraction_completed"
    FIELD_EXTRACTED = "field_extracted"
    FIELD_MISSING = "field_missing"
    FIELD_INVALID = "field_invalid"
    
    # Rule execution
    RULE_EXECUTED = "rule_executed"
    RULE_PASSED = "rule_passed"
    RULE_FAILED = "rule_failed"
    RULE_SKIPPED = "rule_skipped"
    
    # Cross-document
    CROSSDOC_CHECK_STARTED = "crossdoc_check_started"
    CROSSDOC_CHECK_COMPLETED = "crossdoc_check_completed"
    CROSSDOC_MATCH = "crossdoc_match"
    CROSSDOC_MISMATCH = "crossdoc_mismatch"
    
    # Scoring
    SCORE_CALCULATED = "score_calculated"
    SCORE_CAPPED = "score_capped"
    
    # Issue generation
    ISSUE_GENERATED = "issue_generated"
    ISSUE_SEVERITY_ASSIGNED = "issue_severity_assigned"


class AuditSeverity(str, Enum):
    """Severity of audit events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """A single audit event."""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    
    # What happened
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    session_id: Optional[str] = None
    job_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Rule/check context
    rule_id: Optional[str] = None
    document_type: Optional[str] = None
    field_name: Optional[str] = None
    
    # Decision details
    expected: Optional[str] = None
    actual: Optional[str] = None
    decision: Optional[str] = None
    reasoning: Optional[str] = None
    
    # References
    ucp_reference: Optional[str] = None
    isbp_reference: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/JSON."""
        result = asdict(self)
        result["event_type"] = self.event_type.value
        result["severity"] = self.severity.value
        result["timestamp"] = self.timestamp.isoformat()
        return result
    
    def to_log_line(self) -> str:
        """Format as a log line."""
        parts = [
            f"[{self.event_type.value}]",
            f"[{self.severity.value.upper()}]",
            self.message,
        ]
        if self.rule_id:
            parts.append(f"rule={self.rule_id}")
        if self.decision:
            parts.append(f"decision={self.decision}")
        return " ".join(parts)


@dataclass
class AuditTrail:
    """Complete audit trail for a validation session."""
    trail_id: str
    session_id: str
    job_id: Optional[str]
    user_id: Optional[str]
    
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    events: List[AuditEvent] = field(default_factory=list)
    
    # Summary
    total_events: int = 0
    rules_executed: int = 0
    rules_passed: int = 0
    rules_failed: int = 0
    issues_generated: int = 0
    
    # Final outcome
    validation_status: Optional[str] = None
    compliance_score: Optional[float] = None
    was_blocked: bool = False
    block_reason: Optional[str] = None
    
    def add_event(self, event: AuditEvent) -> None:
        """Add an event to the trail."""
        self.events.append(event)
        self.total_events += 1
        
        # Update counters
        if event.event_type == AuditEventType.RULE_EXECUTED:
            self.rules_executed += 1
        elif event.event_type == AuditEventType.RULE_PASSED:
            self.rules_passed += 1
        elif event.event_type == AuditEventType.RULE_FAILED:
            self.rules_failed += 1
        elif event.event_type == AuditEventType.ISSUE_GENERATED:
            self.issues_generated += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trail_id": self.trail_id,
            "session_id": self.session_id,
            "job_id": self.job_id,
            "user_id": self.user_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_events": self.total_events,
            "rules_executed": self.rules_executed,
            "rules_passed": self.rules_passed,
            "rules_failed": self.rules_failed,
            "issues_generated": self.issues_generated,
            "validation_status": self.validation_status,
            "compliance_score": self.compliance_score,
            "was_blocked": self.was_blocked,
            "block_reason": self.block_reason,
            "events": [e.to_dict() for e in self.events],
        }
    
    def to_summary(self) -> Dict[str, Any]:
        """Get summary without full event list."""
        return {
            "trail_id": self.trail_id,
            "session_id": self.session_id,
            "job_id": self.job_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_events": self.total_events,
            "rules_executed": self.rules_executed,
            "rules_passed": self.rules_passed,
            "rules_failed": self.rules_failed,
            "pass_rate": round(self.rules_passed / max(1, self.rules_executed) * 100, 1),
            "issues_generated": self.issues_generated,
            "validation_status": self.validation_status,
            "compliance_score": self.compliance_score,
            "was_blocked": self.was_blocked,
        }


class ValidationAuditLogger:
    """
    Audit logger for validation operations.
    
    Captures every decision with full reasoning for compliance reviews.
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
        persist_events: bool = True,
    ):
        self.session_id = session_id or str(uuid.uuid4())
        self.job_id = job_id
        self.user_id = user_id
        self.persist_events = persist_events
        
        self.trail = AuditTrail(
            trail_id=str(uuid.uuid4()),
            session_id=self.session_id,
            job_id=self.job_id,
            user_id=self.user_id,
            started_at=datetime.utcnow(),
        )
    
    def _create_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        message: str,
        **kwargs,
    ) -> AuditEvent:
        """Create an audit event."""
        return AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            message=message,
            session_id=self.session_id,
            job_id=self.job_id,
            user_id=self.user_id,
            **kwargs,
        )
    
    def _log_event(self, event: AuditEvent) -> None:
        """Log and store an event."""
        # Log to standard logger
        log_level = {
            AuditSeverity.DEBUG: logging.DEBUG,
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.ERROR: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL,
        }.get(event.severity, logging.INFO)
        
        logger.log(log_level, f"AUDIT: {event.to_log_line()}")
        
        # Add to trail
        if self.persist_events:
            self.trail.add_event(event)
    
    # =========================================================================
    # Validation Lifecycle
    # =========================================================================
    
    def log_validation_started(
        self,
        document_count: int,
        document_types: List[str],
    ) -> None:
        """Log validation start."""
        event = self._create_event(
            AuditEventType.VALIDATION_STARTED,
            AuditSeverity.INFO,
            f"Validation started with {document_count} documents",
            details={
                "document_count": document_count,
                "document_types": document_types,
            },
        )
        self._log_event(event)
    
    def log_validation_completed(
        self,
        status: str,
        compliance_score: float,
        issues_count: int,
        processing_time_ms: float,
    ) -> None:
        """Log validation completion."""
        self.trail.validation_status = status
        self.trail.compliance_score = compliance_score
        self.trail.completed_at = datetime.utcnow()
        
        event = self._create_event(
            AuditEventType.VALIDATION_COMPLETED,
            AuditSeverity.INFO,
            f"Validation completed: {status} ({compliance_score}%)",
            details={
                "status": status,
                "compliance_score": compliance_score,
                "issues_count": issues_count,
                "processing_time_ms": processing_time_ms,
            },
        )
        self._log_event(event)
    
    def log_validation_blocked(
        self,
        reason: str,
        missing_fields: List[str],
    ) -> None:
        """Log validation blocked."""
        self.trail.was_blocked = True
        self.trail.block_reason = reason
        self.trail.validation_status = "blocked"
        self.trail.compliance_score = 0
        self.trail.completed_at = datetime.utcnow()
        
        event = self._create_event(
            AuditEventType.VALIDATION_BLOCKED,
            AuditSeverity.WARNING,
            f"Validation blocked: {reason}",
            details={
                "reason": reason,
                "missing_fields": missing_fields,
            },
            decision="BLOCKED",
            reasoning=reason,
        )
        self._log_event(event)
    
    # =========================================================================
    # Gate Checks
    # =========================================================================
    
    def log_gate_check(
        self,
        check_name: str,
        passed: bool,
        expected: str,
        actual: str,
        reasoning: str,
    ) -> None:
        """Log a gate check result."""
        event_type = AuditEventType.GATE_CHECK_PASSED if passed else AuditEventType.GATE_CHECK_FAILED
        severity = AuditSeverity.INFO if passed else AuditSeverity.WARNING
        
        event = self._create_event(
            event_type,
            severity,
            f"Gate check '{check_name}': {'PASSED' if passed else 'FAILED'}",
            rule_id=check_name,
            expected=expected,
            actual=actual,
            decision="PASS" if passed else "FAIL",
            reasoning=reasoning,
        )
        self._log_event(event)
    
    # =========================================================================
    # Extraction
    # =========================================================================
    
    def log_field_extracted(
        self,
        field_name: str,
        value: Any,
        confidence: Optional[float] = None,
        source: Optional[str] = None,
    ) -> None:
        """Log successful field extraction."""
        event = self._create_event(
            AuditEventType.FIELD_EXTRACTED,
            AuditSeverity.DEBUG,
            f"Field '{field_name}' extracted",
            field_name=field_name,
            details={
                "value": str(value)[:200] if value else None,
                "confidence": confidence,
                "source": source,
            },
        )
        self._log_event(event)
    
    def log_field_missing(
        self,
        field_name: str,
        priority: str,
        reasoning: str,
    ) -> None:
        """Log missing field."""
        severity = AuditSeverity.ERROR if priority == "critical" else AuditSeverity.WARNING
        
        event = self._create_event(
            AuditEventType.FIELD_MISSING,
            severity,
            f"Field '{field_name}' ({priority}) not found",
            field_name=field_name,
            details={"priority": priority},
            reasoning=reasoning,
        )
        self._log_event(event)
    
    # =========================================================================
    # Rule Execution
    # =========================================================================
    
    def log_rule_executed(
        self,
        rule_id: str,
        rule_name: str,
        passed: bool,
        expected: str,
        actual: str,
        reasoning: str,
        ucp_reference: Optional[str] = None,
        isbp_reference: Optional[str] = None,
    ) -> None:
        """Log rule execution result."""
        event_type = AuditEventType.RULE_PASSED if passed else AuditEventType.RULE_FAILED
        severity = AuditSeverity.INFO if passed else AuditSeverity.WARNING
        
        event = self._create_event(
            event_type,
            severity,
            f"Rule '{rule_name}': {'PASSED' if passed else 'FAILED'}",
            rule_id=rule_id,
            expected=expected,
            actual=actual,
            decision="PASS" if passed else "FAIL",
            reasoning=reasoning,
            ucp_reference=ucp_reference,
            isbp_reference=isbp_reference,
        )
        self._log_event(event)
    
    def log_rule_skipped(
        self,
        rule_id: str,
        rule_name: str,
        reason: str,
    ) -> None:
        """Log rule skipped."""
        event = self._create_event(
            AuditEventType.RULE_SKIPPED,
            AuditSeverity.DEBUG,
            f"Rule '{rule_name}' skipped: {reason}",
            rule_id=rule_id,
            reasoning=reason,
        )
        self._log_event(event)
    
    # =========================================================================
    # Cross-Document
    # =========================================================================
    
    def log_crossdoc_check(
        self,
        check_name: str,
        source_doc: str,
        target_doc: str,
        passed: bool,
        expected: str,
        actual: str,
        reasoning: str,
    ) -> None:
        """Log cross-document check."""
        event_type = AuditEventType.CROSSDOC_MATCH if passed else AuditEventType.CROSSDOC_MISMATCH
        severity = AuditSeverity.INFO if passed else AuditSeverity.WARNING
        
        event = self._create_event(
            event_type,
            severity,
            f"Cross-doc '{check_name}' ({source_doc} vs {target_doc}): {'MATCH' if passed else 'MISMATCH'}",
            rule_id=check_name,
            details={
                "source_doc": source_doc,
                "target_doc": target_doc,
            },
            expected=expected,
            actual=actual,
            decision="MATCH" if passed else "MISMATCH",
            reasoning=reasoning,
        )
        self._log_event(event)
    
    # =========================================================================
    # Scoring
    # =========================================================================
    
    def log_score_calculated(
        self,
        score: float,
        components: Dict[str, float],
        reasoning: str,
    ) -> None:
        """Log score calculation."""
        event = self._create_event(
            AuditEventType.SCORE_CALCULATED,
            AuditSeverity.INFO,
            f"Compliance score calculated: {score}%",
            details={
                "score": score,
                "components": components,
            },
            reasoning=reasoning,
        )
        self._log_event(event)
    
    def log_score_capped(
        self,
        original_score: float,
        capped_score: float,
        cap_reason: str,
    ) -> None:
        """Log score capping."""
        event = self._create_event(
            AuditEventType.SCORE_CAPPED,
            AuditSeverity.WARNING,
            f"Score capped from {original_score}% to {capped_score}%",
            details={
                "original_score": original_score,
                "capped_score": capped_score,
            },
            reasoning=cap_reason,
        )
        self._log_event(event)
    
    # =========================================================================
    # Issue Generation
    # =========================================================================
    
    def log_issue_generated(
        self,
        issue_id: str,
        title: str,
        severity: str,
        rule_id: Optional[str],
        reasoning: str,
    ) -> None:
        """Log issue generation."""
        event = self._create_event(
            AuditEventType.ISSUE_GENERATED,
            AuditSeverity.INFO,
            f"Issue generated: {title} ({severity})",
            rule_id=rule_id,
            details={
                "issue_id": issue_id,
                "title": title,
                "severity": severity,
            },
            reasoning=reasoning,
        )
        self._log_event(event)
    
    # =========================================================================
    # Trail Management
    # =========================================================================
    
    def get_trail(self) -> AuditTrail:
        """Get the complete audit trail."""
        return self.trail
    
    def get_trail_summary(self) -> Dict[str, Any]:
        """Get audit trail summary."""
        return self.trail.to_summary()
    
    def export_trail_json(self) -> str:
        """Export trail as JSON."""
        return json.dumps(self.trail.to_dict(), indent=2)


# ============================================================================
# Factory Functions
# ============================================================================

def create_audit_logger(
    session_id: Optional[str] = None,
    job_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> ValidationAuditLogger:
    """Create a new audit logger."""
    return ValidationAuditLogger(
        session_id=session_id,
        job_id=job_id,
        user_id=user_id,
    )


# Global instance for simple usage
_current_logger: Optional[ValidationAuditLogger] = None


def get_current_audit_logger() -> Optional[ValidationAuditLogger]:
    """Get the current audit logger (if set)."""
    return _current_logger


def set_current_audit_logger(logger: ValidationAuditLogger) -> None:
    """Set the current audit logger."""
    global _current_logger
    _current_logger = logger

