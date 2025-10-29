# 🚨 Multi-Environment CloudWatch Alarm Setup Guide

## Overview

This guide covers three parallel approaches to implementing multi-environment CloudWatch monitoring for LCopilot API:

- **Python Scripts**: Enhanced for staging/prod environment support
- **Terraform**: Infrastructure as Code module
- **AWS CDK**: Python-based Infrastructure as Code stack

All approaches create environment-specific alarms that trigger when your LCopilot API experiences high error rates (≥5 errors within 1 minute for prod, ≥3 for staging).

## Resource Naming Convention

| Resource Type | Staging | Production |
|---------------|---------|------------|
| **Alarm** | `lcopilot-error-spike-staging` | `lcopilot-error-spike-prod` |
| **Metric** | `LCopilot/LCopilotErrorCount-staging` | `LCopilot/LCopilotErrorCount-prod` |
| **Log Group** | `/aws/lambda/lcopilot-staging` | `/aws/lambda/lcopilot-prod` |
| **SNS Topic** | `lcopilot-alerts-staging` | `lcopilot-alerts-prod` |

## Prerequisites

### Common Requirements
1. **AWS Credentials**: Properly configured AWS access
2. **Environment Separation**: Staging and production AWS resources
3. **AWS Permissions**: CloudWatch, SNS, and CloudFormation access

### Python Scripts
1. **Environment Configuration**: `.env.production` with AWS credentials
2. **Dependencies**: `pip install boto3 python-dotenv requests`

### Terraform
1. **Terraform**: Version >= 1.0 installed
2. **AWS Provider**: Version ~> 5.0

### AWS CDK
1. **Node.js**: For CDK CLI
2. **CDK CLI**: `npm install -g aws-cdk`
3. **Python Dependencies**: `pip install aws-cdk-lib constructs`

## Quick Setup

### 1. Python Scripts (Enhanced for Multi-Environment)

```bash
# Production (default)
python3 setup_alarm.py
python3 verify_alarm.py

# Staging environment
python3 setup_alarm.py --env staging
python3 verify_alarm.py --env staging

# Production explicit
python3 setup_alarm.py --env prod
python3 verify_alarm.py --env prod
```

### 2. Terraform

```bash
# Initialize Terraform
cd terraform
terraform init

# Production deployment
terraform apply -var="environment=prod"

# Staging deployment
terraform apply -var="environment=staging"

# View resources
terraform output
```

### 3. AWS CDK

```bash
# Setup
cd cdk
pip install -r requirements.txt

# Production deployment
cdk deploy --context env=prod

# Staging deployment
cdk deploy --context env=staging

# View resources
cdk ls
cdk diff --context env=staging
```

## Expected Output

### Python Scripts - Successful Setup (Staging)
```
🚀 LCopilot CloudWatch Alarm Setup [STAGING]
==================================================
Environment: staging
Timestamp: 2024-01-15 14:30:25
==================================================
✅ Environment loaded successfully
✅ AWS clients initialized
✅ Found SNS topic: arn:aws:sns:eu-north-1:123456789012:lcopilot-alerts-staging
✅ Alarm created/updated successfully: lcopilot-error-spike-staging
Alarm ARN: arn:aws:cloudwatch:eu-north-1:123456789012:alarm:lcopilot-error-spike-staging
✅ Alarm verification successful

🎉 CloudWatch Alarm Setup Complete!
```

### Python Scripts - Verification Output (Production)
```
🔍 LCopilot CloudWatch Alarm Verification [PROD]
==================================================
Environment: prod
Timestamp: 2024-01-15 14:35:10
Region: eu-north-1
==================================================
✅ Alarm found: lcopilot-error-spike-prod
✅ Namespace: LCopilot
✅ MetricName: LCopilotErrorCount-prod
✅ Threshold: 5.0
✅ SNS Topic: arn:aws:sns:eu-north-1:123456789012:lcopilot-alerts-prod

🎉 Alarm verification successful!
```

### Terraform - Successful Apply
```
terraform apply -var="environment=staging"

Plan: 5 to add, 0 to change, 0 to destroy.

aws_cloudwatch_log_group.lcopilot: Creating...
aws_sns_topic.lcopilot_alerts: Creating...
aws_cloudwatch_log_metric_filter.error_count: Creating...
aws_cloudwatch_metric_alarm.error_spike: Creating...

Apply complete! Resources: 5 added, 0 changed, 0 destroyed.

Outputs:

alarm_name = "lcopilot-error-spike-staging"
sns_topic_arn = "arn:aws:sns:eu-north-1:123456789012:lcopilot-alerts-staging"
environment = "staging"
```

### AWS CDK - Successful Deploy
```
cdk deploy --context env=staging

✨  Synthesis time: 3.42s

LCopilotMonitoring-Staging: deploying...
✅  LCopilotMonitoring-Staging

✨  Deployment time: 45.67s

Outputs:
LCopilotMonitoring-Staging.AlarmName = lcopilot-error-spike-staging
LCopilotMonitoring-Staging.SnsTopicArn = arn:aws:sns:eu-north-1:123456789012:lcopilot-alerts-staging
LCopilotMonitoring-Staging.MonitoringSummary = Environment: staging | Alarm: lcopilot-error-spike-staging | Threshold: ≥3 errors

Stack ARN:
arn:aws:cloudformation:eu-north-1:123456789012:stack/LCopilotMonitoring-Staging/12345678-1234-1234-1234-123456789012
```

## Environment-Specific Configuration

### Production Environment
| Setting | Value | Description |
|---------|-------|-------------|
| **Threshold** | `≥ 5` | Higher threshold for production |
| **Period** | `60 seconds` | 1-minute evaluation window |
| **Log Retention** | `30 days` | Longer retention for production |
| **Evaluation** | `1 period` | Triggers immediately |
| **Missing Data** | `notBreaching` | Treats missing data as OK |

### Staging Environment
| Setting | Value | Description |
|---------|-------|-------------|
| **Threshold** | `≥ 3` | Lower threshold for early detection |
| **Period** | `60 seconds` | Same evaluation window |
| **Log Retention** | `7 days` | Shorter retention for staging |
| **Evaluation** | `1 period` | Triggers immediately |
| **Missing Data** | `notBreaching` | Treats missing data as OK |

## Testing Multi-Environment Alarms

### Test Production Environment
```bash
# 1. Start API in production mode
ENVIRONMENT=production python3 main.py

# 2. Trigger 6 errors (above prod threshold of 5)
curl "http://localhost:8000/debug/spam-errors?count=6"

# 3. Wait 1-2 minutes and check alarm state
python3 verify_alarm.py --env prod
python3 cloudwatch_alert_test.py --env prod

# 4. Check your email/Slack for prod SNS notifications
```

### Test Staging Environment
```bash
# 1. Start API in staging mode
ENVIRONMENT=staging python3 main.py

# 2. Trigger 4 errors (above staging threshold of 3)
curl "http://localhost:8000/debug/spam-errors?count=4"

# 3. Wait 1-2 minutes and check alarm state
python3 verify_alarm.py --env staging
python3 cloudwatch_alert_test.py --env staging

# 4. Check your email/Slack for staging SNS notifications
```

### Cross-Environment Verification
```bash
# Test both environments in sequence
python3 setup_alarm.py --env staging
python3 setup_alarm.py --env prod
python3 verify_alarm.py --env staging
python3 verify_alarm.py --env prod
```

## Troubleshooting

### Common Issues

#### 1. Environment-Specific SNS Topic Not Found
```
❌ SNS topic 'lcopilot-alerts-staging' not found
```

**Solutions**:

**Python/Manual**:
```bash
# Create staging topic
aws sns create-topic --name lcopilot-alerts-staging --region eu-north-1

# Create production topic
aws sns create-topic --name lcopilot-alerts-prod --region eu-north-1
```

**Terraform**:
```bash
# Topics are created automatically
terraform apply -var="environment=staging"
```

**CDK**:
```bash
# Topics are created automatically
cdk deploy --context env=staging
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

#### 3. Wrong Environment Resources
```
❌ Alarm 'lcopilot-error-spike' not found when using --env staging
```

**Solution**: Ensure you're targeting the correct environment:
```bash
# Create staging resources first
python3 setup_alarm.py --env staging

# Then verify staging
python3 verify_alarm.py --env staging
```

## Multi-Environment Deployment Comparison

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **Python Scripts** | Simple, Direct control | Manual process | Development, Testing |
| **Terraform** | Mature IaC, Version control | HCL learning curve | Production deployments |
| **AWS CDK** | Type-safe, Familiar syntax | CDK-specific knowledge | Python teams |

## Advanced Usage Examples

### Deploy All Environments with Terraform
```bash
cd terraform

# Deploy both environments
terraform workspace new staging
terraform apply -var="environment=staging"

terraform workspace new prod
terraform apply -var="environment=prod"

# List workspaces
terraform workspace list
```

### Deploy All Environments with CDK
```bash
cd cdk

# Deploy both environments
cdk deploy --context env=staging
cdk deploy --context env=prod

# Destroy staging when not needed
cdk destroy --context env=staging
```

### Cross-Environment Consistency Check
```bash
# Verify both environments match expected configuration
python3 verify_alarm.py --env staging
python3 verify_alarm.py --env prod

# Compare Terraform outputs
terraform output -json > staging.json -var="environment=staging"
terraform output -json > prod.json -var="environment=prod"
```

## Multi-Environment Monitoring Status

### Production Environment
| Component | Status | Resource Name |
|-----------|--------|---------------|
| **Log Group** | ✅ Exists | `/aws/lambda/lcopilot-prod` |
| **Metric Filter** | ✅ Active | `LCopilotErrorCount-prod` |
| **Alarm** | ✅ Created | `lcopilot-error-spike-prod` |
| **SNS Topic** | ✅ Connected | `lcopilot-alerts-prod` |

### Staging Environment
| Component | Status | Resource Name |
|-----------|--------|---------------|
| **Log Group** | ✅ Exists | `/aws/lambda/lcopilot-staging` |
| **Metric Filter** | ✅ Active | `LCopilotErrorCount-staging` |
| **Alarm** | ✅ Created | `lcopilot-error-spike-staging` |
| **SNS Topic** | ✅ Connected | `lcopilot-alerts-staging` |

## Implementation Consistency Verification

All three approaches (Python, Terraform, CDK) should produce identical AWS resources:

```bash
# List alarms to verify naming consistency
aws cloudwatch describe-alarms --region eu-north-1 --query 'MetricAlarms[?contains(AlarmName, `lcopilot`)].AlarmName'

# Expected output:
# [
#   "lcopilot-error-spike-staging",
#   "lcopilot-error-spike-prod"
# ]

# List SNS topics to verify naming consistency
aws sns list-topics --region eu-north-1 --query 'Topics[?contains(TopicArn, `lcopilot`)].TopicArn'

# Expected output:
# [
#   "arn:aws:sns:eu-north-1:123456789012:lcopilot-alerts-staging",
#   "arn:aws:sns:eu-north-1:123456789012:lcopilot-alerts-prod"
# ]
```

## Related Scripts (All Enhanced for Multi-Env)
- `setup_alarm.py --env {staging|prod}` - Creates environment-specific alarms
- `verify_alarm.py --env {staging|prod}` - Verifies environment-specific configuration
- `cloudwatch_alert_test.py --env {staging|prod}` - Tests environment-specific pipeline

## Next Steps

After successful multi-environment alarm setup:

1. **Environment-Specific SNS Subscriptions**:
   - Configure `lcopilot-alerts-staging` for dev team notifications
   - Configure `lcopilot-alerts-prod` for ops team and PagerDuty

2. **Test Both Environments**: Verify staging alerts don't spam production channels

3. **Environment Dashboards**: Create separate CloudWatch dashboards per environment

4. **Environment-Specific Runbooks**: Document different response procedures for staging vs production alerts

5. **Automated Deployment**: Integrate Terraform/CDK into CI/CD pipeline for consistent deployments

6. **Cross-Environment Testing**: Validate that errors in one environment don't trigger alarms in another

## Production Notes

- **State**: Alarms start in `INSUFFICIENT_DATA` state (normal)
- **First Trigger**: Will change to `ALARM` when threshold is breached
- **Reset**: Returns to `OK` when error rate drops below threshold
- **Environment Isolation**: Staging and production alarms are completely independent
- **Notifications**: SNS sends alerts on state changes (`OK` → `ALARM` → `OK`)
- **Thresholds**: Different thresholds per environment allow for environment-appropriate alerting