# 🐛 LCopilot Debug Endpoints for CloudWatch Testing

## 🎯 Quick Start

**Start the API server:**
```bash
cd apps/api
python main.py
```

**Test single error:**
```bash
curl http://localhost:8000/debug/error
```

**Trigger CloudWatch alarm (5+ errors):**
```bash
curl "http://localhost:8000/debug/spam-errors?count=10"
```

---

## 📋 Available Debug Endpoints

### 1. Single Error - `/debug/error`
- **Method**: GET
- **Purpose**: Generate single ERROR log for CloudWatch metric testing
- **Response**: HTTP 500 with `{"detail": "Simulated error"}`
- **CloudWatch**: Increments `LCopilotErrorCount` metric

```bash
curl http://localhost:8000/debug/error
```

### 2. Spam Errors - `/debug/spam-errors`
- **Method**: GET
- **Purpose**: Generate multiple ERROR logs to trigger CloudWatch alarms
- **Parameters**: `count` (default: 5, max: 20)
- **Response**: HTTP 500 with `{"detail": "Generated X errors for testing"}`
- **CloudWatch**: Triggers `LCopilot-HighErrorRate` alarm when count ≥ 5

```bash
# Default (5 errors - triggers alarm)
curl http://localhost:8000/debug/spam-errors

# Custom count (10 errors)
curl "http://localhost:8000/debug/spam-errors?count=10"

# Minimal (3 errors - won't trigger alarm)
curl "http://localhost:8000/debug/spam-errors?count=3"
```

### 3. Warning Log - `/debug/warning`
- **Method**: GET
- **Purpose**: Generate WARNING level log (separate from errors)
- **Response**: HTTP 200 with success message
- **CloudWatch**: Can be tracked with separate WARNING metric filter

```bash
curl http://localhost:8000/debug/warning
```

---

## 📊 CloudWatch Integration

### Metric Filters That Will Trigger:

| Endpoint | Log Level | Metric Filter | Metric Name |
|----------|-----------|---------------|-------------|
| `/debug/error` | ERROR | `{ $.level = "ERROR" }` | `LCopilotErrorCount` |
| `/debug/spam-errors` | ERROR | `{ $.level = "ERROR" }` | `LCopilotErrorCount` |
| `/debug/warning` | WARNING | `{ $.level = "WARNING" }` | `LCopilotWarningCount`* |

*Note: WARNING metric filter needs to be created separately*

### CloudWatch Alarms:

| Alarm Name | Condition | Trigger Endpoint |
|------------|-----------|------------------|
| `LCopilot-HighErrorRate` | ≥ 5 errors in 1 minute | `/debug/spam-errors` (count≥5) |
| `LCopilot-CriticalErrors` | ≥ 1 critical in 1 minute | `/debug/critical` |

---

## 🧪 Testing Scenarios

### Scenario 1: Single Error Test
```bash
# Generate one error
curl http://localhost:8000/debug/error

# Expected: LCopilotErrorCount += 1
# No alarm (below threshold)
```

### Scenario 2: Alarm Trigger Test
```bash
# Generate 5+ errors to trigger alarm
curl "http://localhost:8000/debug/spam-errors?count=6"

# Expected:
# - LCopilotErrorCount += 6
# - LCopilot-HighErrorRate alarm triggers
# - SNS notification sent (if configured)
```

### Scenario 3: Warning Level Test
```bash
# Generate warning (no alarm)
curl http://localhost:8000/debug/warning

# Expected: WARNING level log
# No error count increment
```

### Scenario 4: Mixed Testing
```bash
# Test multiple types
curl http://localhost:8000/debug/warning
curl http://localhost:8000/debug/error
curl "http://localhost:8000/debug/spam-errors?count=5"

# Expected: Mixed log levels, alarm triggers
```

---

## 📈 Monitoring Results

### 1. Check Logs Locally
- Logs appear immediately in console
- Look for `"level": "ERROR"` in JSON output

### 2. Check CloudWatch Logs
- **Location**: AWS Console → CloudWatch → Log groups → `lcopilot-backend`
- **Stream**: `{hostname}-{environment}`
- **Timing**: Logs appear within 1-2 minutes

### 3. Check CloudWatch Metrics
- **Location**: AWS Console → CloudWatch → Metrics → `LCopilot/API`
- **Metric**: `LCopilotErrorCount`
- **Timing**: Metrics update within 1-2 minutes

### 4. Check CloudWatch Alarms
- **Location**: AWS Console → CloudWatch → Alarms
- **Alarm**: `LCopilot-HighErrorRate`
- **Timing**: Alarm triggers within 1-2 minutes of threshold breach

### 5. Check SNS Notifications
- **Location**: Email inbox (if SNS email subscription configured)
- **Subject**: Contains "LCopilot-HighErrorRate"
- **Timing**: Email arrives within 2-3 minutes of alarm trigger

---

## 🔧 Production Usage

### Environment Variables Required:
```bash
ENVIRONMENT=production          # Enables CloudWatch logging
AWS_REGION=eu-north-1          # Your AWS region
AWS_ACCESS_KEY_ID=your-key     # CloudWatch access
AWS_SECRET_ACCESS_KEY=your-secret  # CloudWatch access
```

### CloudWatch Resources Required:
- Log group: `lcopilot-backend`
- Metric filters: `LCopilotErrorFilter`, `LCopilotCriticalFilter`
- Alarms: `LCopilot-HighErrorRate`, `LCopilot-CriticalErrors`
- SNS topic: `lcopilot-alerts`

### Setup CloudWatch (if not done):
```bash
cd apps/api
python setup_cloudwatch.py
```

---

## 🚨 Safety Notes

- **Rate Limiting**: `/debug/spam-errors` limited to max 20 errors to prevent log spam
- **Production Use**: These endpoints should be removed or secured in production
- **Cost Impact**: High volume testing may incur CloudWatch logging costs
- **Alarm Fatigue**: Repeated testing may trigger multiple SNS notifications

---

## 💡 Additional Metric Filters

To track WARNING logs separately, create this metric filter:

```json
{
  "filterName": "LCopilotWarningFilter",
  "filterPattern": "{ $.level = \"WARNING\" }",
  "metricTransformations": [
    {
      "metricName": "LCopilotWarningCount",
      "metricNamespace": "LCopilot/API",
      "metricValue": "1",
      "defaultValue": 0
    }
  ]
}
```

Then track warnings with `/debug/warning` endpoint! 📊