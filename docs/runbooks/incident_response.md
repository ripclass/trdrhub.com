# Incident Response Runbook

## Overview

This runbook provides structured procedures for responding to incidents affecting TRDR Hub services, ensuring rapid resolution and minimal business impact.

## Incident Classification

### Priority Levels

| Priority | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| P1 - Critical | Complete system outage | 15 minutes | Database down, API completely unavailable |
| P2 - High | Significant service degradation | 1 hour | High error rates, major feature unavailable |
| P3 - Medium | Minor service issues | 4 hours | Performance degradation, non-critical feature issues |
| P4 - Low | Cosmetic or documentation issues | 1 business day | UI glitches, documentation errors |

### Service Impact Categories

- **Customer-Facing**: Issues affecting end users directly
- **Internal Systems**: Issues affecting internal operations
- **Data Integrity**: Issues potentially affecting data accuracy
- **Security**: Issues with potential security implications
- **Compliance**: Issues affecting regulatory compliance

## Incident Response Process

### Phase 1: Detection and Initial Response

#### 1.1 Incident Detection Sources

- Monitoring alerts (Prometheus/Grafana)
- Customer reports
- Internal team observations
- Automated health checks
- External monitoring services

#### 1.2 Initial Assessment (Within 5 minutes)

```bash
# Quick system health check
./scripts/health_check.sh

# Check service status
kubectl get pods -n trdrhub-system
docker-compose ps

# Review recent alerts
curl -s "http://alertmanager:9093/api/v1/alerts" | jq '.data[] | select(.state=="active")'
```

#### 1.3 Immediate Actions

1. **Acknowledge the incident** in monitoring system
2. **Assess severity** using the priority matrix
3. **Create incident ticket** with initial details
4. **Notify stakeholders** based on severity level
5. **Assign incident commander** for P1/P2 incidents

### Phase 2: Investigation and Diagnosis

#### 2.1 Information Gathering

```bash
# System resources
top
df -h
free -m

# Application logs (last 100 lines)
docker-compose logs --tail=100 trdrhub-api
kubectl logs -n trdrhub-system deployment/trdrhub-api --tail=100

# Database status
psql $DATABASE_URL -c "
  SELECT
    datname,
    numbackends,
    xact_commit,
    xact_rollback,
    tup_returned,
    tup_fetched
  FROM pg_stat_database
  WHERE datname = 'trdrhub';"

# Check recent deployments
git log --oneline -10
kubectl rollout history deployment/trdrhub-api -n trdrhub-system
```

#### 2.2 Common Investigation Commands

```bash
# Network connectivity
ping -c 3 database-host
telnet redis-host 6379

# SSL certificate status
openssl s_client -connect api.trdrhub.com:443 -servername api.trdrhub.com

# Queue status (if using Redis)
redis-cli info replication
redis-cli llen trdrhub_queue

# Check disk I/O
iostat -x 1 5
```

#### 2.3 Application-Specific Checks

```bash
# API health endpoints
curl -f https://api.trdrhub.com/health
curl -f https://api.trdrhub.com/ready

# Database migrations status
alembic current
alembic history --verbose

# Audit trail integrity
python3 -c "
from app.services.audit_service import AuditService
from app.core.database import SessionLocal
db = SessionLocal()
valid, violations = AuditService.verify_chain(db, tenant_id='demo')
print(f'Audit chain valid: {valid}')
if violations:
    print('Violations:', violations)
db.close()
"
```

### Phase 3: Containment and Workarounds

#### 3.1 Service Degradation Response

```bash
# Scale up resources
kubectl scale deployment trdrhub-api --replicas=5 -n trdrhub-system

# Enable read-only mode (if applicable)
kubectl set env deployment/trdrhub-api READ_ONLY_MODE=true -n trdrhub-system

# Route traffic to backup region
# (Update load balancer or DNS as needed)
```

#### 3.2 Database Issues

```bash
# Check database connections
psql $DATABASE_URL -c "
  SELECT
    state,
    count(*) as connections
  FROM pg_stat_activity
  WHERE datname = 'trdrhub'
  GROUP BY state;"

# Kill long-running queries (if needed)
psql $DATABASE_URL -c "
  SELECT
    pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE datname = 'trdrhub'
    AND state != 'idle'
    AND now() - query_start > interval '5 minutes';"

# Enable connection pooling if not already active
# Update DATABASE_URL to use PgBouncer
```

#### 3.3 Security Incident Response

```bash
# Check for suspicious activity
grep -i "error\|fail\|attack" /var/log/nginx/access.log | tail -50

# Review audit logs for anomalies
psql $DATABASE_URL -c "
  SELECT
    actor_id,
    action,
    resource_type,
    created_at
  FROM audit_log_entries
  WHERE created_at > now() - interval '1 hour'
  ORDER BY created_at DESC;"

# Block suspicious IP addresses (if applicable)
# iptables -A INPUT -s suspicious.ip.address -j DROP

# Rotate secrets if compromise suspected
python3 scripts/secrets/rotate_secrets.py --force
```

### Phase 4: Resolution and Recovery

#### 4.1 Common Fixes

##### Application Restart

```bash
# Docker Compose
docker-compose restart trdrhub-api

# Kubernetes
kubectl rollout restart deployment/trdrhub-api -n trdrhub-system
kubectl rollout status deployment/trdrhub-api -n trdrhub-system
```

##### Database Recovery

```bash
# Restart database service
sudo systemctl restart postgresql

# Restore from backup if data corruption
python3 scripts/dr/restore_db.py $BACKUP_ID --target-db recovery_db

# Run database maintenance
psql $DATABASE_URL -c "VACUUM ANALYZE;"
```

##### Configuration Rollback

```bash
# Git rollback
git revert HEAD
git push origin main

# Kubernetes rollback
kubectl rollout undo deployment/trdrhub-api -n trdrhub-system

# Environment variable rollback
kubectl set env deployment/trdrhub-api KEY=previous_value -n trdrhub-system
```

#### 4.2 Verification Steps

```bash
# Verify service health
curl -f https://api.trdrhub.com/health

# Check key functionality
curl -X POST https://api.trdrhub.com/api/v1/test-endpoint \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Verify database connectivity
psql $DATABASE_URL -c "SELECT 1;"

# Check queue processing
# (Monitor queue length, processing rates)
```

### Phase 5: Communication and Documentation

#### 5.1 Stakeholder Communication

##### Internal Team Notification (Slack Template)

```
🚨 INCIDENT ALERT - P1 🚨
Service: TRDR Hub API
Status: INVESTIGATING
Impact: Complete service outage
Started: 2024-01-15 14:30 UTC
ETA: Investigating
Incident Commander: @john.doe
Updates: Every 15 minutes
```

##### Customer Communication Template

```
Subject: [URGENT] Service Disruption - TRDR Hub

Dear Valued Customer,

We are currently experiencing a service disruption affecting TRDR Hub.

What happened: Our API services are temporarily unavailable
When: Started at 14:30 UTC on January 15, 2024
Impact: Users cannot access the platform
Resolution: We are actively working on a fix

We will provide updates every 30 minutes until resolved.

For urgent matters, please contact: emergency@trdrhub.com

We apologize for the inconvenience.

TRDR Hub Operations Team
```

#### 5.2 Status Page Updates

```bash
# Update status page (if automated)
curl -X POST https://status.trdrhub.com/api/incidents \
  -H "Authorization: Bearer $STATUS_PAGE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API Service Disruption",
    "status": "investigating",
    "impact": "major",
    "body": "We are investigating reports of API unavailability"
  }'
```

## Post-Incident Review (PIR)

### PIR Template

#### Incident Summary

- **Date/Time**: When the incident occurred
- **Duration**: How long the incident lasted
- **Impact**: What was affected and severity
- **Root Cause**: What caused the incident
- **Resolution**: How it was resolved

#### Timeline

| Time | Action | Person |
|------|--------|---------|
| 14:30 | Incident detected | Monitoring |
| 14:32 | Investigation started | @john.doe |
| 14:45 | Root cause identified | @jane.smith |
| 15:00 | Fix implemented | @bob.jones |
| 15:15 | Service restored | @john.doe |

#### What Went Well

- Quick detection and response
- Clear communication
- Effective team coordination

#### What Could Be Improved

- Earlier detection would have reduced impact
- Need better monitoring for this scenario
- Documentation could be clearer

#### Action Items

1. **Improve monitoring** - Add alert for database connection pool exhaustion
2. **Update runbook** - Include steps for this specific scenario
3. **Team training** - Review incident response procedures
4. **Technical debt** - Address underlying infrastructure issue

### PIR Meeting Checklist

- [ ] Schedule PIR meeting within 2 business days
- [ ] Invite all involved team members
- [ ] Review timeline and actions
- [ ] Identify improvement opportunities
- [ ] Create actionable follow-up items
- [ ] Update documentation and runbooks
- [ ] Schedule follow-up review for action items

## Escalation Procedures

### Internal Escalation

1. **Level 1**: On-call engineer
2. **Level 2**: Senior engineer/Team lead
3. **Level 3**: Engineering manager
4. **Level 4**: CTO/VP Engineering

### External Escalation

- **Cloud Provider**: If infrastructure issue
- **Third-party Vendors**: If external dependency issue
- **Legal/Compliance**: If regulatory implications
- **PR/Marketing**: If public-facing communication needed

## Emergency Contacts

### Internal Team

| Role | Primary | Secondary | Phone | Email |
|------|---------|-----------|-------|-------|
| On-call Engineer | John Doe | Jane Smith | +1-xxx-xxx-xxxx | oncall@trdrhub.com |
| Engineering Manager | Bob Jones | Alice Brown | +1-xxx-xxx-xxxx | eng-mgr@trdrhub.com |
| Database Administrator | Dave Wilson | Carol Davis | +1-xxx-xxx-xxxx | dba@trdrhub.com |
| Security Team | Mike Johnson | Sarah Lee | +1-xxx-xxx-xxxx | security@trdrhub.com |

### External Vendors

| Vendor | Service | Contact | Support Level |
|--------|---------|---------|---------------|
| AWS | Cloud Infrastructure | +1-xxx-xxx-xxxx | Premium Support |
| DataDog | Monitoring | support@datadog.com | Enterprise |
| PagerDuty | Alerting | support@pagerduty.com | Business |

## Incident Response Tools

### Monitoring and Alerting

- **Prometheus/Grafana**: System metrics and alerts
- **Application Logs**: Structured logging for troubleshooting
- **Health Check Endpoints**: Automated health verification
- **External Monitoring**: Third-party uptime monitoring

### Communication Tools

- **Slack**: Real-time team communication
- **PagerDuty**: Alert management and escalation
- **Status Page**: Customer communication
- **Email**: Formal incident notifications

### Recovery Tools

- **Backup Scripts**: Database and object storage backups
- **DR Scripts**: Disaster recovery automation
- **Configuration Management**: Infrastructure as code
- **Rollback Procedures**: Quick revert capabilities

## Compliance and Regulatory Considerations

### Audit Trail

- All incident response actions must be logged in the audit trail
- Maintain detailed timeline of all actions taken
- Document any data access during incident response
- Preserve logs and evidence for compliance review

### Notification Requirements

- **Regulatory Bodies**: Notify within required timeframes if applicable
- **Customers**: Notify if data breach or significant service impact
- **Partners**: Notify if integration services affected
- **Insurance**: Notify carrier if covered incident

### Data Protection

- Follow data minimization principles during investigation
- Secure any extracted data used for debugging
- Ensure proper access controls during emergency access
- Document any compliance implications in PIR

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-15 | System | Initial version |
| 1.1 | 2024-01-20 | System | Added security procedures |