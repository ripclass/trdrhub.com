# TRDRHub Phase 2 Execution Report

- **Date/Session:** 2026-03-01 / subagent b9d5b6e7-7bd3-4476-9f7f-a72ca64a4a1d
- **Objective:** Eliminate schema/runtime causes of `/api/validate` failures and run single-case probe.

## Root cause(s) found
1. DB schema was missing core tables (`users`, `companies`) entirely at start.
2. Alembic `upgrade heads` could not reach full head due migration bug in `20250916_170100_add...` path:
   - `20250917_add_integration_models` hits `sqlalchemy.exc.ProgrammingError: duplicate name: \\"integrationtype\\"` (enum type create path is non-idempotent)
3. Initial non-destructive pass to target revision `20250916_170100` still left ORM-required columns absent (`users.status`, `users.auth_user_id`, `users.onboarding_*`, `users.kyc_*`, `companies.type`, nullable mismatch on `companies.contact_email`), causing potential runtime failures for `/api/validate` bootstrap path.

## Commands executed
- `Get-Content ...\20250916_170100_seed_default_companies.py -First 40`
- `python -m alembic -c alembic.ini current`
- `python -m alembic -c alembic.ini heads`
- `python -m alembic -c alembic.ini branches`
- `python -m alembic -c alembic.ini upgrade heads` *(first pass failed with duplicate enum type error)*
- `python -m alembic -c alembic.ini upgrade 20250916_170100`
- DB column/table diagnostics (`SELECT ...`) for `users`/`companies` against `public` schema
- Manual reconciliation SQL (see exact changes below)
- Single-case probe:
  - `DAY3_API_URL=http://localhost:8000/api/validate/`
  - `python -c "import requests, json; ... requests.post(..., json={'document_type':'letter_of_credit'}) ..."`

## Exact schema changes applied
Executed in DB `lcopilot` via `docker exec trdrhub-postgres psql`:
1. `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'active';`
2. `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS auth_user_id UUID;`
3. `CREATE UNIQUE INDEX IF NOT EXISTS ux_users_auth_user_id ON public.users(auth_user_id) WHERE auth_user_id IS NOT NULL;`
4. `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN NOT NULL DEFAULT false;`
5. `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS onboarding_data JSONB;`
6. `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS onboarding_step VARCHAR(128);`
7. `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS kyc_required BOOLEAN NOT NULL DEFAULT false;`
8. `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS kyc_status VARCHAR(32);`
9. `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS approver_id UUID;`
10. `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE;`
11. `ALTER TABLE public.companies ADD COLUMN IF NOT EXISTS type TEXT;`
12. `UPDATE public.companies SET type = COALESCE(type, 'sme') WHERE type IS NULL;`
13. `ALTER TABLE public.companies ALTER COLUMN contact_email DROP NOT NULL;`

Result of reconciliation query after changes:
- `users` and `companies` exist and required bootstrap columns now present.
- Alembic version now `20250916_170100`.

## Single-case probe request/response summary
- **Request:** `POST http://localhost:8000/api/validate/` with JSON `{ "document_type": "letter_of_credit" }`
- **Raw response:** HTTP 200
- **Response highlights:** includes `job_id`, `structured_result` + `validation_blocked=true`, and detailed gate/issue payload (non-transport, non-schema error).
- **Status:** **PASS** (non-error structured output; valid runtime path reached)

## Phase 2 gate decision
- **PASS** (core `/api/validate` now executes and returns structured result without schema/runtime missing-column missing-table failure).

## Next action
- Plan and apply a controlled migration fix for `20250917_add_integration_models` (enum creation path) so `alembic upgrade heads` can proceed beyond `20250916_170100` in future without manual schema patches.