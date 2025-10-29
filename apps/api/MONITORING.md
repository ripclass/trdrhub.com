# 🔍 LCopilot API Monitoring and CloudWatch Setup

## Overview

The LCopilot API includes comprehensive structured logging and CloudWatch integration for production monitoring, error tracking, and alerting.

## CloudWatch Logging

### Configuration

CloudWatch logging is **automatically enabled** in production mode when:
- `ENVIRONMENT=production` is set
- AWS credentials are configured in `.env.production`
- The `watchtower` package is installed

```bash
# Environment variables required
ENVIRONMENT=production
AWS_REGION=eu-north-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### Log Groups and Streams

- **Log Group**: `lcopilot-backend`
- **Log Stream**: `{hostname}-{environment}` (e.g., `users-iMac.local-production`)
- **Format**: Structured JSON with request correlation

### Disabling CloudWatch

To disable CloudWatch logging:
1. Set `ENVIRONMENT=development`
2. Or remove AWS credentials from environment
3. Logs will only go to console (structured JSON in production, colorized in development)

## Debug Endpoints for Testing

The API includes debug endpoints for testing monitoring and alerting:

| Endpoint | Purpose | CloudWatch Impact |
|----------|---------|-------------------|
| `/debug/error` | Generate single ERROR log | +1 to LCopilotErrorCount |
| `/debug/spam-errors?count=N` | Generate N error logs | +N to LCopilotErrorCount |
| `/debug/warning` | Generate WARNING log | No alarm trigger |
| `/debug/critical` | Generate CRITICAL log | +1 to LCopilotCriticalErrorCount |
| `/debug/slow` | Simulate 6-second request | +1 to LCopilotSlowRequestCount |
| `/debug/test-metrics` | Trigger all metric filters | All metrics increment |

### Testing CloudWatch Alarms

```bash
# Start the API
ENVIRONMENT=production python3 main.py

# Trigger single error (no alarm)
curl http://localhost:8000/debug/error

# Trigger alarm (5+ errors in 1 minute)
curl "http://localhost:8000/debug/spam-errors?count=6"

# Check logs in AWS Console after 1-2 minutes
# Location: CloudWatch → Log groups → lcopilot-backend
```

## Structured Logging Format

All logs are structured JSON with these standard fields:

```json
{
  "timestamp": "2025-09-13T09:43:30.588Z",
  "level": "ERROR",
  "service": "lcopilot-api",
  "environment": "production",
  "hostname": "users-iMac.local",
  "message": "...",
  "module": "lcopilot-api",
  "request_id": "02d7461d-325c-4428-875d-1e20d41d50b5",
  "endpoint": "/debug/spam-errors",
  "error_type": "spam_test_error"
}
```

## CloudWatch Metric Filters

Metric filters automatically extract metrics from structured logs:

| Metric Filter | Pattern | Metric Name |
|---------------|---------|-------------|
| LCopilotErrorFilter | `{ $.level = "ERROR" }` | LCopilotErrorCount |
| LCopilotCriticalFilter | `{ $.level = "CRITICAL" }` | LCopilotCriticalErrorCount |
| LCopilotSlowRequestFilter | `{ $.request_duration_ms > 5000 }` | LCopilotSlowRequestCount |
| LCopilot5xxFilter | `{ $.http_status_code >= 500 }` | LCopilot5xxErrorCount |

## CloudWatch Alarms

Alarms trigger based on metric thresholds:

| Alarm | Condition | Notification |
|-------|-----------|-------------|
| LCopilot-HighErrorRate | ≥ 5 errors in 1 minute | SNS alert |
| LCopilot-CriticalErrors | ≥ 1 critical error in 1 minute | SNS alert |
| LCopilot-SlowRequests | ≥ 3 slow requests in 5 minutes | SNS alert |

## Health Endpoints

Monitor service health:

- `/health/live` - Liveness probe (always returns 200)
- `/health/ready` - Readiness probe (checks database, S3, etc.)
- `/health/info` - Service information and configuration

## Request Correlation

Every request gets a unique UUID4 request ID:
- Added to all log entries
- Returned in `X-Request-ID` header
- Allows tracing requests across the application

## Production Setup

1. **Configure Environment**:
   ```bash
   cp .env .env.production
   # Edit .env.production with production values
   ```

2. **Set up CloudWatch Resources**:
   ```bash
   python3 setup_cloudwatch.py
   ```

3. **Test CloudWatch**:
   ```bash
   python3 cloudwatch_smoketest.py
   ```

4. **Start with CloudWatch**:
   ```bash
   ENVIRONMENT=production python3 main.py
   ```

## Local Development

For local development, CloudWatch is disabled:
- Logs go to console only
- Colorized output for better readability
- No AWS credentials required

```bash
# Development mode (default)
python3 main.py
```

## Troubleshooting

### CloudWatch Not Working

Check these common issues:

1. **Environment**: Ensure `ENVIRONMENT=production`
2. **Credentials**: Verify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
3. **Region**: Confirm AWS_REGION matches your CloudWatch region
4. **Log Group**: Ensure `lcopilot-backend` log group exists
5. **Permissions**: IAM user needs CloudWatch Logs permissions

### Testing Locally

Use the smoke test script to verify setup:

```bash
# Test CloudWatch connectivity
python3 cloudwatch_smoketest.py

# Expected output:
✅ AWS credentials verified
✅ CloudWatch Logs client created
✅ Test log event sent successfully
✅ Production log group accessible
```

## Logs Location

**AWS Console**:
`https://eu-north-1.console.aws.amazon.com/cloudwatch/home?region=eu-north-1#logsV2:log-groups/log-group/lcopilot-backend`

Replace `eu-north-1` with your actual AWS region.