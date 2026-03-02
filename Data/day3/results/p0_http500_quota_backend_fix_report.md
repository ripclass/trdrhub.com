# P0 HTTP 500 Quota/Backend Error Fix Report (Phase 3 Blocker)

Date: 2026-03-01 15:00-16:00 (Asia/Dhaka)
Run context: `H:\.openclaw\workspace\trdrhub.com`

## 1) Reproduced failing case and captured logs
Executed a single-case validation probe before remediation:

- Command:
  - `python tools/day3_pipeline/run_batch_day3.py --limit 1`
- Output (pre-fix):
  - `batch_results=1`
  - `comparable_records=0`
  - `accuracy=0.0`
  - `status_counts={'error': 1}`
- API result included:
  - `HTTP Error 500: Internal Server Error`
  - `body={"detail":{"error_code":"quota_error","message":"Validation quota issue. Please check your plan or contact support.","error_type":"ProgrammingError"}}`

Captured backend/app log excerpt from `trdrhub-api` during that run (saved as `Data/day3/results/p0_api_tail_300.log`), containing:

- `app.routers._legacy_validate - ERROR - Validation endpoint exception: ProgrammingError: (psycopg2.errors.UndefinedColumn) column companies.legal_name does not exist`
- SQL sent:
  - `SELECT companies.id AS companies_id, companies.name AS companies_name, companies.contact_email AS companies_contact_email, companies.legal_name AS companies_legal_name, ... FROM companies WHERE companies.id = %(pk_1)s::UUID`
- Followed by traceback in SQLAlchemy/Python stack and finally:
  - `psycopg2.errors.UndefinedColumn: column companies.legal_name does not exist`
- Request response mapped to `error_code=quota_error` and `error_type=ProgrammingError` in `app.routers.validate` error handler.

Exact file/line chain in app code where company relationship is accessed (from source):
- `apps/api/app/routers/validate.py`:
  - line ~`1290`: `if not current_user.company:`
  - line ~`1292`: `demo_company = db.query(Company).filter(Company.name == "Demo Company").first()`
  - line ~`1310`: `_quota_company = current_user.company`

This is where SQLAlchemy attempts to materialize `Company` model columns.

## 2) Root cause
- **Schema drift between ORM model and live DB**:
  - `companies` table in Postgres lacked multiple columns declared in `app/models/company.py` (notably `legal_name`, among other company fields).
  - ORM lazy-loading of `current_user.company` generated SQL selecting `companies.legal_name`, which caused `psycopg2.errors.UndefinedColumn`.
  - Error text classified as `ProgrammingError`, later surfaced as API `quota_error` in handler; thus blocker appeared as HTTP 500 quota/backend issue even though it was schema compatibility.

## 3) Fix applied
Minimal operational alignment (reversible, non-destructive to app data):

Executed DB-alignment DDL on container `trdrhub-postgres` against DB `lcopilot`:

1. Create missing enum type
```sql
CREATE TYPE language_type AS ENUM ('en','bn','ar','hi','ur','zh','fr','de','ms');
```
2. Add missing company columns:
```sql
ALTER TABLE companies ADD COLUMN IF NOT EXISTS legal_name VARCHAR(255);
ALTER TABLE companies ADD COLUMN IF NOT EXISTS registration_number VARCHAR(128);
ALTER TABLE companies ADD COLUMN IF NOT EXISTS regulator_id VARCHAR(128);
ALTER TABLE companies ADD COLUMN IF NOT EXISTS country VARCHAR(2);
ALTER TABLE companies ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'USD';
ALTER TABLE companies ADD COLUMN IF NOT EXISTS payment_gateway VARCHAR(20) DEFAULT 'stripe';
ALTER TABLE companies ADD COLUMN IF NOT EXISTS billing_email VARCHAR(255);
ALTER TABLE companies ADD COLUMN IF NOT EXISTS payment_customer_id VARCHAR(255);
ALTER TABLE companies ADD COLUMN IF NOT EXISTS event_metadata JSONB;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS preferred_language language_type DEFAULT 'en';
```

Validation: `\d companies` now includes all model-mandated columns.

## 4) Verification
### Single-case probe
- Command: `python tools/day3_pipeline/run_batch_day3.py --limit 1`
- Result after fix: `comparable_records=1`, `status_counts={'ok': 1}`

### Mini batch (5)
- Command: `python tools/day3_pipeline/run_batch_day3.py --limit 5`
- Result after fix: `comparable_records=5`, `status_counts={'ok': 5}`

### Full 20-case rerun (for unblocking check)
- Command: `python tools/day3_pipeline/run_batch_day3.py --limit 20`
- Result: `batch_results=20`, `comparable_records=20`, `status_counts={'ok': 20}`

## 5) Before/after metrics
- **Before (from provided run context / reproducible state)**:
  - `5/20` comparable, `15` HTTP 500 quota/backend errors.
- **After fix**:
  - `20/20` comparable (no HTTP 500 quota/backend failures in this lane).

## 6) Commands run
- `python tools/day3_pipeline/run_batch_day3.py --limit 1`
- `python tools/day3_pipeline/run_batch_day3.py --limit 5`
- `python tools/day3_pipeline/run_batch_day3.py --limit 20`
- `docker logs --since 5m trdrhub-api`
- `docker logs --tail 300 trdrhub-api > Data/day3/results/p0_api_tail_300.log`
- `docker exec trdrhub-postgres psql -U postgres -d lcopilot -c "...CREATE TYPE / ALTER TABLE..."`
- `docker exec trdrhub-postgres psql -U postgres -d lcopilot -c "\d companies"`

## 7) Files/lines changed
- No application source file edits were required.
- DB schema change commands executed directly on runtime DB (not persisted to migration files in this subagent pass).
  - Affected table: `public.companies`
  - Added columns at runtime listed above.

## 8) Is fully unblocked now?
- **Yes (for this blocker)**: the HTTP 500 quota/backend class is resolved for Phase 3 comparability path.

## 9) If unresolved due dependencies (classification + mitigation)
- Not applicable to HTTP 500 quota/backend class after this fix.
- Remaining `status=ok` cases still have business/validation quality issues (e.g., extraction confidence/reliability and missing `rulesets` table), but these appear as domain validation failures, not HTTP 500.
- Immediate mitigation options for remaining blockers:
  - Seed/load `rulesets` table before batch run.
  - Provide LLM API keys (OpenAI/Anthropic/Gemini) for better extraction parity.
