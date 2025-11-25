"""
Rule Executor - Execute rules against validation context.

This module evaluates rules defined in YAML against the actual
document data extracted during validation.

Features:
1. Condition evaluation with multiple operators
2. Field path resolution (e.g., "lc.amount.value")
3. Fuzzy text matching with configurable threshold
4. Issue generation from rule actions
5. Execution audit trail
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from .rule_schema import (
    Rule,
    RuleSet,
    RuleCondition,
    RuleAction,
    RuleCategory,
    RuleSeverity,
    ConditionOperator,
)
from .rule_loader import RuleLoader, get_rule_loader


logger = logging.getLogger(__name__)


@dataclass
class ConditionResult:
    """Result of evaluating a single condition."""
    condition: RuleCondition
    passed: bool
    actual_value: Any
    expected_value: Any
    error: Optional[str] = None


@dataclass
class RuleExecutionResult:
    """Result of executing a single rule."""
    rule: Rule
    passed: bool  # True = rule conditions passed (no issue), False = triggered (issue)
    condition_results: List[ConditionResult]
    issue: Optional[Dict[str, Any]] = None  # Generated issue if rule triggered
    execution_time_ms: int = 0
    skipped: bool = False  # True if rule was skipped (missing required fields)
    skip_reason: Optional[str] = None


@dataclass
class ExecutionSummary:
    """Summary of rule execution."""
    total_rules: int
    passed: int
    failed: int  # Rules that triggered (generated issues)
    skipped: int
    execution_time_ms: int
    issues: List[Dict[str, Any]]
    execution_results: List[RuleExecutionResult] = field(default_factory=list)


class RuleExecutor:
    """
    Executes validation rules against document context.
    
    Usage:
        executor = RuleExecutor()
        result = executor.execute_all_rules(context)
        issues = result.issues
    """
    
    def __init__(
        self,
        rule_loader: Optional[RuleLoader] = None,
        fuzzy_threshold: float = 0.8,
    ):
        self.rule_loader = rule_loader or get_rule_loader()
        self.fuzzy_threshold = fuzzy_threshold
    
    def execute_all_rules(
        self,
        context: Dict[str, Any],
        categories: Optional[List[RuleCategory]] = None,
    ) -> ExecutionSummary:
        """
        Execute all applicable rules against the validation context.
        
        Args:
            context: Validation context with extracted document data
            categories: Optional filter for rule categories
            
        Returns:
            ExecutionSummary with all results and generated issues
        """
        start_time = time.perf_counter()
        
        # Load rules
        rules = self.rule_loader.load_enabled_rules()
        
        # Filter by categories if specified
        if categories:
            rules = [r for r in rules if r.category in categories]
        
        # Execute each rule
        results: List[RuleExecutionResult] = []
        issues: List[Dict[str, Any]] = []
        
        for rule in rules:
            result = self.execute_rule(rule, context)
            results.append(result)
            
            if result.issue:
                issues.append(result.issue)
        
        execution_time = int((time.perf_counter() - start_time) * 1000)
        
        return ExecutionSummary(
            total_rules=len(rules),
            passed=sum(1 for r in results if r.passed and not r.skipped),
            failed=sum(1 for r in results if not r.passed and not r.skipped),
            skipped=sum(1 for r in results if r.skipped),
            execution_time_ms=execution_time,
            issues=issues,
            execution_results=results,
        )
    
    def execute_rule(
        self,
        rule: Rule,
        context: Dict[str, Any],
    ) -> RuleExecutionResult:
        """
        Execute a single rule against the context.
        
        Args:
            rule: Rule to execute
            context: Validation context
            
        Returns:
            RuleExecutionResult with pass/fail status and any generated issue
        """
        start_time = time.perf_counter()
        
        # Check if required fields exist
        if rule.requires_fields:
            missing = self._check_required_fields(rule.requires_fields, context)
            if missing:
                return RuleExecutionResult(
                    rule=rule,
                    passed=True,  # Don't fail if fields missing - skip
                    condition_results=[],
                    skipped=True,
                    skip_reason=f"Missing required fields: {missing}",
                    execution_time_ms=int((time.perf_counter() - start_time) * 1000),
                )
        
        # Evaluate all conditions
        condition_results = []
        all_passed = True
        
        for condition in rule.conditions:
            result = self._evaluate_condition(condition, context)
            condition_results.append(result)
            
            if not result.passed:
                all_passed = False
        
        execution_time = int((time.perf_counter() - start_time) * 1000)
        
        # If any condition failed, rule triggers (generates issue)
        issue = None
        if not all_passed and rule.action:
            issue = self._generate_issue(rule, condition_results, context)
        
        return RuleExecutionResult(
            rule=rule,
            passed=all_passed,
            condition_results=condition_results,
            issue=issue,
            execution_time_ms=execution_time,
            skipped=False,
        )
    
    def execute_ruleset(
        self,
        ruleset: RuleSet,
        context: Dict[str, Any],
    ) -> ExecutionSummary:
        """Execute all rules in a ruleset."""
        start_time = time.perf_counter()
        
        results: List[RuleExecutionResult] = []
        issues: List[Dict[str, Any]] = []
        
        for rule in ruleset.get_enabled_rules():
            result = self.execute_rule(rule, context)
            results.append(result)
            
            if result.issue:
                issues.append(result.issue)
        
        execution_time = int((time.perf_counter() - start_time) * 1000)
        
        return ExecutionSummary(
            total_rules=len(ruleset.rules),
            passed=sum(1 for r in results if r.passed and not r.skipped),
            failed=sum(1 for r in results if not r.passed and not r.skipped),
            skipped=sum(1 for r in results if r.skipped),
            execution_time_ms=execution_time,
            issues=issues,
            execution_results=results,
        )
    
    def _check_required_fields(
        self,
        required: List[str],
        context: Dict[str, Any],
    ) -> List[str]:
        """Check which required fields are missing."""
        missing = []
        for field_path in required:
            value = self._resolve_field(field_path, context)
            if value is None or value == "":
                missing.append(field_path)
        return missing
    
    def _resolve_field(
        self,
        field_path: str,
        context: Dict[str, Any],
    ) -> Any:
        """
        Resolve a field path to its value in context.
        
        Field paths use dot notation: "lc.amount.value"
        """
        parts = field_path.split(".")
        current = context
        
        for part in parts:
            if current is None:
                return None
            
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
        
        return current
    
    def _evaluate_condition(
        self,
        condition: RuleCondition,
        context: Dict[str, Any],
    ) -> ConditionResult:
        """Evaluate a single condition against context."""
        try:
            actual_value = self._resolve_field(condition.field, context)
            expected_value = condition.value
            
            # Resolve compare_field if specified
            if condition.compare_field:
                expected_value = self._resolve_field(condition.compare_field, context)
            
            # Normalize strings if requested
            if condition.normalize:
                actual_value = self._normalize_value(actual_value)
                expected_value = self._normalize_value(expected_value)
            
            # Evaluate based on operator
            passed = self._evaluate_operator(
                condition.operator,
                actual_value,
                expected_value,
                condition.threshold,
                condition.case_sensitive,
            )
            
            return ConditionResult(
                condition=condition,
                passed=passed,
                actual_value=actual_value,
                expected_value=expected_value,
            )
            
        except Exception as e:
            logger.error("Error evaluating condition %s: %s", condition.field, e)
            return ConditionResult(
                condition=condition,
                passed=False,
                actual_value=None,
                expected_value=condition.value,
                error=str(e),
            )
    
    def _evaluate_operator(
        self,
        operator: ConditionOperator,
        actual: Any,
        expected: Any,
        threshold: Optional[float],
        case_sensitive: bool,
    ) -> bool:
        """Evaluate a condition operator."""
        
        # Presence checks
        if operator == ConditionOperator.EXISTS:
            return actual is not None and actual != "" and actual != []
        
        if operator == ConditionOperator.NOT_EXISTS:
            return actual is None or actual == "" or actual == []
        
        if operator == ConditionOperator.IS_NULL:
            return actual is None
        
        if operator == ConditionOperator.IS_NOT_NULL:
            return actual is not None
        
        # String comparisons
        if operator == ConditionOperator.EQUALS:
            if not case_sensitive and isinstance(actual, str) and isinstance(expected, str):
                return actual.lower() == expected.lower()
            return actual == expected
        
        if operator == ConditionOperator.NOT_EQUALS:
            if not case_sensitive and isinstance(actual, str) and isinstance(expected, str):
                return actual.lower() != expected.lower()
            return actual != expected
        
        if operator == ConditionOperator.CONTAINS:
            if actual is None or expected is None:
                return False
            actual_str = str(actual).lower() if not case_sensitive else str(actual)
            expected_str = str(expected).lower() if not case_sensitive else str(expected)
            return expected_str in actual_str
        
        if operator == ConditionOperator.NOT_CONTAINS:
            if actual is None:
                return True
            if expected is None:
                return False
            actual_str = str(actual).lower() if not case_sensitive else str(actual)
            expected_str = str(expected).lower() if not case_sensitive else str(expected)
            return expected_str not in actual_str
        
        if operator == ConditionOperator.STARTS_WITH:
            if actual is None or expected is None:
                return False
            actual_str = str(actual).lower() if not case_sensitive else str(actual)
            expected_str = str(expected).lower() if not case_sensitive else str(expected)
            return actual_str.startswith(expected_str)
        
        if operator == ConditionOperator.ENDS_WITH:
            if actual is None or expected is None:
                return False
            actual_str = str(actual).lower() if not case_sensitive else str(actual)
            expected_str = str(expected).lower() if not case_sensitive else str(expected)
            return actual_str.endswith(expected_str)
        
        if operator == ConditionOperator.MATCHES:
            if actual is None or expected is None:
                return False
            try:
                pattern = re.compile(str(expected), re.IGNORECASE if not case_sensitive else 0)
                return bool(pattern.search(str(actual)))
            except re.error:
                return False
        
        # Numeric comparisons
        if operator in (ConditionOperator.GREATER_THAN, ConditionOperator.GREATER_EQUAL,
                        ConditionOperator.LESS_THAN, ConditionOperator.LESS_EQUAL):
            try:
                actual_num = float(str(actual).replace(",", "")) if actual else 0
                expected_num = float(str(expected).replace(",", "")) if expected else 0
                
                if operator == ConditionOperator.GREATER_THAN:
                    return actual_num > expected_num
                if operator == ConditionOperator.GREATER_EQUAL:
                    return actual_num >= expected_num
                if operator == ConditionOperator.LESS_THAN:
                    return actual_num < expected_num
                if operator == ConditionOperator.LESS_EQUAL:
                    return actual_num <= expected_num
            except (ValueError, TypeError):
                return False
        
        # Fuzzy matching
        if operator == ConditionOperator.SIMILAR_TO:
            if actual is None or expected is None:
                return False
            similarity = self._calculate_similarity(str(actual), str(expected))
            threshold_val = threshold or self.fuzzy_threshold
            return similarity >= threshold_val
        
        # Field matching (same as equals but with resolved compare_field)
        if operator == ConditionOperator.MATCHES_FIELD:
            return self._evaluate_operator(
                ConditionOperator.EQUALS, actual, expected, threshold, case_sensitive
            )
        
        # List operations
        if operator == ConditionOperator.IN:
            if not isinstance(expected, (list, tuple, set)):
                return False
            return actual in expected
        
        if operator == ConditionOperator.NOT_IN:
            if not isinstance(expected, (list, tuple, set)):
                return True
            return actual not in expected
        
        # Default to false for unknown operators
        logger.warning("Unknown operator: %s", operator)
        return False
    
    def _normalize_value(self, value: Any) -> Any:
        """Normalize a value for comparison."""
        if value is None:
            return None
        if isinstance(value, str):
            # Normalize whitespace, trim
            normalized = re.sub(r'\s+', ' ', value).strip()
            return normalized
        return value
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings.
        
        Uses a simplified token-based Jaccard similarity.
        """
        if not str1 or not str2:
            return 0.0
        
        # Tokenize and normalize
        tokens1 = set(re.findall(r'\w+', str1.lower()))
        tokens2 = set(re.findall(r'\w+', str2.lower()))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # Jaccard similarity
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        return len(intersection) / len(union) if union else 0.0
    
    def _generate_issue(
        self,
        rule: Rule,
        condition_results: List[ConditionResult],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate an issue from a triggered rule."""
        action = rule.action
        
        # Find the first failed condition for expected/actual
        failed_condition = next(
            (cr for cr in condition_results if not cr.passed),
            None
        )
        
        # Format expected/actual using templates if provided
        expected = self._format_template(
            action.expected_template or str(failed_condition.expected_value if failed_condition else ""),
            context
        )
        actual = self._format_template(
            action.actual_template or str(failed_condition.actual_value if failed_condition else ""),
            context
        )
        
        # Build document references
        doc_names = []
        doc_ids = []
        documents = context.get("documents", [])
        
        for doc_type in rule.source_documents + rule.target_documents:
            for doc in documents:
                if doc.get("document_type") == doc_type or doc.get("type") == doc_type:
                    doc_names.append(doc.get("name") or doc.get("filename") or doc_type)
                    if doc.get("id"):
                        doc_ids.append(doc["id"])
        
        if not doc_names:
            doc_names = rule.source_documents or ["Document"]
        
        return {
            "rule": rule.id,
            "title": action.title or rule.name,
            "passed": False,
            "severity": rule.severity.value if isinstance(rule.severity, RuleSeverity) else rule.severity,
            "message": action.message or rule.description,
            "expected": expected,
            "actual": actual,
            "suggestion": action.suggestion or f"Review {rule.name} requirements",
            "documents": doc_names,
            "document_names": doc_names,
            "document_ids": doc_ids,
            "display_card": True,
            "ruleset_domain": f"icc.lcopilot.{rule.category.value if isinstance(rule.category, RuleCategory) else rule.category}",
            "ucp_reference": rule.ucp_reference,
            "isbp_reference": rule.isbp_reference,
            "rule_version": rule.version,
            "auto_generated": True,
        }
    
    def _format_template(self, template: str, context: Dict[str, Any]) -> str:
        """Format a template string with context values."""
        if not template:
            return ""
        
        # Find all {field.path} placeholders
        pattern = re.compile(r'\{([^}]+)\}')
        
        def replace_field(match):
            field_path = match.group(1)
            value = self._resolve_field(field_path, context)
            if value is None:
                return "N/A"
            return str(value)
        
        try:
            return pattern.sub(replace_field, template)
        except Exception:
            return template


# Convenience function
def execute_rules(
    context: Dict[str, Any],
    categories: Optional[List[RuleCategory]] = None,
) -> ExecutionSummary:
    """
    Execute all applicable rules against context.
    
    This is the main entry point for rule execution.
    """
    executor = RuleExecutor()
    return executor.execute_all_rules(context, categories)

