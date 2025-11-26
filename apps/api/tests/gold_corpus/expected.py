"""
Expected results schema for gold corpus test sets.

Each test set has an expected.json that defines:
1. Which fields should be extracted (and expected values)
2. Which validation issues should be raised
3. Which validation issues should NOT be raised (false positive checks)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import json
from pathlib import Path


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MEDIUM = "medium"
    MINOR = "minor"


class FieldCriticality(str, Enum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    OPTIONAL = "optional"


@dataclass
class ExpectedField:
    document_type: str
    field_name: str
    expected_value: Any
    match_type: str = "exact"
    tolerance: Optional[float] = None
    criticality: FieldCriticality = FieldCriticality.IMPORTANT
    
    def matches(self, actual_value: Any) -> bool:
        if actual_value is None:
            return False
        
        if self.match_type == "exact":
            return str(actual_value).strip().lower() == str(self.expected_value).strip().lower()
        elif self.match_type == "contains":
            return str(self.expected_value).lower() in str(actual_value).lower()
        elif self.match_type == "regex":
            import re
            return bool(re.search(self.expected_value, str(actual_value), re.I))
        elif self.match_type == "numeric_tolerance":
            try:
                actual = float(str(actual_value).replace(",", ""))
                expected = float(str(self.expected_value).replace(",", ""))
                tolerance = self.tolerance or 0.01
                return abs(actual - expected) / expected <= tolerance
            except (ValueError, TypeError):
                return False
        return False


@dataclass
class ExpectedIssue:
    rule_id: str
    severity: IssueSeverity
    document_type: Optional[str] = None
    title_contains: Optional[str] = None
    description: Optional[str] = None
    
    def matches(self, actual_issue: Dict[str, Any]) -> bool:
        actual_rule = str(actual_issue.get("rule", "")).upper().replace("_", "-").replace(" ", "-")
        expected_rule = self.rule_id.upper().replace("_", "-").replace(" ", "-")
        
        if actual_rule != expected_rule:
            return False
        
        actual_severity = str(actual_issue.get("severity", "")).lower()
        if actual_severity != self.severity.value:
            return False
        
        if self.document_type:
            actual_doc = str(actual_issue.get("document_type", "") or actual_issue.get("document", "")).lower()
            if self.document_type.lower() not in actual_doc:
                return False
        
        if self.title_contains:
            actual_title = str(actual_issue.get("title", "")).lower()
            if self.title_contains.lower() not in actual_title:
                return False
        
        return True


@dataclass
class FalsePositiveCheck:
    rule_id: str
    document_type: Optional[str] = None
    description: str = ""
    
    def triggered_by(self, actual_issue: Dict[str, Any]) -> bool:
        actual_rule = str(actual_issue.get("rule", "")).upper().replace("_", "-")
        expected_rule = self.rule_id.upper().replace("_", "-")
        
        if actual_rule != expected_rule:
            return False
        
        if self.document_type:
            actual_doc = str(actual_issue.get("document_type", "") or actual_issue.get("document", "")).lower()
            if self.document_type.lower() not in actual_doc:
                return False
        
        return True


@dataclass
class ExpectedResult:
    set_id: str
    description: str
    version: str = "1.0"
    expected_compliance_rate: Optional[float] = None
    compliance_tolerance: float = 5.0
    expected_fields: List[ExpectedField] = field(default_factory=list)
    expected_issues: List[ExpectedIssue] = field(default_factory=list)
    false_positive_checks: List[FalsePositiveCheck] = field(default_factory=list)
    expected_status: str = "warning"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "set_id": self.set_id,
            "description": self.description,
            "version": self.version,
            "expected_compliance_rate": self.expected_compliance_rate,
            "compliance_tolerance": self.compliance_tolerance,
            "expected_status": self.expected_status,
            "expected_fields": [
                {
                    "document_type": f.document_type,
                    "field_name": f.field_name,
                    "expected_value": f.expected_value,
                    "match_type": f.match_type,
                    "tolerance": f.tolerance,
                    "criticality": f.criticality.value,
                }
                for f in self.expected_fields
            ],
            "expected_issues": [
                {
                    "rule_id": i.rule_id,
                    "severity": i.severity.value,
                    "document_type": i.document_type,
                    "title_contains": i.title_contains,
                    "description": i.description,
                }
                for i in self.expected_issues
            ],
            "false_positive_checks": [
                {
                    "rule_id": f.rule_id,
                    "document_type": f.document_type,
                    "description": f.description,
                }
                for f in self.false_positive_checks
            ],
        }
    
    def save(self, path: Path):
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> "ExpectedResult":
        with open(path, 'r') as f:
            data = json.load(f)
        
        return cls(
            set_id=data["set_id"],
            description=data["description"],
            version=data.get("version", "1.0"),
            expected_compliance_rate=data.get("expected_compliance_rate"),
            compliance_tolerance=data.get("compliance_tolerance", 5.0),
            expected_status=data.get("expected_status", "warning"),
            expected_fields=[
                ExpectedField(
                    document_type=f["document_type"],
                    field_name=f["field_name"],
                    expected_value=f["expected_value"],
                    match_type=f.get("match_type", "exact"),
                    tolerance=f.get("tolerance"),
                    criticality=FieldCriticality(f.get("criticality", "important")),
                )
                for f in data.get("expected_fields", [])
            ],
            expected_issues=[
                ExpectedIssue(
                    rule_id=i["rule_id"],
                    severity=IssueSeverity(i["severity"]),
                    document_type=i.get("document_type"),
                    title_contains=i.get("title_contains"),
                    description=i.get("description"),
                )
                for i in data.get("expected_issues", [])
            ],
            false_positive_checks=[
                FalsePositiveCheck(
                    rule_id=f["rule_id"],
                    document_type=f.get("document_type"),
                    description=f.get("description", ""),
                )
                for f in data.get("false_positive_checks", [])
            ],
        )

