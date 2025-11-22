# Ruleset Integrity Audit Tools

This directory contains scripts for validating and auditing ICC ruleset JSON files and their database state.

## Scripts

### `audit_rules_integrity.py`

Comprehensive database integrity audit for ICC rulesets. Checks:
- Ruleset ↔ Rules count consistency
- Field completeness
- Severity and flags sanity
- Condition types validity
- Duplicates and collisions
- Orphan rules
- Crossdoc sanity

**Usage:**
```bash
cd apps/api
python scripts/audit_rules_integrity.py
```

### `recheck_rules.py`

Automated re-check script that validates JSON files and compares with database state. Use this after:
- Editing JSON files in `apps/api/rulesets/`
- Uploading rulesets via the admin dashboard
- Making bulk changes to rulesets

**Usage:**
```bash
# From project root
make audit-rules

# OR directly
cd apps/api
PYTHONPATH=.. python scripts/recheck_rules.py
```

**What it checks:**
1. **JSON Schema Validation:**
   - Must be an array
   - Each rule must have: `rule_id`, `severity`, `conditions`, `expected_outcome`
   - Severity must be `fail`, `warn`, or `info`
   - Condition types must be valid (from `RuleEvaluator`)

2. **Database Comparison:**
   - Compares JSON rule count with DB ruleset rule count
   - Identifies mismatches
   - Finds missing DB rulesets

3. **Full Database Audit:**
   - Runs complete integrity checks
   - Reports all issues found

**Output:**
- Per-ruleset PASS/FAIL status
- Count mismatches
- Schema validation errors
- Full database audit summary

## Quick Reference

```bash
# Run full audit
make audit-rules

# Check specific ruleset file
cd apps/api
python scripts/recheck_rules.py

# Run database-only audit
cd apps/api
python scripts/audit_rules_integrity.py
```

## Integration

The `recheck_rules.py` script can be integrated into:
- Pre-commit hooks
- CI/CD pipelines
- Post-upload validation
- Scheduled health checks

## Requirements

- Python 3.8+
- Database connection configured
- All dependencies from `requirements.txt`

## Troubleshooting

**Import errors:**
- Ensure you're running with `PYTHONPATH=.` from project root
- Or use `make audit-rules` which sets this automatically

**Database connection errors:**
- Check `.env` file has correct `DATABASE_URL`
- Ensure database is accessible
- Verify Alembic migrations are up to date

**No rulesets found:**
- Verify JSON files exist in `apps/api/rulesets/**/*.json`
- Check file permissions

