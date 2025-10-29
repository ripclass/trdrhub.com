# 🔍 LCopilot Monitoring & Logging Guide

This document describes the production-grade monitoring and logging system implemented for LCopilot API.

## 📋 Table of Contents

- [Overview](#overview)
- [Structured Logging](#structured-logging)
- [Request Tracking](#request-tracking)
- [Health Endpoints](#health-endpoints)
- [CloudWatch Integration](#cloudwatch-integration)
- [Alerting & Notifications](#alerting--notifications)
- [Setup Instructions](#setup-instructions)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

LCopilot API includes comprehensive monitoring with:

- **Structured JSON logging** with request correlation
- **CloudWatch integration** for production log aggregation
- **Health endpoints** for load balancer checks
- **Automated alerting** for error spikes and performance issues
- **Request tracking** with unique IDs across the entire request lifecycle

## 📝 Structured Logging

### Features

- **JSON format** for easy parsing and filtering
- **Request correlation** with unique request IDs
- **Multiple log levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Contextual information**: service, environment, hostname, version
- **Performance metrics**: request duration, database query times
- **External service tracking**: S3, Document AI, database operations

### Log Format

```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "level": "INFO",
  "service": "lcopilot-api",
  "environment": "production",
  "hostname": "api-server-01",
  "version": "2.0.0",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "API request completed",
  "http_method": "POST",
  "http_path": "/api/sessions",
  "http_status_code": 200,
  "request_duration_ms": 342.56,
  "user_id": "user_123"
}
```

### Usage in Code

```python
from app.utils.logger import get_logger, log_api_request

# Get logger with request context
logger = get_logger("service_name", request_id="req_123")

# Log with structured data
logger.info(
    "Document processed successfully",
    document_id="doc_456",
    processing_time_ms=1250.5,
    document_type="letter_of_credit"
)

# Log API requests automatically
log_api_request(
    logger,
    method="POST",
    path="/api/documents",
    status_code=201,
    duration_ms=800.2
)
```

## 🔄 Request Tracking

### Request ID Middleware

Every API request gets a unique request ID that:

- **Preserves client-provided** `X-Request-ID` headers
- **Generates UUID4** if no ID provided
- **Injects into log context** automatically
- **Returns in response headers** for client correlation
- **Tracks request lifecycle** from start to finish

### Request Flow

```
1. Client Request  → [X-Request-ID: abc123] (optional)
2. Middleware      → Generate/preserve request ID
3. Log Context     → Inject ID into all logs
4. Response        → Return ID in X-Request-ID header
5. Error Handling  → Include ID in error responses
```

## 🏥 Health Endpoints

### Liveness Probe: `/health/live`

**Purpose**: Indicates if the service is alive
**Used by**: Kubernetes, load balancers
**Response**:

```json
{
  "status": "ok",
  "timestamp": "2025-01-15T10:30:45.123Z",
  "version": "2.0.0",
  "environment": "production",
  "uptime_seconds": 3600
}
```

### Readiness Probe: `/health/ready`

**Purpose**: Indicates if the service is ready to handle requests
**Used by**: Load balancers for traffic routing
**Checks**:

- ✅ Database connectivity (PostgreSQL)
- ✅ S3 bucket accessibility
- ✅ Document AI availability (unless using stubs)

**Response**:

```json
{
  "status": "ok",
  "timestamp": "2025-01-15T10:30:45.123Z",
  "overall_healthy": true,
  "checks": {
    "database": {
      "status": "ok",
      "response_time_ms": 23.45,
      "message": "Database connection successful"
    },
    "s3": {
      "status": "ok",
      "response_time_ms": 156.78,
      "message": "S3 bucket 'lcopilot-docs-prod' accessible",
      "bucket": "lcopilot-docs-prod"
    },
    "document_ai": {
      "status": "ok",
      "response_time_ms": 489.12,
      "message": "Document AI accessible (3 processors found)",
      "project": "lcopilot-docai",
      "location": "eu"
    }
  }
}
```

### Service Info: `/health/info`

**Purpose**: Detailed service information (non-sensitive)

```json
{
  "service": "lcopilot-api",
  "version": "2.0.0",
  "environment": "production",
  "uptime_seconds": 7200,
  "configuration": {
    "use_stubs": false,
    "debug_mode": false,
    "aws_region": "eu-north-1",
    "database_configured": true,
    "s3_bucket": "lcopilot-docs-prod"
  },
  "runtime": {
    "python_version": "3.9.6",
    "process_id": 1234
  }
}
```

## ☁️ CloudWatch Integration

### Log Groups & Streams

- **Log Group**: `lcopilot-backend`
- **Log Stream**: `{hostname}-{environment}`
- **Retention**: 30 days
- **Format**: JSON with structured fields

### Metric Filters

| Filter Name | Pattern | Metric | Description |
|-------------|---------|---------|-------------|
| `LCopilotErrorFilter` | `{ $.level = "ERROR" }` | `LCopilotErrorCount` | Count of ERROR level logs |
| `LCopilotCriticalFilter` | `{ $.level = "CRITICAL" }` | `LCopilotCriticalErrorCount` | Count of CRITICAL level logs |
| `LCopilot5xxErrorFilter` | `{ $.http_status_code >= 500 }` | `LCopilot5xxErrorCount` | Count of 5xx HTTP errors |
| `LCopilotSlowRequestFilter` | `{ $.request_duration_ms > 5000 }` | `LCopilotSlowRequestCount` | Count of slow requests (>5s) |

### Environment Configuration

```bash
# Required for CloudWatch logging
ENVIRONMENT=production
AWS_REGION=eu-north-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

## 🚨 Alerting & Notifications

### CloudWatch Alarms

| Alarm Name | Condition | Threshold | Action |
|------------|-----------|-----------|---------|
| `LCopilot-HighErrorRate` | Error count in 1 min | ≥ 5 errors | SNS notification |
| `LCopilot-CriticalErrors` | Critical errors in 1 min | ≥ 1 error | SNS notification |
| `LCopilot-High5xxErrors` | 5xx errors in 5 min | ≥ 10 errors | SNS notification |
| `LCopilot-SlowRequests` | Slow requests in 5 min | ≥ 5 requests | SNS notification |

### SNS Topic

- **Topic Name**: `lcopilot-alerts`
- **Purpose**: Send notifications when alarms trigger
- **Supports**: Email, SMS, Slack webhooks

## 🛠️ Setup Instructions

### 1. Install Dependencies

```bash
cd apps/api
pip install -r requirements.txt
```

Required packages:
- `structlog==24.1.0` - Structured logging
- `watchtower==3.0.1` - CloudWatch log handler
- `boto3-stubs[essential]==1.34.0` - AWS SDK type hints

### 2. Configure Environment Variables

Create `.env.production`:

```bash
# Application
ENVIRONMENT=production
DEBUG=false

# Database
DATABASE_URL=postgresql://user:pass@host:5432/lcopilot

# AWS CloudWatch
AWS_REGION=eu-north-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Service Configuration
USE_STUBS=false
SECRET_KEY=your-production-secret-key
```

### 3. Set Up CloudWatch Resources

```bash
cd apps/api
python setup_cloudwatch.py
```

This creates:
- Log group with 30-day retention
- Metric filters for error tracking
- CloudWatch alarms
- SNS topic for notifications

### 4. Subscribe to Alerts

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:eu-north-1:123456789012:lcopilot-alerts \
  --protocol email \
  --notification-endpoint your-email@domain.com
```

### 5. Start the Application

```bash
python main.py
```

The application will:
- Initialize structured logging
- Configure CloudWatch handlers
- Register health endpoints
- Start request tracking

## 🧪 Testing

### Run Test Suite

```bash
python test_monitoring.py
```

This tests:
- ✅ Logging configuration
- ✅ Environment variables
- ✅ Health endpoints
- ✅ Request tracking
- ✅ Error handling
- ✅ CloudWatch dependencies

### Manual Testing

#### Test Health Endpoints

```bash
# Liveness check
curl http://localhost:8000/health/live

# Readiness check
curl http://localhost:8000/health/ready

# Service info
curl http://localhost:8000/health/info
```

#### Test Request Tracking

```bash
# Send request with custom ID
curl -H "X-Request-ID: test-123" http://localhost:8000/

# Check response headers for request ID
curl -I http://localhost:8000/
```

#### Test Error Handling

```bash
# Trigger 404 error
curl http://localhost:8000/nonexistent

# Trigger 500 error (if endpoint exists)
curl -X POST http://localhost:8000/simulate-error
```

### Simulate Alarm Testing

To test CloudWatch alarms:

1. **Generate error spike**:
   ```bash
   for i in {1..6}; do
     curl http://localhost:8000/nonexistent
     sleep 1
   done
   ```

2. **Check CloudWatch**:
   - Go to AWS CloudWatch Console
   - Check "Alarms" section
   - Look for `LCopilot-HighErrorRate` alarm

3. **Verify SNS notification**:
   - Check email for alarm notification
   - Should arrive within 1-2 minutes

## 🔧 Troubleshooting

### Common Issues

#### 1. CloudWatch Logs Not Appearing

**Symptoms**: Logs not visible in CloudWatch console

**Solutions**:
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify log group exists
aws logs describe-log-groups --log-group-name-prefix lcopilot-backend

# Check IAM permissions for CloudWatch Logs
# Required: logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents
```

#### 2. Health Checks Failing

**Symptoms**: `/health/ready` returns 503

**Solutions**:
```bash
# Check database connection
psql $DATABASE_URL -c "SELECT 1"

# Verify S3 bucket access
aws s3 ls s3://your-bucket-name

# Test Document AI
python -c "
from google.cloud import documentai
client = documentai.DocumentProcessorServiceClient()
print('Document AI client created successfully')
"
```

#### 3. Request IDs Not Generated

**Symptoms**: Missing `X-Request-ID` headers

**Solutions**:
- Ensure `RequestIDMiddleware` is registered first
- Check middleware order in `main.py`
- Verify imports are correct

#### 4. Structured Logs Not JSON

**Symptoms**: Logs appear as plain text

**Solutions**:
- Check `ENVIRONMENT=production` is set
- Verify `structlog` is installed correctly
- Check logger configuration in `logger.py`

### Debugging Commands

```bash
# Check log format
tail -f /var/log/lcopilot.log | head -1 | python -m json.tool

# Test logger directly
python -c "
from app.utils.logger import get_logger
logger = get_logger('test')
logger.info('Test message', field='value')
"

# Check health endpoint locally
curl -v http://localhost:8000/health/ready | python -m json.tool

# Verify CloudWatch setup
python setup_cloudwatch.py
```

### Performance Considerations

- **Log Level**: Use INFO+ in production (avoid DEBUG)
- **Batch Size**: CloudWatch batches up to 100 log entries
- **Rate Limits**: CloudWatch has API rate limits (~5 requests/second)
- **Costs**: CloudWatch logs are charged per GB ingested and stored

## 📊 Monitoring Best Practices

### Log Levels

- **DEBUG**: Detailed information for diagnosing problems
- **INFO**: General information about application flow
- **WARNING**: Something unexpected happened but application continues
- **ERROR**: Serious problem occurred, function couldn't complete
- **CRITICAL**: Very serious error, application may crash

### What to Log

**✅ Do Log**:
- API requests/responses with duration
- Database operations with timing
- External service calls (S3, Document AI)
- Authentication events
- Business logic errors
- Performance metrics

**❌ Don't Log**:
- Passwords or secret keys
- Credit card numbers
- Personal identification numbers
- Full request/response bodies (unless sanitized)
- High-frequency debug information in production

### Alert Thresholds

- **Error Rate**: > 5 errors per minute
- **Critical Errors**: ≥ 1 critical error per minute
- **Response Time**: > 5 seconds for 95th percentile
- **Health Check**: 3 consecutive failures

## 🔗 Related Resources

- [AWS CloudWatch Logs Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/)
- [Structlog Documentation](https://www.structlog.org/)
- [FastAPI Middleware Guide](https://fastapi.tiangolo.com/tutorial/middleware/)
- [Kubernetes Health Checks](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

---

**🆘 Need Help?**

If you encounter issues with the monitoring setup:

1. Check this troubleshooting guide first
2. Run the test suite: `python test_monitoring.py`
3. Verify AWS credentials and permissions
4. Check application logs for error messages
5. Consult the CloudWatch console for alarm states

**⚡ Quick Health Check**: `curl http://localhost:8000/health/live`