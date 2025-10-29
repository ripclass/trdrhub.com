# 🚨 CloudWatch Alarm Setup Guide

## Overview

The `setup_alarm.py` script creates a production-ready CloudWatch alarm that triggers when your LCopilot API experiences high error rates (≥5 errors within 1 minute).

## Prerequisites

1. **Environment Configuration**: `.env.production` with AWS credentials
2. **SNS Topic**: `lcopilot-alerts` topic must exist
3. **AWS Permissions**: CloudWatch and SNS access

## Quick Setup

```bash
# Create the alarm
python3 setup_alarm.py

# Verify it was created correctly
python3 verify_alarm.py
```

## Expected Output

### Successful Setup
```
🚀 LCopilot CloudWatch Alarm Setup
==================================================
✅ Environment loaded successfully
✅ AWS clients initialized
✅ Found SNS topic: arn:aws:sns:eu-north-1:123456789012:lcopilot-alerts
✅ Alarm created/updated successfully: lcopilot-error-spike
Alarm ARN: arn:aws:cloudwatch:eu-north-1:123456789012:alarm:lcopilot-error-spike
✅ Alarm verification successful

🎉 CloudWatch Alarm Setup Complete!
```

### Verification Output
```
🔍 LCopilot CloudWatch Alarm Verification
==================================================
✅ Alarm found: lcopilot-error-spike
✅ Namespace: LCopilot
✅ MetricName: LCopilotErrorCount
✅ Threshold: 5.0
✅ SNS Topic: arn:aws:sns:eu-north-1:123456789012:lcopilot-alerts

🎉 Alarm verification successful!
```

## Alarm Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| **Name** | `lcopilot-error-spike` | Alarm identifier |
| **Metric** | `LCopilot/LCopilotErrorCount` | Error count metric |
| **Threshold** | `≥ 5` | Triggers when 5 or more errors |
| **Period** | `60 seconds` | 1-minute evaluation window |
| **Evaluation** | `1 period` | Triggers immediately |
| **Missing Data** | `notBreaching` | Treats missing data as OK |
| **Actions** | SNS notification | Sends alert to `lcopilot-alerts` |

## Testing the Alarm

Once set up, test the alarm:

```bash
# 1. Start the API in production mode
ENVIRONMENT=production python3 main.py

# 2. Trigger 6 errors (above threshold)
curl "http://localhost:8000/debug/spam-errors?count=6"

# 3. Wait 1-2 minutes and check alarm state
python3 verify_alarm.py

# 4. Check your email/Slack for SNS notification
```

## Troubleshooting

### Common Issues

#### 1. SNS Topic Not Found
```
❌ SNS topic 'lcopilot-alerts' not found
```

**Solution**: Create the SNS topic first:
```bash
aws sns create-topic --name lcopilot-alerts --region eu-north-1
```

#### 2. AWS Credentials Missing
```
❌ Missing required environment variables: ['AWS_ACCESS_KEY_ID']
```

**Solution**: Check `.env.production` contains:
```
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=eu-north-1
```

#### 3. Insufficient Permissions
```
❌ AWS client initialization failed: Access Denied
```

**Solution**: Ensure IAM user has these permissions:
- `cloudwatch:PutMetricAlarm`
- `cloudwatch:DescribeAlarms`
- `sns:ListTopics`
- `sts:GetCallerIdentity`

## Script Features

### `setup_alarm.py`
- ✅ **Environment Loading**: Loads from `.env.production`
- ✅ **AWS Client Init**: Proper region and credential handling
- ✅ **SNS Discovery**: Automatically finds topic ARN
- ✅ **Idempotent**: Safe to run multiple times
- ✅ **Verification**: Confirms alarm was created correctly
- ✅ **Error Handling**: Clear error messages and solutions

### `verify_alarm.py`
- ✅ **Configuration Check**: Validates all alarm settings
- ✅ **SNS Verification**: Confirms topic attachment
- ✅ **Status Display**: Shows current alarm state
- ✅ **Detailed Output**: Lists all configuration values

## Integration Workflow

This alarm integrates with the complete monitoring pipeline:

```
API Errors → CloudWatch Logs → Metric Filter → Alarm → SNS → Email/Slack
```

### Related Scripts
- `verify_cloudwatch_full.py` - Verifies logs and metrics are flowing
- `cloudwatch_alert_test.py` - End-to-end monitoring pipeline test
- `setup_cloudwatch.py` - Creates log groups and metric filters

### Monitoring Chain Status

After running `setup_alarm.py`, your monitoring status should be:

| Component | Status | Script |
|-----------|--------|--------|
| **Log Group** | ✅ Exists | `setup_cloudwatch.py` |
| **Metric Filter** | ✅ Active | `setup_cloudwatch.py` |
| **Alarm** | ✅ Created | `setup_alarm.py` ← **This script** |
| **SNS Topic** | ✅ Connected | `setup_alarm.py` |

## Production Notes

- **State**: Alarm starts in `INSUFFICIENT_DATA` state (normal)
- **First Trigger**: Will change to `ALARM` when threshold is breached
- **Reset**: Returns to `OK` when error rate drops below threshold
- **Notifications**: SNS sends alerts on state changes (`OK` → `ALARM` → `OK`)

## Next Steps

After successful alarm setup:

1. **Configure SNS Subscriptions**: Add email/Slack endpoints to the topic
2. **Test Notifications**: Verify alerts reach your team
3. **Monitor Dashboard**: Create CloudWatch dashboard for visualization
4. **Document Runbook**: Create incident response procedures