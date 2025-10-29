"""
Debug routes for testing monitoring and logging system.
"""

from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone

from ..middleware.logging import get_request_logger


router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/error")
async def trigger_error(request: Request):
    """
    Deliberately trigger a single error for CloudWatch metric filter testing.

    This endpoint:
    1. Logs an ERROR level message for CloudWatch metric filters
    2. Raises a 500 HTTP exception
    3. Allows testing of error monitoring and alerting
    """

    # Get logger with request context
    logger = get_request_logger(request, "debug")

    # Log the error with structured data for CloudWatch metric filters
    logger.error(
        "Simulated error for CloudWatch test",
        extra={"level": "ERROR"},
        error_type="simulated_error",
        endpoint="/debug/error",
        trigger_reason="single_error_test"
    )

    # Raise HTTP exception to return 500 status
    raise HTTPException(
        status_code=500,
        detail="Simulated error"
    )


@router.get("/spam-errors")
async def spam_errors(request: Request, count: int = 5):
    """
    Generate multiple errors to trigger CloudWatch alarm testing.

    This endpoint:
    1. Logs multiple ERROR level messages in rapid succession
    2. Designed to trigger CloudWatch alarms (≥5 errors triggers alarm)
    3. Useful for testing alarm notifications and SNS integration

    Args:
        count: Number of errors to generate (default: 5, enough to trigger alarm)
    """

    # Get logger with request context
    logger = get_request_logger(request, "debug")

    # Validate count parameter
    if count < 1:
        count = 1
    elif count > 20:  # Limit to prevent excessive logging
        count = 20

    logger.info(
        f"Starting spam error test - generating {count} errors",
        endpoint="/debug/spam-errors",
        error_count=count,
        purpose="cloudwatch_alarm_testing"
    )

    # Generate multiple error logs in rapid succession
    for i in range(count):
        logger.error(
            f"Spam error {i+1} for CloudWatch alarm test",
            extra={"level": "ERROR"},
            error_sequence=i+1,
            total_errors=count,
            endpoint="/debug/spam-errors",
            error_type="spam_test_error",
            alarm_trigger_expected=count >= 5
        )

    logger.info(
        f"Spam error test completed - generated {count} errors",
        endpoint="/debug/spam-errors",
        error_count=count,
        alarm_should_trigger=count >= 5,
        note="Check CloudWatch alarm 'LCopilot-HighErrorRate' in 1-2 minutes"
    )

    # Raise HTTP exception to return 500 status
    raise HTTPException(
        status_code=500,
        detail=f"Generated {count} errors for testing"
    )


@router.get("/warning")
async def simulate_warning(request: Request):
    """
    Generate a warning log for testing warning-level monitoring.

    This endpoint:
    1. Logs a WARNING level message for CloudWatch metric filters
    2. Returns successfully (200 status)
    3. Useful for tracking warning-level events separate from errors
    """

    logger = get_request_logger(request, "debug")

    logger.warning(
        "Simulated warning for CloudWatch test",
        extra={"level": "WARNING"},
        warning_type="simulated_warning",
        endpoint="/debug/warning",
        severity="warning",
        trigger_reason="warning_level_test"
    )

    return {
        "status": "warning_logged",
        "message": "Warning log generated successfully",
        "level": "WARNING",
        "endpoint": "/debug/warning",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "note": "Check CloudWatch for WARNING level logs"
    }


@router.get("/critical")
async def simulate_critical(request: Request):
    """
    Generate a critical error log for testing critical error monitoring.

    This endpoint logs a critical error and raises a 500 exception.
    """

    logger = get_request_logger(request, "debug")

    logger.critical(
        "Simulated critical error for CloudWatch test",
        error_type="simulated_critical_error",
        endpoint="/debug/critical",
        severity="critical",
        timestamp=datetime.now(timezone.utc).isoformat(),
        impact="high",
        requires_immediate_attention=True
    )

    raise HTTPException(
        status_code=500,
        detail="Simulated critical error"
    )


@router.get("/slow")
async def simulate_slow_request(request: Request):
    """
    Simulate a slow request for testing slow request monitoring.

    This endpoint introduces a delay to trigger slow request metrics.
    """
    import asyncio

    logger = get_request_logger(request, "debug")

    logger.info(
        "Starting slow request simulation",
        endpoint="/debug/slow",
        expected_duration_seconds=6
    )

    # Simulate slow processing (6 seconds to exceed the 5-second threshold)
    await asyncio.sleep(6)

    logger.info(
        "Slow request completed",
        endpoint="/debug/slow",
        actual_duration_seconds=6
    )

    return {
        "status": "slow_request_completed",
        "message": "Request took 6 seconds to complete",
        "duration_seconds": 6,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/5xx-series")
async def simulate_5xx_errors(request: Request):
    """
    Generate multiple 5xx errors for testing error rate monitoring.

    This endpoint simulates different types of 5xx errors.
    """
    import random

    logger = get_request_logger(request, "debug")

    # Randomly select a 5xx error type
    error_types = [
        (500, "Internal Server Error"),
        (502, "Bad Gateway"),
        (503, "Service Unavailable"),
        (504, "Gateway Timeout")
    ]

    status_code, error_message = random.choice(error_types)

    logger.error(
        f"Simulated {status_code} error for 5xx monitoring",
        error_type=f"simulated_{status_code}_error",
        endpoint="/debug/5xx-series",
        http_status_code=status_code,
        error_message=error_message,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

    raise HTTPException(
        status_code=status_code,
        detail=error_message
    )


@router.get("/test-metrics")
async def test_all_metrics(request: Request):
    """
    Test all monitoring metrics in sequence.

    This endpoint can be used to trigger all metric filters for comprehensive testing.
    """

    logger = get_request_logger(request, "debug")

    logger.info(
        "Starting comprehensive metrics test",
        endpoint="/debug/test-metrics",
        test_scope="all_metric_filters"
    )

    # Log different severity levels
    logger.warning("Test warning message for metric testing")
    logger.error("Test error message for metric testing")
    logger.critical("Test critical message for metric testing")

    # Log a simulated slow request
    logger.info(
        "Simulated slow request log",
        request_duration_ms=6500,  # Over 5000ms threshold
        endpoint="/debug/test-metrics"
    )

    # Log a 5xx error
    logger.error(
        "Test 5xx error log",
        http_status_code=500,
        endpoint="/debug/test-metrics"
    )

    logger.info(
        "Comprehensive metrics test completed",
        metrics_triggered=[
            "LCopilotErrorCount",
            "LCopilotCriticalErrorCount",
            "LCopilot5xxErrorCount",
            "LCopilotSlowRequestCount"
        ]
    )

    return {
        "status": "metrics_test_completed",
        "message": "All metric filters should have been triggered",
        "metrics_triggered": [
            "LCopilotErrorCount",
            "LCopilotCriticalErrorCount",
            "LCopilot5xxErrorCount",
            "LCopilotSlowRequestCount"
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "note": "Check CloudWatch metrics in 1-2 minutes"
    }


@router.get("/info")
async def debug_info(request: Request):
    """
    Get debug information about the monitoring system.

    This endpoint provides information about available debug routes and monitoring setup.
    """

    logger = get_request_logger(request, "debug")

    logger.info(
        "Debug info requested",
        endpoint="/debug/info"
    )

    return {
        "debug_routes": {
            "/debug/error": "Trigger ERROR level log + 500 exception",
            "/debug/warning": "Trigger WARNING level log (returns 200)",
            "/debug/critical": "Trigger CRITICAL level log + 500 exception",
            "/debug/slow": "Simulate slow request (6 seconds)",
            "/debug/5xx-series": "Random 5xx errors (500, 502, 503, 504)",
            "/debug/test-metrics": "Trigger all metric filters at once",
            "/debug/info": "This endpoint - debug information"
        },
        "cloudwatch_metrics": {
            "LCopilotErrorCount": "Triggered by ERROR level logs",
            "LCopilotCriticalErrorCount": "Triggered by CRITICAL level logs",
            "LCopilot5xxErrorCount": "Triggered by http_status_code >= 500",
            "LCopilotSlowRequestCount": "Triggered by request_duration_ms > 5000"
        },
        "usage_instructions": {
            "single_test": "Call individual endpoints like /debug/error",
            "comprehensive_test": "Call /debug/test-metrics to trigger all filters",
            "monitoring": "Check CloudWatch metrics 1-2 minutes after calling endpoints",
            "alarms": "Sustained error rates will trigger CloudWatch alarms"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }