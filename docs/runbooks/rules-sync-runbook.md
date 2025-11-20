# Rules Table Backfill & Sync Runbook

The goal of this runbook is to repopulate the `rules` governance table from the canonical ruleset JSON stored in Supabase. Follow these steps whenever a new ruleset schema ships or an environment loses the normalized rows.

## Prerequisites

- Backend `.env` contains `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
- Database is reachable via the standard `DATABASE_URL`.
- The new CLI importer and sync script are available (`scripts/import_rules.py`, `scripts/sync_rulesets.py`).

## 1. Dry run against staging

```powershell
cd apps/api
python ..\..\scripts\sync_rulesets.py --include-inactive --limit 1
```

Verify that:

- The script reports `inserted/updated` counts instead of throwing errors.
- The `rules_audit` table receives an `import` entry for the targeted ruleset.

## 2. Full active sync

```powershell
cd apps/api
python ..\..\scripts\sync_rulesets.py
```

What happens:

- Every active ruleset is downloaded from Supabase Storage.
- `RulesImporter` upserts each rule into `rules` with `is_active=True`.
- Metrics are emitted (`rules_import_total`) and cache is invalidated.

## 3. Spot check

Run a quick SQL to ensure rows reference the latest ruleset:

```sql
select ruleset_version, count(*) 
from rules 
where ruleset_version like '%.%' 
group by 1 
order by max(updated_at) desc;
```

If you expect inactive/draft rows, re-run the script with `--include-inactive`.

## 4. Backfill specific rulesets

To re-import only one ruleset:

```powershell
python ..\..\scripts\sync_rulesets.py --ruleset-id <UUID>
```

Or to re-create a ruleset from a local JSON (bypassing Supabase):

```powershell
python scripts/import_rules.py Data/ucp600.json --ruleset-id <UUID> --activate
```

## 5. Rollback plan

If the sync fails mid-run:

1. Check `rules_audit` for the last successful `import` action.
2. Re-run the sync script with `--ruleset-id` for the affected entry.
3. If the normalized table is corrupt, truncate `rules` (non-production environments only) and run the active sync again.

Document every run in the deployment ticket, including:

- Command issued (`sync_rulesets` or `import_rules`)
- Number of rules inserted/updated
- Any warnings or errors printed by the script

