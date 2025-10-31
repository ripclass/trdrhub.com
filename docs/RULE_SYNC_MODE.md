# Rule Sync Mode (Local + RulHub Hybrid)

This supersedes LOCAL_RULE_MODE.md and documents both offline and online (RulHub) flows.

## Modes

- Offline (default): `USE_RULHUB_API=false` → validate using local Postgres `rules_registry`.
- Online: `USE_RULHUB_API=true` → fetch latest rules from RulHub API at validation time; weekly background sync persists to DB.

## Environment Toggles

```env
USE_RULHUB_API=false
RULHUB_API_URL=https://api.rulhub.com
RULHUB_API_KEY=
```

Set these in `apps/api/.env` (or production env).

## Setup

1) DB migrate and seed (for offline fallback):
```bash
cd apps/api
alembic upgrade head
cd ../..
python scripts/seed_rules.py
```

2) Run API:
```bash
cd apps/api
uvicorn main:app --reload
```

## Validate Endpoint

POST `http://localhost:8000/api/validate/`

- Offline example:
```json
{"document_type":"lc","consistency":true}
```

- Invoice example:
```json
{"document_type":"invoice","date_format":"15/10/2025"}
```

## Hybrid Logic

- When `USE_RULHUB_API=true`, service tries RulHub first; on error, falls back to local DB.
- When `USE_RULHUB_API=false`, only local DB is used.

## Auto-Sync

- Weekly job runs every Monday at 03:00 server time to sync rules for common document types.
- Manual trigger (admin only): `POST /rules/sync`

Example Render cron (CLI):
```bash
render cron create "rulhub-weekly-sync" --schedule "0 3 * * MON" \
  --command "python -m app.jobs.rulhub_sync_job"
```

## Migration Notes

- Keep `code` stable as external identifier to enable upserts.
- Local schema mirrors RulHub fields to simplify migration.

## Troubleshooting

- If API is enabled but URL/key missing, fetch will raise and fallback to DB.
- Ensure outbound network access for API mode.
