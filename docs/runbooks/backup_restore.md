# Backup and Restore Runbook

## Overview

This runbook provides step-by-step procedures for backing up and restoring TRDR Hub data and configurations. It covers both database and object storage backup/restore operations.

## Prerequisites

- Administrative access to TRDR Hub systems
- Access to backup storage (S3/MinIO)
- Database credentials and access
- Docker/Kubernetes access if applicable

## Database Backup Procedures

### 1. Regular Database Backup

#### Using the Backup Script

```bash
# Navigate to project directory
cd /path/to/trdrhub-suite-main

# Run database backup
python3 scripts/dr/backup_db.py

# With compression (recommended)
python3 scripts/dr/backup_db.py --compression

# With encryption (for sensitive environments)
python3 scripts/dr/backup_db.py --compression --encryption
```

#### Manual pg_dump Backup

```bash
# Set environment variables
export DATABASE_URL="postgresql://user:password@host:port/database"

# Create backup with compression
pg_dump $DATABASE_URL \
  --format=custom \
  --compress=9 \
  --verbose \
  --file=trdrhub_backup_$(date +%Y%m%d_%H%M%S).dump

# Verify backup integrity
pg_restore --list trdrhub_backup_*.dump | head -20
```

### 2. Automated Backup Schedule

#### Cron Job Setup

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/trdrhub-suite-main && python3 scripts/dr/backup_db.py >> /var/log/trdrhub_backup.log 2>&1

# Add weekly full backup on Sundays at 1 AM
0 1 * * 0 cd /path/to/trdrhub-suite-main && python3 scripts/dr/backup_db.py --encryption >> /var/log/trdrhub_backup_weekly.log 2>&1
```

#### Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: trdrhub-db-backup
  namespace: trdrhub-system
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: trdrhub-backup:latest
            command:
            - python3
            - scripts/dr/backup_db.py
            - --output-json
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: trdrhub-secrets
                  key: database_url
          restartPolicy: OnFailure
```

## Database Restore Procedures

### 1. Point-in-Time Restore

#### List Available Backups

```bash
# List local backups
python3 scripts/dr/backup_db.py --list

# List S3 backups
aws s3 ls s3://trdrhub-dr-backups/database/ --recursive
```

#### Restore from Backup

```bash
# Restore to current database (CAUTION!)
python3 scripts/dr/restore_db.py backup_id_here

# Restore to test database
python3 scripts/dr/restore_db.py backup_id_here \
  --target-db postgresql://user:password@host:port/test_db

# Dry run (show what would be restored)
python3 scripts/dr/restore_db.py backup_id_here --dry-run
```

### 2. Emergency Restore Procedure

#### Step 1: Stop Application Services

```bash
# Docker Compose
docker-compose down

# Kubernetes
kubectl scale deployment trdrhub-api --replicas=0 -n trdrhub-system
kubectl scale deployment trdrhub-worker --replicas=0 -n trdrhub-system
```

#### Step 2: Create Database Backup (Safety)

```bash
# Backup current state before restore
pg_dump $DATABASE_URL --file=pre_restore_backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Step 3: Restore Database

```bash
# Option 1: Complete database drop and restore
dropdb trdrhub_db
createdb trdrhub_db
python3 scripts/dr/restore_db.py $BACKUP_ID

# Option 2: Restore to new database and switch
createdb trdrhub_db_restored
python3 scripts/dr/restore_db.py $BACKUP_ID \
  --target-db postgresql://user:password@host:port/trdrhub_db_restored
```

#### Step 4: Verify Restoration

```bash
# Check database connectivity
psql $DATABASE_URL -c "SELECT version();"

# Verify table counts
psql $DATABASE_URL -c "
  SELECT schemaname,tablename,n_tup_ins
  FROM pg_stat_user_tables
  ORDER BY n_tup_ins DESC;
"

# Check audit chain integrity
python3 -c "
from scripts.dr.restore_db import verify_audit_chain
print('Audit chain verification:', verify_audit_chain('$DATABASE_URL'))
"
```

#### Step 5: Restart Services

```bash
# Docker Compose
docker-compose up -d

# Kubernetes
kubectl scale deployment trdrhub-api --replicas=3 -n trdrhub-system
kubectl scale deployment trdrhub-worker --replicas=2 -n trdrhub-system
```

## Object Storage Backup/Restore

### 1. Object Storage Backup

#### Using the Backup Script

```bash
# Full backup (first time)
python3 scripts/dr/backup_objects.py --full

# Incremental backup (regular)
python3 scripts/dr/backup_objects.py

# With checksum verification
python3 scripts/dr/backup_objects.py --verify-checksums
```

#### Manual S3 Sync

```bash
# Backup local storage to S3
aws s3 sync ./storage s3://trdrhub-dr-objects/$(date +%Y%m%d)/local/ \
  --exclude "*.tmp" \
  --exclude "cache/*"

# Backup source S3 bucket
aws s3 sync s3://trdrhub-compliance s3://trdrhub-dr-objects/$(date +%Y%m%d)/s3/
```

### 2. Object Storage Restore

#### Using the Restore Script

```bash
# List available object backups
python3 scripts/dr/backup_objects.py --list

# Restore from specific backup
python3 scripts/dr/restore_objects.py backup_id_here

# Restore to different location
python3 scripts/dr/restore_objects.py backup_id_here --target-path ./restored_storage/
```

#### Manual S3 Restore

```bash
# Restore from S3 backup
aws s3 sync s3://trdrhub-dr-objects/20240115/local/ ./storage/
aws s3 sync s3://trdrhub-dr-objects/20240115/s3/ s3://trdrhub-compliance/
```

## Disaster Recovery Procedures

### 1. Complete System Restore

#### Step 1: Infrastructure Preparation

```bash
# Ensure infrastructure is ready
# - Database server is running
# - S3/MinIO is accessible
# - Application servers are ready

# Verify connectivity
pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER
aws s3 ls s3://trdrhub-dr-backups/
```

#### Step 2: Database Restore

```bash
# Find latest backup
LATEST_DB_BACKUP=$(python3 scripts/dr/backup_db.py --list --output-json | \
  jq -r '.[0].backup_id')

echo "Restoring database backup: $LATEST_DB_BACKUP"

# Restore database
python3 scripts/dr/restore_db.py $LATEST_DB_BACKUP
```

#### Step 3: Object Storage Restore

```bash
# Find latest object backup
LATEST_OBJ_BACKUP=$(python3 scripts/dr/backup_objects.py --list --output-json | \
  jq -r '.[0].backup_id')

echo "Restoring object backup: $LATEST_OBJ_BACKUP"

# Restore objects
python3 scripts/dr/restore_objects.py $LATEST_OBJ_BACKUP
```

#### Step 4: Application Configuration

```bash
# Restore configuration files
# (These should be in version control or backed up separately)

# Update database migrations if needed
alembic upgrade head

# Restart services with updated configuration
docker-compose up -d
```

## Backup Verification and Testing

### 1. Regular Backup Testing

#### Monthly Restore Test

```bash
#!/bin/bash
# Monthly backup test script

TEST_DB="trdrhub_test_$(date +%Y%m)"
LATEST_BACKUP=$(python3 scripts/dr/backup_db.py --list --output-json | jq -r '.[0].backup_id')

# Create test database
createdb $TEST_DB

# Restore backup
python3 scripts/dr/restore_db.py $LATEST_BACKUP \
  --target-db postgresql://user:password@host:port/$TEST_DB

# Verify restoration
RESTORE_SUCCESS=$?

# Run basic queries
psql postgresql://user:password@host:port/$TEST_DB -c "
  SELECT
    COUNT(*) as total_audit_entries,
    MAX(created_at) as latest_entry
  FROM audit_log_entries;
"

# Cleanup
dropdb $TEST_DB

if [ $RESTORE_SUCCESS -eq 0 ]; then
  echo "✅ Monthly backup test passed"
else
  echo "❌ Monthly backup test failed"
  exit 1
fi
```

### 2. Automated DR Drill

```bash
# Run full DR drill
python3 scripts/dr/dr_drill.py \
  --target-rpo=15 \
  --target-rto=60 \
  --output-json > dr_drill_$(date +%Y%m%d).json

# Check results
if [ $? -eq 0 ]; then
  echo "✅ DR drill completed successfully"
  cat dr_drill_$(date +%Y%m%d).json | jq '.success'
else
  echo "❌ DR drill failed"
fi
```

## Troubleshooting Common Issues

### Database Backup Issues

#### Issue: pg_dump fails with "connection refused"

```bash
# Check database connectivity
pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER

# Check if database is accepting connections
psql $DATABASE_URL -c "SELECT 1;"

# Verify pg_hba.conf allows connection
sudo grep -E "^(local|host)" /etc/postgresql/*/main/pg_hba.conf
```

#### Issue: Backup file is corrupted

```bash
# Verify backup integrity
pg_restore --list backup_file.dump

# Check file size and permissions
ls -la backup_file.dump
```

### Database Restore Issues

#### Issue: Restore fails with permission errors

```bash
# Grant necessary permissions
psql $DATABASE_URL -c "ALTER USER $DB_USER CREATEDB;"

# Or restore as superuser
sudo -u postgres pg_restore -d $DATABASE_NAME backup_file.dump
```

#### Issue: Foreign key constraint errors

```bash
# Restore without triggers first, then add constraints
pg_restore --disable-triggers --data-only -d $DATABASE_NAME backup_file.dump

# Then restore constraints
pg_restore --schema-only --triggers-only -d $DATABASE_NAME backup_file.dump
```

### S3/Object Storage Issues

#### Issue: S3 access denied

```bash
# Check AWS credentials
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://trdrhub-dr-backups/

# Verify IAM permissions
aws iam get-user-policy --user-name backup-user --policy-name BackupPolicy
```

#### Issue: Large file upload timeout

```bash
# Use multipart upload for large files
aws s3 cp large_backup.dump s3://bucket/path/ \
  --storage-class STANDARD_IA \
  --cli-read-timeout 0
```

## Monitoring and Alerting

### Backup Success Monitoring

```bash
# Check last successful backup
LAST_BACKUP=$(python3 scripts/dr/backup_db.py --list | head -1)
echo "Last backup: $LAST_BACKUP"

# Alert if backup is older than 25 hours
BACKUP_AGE=$(stat -c %Y $LAST_BACKUP_FILE)
CURRENT_TIME=$(date +%s)
AGE_HOURS=$(( ($CURRENT_TIME - $BACKUP_AGE) / 3600 ))

if [ $AGE_HOURS -gt 25 ]; then
  echo "⚠️  Backup is older than 25 hours!"
  # Send alert (Slack, email, etc.)
fi
```

### Storage Space Monitoring

```bash
# Check backup storage usage
aws s3api list-objects-v2 --bucket trdrhub-dr-backups \
  --query 'sum(Contents[].Size)' --output text | \
  awk '{print "Backup storage usage: " $1/1024/1024/1024 " GB"}'

# Check local disk space
df -h /backup/path/
```

## Recovery Time and Point Objectives

### Current Targets

- **RPO (Recovery Point Objective)**: 15 minutes
- **RTO (Recovery Time Objective)**: 60 minutes

### Measuring Performance

```bash
# Measure backup time
time python3 scripts/dr/backup_db.py

# Measure restore time
time python3 scripts/dr/restore_db.py $BACKUP_ID --target-db test_db

# Full DR drill with metrics
python3 scripts/dr/dr_drill.py --target-rpo=15 --target-rto=60
```

## Security Considerations

1. **Encryption**: Always encrypt backups in production environments
2. **Access Control**: Limit backup access to authorized personnel only
3. **Network Security**: Use VPN or private networks for backup transfers
4. **Retention Policy**: Implement backup retention and secure deletion
5. **Audit Trail**: Log all backup and restore operations

## Contact Information

- **Primary DBA**: [contact info]
- **Backup Administrator**: [contact info]
- **On-Call Engineering**: [contact info]
- **Security Team**: [contact info]

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-15 | System | Initial version |
| 1.1 | 2024-01-20 | System | Added K8s procedures |