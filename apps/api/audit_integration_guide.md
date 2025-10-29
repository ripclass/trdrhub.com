# 🔍 LCopilot Audit Trail Integration Guide

## Overview

The LCopilot Audit Trail system provides comprehensive compliance traceability for all user actions. Every upload, validation, download, and LC version operation is automatically logged with who/what/when/result/version information.

## 🏗️ Architecture

### Components
- **Database Model**: `AuditLog` with comprehensive fields for compliance
- **Service Layer**: `AuditService` with file hashing and integrity verification
- **Middleware**: `AuditMiddleware` for automatic request correlation
- **Admin API**: Advanced queries, compliance reports, and file integrity checks
- **Schemas**: Type-safe Pydantic models for all operations

### Key Features
- ✅ Automatic file hashing (SHA-256) for integrity verification
- ✅ Request correlation IDs for tracing complete workflows
- ✅ IP address tracking and user agent logging
- ✅ Configurable retention policies (default 7 years)
- ✅ Advanced search and filtering capabilities
- ✅ Compliance reporting with statistics and breakdowns
- ✅ Real-time failure monitoring and alerting

## 🚀 Integration Steps

### 1. Apply Database Migration

```bash
# Apply the audit_log table migration
alembic upgrade head
```

### 2. Add Audit Middleware to FastAPI App

```python
# In main.py
from app.middleware.audit_middleware import AuditMiddleware

app = FastAPI(title="LCopilot API")

# Add audit middleware (place early in middleware stack)
app.add_middleware(AuditMiddleware, excluded_paths=["/docs", "/health"])
```

### 3. Update Model Imports

```python
# In app/models/__init__.py
from .audit_log import AuditLog, AuditAction, AuditResult

# Add to __all__
__all__ = [
    "User", "ValidationSession", "Document", "Discrepancy",
    "LCVersion", "AuditLog", "AuditAction", "AuditResult"
]
```

### 4. Add Audit Router to Main App

```python
# In main.py
from app.routers import audit

app.include_router(audit.router)
```

### 5. Integration in Existing Endpoints

#### Manual Audit Logging (Recommended for Critical Operations)

```python
from app.services.audit_service import AuditService
from app.models.audit_log import AuditAction, AuditResult

@router.post("/upload")
async def upload_file(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    audit_service = AuditService(db)

    try:
        file_content = await file.read()

        # Your existing upload logic here
        validation_session = create_validation_session(...)

        # Log successful upload
        audit_service.log_upload(
            user=current_user,
            file_content=file_content,
            filename=file.filename,
            lc_number=extracted_lc_number,
            validation_session_id=str(validation_session.id),
            correlation_id=request.state.correlation_id,
            ip_address=get_client_ip(request),
            result=AuditResult.SUCCESS
        )

        return {"session_id": validation_session.id}

    except Exception as e:
        # Log failed upload
        audit_service.log_upload(
            user=current_user,
            file_content=file_content,
            filename=file.filename,
            result=AuditResult.FAILURE,
            error_message=str(e)
        )
        raise HTTPException(500, detail=str(e))
```

#### Validation Logging

```python
@router.post("/validate/{session_id}")
async def validate_documents(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    audit_service = AuditService(db)
    start_time = time.time()

    try:
        # Your validation logic
        discrepancies = perform_validation(session_id)
        duration_ms = int((time.time() - start_time) * 1000)

        # Log successful validation
        audit_service.log_validation(
            user=current_user,
            validation_session_id=str(session_id),
            lc_number=session.lc_number,
            discrepancy_count=len(discrepancies),
            duration_ms=duration_ms,
            result=AuditResult.SUCCESS
        )

        return {"discrepancies": discrepancies}

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)

        audit_service.log_validation(
            user=current_user,
            validation_session_id=str(session_id),
            duration_ms=duration_ms,
            result=AuditResult.ERROR,
            error_message=str(e)
        )
        raise
```

#### LC Version Operations

```python
from app.seeds.seed_versions import hook_into_validation_pipeline

# In your validation completion handler
def on_validation_complete(db: Session, session: ValidationSession):
    # Existing logic...

    # Automatically seed V1 if first version
    hook_into_validation_pipeline(db, session)

    # Manual audit logging for version creation
    if version_created:
        audit_service = AuditService(db)
        audit_service.log_version_action(
            action=AuditAction.CREATE_VERSION,
            user=session.user,
            lc_number=session.lc_number,
            lc_version="V1",
            version_id=str(version.id),
            metadata={"auto_created": True, "validation_session_id": str(session.id)}
        )
```

## 📊 Admin Dashboard Integration

### Audit Log Queries

```python
# Get recent user activity
GET /admin/audit/user/{user_id}/activity?limit=50

# Get LC audit trail
GET /admin/audit/lc/{lc_number}/activity

# Search audit logs
GET /admin/audit/search?q=validation&limit=100

# Get recent failures
GET /admin/audit/failures?hours=24

# Get compliance statistics
GET /admin/audit/statistics?days=30
```

### Compliance Reporting

```python
# Generate compliance report
POST /admin/audit/compliance-report
{
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-12-31T23:59:59Z",
    "user_id": "optional-user-filter",
    "action": "upload",
    "include_details": true
}
```

### File Integrity Verification

```python
# Verify file integrity
POST /admin/audit/verify-integrity?file_hash=abc123&expected_hash=abc123
```

## 🔧 Configuration

### Environment Variables

```bash
# Audit configuration
AUDIT_ENABLED=true
AUDIT_RETENTION_DAYS=2555  # 7 years default
AUDIT_AUTO_ARCHIVE=true
AUDIT_EXCLUDED_PATHS="/docs,/health,/metrics"
```

### Retention Policy

```python
# Default retention periods
DEFAULT_RETENTION_DAYS = 2555  # 7 years
CRITICAL_ACTION_RETENTION_DAYS = 3650  # 10 years for critical actions
MIN_RETENTION_DAYS = 365  # 1 year minimum
```

## 🎯 Usage Examples

### Frontend Integration

```typescript
// Add correlation ID to requests
const correlationId = uuidv4();

const response = await fetch('/api/upload', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'X-Correlation-ID': correlationId
    },
    body: formData
});

// Correlation ID is returned in response headers
const responseCorrelationId = response.headers.get('X-Correlation-ID');
```

### Monitoring and Alerting

```python
# Monitor recent failures
@scheduler.scheduled_job('interval', minutes=5)
def check_audit_failures():
    recent_failures = audit_service.get_recent_failures(hours=1)

    if len(recent_failures) > FAILURE_THRESHOLD:
        send_alert(f"High failure rate detected: {len(recent_failures)} failures in last hour")
```

### Custom Audit Events

```python
# Log custom business events
audit_service.log_action(
    action="CUSTOM_BUSINESS_EVENT",
    user=current_user,
    resource_type="business_process",
    resource_id="process_123",
    result=AuditResult.SUCCESS,
    metadata={
        "process_name": "quarterly_report_generation",
        "parameters": {"quarter": "Q1_2025"},
        "business_impact": "high"
    }
)
```

## 🔍 Troubleshooting

### Common Issues

1. **Missing Correlation IDs**: Ensure middleware is properly configured
2. **Performance Issues**: Check database indexes on audit_log table
3. **Large Log Volume**: Implement log archiving and cleanup procedures
4. **Missing User Context**: Verify JWT token extraction in middleware

### Debug Mode

```python
# Enable detailed audit logging
AUDIT_DEBUG=true
```

### Health Checks

```python
# Check audit system health
GET /admin/audit/statistics

# Expected response includes:
# - total_actions > 0
# - success_rate > 95%
# - recent_failures < threshold
```

## 📈 Performance Considerations

### Database Optimization

- Indexes are automatically created on key fields (user_id, timestamp, action, etc.)
- Consider partitioning by month for high-volume environments
- Implement automatic archiving for logs older than retention period

### Middleware Performance

- Audit middleware adds ~1-5ms per request
- File hashing adds overhead proportional to file size
- Consider async logging for high-throughput scenarios

## 🔒 Security and Compliance

### Data Protection
- Sensitive fields are automatically redacted in request/response logging
- File hashes provide tamper-evidence for uploaded documents
- IP addresses and user agents logged for forensic analysis

### Compliance Features
- 7-year default retention meets most regulatory requirements
- Immutable audit trail (append-only)
- Comprehensive activity tracking for SOX, GDPR, and financial regulations

## 🚀 Deployment Checklist

- [ ] Database migration applied (`alembic upgrade head`)
- [ ] Middleware configured in main.py
- [ ] Audit router included in FastAPI app
- [ ] Model imports updated
- [ ] Critical endpoints instrumented with manual logging
- [ ] Admin access configured for audit endpoints
- [ ] Retention policy configured
- [ ] Monitoring and alerting set up
- [ ] Performance impact tested
- [ ] Compliance requirements verified

## 📞 Support

For issues or questions about the audit trail system:
1. Check this integration guide
2. Review test cases in `tests/test_audit.py`
3. Examine demo script: `python audit_demo.py`
4. Contact the development team

---

**Next Steps**: Run `python audit_demo.py` to see the complete audit trail system in action!