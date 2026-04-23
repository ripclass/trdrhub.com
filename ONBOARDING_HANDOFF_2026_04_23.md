# Onboarding refactor handoff — 2026-04-23 evening

Fresh-session continuity doc. Self-contained; assumes zero memory of
prior conversations. Read top to bottom, decide path 1 or path 2, execute.

## Where we left off

The 4-day onboarding refactor shipped to master. Backend schema + 3-question
wizard + routing + sort-priority + auto-complete hotfix are **real and
working**. Day 4's placeholder dashboards (agency, group overview,
enterprise group link) are **half-baked noise** that Ripon explicitly
called out as worse than not shipping:

> "the flow and dashboard is soooo lame... there are so many things wrong
> I can't even list them down... what can a sourcing agent do after landing
> that dashboard? there's nothing there, no sidebar... if we didn't do
> anything on new dashboards then it's fine, we will start."

The session ended on a decision point — rip the placeholders or build them
real. Ripon left without choosing.

## Live state (verify before assuming)

- **master:** `25d41a22` — "delete orphaned ImporterAnalytics.tsx + api/importer.ts".
  Check: `git log --oneline -5`.
- **Render (backend):** commit `4ee9e13f` or later live on
  `srv-d41dio8dl3ps73db8gpg`. `/onboarding/status` no longer auto-completes
  onboarding. Verify: `curl -s https://api.trdrhub.com/health/db-schema` returns
  `status: ok`.
- **Vercel (frontend):** last commit auto-deploys from master.
- **Test user broken state:** `jk@ith.com` (UUID `8c23fdf4-c6cb-4426-aefe-078edd1d7d8f`)
  signed up under the bug — has `business_activities=['exporter']` (server default)
  despite picking Agent. Recovery: `POST /api/onboarding/reset` with their JWT, then
  re-run the wizard. Works correctly after `4ee9e13f`.

## What's real — don't touch unless intentional

- `Company.business_activities` (text[]) + `Company.tier` (VARCHAR) + `Company.country` default.
  Migration `20260423_add_company_onboarding_fields` applied.
- `POST /api/onboarding/complete` — Pydantic schema + service + router wired.
- `apps/web/src/lib/lcopilot/activities.ts` — `ACTIVITY_PRIORITY` =
  `['agent', 'exporter', 'importer', 'services']` + `sortActivitiesByPriority()`.
  Mirrored in `apps/api/app/services/onboarding_service.py::_ACTIVITY_PRIORITY`.
- `apps/web/src/components/onboarding/OnboardingWizard.tsx` — 3-step modal
  wizard. Used by post-auth `/onboarding` page.
- `apps/web/src/pages/Register.tsx` — pre-auth 2-step flow (activities × tier
  × country, then email/password). Submits via `registerWithEmail` then
  `completeOnboarding`.
- `apps/web/src/components/lcopilot/WorkspaceSwitcher.tsx` — header dropdown,
  renders null for single-activity users. Actually useful.
- `apps/web/src/lib/lcopilot/routing.ts` — activity-based landing. `destinationForPrimaryActivity`.
- `/lcopilot/combined-dashboard` + `/lcopilot/enterprise-dashboard` are
  `<Navigate>` redirects (retired dashboards).
- 49/49 routing tests green (`lcopilotRouting.test.ts` + `onboarding-scenario-matrix.test.ts`
  + `loginRedirect.test.tsx`).

## What's placeholder noise — pending decision

| File | What it does today | What it would need to be real |
|---|---|---|
| `apps/web/src/pages/lcopilot/AgencyDashboard.tsx` | Empty-state card, disabled "Add supplier" button, supplier portfolio table scaffold. No sidebar. | Supplier CRUD, LC portfolio per supplier, agent re-papering workflow, dedicated sidebar. Backend supplier model + endpoints. ~1-2 days. |
| `apps/web/src/pages/lcopilot/GroupOverview.tsx` | Three em-dash KPI tiles + "shipping later" copy. | Cross-SBU KPI aggregation endpoint, drilldown. ~3-5 days. |
| `apps/web/src/components/lcopilot/EnterpriseGroupLink.tsx` | Header button tied to `useTier() === 'enterprise'`. Links to GroupOverview. | Only meaningful if GroupOverview is real. |
| `apps/web/src/lib/lcopilot/tier.ts` | Pure hook, harmless. | Useful even without the link — gates other enterprise features. |
| `apps/api/app/routers/agency.py` | Stub `GET /api/agency/suppliers → []`. | Real supplier model + CRUD. |

**Also feeding the noise**: `/lcopilot/agency-dashboard` route in App.tsx.

## Path 1 — rip the placeholders (fast, cleaner)

~30 min.

1. Delete `apps/web/src/pages/lcopilot/AgencyDashboard.tsx`
2. Delete `apps/web/src/pages/lcopilot/GroupOverview.tsx`
3. Delete `apps/web/src/components/lcopilot/EnterpriseGroupLink.tsx`
4. Optional: delete `apps/web/src/lib/lcopilot/tier.ts` (harmless but unused
   if the link is gone)
5. Optional: delete `apps/api/app/routers/agency.py` + unregister from `main.py`
6. Remove the two routes from `apps/web/src/App.tsx`
   (`/lcopilot/agency-dashboard` + `/lcopilot/group-overview`)
7. Update `ACTIVITY_DESTINATIONS` in `routing.ts` + `ACTIVITY_DASHBOARD` in
   `activeWorkspace.ts`: map `agent` → `/lcopilot/exporter-dashboard` (same
   as `services` does today)
8. Update `onboarding-scenario-matrix.test.ts` + `lcopilotRouting.test.ts`
   expectations: agent → exporter-dashboard
9. Update `ExporterDashboardLayout.tsx` + `ImporterDashboardV2.tsx` to
   drop the `headerExtras={<EnterpriseGroupLink />}` prop
10. Optional: drop the `headerExtras` slot on `DashboardLayout`
11. Commit + push. Run routing tests.

Net: activities still persist correctly, workspace switcher still works,
no dead pages for users to land on.

## Path 2 — build agency real (slower, product-forward)

~1-2 days on agency alone, longer for group overview. Requires a product
decision on what an agency dashboard MUST have on day 1. See Ripon's
prospect ranking — buying houses are a Tier-1 segment, so real build is
defensible, but do not start without a spec.

Minimum viable agency dashboard:
- Sidebar with nav: Dashboard / Suppliers / LCs / Billing / Settings
- Supplier list page with add/edit
- Per-supplier LC portfolio view
- Backend: Supplier model (id, name, country, contact), Supplier endpoints
  (GET list, POST create, GET detail)
- No AI features on day 1 — stays credit-free

If Path 2: start a new branch (`agency-dashboard-v1`), don't build in master.

## Two known bugs either path should address

1. **`use-auth.tsx::registerWithEmail` uses raw `fetch('/auth/register')`** —
   bypasses axios CSRF middleware, fails 403 silently. Zero
   `/auth/register` calls appear in Render logs during live signup tests.
   Fix: replace with `api.post('/auth/register', ...)` so the interceptor
   adds the CSRF header. This is a small surgery in `use-auth.tsx` around
   line 629. Test: fresh signup should show a POST /auth/register in
   Render logs.

2. **`completeOnboarding` loses the CSRF race on first call** — on a fresh
   signup, no prior `/auth/csrf-token` fetch has happened. The axios
   interceptor tries to fetch on-demand but there's an async window where
   the POST fires naked. Evidence: zero POST /api/onboarding/complete in
   Render logs during the 05:43 live signup window. Fix: `await` a CSRF
   prefetch explicitly in `Register.tsx::handleRegister` before the
   `completeOnboarding` call, or add explicit retry-on-403 with header
   refresh.

Both bugs mean signup silently writes nothing to the backend beyond the
Supabase user + auto-created-by-/auth/me User row. After `4ee9e13f` the
user just gets bounced to `/onboarding` to re-enter, which works, but
that's a bad first-impression UX.

## Starter commands

```bash
# Live state
git log --oneline -10
curl -s https://api.trdrhub.com/health/db-schema

# Deploy history
render deploys list srv-d41dio8dl3ps73db8gpg -o json | python -c "import json,sys; d=json.load(sys.stdin); print(d[0]['status'], d[0]['commit']['id'][:8], d[0]['commit']['message'].splitlines()[0][:80])"

# Routing tests
cd apps/web && npx vitest run src/__tests__/lcopilotRouting.test.ts src/__tests__/onboarding-scenario-matrix.test.ts

# Recover the jk@ith.com test user (needs their JWT)
# Or ignore — just test with a fresh signup, works correctly now.
```

## Don't re-litigate

- 3-question model is locked (activities × country × tier).
- ACTIVITY_PRIORITY order is locked (`agent > exporter > importer > services`).
  It's mirrored in two places; if you change it in one, change both.
- `/combined-dashboard` and `/enterprise-dashboard` are retired. Their
  `<Navigate>` redirects stay ≥90 days.

## Standing rules from CLAUDE.md + memory

- **TrdrHub is global** — no BD-specific defaults in UI / copy / validators.
  The `Register.tsx` "Local payment options in BDT" copy was legit (it's
  payment-gateway localisation, not a hardcode).
- **Extraction is a blind transcriber** — doesn't apply here but stays true.
- **Vercel plugin hook nags are false positives** — apps/web is a Vite
  SPA, not Next.js. Ignore `"use client"` suggestions.
- **Don't reinvent RulHub** — not onboarding-relevant.
- **Don't touch `J:\Enso Intelligence\ICC Rule Engine\`** — separate
  workspace.
- **No placeholder dashboards** — new rule from this session. See
  `memory/feedback_no_placeholder_dashboards.md`.
