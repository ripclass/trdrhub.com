"""
Production-grade structured logging with CloudWatch integration.
"""

import os
import sys
import socket
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone

import structlog
from structlog.typing import FilteringBoundLogger

# Import CloudWatch handler with fallback
try:
    from watchtower import CloudWatchLogHandler
    CLOUDWATCH_AVAILABLE = True
except ImportError:
    CLOUDWATCH_AVAILABLE = False
    CloudWatchLogHandler = None


class LCopilotLogger:
    """
    Centralized logger configuration for LCopilot API.

    Features:
    - Structured JSON logging
    - CloudWatch integration for production
    - Request ID injection
    - ISO 8601 timestamps
    """

    def __init__(self):
        self.service_name = "lcopilot-api"
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.debug_mode = os.getenv("DEBUG", "true").lower() == "true"

        # Try to get AWS region from settings first, then environment
        try:
            from app.config import settings
            self.aws_region = settings.AWS_REGION
        except ImportError:
            self.aws_region = os.getenv("AWS_REGION", "us-east-1")

        # Get hostname for log stream naming
        self.hostname = socket.gethostname()

        # Configure structlog
        self._configure_structlog()

        # Get the configured logger
        self.logger = structlog.get_logger(self.service_name)

    def _configure_structlog(self):
        """Configure structlog with JSON output and CloudWatch integration."""

        # Common processors for all environments
        processors = [
            # Add timestamp in ISO format
            structlog.processors.TimeStamper(fmt="iso", utc=True),

            # Add log level
            structlog.stdlib.add_log_level,

            # Add service name and environment
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),

            # Add static context
            self._add_static_context,

            # Format as JSON for production, colorized for development
            self._get_final_processor(),
        ]

        # Configure structlog
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Configure standard library logging
        self._configure_stdlib_logging()

    def _add_static_context(self, logger, method_name, event_dict):
        """Add static context to all log entries."""
        event_dict["service"] = self.service_name
        event_dict["environment"] = self.environment
        event_dict["hostname"] = self.hostname

        # Add version if available
        event_dict["version"] = os.getenv("APP_VERSION", "unknown")

        return event_dict

    def _get_final_processor(self):
        """Get the final processor based on environment."""
        if self.environment == "production":
            # JSON output for production
            return structlog.processors.JSONRenderer()
        else:
            # Colorized output for development
            return structlog.dev.ConsoleRenderer(colors=True)

    def _configure_stdlib_logging(self):
        """Configure standard library logging with CloudWatch handler."""

        # Create root logger
        root_logger = logging.getLogger()
        root_logger.handlers.clear()  # Clear existing handlers

        # Set log level
        if self.debug_mode:
            root_logger.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.INFO)

        # Console handler (always present)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)

        # Use JSON formatter for console in production
        if self.environment == "production":
            console_formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "' +
                self.service_name + '", "environment": "' + self.environment +
                '", "hostname": "' + self.hostname + '", "message": "%(message)s", "module": "%(name)s"}'
            )
        else:
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # CloudWatch handler for production
        if self.environment == "production" and CLOUDWATCH_AVAILABLE:
            try:
                cloudwatch_handler = self._create_cloudwatch_handler()
                if cloudwatch_handler:
                    root_logger.addHandler(cloudwatch_handler)
                    print(f"✅ CloudWatch handler added - logs will stream to lcopilot-backend/{self.hostname}-{self.environment}", file=sys.stderr)
            except Exception as e:
                # Don't fail startup if CloudWatch is unavailable
                print(f"Warning: CloudWatch logging failed to initialize: {str(e)}", file=sys.stderr)

        # Silence noisy third-party loggers
        logging.getLogger("boto3").setLevel(logging.WARNING)
        logging.getLogger("botocore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("watchtower").setLevel(logging.WARNING)

    def _create_cloudwatch_handler(self) -> Optional[Any]:
        """Create CloudWatch log handler if available."""

        if not CLOUDWATCH_AVAILABLE:
            return None

        try:
            import boto3

            # Create boto3 session with proper region configuration
            session = boto3.Session(region_name=self.aws_region)

            # Verify AWS credentials are available
            try:
                session.client('sts').get_caller_identity()
                print(f"✅ AWS credentials verified for CloudWatch logging", file=sys.stderr)
            except Exception as e:
                print(f"❌ AWS credentials not available: {str(e)}", file=sys.stderr)
                return None

            # CloudWatch log configuration
            log_group = "lcopilot-backend"
            log_stream = f"{self.hostname}-{self.environment}"

            handler = CloudWatchLogHandler(
                log_group_name=log_group,
                log_stream_name=log_stream,
                use_queues=True,  # Use background queues for better performance
                send_interval=5,   # Send logs every 5 seconds for faster testing
                max_batch_size=100,  # Batch up to 100 log entries
                max_batch_count=10,  # Keep up to 10 batches in memory
                create_log_group=False,  # Log group already exists
                create_log_stream=True,   # Create log stream if needed
                boto3_client=session.client('logs'),  # Pass pre-configured client
            )

            # JSON formatter for CloudWatch
            cloudwatch_formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "' +
                self.service_name + '", "environment": "' + self.environment +
                '", "hostname": "' + self.hostname + '", "message": "%(message)s", ' +
                '"module": "%(name)s", "lineno": %(lineno)d}'
            )

            handler.setFormatter(cloudwatch_formatter)
            handler.setLevel(logging.INFO)  # Only send INFO and above to CloudWatch

            return handler

        except Exception as e:
            print(f"Failed to create CloudWatch handler: {str(e)}", file=sys.stderr)
            return None

    def get_logger(self, name: Optional[str] = None) -> FilteringBoundLogger:
        """Get a logger instance with optional name binding."""
        if name:
            return self.logger.bind(logger_name=name)
        return self.logger

    def bind_request_context(self, request_id: str, **kwargs) -> FilteringBoundLogger:
        """Bind request context to logger."""
        context = {"request_id": request_id}
        context.update(kwargs)
        return self.logger.bind(**context)


# Global logger instance
_logger_instance: Optional[LCopilotLogger] = None


def get_logger(name: Optional[str] = None, request_id: Optional[str] = None) -> FilteringBoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Optional logger name for context
        request_id: Optional request ID for request tracking

    Returns:
        Configured structlog logger
    """
    global _logger_instance

    if _logger_instance is None:
        _logger_instance = LCopilotLogger()

    logger = _logger_instance.get_logger(name)

    if request_id:
        logger = logger.bind(request_id=request_id)

    return logger


def configure_logging():
    """Initialize logging configuration. Call this at startup."""
    global _logger_instance
    _logger_instance = LCopilotLogger()
    return _logger_instance.logger


def log_exception(logger: FilteringBoundLogger, exc: Exception, **context):
    """
    Log an exception with full context and stack trace.

    Args:
        logger: The logger instance
        exc: The exception to log
        **context: Additional context to include
    """
    import traceback

    logger.error(
        "Unhandled exception occurred",
        exception_type=exc.__class__.__name__,
        exception_message=str(exc),
        stack_trace=traceback.format_exc(),
        **context
    )


def log_api_request(logger: FilteringBoundLogger, method: str, path: str,
                   status_code: int, duration_ms: float, **context):
    """
    Log API request with standard fields.

    Args:
        logger: The logger instance
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        **context: Additional context
    """
    level = "error" if status_code >= 500 else "warning" if status_code >= 400 else "info"

    getattr(logger, level)(
        "API request completed",
        http_method=method,
        http_path=path,
        http_status_code=status_code,
        request_duration_ms=round(duration_ms, 2),
        **context
    )


def log_database_operation(logger: FilteringBoundLogger, operation: str,
                          table: str, duration_ms: float, **context):
    """
    Log database operation with performance metrics.

    Args:
        logger: The logger instance
        operation: Database operation (SELECT, INSERT, UPDATE, DELETE)
        table: Table name
        duration_ms: Operation duration in milliseconds
        **context: Additional context
    """
    logger.info(
        "Database operation completed",
        db_operation=operation,
        db_table=table,
        db_duration_ms=round(duration_ms, 2),
        **context
    )


def log_external_service_call(logger: FilteringBoundLogger, service: str,
                             operation: str, success: bool, duration_ms: float, **context):
    """
    Log external service calls (S3, Document AI, etc.).

    Args:
        logger: The logger instance
        service: Service name (s3, documentai, etc.)
        operation: Operation performed
        success: Whether the operation succeeded
        duration_ms: Operation duration in milliseconds
        **context: Additional context
    """
    level = "info" if success else "error"

    getattr(logger, level)(
        "External service call completed",
        external_service=service,
        external_operation=operation,
        external_success=success,
        external_duration_ms=round(duration_ms, 2),
        **context
    )