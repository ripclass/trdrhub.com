# Onboarding Refactor — Fresh Session Resume

Strategic + execution handoff for the LCopilot onboarding redesign. Brainstorm + plan complete 2026-04-22 evening, not yet executed. Self-contained, assumes zero memory of prior conversations.

## Why this exists

Current 5-role onboarding (exporter / importer / combined / enterprise / bank) uses engineering categories instead of industry self-identification, misses the biggest underserved segment (sourcing/buying houses), has no jurisdiction layer, and conflates pricing tier with dashboard layout. Two of the five resulting dashboards (combined, enterprise) are orphaned (mock data, no sidebar links, last touched 2026-03-15) — they shouldn't exist as separate pages at all.

## Read first (in order, ~10 min)

1. `memory/project_lcopilot_onboarding_redesign.md` — ★★ critique of current model + proposed 3-question model + dashboard mapping + migration plan + execution sequencing
2. `memory/reference_trade_finance_actor_map.md` — ★ who exists in trade finance globally (informs why "agent" is a first-class persona)
3. `memory/project_prospective_clients_global_ranking.md` — ★ 15 customer segments ranked by revenue × ease-of-close + geographic launch order
4. `memory/project_importer_parity_shipped_2026_04_22.md` — Stream A's just-shipped importer baseline (architectural foundation you'll build on)
5. `memory/reference_render_migrations.md` — migration gotcha + how preDeployCommand now handles it

## Live state when this prompt was written

- **master:** check with `git log --oneline -5` — last commits include `07f449a8` (the /health/db-schema + preDeployCommand fix that resolved the 2026-04-22 workflow_type production incident)
- **Render backend:** `srv-d41dio8dl3ps73db8gpg` — preDeployCommand now runs `alembic upgrade head` automatically, so future migrations land cleanly
- **OpenRouter credits:** assumed still out (waiting 1-2 days from 2026-04-22 for Ripon to top up). Verify by curling RulHub probe — extraction work is gated on credits, but the onboarding refactor itself is credit-free.
- **/health/db-schema endpoint:** live, returns `{tables_checked: {validation_sessions, users, companies}, missing_columns: {}}` when clean, 503 + drift map when broken
- **Stream A (importer parity):** all 4 phases shipped + smoke-verified. See their continuity in `NEXT_SESSION_PROMPT.md` and `IMPORTER_RESUME_PROMPT.md`.

## Locked decisions (don't re-litigate)

| Decision | Choice |
|---|---|
| Storage of business_activities | `Company` model, PostgreSQL `text[]` with CHECK constraint |
| Storage of country | `Company.country` VARCHAR(2), ISO 3166-1 alpha-2 |
| Storage of tier | `Company.tier` VARCHAR(20), enum solo/sme/enterprise |
| Keep `workflow_type` on `ValidationSession`? | Yes, unchanged. New onboarding fields are company-level, orthogonal. |
| Combined + Enterprise dashboards | Delete (with 301 redirects, kept ≥90 days). Replace with header workspace switcher for multi-activity companies. |
| Routing | Activities-driven, not role-driven. 1 activity → land on that dashboard; 2+ → land on first + show switcher in header. |
| Multi-tab support | Active workspace persisted in `sessionStorage` (per-tab), so Meghna user can have export in one tab, import in another. |
| Agency dashboard | Skeleton only in this refactor (Day 4). Real build deferred until credits return + explicit sign-off on full agency spec. |
| Enterprise tier features (group rollup, RBAC, audit log) | Defer to next sprint. This refactor only wires the tier flag + one visible affordance. |

## Execution plan — 4 days, all credit-free

### Day 1 — backend schema + onboarding endpoint (~6 hours)

**Files:**
- `apps/api/app/models.py` — extend `Company`: `business_activities` (text[], NOT NULL, default `['exporter']`), `country` (VARCHAR(2), default `'BD'`), `tier` (VARCHAR(20), default `'sme'`). Add `BusinessActivity` and `BusinessTier` enums.
- `apps/api/alembic/versions/20260423_add_company_onboarding_fields.py` — new migration. `server_default` for atomic backfill. CHECK constraints for enum validity. Backfill from existing `role` field if present.
- `apps/api/app/services/onboarding_service.py` — new service.
- `apps/api/app/routers/onboarding.py` — `POST /api/onboarding/complete` accepting `{activities, country, tier}`. Wire into router registry in `main.py`.
- `packages/shared-types/src/api.ts` — Zod schemas.

**Verify:** `curl https://api.trdrhub.com/health/db-schema` after deploy → confirm new columns present in `companies` table count.

### Day 2 — frontend onboarding wizard rewrite (~4 hours)

**Files:**
- `apps/web/src/pages/auth/OnboardingWizard.tsx` (or wherever it lives) — rewrite as 3 sequential steps:
  - Q1: business activities (multi-select checkboxes)
  - Q2: country (search-as-you-type, 15+ options)
  - Q3: team size (radio, with skip → defaults to SME)
- `apps/web/src/lib/lcopilot/routing.ts` — derive landing dashboard from `business_activities`. Multi-activity → first activity's dashboard.
- `apps/web/src/hooks/use-onboarding.ts` — wraps the new endpoint, optimistic update.

### Day 3 — header workspace switcher + dead route cleanup (~4 hours)

**Files to create:**
- `apps/web/src/components/lcopilot/WorkspaceSwitcher.tsx` — header dropdown shown when `business_activities.length >= 2`.
- `apps/web/src/lib/lcopilot/activeWorkspace.ts` — sessionStorage hook for per-tab active workspace.

**Files to delete + redirect:**
- `apps/web/src/pages/CombinedDashboard.tsx` → 301 from `/lcopilot/combined-dashboard` to `/lcopilot/exporter-dashboard`
- `apps/web/src/pages/EnterpriseDashboard.tsx` → 301 from `/lcopilot/enterprise-dashboard` to `/lcopilot/exporter-dashboard`
- Update `App.tsx` routes table accordingly. Keep redirects ≥90 days.

**Sidebars:** when company has 2+ activities, render `WorkspaceSwitcher` above sidebar; sidebar items themselves stay activity-specific.

### Day 4 — agency placeholder + enterprise tier flag + smoke (~4 hours)

**Files:**
- `apps/web/src/pages/lcopilot/AgencyDashboard.tsx` — empty state with "Add supplier" CTA + placeholder portfolio table. Route: `/lcopilot/agency-dashboard`.
- `apps/api/app/routers/agency.py` — stub `GET /api/agency/suppliers` returning `[]` (real impl deferred).
- `apps/web/src/lib/lcopilot/tier.ts` — `useTier()` returns solo/sme/enterprise. Show "Group overview" link in header for tier=enterprise.
- `apps/web/src/pages/lcopilot/GroupOverview.tsx` — placeholder page (real cross-SBU rollup deferred).

**Smoke test all four roles end-to-end:**
- Exporter (single activity) → lands on exporter dashboard, no switcher
- Importer (single) → lands on importer dashboard, no switcher
- Multi (export + import) → lands on exporter, switcher visible, can flip to importer
- Agent → lands on agency dashboard placeholder
- Verify combined/enterprise URLs 301 to exporter

## What NOT to do in this refactor

- Build the full agency dashboard (skeleton only — real build needs AI credits + explicit spec sign-off)
- Build enterprise group-overview cross-SBU rollup (placeholder only — needs new backend endpoint)
- Country-specific rule packs in RulHub (separate workspace's job; just send `country` to RulHub via `validation_execution.py` — 5-min wire-up on Day 1)
- Pricing UI / billing changes (separate concern)
- C&F / freight forwarder dashboards (deferred per prospect ranking)

## Open balls (not blocking onboarding refactor)

| Item | Owner | Status |
|---|---|---|
| ISBP821-A31 (invoice unsigned) still silent | RulHub session | Flagged for separate investigation |
| OpenRouter credit top-up | Ripon | Waiting 1-2 days from 2026-04-22 |
| Stream A's corpus generator MT700 layout bug | Stream A | Documented in their `NEXT_SESSION_PROMPT.md`, ~30 min fix |
| Stream A's deferred Playwright specs | Stream A | Three e2e specs to write using new fixtures |

## Migration from current model

| Current `role` value | New onboarding fields |
|---|---|
| `exporter` | `activities=['exporter']`, `country='BD'`, `tier='sme'` |
| `importer` | `activities=['importer']`, `country='BD'`, `tier='sme'` |
| `combined` | `activities=['exporter','importer']`, `country='BD'`, `tier='sme'` |
| `enterprise` | `activities=['exporter','importer']`, `country='BD'`, `tier='enterprise'` |
| `bank` | parked, no migration |

Existing `role` column stays during this refactor as a compatibility shim; deprecate in a follow-up release after frontend fully derives from `business_activities`.

## Reminders (standing rules)

- **Don't touch `J:\Enso Intelligence\ICC Rule Engine\`** — separate Claude workspace.
- **No hardcoded Python validators per discrepancy class** — AI Examiner is the pattern.
- **Extraction is a blind transcriber** — no format validation at extraction, no jurisdiction hardcoding.
- **Vercel plugin hook nags are false positives** — Vite + FastAPI repo, not Next.js.
- **Inline execution**, not subagents (per Ripon's preference).
- **Stream A's `NEXT_SESSION_PROMPT.md` covers their continuity** — don't trample it. This file is for the strategic / onboarding refactor scope only.

## Greenlight check before starting

Confirm with Ripon:
1. AI credits status (informational — Day 1-4 don't need credits)
2. Greenlight to start Day 1 (backend schema + endpoint, no UI changes yet)
3. Whether the activity list, country list, or tier names need adjustment before the migration goes in (easier to change strings now than after data lands)

Then start Day 1.

## First action commands

```bash
git log --oneline -5
curl -s https://api.trdrhub.com/health/db-schema
cat memory/project_lcopilot_onboarding_redesign.md
ls apps/api/app/models.py apps/api/alembic/versions/ | head
```
