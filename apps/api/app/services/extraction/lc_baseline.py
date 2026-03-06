"""
LC Baseline - Phase 2: Modular LC Extractor with Field Tracking

This module defines the canonical LC structure and tracks extraction status
for each required field. It enables:
1. Validation gating (Phase 4) - Block if critical fields missing
2. Issue generation (Phase 5) - Auto-create issues for missing fields
3. Compliance scoring (Phase 6) - Factor in extraction completeness

The LC is the "constitution" - all other documents must match it.
If we can't extract the LC, we can't validate anything.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import date


logger = logging.getLogger(__name__)


class FieldPriority(str, Enum):
    """Priority level for LC fields."""
    CRITICAL = "critical"   # Extraction fails without these
    REQUIRED = "required"   # Should generate issue if missing
    IMPORTANT = "important" # Should generate warning if missing
    OPTIONAL = "optional"   # Nice to have, no issue if missing


class ExtractionStatus(str, Enum):
    """Status of field extraction."""
    EXTRACTED = "extracted"      # Successfully extracted with value
    PARTIAL = "partial"          # Extracted but may be incomplete
    MISSING = "missing"          # Not found in document
    INVALID = "invalid"          # Found but couldn't parse
    NOT_APPLICABLE = "n/a"       # Not expected in this LC type


class MissingReason(str, Enum):
    """Deterministic reason codes for missing/invalid fields."""
    MISSING_IN_SOURCE = "missing_in_source"
    PARSER_FAILED = "parser_failed"
    CONFLICT_DETECTED = "conflict_detected"


@dataclass
class FieldResult:
    """Result of extracting a single field."""
    field_name: str
    priority: FieldPriority
    status: ExtractionStatus
    value: Optional[Any] = None
    raw_value: Optional[str] = None  # Original text before parsing
    confidence: float = 0.0  # 0.0 to 1.0
    source: Optional[str] = None  # Which parser extracted this
    error: Optional[str] = None  # Error message if invalid/missing
    missing_reason: Optional[str] = None  # Deterministic missing reason code
    # Evidence span (when available)
    evidence_text: Optional[str] = None
    evidence_page: Optional[int] = None
    evidence_location: Optional[Any] = None  # bbox/span info when available
    
    @property
    def is_present(self) -> bool:
        return self.status in (ExtractionStatus.EXTRACTED, ExtractionStatus.PARTIAL)
    
    @property
    def is_critical_missing(self) -> bool:
        return self.priority == FieldPriority.CRITICAL and not self.is_present
    
    @property
    def has_evidence(self) -> bool:
        return bool(self.evidence_text) or self.evidence_page is not None or self.evidence_location is not None


@dataclass
class PartyInfo:
    """Structured party information (Applicant/Beneficiary/Bank)."""
    name: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    account: Optional[str] = None
    swift_code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in {
            "name": self.name,
            "address": self.address,
            "country": self.country,
            "account": self.account,
            "swift_code": self.swift_code,
        }.items() if v is not None}
    
    @property
    def is_valid(self) -> bool:
        return bool(self.name)


@dataclass
class AmountInfo:
    """Structured amount with currency."""
    value: Optional[float] = None
    currency: Optional[str] = None
    raw: Optional[str] = None
    tolerance_percent: Optional[float] = None  # e.g., +/- 10%
    tolerance_amount: Optional[float] = None   # e.g., +/- 5000
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in {
            "value": self.value,
            "currency": self.currency,
            "raw": self.raw,
            "tolerance_percent": self.tolerance_percent,
            "tolerance_amount": self.tolerance_amount,
        }.items() if v is not None}
    
    @property
    def is_valid(self) -> bool:
        return self.value is not None and self.value > 0


@dataclass
class PortInfo:
    """Port of loading/discharge."""
    name: Optional[str] = None
    country: Optional[str] = None
    code: Optional[str] = None  # UN/LOCODE
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in {
            "name": self.name,
            "country": self.country,
            "code": self.code,
        }.items() if v is not None}
    
    @property
    def is_valid(self) -> bool:
        return bool(self.name)


@dataclass
class TimelineInfo:
    """LC timeline dates."""
    issue_date: Optional[str] = None       # ISO format YYYY-MM-DD
    expiry_date: Optional[str] = None      # ISO format YYYY-MM-DD
    expiry_place: Optional[str] = None
    latest_shipment: Optional[str] = None  # ISO format YYYY-MM-DD
    presentation_period: Optional[int] = None  # Days after shipment
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in {
            "issue_date": self.issue_date,
            "expiry_date": self.expiry_date,
            "expiry_place": self.expiry_place,
            "latest_shipment": self.latest_shipment,
            "presentation_period": self.presentation_period,
        }.items() if v is not None}


@dataclass
class GoodsItem:
    """Single goods line item."""
    description: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    hs_code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in {
            "description": self.description,
            "quantity": self.quantity,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "total_price": self.total_price,
            "hs_code": self.hs_code,
        }.items() if v is not None}


@dataclass
class LCBaseline:
    """
    The canonical LC structure - the "constitution" for validation.
    
    All required fields are tracked with extraction status.
    This enables:
    - Gating: Block validation if critical fields missing
    - Issues: Generate issues for missing required fields
    - Scoring: Calculate extraction completeness
    """
    
    # Core identifiers (CRITICAL)
    lc_number: FieldResult = field(default_factory=lambda: FieldResult(
        "lc_number", FieldPriority.CRITICAL, ExtractionStatus.MISSING
    ))
    lc_type: FieldResult = field(default_factory=lambda: FieldResult(
        "lc_type", FieldPriority.REQUIRED, ExtractionStatus.MISSING
    ))
    
    # Parties (CRITICAL for applicant/beneficiary)
    applicant: FieldResult = field(default_factory=lambda: FieldResult(
        "applicant", FieldPriority.CRITICAL, ExtractionStatus.MISSING
    ))
    beneficiary: FieldResult = field(default_factory=lambda: FieldResult(
        "beneficiary", FieldPriority.CRITICAL, ExtractionStatus.MISSING
    ))
    issuing_bank: FieldResult = field(default_factory=lambda: FieldResult(
        "issuing_bank", FieldPriority.IMPORTANT, ExtractionStatus.MISSING
    ))
    advising_bank: FieldResult = field(default_factory=lambda: FieldResult(
        "advising_bank", FieldPriority.OPTIONAL, ExtractionStatus.MISSING
    ))
    
    # Amount (CRITICAL)
    amount: FieldResult = field(default_factory=lambda: FieldResult(
        "amount", FieldPriority.CRITICAL, ExtractionStatus.MISSING
    ))
    currency: FieldResult = field(default_factory=lambda: FieldResult(
        "currency", FieldPriority.CRITICAL, ExtractionStatus.MISSING
    ))
    
    # Timeline (REQUIRED)
    expiry_date: FieldResult = field(default_factory=lambda: FieldResult(
        "expiry_date", FieldPriority.REQUIRED, ExtractionStatus.MISSING
    ))
    issue_date: FieldResult = field(default_factory=lambda: FieldResult(
        "issue_date", FieldPriority.IMPORTANT, ExtractionStatus.MISSING
    ))
    latest_shipment: FieldResult = field(default_factory=lambda: FieldResult(
        "latest_shipment", FieldPriority.REQUIRED, ExtractionStatus.MISSING
    ))
    
    # Shipment details (REQUIRED)
    port_of_loading: FieldResult = field(default_factory=lambda: FieldResult(
        "port_of_loading", FieldPriority.REQUIRED, ExtractionStatus.MISSING
    ))
    port_of_discharge: FieldResult = field(default_factory=lambda: FieldResult(
        "port_of_discharge", FieldPriority.REQUIRED, ExtractionStatus.MISSING
    ))
    incoterm: FieldResult = field(default_factory=lambda: FieldResult(
        "incoterm", FieldPriority.IMPORTANT, ExtractionStatus.MISSING
    ))
    
    # Goods (REQUIRED)
    goods_description: FieldResult = field(default_factory=lambda: FieldResult(
        "goods_description", FieldPriority.REQUIRED, ExtractionStatus.MISSING
    ))
    
    # Documents required (IMPORTANT)
    documents_required: FieldResult = field(default_factory=lambda: FieldResult(
        "documents_required", FieldPriority.IMPORTANT, ExtractionStatus.MISSING
    ))
    
    # Terms and conditions (IMPORTANT)
    ucp_reference: FieldResult = field(default_factory=lambda: FieldResult(
        "ucp_reference", FieldPriority.IMPORTANT, ExtractionStatus.MISSING
    ))
    additional_conditions: FieldResult = field(default_factory=lambda: FieldResult(
        "additional_conditions", FieldPriority.OPTIONAL, ExtractionStatus.MISSING
    ))
    
    # Structured data holders (not tracked as FieldResult)
    _applicant_info: Optional[PartyInfo] = field(default=None, repr=False)
    _beneficiary_info: Optional[PartyInfo] = field(default=None, repr=False)
    _amount_info: Optional[AmountInfo] = field(default=None, repr=False)
    _timeline_info: Optional[TimelineInfo] = field(default=None, repr=False)
    _port_of_loading_info: Optional[PortInfo] = field(default=None, repr=False)
    _port_of_discharge_info: Optional[PortInfo] = field(default=None, repr=False)
    _goods_items: List[GoodsItem] = field(default_factory=list, repr=False)
    _documents_list: List[str] = field(default_factory=list, repr=False)
    _conditions_list: List[str] = field(default_factory=list, repr=False)
    _hs_codes: List[str] = field(default_factory=list, repr=False)
    
    # Metadata
    _source_parsers: List[str] = field(default_factory=list, repr=False)
    _raw_text_length: int = field(default=0, repr=False)
    _extraction_time_ms: int = field(default=0, repr=False)
    
    def get_all_fields(self) -> List[FieldResult]:
        """Get all tracked fields."""
        return [
            self.lc_number, self.lc_type,
            self.applicant, self.beneficiary, self.issuing_bank, self.advising_bank,
            self.amount, self.currency,
            self.expiry_date, self.issue_date, self.latest_shipment,
            self.port_of_loading, self.port_of_discharge, self.incoterm,
            self.goods_description, self.documents_required,
            self.ucp_reference, self.additional_conditions,
        ]
    
    def get_critical_fields(self) -> List[FieldResult]:
        """Get only critical fields."""
        return [f for f in self.get_all_fields() if f.priority == FieldPriority.CRITICAL]
    
    def get_required_fields(self) -> List[FieldResult]:
        """Get critical + required fields."""
        return [f for f in self.get_all_fields() 
                if f.priority in (FieldPriority.CRITICAL, FieldPriority.REQUIRED)]
    
    def get_missing_critical(self) -> List[FieldResult]:
        """Get critical fields that are missing."""
        return [f for f in self.get_critical_fields() if not f.is_present]
    
    def get_missing_required(self) -> List[FieldResult]:
        """Get required fields that are missing."""
        return [f for f in self.get_required_fields() if not f.is_present]
    
    def get_all_missing(self) -> List[FieldResult]:
        """Get all missing fields."""
        return [f for f in self.get_all_fields() if not f.is_present]
    
    @property
    def has_critical_missing(self) -> bool:
        """True if any critical field is missing."""
        return len(self.get_missing_critical()) > 0
    
    @property
    def is_valid_for_validation(self) -> bool:
        """True if baseline has enough data for validation to proceed."""
        # Must have LC number, amount, and at least one party
        return (
            self.lc_number.is_present
            and self.amount.is_present
            and (self.applicant.is_present or self.beneficiary.is_present)
        )
    
    @property
    def extraction_completeness(self) -> float:
        """
        Calculate extraction completeness score (0.0 to 1.0).
        
        Weighted by field priority:
        - Critical: 3x weight
        - Required: 2x weight
        - Important: 1x weight
        - Optional: 0.5x weight
        """
        weights = {
            FieldPriority.CRITICAL: 3.0,
            FieldPriority.REQUIRED: 2.0,
            FieldPriority.IMPORTANT: 1.0,
            FieldPriority.OPTIONAL: 0.5,
        }
        
        total_weight = 0.0
        extracted_weight = 0.0
        
        for field_result in self.get_all_fields():
            weight = weights[field_result.priority]
            total_weight += weight
            if field_result.is_present:
                # Factor in confidence
                extracted_weight += weight * field_result.confidence
        
        return extracted_weight / total_weight if total_weight > 0 else 0.0
    
    @property
    def critical_completeness(self) -> float:
        """Completeness of critical fields only."""
        critical = self.get_critical_fields()
        if not critical:
            return 1.0
        present = sum(1 for f in critical if f.is_present)
        return present / len(critical)
    
    def get_extraction_summary(self) -> Dict[str, Any]:
        """Get a summary of extraction status."""
        all_fields = self.get_all_fields()
        
        by_status = {}
        for status in ExtractionStatus:
            by_status[status.value] = [f.field_name for f in all_fields if f.status == status]
        
        by_priority = {}
        for priority in FieldPriority:
            fields = [f for f in all_fields if f.priority == priority]
            present = sum(1 for f in fields if f.is_present)
            by_priority[priority.value] = {
                "total": len(fields),
                "extracted": present,
                "missing": len(fields) - present,
            }
        
        return {
            "total_fields": len(all_fields),
            "extracted": sum(1 for f in all_fields if f.is_present),
            "missing": sum(1 for f in all_fields if not f.is_present),
            "completeness": round(self.extraction_completeness * 100, 1),
            "critical_completeness": round(self.critical_completeness * 100, 1),
            "is_valid_for_validation": self.is_valid_for_validation,
            "has_critical_missing": self.has_critical_missing,
            "by_status": by_status,
            "by_priority": by_priority,
            "missing_critical": [f.field_name for f in self.get_missing_critical()],
            "missing_required": [f.field_name for f in self.get_missing_required()],
            "source_parsers": self._source_parsers,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {
            "number": self.lc_number.value,
            "lc_type": self.lc_type.value,
            "applicant": self._applicant_info.to_dict() if self._applicant_info else None,
            "beneficiary": self._beneficiary_info.to_dict() if self._beneficiary_info else None,
            "issuing_bank": self.issuing_bank.value,
            "advising_bank": self.advising_bank.value,
            "amount": self._amount_info.to_dict() if self._amount_info else None,
            "ports": {
                "loading": self._port_of_loading_info.to_dict() if self._port_of_loading_info else None,
                "discharge": self._port_of_discharge_info.to_dict() if self._port_of_discharge_info else None,
            },
            "incoterm": self.incoterm.value,
            "timeline": self._timeline_info.to_dict() if self._timeline_info else None,
            "goods_description": self.goods_description.value,
            "goods_items": [g.to_dict() for g in self._goods_items],
            "hs_codes": self._hs_codes,
            "documents_required": self._documents_list,
            "ucp_reference": self.ucp_reference.value,
            "additional_conditions": self._conditions_list,
            "extraction_summary": self.get_extraction_summary(),
        }
        
        # Include field-level extraction status for transparency
        result["field_status"] = {
            f.field_name: {
                "status": f.status.value,
                "priority": f.priority.value,
                "confidence": f.confidence,
                "source": f.source,
                "error": f.error,
                "missing_reason": f.missing_reason,
                "evidence_text": f.evidence_text,
                "evidence_page": f.evidence_page,
                "evidence_location": f.evidence_location,
            }
            for f in self.get_all_fields()
        }
        
        return {k: v for k, v in result.items() if v is not None}
    
    def generate_missing_field_issues(self) -> List[Dict[str, Any]]:
        """
        Generate validation issues for missing fields.
        
        This is used by Phase 5 (Issue Engine) to auto-create issues.
        """
        issues = []
        
        for field_result in self.get_all_fields():
            if field_result.is_present:
                continue
            
            # Determine severity based on priority
            if field_result.priority == FieldPriority.CRITICAL:
                severity = "critical"
            elif field_result.priority == FieldPriority.REQUIRED:
                severity = "major"
            elif field_result.priority == FieldPriority.IMPORTANT:
                severity = "minor"
            else:
                continue  # Skip optional fields
            
            human_name = field_result.field_name.replace("_", " ").title()
            
            issues.append({
                "rule": f"LC-MISSING-{field_result.field_name.upper()}",
                "title": f"Missing {human_name}",
                "passed": False,
                "severity": severity,
                "message": f"The {human_name} could not be extracted from the Letter of Credit. "
                           f"This field is {field_result.priority.value} for validation.",
                "expected": f"{human_name} must be present in the LC",
                "actual": "Not found or could not be extracted",
                "suggestion": f"Verify the LC document contains the {human_name} field, "
                              f"or re-scan with better quality.",
                "field_name": field_result.field_name,
                "field_priority": field_result.priority.value,
                "extraction_status": field_result.status.value,
                "extraction_error": field_result.error,
                "missing_reason": field_result.missing_reason,
                "documents": ["Letter of Credit"],
                "document_names": ["Letter of Credit"],
                "display_card": True,
                "ruleset_domain": "icc.lcopilot.extraction",
                "auto_generated": True,
            })
        
        return issues


# ---------------------------------------------------------------------------
# Factory function to create LCBaseline from extraction results
# ---------------------------------------------------------------------------

def create_lc_baseline_from_extraction(
    extraction_result: Dict[str, Any],
    raw_text: str = "",
    source_parsers: Optional[List[str]] = None,
) -> LCBaseline:
    """
    Create an LCBaseline from the output of extract_lc_structured().
    
    This bridges the old extraction format to the new baseline format,
    populating field status based on what was extracted.
    """
    baseline = LCBaseline()
    baseline._source_parsers = source_parsers or ["unknown"]
    baseline._raw_text_length = len(raw_text) if raw_text else 0
    
    evidence_map = (
        extraction_result.get("field_evidence")
        or extraction_result.get("_field_evidence")
        or extraction_result.get("evidence")
        or {}
    )

    field_diagnostics = extraction_result.get("_field_diagnostics") or {}

    def _apply_evidence(field_result: FieldResult, evidence: Any) -> None:
        if not evidence:
            return
        if isinstance(evidence, str):
            field_result.evidence_text = evidence
            return
        if isinstance(evidence, dict):
            field_result.evidence_text = (
                evidence.get("text")
                or evidence.get("snippet")
                or evidence.get("raw")
                or evidence.get("value")
            )
            field_result.evidence_page = evidence.get("page")
            field_result.evidence_location = (
                evidence.get("location")
                or evidence.get("bbox")
                or evidence.get("span")
            )

    def _extract_snippet(value: Any) -> Optional[str]:
        if not raw_text:
            return None
        if value is None:
            return None
        value_str = str(value).strip()
        if not value_str:
            return None
        lowered = raw_text.lower()
        idx = lowered.find(value_str.lower())
        if idx == -1:
            return None
        window = 60
        start = max(0, idx - window)
        end = min(len(raw_text), idx + len(value_str) + window)
        return raw_text[start:end].strip()

    def _get_evidence(field_key: str, *fallback_keys: str) -> Any:
        for key in (field_key, *fallback_keys):
            if key in evidence_map:
                return evidence_map.get(key)
        return None

    def _get_missing_reason(field_key: str) -> MissingReason:
        diag = field_diagnostics.get(field_key) or {}
        if diag.get("conflict"):
            return MissingReason.CONFLICT_DETECTED
        if diag.get("invalid_candidates"):
            return MissingReason.PARSER_FAILED
        return MissingReason.MISSING_IN_SOURCE

    def _get_missing_status(field_key: str) -> Tuple[ExtractionStatus, Optional[str], MissingReason]:
        diag = field_diagnostics.get(field_key) or {}
        if diag.get("conflict"):
            return ExtractionStatus.INVALID, "Conflicting values detected", MissingReason.CONFLICT_DETECTED
        if diag.get("invalid_candidates"):
            return ExtractionStatus.INVALID, "Parser failed to extract a valid value", MissingReason.PARSER_FAILED
        return ExtractionStatus.MISSING, None, MissingReason.MISSING_IN_SOURCE

    def set_field(
        field_result: FieldResult,
        value: Any,
        source: str = "extraction",
        confidence: float = 0.8,
        evidence: Any = None,
        status_override: Optional[ExtractionStatus] = None,
        error: Optional[str] = None,
        missing_reason: Optional[MissingReason] = None,
    ):
        """Helper to set a field result."""
        if value is not None and value != "" and value != {}:
            field_result.status = ExtractionStatus.EXTRACTED
            field_result.value = value
            field_result.confidence = confidence
            field_result.source = source
            field_result.error = None
            field_result.missing_reason = None
            _apply_evidence(field_result, evidence)
            if field_result.priority == FieldPriority.CRITICAL and not field_result.evidence_text:
                snippet = _extract_snippet(value)
                if snippet:
                    field_result.evidence_text = snippet
        else:
            field_result.status = status_override or ExtractionStatus.MISSING
            field_result.confidence = 0.0
            field_result.error = error
            field_result.missing_reason = (
                missing_reason.value if isinstance(missing_reason, MissingReason) else missing_reason
            ) or MissingReason.MISSING_IN_SOURCE.value
    
    # LC Number
    lc_number_status, lc_number_error, lc_number_reason = _get_missing_status("lc_number")
    set_field(
        baseline.lc_number,
        extraction_result.get("number"),
        evidence=_get_evidence("lc_number", "number", "20"),
        status_override=lc_number_status,
        error=lc_number_error,
        missing_reason=lc_number_reason,
    )
    
    # LC Type
    lc_type = extraction_result.get("lc_type")
    if not lc_type:
        # Try to infer from form_of_doc_credit in mt700
        mt700 = extraction_result.get("mt700", {})
        lc_type = mt700.get("form_of_doc_credit")
    lc_type_status, lc_type_error, lc_type_reason = _get_missing_status("lc_type")
    set_field(
        baseline.lc_type,
        lc_type,
        status_override=lc_type_status,
        error=lc_type_error,
        missing_reason=lc_type_reason,
    )
    
    # Applicant
    applicant_data = extraction_result.get("applicant")
    if applicant_data:
        if isinstance(applicant_data, str):
            baseline._applicant_info = PartyInfo(name=applicant_data)
        elif isinstance(applicant_data, dict):
            baseline._applicant_info = PartyInfo(
                name=applicant_data.get("name"),
                address=applicant_data.get("address"),
                country=applicant_data.get("country"),
            )
        applicant_status, applicant_error, applicant_reason = _get_missing_status("applicant")
        set_field(
            baseline.applicant,
            baseline._applicant_info.name if baseline._applicant_info else None,
            evidence=_get_evidence("applicant", "applicant_name", "50"),
            status_override=applicant_status,
            error=applicant_error,
            missing_reason=applicant_reason,
        )
    else:
        applicant_status, applicant_error, applicant_reason = _get_missing_status("applicant")
        set_field(
            baseline.applicant,
            None,
            status_override=applicant_status,
            error=applicant_error,
            missing_reason=applicant_reason,
        )
    
    # Beneficiary
    beneficiary_data = extraction_result.get("beneficiary")
    if beneficiary_data:
        if isinstance(beneficiary_data, str):
            baseline._beneficiary_info = PartyInfo(name=beneficiary_data)
        elif isinstance(beneficiary_data, dict):
            baseline._beneficiary_info = PartyInfo(
                name=beneficiary_data.get("name"),
                address=beneficiary_data.get("address"),
                country=beneficiary_data.get("country"),
            )
        beneficiary_status, beneficiary_error, beneficiary_reason = _get_missing_status("beneficiary")
        set_field(
            baseline.beneficiary,
            baseline._beneficiary_info.name if baseline._beneficiary_info else None,
            evidence=_get_evidence("beneficiary", "beneficiary_name", "59"),
            status_override=beneficiary_status,
            error=beneficiary_error,
            missing_reason=beneficiary_reason,
        )
    else:
        beneficiary_status, beneficiary_error, beneficiary_reason = _get_missing_status("beneficiary")
        set_field(
            baseline.beneficiary,
            None,
            status_override=beneficiary_status,
            error=beneficiary_error,
            missing_reason=beneficiary_reason,
        )
    
    # Amount
    amount_data = extraction_result.get("amount")
    amount_parse_failed = False
    raw_value = None
    if amount_data:
        if isinstance(amount_data, dict):
            raw_value = amount_data.get("value") or amount_data.get("raw")
            try:
                value = float(str(raw_value).replace(",", "")) if raw_value else None
            except (ValueError, TypeError):
                value = None
                if raw_value:
                    amount_parse_failed = True
            baseline._amount_info = AmountInfo(
                value=value,
                currency=amount_data.get("currency"),
                raw=str(raw_value) if raw_value else None,
            )
        elif isinstance(amount_data, (int, float)):
            baseline._amount_info = AmountInfo(value=float(amount_data))
        elif isinstance(amount_data, str):
            try:
                baseline._amount_info = AmountInfo(value=float(amount_data.replace(",", "")), raw=amount_data)
            except ValueError:
                baseline._amount_info = AmountInfo(raw=amount_data)
                amount_parse_failed = True
        
        amount_status, amount_error, amount_reason = _get_missing_status("amount")
        if amount_parse_failed:
            amount_status = ExtractionStatus.INVALID
            amount_error = "Invalid amount format"
            amount_reason = MissingReason.PARSER_FAILED
        set_field(
            baseline.amount,
            baseline._amount_info.value if baseline._amount_info and baseline._amount_info.is_valid else None,
            evidence=_get_evidence("amount", "lc_amount", "32B_amount"),
            status_override=amount_status,
            error=amount_error,
            missing_reason=amount_reason,
        )
    else:
        amount_status, amount_error, amount_reason = _get_missing_status("amount")
        set_field(
            baseline.amount,
            None,
            status_override=amount_status,
            error=amount_error,
            missing_reason=amount_reason,
        )

    # Currency
    currency_value = None
    if baseline._amount_info and baseline._amount_info.currency:
        currency_value = baseline._amount_info.currency
    if not currency_value:
        currency_value = extraction_result.get("currency")
    currency_status, currency_error, currency_reason = _get_missing_status("currency")
    set_field(
        baseline.currency,
        currency_value,
        status_override=currency_status,
        error=currency_error,
        missing_reason=currency_reason,
    )
    
    # Timeline
    timeline_data = extraction_result.get("timeline", {})
    baseline._timeline_info = TimelineInfo(
        issue_date=timeline_data.get("issue_date"),
        expiry_date=timeline_data.get("expiry_date"),
        latest_shipment=timeline_data.get("latest_shipment"),
    )
    expiry_status, expiry_error, expiry_reason = _get_missing_status("expiry_date")
    set_field(
        baseline.expiry_date,
        baseline._timeline_info.expiry_date,
        status_override=expiry_status,
        error=expiry_error,
        missing_reason=expiry_reason,
    )
    issue_status, issue_error, issue_reason = _get_missing_status("issue_date")
    set_field(
        baseline.issue_date,
        baseline._timeline_info.issue_date,
        status_override=issue_status,
        error=issue_error,
        missing_reason=issue_reason,
    )
    shipment_status, shipment_error, shipment_reason = _get_missing_status("latest_shipment")
    set_field(
        baseline.latest_shipment,
        baseline._timeline_info.latest_shipment,
        status_override=shipment_status,
        error=shipment_error,
        missing_reason=shipment_reason,
    )
    
    # Ports
    ports_data = extraction_result.get("ports", {})
    pol = ports_data.get("loading")
    pod = ports_data.get("discharge")
    
    if pol:
        if isinstance(pol, str):
            baseline._port_of_loading_info = PortInfo(name=pol)
        elif isinstance(pol, dict):
            baseline._port_of_loading_info = PortInfo(
                name=pol.get("name") or pol.get("port"),
                country=pol.get("country"),
            )
        pol_status, pol_error, pol_reason = _get_missing_status("port_of_loading")
        set_field(
            baseline.port_of_loading,
            baseline._port_of_loading_info.name if baseline._port_of_loading_info else None,
            status_override=pol_status,
            error=pol_error,
            missing_reason=pol_reason,
        )
    else:
        pol_status, pol_error, pol_reason = _get_missing_status("port_of_loading")
        set_field(
            baseline.port_of_loading,
            None,
            status_override=pol_status,
            error=pol_error,
            missing_reason=pol_reason,
        )
    
    if pod:
        if isinstance(pod, str):
            baseline._port_of_discharge_info = PortInfo(name=pod)
        elif isinstance(pod, dict):
            baseline._port_of_discharge_info = PortInfo(
                name=pod.get("name") or pod.get("port"),
                country=pod.get("country"),
            )
        pod_status, pod_error, pod_reason = _get_missing_status("port_of_discharge")
        set_field(
            baseline.port_of_discharge,
            baseline._port_of_discharge_info.name if baseline._port_of_discharge_info else None,
            status_override=pod_status,
            error=pod_error,
            missing_reason=pod_reason,
        )
    else:
        pod_status, pod_error, pod_reason = _get_missing_status("port_of_discharge")
        set_field(
            baseline.port_of_discharge,
            None,
            status_override=pod_status,
            error=pod_error,
            missing_reason=pod_reason,
        )
    
    # Incoterm
    incoterm_status, incoterm_error, incoterm_reason = _get_missing_status("incoterm")
    set_field(
        baseline.incoterm,
        extraction_result.get("incoterm"),
        status_override=incoterm_status,
        error=incoterm_error,
        missing_reason=incoterm_reason,
    )
    
    # Goods
    goods_items = extraction_result.get("goods", [])
    goods_desc_parts = []
    for item in goods_items:
        if isinstance(item, dict):
            desc = item.get("description") or item.get("line") or ""
            if desc:
                goods_desc_parts.append(desc)
                baseline._goods_items.append(GoodsItem(
                    description=desc,
                    quantity=item.get("quantity", {}).get("value") if isinstance(item.get("quantity"), dict) else item.get("quantity"),
                    unit=item.get("quantity", {}).get("unit") if isinstance(item.get("quantity"), dict) else None,
                    hs_code=item.get("hs_code"),
                ))
        elif isinstance(item, str):
            goods_desc_parts.append(item)
            baseline._goods_items.append(GoodsItem(description=item))
    
    goods_desc = "\n".join(goods_desc_parts) if goods_desc_parts else None
    goods_status, goods_error, goods_reason = _get_missing_status("goods_description")
    set_field(
        baseline.goods_description,
        goods_desc,
        status_override=goods_status,
        error=goods_error,
        missing_reason=goods_reason,
    )
    
    # HS Codes
    baseline._hs_codes = extraction_result.get("hs_codes", [])
    
    # Documents required
    docs_required = extraction_result.get("documents_required", [])
    baseline._documents_list = docs_required if isinstance(docs_required, list) else []
    docs_status, docs_error, docs_reason = _get_missing_status("documents_required")
    set_field(
        baseline.documents_required,
        docs_required if docs_required else None,
        status_override=docs_status,
        error=docs_error,
        missing_reason=docs_reason,
    )
    
    # UCP Reference
    ucp_status, ucp_error, ucp_reason = _get_missing_status("ucp_reference")
    set_field(
        baseline.ucp_reference,
        extraction_result.get("ucp_reference"),
        status_override=ucp_status,
        error=ucp_error,
        missing_reason=ucp_reason,
    )
    
    # Additional conditions (47A clauses) - canonical name is "additional_conditions"
    conditions = extraction_result.get("additional_conditions", []) or extraction_result.get("clauses_47a", [])
    baseline._conditions_list = conditions if isinstance(conditions, list) else []
    conditions_status, conditions_error, conditions_reason = _get_missing_status("additional_conditions")
    set_field(
        baseline.additional_conditions,
        conditions if conditions else None,
        status_override=conditions_status,
        error=conditions_error,
        missing_reason=conditions_reason,
    )
    
    logger.info(
        "Created LCBaseline: completeness=%.1f%%, critical_missing=%s, valid=%s",
        baseline.extraction_completeness * 100,
        [f.field_name for f in baseline.get_missing_critical()],
        baseline.is_valid_for_validation,
    )
    
    return baseline

