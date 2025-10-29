"""
SafeRuleValidator: Pipeline guards with comprehensive error handling and safe rule execution.
Provides robust validation with graceful degradation and structured error reporting.
"""

import traceback
import uuid
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Union
import logging
import signal
import time
from contextlib import contextmanager

class ErrorSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    WARNING = "warning"

class RuleExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"

@dataclass
class ValidationError:
    """Structured validation error with unique tracking ID"""
    error_id: str
    rule_id: str
    severity: ErrorSeverity
    message: str
    details: Optional[str] = None
    field_location: Optional[str] = None
    timestamp: Optional[str] = None
    stack_trace: Optional[str] = None
    recovery_action: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

@dataclass
class RuleExecutionResult:
    """Result of rule execution with comprehensive metadata"""
    rule_id: str
    status: RuleExecutionStatus
    execution_time_ms: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[ValidationError] = None
    warnings: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class TimeoutException(Exception):
    """Raised when rule execution exceeds timeout"""
    pass

class SafeRuleValidator:
    """
    Pipeline guard that safely executes compliance rules with comprehensive error handling.
    Prevents silent failures and ensures graceful degradation.
    """

    def __init__(self, logger: Optional[logging.Logger] = None,
                 default_timeout: int = 30,
                 max_retries: int = 2):
        self.logger = logger or logging.getLogger(__name__)
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.execution_history: List[RuleExecutionResult] = []
        self.error_counts: Dict[str, int] = {}

    @contextmanager
    def timeout(self, seconds: int):
        """Context manager for rule execution timeout"""
        def timeout_handler(signum, frame):
            raise TimeoutException(f"Rule execution timed out after {seconds} seconds")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    def generate_error_id(self, rule_id: str) -> str:
        """Generate unique error ID for tracking"""
        error_count = self.error_counts.get(rule_id, 0) + 1
        self.error_counts[rule_id] = error_count
        timestamp = int(time.time())
        return f"ERR-{rule_id}-{timestamp}-{error_count:03d}"

    def validate_input(self, lc_document: Dict[str, Any]) -> List[ValidationError]:
        """Validate basic input structure and types"""
        errors = []

        if not isinstance(lc_document, dict):
            errors.append(ValidationError(
                error_id=self.generate_error_id("VAL-001"),
                rule_id="INPUT-VALIDATION",
                severity=ErrorSeverity.CRITICAL,
                message="LC document must be a dictionary",
                details=f"Received type: {type(lc_document).__name__}",
                recovery_action="Provide valid LC document structure"
            ))
            return errors

        # Check for required top-level fields
        required_fields = ['lc_number', 'amount', 'applicant', 'beneficiary']
        for field in required_fields:
            if field not in lc_document:
                errors.append(ValidationError(
                    error_id=self.generate_error_id("VAL-002"),
                    rule_id="INPUT-VALIDATION",
                    severity=ErrorSeverity.HIGH,
                    message=f"Missing required field: {field}",
                    field_location=field,
                    recovery_action=f"Add {field} to LC document"
                ))
            elif lc_document[field] is None:
                errors.append(ValidationError(
                    error_id=self.generate_error_id("VAL-003"),
                    rule_id="INPUT-VALIDATION",
                    severity=ErrorSeverity.HIGH,
                    message=f"Required field is null: {field}",
                    field_location=field,
                    recovery_action=f"Provide valid value for {field}"
                ))

        return errors

    def safe_apply_rule(self, rule_func: Callable, rule_id: str, lc_document: Dict[str, Any],
                       timeout: Optional[int] = None, retry_count: int = 0, **kwargs) -> RuleExecutionResult:
        """
        Safely execute a compliance rule with comprehensive error handling.

        Args:
            rule_func: The rule function to execute
            rule_id: Unique identifier for the rule
            lc_document: The LC document to validate
            timeout: Execution timeout in seconds (default: self.default_timeout)
            retry_count: Current retry attempt
            **kwargs: Additional arguments for the rule function

        Returns:
            RuleExecutionResult with execution details and any errors
        """
        start_time = time.time()
        timeout = timeout or self.default_timeout

        try:
            # Input validation
            input_errors = self.validate_input(lc_document)
            if input_errors:
                critical_input_errors = [e for e in input_errors if e.severity == ErrorSeverity.CRITICAL]
                if critical_input_errors:
                    return RuleExecutionResult(
                        rule_id=rule_id,
                        status=RuleExecutionStatus.ERROR,
                        execution_time_ms=(time.time() - start_time) * 1000,
                        error=critical_input_errors[0]
                    )

            # Execute rule with timeout
            with self.timeout(timeout):
                self.logger.info(f"Executing rule {rule_id} (attempt {retry_count + 1})")

                # Call the rule function
                result = rule_func(lc_document, **kwargs)

                execution_time = (time.time() - start_time) * 1000

                # Validate rule result structure
                if not isinstance(result, dict):
                    raise ValueError(f"Rule {rule_id} must return a dictionary, got {type(result)}")

                execution_result = RuleExecutionResult(
                    rule_id=rule_id,
                    status=RuleExecutionStatus.SUCCESS,
                    execution_time_ms=execution_time,
                    result=result,
                    warnings=[e.message for e in input_errors if e.severity == ErrorSeverity.WARNING],
                    metadata={
                        'retry_count': retry_count,
                        'input_validation_errors': len(input_errors)
                    }
                )

                self.logger.info(f"Rule {rule_id} executed successfully in {execution_time:.2f}ms")
                return execution_result

        except TimeoutException as e:
            execution_time = (time.time() - start_time) * 1000
            error = ValidationError(
                error_id=self.generate_error_id(rule_id),
                rule_id=rule_id,
                severity=ErrorSeverity.HIGH,
                message=f"Rule execution timeout: {str(e)}",
                details=f"Rule {rule_id} exceeded {timeout}s timeout",
                recovery_action="Consider increasing timeout or optimizing rule performance"
            )

            self.logger.error(f"Rule {rule_id} timed out after {timeout}s", exc_info=True)

            return RuleExecutionResult(
                rule_id=rule_id,
                status=RuleExecutionStatus.TIMEOUT,
                execution_time_ms=execution_time,
                error=error,
                metadata={'timeout_seconds': timeout, 'retry_count': retry_count}
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000

            # Determine if we should retry
            if retry_count < self.max_retries and self._is_retryable_error(e):
                self.logger.warning(f"Rule {rule_id} failed (attempt {retry_count + 1}), retrying: {str(e)}")
                time.sleep(0.5 * (retry_count + 1))  # Exponential backoff
                return self.safe_apply_rule(rule_func, rule_id, lc_document, timeout, retry_count + 1, **kwargs)

            # Create error with full context
            error = ValidationError(
                error_id=self.generate_error_id(rule_id),
                rule_id=rule_id,
                severity=self._determine_error_severity(e),
                message=f"Rule execution failed: {str(e)}",
                details=f"Exception type: {type(e).__name__}",
                stack_trace=traceback.format_exc(),
                recovery_action=self._get_recovery_action(e, rule_id)
            )

            self.logger.error(f"Rule {rule_id} failed after {retry_count + 1} attempts: {str(e)}", exc_info=True)

            return RuleExecutionResult(
                rule_id=rule_id,
                status=RuleExecutionStatus.ERROR,
                execution_time_ms=execution_time,
                error=error,
                metadata={'retry_count': retry_count, 'exception_type': type(e).__name__}
            )

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is worth retrying"""
        retryable_types = (ConnectionError, TimeoutError, OSError)
        return isinstance(error, retryable_types)

    def _determine_error_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity based on exception type"""
        if isinstance(error, (KeyError, AttributeError)):
            return ErrorSeverity.HIGH
        elif isinstance(error, (ValueError, TypeError)):
            return ErrorSeverity.MEDIUM
        elif isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorSeverity.LOW
        else:
            return ErrorSeverity.CRITICAL

    def _get_recovery_action(self, error: Exception, rule_id: str) -> str:
        """Suggest recovery action based on error type"""
        if isinstance(error, KeyError):
            return f"Check if required fields are present in LC document for rule {rule_id}"
        elif isinstance(error, ValueError):
            return f"Verify data types and formats for rule {rule_id}"
        elif isinstance(error, AttributeError):
            return f"Check method/attribute availability for rule {rule_id}"
        elif isinstance(error, ConnectionError):
            return f"Check network connectivity and retry rule {rule_id}"
        else:
            return f"Review rule {rule_id} implementation and input data"

    def safe_validate_document(self, lc_document: Dict[str, Any],
                             rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Safely validate an LC document against multiple rules with comprehensive error handling.

        Args:
            lc_document: The LC document to validate
            rules: List of rule dictionaries with 'func', 'rule_id', and optional 'timeout', 'kwargs'

        Returns:
            Comprehensive validation result with compliance score and error summary
        """
        validation_start = time.time()
        results = []
        all_errors = []
        all_warnings = []

        self.logger.info(f"Starting validation of LC {lc_document.get('lc_number', 'unknown')} with {len(rules)} rules")

        # Execute all rules safely
        for rule_config in rules:
            rule_func = rule_config['func']
            rule_id = rule_config['rule_id']
            rule_timeout = rule_config.get('timeout')
            rule_kwargs = rule_config.get('kwargs', {})

            result = self.safe_apply_rule(rule_func, rule_id, lc_document, rule_timeout, **rule_kwargs)
            results.append(result)
            self.execution_history.append(result)

            # Collect errors and warnings
            if result.error:
                all_errors.append(result.error)
            if result.warnings:
                all_warnings.extend(result.warnings)

        # Calculate compliance metrics
        total_rules = len(rules)
        successful_rules = len([r for r in results if r.status == RuleExecutionStatus.SUCCESS])
        failed_rules = len([r for r in results if r.status in [RuleExecutionStatus.FAILED, RuleExecutionStatus.ERROR]])
        timeout_rules = len([r for r in results if r.status == RuleExecutionStatus.TIMEOUT])

        compliance_score = successful_rules / total_rules if total_rules > 0 else 0.0

        # Categorize errors by severity
        critical_errors = [e for e in all_errors if e.severity == ErrorSeverity.CRITICAL]
        high_errors = [e for e in all_errors if e.severity == ErrorSeverity.HIGH]
        medium_errors = [e for e in all_errors if e.severity == ErrorSeverity.MEDIUM]
        low_errors = [e for e in all_errors if e.severity == ErrorSeverity.LOW]

        # Determine overall status
        if critical_errors:
            overall_status = "critical_failure"
        elif high_errors:
            overall_status = "non_compliant"
        elif medium_errors or failed_rules > 0:
            overall_status = "discrepant"
        elif timeout_rules > 0:
            overall_status = "partially_validated"
        else:
            overall_status = "compliant"

        validation_time = (time.time() - validation_start) * 1000

        # Build comprehensive result
        validation_result = {
            "compliance_score": round(compliance_score, 3),
            "overall_status": overall_status,
            "validation_summary": {
                "total_rules_checked": total_rules,
                "passed": successful_rules,
                "failed": failed_rules,
                "timeout": timeout_rules,
                "warnings": len(all_warnings),
                "total_validation_time_ms": round(validation_time, 2)
            },
            "error_summary": {
                "critical_errors": len(critical_errors),
                "high_priority_errors": len(high_errors),
                "medium_priority_errors": len(medium_errors),
                "low_priority_errors": len(low_errors),
                "total_errors": len(all_errors),
                "error_categories": list(set([e.rule_id.split('-')[0] for e in all_errors if '-' in e.rule_id])),
                "system_behavior": "graceful_degradation" if len(all_errors) > 0 else "normal_operation",
                "recovery_actions": ["input_sanitization", "error_reporting", "safe_fallback"]
            },
            "rule_execution_details": [
                {
                    "rule_id": r.rule_id,
                    "status": r.status.value,
                    "execution_time_ms": round(r.execution_time_ms, 2),
                    "error_id": r.error.error_id if r.error else None,
                    "warnings_count": len(r.warnings) if r.warnings else 0
                }
                for r in results
            ]
        }

        # Add critical failures for detailed reporting
        if critical_errors:
            validation_result["critical_failures"] = [
                {
                    "rule_id": e.rule_id,
                    "error_id": e.error_id,
                    "description": e.message,
                    "severity": e.severity.value,
                    "field_location": e.field_location,
                    "suggested_fix": e.recovery_action,
                    "timestamp": e.timestamp
                }
                for e in critical_errors[:5]  # Limit to first 5 for readability
            ]

        # Add input validation errors if any
        if all_errors:
            input_validation_errors = [e for e in all_errors if e.rule_id == "INPUT-VALIDATION"]
            if input_validation_errors:
                validation_result["input_errors"] = [
                    {
                        "field": e.field_location,
                        "error": e.message,
                        "error_code": e.error_id
                    }
                    for e in input_validation_errors
                ]

        self.logger.info(f"Validation completed: {overall_status}, score: {compliance_score:.3f}, {len(all_errors)} errors")

        return validation_result

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics from history"""
        if not self.execution_history:
            return {"message": "No executions recorded"}

        total_executions = len(self.execution_history)
        successful = len([r for r in self.execution_history if r.status == RuleExecutionStatus.SUCCESS])
        failed = len([r for r in self.execution_history if r.status == RuleExecutionStatus.ERROR])
        timeouts = len([r for r in self.execution_history if r.status == RuleExecutionStatus.TIMEOUT])

        avg_execution_time = sum(r.execution_time_ms for r in self.execution_history) / total_executions

        return {
            "total_executions": total_executions,
            "success_rate": round(successful / total_executions, 3),
            "failure_rate": round(failed / total_executions, 3),
            "timeout_rate": round(timeouts / total_executions, 3),
            "average_execution_time_ms": round(avg_execution_time, 2),
            "total_unique_errors": len(self.error_counts)
        }

    def reset_history(self):
        """Reset execution history and error counts"""
        self.execution_history.clear()
        self.error_counts.clear()
        self.logger.info("Execution history and error counts reset")