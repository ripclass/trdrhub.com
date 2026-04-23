# Register Wizard Alignment — Day 2 Follow-up

**Filed:** 2026-04-23 after live-signup verification of the onboarding refactor.
**Status:** Not yet executed. Self-contained. Assume zero memory of prior conversations.

## The gap

The 4-day onboarding refactor (merged in `master` as of `6037682f`) rewrote the
**post-auth** wizard at `apps/web/src/components/onboarding/OnboardingWizard.tsx`
to use the new 3-question model:

- Activities: `exporter / importer / agent / services` (multi-select)
- Country: 15 ISO-2 markets, no default
- Tier: `solo / sme / enterprise`

It persists via `POST /api/onboarding/complete` into new `Company` columns
`business_activities` (text[]) + `tier` (VARCHAR(20)) + existing `country`.

**What it missed:** `apps/web/src/pages/Register.tsx` has its own inline
pre-auth wizard with the **legacy** category set. New signups never touch the
refactored component. Live-verified 2026-04-23 by loading `/register`:

- Business Type options: `Exporter / Importer / Both / Logistics` (4 of them, and
  "Both" + "Logistics" aren't in the new `BusinessActivity` enum)
- Team Size options: `Small / Growing / Established / Enterprise` (four, mapped
  to legacy company.size values `sme / medium / large / enterprise`)
- Country: defaults to `BD` with `✓ Local payment options available in BDT` — the
  exact "Bangladesh-specific defaults in UI" the CLAUDE.md standing rule
  prohibits.

## What Register.tsx does on submit (today)

Trace from `apps/web/src/pages/Register.tsx::handleRegister`:

1. Calls `registerWithEmail(email, password, fullName, role, { companyName,
   companyType, companySize, businessTypes, country, currency, paymentGateway })`
   from `apps/web/src/hooks/use-auth.tsx` — this creates the Supabase user +
   backend `Company` row. Writes the legacy shape into `Company.event_metadata`
   and into user onboarding_data via the auth flow.
2. Calls `updateProgress()` — hits **`PUT /onboarding/progress`** (legacy endpoint),
   NOT `POST /onboarding/complete` (the endpoint Day 1 shipped).
3. Sets `complete: true` (for small/growing, skipped for "established/enterprise"
   which takes the team-setup detour).
4. Navigates to `/lcopilot/dashboard` which then resolves via `resolveLcopilotRoute`.

Because step 2 writes only `business_types` + `company.size` into
`user.onboarding_data` JSONB (not the new `Company.business_activities` /
`Company.tier` columns), new signups post-Day-1 have:

- `Company.business_activities = ['exporter']` (server_default) — almost always
  wrong for non-exporter signups
- `Company.tier = 'sme'` (server_default) — loses small/growing/established/enterprise
  nuance
- `Company.country` — correctly populated (this one already worked)

Day 2's `routing.ts` falls back to the legacy shape in `user.onboarding_data`,
so users are still routed correctly. But all the new-shape consumers
(`WorkspaceSwitcher`, `useTier()`, `EnterpriseGroupLink`, `/api/agency/suppliers`
scope) read from `details.activities` / `Company.tier` — those read empty for
brand-new users. The multi-activity switcher in particular won't appear for
"Both" signups because `business_activities` stays at `['exporter']`.

## What needs to change

### Frontend — `Register.tsx`

Swap the step-1 category set:

| Today | Target |
|---|---|
| `CompanyType` = exporter / importer / both / logistics | `BusinessActivity[]` multi-select — exporter / importer / agent / services. UX: 4 toggle-buttons, users pick one OR multiple (so "Both" becomes `[exporter, importer]` naturally). |
| `CompanySize` = small / growing / established / enterprise | `BusinessTier` = solo / sme / enterprise. "Skip → SME" affordance per the `OnboardingWizard` rewrite. |
| Country default `BD` + `Local payment options in BDT` copy | No default. Placeholder `"Select your country"`. Currency/payment-gateway hints can still appear after selection, but don't pre-bias. |
| Country list has 20 markets | Reconcile with the 15 locked in `memory/project_lcopilot_onboarding_redesign.md`. Register.tsx currently has `NP, MY, ID, TH, PH` that the post-auth wizard lacks; the post-auth wizard has `GB, US, DE, NL` that Register lacks. Pick one canonical list and share it. Recommend extracting into `apps/web/src/lib/lcopilot/countries.ts` and importing from both places. |

Both the type and size options should be sourced from
`packages/shared-types/src/api.ts::BusinessActivitySchema` /
`BusinessTierSchema` (already exported as Zod), not redeclared inline. Same
for the country list.

Drop the `getBackendRole` / `getBusinessTypes` / `mapSizeToBackend` helpers —
after alignment, the values ARE already the backend names.

### Frontend — `Register.handleRegister`

Replace the `updateProgress()` call with `completeOnboarding()` from
`apps/web/src/api/onboarding.ts` (added in `43343125`):

```ts
await completeOnboarding({
  activities,        // BusinessActivity[]
  country,           // ISO-2 uppercase
  tier,              // BusinessTier
  company_name: formData.companyName,
})
```

Drop the `requiresTeamSetup` branch — team setup was only meaningful under the
old "tenant_admin → /team-setup" flow which Day 3 retired alongside the
combined/enterprise dashboards.

### Frontend — `registerWithEmail` in `use-auth.tsx`

`companyInfo` signature accepts `companyType` + `companySize` + `businessTypes`
— three parallel representations of the same fact. Collapse to:

```ts
companyInfo?: {
  companyName?: string
  activities: BusinessActivity[]
  tier: BusinessTier
  country: string
}
```

Verify the server-side handler this calls (probably `POST /auth/register` in
`apps/api/app/routers/auth.py`) also accepts the new shape OR have the caller
do a separate `POST /api/onboarding/complete` after registration (simpler — no
auth-router surgery).

### Backend — minor or none

If the frontend calls `POST /api/onboarding/complete` after registration, the
backend needs nothing new — Day 1 already ships that endpoint. If the frontend
keeps writing through the auth-register path, `apps/api/app/routers/auth.py`
and whichever service handles `companyInfo` need to write
`Company.business_activities` + `Company.tier` directly.

Recommended: do it all on the frontend with the explicit two-call
`registerWithEmail` → `completeOnboarding` sequence. Cleaner contract, no
backend schema duplication.

## Risks

1. **In-flight registrations during deploy.** Users mid-signup when the
   frontend bundle swaps over will see old + new field names briefly. No DB
   corruption since the old progress endpoint still exists, but UX hiccup.
   Mitigate by deploying behind a feature flag, OR accept the <5min exposure.

2. **Historical data.** Users registered between Day 1 deploy (2026-04-23) and
   this fix will have `business_activities = ['exporter']` + `tier = 'sme'`
   defaults regardless of what they actually picked. One-time backfill from
   `event_metadata->>business_type` covers them — the Day 1 migration
   (`20260423_add_company_onboarding_fields`) already does exactly this for
   pre-existing rows. Worth re-running as a job after this fix lands to sweep
   up the recent-signup rows:

   ```sql
   UPDATE companies
   SET business_activities = CASE
       WHEN event_metadata->>'business_type' = 'both'     THEN ARRAY['exporter','importer']::text[]
       WHEN event_metadata->>'business_type' = 'exporter' THEN ARRAY['exporter']::text[]
       WHEN event_metadata->>'business_type' = 'importer' THEN ARRAY['importer']::text[]
       WHEN event_metadata->>'business_type' = 'logistics' THEN ARRAY['services']::text[]  -- legacy "logistics" collapses to services
       ELSE business_activities
   END,
   tier = CASE
       WHEN event_metadata->>'company_size' = 'enterprise' THEN 'enterprise'
       WHEN event_metadata->>'company_size' IN ('small','sme') THEN 'sme'
       WHEN event_metadata->>'company_size' IN ('medium','growing','established','large') THEN 'sme'  -- medium/large collapse to sme
       ELSE tier
   END
   WHERE created_at > '2026-04-23'::date
   ```

3. **"Logistics" was a first-class option.** If a current customer picked
   Logistics at signup, they get `activities=['services']` after the backfill.
   That's the closest match but not identical — Logistics was effectively
   "freight-forwarder who uses LCs", which is adjacent to the `services` activity
   ("freight forwarder / customs broker / LC consultant"). Accept the collapse.

## Execution plan

Four steps, roughly 4 hours total:

1. **Extract shared lists** — `apps/web/src/lib/lcopilot/countries.ts` with the
   canonical 15-market list. Both `OnboardingWizard.tsx` and `Register.tsx`
   import from there.

2. **Rewrite `Register.tsx` step 1** — activities (multi-select), tier (3-way
   radio + Skip→SME), country (Select from shared list, no default). Update
   local `CompanyType` + `CompanySize` types to re-export the shared enums.

3. **Collapse `registerWithEmail` signature** — drop `companyType` +
   `companySize` + `businessTypes`; accept `activities` + `tier`. Update
   `Register.handleRegister` to call `registerWithEmail` then
   `completeOnboarding`.

4. **Backfill job + verify** — run the UPDATE above as a Render one-off job,
   then `curl /health/db-schema` + `gh pr create` → merge → Playwright-smoke a
   fresh signup across 4 activity paths.

## What NOT to do

- Don't refactor `auth.py` registration endpoint unless the two-call frontend
  sequence turns out to be slow or racy. Keep server changes at zero.
- Don't remove `updateProgress()` or `PUT /onboarding/progress` — bank KYC flow
  still uses it, and the post-auth wizard's hydrate-from-legacy-state path
  depends on the shape it writes.
- Don't remove `getBackendRole` tenant_admin mapping from anywhere downstream
  until you've grepped for `tenant_admin` usage. The role column has a CHECK
  constraint that includes it.

## Dependencies

- Branch from current `master` (commit `6037682f` or later).
- No new AI credits needed.
- No new migration — backfill is an idempotent UPDATE, not a schema change.

## Greenlight check

Before starting:

1. Confirm with Ripon that the 15-market list is final (any additions now
   avoids a second pass).
2. Confirm "Logistics" collapses to `services` (vs. e.g. `exporter` or a new
   activity value).
3. Confirm two-call frontend sequence vs. single-call server-side aggregation.
