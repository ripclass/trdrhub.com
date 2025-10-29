"""
Health and readiness endpoints for monitoring and load balancer checks.
"""

import os
import time
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..database import get_db
from ..middleware.logging import get_request_logger
from ..utils.logger import log_external_service_call


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str  # "ok" or "error"
    timestamp: str
    version: str
    environment: str
    uptime_seconds: Optional[int] = None


class ReadinessStatus(BaseModel):
    """Readiness check response model."""
    status: str  # "ok" or "error"
    timestamp: str
    checks: Dict[str, Dict[str, Any]]
    overall_healthy: bool


class HealthChecker:
    """Handles health and readiness checks for LCopilot API."""

    def __init__(self):
        self.start_time = time.time()
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.version = os.getenv("APP_VERSION", "unknown")
        self.use_stubs = os.getenv("USE_STUBS", "false").lower() == "true"

    def get_uptime_seconds(self) -> int:
        """Get application uptime in seconds."""
        return int(time.time() - self.start_time)

    async def check_database(self, db: Session, logger) -> Dict[str, Any]:
        """Check database connectivity and health."""
        start_time = time.time()

        try:
            # Simple query to test connection
            result = db.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()

            duration_ms = (time.time() - start_time) * 1000

            if row and row[0] == 1:
                log_external_service_call(
                    logger,
                    service="postgresql",
                    operation="health_check",
                    success=True,
                    duration_ms=duration_ms
                )

                return {
                    "status": "ok",
                    "response_time_ms": round(duration_ms, 2),
                    "message": "Database connection successful"
                }
            else:
                raise Exception("Unexpected query result")

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            log_external_service_call(
                logger,
                service="postgresql",
                operation="health_check",
                success=False,
                duration_ms=duration_ms,
                error=str(e)
            )

            return {
                "status": "error",
                "response_time_ms": round(duration_ms, 2),
                "message": f"Database check failed: {str(e)}"
            }

    async def check_s3(self, logger) -> Dict[str, Any]:
        """Check S3 bucket accessibility."""
        if self.use_stubs:
            return {
                "status": "ok",
                "message": "S3 check skipped (using stubs)",
                "response_time_ms": 0
            }

        start_time = time.time()

        try:
            import boto3
            from botocore.exceptions import ClientError

            bucket_name = os.getenv("S3_BUCKET_NAME")
            if not bucket_name:
                raise Exception("S3_BUCKET_NAME not configured")

            # Create S3 client
            s3_client = boto3.client('s3')

            # Check if bucket exists and is accessible
            s3_client.head_bucket(Bucket=bucket_name)

            duration_ms = (time.time() - start_time) * 1000

            log_external_service_call(
                logger,
                service="s3",
                operation="health_check",
                success=True,
                duration_ms=duration_ms,
                bucket=bucket_name
            )

            return {
                "status": "ok",
                "response_time_ms": round(duration_ms, 2),
                "message": f"S3 bucket '{bucket_name}' accessible",
                "bucket": bucket_name
            }

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            log_external_service_call(
                logger,
                service="s3",
                operation="health_check",
                success=False,
                duration_ms=duration_ms,
                error=str(e)
            )

            return {
                "status": "error",
                "response_time_ms": round(duration_ms, 2),
                "message": f"S3 check failed: {str(e)}"
            }

    async def check_document_ai(self, logger) -> Dict[str, Any]:
        """Check Google Cloud Document AI availability."""
        if self.use_stubs:
            return {
                "status": "ok",
                "message": "Document AI check skipped (using stubs)",
                "response_time_ms": 0
            }

        start_time = time.time()

        try:
            from google.cloud import documentai

            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("GOOGLE_DOCUMENTAI_LOCATION", "us")

            if not project_id:
                raise Exception("GOOGLE_CLOUD_PROJECT not configured")

            # Create Document AI client
            client = documentai.DocumentProcessorServiceClient()

            # List processors to test connectivity
            parent = client.common_location_path(project_id, location)

            # Use asyncio timeout for the synchronous call
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, client.list_processors, {"parent": parent}
                ),
                timeout=10.0  # 10 second timeout
            )

            duration_ms = (time.time() - start_time) * 1000

            # Check if we can access processors
            processor_count = len(list(response))

            log_external_service_call(
                logger,
                service="documentai",
                operation="health_check",
                success=True,
                duration_ms=duration_ms,
                processor_count=processor_count
            )

            return {
                "status": "ok",
                "response_time_ms": round(duration_ms, 2),
                "message": f"Document AI accessible ({processor_count} processors found)",
                "project": project_id,
                "location": location
            }

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = "Document AI check timed out"

            log_external_service_call(
                logger,
                service="documentai",
                operation="health_check",
                success=False,
                duration_ms=duration_ms,
                error=error_msg
            )

            return {
                "status": "error",
                "response_time_ms": round(duration_ms, 2),
                "message": error_msg
            }

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            log_external_service_call(
                logger,
                service="documentai",
                operation="health_check",
                success=False,
                duration_ms=duration_ms,
                error=str(e)
            )

            return {
                "status": "error",
                "response_time_ms": round(duration_ms, 2),
                "message": f"Document AI check failed: {str(e)}"
            }


# Global health checker instance
health_checker = HealthChecker()

# Create router
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthStatus)
async def liveness_check(request: Request):
    """
    Liveness probe - indicates if the service is alive.

    This endpoint should always return 200 OK if the service is running.
    Used by Kubernetes/load balancers to determine if the pod is alive.
    """
    logger = get_request_logger(request, "health")

    logger.info("Liveness check requested")

    return HealthStatus(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=health_checker.version,
        environment=health_checker.environment,
        uptime_seconds=health_checker.get_uptime_seconds()
    )


@router.get("/ready", response_model=ReadinessStatus)
async def readiness_check(request: Request, db: Session = Depends(get_db)):
    """
    Readiness probe - indicates if the service is ready to handle requests.

    Checks:
    - Database connectivity
    - S3 bucket access
    - Document AI availability (if not using stubs)

    Used by Kubernetes/load balancers to determine if the pod should receive traffic.
    """
    logger = get_request_logger(request, "health")

    logger.info("Readiness check requested")

    # Run all checks concurrently
    checks = {}
    overall_start_time = time.time()

    try:
        # Database check (required)
        checks["database"] = await health_checker.check_database(db, logger)

        # S3 check (required for file operations)
        checks["s3"] = await health_checker.check_s3(logger)

        # Document AI check (required for OCR, unless using stubs)
        checks["document_ai"] = await health_checker.check_document_ai(logger)

        # Determine overall health
        overall_healthy = all(
            check.get("status") == "ok" for check in checks.values()
        )

        overall_duration_ms = (time.time() - overall_start_time) * 1000

        logger.info(
            "Readiness check completed",
            overall_healthy=overall_healthy,
            total_duration_ms=round(overall_duration_ms, 2),
            check_results={k: v.get("status") for k, v in checks.items()}
        )

        # Return 200 if healthy, 503 if not
        status_code = 200 if overall_healthy else 503

        response = ReadinessStatus(
            status="ok" if overall_healthy else "error",
            timestamp=datetime.now(timezone.utc).isoformat(),
            checks=checks,
            overall_healthy=overall_healthy
        )

        if not overall_healthy:
            # Log failed readiness check
            logger.warning(
                "Readiness check failed",
                failed_checks=[k for k, v in checks.items() if v.get("status") != "ok"]
            )

        return response

    except Exception as e:
        overall_duration_ms = (time.time() - overall_start_time) * 1000

        logger.error(
            "Readiness check failed with exception",
            error=str(e),
            total_duration_ms=round(overall_duration_ms, 2)
        )

        # Return error response
        return ReadinessStatus(
            status="error",
            timestamp=datetime.now(timezone.utc).isoformat(),
            checks=checks,  # Return whatever checks completed
            overall_healthy=False
        )


@router.get("/info")
async def service_info(request: Request):
    """
    Service information endpoint.

    Returns detailed information about the service configuration
    and runtime environment (non-sensitive data only).
    """
    logger = get_request_logger(request, "health")

    logger.info("Service info requested")

    return {
        "service": "lcopilot-api",
        "version": health_checker.version,
        "environment": health_checker.environment,
        "uptime_seconds": health_checker.get_uptime_seconds(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "use_stubs": health_checker.use_stubs,
            "debug_mode": os.getenv("DEBUG", "false").lower() == "true",
            "aws_region": os.getenv("AWS_REGION", "not-set"),
            "database_configured": bool(os.getenv("DATABASE_URL")),
            "s3_bucket": os.getenv("S3_BUCKET_NAME", "not-set"),
            "documentai_project": os.getenv("GOOGLE_CLOUD_PROJECT", "not-set"),
            "documentai_location": os.getenv("GOOGLE_DOCUMENTAI_LOCATION", "not-set"),
        },
        "runtime": {
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            "process_id": os.getpid(),
        }
    }