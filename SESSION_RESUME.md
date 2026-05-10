# Session resume — UI/UX housekeeping + pricing restructure (2026-05-10)

**Last updated:** 2026-05-10
**State at commit:** `c56b4e01` (billing-UI tier labels) — branch `master`, pushed. Migration `20260510` applied on Render (see below).
**Active phase:** Path A build = 100% shipped (A1-A13). Launch-prep in flight (~10 weeks to 2026-07-25). This session shipped: brand housekeeping + importer-dashboard bug fixes + the clean-sheet LCopilot pricing restructure — **now complete end-to-end** (backend ✅ + frontend reconciliation ✅ + TRDR landing ✅ + public `/api/check` + `/check` lead-magnet ✅ + billing-UI tier labels ✅). The only remaining pricing-restructure loose ends are v1.1 / polish (Agency toggle on the secondary pricing components, real prices in `UpgradeModal` — both deferred with self-serve Stripe checkout).

---

## Resume prompt

```
The LCopilot pricing restructure is complete (last commit c56b4e01). Nothing
left on it except v1.1/polish: the Trader/Agency toggle on the secondary pricing
components (trdr-pricing-section.tsx — Pricing.tsx is dead, ToolPricingSection is
parked tools), and real prices in UpgradeModal/PLAN_DEFINITIONS (will be reworked
with self-serve Stripe checkout, v1.1 backlog). So pick from the launch-prep
options instead — see memory: project_launch_prep_options_2026_05_02.md and the
LAUNCH_CHECKLIST_2026_07_25.md / EXECUTION_PLAN_PATH_A_2026_04_25.md at repo root.
Standing rules still in force: push every commit immediately; new backend
migration -> `render jobs create srv-d41dio8dl3ps73db8gpg --start-command
"alembic upgrade head"` then verify /health/db-schema; keep Sonnet 4.6 / Opus,
never downgrade models for cost.
```

**Migration 20260510 — ✅ APPLIED on Render trdrhub-api 2026-05-10 13:52 UTC.** First attempt failed on the pre-existing `ck_companies_tier_valid` CHECK constraint (it only allowed `('solo','sme','enterprise')`) → fixed in commit `5b665fac` (drop → UPDATE → re-create constraint with the 7 new values), redeployed, re-ran, succeeded. `/health/db-schema` = ok. **141 company rows migrated `sme` → `business`** (25 LCs/mo, was 50) — mostly auto-created/test rows, but if any are real paying SME customers, grandfather them (`company.quota_limit = 50` or bump to `enterprise`). Future backend deploys with a new migration still need a manual `render jobs create srv-d41dio8dl3ps73db8gpg --start-command "alembic upgrade head"` (no auto hook).

---

## What shipped today (19 commits, `93c8a394..c56b4e01`)

### Brand-drift housekeeping (the "everything's bluish, not our brand" complaint)
| Commit | What |
|---|---|
| `9e513911` | LcopilotRouter post-login splash + `index.css` light-mode sidebar tokens → brand (`#00261C` deep green / `#B2F273` lime / `#EDF5F2` mint). The CSS token change flips every shadcn sidebar brand-true in light mode in one edit. |
| `292064cc` | Adopt the DocGenerator sidebar pattern (hardcoded brand classes) in Exporter / Importer / Agency / Bank sidebars |
| `64c9b82f` | Retire `/hub` — `/hub` + `/hub/*` now redirect to `/lcopilot/dashboard` (kills the off-brand multicolor "all tools" grid); strip "Back to Hub" links from the sidebars. Hub page files left as dead code (other tools launch over 6 months). |
| `c487424c` | Delete legacy `Dashboard.tsx` (mock "Dhaka Exports Ltd" data); `/dashboard` → redirect; recolor the 3 highest-drift LCopilot results components (`HowToFixSection`, `ExporterIssueCard`, `ExtractionReview`) to brand |
| `3a4cfcb2` | Two more loaders missed in `9e513911` — `LcopilotBetaRoute` + `RequireAuth` ("Loading your dashboard…" / "Checking your session…") were still slate-blue |

### Importer dashboard bugs (Ripon walked the dashboard and found broken paths)
| Commit | What |
|---|---|
| `bdc4fea3` | "View all →" linked to non-existent `/reviews` (404) → removed. Per-row "View →" hardcoded `/lcopilot/results-v2/${id}` for every session → now branches by `workflow_type`: importer rows → `/lcopilot/import-results/${id}`, exporter rows → `/lcopilot/exporter-dashboard?section=reviews&jobId=${id}` (keeps the sidebar). `ExporterResultsV2` error-state "Back to Upload" went to legacy `/lcopilot/upload` → now `/lcopilot/dashboard`. |
| `c3dfa8bb` | Remove the placeholder Settings tab from the importer sidebar (was a dead-end "No importer-specific settings yet" card — violated the no-placeholder-dashboards rule) |
| `d69fa73a` | Billing tab showed "Billing data is temporarily unavailable" for most users — root cause was a frontend↔backend enum drift (backend `Company.plan` ∈ free/pay_per_check/monthly_basic/monthly_pro/enterprise; frontend `normalizePlanType` only matched FREE/ENTERPRISE → returned null → empty fallback). Added a `tier` field to `/billing/company` (derived from `company.tier`, falls back to mapping `plan`); broadened `normalizePlanType` to accept all three string shapes; `BillingOverviewPage` prefers `info.tier`. *(Note: the new pricing restructure below supersedes the tier-name mapping introduced here — see the spec §8 item 5.)* |

### Pricing restructure — the big one
| Commit | What |
|---|---|
| `dde0df78` | Design spec: `docs/superpowers/specs/2026-05-10-lcopilot-pricing-restructure-design.md` (brainstorming session) |
| `f16e9ae5` | **Backend.** `company.tier` is now the 7-value billing enum (`payg`/`solo`/`business`/`enterprise`/`agency_starter`/`agency_pro`/`agency_enterprise`); new `BusinessSize` enum for the onboarding Q3 "company size" answer + `starting_billing_tier()` mapping; `entitlements.py` rewrite (quota/seat/overage maps for all 7 tiers, agency fair-use soft-cap advisory log, default → `business`); `/api/entitlements/current` returns `overage_rate_usd`; `billing_service._resolve_tier` updated; migration `20260510_pricing_restructure_tier` (`sme`→`business`, default→`payg`, logs `sme` count). |
| `64277e47` | **Frontend pt 1.** `lib/pricing.ts` rewritten as the single source of truth — `PRICING_TIERS` = 3 trader tiers + `AGENCY_TIERS` + `track`/`seatBased`/`custom`/`overageRateUsd`/`upgradeToId`; `PAY_PER_USE.lc_validation` 8→12; helper exports preserved. `Index.tsx` pricing cards derived from it; "Free $0/forever" card + the "2 vs 5 free LCs" self-contradiction scrubbed. |
| `120ed3c9` | **Frontend pt 2.** `PricingPage.tsx` Trader/Agency toggle + shared `<PricingCard>` + Enterprise/Agency-Enterprise wide card + FAQ rewrite (no "14-day free trial"). `QuotaStrip.tsx` 7-value tiers, three states (pool bar + overage line / PAYG line / agency "Unlimited (fair use)" pill), brand-lime bar. `entitlementsApi.ts` `overage_rate_usd`. `types/billing.ts` `normalizePlanType` folds the 7 new tiers into `PlanType`. |
| `5b665fac` | **Migration fix + applied.** First migration run failed on the pre-existing `ck_companies_tier_valid` CHECK constraint; migration now drops → updates → re-creates it with the 7 new tier values. Redeployed + re-ran on Render → succeeded. **141 company rows `sme` → `business`** (mostly test rows; grandfather any real paying ones). `/health/db-schema` ok. |
| `0cda613d` | **TRDR landing pricing block.** `trdr-pricing-section.tsx` (the `/trdr` platform landing) — Enterprise now shows its real $699/mo + "volume bands above 150 LCs/mo" (was mislabeled "Custom"); "14-day free trial" copy (×3) → "pay-as-you-go from $12/LC, no card to start, metered per LC presentation"; CTAs → "Start <tier>" / "Talk to Sales"; stray `border-gray` → `border-border`. |
| `a0efcb81` | **Public free LC checker — the lead magnet.** Backend: `app/routers/public_check.py` (`POST /api/check` — multipart, runs the full pipeline anonymously via the `demo@trdrhub.com` sentinel user so the pipeline's billing/quota/usage code already special-cases it → zero pipeline edits → returns the trimmed `{verdict, verdict_label, verdict_color, finding_count, top_findings:[≤2], signup_cta}`; `GET /api/check/availability` non-consuming probe; kill switch `settings.PUBLIC_LC_CHECK_ENABLED`). `app/utils/anon_rate_limit.py` — Redis-backed per-IP-per-path 1/24h counter (the generic in-memory `RateLimiterMiddleware` can't do that; un-rate-limited public LLM endpoint = unbounded spend); fails closed (503) if Redis is configured-but-unreachable, open if not configured (local). `main.py` mounts it + CSRF/audit-exempt. `tests/public_lc_check_test.py` — 12 tests. Frontend: `pages/CheckPage.tsx` (public, brand-themed, marketing shell, drag/drop → trimmed verdict card → sign-up gate; handles the 1/IP/24h limit), `lib/lcopilot/publicCheckApi.ts` (plain-fetch, no auth/CSRF), `/check` route in `App.tsx`, "try it free" callout on `PricingPage`. No new migration. |
| `c56b4e01` | **Billing-UI tier labels.** `lib/billing/tierDisplay.ts` — shared `BILLING_TIER_DISPLAY_NAMES` + `tierDisplayName(rawTier)` + `isAgencyBillingTier()`. `QuotaStrip.tsx` drops its local copies, imports the shared module. `types/billing.ts` — `PLAN_DEFINITIONS` realigned (`STARTER`→"Solo", `PROFESSIONAL`→"Business"+`popular`, Enterprise features; FREE→/check; price/currency left stale BDT with a note — real prices land with v1.1 checkout). `PlanCard.tsx` (+ Compact) — prefers `tierDisplayName(billingInfo.tier)` for the title+badge. `AlertBanner.tsx` — new `tierName` prop; `BillingOverviewPage.tsx` passes `currentTierName`. `UpgradeModal` labels fixed for free by the `PLAN_DEFINITIONS` rename. |

Pricing restructure: **complete.** Remaining loose ends are v1.1 / polish only — Trader/Agency toggle on the secondary pricing components (`trdr-pricing-section.tsx`; `Pricing.tsx` is dead/unrouted, `ToolPricingSection.tsx` is parked tools), and real prices in `UpgradeModal`/`PLAN_DEFINITIONS` (reworked with self-serve Stripe checkout, v1.1 backlog). Neither is launch-blocking.

Also: `reference_competitor_tradingdocs_ai.md` + `reference_lcopilot_pricing_model.md` saved to memory.

---

## The locked pricing model (so the frontend doesn't re-derive)

**Trader track** (exporter + importer personas): PAYG **$12/LC set** · Solo **$49/mo, 5 LCs, 1 seat** · Business **$149/mo, 25 LCs, 5 seats** · Enterprise **$699/mo, 100 LCs, 10 seats**. Overage rates (display only — quota gate still hard-blocks; metered billing is v1.1): $10 / $7 / $5 per LC. Yearly ≈ 16% off (Solo $41, Business $125, Enterprise $587 per month).

**Agency/Services track** (agent + services personas): per operator seat — Agency Starter **$199/seat/mo** · Agency Pro **$299/seat/mo** · Agency Enterprise **custom**. "Unlimited" LCs per seat within a ~50 LCs/seat/mo fair-use soft cap (advisory, not enforced). Yearly: $167 / $251 per seat/mo.

**"Free"** = a public logged-out LC checker at `/check` (1 anonymous run / IP / 24h, trimmed results, sign-up gate). No in-app monthly free quota. `/api/check` endpoint + `/check` page = deferred follow-up.

**Localization** multipliers off USD: BDT ×86, INR ×69, PKR ×172, EUR ×0.93, GBP ×0.80, AED ×3.67, SGD ×1.35, AUD ×1.55. Keep the 9-currency table.

**Best-judgement calls made on the spec §6 open items:** (1) `sme`→`business` migration with a row-count log so real accounts can be grandfathered manually; (2) no Solo hard-block opt-out — always allow + (eventually) charge overage; (3) keep the existing FX multipliers; (4) `/check` at top level.

---

## Pricing restructure — DONE (see spec §8 for the full per-commit detail)

All of: `lib/pricing.ts` single source of truth (`64277e47`), `Index.tsx` cards + FAQ scrub (`64277e47`), `PricingPage.tsx` Trader/Agency toggle (`120ed3c9`), `QuotaStrip.tsx` 7-value tiers (`120ed3c9`), `types/billing.ts` / `BillingOverviewPage.tsx` 7-value handling (`120ed3c9` + `c56b4e01`), TRDR landing block (`0cda613d`), public `/api/check` + `/check` page (`a0efcb81`), billing-UI tier labels via shared `tierDisplay.ts` (`c56b4e01`). **v1.1 / polish leftovers** (not launch-blocking): Trader/Agency toggle on `trdr-pricing-section.tsx`; real prices in `UpgradeModal` / `PLAN_DEFINITIONS` (with self-serve Stripe checkout).

## Ops note
Migration `20260510_pricing_restructure_tier` is **applied** (Render trdrhub-api, 2026-05-10 13:52 UTC; `/health/db-schema` ok; 141 `sme`→`business` rows — grandfather any real paying SME customers via `quota_limit=50`). For future backend deploys with a new migration: trdrhub-api has no pre/post-deploy hook (`reference_render_migrations.md`), so run `render jobs create srv-d41dio8dl3ps73db8gpg --start-command "alembic upgrade head"` manually, then verify `/health/db-schema`.

---

## Other launch-prep items still open (unchanged from 2026-05-02)
- RulHub `/v1/validate/set` returning HTTP 500 universally → handed to rulhub Claude (separate workspace `J:\Enso Intelligence\ICC Rule Engine\`), 4 ref_ids + sanitized payload preview provided. trdrhub falls back to local DB tiered, so no customer-facing breakage, but the deterministic UCP600 layer isn't firing.
- UAT customer outreach · bug-bash week (2026-07-20→23) · Pingdom + Sentry wiring · roll-back plan review.
