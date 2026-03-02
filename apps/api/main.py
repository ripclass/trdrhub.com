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
from fastapi.exceptions import RequestValidationError
try:
    from mangum import Mangum  # AWS Lambda adapter (optional)  # type: ignore
    MANGUM_AVAILABLE = True
except ImportError:
    MANGUM_AVAILABLE = False

# Import logging and monitoring
from app.utils.logger import configure_logging, get_logger, log_exception
from app.middleware.logging import RequestIDMiddleware, RequestContextMiddleware
from app.middleware.tenant_resolver import TenantResolverMiddleware
from app.middleware.org_scope import OrgScopeMiddleware
from app.middleware.locale import LocaleMiddleware
from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

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
from sqlalchemy.exc import UnsupportedCompilationError, CompileError, OperationalError, DisconnectionError, TimeoutError as SATimeoutError, NoReferencedTableError
from app.utils.db_resilience import DB_OUTAGE_MESSAGE
from app.routers import auth, sessions, fake_s3, documents, lc_versions, audit, admin, analytics, billing, bank, bank_workflow, bank_users, bank_policy, bank_queue, bank_auth, bank_compliance, bank_sla, bank_evidence, bank_bulk_jobs, bank_ai, bank_duplicates, bank_saved_views, bank_tokens, bank_webhooks, bank_orgs, validate, rules_admin, onboarding, sme, sme_templates, workspace_sharing, company_profile, support, importer, exporter, jobs_public, price_verify, price_verify_admin, usage, members, admin_banks, tracking, doc_generator, doc_generator_catalog, doc_generator_advanced, lc_builder, hs_code, sanctions

# V2 Pipeline removed - using V1 with enhanced features
from app.routes.health import router as health_router
from app.routes.debug import router as debug_router
from app.schemas import ApiError
from app.config import settings
from app.middleware.quota_middleware import QuotaEnforcementMiddleware
from app.middleware.rate_limit import RateLimiterMiddleware
from app.middleware.csrf import CSRFMiddleware


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
    
    # Removed legacy sync event – rules are now DB-driven.

    # Initialize performance optimizations for Lambda
    if os.environ.get('AWS_LAMBDA_FUNCTION_NAME') and HAS_MONITORING:
        optimize_lambda_init()
    
    # Start background job scheduler (for tracking alerts, etc.)
    try:
        from app.scheduler import start_scheduler, stop_scheduler
        start_scheduler()
        logger.info("Background job scheduler started")
    except Exception as e:
        logger.warning(f"Failed to start scheduler: {e}")
    
    yield

    # Shutdown
    logger.info("LCopilot API shutting down")
    
    # Stop background scheduler
    try:
        from app.scheduler import stop_scheduler
        stop_scheduler()
        logger.info("Background job scheduler stopped")
    except Exception as e:
        logger.warning(f"Error stopping scheduler: {e}")


# Create database tables only when explicitly allowed
_auto_create_flag = os.getenv("ENABLE_SQLALCHEMY_CREATE_ALL", "").lower() in {"1", "true", "yes"}
if settings.is_development() or settings.USE_STUBS:
    # Keep backwards-compatible behavior for dev/stub installs unless the flag
    # is explicitly disabled. Teams that prefer Alembic-only flows should unset
    # the env var (default) and run `scripts/bootstrap_test_db.py`.
    _auto_create_flag = _auto_create_flag or os.getenv("DISABLE_DEV_CREATE_ALL", "").lower() not in {"1", "true", "yes"}

if _auto_create_flag:
    try:
        Base.metadata.create_all(bind=engine)
    except (UnsupportedCompilationError, CompileError) as exc:
        print(f"Skipping automatic schema creation due to unsupported dialect features: {exc}")
    except NoReferencedTableError as exc:
        # FK target table (e.g. 'organizations') is not defined as a SQLAlchemy
        # model but exists in the DB via Alembic migrations.  create_all cannot
        # resolve the reference from metadata alone so we skip it here and rely
        # on Alembic to manage the schema.  This is safe in production because
        # the real schema is managed exclusively by Alembic migrations.
        print(
            f"WARNING: Base.metadata.create_all() skipped — FK resolution error: {exc}. "
            "Schema is managed by Alembic migrations. This is expected in production."
        )
else:
    print("Skipping Base.metadata.create_all(); rely on Alembic migrations instead.")

# Create FastAPI app with lifespan events
app = FastAPI(
    title="LCopilot API",
    description="AI-powered Letter of Credit validation platform",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/healthz", tags=["health"], summary="Lightweight liveness probe")
async def healthz() -> Dict[str, str]:
    """Simple health endpoint for load balancers and uptime checks."""
    return {"status": "ok"}


@app.get("/health", tags=["health"], summary="Docker-compatible health probe")
async def health_check() -> Dict[str, str]:
    """Compat endpoint for container health checks."""
    return {"status": "ok"}


# Include API routers
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(lc_versions.router)  # LC version control endpoints
app.include_router(audit.router)        # Audit trail and compliance endpoints
app.include_router(admin.router)        # Admin endpoints for user and role management
app.include_router(analytics.router)    # Analytics dashboard endpoints
app.include_router(billing.router)      # Billing and payment management endpoints
app.include_router(bank.router)  # Bank portfolio endpoints
app.include_router(bank_workflow.router)  # Bank workflow endpoints (approvals, discrepancy workflow)
app.include_router(bank_users.router)  # Bank user management endpoints
app.include_router(bank_policy.router)  # Bank policy overlay endpoints
app.include_router(bank_queue.router)  # Bank queue operations endpoints
app.include_router(bank_auth.router)  # Bank authentication endpoints (2FA)
app.include_router(bank_compliance.router)  # Bank compliance endpoints (data retention, export, erase)
app.include_router(bank_sla.router)  # Bank SLA dashboards endpoints
app.include_router(bank_evidence.router)  # Bank evidence packs endpoints
app.include_router(bank_ai.router)  # Bank AI assistance endpoints
app.include_router(bank_duplicates.router)  # Bank duplicate detection endpoints
app.include_router(bank_saved_views.router)  # Bank saved views endpoints
app.include_router(bank_tokens.router)  # Bank API tokens endpoints
app.include_router(bank_webhooks.router)  # Bank webhooks endpoints
app.include_router(bank_orgs.router)  # Bank organizations endpoints
app.include_router(onboarding.router)   # Onboarding wizard endpoints
app.include_router(sme.router)          # SME workspace endpoints (LC Workspace, Drafts, Amendments)
app.include_router(sme_templates.router)  # SME templates endpoints (LC and document templates with pre-fill)
app.include_router(workspace_sharing.router)  # SME workspace sharing endpoints (team roles, invitations)
app.include_router(company_profile.router)  # Company profile endpoints (addresses, compliance, consignee/shipper)
app.include_router(support.router)  # Support ticket endpoints (with context pre-filling)
app.include_router(importer.router)  # Importer-specific endpoints (supplier fix pack, bank precheck)
app.include_router(price_verify.router)  # Price verification endpoints (commodity price comparison)
app.include_router(price_verify_admin.router)  # Price verify admin (commodity management)
app.include_router(usage.router)  # Hub usage tracking (limits, billing, history)
app.include_router(members.router)  # RBAC team management (members, invitations, permissions)
app.include_router(admin_banks.router)  # Admin bank management (invite-only bank onboarding)
app.include_router(tracking.router)  # Container & vessel tracking (real-time AIS, carrier APIs)
app.include_router(doc_generator.router)  # Shipping document generator (Invoice, Packing List, CoO)
app.include_router(doc_generator_catalog.router)  # Doc generator templates, products, buyers (Phase 2)
app.include_router(doc_generator_advanced.router)  # Doc generator signatures, translations, certificates (Phase 3)
app.include_router(lc_builder.router)  # LC Application Builder (wizard, clauses, MT700 export)
app.include_router(hs_code.router)  # HS Code Finder (AI classification, duty calculator, FTA checker)
app.include_router(sanctions.router)  # Sanctions Screener (party, vessel, goods screening)
# V2 router removed - V1 enhanced with bank-grade features
app.include_router(exporter.router)  # Exporter-specific endpoints (customs pack, bank submissions)
app.include_router(jobs_public.router)  # Public validation job status/results endpoints
app.include_router(health_router)       # Use the new comprehensive health endpoints

# Development-only routes
if settings.is_development() or settings.USE_STUBS:
    app.include_router(debug_router)        # Debug routes for monitoring testing
    app.include_router(fake_s3.router)      # Fake S3 routes for stub mode

# Production routes
app.include_router(documents.router)
app.include_router(validate.router)
app.include_router(rules_admin.router)
app.include_router(rules_admin.rules_router)

# Note: Startup logging is now handled in the lifespan function

# Add logging middleware (order matters - add first)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(TenantResolverMiddleware)
app.add_middleware(OrgScopeMiddleware)  # Resolve org_id for multi-org switching
app.add_middleware(LocaleMiddleware)  # Resolve locale for i18n
app.add_middleware(SecurityHeadersMiddleware)  # Add security headers to all responses

# Baseline abuse protection
_rate_limit = os.getenv("API_RATE_LIMIT_TENANT") or os.getenv("API_RATE_LIMIT")
_anon_rate_limit = os.getenv("API_RATE_LIMIT_ANON")
_rate_window = os.getenv("API_RATE_WINDOW")

try:
    rate_limit_per_window = int(_rate_limit) if _rate_limit is not None else 120
except ValueError:
    rate_limit_per_window = 120

try:
    anon_limit = int(_anon_rate_limit) if _anon_rate_limit is not None else 10
except ValueError:
    anon_limit = 10

try:
    rate_limit_window_seconds = int(_rate_window) if _rate_window is not None else 60
except ValueError:
    rate_limit_window_seconds = 60

app.add_middleware(
    RateLimiterMiddleware,
    limit=rate_limit_per_window,
    window_seconds=rate_limit_window_seconds,
    unauthenticated_limit=anon_limit,
    authenticated_limit=rate_limit_per_window,
    exempt_paths=(
        "/health",
        "/health/info",
        "/health/live",
        "/health/ready",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/warm",
    ),
)

# Add quota enforcement middleware (before audit middleware)
app.add_middleware(QuotaEnforcementMiddleware)

# Add audit middleware for compliance traceability
app.add_middleware(
    AuditMiddleware,
        excluded_paths=[
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
            "/warm",
            "/auth/login",
            "/auth/register",
            "/auth/csrf-token",  # Temporarily exempt to avoid audit logging issues
            "/api/validate",  # TEMPORARY - Exempt for demo mode
            "/auth/fix-password",  # TEMPORARY - Remove after fixing passwords
        ],
)

# Add CSRF protection middleware (before CORS) for authenticated environments
if not settings.USE_STUBS:
    app.add_middleware(
        CSRFMiddleware,
        secret_key=settings.SECRET_KEY,
        cookie_name="csrf_token",
        header_name="X-CSRF-Token",
        exempt_paths={
            "/health",
            "/health/info",
            "/health/live",
            "/health/ready",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/metrics",
            "/warm",
            "/auth/csrf-token",  # CSRF token endpoint itself
            "/auth/login",
            "/auth/register",
            "/auth/fix-password",  # TEMPORARY - Remove after fixing passwords
            "/api/validate",  # TEMPORARY - Exempt for demo mode (validation works without auth)
            "/price-verify",  # Price verification API (public tool)
            "/members/admin/seed-existing-users",  # One-time setup endpoint
        },
        exempt_methods={"GET", "HEAD", "OPTIONS"},
        token_expiry_seconds=3600,  # 1 hour
    )

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

if not settings.is_production() and cors_origins == ["http://localhost:5173"]:
    cors_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

allowed_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
allowed_headers = [
    "Authorization",
    "Content-Type",
    "Accept",
    "X-Requested-With",
    "X-CSRF-Token",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
)


# Note: Performance and request tracking is now handled by RequestIDMiddleware


# Error handling middleware with structured logging
async def database_exception_handler(request: Request, exc: Exception):
    """Return explicit 503 for database connectivity outages."""
    from datetime import datetime, timezone

    origin = request.headers.get("origin")
    cors_headers = {}
    if origin:
        allowed_origins = settings.CORS_ALLOW_ORIGINS
        if settings.is_production() and allowed_origins == ["*"]:
            allowed_origins = [
                "https://trdrhub.com",
                "https://www.trdrhub.com",
                "https://trdrhub.vercel.app",
            ]
        if "*" in allowed_origins or origin in allowed_origins:
            cors_headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
            }

    return JSONResponse(
        status_code=503,
        content={
            "error": "database_unavailable",
            "message": DB_OUTAGE_MESSAGE,
            "detail": "Database connectivity issue detected. Retry shortly.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path),
        },
        headers={
            "X-Request-ID": getattr(request.state, "request_id", "unknown"),
            **cors_headers,
        }
    )


# Register DB-related exception handlers explicitly (FastAPI requires one class per registration)
app.add_exception_handler(OperationalError, database_exception_handler)
app.add_exception_handler(DisconnectionError, database_exception_handler)
app.add_exception_handler(SATimeoutError, database_exception_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with structured error responses and logging."""
    from datetime import datetime, timezone
    from app.middleware.logging import get_request_logger

    # Get logger with request context
    logger = get_request_logger(request, "exception_handler")

    error_identifier = type(exc).__name__.lower()
    message = str(exc)
    if settings.is_production():
        message = "An unexpected error occurred. Please contact support if the issue persists."

    error_response = ApiError(
        error=error_identifier if not settings.is_production() else "server_error",
        message=message,
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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors with a clean, frontend-safe response.
    
    This prevents React Error #31 caused by rendering raw Pydantic error objects
    that have keys like {type, loc, msg, input, ctx, url}.
    """
    from datetime import datetime, timezone
    
    # Extract human-readable error messages
    errors = exc.errors()
    messages = []
    for err in errors:
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Validation error")
        messages.append(f"{loc}: {msg}" if loc else msg)
    
    error_message = "; ".join(messages) if messages else "Request validation failed"
    
    # Build CORS headers
    origin = request.headers.get("origin")
    cors_headers = {}
    if origin:
        allowed_origins = settings.CORS_ALLOW_ORIGINS
        if settings.is_production() and allowed_origins == ["*"]:
            allowed_origins = [
                "https://trdrhub.com",
                "https://www.trdrhub.com",
                "https://trdrhub.vercel.app",
            ]
        if "*" in allowed_origins or origin in allowed_origins:
            cors_headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
            }
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": error_message,
            "detail": error_message,  # String, not array of objects
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path),
        },
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
        import psutil  # type: ignore

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
