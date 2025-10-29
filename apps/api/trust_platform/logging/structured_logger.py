"""
Structured JSON logging system for LCopilot Trust Platform.
Provides comprehensive logging with structured data, error tracking, and CloudWatch integration.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
import boto3
from pathlib import Path
import sys

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class EventType(Enum):
    VALIDATION_START = "validation_start"
    VALIDATION_COMPLETE = "validation_complete"
    RULE_EXECUTION = "rule_execution"
    ERROR_OCCURRED = "error_occurred"
    COMPLIANCE_CHECK = "compliance_check"
    USER_ACTION = "user_action"
    SYSTEM_HEALTH = "system_health"
    PERFORMANCE_METRIC = "performance_metric"
    SECURITY_EVENT = "security_event"
    BUSINESS_EVENT = "business_event"

@dataclass
class LogContext:
    """Context information for structured logging"""
    request_id: str
    user_id: Optional[str] = None
    customer_id: Optional[str] = None
    session_id: Optional[str] = None
    lc_reference: Optional[str] = None
    document_id: Optional[str] = None
    rule_id: Optional[str] = None
    component: Optional[str] = None
    environment: str = "production"
    version: str = "2.1.0"

@dataclass
class PerformanceData:
    """Performance metrics for logging"""
    execution_time_ms: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    queue_size: Optional[int] = None
    concurrent_requests: Optional[int] = None

@dataclass
class ErrorData:
    """Structured error information"""
    error_id: str
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    recovery_action: Optional[str] = None
    severity: str = "medium"
    component: Optional[str] = None
    user_impact: Optional[str] = None

@dataclass
class ValidationData:
    """Validation-specific logging data"""
    validation_id: str
    compliance_score: Optional[float] = None
    rules_checked: Optional[int] = None
    rules_passed: Optional[int] = None
    rules_failed: Optional[int] = None
    critical_errors: Optional[int] = None
    processing_time_ms: Optional[float] = None
    overall_status: Optional[str] = None

@dataclass
class BusinessData:
    """Business event logging data"""
    event_name: str
    revenue_impact: Optional[float] = None
    customer_tier: Optional[str] = None
    feature_used: Optional[str] = None
    conversion_funnel_stage: Optional[str] = None
    subscription_status: Optional[str] = None

class StructuredLogger:
    """
    Structured JSON logger with CloudWatch integration and comprehensive event tracking.
    Provides consistent logging format across the LCopilot Trust Platform.
    """

    def __init__(self,
                 logger_name: str = "lcop_trust_platform",
                 environment: str = "production",
                 enable_cloudwatch: bool = True,
                 enable_console: bool = True):

        self.logger_name = logger_name
        self.environment = environment
        self.enable_cloudwatch = enable_cloudwatch
        self.enable_console = enable_console

        # Setup base logger
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Setup structured JSON formatter
        self.json_formatter = self._create_json_formatter()

        # Setup console handler if enabled
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(self.json_formatter)
            self.logger.addHandler(console_handler)

        # Setup CloudWatch handler if enabled
        if enable_cloudwatch:
            try:
                self.cloudwatch_logs = boto3.client('logs')
                self.log_group_name = f'/lcop-trust-platform/{environment}'
                self.log_stream_name = f'{logger_name}-{datetime.now().strftime("%Y-%m-%d")}'
                self._ensure_cloudwatch_setup()
            except Exception as e:
                self.logger.warning(f"CloudWatch logging setup failed: {str(e)}")
                self.enable_cloudwatch = False

    def _create_json_formatter(self):
        """Create JSON formatter for structured logging"""
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                # Build base log entry
                log_entry = {
                    'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                }

                # Add structured data if present
                if hasattr(record, 'structured_data'):
                    log_entry['data'] = record.structured_data

                # Add exception info if present
                if record.exc_info:
                    log_entry['exception'] = {
                        'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                        'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                        'traceback': traceback.format_exception(*record.exc_info)
                    }

                return json.dumps(log_entry, default=str)

        return JSONFormatter()

    def _ensure_cloudwatch_setup(self):
        """Ensure CloudWatch log group and stream exist"""
        try:
            # Create log group if it doesn't exist
            try:
                self.cloudwatch_logs.create_log_group(
                    logGroupName=self.log_group_name
                )
            except self.cloudwatch_logs.exceptions.ResourceAlreadyExistsException:
                pass  # Log group already exists

            # Create log stream if it doesn't exist
            try:
                self.cloudwatch_logs.create_log_stream(
                    logGroupName=self.log_group_name,
                    logStreamName=self.log_stream_name
                )
            except self.cloudwatch_logs.exceptions.ResourceAlreadyExistsException:
                pass  # Log stream already exists

        except Exception as e:
            self.logger.warning(f"CloudWatch setup failed: {str(e)}")

    def _log_with_structure(self,
                           level: LogLevel,
                           message: str,
                           event_type: EventType,
                           context: Optional[LogContext] = None,
                           performance: Optional[PerformanceData] = None,
                           error: Optional[ErrorData] = None,
                           validation: Optional[ValidationData] = None,
                           business: Optional[BusinessData] = None,
                           extra_data: Optional[Dict[str, Any]] = None):
        """Core structured logging method"""

        # Build structured data
        structured_data = {
            'event_type': event_type.value,
            'environment': self.environment,
            'timestamp_utc': datetime.utcnow().isoformat(),
        }

        # Add context data
        if context:
            structured_data['context'] = asdict(context)

        # Add performance data
        if performance:
            structured_data['performance'] = asdict(performance)

        # Add error data
        if error:
            structured_data['error'] = asdict(error)

        # Add validation data
        if validation:
            structured_data['validation'] = asdict(validation)

        # Add business data
        if business:
            structured_data['business'] = asdict(business)

        # Add extra data
        if extra_data:
            structured_data['extra'] = extra_data

        # Create log record with structured data
        log_record = logging.LogRecord(
            name=self.logger.name,
            level=getattr(logging, level.value),
            pathname='',
            lineno=0,
            msg=message,
            args=(),
            exc_info=None
        )
        log_record.structured_data = structured_data

        # Log the record
        self.logger.handle(log_record)

        # Send to CloudWatch if enabled
        if self.enable_cloudwatch:
            self._send_to_cloudwatch(log_record)

    def _send_to_cloudwatch(self, log_record):
        """Send log record to CloudWatch"""
        try:
            log_events = [{
                'timestamp': int(log_record.created * 1000),
                'message': self.json_formatter.format(log_record)
            }]

            self.cloudwatch_logs.put_log_events(
                logGroupName=self.log_group_name,
                logStreamName=self.log_stream_name,
                logEvents=log_events
            )
        except Exception as e:
            # Fallback to console logging if CloudWatch fails
            print(f"CloudWatch logging failed: {str(e)}")

    # Convenience methods for different log levels
    def debug(self, message: str, event_type: EventType = EventType.SYSTEM_HEALTH, **kwargs):
        """Log debug message"""
        self._log_with_structure(LogLevel.DEBUG, message, event_type, **kwargs)

    def info(self, message: str, event_type: EventType = EventType.SYSTEM_HEALTH, **kwargs):
        """Log info message"""
        self._log_with_structure(LogLevel.INFO, message, event_type, **kwargs)

    def warning(self, message: str, event_type: EventType = EventType.ERROR_OCCURRED, **kwargs):
        """Log warning message"""
        self._log_with_structure(LogLevel.WARNING, message, event_type, **kwargs)

    def error(self, message: str, event_type: EventType = EventType.ERROR_OCCURRED, **kwargs):
        """Log error message"""
        self._log_with_structure(LogLevel.ERROR, message, event_type, **kwargs)

    def critical(self, message: str, event_type: EventType = EventType.ERROR_OCCURRED, **kwargs):
        """Log critical message"""
        self._log_with_structure(LogLevel.CRITICAL, message, event_type, **kwargs)

    # Specialized logging methods
    def log_validation_start(self,
                            context: LogContext,
                            lc_reference: str,
                            customer_tier: str,
                            rules_to_check: int):
        """Log validation start event"""
        self.info(
            f"Starting LC validation for {lc_reference}",
            event_type=EventType.VALIDATION_START,
            context=context,
            validation=ValidationData(
                validation_id=context.request_id,
                rules_checked=rules_to_check
            ),
            business=BusinessData(
                event_name="validation_started",
                customer_tier=customer_tier
            )
        )

    def log_validation_complete(self,
                               context: LogContext,
                               validation_result: Dict[str, Any],
                               processing_time_ms: float):
        """Log validation completion event"""
        self.info(
            f"Validation completed for {context.lc_reference}",
            event_type=EventType.VALIDATION_COMPLETE,
            context=context,
            validation=ValidationData(
                validation_id=context.request_id,
                compliance_score=validation_result.get('compliance_score'),
                rules_checked=validation_result.get('validation_summary', {}).get('total_rules_checked'),
                rules_passed=validation_result.get('validation_summary', {}).get('passed'),
                rules_failed=validation_result.get('validation_summary', {}).get('failed'),
                critical_errors=validation_result.get('error_summary', {}).get('critical_errors'),
                processing_time_ms=processing_time_ms,
                overall_status=validation_result.get('overall_status')
            ),
            performance=PerformanceData(
                execution_time_ms=processing_time_ms
            )
        )

    def log_rule_execution(self,
                          context: LogContext,
                          rule_id: str,
                          execution_status: str,
                          execution_time_ms: float,
                          error_info: Optional[Dict[str, Any]] = None):
        """Log individual rule execution"""
        message = f"Rule {rule_id} executed: {execution_status}"

        # Create context with rule_id
        rule_context = LogContext(
            **asdict(context),
            rule_id=rule_id
        )

        error_data = None
        if error_info:
            error_data = ErrorData(
                error_id=error_info.get('error_id', 'unknown'),
                error_type=error_info.get('error_type', 'rule_execution_error'),
                error_message=error_info.get('message', 'Rule execution failed'),
                severity=error_info.get('severity', 'medium'),
                component='rule_engine',
                recovery_action=error_info.get('recovery_action')
            )

        level = LogLevel.ERROR if error_info else LogLevel.INFO

        self._log_with_structure(
            level=level,
            message=message,
            event_type=EventType.RULE_EXECUTION,
            context=rule_context,
            performance=PerformanceData(execution_time_ms=execution_time_ms),
            error=error_data
        )

    def log_compliance_check(self,
                           context: LogContext,
                           compliance_type: str,
                           result: str,
                           score: float,
                           violations: List[str] = None):
        """Log compliance check results"""
        self.info(
            f"Compliance check ({compliance_type}): {result}",
            event_type=EventType.COMPLIANCE_CHECK,
            context=context,
            validation=ValidationData(
                validation_id=context.request_id,
                compliance_score=score,
                overall_status=result
            ),
            extra_data={
                'compliance_type': compliance_type,
                'violations': violations or []
            }
        )

    def log_user_action(self,
                       context: LogContext,
                       action: str,
                       feature: str,
                       success: bool = True,
                       additional_data: Optional[Dict[str, Any]] = None):
        """Log user actions and feature usage"""
        self.info(
            f"User action: {action} on {feature}",
            event_type=EventType.USER_ACTION,
            context=context,
            business=BusinessData(
                event_name=action,
                feature_used=feature,
                customer_tier=additional_data.get('customer_tier') if additional_data else None
            ),
            extra_data={
                'success': success,
                'additional_data': additional_data or {}
            }
        )

    def log_performance_metric(self,
                             metric_name: str,
                             metric_value: float,
                             context: Optional[LogContext] = None,
                             additional_metrics: Optional[Dict[str, float]] = None):
        """Log performance metrics"""
        self.info(
            f"Performance metric: {metric_name} = {metric_value}",
            event_type=EventType.PERFORMANCE_METRIC,
            context=context,
            performance=PerformanceData(
                execution_time_ms=metric_value if 'time' in metric_name.lower() else 0
            ),
            extra_data={
                'metric_name': metric_name,
                'metric_value': metric_value,
                'additional_metrics': additional_metrics or {}
            }
        )

    def log_security_event(self,
                          event_name: str,
                          severity: str,
                          context: Optional[LogContext] = None,
                          threat_details: Optional[Dict[str, Any]] = None):
        """Log security-related events"""
        self.warning(
            f"Security event: {event_name}",
            event_type=EventType.SECURITY_EVENT,
            context=context,
            error=ErrorData(
                error_id=str(uuid.uuid4()),
                error_type='security_event',
                error_message=event_name,
                severity=severity,
                component='security_monitor'
            ),
            extra_data={
                'threat_details': threat_details or {},
                'event_name': event_name
            }
        )

    def log_business_event(self,
                          event_name: str,
                          customer_tier: str,
                          revenue_impact: Optional[float] = None,
                          context: Optional[LogContext] = None,
                          event_data: Optional[Dict[str, Any]] = None):
        """Log business-relevant events"""
        self.info(
            f"Business event: {event_name}",
            event_type=EventType.BUSINESS_EVENT,
            context=context,
            business=BusinessData(
                event_name=event_name,
                customer_tier=customer_tier,
                revenue_impact=revenue_impact
            ),
            extra_data=event_data or {}
        )

    def create_context(self,
                      request_id: Optional[str] = None,
                      user_id: Optional[str] = None,
                      customer_id: Optional[str] = None,
                      lc_reference: Optional[str] = None,
                      document_id: Optional[str] = None,
                      component: Optional[str] = None) -> LogContext:
        """Create a logging context for consistent tracking"""
        return LogContext(
            request_id=request_id or str(uuid.uuid4()),
            user_id=user_id,
            customer_id=customer_id,
            lc_reference=lc_reference,
            document_id=document_id,
            component=component,
            environment=self.environment
        )

# Global logger instance for easy import
trust_logger = StructuredLogger(
    logger_name="lcop_trust_platform",
    environment="production",
    enable_cloudwatch=True,
    enable_console=True
)

def get_logger(name: str = "lcop_trust_platform", environment: str = "production") -> StructuredLogger:
    """Get or create a structured logger instance"""
    return StructuredLogger(
        logger_name=name,
        environment=environment,
        enable_cloudwatch=True,
        enable_console=True
    )