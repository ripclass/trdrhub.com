"""
Rule Schema - Pydantic models for external rule definitions.

Rules are defined in YAML and loaded into these models for execution.
This schema ensures rules are:
1. Well-structured and validated
2. Self-documenting with metadata
3. Versionable and auditable
4. Executable with clear semantics
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime


logger = logging.getLogger(__name__)


class RuleCategory(str, Enum):
    """Categories of validation rules."""
    EXTRACTION = "extraction"           # LC field extraction checks
    CROSSDOC = "crossdoc"              # Cross-document validation
    UCP600 = "ucp600"                  # UCP600 compliance
    ISBP745 = "isbp745"                # ISBP745 compliance
    DOCUMENT = "document"              # Document-specific rules
    TIMING = "timing"                  # Date/timeline validation
    AMOUNT = "amount"                  # Amount/tolerance validation
    PARTY = "party"                    # Party name matching
    PORT = "port"                      # Port/shipment validation
    GOODS = "goods"                    # Goods description matching
    CUSTOM = "custom"                  # Bank-specific custom rules


class RuleSeverity(str, Enum):
    """Severity levels for rule violations."""
    CRITICAL = "critical"   # Blocks validation, must be fixed
    MAJOR = "major"         # Serious issue, likely bank rejection
    MINOR = "minor"         # Warning, should be reviewed
    INFO = "info"           # Informational, no action required


class ConditionOperator(str, Enum):
    """Operators for rule conditions."""
    # Presence checks
    EXISTS = "exists"               # Field exists and is not empty
    NOT_EXISTS = "not_exists"       # Field is missing or empty
    IS_NULL = "is_null"             # Field is explicitly null
    IS_NOT_NULL = "is_not_null"     # Field is not null
    
    # Comparison operators
    EQUALS = "equals"               # Exact match
    NOT_EQUALS = "not_equals"       # Not equal
    CONTAINS = "contains"           # String contains
    NOT_CONTAINS = "not_contains"   # String does not contain
    STARTS_WITH = "starts_with"     # String starts with
    ENDS_WITH = "ends_with"         # String ends with
    MATCHES = "matches"             # Regex match
    
    # Numeric comparisons
    GREATER_THAN = "gt"             # Greater than
    GREATER_EQUAL = "gte"           # Greater than or equal
    LESS_THAN = "lt"                # Less than
    LESS_EQUAL = "lte"              # Less than or equal
    BETWEEN = "between"             # Value is between min and max
    
    # Date comparisons
    BEFORE = "before"               # Date is before
    AFTER = "after"                 # Date is after
    WITHIN_DAYS = "within_days"     # Date is within N days
    
    # Cross-document comparisons
    MATCHES_FIELD = "matches_field" # Matches another document's field
    SIMILAR_TO = "similar_to"       # Fuzzy match with threshold
    
    # List operations
    IN = "in"                       # Value is in list
    NOT_IN = "not_in"               # Value is not in list
    ALL_OF = "all_of"               # All conditions must match
    ANY_OF = "any_of"               # Any condition matches
    NONE_OF = "none_of"             # No conditions match


@dataclass
class RuleCondition:
    """
    A single condition in a rule.
    
    Example YAML:
    ```yaml
    condition:
      field: "lc.amount.value"
      operator: "exists"
    ```
    """
    field: str                              # Field path (e.g., "lc.amount.value")
    operator: ConditionOperator             # Comparison operator
    value: Optional[Any] = None             # Expected value (for comparison ops)
    compare_field: Optional[str] = None     # Other field to compare against
    threshold: Optional[float] = None       # For fuzzy matching (0.0-1.0)
    case_sensitive: bool = False            # For string comparisons
    normalize: bool = True                  # Normalize strings before comparison
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator.value if isinstance(self.operator, ConditionOperator) else self.operator,
            "value": self.value,
            "compare_field": self.compare_field,
            "threshold": self.threshold,
            "case_sensitive": self.case_sensitive,
            "normalize": self.normalize,
        }


@dataclass
class RuleAction:
    """
    Action to take when rule triggers.
    
    Example YAML:
    ```yaml
    action:
      type: "issue"
      title: "LC Amount Missing"
      message: "The LC amount could not be extracted"
    ```
    """
    type: str = "issue"                     # "issue", "warning", "block", "log"
    title: str = ""                         # Issue title
    message: str = ""                       # Detailed message
    suggestion: Optional[str] = None        # Suggested fix
    expected_template: Optional[str] = None # Template for expected value
    actual_template: Optional[str] = None   # Template for actual value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "suggestion": self.suggestion,
            "expected_template": self.expected_template,
            "actual_template": self.actual_template,
        }


@dataclass
class Rule:
    """
    A complete validation rule definition.
    
    Example YAML:
    ```yaml
    - id: CROSSDOC-AMOUNT-1
      name: Invoice Amount vs LC Amount
      category: crossdoc
      severity: major
      description: |
        Validates that invoice amount does not exceed LC amount plus tolerance.
      ucp_reference: "UCP600 Article 18(b)"
      enabled: true
      
      conditions:
        - field: "lc.amount.value"
          operator: "exists"
        - field: "invoice.amount"
          operator: "exists"
        - field: "invoice.amount"
          operator: "lte"
          compare_field: "lc.amount.value"
          
      action:
        type: "issue"
        title: "Invoice Amount Exceeds LC"
        message: "Invoice amount exceeds LC value"
        expected_template: "<= {lc.amount.value} {lc.amount.currency}"
        actual_template: "{invoice.amount} {invoice.currency}"
    ```
    """
    id: str                                         # Unique rule identifier
    name: str                                       # Human-readable name
    category: RuleCategory                          # Rule category
    severity: RuleSeverity                          # Violation severity
    description: str = ""                           # Detailed description
    
    # Rule conditions (all must pass for rule to NOT trigger)
    conditions: List[RuleCondition] = field(default_factory=list)
    
    # Action when rule triggers (conditions fail)
    action: Optional[RuleAction] = None
    
    # Metadata
    enabled: bool = True                            # Is rule active?
    version: str = "1.0.0"                          # Rule version
    
    # Compliance references
    ucp_reference: Optional[str] = None             # UCP600 article reference
    isbp_reference: Optional[str] = None            # ISBP745 reference
    
    # Documents involved
    source_documents: List[str] = field(default_factory=list)  # e.g., ["letter_of_credit"]
    target_documents: List[str] = field(default_factory=list)  # e.g., ["commercial_invoice"]
    
    # Execution hints
    requires_fields: List[str] = field(default_factory=list)   # Fields that must exist
    optional_fields: List[str] = field(default_factory=list)   # Fields that may exist
    
    # Override/customization
    can_override: bool = True                       # Can bank override this rule?
    override_requires_approval: bool = False        # Does override need approval?
    
    # Audit
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value if isinstance(self.category, RuleCategory) else self.category,
            "severity": self.severity.value if isinstance(self.severity, RuleSeverity) else self.severity,
            "description": self.description,
            "conditions": [c.to_dict() for c in self.conditions],
            "action": self.action.to_dict() if self.action else None,
            "enabled": self.enabled,
            "version": self.version,
            "ucp_reference": self.ucp_reference,
            "isbp_reference": self.isbp_reference,
            "source_documents": self.source_documents,
            "target_documents": self.target_documents,
            "requires_fields": self.requires_fields,
            "optional_fields": self.optional_fields,
            "can_override": self.can_override,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Rule:
        """Create a Rule from a dictionary (e.g., loaded from YAML)."""
        conditions = []
        for cond_data in data.get("conditions", []):
            operator = cond_data.get("operator", "exists")
            if isinstance(operator, str):
                try:
                    operator = ConditionOperator(operator)
                except ValueError:
                    operator = ConditionOperator.EXISTS
            
            conditions.append(RuleCondition(
                field=cond_data.get("field", ""),
                operator=operator,
                value=cond_data.get("value"),
                compare_field=cond_data.get("compare_field"),
                threshold=cond_data.get("threshold"),
                case_sensitive=cond_data.get("case_sensitive", False),
                normalize=cond_data.get("normalize", True),
            ))
        
        action_data = data.get("action", {})
        action = RuleAction(
            type=action_data.get("type", "issue"),
            title=action_data.get("title", ""),
            message=action_data.get("message", ""),
            suggestion=action_data.get("suggestion"),
            expected_template=action_data.get("expected_template"),
            actual_template=action_data.get("actual_template"),
        ) if action_data else None
        
        category = data.get("category", "custom")
        if isinstance(category, str):
            try:
                category = RuleCategory(category)
            except ValueError:
                category = RuleCategory.CUSTOM
        
        severity = data.get("severity", "minor")
        if isinstance(severity, str):
            try:
                severity = RuleSeverity(severity)
            except ValueError:
                severity = RuleSeverity.MINOR
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            category=category,
            severity=severity,
            description=data.get("description", ""),
            conditions=conditions,
            action=action,
            enabled=data.get("enabled", True),
            version=data.get("version", "1.0.0"),
            ucp_reference=data.get("ucp_reference"),
            isbp_reference=data.get("isbp_reference"),
            source_documents=data.get("source_documents", []),
            target_documents=data.get("target_documents", []),
            requires_fields=data.get("requires_fields", []),
            optional_fields=data.get("optional_fields", []),
            can_override=data.get("can_override", True),
            override_requires_approval=data.get("override_requires_approval", False),
        )


@dataclass
class RuleSet:
    """
    A collection of related rules.
    
    Example YAML:
    ```yaml
    ruleset:
      id: ucp600-crossdoc
      name: UCP600 Cross-Document Rules
      version: 1.0.0
      description: Cross-document validation rules per UCP600
      
    rules:
      - id: CROSSDOC-GOODS-1
        ...
    ```
    """
    id: str                                 # Ruleset identifier
    name: str                               # Human-readable name
    version: str = "1.0.0"                  # Ruleset version
    description: str = ""                   # Description
    rules: List[Rule] = field(default_factory=list)
    
    # Metadata
    enabled: bool = True
    category: Optional[RuleCategory] = None
    ucp_version: str = "UCP600"             # UCP version this ruleset follows
    
    # Audit
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None
    
    def get_enabled_rules(self) -> List[Rule]:
        """Get all enabled rules."""
        return [r for r in self.rules if r.enabled]
    
    def get_rules_by_category(self, category: RuleCategory) -> List[Rule]:
        """Get rules by category."""
        return [r for r in self.rules if r.category == category]
    
    def get_rules_by_severity(self, severity: RuleSeverity) -> List[Rule]:
        """Get rules by severity."""
        return [r for r in self.rules if r.severity == severity]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "enabled": self.enabled,
            "category": self.category.value if self.category else None,
            "ucp_version": self.ucp_version,
            "rules": [r.to_dict() for r in self.rules],
            "rule_count": len(self.rules),
            "enabled_count": len(self.get_enabled_rules()),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RuleSet:
        """Create a RuleSet from a dictionary."""
        rules = [Rule.from_dict(r) for r in data.get("rules", [])]
        
        category = data.get("category")
        if isinstance(category, str):
            try:
                category = RuleCategory(category)
            except ValueError:
                category = None
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            rules=rules,
            enabled=data.get("enabled", True),
            category=category,
            ucp_version=data.get("ucp_version", "UCP600"),
        )

