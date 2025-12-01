"""
Audit Logging Service for Price Verification

Every verification action is logged immutably for compliance.
Logs include: who, what, when, input, output, and source data.

This is critical for bank compliance - every price check must be traceable.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Types of auditable actions."""
    PRICE_VERIFY_SINGLE = "price_verify_single"
    PRICE_VERIFY_BATCH = "price_verify_batch"
    PRICE_EXTRACT = "price_extract"
    TBML_FLAG = "tbml_flag"
    REPORT_GENERATE = "report_generate"
    REPORT_EXPORT = "report_export"
    SETTINGS_CHANGE = "settings_change"
    COMMODITY_SEARCH = "commodity_search"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"  # e.g., TBML detection


@dataclass
class AuditEntry:
    """
    A single audit log entry with complete traceability.
    """
    id: str
    timestamp: datetime
    action: AuditAction
    severity: AuditSeverity
    
    # Who
    user_id: Optional[str]
    user_email: Optional[str]
    company_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    
    # What
    resource_type: str  # e.g., "verification", "report"
    resource_id: Optional[str]
    
    # Input
    request_data: Dict[str, Any]
    
    # Output
    response_summary: Dict[str, Any]
    verdict: Optional[str]
    risk_level: Optional[str]
    
    # Source Attribution
    data_sources: List[Dict[str, Any]]
    
    # Context
    session_id: Optional[str]
    request_id: Optional[str]
    duration_ms: Optional[int]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "severity": self.severity.value,
        }


class AuditLogService:
    """
    Service for creating and querying audit logs.
    
    In production, this should write to:
    1. PostgreSQL (for querying)
    2. Append-only log file (for immutability)
    3. Optionally: external SIEM (Security Information and Event Management)
    """
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self._buffer: List[AuditEntry] = []
        self._buffer_size = 100
    
    async def log_verification(
        self,
        user_id: Optional[str],
        user_email: Optional[str],
        company_id: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
        request_id: Optional[str],
        commodity: str,
        input_price: float,
        input_unit: str,
        input_currency: str,
        market_price: float,
        variance_percent: float,
        verdict: str,
        risk_level: str,
        risk_flags: List[str],
        data_sources: List[Dict[str, Any]],
        duration_ms: int,
        document_context: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """
        Log a price verification action.
        
        This is the main audit entry for compliance.
        """
        # Determine severity
        severity = AuditSeverity.INFO
        if risk_level in ("high", "critical") or "tbml_risk" in risk_flags:
            severity = AuditSeverity.CRITICAL
        elif risk_level == "medium" or verdict == "warning":
            severity = AuditSeverity.WARNING
        
        entry = AuditEntry(
            id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            action=AuditAction.PRICE_VERIFY_SINGLE,
            severity=severity,
            user_id=user_id,
            user_email=user_email,
            company_id=company_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type="verification",
            resource_id=None,
            request_data={
                "commodity": commodity,
                "price": input_price,
                "unit": input_unit,
                "currency": input_currency,
                "document_context": document_context,
            },
            response_summary={
                "market_price": market_price,
                "variance_percent": variance_percent,
                "verdict": verdict,
                "risk_level": risk_level,
                "risk_flags": risk_flags,
            },
            verdict=verdict,
            risk_level=risk_level,
            data_sources=data_sources,
            session_id=None,
            request_id=request_id,
            duration_ms=duration_ms,
        )
        
        await self._persist(entry)
        
        # Log critical events immediately
        if severity == AuditSeverity.CRITICAL:
            logger.warning(
                f"TBML ALERT: {commodity} @ ${input_price}/{input_unit} "
                f"variance={variance_percent:.1f}% user={user_email}"
            )
        
        return entry
    
    async def log_batch_verification(
        self,
        user_id: Optional[str],
        user_email: Optional[str],
        company_id: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
        request_id: Optional[str],
        file_count: int,
        total_items: int,
        passed: int,
        warnings: int,
        failed: int,
        tbml_flags: int,
        duration_ms: int,
    ) -> AuditEntry:
        """Log a batch verification action."""
        severity = AuditSeverity.INFO
        if tbml_flags > 0:
            severity = AuditSeverity.CRITICAL
        elif failed > 0 or warnings > 0:
            severity = AuditSeverity.WARNING
        
        entry = AuditEntry(
            id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            action=AuditAction.PRICE_VERIFY_BATCH,
            severity=severity,
            user_id=user_id,
            user_email=user_email,
            company_id=company_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type="batch_verification",
            resource_id=None,
            request_data={
                "file_count": file_count,
            },
            response_summary={
                "total_items": total_items,
                "passed": passed,
                "warnings": warnings,
                "failed": failed,
                "tbml_flags": tbml_flags,
            },
            verdict="batch_complete",
            risk_level="critical" if tbml_flags > 0 else ("warning" if failed > 0 else "low"),
            data_sources=[],
            session_id=None,
            request_id=request_id,
            duration_ms=duration_ms,
        )
        
        await self._persist(entry)
        return entry
    
    async def log_extraction(
        self,
        user_id: Optional[str],
        user_email: Optional[str],
        ip_address: Optional[str],
        request_id: Optional[str],
        filename: str,
        file_size: int,
        items_extracted: int,
        success: bool,
        duration_ms: int,
    ) -> AuditEntry:
        """Log a document extraction action."""
        entry = AuditEntry(
            id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            action=AuditAction.PRICE_EXTRACT,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            user_id=user_id,
            user_email=user_email,
            company_id=None,
            ip_address=ip_address,
            user_agent=None,
            resource_type="extraction",
            resource_id=None,
            request_data={
                "filename": filename,
                "file_size": file_size,
            },
            response_summary={
                "items_extracted": items_extracted,
                "success": success,
            },
            verdict="success" if success else "failed",
            risk_level="low",
            data_sources=[{"name": "ocr", "provider": "google_documentai"}],
            session_id=None,
            request_id=request_id,
            duration_ms=duration_ms,
        )
        
        await self._persist(entry)
        return entry
    
    async def log_tbml_alert(
        self,
        user_id: Optional[str],
        user_email: Optional[str],
        company_id: Optional[str],
        verification_id: str,
        commodity: str,
        variance_percent: float,
        risk_flags: List[str],
        recommended_action: str,
    ) -> AuditEntry:
        """
        Log a TBML (Trade-Based Money Laundering) alert.
        
        These are CRITICAL severity and may trigger notifications.
        """
        entry = AuditEntry(
            id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            action=AuditAction.TBML_FLAG,
            severity=AuditSeverity.CRITICAL,
            user_id=user_id,
            user_email=user_email,
            company_id=company_id,
            ip_address=None,
            user_agent=None,
            resource_type="tbml_alert",
            resource_id=verification_id,
            request_data={
                "commodity": commodity,
                "variance_percent": variance_percent,
            },
            response_summary={
                "risk_flags": risk_flags,
                "recommended_action": recommended_action,
            },
            verdict="tbml_flagged",
            risk_level="critical",
            data_sources=[],
            session_id=None,
            request_id=None,
            duration_ms=None,
        )
        
        await self._persist(entry)
        
        # Critical logging
        logger.critical(
            f"TBML ALERT GENERATED: verification={verification_id} "
            f"commodity={commodity} variance={variance_percent:.1f}% "
            f"flags={risk_flags} user={user_email}"
        )
        
        return entry
    
    async def _persist(self, entry: AuditEntry):
        """
        Persist audit entry to storage.
        
        Currently logs to structured logger.
        In production, would also write to:
        - PostgreSQL audit_logs table
        - Append-only file for immutability
        - External SIEM if configured
        """
        # Always log to structured logger
        log_data = entry.to_dict()
        
        if entry.severity == AuditSeverity.CRITICAL:
            logger.critical(f"AUDIT [{entry.action.value}]: {json.dumps(log_data)}")
        elif entry.severity == AuditSeverity.WARNING:
            logger.warning(f"AUDIT [{entry.action.value}]: {json.dumps(log_data)}")
        else:
            logger.info(f"AUDIT [{entry.action.value}]: {json.dumps(log_data)}")
        
        # Buffer for batch DB writes
        self._buffer.append(entry)
        
        # Flush if buffer is full
        if len(self._buffer) >= self._buffer_size:
            await self._flush_buffer()
    
    async def _flush_buffer(self):
        """Flush buffered entries to database."""
        if not self._buffer:
            return
        
        if self.db:
            try:
                # In production, batch insert to audit_logs table
                # For now, just clear buffer
                pass
            except Exception as e:
                logger.error(f"Failed to flush audit buffer: {e}")
        
        self._buffer = []
    
    async def query_logs(
        self,
        user_id: Optional[str] = None,
        company_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        severity: Optional[AuditSeverity] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEntry]:
        """
        Query audit logs with filters.
        
        In production, this would query the database.
        For now, returns empty list.
        """
        # TODO: Implement database query
        return []
    
    async def get_compliance_report(
        self,
        company_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Generate a compliance report for the given period.
        
        Returns summary statistics for regulatory reporting.
        """
        # TODO: Implement aggregation query
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "company_id": company_id,
            "summary": {
                "total_verifications": 0,
                "tbml_alerts": 0,
                "high_risk_transactions": 0,
                "compliance_rate": 0.0,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# Singleton instance
_audit_service: Optional[AuditLogService] = None


def get_audit_service(db: Optional[Session] = None) -> AuditLogService:
    """Get or create the audit log service instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditLogService(db)
    return _audit_service

