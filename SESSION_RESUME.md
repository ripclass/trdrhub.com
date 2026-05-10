# Session resume — UI/UX housekeeping + pricing restructure (2026-05-10)

**Last updated:** 2026-05-10
**State at commit:** `120ed3c9` (pricing restructure frontend, part 3) — branch `master`, pushed
**Active phase:** Path A build = 100% shipped (A1-A13). Launch-prep in flight (~10 weeks to 2026-07-25). This session: brand housekeeping + importer-dashboard bug fixes + a clean-sheet LCopilot pricing restructure (backend ✅ + frontend reconciliation ✅ — only the public `/check` lead-magnet + a couple of secondary-pricing-component polish items remain).

---

## Resume prompt

```
Finish the LCopilot pricing restructure tail. Backend (f16e9ae5) + frontend
reconciliation (64277e47, 120ed3c9) are shipped. Read
docs/superpowers/specs/2026-05-10-lcopilot-pricing-restructure-design.md §8 (locked
numbers + remaining items). Remaining: (1) public POST /api/check endpoint (no auth,
mirror validate_run.py::validate_doc with current_user=None, IP rate-limit 1/IP/24h,
trimmed response) + a public /check page in apps/web; (2) add the Trader/Agency toggle
to trdr-pricing-section.tsx / Pricing.tsx / ToolPricingSection.tsx (they already render
the new trader tiers, just no toggle — mirror PricingPage.tsx); (3) swap PlanType for
the raw tier + a display-name map in the billing UI (BillingOverviewPage etc.) so
"Business" shows as "Business" not "Professional".
Also: run `alembic upgrade head` on Render trdrhub-api after the backend deploy lands
(no auto hook) — check the migration's "sme row count" log line; grandfather any real
sme customers (business=25 LCs/mo vs old sme=50).
```

---

## What shipped today (14 commits, `93c8a394..120ed3c9`)

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

Remaining for the pricing restructure (see spec §8): public `POST /api/check` + `/check` page (the free LC-check lead magnet); Trader/Agency toggle on `trdr-pricing-section.tsx` / `Pricing.tsx` / `ToolPricingSection.tsx` (they render the new trader tiers fine, just no toggle); swap `PlanType` for the raw tier + display-name map in the billing UI so "Business" reads as "Business".

Also: `reference_competitor_tradingdocs_ai.md` + `reference_lcopilot_pricing_model.md` saved to memory.

---

## The locked pricing model (so the frontend doesn't re-derive)

**Trader track** (exporter + importer personas): PAYG **$12/LC set** · Solo **$49/mo, 5 LCs, 1 seat** · Business **$149/mo, 25 LCs, 5 seats** · Enterprise **$699/mo, 100 LCs, 10 seats**. Overage rates (display only — quota gate still hard-blocks; metered billing is v1.1): $10 / $7 / $5 per LC. Yearly ≈ 16% off (Solo $41, Business $125, Enterprise $587 per month).

**Agency/Services track** (agent + services personas): per operator seat — Agency Starter **$199/seat/mo** · Agency Pro **$299/seat/mo** · Agency Enterprise **custom**. "Unlimited" LCs per seat within a ~50 LCs/seat/mo fair-use soft cap (advisory, not enforced). Yearly: $167 / $251 per seat/mo.

**"Free"** = a public logged-out LC checker at `/check` (1 anonymous run / IP / 24h, trimmed results, sign-up gate). No in-app monthly free quota. `/api/check` endpoint + `/check` page = deferred follow-up.

**Localization** multipliers off USD: BDT ×86, INR ×69, PKR ×172, EUR ×0.93, GBP ×0.80, AED ×3.67, SGD ×1.35, AUD ×1.55. Keep the 9-currency table.

**Best-judgement calls made on the spec §6 open items:** (1) `sme`→`business` migration with a row-count log so real accounts can be grandfathered manually; (2) no Solo hard-block opt-out — always allow + (eventually) charge overage; (3) keep the existing FX multipliers; (4) `/check` at top level.

---

## Still pending — pricing restructure frontend (see spec §8 for full detail)

1. `apps/web/src/lib/pricing.ts` — rewrite `PRICING_TIERS` (3 trader tiers) + add `AGENCY_TIERS` + `track`/`seatBased`/`overageRateUsd` fields; `PAY_PER_USE.lc_validation` USD 8 → 12; keep all helper exports (5 files import them).
2. `apps/web/src/pages/Index.tsx` — import trader tiers from `lib/pricing.ts`; fix the 2-vs-5-free-LC FAQ contradiction.
3. `PricingPage.tsx` + `components/sections/trdr-pricing-section.tsx` — Trader ↔ Agency toggle.
4. `components/entitlements/QuotaStrip.tsx` — new tiers + overage line + "Unlimited (fair use)" for agency.
5. `types/billing.ts` + `BillingOverviewPage.tsx` — `normalizePlanType` / tier handling for the 7-value model.
6. **Deferred follow-up:** `POST /api/check` (public, no-auth, IP rate-limited, trimmed result) + `/check` page.

## Ops note
Backend deploy lands on Render via push → **run `alembic upgrade head` manually** afterward (trdrhub-api has no pre/post-deploy hook — `reference_render_migrations.md`). Verify via `/health/db-schema`. Migration `20260510_pricing_restructure_tier` logs the count of `sme` rows it rewrites — check that line; if any are real paying customers, grandfather them (bump to `enterprise` or set `quota_limit=50`) since `business` = 25 LCs/mo vs the old `sme` 50.

---

## Other launch-prep items still open (unchanged from 2026-05-02)
- RulHub `/v1/validate/set` returning HTTP 500 universally → handed to rulhub Claude (separate workspace `J:\Enso Intelligence\ICC Rule Engine\`), 4 ref_ids + sanitized payload preview provided. trdrhub falls back to local DB tiered, so no customer-facing breakage, but the deterministic UCP600 layer isn't firing.
- UAT customer outreach · bug-bash week (2026-07-20→23) · Pingdom + Sentry wiring · roll-back plan review.
