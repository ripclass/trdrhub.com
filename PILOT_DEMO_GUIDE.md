# TRDR Hub Bank-Grade Pilot Demo Guide

## Quick Start

### 1. Run the Pilot Demo

```bash
make pilot_demo
```

This single command will:
- Initialize the database with Alembic migrations
- Create all necessary tables with proper schemas
- Seed realistic demo data (tenants, users, LC sessions, audit trails)
- Set up immutable audit trail with hash-chained entries
- Configure governance approval workflows
- Start the complete bank-grade compliance system

### 2. Access the System

After running `make pilot_demo`, you'll have access to:

**Admin Console**: http://localhost:3000/admin
- Comprehensive compliance dashboard
- Audit trail explorer with chain verification
- Disaster recovery management
- Secrets lifecycle monitoring
- Governance approval workflows

**Grafana Dashboards**: http://localhost:3001
- Real-time compliance metrics
- Audit chain health monitoring
- DR/backup status dashboards
- Performance and security metrics

### 3. Demo Login Credentials

| Role | Email | Password | Access Level |
|------|-------|----------|--------------|
| Super Admin | admin@lcopilot.com | admin123 | Full system access |
| SME Admin | sme.admin@demo.com | sme123 | Tenant admin |
| Bank Officer | bank.officer@demo.com | bank123 | Bank operations |
| Auditor | auditor@demo.com | audit123 | Compliance review |
| Exporter | exporter@demo.com | export123 | LC operations |

## Bank-Grade Capabilities Demonstration

### 1. Immutable Audit Trail

**Verify Chain Integrity:**
```bash
# Check audit chain health
curl -X POST "http://localhost:8000/admin/audit/verify?tenant_id=demo-bank"

# Export audit trail for compliance
curl "http://localhost:8000/admin/audit/export?tenant_id=demo-bank&format=json" > audit_export.json
```

**Demo Actions:**
1. Login to Admin Console → Audit Explorer
2. Search audit entries by actor, resource, or time period
3. Click "Verify Chain" to validate tamper-proof integrity
4. Export audit trail in CSV/JSON/PDF formats
5. Observe real-time hash chain verification

### 2. Disaster Recovery System

**Run DR Drill:**
```bash
# Full automated DR drill with RPO/RTO measurement
make dr_drill

# Manual backup creation
make backup

# List available backups
python3 scripts/dr/backup_db.py --list
```

**Demo Actions:**
1. Admin Console → DR & Backups
2. View backup status and history
3. Run DR drill to measure RPO/RTO
4. Review drill results with compliance metrics
5. Monitor backup health dashboards

### 3. Secrets Lifecycle Management

**Rotate Secrets:**
```bash
# Rotate all application secrets with audit trail
make rotate_secrets

# View rotation history
curl "http://localhost:8000/admin/secrets/rotations"
```

**Demo Actions:**
1. Admin Console → Secrets Management
2. View current secret rotation status
3. Perform controlled secret rotation
4. Monitor service restart automation
5. Review rotation audit logs

### 4. Governance Enforcement (4-Eyes Approval)

**Test Approval Workflows:**

The system includes pre-configured approval requirements for sensitive operations:

1. Admin Console → Governance → Approvals Queue
2. Try to perform a sensitive action (role change, data export)
3. System will require 4-eyes approval
4. Second user must approve the action
5. All approval activity is audited

**Example API Test:**
```bash
# This will trigger approval requirement
curl -X POST "http://localhost:8000/admin/governance/sensitive-action" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"action": "role_change", "target_user": "user_id"}'
```

### 5. Compliance Glossary

**Access Comprehensive Glossary:**
1. Navigate to http://localhost:3000/compliance/glossary
2. Search 100+ trade finance terms
3. Filter by category (Banking, Compliance, Regulations)
4. Cross-reference with UCP 600, ISBP guidelines
5. Use inline tooltips throughout the application

## Advanced Demo Scenarios

### Scenario 1: Complete LC Processing Audit

1. **Login as Exporter** (exporter@demo.com)
2. **Process LC documents** - uploads are audited
3. **Login as Bank Officer** (bank.officer@demo.com)
4. **Review and validate** - decisions are audited
5. **Login as Auditor** (auditor@demo.com)
6. **Verify audit chain** for complete traceability
7. **Export compliance report** with tamper-proof evidence

### Scenario 2: Security Incident Response

1. **Trigger security alert** (simulate suspicious activity)
2. **Admin Console** shows security dashboard alerts
3. **Automated secret rotation** if compromise detected
4. **Audit trail preservation** during incident
5. **Compliance reporting** post-incident

### Scenario 3: Regulatory Compliance Audit

1. **External auditor login** (auditor@demo.com)
2. **Access read-only dashboards** with full visibility
3. **Export complete audit trail** for date range
4. **Verify hash chain integrity** - proves no tampering
5. **Generate compliance report** with RPO/RTO metrics

## System Architecture Verification

### Database Layer
```bash
# Verify Alembic migrations
alembic current
alembic history

# Check audit table structure
psql $DATABASE_URL -c "\d audit_log_entries"

# Verify hash chain
python3 -c "
from app.services.audit_service import AuditService
from app.core.database import SessionLocal
db = SessionLocal()
valid, violations = AuditService.verify_chain(db, tenant_id='demo-bank')
print(f'Hash chain valid: {valid}')
print(f'Violations: {len(violations)}')
"
```

### API Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Admin audit API
curl http://localhost:8000/admin/audit/stats?tenant_id=demo-bank

# Governance API
curl http://localhost:8000/admin/governance/stats?tenant_id=demo-bank

# DR metrics
curl http://localhost:8000/admin/dr/metrics
```

### Frontend Features
1. **Multi-tenant dashboard** with role-based access
2. **Real-time audit visualization** with search/filter
3. **Governance workflow UI** for approvals
4. **Compliance glossary** with smart tooltips
5. **DR status monitoring** with drill results

## Compliance Standards Demonstrated

### ✅ Bank-Grade Audit Trail
- **Immutable**: Hash-chained entries prevent tampering
- **Complete**: Every action is logged with context
- **Traceable**: Full actor-resource-action tracking
- **Exportable**: Multiple formats for regulators

### ✅ Disaster Recovery
- **Automated**: Scripts for backup/restore operations
- **Measured**: RPO/RTO metrics with targets
- **Tested**: Regular DR drills with validation
- **Documented**: Complete runbooks and procedures

### ✅ Security Controls
- **Secrets Management**: Automated rotation with audit
- **Access Control**: Role-based permissions
- **4-Eyes Approval**: Sensitive operations require dual approval
- **Monitoring**: Real-time security dashboards

### ✅ Regulatory Compliance
- **Data Protection**: Encryption at rest and in transit
- **Audit Requirements**: Comprehensive logging
- **Change Management**: All modifications tracked
- **Documentation**: Complete operational runbooks

## Operational Runbooks

Access complete operational documentation:

```bash
# Start runbook server
make runbooks_serve

# Then visit: http://localhost:8080/runbooks/
```

Available runbooks:
- **Backup & Restore Procedures** - Step-by-step recovery
- **Incident Response** - P1/P2/P3 escalation procedures
- **DR Drill Execution** - Compliance testing procedures
- **Compliance Audit** - Evidence gathering processes

## Performance & Metrics

The system includes comprehensive metrics:

- **Audit Performance**: Hash verification speed, chain health
- **DR Metrics**: Backup success rates, RPO/RTO measurements
- **Security Metrics**: Failed logins, suspicious activity
- **Business Metrics**: LC processing times, error rates

## Support & Documentation

- **System Status**: Built-in health checks and monitoring
- **API Documentation**: Swagger UI at http://localhost:8000/docs
- **Admin Guides**: Complete operational procedures
- **Compliance Reports**: Automated evidence generation

---

## Next Steps for Production

1. **Environment Configuration**: Update settings for production databases and cloud services
2. **Certificate Management**: Configure TLS certificates for HTTPS
3. **Monitoring Integration**: Connect to production Prometheus/Grafana
4. **Backup Storage**: Configure enterprise backup storage (S3/Azure)
5. **Identity Provider**: Integrate with enterprise SSO/LDAP
6. **Security Hardening**: Apply production security configurations

The pilot demo provides a complete bank-grade compliance platform ready for enterprise deployment with minimal configuration changes.