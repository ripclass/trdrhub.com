# Admin Dashboard Status

_Updated: 2025-11-14_

This note summarizes which parts of the admin (`/admin`) experience are powered by live production data and which pieces intentionally degrade when data is unavailable.

## Production-backed

- **Ruleset management**
  - Upload → validates JSON schema, stores file in Supabase Storage bucket `rules/`
  - List/Publish/Rollback → reads/writes from `public.rulesets` and `ruleset_audit`
  - Errors bubble up to UI with actionable messages
- **Operational alerts**
  - `/admin/ops/system-alerts` exposes persisted alerts stored in `system_alerts`
  - Auto-generates alerts for failed validation sessions (last 24h)
  - Acknowledge/Snooze actions update real records
- **Operational jobs**
  - `/admin/jobs/*` endpoints read/write from `jobs_queue`, `jobs_dlq`, `jobs_history`
  - Retry/Cancel actions modify queue entries
- **Dashboard KPIs**
  - `/admin/dashboard/kpis` aggregates from:
    - `validation_sessions` (volume/success rate)
    - `companies` (active tenants)
    - `rulesets` (published rulebooks)
    - `system_alerts` (open alerts)
- **Recent activity**
  - `/admin/dashboard/activity` surfaces latest audit entries recorded via `/admin/audit/log-action`
- **Audit logging**
  - `useAdminAudit` now posts lightweight events to `/admin/audit/log-action`

## Graceful fallbacks

- **Ops metrics grid**
  - If `/admin/jobs/queue/stats` fails, UI shows descriptive error instead of mock data
- **Alerts list**
  - Displays inline warning when API fails
  - No longer injects placeholder “sample” alerts
- **Activity feed**
  - Shows “No recent activity recorded” when dataset is empty

## Mock-only (by design)

- **System settings** panel still uses static defaults (backend endpoint not implemented).
  - API returns stub; UI labels clearly mark it as such.
- **Advanced sections** (LLM prompts, connectors, billing adjustments, etc.) remain hidden/inactive until backend support exists.

## Toggling data source

The frontend now honors `VITE_ADMIN_DATA_SOURCE`. By default it points to `"api"`. To use mock data locally:

```bash
VITE_ADMIN_DATA_SOURCE=mock npm run dev
```

In production builds this flag is **not** set, so the API implementation is always used.

## Logging & monitoring

- All admin endpoints log at INFO on success and ERROR on failures (request ID + actor ID).
- Ruleset uploads log validation metadata and storage path.
- System alerts sync/auto-resolution emit structured logs for observability.

## Cleanup tooling

- `apps/api/scripts/cleanup_demo_data.py` prints (or executes with `--apply`) SQL statements that remove demo/test users, companies, validation sessions, and alert records matching supplied email patterns.

