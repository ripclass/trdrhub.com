"""
FastAPI application with performance monitoring integration.

This is an example of how to integrate the performance monitoring
middleware with a FastAPI application.
"""

import os
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
try:
    from mangum import Mangum  # AWS Lambda adapter (optional)
    MANGUM_AVAILABLE = True
except ImportError:
    MANGUM_AVAILABLE = False

# Import logging and monitoring
from app.utils.logger import configure_logging, get_logger, log_exception
from app.middleware.logging import RequestIDMiddleware, RequestContextMiddleware
from app.middleware.tenant_resolver import TenantResolverMiddleware
# from app.middleware.audit_middleware import AuditMiddleware

# Import performance monitoring (optional for basic operation)
try:
    from middleware.performance_monitoring import (
        monitor_performance,
        performance_context,
        optimize_lambda_init
    )
    HAS_MONITORING = True
except ImportError:
    print("Performance monitoring middleware not found - running without monitoring")
    HAS_MONITORING = False
    
    # Provide no-op decorators
    def monitor_performance(func):
        return func
    
    def performance_context(name):
        from contextlib import nullcontext
        return nullcontext()
    
    def optimize_lambda_init():
        pass

# Import application modules
from app.database import Base, engine
from sqlalchemy.exc import UnsupportedCompilationError, CompileError
from app.routers import auth, sessions, fake_s3, documents, lc_versions, audit, admin, analytics, billing, bank, validate, rules_admin, onboarding
from app.routes.health import router as health_router
from app.routes.debug import router as debug_router
from app.schemas import ApiError
from app.config import settings
from app.middleware.quota_middleware import QuotaEnforcementMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    startup_issues = []

    # Initialize logging first
    logger = configure_logging()
    logger.info("LCopilot API starting up", environment=settings.ENVIRONMENT)

    # Startup
    logger.info(
        "Application configuration",
        environment=settings.ENVIRONMENT,
        debug_mode=settings.DEBUG,
        stub_mode=settings.USE_STUBS
    )
    
    # Production safety warnings
    if settings.is_production():
        if settings.USE_STUBS:
            startup_issues.append("CRITICAL: Stub mode is enabled in production!")
            logger.critical("Stub mode enabled in production - this is unsafe!")
        if settings.SECRET_KEY == "dev-secret-key-change-in-production":
            startup_issues.append("CRITICAL: Default secret key is being used in production!")
            logger.critical("Default secret key detected in production!")
        logger.info("Production mode enabled - real services will be used")
    else:
        logger.info("Development mode - stub services available")
    
    # Check database connectivity
    try:
        from app.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection established")
    except Exception as e:
        startup_issues.append(f"Database connection failed: {e}")
        logger.error("Database connection failed", error=str(e))
    
    # Check stub mode configuration if enabled
    if settings.USE_STUBS:
        print(f"  Stub Scenario: {settings.STUB_SCENARIO}")
        print(f"  OCR Failures: {settings.STUB_FAIL_OCR}")
        print(f"  Storage Failures: {settings.STUB_FAIL_STORAGE}")
        
        # Initialize stub directories using utility functions
        try:
            from app.utils import ensure_stub_directories
            directories = ensure_stub_directories(settings)
            print(f"✅ Stub directories initialized: {list(directories.keys())}")
        except Exception as e:
            startup_issues.append(f"Failed to initialize stub directories: {e}")
            print(f"❌ Stub directory initialization: {e}")
        
        # Validate stub scenario file exists and is valid JSON
        from pathlib import Path
        scenario_file = Path(settings.STUB_DATA_DIR) / settings.STUB_SCENARIO
        if not scenario_file.exists():
            startup_issues.append(f"Stub scenario file not found: {scenario_file}")
            print(f"❌ Stub scenario file: {scenario_file} not found")
        else:
            try:
                # Validate JSON syntax and structure
                import json
                from app.stubs.models import StubScenarioModel
                
                with open(scenario_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Validate with Pydantic model
                scenario = StubScenarioModel.model_validate(data)
                print(f"✅ Stub scenario file: {scenario_file}")
                print(f"  Scenario: {scenario.scenario_name}")
                print(f"  Documents: {len(scenario.documents)}")
                print(f"  Expected discrepancies: {scenario.expected_discrepancies}")
                
            except json.JSONDecodeError as e:
                startup_issues.append(f"Invalid JSON in scenario file {scenario_file}: {e}")
                print(f"❌ Stub scenario JSON: Invalid syntax in {scenario_file}")
            except Exception as e:
                startup_issues.append(f"Invalid scenario file {scenario_file}: {e}")
                print(f"❌ Stub scenario validation: {e}")
    
    # Check required environment variables for real services
    if not settings.USE_STUBS:
        if not settings.GOOGLE_CLOUD_PROJECT:
            startup_issues.append("GOOGLE_CLOUD_PROJECT not set - OCR services may fail")
        if not settings.GOOGLE_DOCUMENTAI_PROCESSOR_ID:
            startup_issues.append("GOOGLE_DOCUMENTAI_PROCESSOR_ID not set - OCR services may fail")
    
    # Log startup summary
    if startup_issues:
        logger.warning(
            "Startup issues detected",
            issue_count=len(startup_issues),
            issues=startup_issues
        )
    else:
        logger.info("All startup validations passed")
    
    # Start weekly RulHub sync when enabled
    try:
        if settings.USE_RULHUB_API:
            from app.jobs.rulhub_sync_job import start_sync_job
            start_sync_job()
            logger.info("RulHub weekly sync job started")
    except Exception as e:
        logger.error("Failed to start RulHub sync job", error=str(e))

    # Initialize performance optimizations for Lambda
    if os.environ.get('AWS_LAMBDA_FUNCTION_NAME') and HAS_MONITORING:
        optimize_lambda_init()
    
    yield

    # Shutdown
    logger.info("LCopilot API shutting down")


# Create database tables in development/stub environments only
if settings.is_development() or settings.USE_STUBS:
    try:
        Base.metadata.create_all(bind=engine)
    except (UnsupportedCompilationError, CompileError) as exc:
        print(f"Skipping automatic schema creation due to unsupported dialect features: {exc}")

# Create FastAPI app with lifespan events
app = FastAPI(
    title="LCopilot API",
    description="AI-powered Letter of Credit validation platform",
    version="1.0.0",
    lifespan=lifespan
)

# Include API routers
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(lc_versions.router)  # LC version control endpoints
app.include_router(audit.router)        # Audit trail and compliance endpoints
app.include_router(admin.router)        # Admin endpoints for user and role management
app.include_router(analytics.router)    # Analytics dashboard endpoints
app.include_router(billing.router)      # Billing and payment management endpoints
app.include_router(bank.router)  # Bank portfolio endpoints
app.include_router(onboarding.router)   # Onboarding wizard endpoints
app.include_router(health_router)       # Use the new comprehensive health endpoints

# Development-only routes
if settings.is_development() or settings.USE_STUBS:
    app.include_router(debug_router)        # Debug routes for monitoring testing
    app.include_router(fake_s3.router)      # Fake S3 routes for stub mode

# Production routes
app.include_router(documents.router)
app.include_router(validate.router)
app.include_router(rules_admin.router)

# Note: Startup logging is now handled in the lifespan function

# Add logging middleware (order matters - add first)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(TenantResolverMiddleware)

# Add quota enforcement middleware (before audit middleware)
app.add_middleware(QuotaEnforcementMiddleware)

# Add audit middleware for compliance traceability
# app.add_middleware(
#     AuditMiddleware,
#     excluded_paths=["/docs", "/redoc", "/openapi.json", "/health", "/metrics", "/warm"]
# )

# Add CORS middleware
# In production, restrict to specific domains for security
# Set CORS_ALLOW_ORIGINS env var as comma-separated list: "https://trdrhub.com,https://www.trdrhub.com"
# Defaults to ["*"] for development
cors_origins = settings.CORS_ALLOW_ORIGINS
if settings.is_production() and cors_origins == ["*"]:
    # Fallback for production if not configured - use common production domains
    cors_origins = [
        "https://trdrhub.com",
        "https://www.trdrhub.com",
        "https://trdrhub.vercel.app",  # Vercel preview URLs
    ]
    print(
        "WARNING: CORS_ALLOW_ORIGINS not configured for production, using defaults. "
        "Set CORS_ALLOW_ORIGINS env var for security."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Note: Performance and request tracking is now handled by RequestIDMiddleware


# Error handling middleware with structured logging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with structured error responses and logging."""
    from datetime import datetime, timezone
    from app.middleware.logging import get_request_logger

    # Get logger with request context
    logger = get_request_logger(request, "exception_handler")

    error_response = ApiError(
        error=type(exc).__name__.lower(),
        message=str(exc),
        timestamp=datetime.now(timezone.utc),
        path=str(request.url.path),
        method=request.method
    )

    # Log exception with structured logging
    log_exception(
        logger,
        exc,
        http_method=request.method,
        http_path=str(request.url.path),
        error_type=type(exc).__name__
    )

    # Get CORS headers from request origin
    origin = request.headers.get("origin")
    cors_headers = {}
    if origin:
        # Check if origin is in allowed list
        allowed_origins = settings.CORS_ALLOW_ORIGINS
        if settings.is_production() and allowed_origins == ["*"]:
            # Use default production origins
            allowed_origins = [
                "https://trdrhub.com",
                "https://www.trdrhub.com",
                "https://trdrhub.vercel.app",
            ]
        if "*" in allowed_origins or origin in allowed_origins:
            cors_headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
            }

    # Serialize error response to JSON string first, then parse back to dict
    # This ensures datetime objects are properly serialized to ISO strings
    import json
    error_dict = json.loads(error_response.model_dump_json())
    
    return JSONResponse(
        status_code=500,
        content=error_dict,
        headers={
            "X-Request-ID": getattr(request.state, "request_id", "unknown"),
            **cors_headers
        }
    )


# Note: Health endpoints are now handled by the dedicated health router


# Warming endpoint to handle Lambda warmer requests
@app.post("/warm")
async def warm_endpoint(request: Request):
    """Handle warming requests from Lambda warmer."""
    body = await request.json()
    
    if body.get('warming') and body.get('source') == 'lambda-warmer':
        return {
            "status": "warm",
            "message": "Lambda function is warm",
            "timestamp": time.time()
        }
    
    return {"status": "ok"}


# Root endpoint with logging
@app.get("/")
async def root(request: Request):
    """API root endpoint."""
    from app.middleware.logging import get_request_logger

    logger = get_request_logger(request, "root")
    logger.info("Root endpoint accessed")

    return {
        "message": "LCopilot API - AI-powered Letter of Credit validation",
        "version": "2.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "docs_url": "/docs",
        "health_endpoints": {
            "liveness": "/health/live",
            "readiness": "/health/ready",
            "info": "/health/info"
        }
    }


# Performance metrics endpoint with logging
@app.get("/metrics/performance")
async def get_performance_metrics(request: Request):
    """Get current performance metrics."""
    from app.middleware.logging import get_request_logger

    logger = get_request_logger(request, "metrics")

    try:
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        metrics = {
            "memory_usage_mb": round(memory_info.rss / 1024 / 1024, 2),
            "memory_percent": round(process.memory_percent(), 2),
            "cpu_percent": round(process.cpu_percent(), 2),
            "timestamp": time.time()
        }

        logger.info("Performance metrics requested", **metrics)
        return metrics

    except Exception as e:
        logger.error("Failed to get performance metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get metrics")


# Lambda handler using Mangum (only when available/environment requires it)
if MANGUM_AVAILABLE:
    handler = Mangum(app, lifespan="off")

    @monitor_performance
    def lambda_handler(event: Dict[str, Any], context: Any) -> Any:
        """Lambda handler with performance monitoring."""
        return handler(event, context)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

