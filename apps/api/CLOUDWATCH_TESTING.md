# 🧪 CloudWatch Alert Testing Guide

## Overview

The `cloudwatch_alert_test.py` script validates your entire CloudWatch monitoring pipeline from API errors to SNS notifications.

## Prerequisites

1. **API Server Running**:
   ```bash
   ENVIRONMENT=production python3 main.py
   ```

2. **CloudWatch Infrastructure**:
   - Log group: `lcopilot-backend`
   - Metric filter: `LCopilotErrorCount` (namespace: `LCopilot`)
   - Alarm: `lcopilot-error-spike` (threshold: ≥5 errors in 1 minute)
   - SNS topic with email/Slack subscription

3. **Environment Configuration**:
   ```bash
   # .env.production must contain:
   AWS_ACCESS_KEY_ID=your-key
   AWS_SECRET_ACCESS_KEY=your-secret
   AWS_REGION=eu-north-1
   ```

## Running the Test

### Basic Test (Default 6 errors)
```bash
python3 cloudwatch_alert_test.py
```

### Custom Configuration
```bash
# Trigger 8 errors
python3 cloudwatch_alert_test.py --count 8

# Longer timeout (10 minutes)
python3 cloudwatch_alert_test.py --timeout 600

# Different API URL
python3 cloudwatch_alert_test.py --api-url http://your-api.com
```

## Expected Output Flow

```
🚀 LCopilot CloudWatch Alert Validation
==================================================
🔧 Loading environment from .env.production...
✅ Environment loaded successfully

☁️ Initializing AWS clients...
✅ AWS clients initialized
   Account: 848566117223
   Region: eu-north-1
   User/Role: lcopilot-api

🚨 Triggering 6 spam errors on API...
✅ Triggered 6 spam errors on API
   Response: Generated 6 errors for testing

⏳ Waiting for metric datapoint...
   Checking for metric datapoint... (attempt 1)
   Checking for metric datapoint... (attempt 2)
✅ Metric datapoint detected!
   Metric: LCopilot/LCopilotErrorCount
   Value: 6.0
   Timestamp: 2025-09-13T10:45:00Z

⏳ Waiting for alarm 'lcopilot-error-spike' to trigger...
   Checking alarm status... (attempt 1)
   Alarm state: OK
   Checking alarm status... (attempt 2)
   Alarm state: ALARM
✅ Alarm triggered: lcopilot-error-spike
   State: ALARM
   Reason: Threshold Crossed: 6 datapoints [6.0] greater than threshold (5.0)

📩 SNS Notification Check:
   Check your email/Slack subscription to confirm SNS notification arrived
   Expected: Email with subject containing 'lcopilot-error-spike'

⏳ Waiting for alarm 'lcopilot-error-spike' to reset...
   Checking alarm reset... (attempt 1)
   Alarm state: ALARM
   ... (continues until OK or timeout)
✅ Alarm reset to OK
   Reason: No data for alarm

==================================================
📊 CLOUDWATCH ALERT VALIDATION RESULTS
==================================================
✅ API error injection successful
✅ Metric datapoint detected: value=6.0
✅ Alarm triggered successfully
✅ SNS notification should have been sent
✅ Alarm reset to OK

🎉 CloudWatch alert validation completed successfully!
⏱️  Total validation time: 127.3 seconds
```

## Troubleshooting

### Common Issues

#### 1. API Connection Failed
```
❌ Failed to connect to API at http://localhost:8000
   Make sure the API server is running: ENVIRONMENT=production python3 main.py
```

**Solution**: Start the API server in production mode

#### 2. AWS Credentials Not Found
```
❌ Missing required environment variables: ['AWS_ACCESS_KEY_ID']
```

**Solution**: Check your `.env.production` file has all AWS variables

#### 3. Alarm Not Found
```
❌ Alarm 'lcopilot-error-spike' not found
```

**Solution**: Run `python3 setup_cloudwatch.py` to create CloudWatch resources

#### 4. No Metric Datapoints
```
❌ No datapoints detected within 300 seconds
```

**Possible causes**:
- Metric filter not configured correctly
- CloudWatch logs not flowing (check watchtower configuration)
- Wrong metric namespace/name
- Timing issue (try longer timeout)

#### 5. Alarm Doesn't Trigger
```
❌ Alarm did not trigger within 300 seconds
```

**Possible causes**:
- Alarm threshold too high (check if it's set to ≥5)
- Metric filter not working
- Alarm evaluation period too long
- Wrong metric being monitored

### Manual Verification

If the script fails, you can manually verify each step:

#### 1. Check CloudWatch Logs
```bash
# AWS Console → CloudWatch → Log groups → lcopilot-backend
# Look for recent log entries with "level": "ERROR"
```

#### 2. Check Metrics
```bash
# AWS Console → CloudWatch → Metrics → LCopilot → LCopilotErrorCount
# Should show recent data points
```

#### 3. Check Alarm
```bash
# AWS Console → CloudWatch → Alarms → lcopilot-error-spike
# Check alarm state and history
```

#### 4. Test API Manually
```bash
curl "http://localhost:8000/debug/spam-errors?count=6"
# Should return HTTP 500 with error count
```

## Script Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--count` | 6 | Number of errors to trigger |
| `--timeout` | 300 | Seconds to wait for metrics/alarms |
| `--alarm-reset-timeout` | 600 | Seconds to wait for alarm reset |
| `--api-url` | http://localhost:8000 | API base URL |

## Integration with CI/CD

You can use this script in automated testing:

```bash
# In your deployment pipeline
python3 cloudwatch_alert_test.py --count 8 --timeout 600

# Exit code 0 = success, 1 = failure
if [ $? -eq 0 ]; then
    echo "CloudWatch monitoring validated ✅"
else
    echo "CloudWatch monitoring validation failed ❌"
    exit 1
fi
```

## Performance Notes

- **Timing**: Full validation typically takes 2-5 minutes
- **Rate Limits**: Script respects AWS API rate limits (15-second intervals)
- **Idempotent**: Safe to run multiple times
- **Non-destructive**: Only triggers test errors, no system changes

## Related Files

- `cloudwatch_smoketest.py` - Basic CloudWatch connectivity test
- `setup_cloudwatch.py` - Create CloudWatch infrastructure
- `MONITORING.md` - Complete monitoring system documentation
- `DEBUG_ENDPOINTS.md` - Debug endpoint reference