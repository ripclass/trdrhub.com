"""
External Rules Engine - Phase 3

This module provides externalized validation rules in YAML format,
enabling:
1. Version control of rules
2. Audit trails for rule changes
3. Live updates without code deployment
4. Bank-specific rule customization
5. UCP600/ISBP745 compliance tracking

Key Components:
- rule_schema.py: Pydantic models for rule definitions
- rule_loader.py: Load rules from YAML/database
- rule_executor.py: Execute rules against validation context
- rule_catalog.py: Registry of all available rules

Default Rules (YAML files):
- lc_extraction_rules.yaml: Missing field detection
- crossdoc_rules.yaml: Cross-document validation
- ucp600_rules.yaml: UCP600 compliance rules
- document_rules.yaml: Document-specific rules
"""

from .rule_schema import (
    Rule,
    RuleCategory,
    RuleSeverity,
    RuleCondition,
    RuleAction,
    RuleSet,
)
from .rule_loader import RuleLoader, get_rule_loader
from .rule_executor import RuleExecutor, RuleExecutionResult

__all__ = [
    "Rule",
    "RuleCategory", 
    "RuleSeverity",
    "RuleCondition",
    "RuleAction",
    "RuleSet",
    "RuleLoader",
    "get_rule_loader",
    "RuleExecutor",
    "RuleExecutionResult",
]

