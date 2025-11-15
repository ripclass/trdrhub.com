"""
Rule Evaluator

Evaluates JSON rules against LC document context.
Handles condition evaluation, field path resolution, and operator logic.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


class MissingFieldError(Exception):
    """Raised when a rule references a field that is not present in the context."""

    def __init__(self, field: Optional[str], operator: Optional[str]):
        self.field = field
        self.operator = operator
        message = f"Missing field '{field}' for operator '{operator}'"
        super().__init__(message)


class RuleEvaluator:
    """
    Evaluates rules against document context.
    
    Supports:
    - Field path resolution (dot notation: lc.goods_description)
    - All operators: equals, not_equals, contains, matches, within_days, before, after, in, not_in, exists, not_exists
    - value vs value_ref handling
    - day_type (banking vs calendar days)
    - applies_if preconditions
    """
    
    def __init__(self):
        self.banking_days_cache = {}  # Cache for banking day calculations
    
    def resolve_field_path(self, context: Dict[str, Any], field_path: str) -> Any:
        """
        Resolve a dot-notation field path from context.
        
        Examples:
        - "lc.goods_description" -> context["lc"]["goods_description"]
        - "invoice.amount" -> context["invoice"]["amount"]
        - "lc_number" -> context["lc_number"]
        """
        parts = field_path.split(".")
        value = context
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(value):
                    value = value[idx]
                else:
                    return None
            else:
                return None
            
            if value is None:
                return None
        
        return value
    
    def is_banking_day(self, date: datetime) -> bool:
        """Check if a date is a banking day (Monday-Friday, excluding holidays)."""
        # Simple implementation: Monday=0, Sunday=6
        # TODO: Add holiday calendar support
        weekday = date.weekday()
        return weekday < 5  # Monday to Friday
    
    def add_banking_days(self, start_date: datetime, days: int) -> datetime:
        """Add banking days to a date."""
        current = start_date
        added = 0
        
        while added < days:
            current += timedelta(days=1)
            if self.is_banking_day(current):
                added += 1
        
        return current
    
    def add_calendar_days(self, start_date: datetime, days: int) -> datetime:
        """Add calendar days to a date."""
        return start_date + timedelta(days=days)
    
    def evaluate_operator(
        self,
        operator: str,
        field_value: Any,
        condition_value: Any,
        value_ref: Optional[str],
        context: Dict[str, Any],
        day_type: Optional[str] = None,
        field_path: Optional[str] = None
    ) -> bool:
        """
        Evaluate a single operator condition.
        
        Args:
            operator: Operator name (equals, contains, within_days, etc.)
            field_value: Value from the document field
            condition_value: Literal value from condition (if not value_ref)
            value_ref: Reference to another field path (if not literal)
            context: Full document context for resolving references
            day_type: "banking" or "calendar" for time operators
            field_path: Field path being evaluated (for error messages)
        """
        # Resolve value_ref if present
        if value_ref:
            compare_value = self.resolve_field_path(context, value_ref)
        else:
            compare_value = condition_value
        
        if field_value is None:
            # Field doesn't exist for this rule
            if operator in ["exists", "not_exists", "is_empty"]:
                return operator == "not_exists" or operator == "is_empty"
            # Only raise MissingFieldError if field_path is provided and operator requires the field
            if field_path:
                raise MissingFieldError(field_path, operator)
            # Otherwise, return False (field doesn't exist, so condition fails)
            return False
        
        # Type coercion for comparisons
        try:
            # Try to convert to same type for comparison
            if isinstance(compare_value, (int, float)) and isinstance(field_value, str):
                try:
                    field_value = float(field_value)
                except (ValueError, TypeError):
                    pass
            elif isinstance(compare_value, str) and isinstance(field_value, (int, float)):
                compare_value = str(compare_value)
        except (ValueError, TypeError):
            pass
        
        # Evaluate operator
        if operator == "equals":
            return field_value == compare_value
        
        elif operator == "not_equals":
            return field_value != compare_value
        
        elif operator == "contains":
            if isinstance(field_value, str) and isinstance(compare_value, str):
                return compare_value.lower() in field_value.lower()
            elif isinstance(field_value, list):
                return compare_value in field_value
            return False
        
        elif operator == "not_contains":
            if isinstance(field_value, str) and isinstance(compare_value, str):
                return compare_value.lower() not in field_value.lower()
            elif isinstance(field_value, list):
                return compare_value not in field_value
            return True
        
        elif operator == "matches":
            if isinstance(field_value, str) and isinstance(compare_value, str):
                try:
                    return bool(re.match(compare_value, field_value))
                except re.error:
                    logger.warning(f"Invalid regex pattern: {compare_value}")
                    return False
            return False
        
        elif operator == "in":
            if isinstance(compare_value, list):
                return field_value in compare_value
            return False
        
        elif operator == "not_in":
            if isinstance(compare_value, list):
                return field_value not in compare_value
            return True
        
        elif operator == "greater_than_or_equal":
            try:
                return float(field_value) >= float(compare_value)
            except (ValueError, TypeError):
                return False
        
        elif operator == "less_than_or_equal":
            try:
                return float(field_value) <= float(compare_value)
            except (ValueError, TypeError):
                return False
        
        elif operator == "between":
            if not isinstance(condition_value, dict):
                return False
            try:
                field_numeric = float(field_value)
            except (ValueError, TypeError):
                return False
            
            minimum = condition_value.get("min")
            maximum = condition_value.get("max")
            tolerance = condition_value.get("tolerance", 0)
            allow_exceed = condition_value.get("allow_exceed_credit")
            allow_under = condition_value.get("allow_under_credit")
            min_percent = condition_value.get("min_percent")
            max_percent = condition_value.get("max_percent")
            
            if minimum is not None:
                try:
                    min_value = float(minimum)
                    if not allow_under:
                        min_value -= float(tolerance or 0)
                    if field_numeric < min_value:
                        return False
                except (ValueError, TypeError):
                    return False
            
            if maximum is not None:
                try:
                    max_value = float(maximum)
                    if not allow_exceed:
                        max_value += float(tolerance or 0)
                    if field_numeric > max_value:
                        return False
                except (ValueError, TypeError):
                    return False
            
            if min_percent is not None:
                try:
                    if field_numeric < float(min_percent):
                        return False
                except (ValueError, TypeError):
                    return False
            
            if max_percent is not None:
                try:
                    if field_numeric > float(max_percent):
                        return False
                except (ValueError, TypeError):
                    return False
            
            return True
        
        elif operator == "not_contains_any":
            if not compare_value:
                return True
            terms = compare_value if isinstance(compare_value, list) else [compare_value]
            if isinstance(field_value, str):
                lower_value = field_value.lower()
                return all(term.lower() not in lower_value for term in terms if isinstance(term, str))
            if isinstance(field_value, list):
                return not any(term in field_value for term in terms)
            return True
        
        elif operator == "greater_than":
            try:
                return float(field_value) > float(compare_value)
            except (ValueError, TypeError):
                return False
        
        elif operator == "less_than":
            try:
                return float(field_value) < float(compare_value)
            except (ValueError, TypeError):
                return False
        
        elif operator == "within_days":
            if not isinstance(field_value, (str, datetime)):
                return False
            
            # Parse dates
            if isinstance(field_value, str):
                try:
                    field_date = datetime.fromisoformat(field_value.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    return False
            else:
                field_date = field_value
            
            if not isinstance(compare_value, (str, datetime)):
                return False
            
            if isinstance(compare_value, str):
                try:
                    compare_date = datetime.fromisoformat(compare_value.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    return False
            else:
                compare_date = compare_value
            
            # Get days from condition_value (if it's a number)
            days = condition_value if isinstance(condition_value, (int, float)) else 0
            
            # Calculate target date based on day_type
            if day_type == "banking":
                target_date = self.add_banking_days(compare_date, int(days))
            else:
                # Default to calendar days
                target_date = self.add_calendar_days(compare_date, int(days))
            
            # Check if field_date is within the window
            return compare_date <= field_date <= target_date
        
        elif operator == "before":
            if not isinstance(field_value, (str, datetime)):
                return False
            
            if isinstance(field_value, str):
                try:
                    field_date = datetime.fromisoformat(field_value.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    return False
            else:
                field_date = field_value
            
            if isinstance(compare_value, str):
                try:
                    compare_date = datetime.fromisoformat(compare_value.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    return False
            else:
                compare_date = compare_value
            
            return field_date < compare_date
        
        elif operator == "after":
            if not isinstance(field_value, (str, datetime)):
                return False
            
            if isinstance(field_value, str):
                try:
                    field_date = datetime.fromisoformat(field_value.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    return False
            else:
                field_date = field_value
            
            if isinstance(compare_value, str):
                try:
                    compare_date = datetime.fromisoformat(compare_value.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    return False
            else:
                compare_date = compare_value
            
            return field_date > compare_date
        
        elif operator == "exists":
            return field_value is not None
        
        elif operator == "not_exists":
            return field_value is None
        
        elif operator == "is_empty":
            if isinstance(field_value, str):
                return len(field_value.strip()) == 0
            elif isinstance(field_value, list):
                return len(field_value) == 0
            return field_value is None
        
        elif operator == "is_not_empty":
            if isinstance(field_value, str):
                return len(field_value.strip()) > 0
            elif isinstance(field_value, list):
                return len(field_value) > 0
            return field_value is not None
        
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False
    
    def evaluate_condition(
        self,
        condition: Dict[str, Any],
        context: Dict[str, Any],
        *,
        rule_id: Optional[str] = None,
        condition_index: Optional[int] = None,
        condition_type: str = "condition"
    ) -> bool:
        """
        Evaluate a single condition against context.
        
        Args:
            condition: Condition dict with field, operator, value/value_ref, etc.
            context: Document context for field resolution
        """
        normalized = self._normalize_condition(condition)
        if not normalized:
            logger.warning(
                "Invalid condition (rule=%s, idx=%s, type=%s, payload=%s): missing field or operator",
                rule_id or "unknown",
                condition_index,
                condition_type,
                condition,
            )
            return False
        
        field_path = normalized["field"]
        operator = normalized["operator"]
        value = normalized.get("value")
        value_ref = normalized.get("value_ref")
        day_type = normalized.get("day_type")
        
        # Resolve field value
        field_value = self.resolve_field_path(context, field_path)
        
        # Evaluate operator
        return self.evaluate_operator(
            operator=operator,
            field_value=field_value,
            condition_value=value,
            value_ref=value_ref,
            context=context,
            day_type=day_type,
            field_path=field_path
        )
    
    def _normalize_condition(self, condition: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalize various condition schemas into the core evaluator schema.
        """
        cond = dict(condition)
        field_path = cond.get("field") or cond.get("path") or cond.get("left_path")
        operator = cond.get("operator")
        value = cond.get("value")
        value_ref = cond.get("value_ref")
        cond_type = cond.get("type")
        day_type = cond.get("day_type")
        
        def is_field_path(candidate: Any) -> bool:
            return isinstance(candidate, str) and "." in candidate and " " not in candidate
        
        if cond_type == "enum_value":
            field_path = field_path or cond.get("path")
            operator = operator or ("not_in" if cond.get("disallowed_values") else "in")
            if operator == "in":
                value = cond.get("allowed_values") or []
            else:
                value = cond.get("disallowed_values") or []
        
        elif cond_type == "field_presence":
            field_path = field_path or cond.get("path")
            operator = operator or ("not_exists" if cond.get("required") is False else "exists")
        
        elif cond_type == "doc_required":
            field_path = field_path or cond.get("path")
            disallowed_terms = cond.get("disallowed_terms")
            if disallowed_terms:
                operator = "not_contains_any"
                value = disallowed_terms
            else:
                operator = operator or "exists"
        
        elif cond_type == "equality_match":
            field_path = field_path or cond.get("left_path")
            operator = operator or "equals"
            right_path = cond.get("right_path")
            if value is None:
                if is_field_path(right_path):
                    value_ref = right_path
                else:
                    value = right_path
        
        elif cond_type == "consistency_check":
            field_path = field_path or cond.get("left_path")
            operator = operator or "equals"
            right_path = cond.get("right_path")
            if value is None:
                if is_field_path(right_path):
                    value_ref = right_path
                else:
                    value = right_path
        
        elif cond_type == "date_order":
            field_path = field_path or cond.get("left_path")
            right_path = cond.get("right_path")
            if operator is None:
                operator = "before"
            if value is None and right_path is not None:
                if is_field_path(right_path):
                    value_ref = right_path
                else:
                    value = right_path
        
        elif cond_type == "numeric_range":
            field_path = field_path or cond.get("path")
            operator = "between"
            value = {
                "min": cond.get("min"),
                "max": cond.get("max"),
                "tolerance": cond.get("tolerance"),
                "allow_exceed_credit": cond.get("allow_exceed_credit"),
                "allow_under_credit": cond.get("allow_under_credit"),
                "min_percent": cond.get("min_percent"),
                "max_percent": cond.get("max_percent"),
            }
        
        elif cond_type == "time_constraint":
            field_path = field_path or cond.get("path")
            raw_operator = operator or cond.get("operator")
            if raw_operator in {"within", "within_days", "max_days_after"}:
                operator = "within_days"
            elif raw_operator == "max_days":
                operator = "less_than_or_equal"
            else:
                operator = raw_operator or "less_than_or_equal"
            if value is None:
                value = cond.get("value")
            if value is None and cond.get("days") is not None:
                value = cond.get("days")
        
        if field_path and operator:
            return {
                "field": field_path,
                "operator": operator,
                "value": value,
                "value_ref": value_ref,
                "day_type": day_type,
            }
        return None
    
    def evaluate_rule(
        self,
        rule: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a single rule against context.
        
        Returns:
            {
                "rule_id": "...",
                "passed": bool,
                "violations": [...],
                "message": "..."
            }
        """
        rule_id = rule.get("rule_id", "unknown")
        
        # Check applies_if preconditions
        applies_if = rule.get("applies_if", [])
        if applies_if:
            for precondition in applies_if:
                if not self.evaluate_condition(
                    precondition,
                    context,
                    rule_id=rule_id,
                    condition_index=index,
                    condition_type="applies_if",
                ):
                    # Rule doesn't apply - return as passed (not applicable)
                    return {
                        "rule_id": rule_id,
                        "passed": True,
                        "violations": [],
                        "message": "Rule not applicable (precondition not met)",
                        "not_applicable": True
                    }
        
        # Evaluate all conditions (all must pass)
        conditions = rule.get("conditions", [])
        if not conditions:
            logger.warning(f"Rule {rule_id} has no conditions")
            return {
                "rule_id": rule_id,
                "passed": True,
                "violations": [],
                "message": "No conditions to evaluate"
            }
        
        violations = []
        all_passed = True
        
        missing_fields: List[str] = []
        evaluated_conditions = 0

        for index, condition in enumerate(conditions):
            try:
                passed = self.evaluate_condition(
                    condition,
                    context,
                    rule_id=rule_id,
                    condition_index=index,
                    condition_type="condition",
                )
                evaluated_conditions += 1
            except MissingFieldError as missing_error:
                if missing_error.field:
                    missing_fields.append(missing_error.field)
                else:
                    missing_fields.append(condition.get("field") or "unknown")
                continue

            if not passed:
                all_passed = False
                violations.append({
                    "condition": condition,
                    "field": condition.get("field"),
                    "operator": condition.get("operator"),
                    "message": condition.get("message", f"Condition failed: {condition.get('field')} {condition.get('operator')}")
                })

        if missing_fields and not violations:
            missing_field_list = ", ".join(sorted(set(missing_fields)))
            return {
                "rule_id": rule_id,
                "passed": True,
                "violations": [],
                "message": f"Rule skipped (missing data: {missing_field_list})",
                "severity": rule.get("severity", "info"),
                "title": rule.get("title", rule_id),
                "not_applicable": True,
                "missing_fields": sorted(set(missing_fields)),
            }
        
        # Determine outcome message
        expected_outcome = rule.get("expected_outcome", {})
        if all_passed:
            message = expected_outcome.get("valid", [""])[0] if expected_outcome.get("valid") else "Rule passed"
        else:
            message = expected_outcome.get("invalid", [""])[0] if expected_outcome.get("invalid") else violations[0].get("message", "Rule failed")
        
        return {
            "rule_id": rule_id,
            "passed": all_passed,
            "violations": violations,
            "message": message,
            "severity": rule.get("severity", "warning"),
            "title": rule.get("title", rule_id),
            "not_applicable": False
        }
    
    async def evaluate_rules(
        self,
        rules: List[Dict[str, Any]],
        input_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate multiple rules against input context.
        
        Args:
            rules: List of rule objects
            input_context: Document context (LC, invoice, BL data)
        
        Returns:
            {
                "outcomes": [...],
                "violations": [...],
                "ruleset_version": "...",
                "rules_evaluated": N,
                "rules_passed": M,
                "rules_failed": K
            }
        """
        outcomes = []
        violations = []
        
        for rule in rules:
            try:
                result = self.evaluate_rule(rule, input_context)
                outcomes.append(result)
                
                if not result.get("passed", False) and not result.get("not_applicable", False):
                    violations.append(result)
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.get('rule_id', 'unknown')}: {e}")
                outcomes.append({
                    "rule_id": rule.get("rule_id", "unknown"),
                    "passed": False,
                    "violations": [{"error": str(e)}],
                    "message": f"Evaluation error: {e}"
                })
        
        rules_passed = len([r for r in outcomes if r.get("passed", False)])
        rules_failed = len([r for r in outcomes if not r.get("passed", False) and not r.get("not_applicable", False)])
        
        return {
            "outcomes": outcomes,
            "violations": violations,
            "rules_evaluated": len(rules),
            "rules_passed": rules_passed,
            "rules_failed": rules_failed,
            "rules_not_applicable": len([r for r in outcomes if r.get("not_applicable", False)])
        }

