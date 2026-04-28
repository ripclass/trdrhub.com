# Launch checklist — 2026-07-25

Phase A13 deliverable. Run through this in order during the
launch-prep week (2026-07-20 → 2026-07-25).

## Code freeze: 2026-07-24 Friday

After freeze, only critical bugfixes. Anything else gets logged to
the v1.1 backlog.

---

## 1. Backend deploy + migrations

```bash
git push origin master
# Render auto-deploys to staging; promote to prod when staging is green.
render jobs create srv-d41dio8dl3ps73db8gpg --start-command "alembic upgrade head"
```

Pending migrations to verify on prod (verify table presence via
`/health/db-schema`, re-run the job if any are missing — see
`reference_render_migrations.md`):

- `20260428_add_user_notifications` — Phase A3
- `20260429_add_agency_suppliers_buyers` — Phase A5
- `20260430_add_services_clients_time` — Phase A8

## 2. Environment variables on Render

| Var | Purpose | Required |
|---|---|---|
| `DATABASE_URL` | Postgres | yes |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | Auth | yes |
| `OPENROUTER_API_KEY` | LLM provider | yes |
| `USE_RULHUB_API=true` + `RULHUB_API_KEY` | Validation rules | yes (RulHub down → fall back to local validators) |
| `SMTP_HOST` + `SMTP_USERNAME` + `SMTP_PASSWORD` + `SMTP_FROM_EMAIL` | Email delivery (notifications, repaper invites) | recommended |
| `FRONTEND_URL` | Used in email links | yes (default `http://localhost:5173` is wrong on prod) |
| `BULK_VALIDATE_STORAGE_DIR` | Bulk uploads + repaper file storage | recommended |

## 3. Vercel feature flags

Set on the Vercel project (or via `vercel env add`) for the
production deployment. Default-off flags can be flipped on once
each persona's smoke pass is green:

| Flag | Phase | Default for launch |
|---|---|---|
| `VITE_LCOPILOT_BULK_VALIDATION` | A1 | ON |
| `VITE_LCOPILOT_DISCREPANCY_WORKFLOW` | A2 | ON |
| `VITE_LCOPILOT_NOTIFICATIONS` | A3 | ON |
| `VITE_LCOPILOT_AGENCY_REAL` | A5/A6/A7 | ON for agency-tier customers |
| `VITE_LCOPILOT_SERVICES_REAL` | A8/A9 | ON for services-tier customers |
| `VITE_LCOPILOT_ENTERPRISE_TIER` | A10 | ON for enterprise tenants |
| `VITE_LCOPILOT_IMPORTER_V2` | A2 (importer parity) | ON |

## 4. Smoke matrix run

Hit the deployed API after each significant change:

```bash
# Public surface only (no auth needed)
python scripts/smoke_matrix.py --api https://api.trdrhub.com --public-only

# With a real Supabase JWT — runs the full read-only matrix as one
# persona. Repeat per persona test account for the full sweep.
python scripts/smoke_matrix.py --api https://api.trdrhub.com --token "$JWT"
```

The script exits non-zero on any failure. CI can wrap this for the
nightly green-build alarm.

## 5. Persona × tier × country sample matrix (manual)

Sample 30 of the 270 combos by hand. Each cell:

1. Fresh signup → wizard → land on correct dashboard
2. Run a single validation
3. Run a bulk validation
4. Verify notifications fire (bell + email if SMTP up)
5. Verify quota enforces (Solo at 10, SME at 50, Enterprise unlimited)
6. Verify lifecycle state transitions
7. Verify discrepancy workflow + repapering
8. Verify enterprise tier features render only for enterprise users

Suggested sample (Tier × Country × Persona):

| Persona | Tier | Country |
|---|---|---|
| exporter | solo | BD |
| exporter | sme | IN |
| exporter | enterprise | US |
| importer | solo | UAE |
| importer | sme | VN |
| importer | enterprise | GB |
| agent | sme | BD |
| agent | enterprise | IN |
| services | sme | BD |
| services | enterprise | UAE |
| exporter+importer | sme | VN |
| exporter+agent | enterprise | US |
| importer+services | enterprise | GB |
| all-four | enterprise | BD |
| ... | ... | ... |

## 6. Bug bash week (2026-07-20 → 2026-07-23)

Internal team runs through every flow, logs bugs to
`https://github.com/ripclass/trdrhub.com/issues` with labels:

- `bug-bash` — discovered during this week
- `priority:critical` — must-fix before launch
- `priority:major` — should-fix; ship-deferred
- `priority:minor` — log for v1.1

Daily triage: critical → assign + start; major → estimate;
minor → backlog.

**Hold launch on any open critical.**

## 7. UAT (concurrent with bug bash)

Friendly customers sign up and try the full product.
Capture feedback in `docs/UAT_2026_07.md`. Aim:

- 1 BD exporter (solo or SME)
- 1 BD importer
- 1 BD or IN agent
- 1 services consultant
- 1 enterprise tenant (multi-activity)

**Done criterion:** every UAT customer reaches their first
successful validation in under 10 minutes from signup.

## 8. Launch week

- **2026-07-24 Fri:** code freeze; final smoke run on staging.
- **2026-07-25 Sat:** weekend final QA, all feature flags reviewed.
- **2026-07-26 Sun:** production deploy with all flags ON, monitor.
- **2026-07-27 Mon:** public launch announcement.
- **2026-07-28 onwards:** support + monitor + log v1.1 backlog.

## 9. Day-of monitoring

- `/api/status` ping every 30s (Pingdom or equivalent).
- Sentry / equivalent alarms wired for 5xx spikes.
- DB connection pool monitoring.
- LLM provider usage cost alarm.
- On-call rotation for the launch weekend.

## 10. Roll-back plan

Every feature flag is reversible. Flipping a flag off in Vercel +
redeploy reverts to the prior surface within ~3 minutes. For
data-layer issues, the latest pre-launch DB snapshot lives at
[paste backup ref here] and can be restored via Supabase point-
in-time recovery.

## 11. v1.1 backlog seeds

These ship after launch — don't gate the launch on them:

- Failure-mode degradation queue (currently the pipeline catches LLM
  errors gracefully but doesn't auto-retry on 429).
- Bulk action bar (approve-all-clean / repaper-all / per-supplier
  PDFs) — plumbed in A6 slice 3 deferral note.
- Monthly aggregate PDF in agency reports — covered by per-supplier
  + per-buyer roll-ups for v1.
- Settings UX completeness (default issuing bank, email signature,
  branding logo upload) — endpoints exist via existing routers; UI
  pending.
- Multi-entity enterprise hierarchy (parent / subsidiary group
  overview).
- Real Stripe checkout wiring on the QuotaStrip "Upgrade" CTA
  (currently links to `/pricing`).
