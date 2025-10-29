# LCopilot Observability & Resilience Stack

Complete enterprise-grade observability and resilience framework for LCopilot API monitoring across staging and production environments.

## 🎯 Overview

This observability stack provides comprehensive monitoring, alerting, and resilience testing capabilities:

- **Environment-scoped dashboards** (CloudWatch + optional Grafana)
- **Synthetic canaries** for golden path monitoring
- **Chaos engineering** with controlled fault injection
- **SLO/SLA reporting** with automated PDF generation
- **Security monitoring** with anomaly detection
- **Advanced log analytics** with cost optimization

## 📁 Architecture

```
apps/api/
├── config/
│   └── enterprise_config.yaml          # Centralized configuration
├── dashboards/
│   └── lcopilot_health_template.json  # CloudWatch dashboard template
├── canaries/
│   └── golden_path_canary.py          # Synthetic monitoring
├── chaos/
│   └── chaos_controller.py            # Fault injection system
├── slo_reporting/
│   └── sla_report_generator.py        # SLA compliance reporting
├── security/
│   └── security_monitor.py            # Security event monitoring
├── utils/
│   ├── dashboard_manager.py           # Dashboard deployment
│   └── log_insights_manager.py        # Advanced log analytics
├── .github/workflows/
│   └── observability-tests.yml        # CI/CD validation
└── verify_observability_stack.py      # Comprehensive verification
```

## 🚀 Quick Start

### 1. Deploy Complete Stack
```bash
# Deploy all observability components
make setup-observability

# Verify deployment
make verify-observability
```

### 2. Individual Component Deployment

#### CloudWatch Dashboards
```bash
# Deploy dashboards to both environments
python3 utils/dashboard_manager.py --env staging --deploy
python3 utils/dashboard_manager.py --env prod --deploy

# Verify dashboard deployment
python3 utils/dashboard_manager.py --env both --verify
```

#### Synthetic Canaries
```bash
# Run canaries for golden path testing
python3 canaries/golden_path_canary.py --env staging --scenario all --publish-metrics

# Run specific scenario
python3 canaries/golden_path_canary.py --env prod --scenario upload_validate_report
```

#### Chaos Engineering
```bash
# Test error spike injection (staging only)
python3 chaos/chaos_controller.py --env staging --fault error_spike --duration 120

# Test latency injection
python3 chaos/chaos_controller.py --env staging --fault latency_injection --duration 300

# Emergency stop all chaos experiments
python3 chaos/chaos_controller.py --env staging --emergency-stop
```

#### SLA Reporting
```bash
# Generate monthly SLA report
python3 slo_reporting/sla_report_generator.py --env prod --month 2024-01 --format html

# Upload to S3
python3 slo_reporting/sla_report_generator.py --env prod --month 2024-01 --upload-s3
```

#### Security Monitoring
```bash
# Create security alarms
python3 security/security_monitor.py --env prod --create-alarms

# Analyze security logs
python3 security/security_monitor.py --env prod --analyze-logs --hours 24
```

## 📊 Dashboard Features

### CloudWatch Dashboard Widgets

| Widget | Description | Metrics |
|--------|-------------|---------|
| **Error Rate** | 1-min and 5-min error rates | `LCopilotErrorCount-{env}` |
| **Alarm Status** | Primary alarm states | `lcopilot-error-spike-{env}` |
| **Canary Success** | Golden path success rate | `CanarySuccessRate-{env}` |
| **Canary Latency** | End-to-end response times | `CanaryLatencyMs-{env}` |
| **Security Events** | Authentication failures | `AuthFailureCount-{env}` |
| **Top Errors** | Log insights query widget | Real-time error analysis |

### Dashboard URLs
- **Staging**: `https://console.aws.amazon.com/cloudwatch/home?region=eu-north-1#dashboards:name=lcopilot-health-staging`
- **Production**: `https://console.aws.amazon.com/cloudwatch/home?region=eu-north-1#dashboards:name=lcopilot-health-prod`

## 🔍 Synthetic Monitoring

### Golden Path Canary Tests

1. **upload_validate_report** (45s timeout)
   - Upload test file
   - Validate file processing
   - Generate report
   - End-to-end flow verification

2. **auth_check** (15s timeout)
   - Authentication endpoint validation
   - Basic connectivity test

### Metrics Published
- `CanarySuccessRate-{env}`: Overall success percentage
- `CanaryLatencyMs-{env}`: End-to-end latency
- `CanaryScenarioDuration-{env}`: Individual scenario timing

### Scheduling
- **Staging**: Every 5 minutes
- **Production**: Every 10 minutes

## 🌪️ Chaos Engineering

### Fault Types

| Fault Type | Description | Duration | Safety |
|------------|-------------|----------|---------|
| **error_spike** | Increase error rate 10x | 120s | Auto-rollback |
| **latency_injection** | Add 500-2000ms delay | 300s | Auto-rollback |
| **log_pipeline_drop** | Simulate log pipeline failure | 60s | Simulation only |

### Safety Controls
- ✅ **Staging**: Allowed by default
- ⚠️ **Production**: Requires `--force` flag
- 🎫 **Change Tickets**: Required for production
- ⏰ **Time Limits**: Max 600 seconds
- 🔄 **Auto-Rollback**: Automatic cleanup

### Feature Flag Control
Chaos experiments use DynamoDB feature flags:
- `CHAOS_ERROR_RATE`: Error rate multiplier
- `CHAOS_LATENCY_MS`: Latency injection range
- `CHAOS_DROP_LOGS`: Log pipeline simulation

## 📈 SLO/SLA Reporting

### SLO Targets

| Environment | Error Rate/Min | Canary Success | P95 Latency | Availability |
|-------------|----------------|----------------|-------------|--------------|
| **Staging** | ≤3 errors/min | ≥95% | ≤30s | ≥99.0% |
| **Production** | ≤5 errors/min | ≥99% | ≤15s | ≥99.9% |

### Report Sections
1. **Executive Summary**: High-level compliance overview
2. **SLO Compliance**: Detailed metric analysis
3. **Incident Timeline**: Alarm history and downtime
4. **Top Errors Analysis**: Most common error types
5. **Performance Trends**: Response time analysis
6. **Recommendations**: Actionable improvements

### Output Formats
- **JSON**: Machine-readable data
- **HTML**: Human-readable reports
- **S3 Upload**: Automated archival

## 🔒 Security Monitoring

### Monitored Events
- Authentication failures
- Brute force attacks
- Geographic anomalies
- IP-based suspicious activity
- High-risk security events

### Anomaly Detection
- **Brute Force**: 10+ failures from same IP in 5 minutes
- **Geographic**: High activity from suspicious countries
- **Volume**: 2x normal authentication failure threshold

### Security Alarms
- `lcopilot-auth-failures-{env}`: Authentication failure spikes
- `lcopilot-suspicious-ips-{env}`: Suspicious IP activity
- `lcopilot-high-risk-security-{env}`: High-risk event aggregation

### Risk Scoring
Events scored 0-100 based on:
- Multiple failed attempts (+30 points)
- Suspicious countries (+25 points)
- Known malicious IPs (+30 points)
- Private IPs (-10 points)

## 📋 Log Analytics

### Predefined Queries

| Query | Description | Cost Optimized |
|-------|-------------|----------------|
| **TopErrorTypes** | Most common errors | ✅ Yes |
| **ErrorFrequency** | Error frequency over time | ✅ Yes |
| **ServiceErrorBreakdown** | Errors by service/component | ✅ Yes |
| **ErrorDetails** | Detailed error information | ❌ No |
| **SecurityEvents** | Authentication/security events | ✅ Yes |
| **PerformanceMetrics** | Response time analysis | ✅ Yes |

### Cost Optimization
- Log filtering for debug messages
- S3 archival after retention period
- Query result caching
- Time-range optimization

## 🔄 CI/CD Integration

### GitHub Workflows

1. **observability-tests.yml**
   - Configuration validation
   - Python syntax checking
   - Component integration testing
   - Multi-environment verification

2. **terraform-plan-apply.yml** (Enhanced)
   - Infrastructure deployment
   - Post-deployment validation
   - Observability component verification

### Makefile Targets

```bash
# Setup
make setup-observability     # Deploy full stack
make deploy-dashboards       # Deploy dashboards only

# Testing
make test-observability      # Comprehensive tests
make run-canaries           # Execute synthetic tests
make test-chaos             # Run chaos experiments

# Monitoring
make verify-observability    # Full stack verification
make security-scan-logs     # Security analysis
make generate-sla-report    # SLA compliance report

# Maintenance
make logs-insights          # Run log analysis
make show-dashboard-urls    # Display dashboard links
```

## 🛠️ Configuration

### Enterprise Configuration (`enterprise_config.yaml`)

```yaml
observability:
  enable_dashboards: true
  dashboards:
    cloudwatch_enabled: true
    grafana_enabled: false
    refresh_interval: 300

  canary:
    enabled: true
    implementation: "lambda"
    schedule_minutes:
      staging: 5
      prod: 10
    api_endpoints:
      staging: "https://api-staging.company.com"
      prod: "https://api.company.com"

chaos:
  allowed_in_prod: false
  allowed_in_staging: true
  fault_types:
    error_spike:
      enabled: true
      duration_seconds: 120
      error_rate_multiplier: 10

slo:
  targets:
    prod:
      error_rate_per_minute: 5
      canary_success_rate: 99
      p95_latency_seconds: 15
      availability_percent: 99.9

security:
  enable_auth_alarms: true
  auth_monitoring:
    failure_threshold:
      prod: 50
    metrics:
      auth_failure_count: "AuthFailureCount-{env}"
```

## 📊 Metrics Reference

### LCopilot Namespace
- `LCopilotErrorCount-{env}`: Application error count
- `CanarySuccessRate-{env}`: Synthetic test success rate
- `CanaryLatencyMs-{env}`: End-to-end latency
- `CanaryScenarioDuration-{env}`: Individual test duration

### LCopilot/Security Namespace
- `AuthFailureCount-{env}`: Authentication failures
- `SuspiciousIPCount-{env}`: Suspicious IP addresses
- `HighRiskSecurityEvents-{env}`: High-risk events
- `SecurityAnomaly-*-{env}`: Anomaly detection results

### LCopilot/Chaos Namespace
- `ChaosExperimentActive`: Active chaos experiments
- Feature flag metrics for experiment control

## 🚨 Alerting

### Alert Routing by Environment

#### Staging
- **Channels**: Slack, Email
- **Escalation**: Development team
- **Response Time**: Best effort

#### Production
- **Channels**: PagerDuty, Slack, Email
- **Escalation**: Ops team, On-call rotation
- **Response Time**: 15-minute SLA

### Alarm Thresholds
- **Error Rate**: Staging ≥3/min, Production ≥5/min
- **Canary Failures**: Success rate <95% (staging), <99% (prod)
- **Security Events**: Staging ≥20/5min, Production ≥50/5min

## 🎯 Best Practices

### Deployment
1. Always test in staging first
2. Verify dashboards after deployment
3. Run canaries to validate golden path
4. Monitor alarms for false positives

### Chaos Engineering
1. Start with staging environment
2. Use short durations (60-120 seconds)
3. Monitor dashboards during experiments
4. Have emergency stop ready
5. Never run chaos in production without approval

### SLA Reporting
1. Generate reports monthly
2. Review trends over time
3. Address recurring issues
4. Update SLO targets based on data

### Security Monitoring
1. Tune thresholds to reduce noise
2. Investigate all high-risk events
3. Review geographic patterns monthly
4. Update IP reputation lists

## 🔧 Troubleshooting

### Common Issues

#### Dashboards Not Loading
```bash
# Verify dashboard exists
python3 utils/dashboard_manager.py --env prod --verify

# Redeploy if missing
python3 utils/dashboard_manager.py --env prod --deploy
```

#### Canaries Failing
```bash
# Check canary configuration
python3 canaries/golden_path_canary.py --env staging --scenario auth_check

# Verify API endpoints are accessible
curl -I https://api-staging.company.com/health
```

#### No Metrics Data
```bash
# Check CloudWatch namespace
aws cloudwatch list-metrics --namespace LCopilot

# Verify metric publishing
python3 verify_observability_stack.py --env staging --check canaries --verbose
```

#### Chaos Experiments Stuck
```bash
# Emergency stop all experiments
python3 chaos/chaos_controller.py --env staging --emergency-stop

# Check active experiments
python3 chaos/chaos_controller.py --env staging --list-active
```

### Log Locations
- **Application Logs**: `/aws/lambda/lcopilot-{env}`
- **API Gateway Logs**: `/aws/apigateway/lcopilot-{env}`
- **Chaos Logs**: DynamoDB feature flags table
- **Security Events**: CloudWatch Logs Insights queries

## 📚 Additional Resources

- [ENTERPRISE_MONITORING_PLAYBOOK.md](ENTERPRISE_MONITORING_PLAYBOOK.md): Detailed operational procedures
- [MULTI_ENV_ALARM_GUIDE.md](MULTI_ENV_ALARM_GUIDE.md): Multi-environment setup guide
- [Terraform Modules](terraform/): Infrastructure as Code
- [CDK Stack](cdk/): AWS CDK implementation
- [GitHub Workflows](.github/workflows/): CI/CD automation

## 🤝 Contributing

1. Test changes in staging environment
2. Run observability tests: `make test-observability`
3. Update documentation for new features
4. Ensure all CI checks pass
5. Get approval for production changes

## 📄 License

Enterprise Internal Use Only - See company licensing terms.