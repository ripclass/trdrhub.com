# Day3 Schema Reconcile Plan
## Objective
Reconcile DB schema mismatch causing `/api/validate` 500s during Day3 smoke (errors observed: `relation users does not exist` -> `column users.auth_user_id does not exist` -> `column companies.type does not exist`).

## 1) What I audited
### SQLAlchemy model/API path used by `/api/validate`
- `app/routers/validate.py`
  - `get_or_create_demo_user()` does:
    - `db.query(User).filter(User.email == ...)`
    - raw SQL `SELECT id FROM companies WHERE name = :name`
    - raw SQL
      ```sql
      INSERT INTO companies (id, name, type, created_at, updated_at)
      VALUES (:id, :name, :type, NOW(), NOW())
      ```
    - creates `User(email, role, company_id, onboarding_completed, status, ...)`
- `app/core/security.py` uses `User.auth_user_id` in optional auth flows and model checks.

### Required runtime columns for this flow
- `users.id` (PK)
- `users.email`
- `users.password`/`hashed_password` (per model, used in create/login paths)
- `users.company_id` (FK to companies)
- **`users.auth_user_id`** (must exist for auth model/flows)
- **`companies.id`**
- **`companies.name`**
- **`companies.type`** (currently referenced by raw SQL in `/api/validate`)
- `users.status` (demo create sets status)

## 2) Why migrations diverge / why this broke
### Canonical Alembic location
- Active config points to **`apps/api/alembic`** (`apps/api/alembic.ini` => `script_location = alembic`).
- `apps/api/migrations/` is a legacy directory and is **not active** by current config, which is a major source of confusion.

### Current Alembic graph observations (from `apps/api/alembic/history --verbose`)
- There are two active heads:
  - `20260227_day1_p0_failclosed` (head)
  - `sanctions_001` (head)
- This is expected given branch from `20251223_create_rules_audit_table`:
  - `20251223 -> 20251130_price_verify -> ... -> sanctions_001`
  - `20251223 -> 20260227_day1_p0_failclosed`
- So `alembic upgrade head` (singular) can be ambiguous; use `upgrade heads` or create a merge revision for future single-head cleanliness.
- There is no evidence in the active migration chain that a `companies.type` column is introduced; `type` only appears as required by raw SQL in `/api/validate`.
- `users.auth_user_id` is added by migration `20251115_add_auth_user_id_to_users` in the active chain, but some environments appear to have run only partial/older migrations.

## 3) Minimal safe reconciliation plan

### A) Pre-flight checks (non-invasive)
Run from API working dir:
```bash
cd H:\.openclaw\workspace\trdrhub.com\apps\api
python -m alembic -c alembic.ini current
python -m alembic -c alembic.ini heads
python -m alembic -c alembic.ini branches
```

Then inspect live DB shape directly (set `DATABASE_URL` first):
```sql
-- relationship-level checks
SELECT to_regclass('public.users') IS NOT NULL AS users_table_exists;
SELECT to_regclass('public.companies') IS NOT NULL AS companies_table_exists;

-- required columns
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('users','companies')
  AND column_name IN ('id','email','hashed_password','status','company_id','auth_user_id','role','is_active',
                      'name','type')
ORDER BY table_name, column_name;
```

### B) Patch-only schema fix (safe, no table rebuild)
If `users` exists but lacks `auth_user_id`:
```sql
ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS auth_user_id UUID;

CREATE UNIQUE INDEX IF NOT EXISTS ux_users_auth_user_id
  ON public.users(auth_user_id)
  WHERE auth_user_id IS NOT NULL;
```

If `companies` exists but lacks `type`:
```sql
ALTER TABLE public.companies
  ADD COLUMN IF NOT EXISTS type TEXT;

-- optional default for pre-existing rows (prevents null surprises if strict business logic added later)
UPDATE public.companies
SET type = COALESCE(type, 'sme')
WHERE type IS NULL;
```

Optional FK backfill (only if Supabase auth schema exists and you want full linkage):
```sql
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'auth' AND table_name = 'users'
  ) THEN
    ALTER TABLE public.users
      DROP CONSTRAINT IF EXISTS fk_users_auth_user_id;

    ALTER TABLE public.users
      ADD CONSTRAINT fk_users_auth_user_id
      FOREIGN KEY (auth_user_id)
      REFERENCES auth.users(id)
      ON DELETE SET NULL;
  END IF;
END $$;
```

### C) If either `users` or `companies` table is missing
If preflight shows a missing relation, run migration bootstrap only (recommended order):
```bash
cd H:\.openclaw\workspace\trdrhub.com\apps\api
python -m alembic -c alembic.ini upgrade heads
```
This applies all reachable history to the two current heads.

### D) Canonical future-proofing for multi-head state
Create explicit merge revision to eliminate two-head drift:
```bash
cd H:\.openclaw\workspace\trdrhub.com\apps\api
python -m alembic -c alembic.ini merge -m "merge_day3_validation_heads" sanctions_001 20260227_day1_p0_failclosed
# review generated revision, then:
python -m alembic -c alembic.ini upgrade heads
```
Then codebase should consistently move on a single head in future.

## 4) Rollback/safety notes
- **No destructive reset included.**
- If patching via raw SQL was used and needs undo:
```sql
ALTER TABLE public.users DROP CONSTRAINT IF EXISTS fk_users_auth_user_id;
DROP INDEX IF EXISTS public.ux_users_auth_user_id;
ALTER TABLE public.users DROP COLUMN IF EXISTS auth_user_id;

ALTER TABLE public.companies DROP COLUMN IF EXISTS type;
```
- Do **not** run schema-level `DROP TABLE` unless approved.
- If DB was already missing expected Alembic chain and you require deterministic rebuild, a full migration reset (`DROP SCHEMA`/recreate) is possible but **requires explicit approval**.

## 5) Expected post-fix validation checks
1. Start API and hit `/api/validate` unauthenticated with a smoke doc.
2. Expect successful user bootstrap:
   - no 500 from missing `users`/`companies` columns
3. Expected query behavior:
   - demo company lookup/insert succeeds (no `relation ... type ...` errors)
   - token-auth flows read `User.auth_user_id` without `UndefinedColumn` errors
4. Re-run smoke20 and check day-gate:
   - 422 == 0
   - pass_blocked_ratio <= threshold
   - comparable_records / total >= target
