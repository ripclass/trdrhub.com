"""
Data models for the rules engine.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from uuid import UUID

from ..models import DiscrepancyType, DiscrepancySeverity, DocumentType


class FieldType(str, Enum):
    """Types of fields that can be validated."""
    DATE = "date"
    AMOUNT = "amount"
    PARTY = "party"
    PORT = "port"
    TEXT = "text"
    NUMBER = "number"


class ValidationStatus(str, Enum):
    """Status of a validation rule."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ExtractedField:
    """Represents a field extracted from a document."""
    field_name: str
    field_type: FieldType
    value: Optional[str]
    confidence: float
    document_type: DocumentType
    raw_text: Optional[str] = None
    normalized_value: Optional[str] = None


@dataclass
class ValidationRule:
    """Represents a validation rule."""
    rule_id: str
    rule_name: str
    description: str
    field_type: FieldType
    severity: DiscrepancySeverity
    is_cross_document: bool = False


@dataclass
class ValidationResult:
    """Result of applying a validation rule."""
    rule: ValidationRule
    status: ValidationStatus
    message: str
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    confidence: float = 1.0
    affected_documents: List[DocumentType] = None
    
    def __post_init__(self):
        if self.affected_documents is None:
            self.affected_documents = []


@dataclass
class FieldComparison:
    """Comparison of the same field across different documents."""
    field_name: str
    field_type: FieldType
    lc_field: Optional[ExtractedField] = None
    invoice_field: Optional[ExtractedField] = None
    bl_field: Optional[ExtractedField] = None
    is_consistent: bool = True
    discrepancies: List[str] = None
    
    def __post_init__(self):
        if self.discrepancies is None:
            self.discrepancies = []


@dataclass
class DocumentValidationSummary:
    """Summary of validation results for all documents."""
    session_id: UUID
    total_rules: int
    passed_rules: int
    failed_rules: int
    warnings: int
    critical_issues: int
    major_issues: int
    minor_issues: int
    validation_results: List[ValidationResult]
    field_comparisons: List[FieldComparison]
    processing_time_ms: int
    validated_at: datetime