# LCopilot Pricing Restructure — Design

**Date:** 2026-05-10
**Status:** **Mostly shipped.** Backend (`f16e9ae5`) + frontend reconciliation (`64277e47`, `120ed3c9`) done; remaining: public `/check` endpoint + `/check` page, and the Agency toggle on the secondary pricing components — see §8.
**Owner:** Ripon
**Scope:** Clean-sheet redesign of the LCopilot pricing model, shipped pre-launch (target launch 2026-07-25), and full reconciliation of the three currently-contradictory pricing definitions in the codebase.

---

## 1. Problem

There is no single pricing model — there are **three contradictory ones**:

| Where | Tiers | Quotas | Per-LC price |
|---|---|---|---|
| `apps/web/src/pages/Index.tsx` (the `/lcopilot` + `/` landing pricing section) | Free / Pay-as-you-go / Professional / Business | 2 / PAYG / 10 / 40 LCs/mo — *and the FAQ on the same page says "5 validations/month"* | $12/LC PAYG, $79/mo, $199/mo |
| `apps/web/src/lib/pricing.ts` (the `/pricing` page + `trdr-pricing-section.tsx`) | Starter / Growth / Pro / Enterprise | 10 / 30 / 80 / ∞ | $8/LC PAYG, $49 / $99 / $199 / $499/mo |
| `apps/api/app/services/entitlements.py` (what the backend actually enforces) | solo / sme / enterprise | 10 / 50 / ∞ | no prices |

Consequences: a customer who pays for "80 validations (Pro)" on the pricing page is mapped, server-side, to a tier that gives them 50 (or unlimited) — either less than they paid for (liability) or unlimited at a low price (revenue leak). The landing page contradicts itself (2 vs 5 free). No model accounts for the four personas (exporter, importer, agency/sourcing-agent, services/freight-forwarder) whose usage shapes genuinely differ.

**Non-blocking-but-relevant context:** self-serve Stripe checkout is not wired (it is in the v1.1 backlog). At launch, plans are provisioned manually / sales-side regardless. There is therefore **no Stripe product catalog to keep in sync** — the pricing model can be redesigned freely now.

---

## 2. Decisions (locked)

- **Metering unit:** one **LC presentation** (the LC + all its supporting documents, validated together) = 1 unit, everywhere. A 2-doc set and a 30-doc set both count as 1.
- **"Free" mechanism:** a **public, logged-out LC checker** (1 anonymous run per browser/IP, IP rate-limited, results trimmed → sign-up CTA). **No** in-app monthly free quota. The checker is a lead magnet, not a plan.
- **Two persona tracks:** a **Trader track** (exporter + importer personas — validate their *own* LCs) and an **Agency/Services track** (agency/sourcing-agent + services/freight-forwarder personas — validate on behalf of *many* clients).
- **Rollout:** approach A — the full clean-sheet (both tracks + public checker + reconciliation + company migration) ships pre-launch.
- **COGS baseline used for margin math:** ~$3–4 model spend per presentation (extraction vision LLM + AI Examiner Sonnet + RulHub API + Opus veto); more for large sets. Effective revenue per LC must comfortably clear ~$4–5/LC; subscription must beat PAYG by enough to be worth subscribing.

---

## 3. The pricing model

### 3.1 Public LC Checker (free, no account)

- New public page (`/check`, brand-themed, in the marketing shell). Accepts the same multipart upload as `/api/validate` (LC + supporting docs).
- Runs the existing pipeline: extraction → AI Examiner → RulHub → Opus veto.
- Returns a **trimmed** result: verdict + total finding count + the top 2 findings (title + severity only). The full PDF, full finding list, and "run another" are gated behind "Sign up to see everything / export this".
- Rate limit: **1 run per IP per 24 h** (Redis counter via the existing rate-limiter middleware). A 2nd attempt within the window returns HTTP 429 with the sign-up CTA.

### 3.2 Trader track (personas: exporter, importer)

| Tier | Price (USD/mo) | LC sets included | Effective $/LC | Discount vs PAYG | COGS @ full use | Gross margin* | Seats | Overage rate | Headline features |
|---|---|---|---|---|---|---|---|---|---|
| **Pay-as-you-go** | $12 / LC set | — (no pool) | $12 | — | $3–4 | ~67–75% | 1 | n/a (it *is* per-use) | All rules, sanctions screening, full PDF report, no commitment |
| **Solo** | **$49** | **5** | $9.80 | 18% | ~$15–20 | ~64% | 1 | **$10 / LC** | + Excel export, validation history, email support |
| **Business** (most popular) | **$149** | **25** | $5.96 | 50% | ~$87–100 | ~38% | 5 | **$7 / LC** | + API access, custom branding, analytics, priority support |
| **Enterprise** | **$699** (base) | **100** | $6.99 | 42% | ~$350–400 | ~43% | 10 | **$5 / LC** | + integrations, on-prem option, custom rule sets, dedicated account manager, SLA. True-unlimited and volume bands negotiated for sustained usage above ~150 LCs/mo. |

\* gross margin = (revenue − model COGS) ÷ revenue, before fixed costs. All three overage rates ($10 / $7 / $5) sit above per-LC COGS, so exceeding quota stays profitable and nudges the upgrade.

Notes:
- PAYG `quota = 0` means "no included pool" — each validation is a billable $12 event recorded as a `UsageRecord`; the invoice settles via the existing manual/sales flow (consistent with the current no-self-serve-checkout state).
- The $49 → $149 gap (5 → 25 LCs) is intentional: Solo = occasional use, Business = real volume + team + API. The $10/LC Solo overage makes Solo "stretchy" to ~10 LCs/mo before Business wins on price; above that Business's pull is seats + API + branding, not raw LC price.

### 3.3 Agency / Services track (personas: agency/sourcing-agent, services/freight-forwarder)

Billing axis: **per operator seat**, flat $/seat/mo, **unlimited LCs per seat within a fair-use soft cap**. The soft cap is *not hard-enforced* — crossing it logs an internal alert so sales can have a volume conversation. Buy as many seats as you have operators.

| Tier | Price (USD / seat / mo) | LCs per seat | Fair-use soft cap | Roster (suppliers/clients) | Headline features |
|---|---|---|---|---|---|
| **Agency Starter** | **$199** | unlimited | ~50 LCs / seat / mo | up to 25 | Bulk inbox, per-supplier reporting, per-supplier PDF packs |
| **Agency Pro** (most popular) | **$299** | unlimited | ~50 LCs / seat / mo | unlimited | + white-label per-client PDFs, API access, priority support |
| **Agency Enterprise** | **custom** (per-seat with volume discounts) | unlimited | negotiated | unlimited | + dedicated account manager, SLA, integrations |

Margin sanity: at $199/seat a 30-LC/mo operator = $6.63/LC (profitable); at the 50-LC soft cap = $4.00/LC (≈ break-even on COGS). "Unlimited" therefore holds comfortably for any realistic agency operator (typically 10–30 LCs/mo); the soft cap exists only to catch extreme abuse.

### 3.4 Localization

Keep the existing 9-currency localized pricing table, regenerated for the new tiers. Conversion multipliers off the USD figure (same as the current table): **BDT ×86, INR ×69, PKR ×172, EUR ×0.93, GBP ×0.80, AED ×3.67, SGD ×1.35, AUD ×1.55.** Annual billing = ~16% discount on the per-month figure (same as today). Example: Solo $49 → ৳4,200 / ₹3,400 / Rs 8,400 / €45 / £39 / د.إ180 / S$66 / A$76. This is a deliberate edge versus TradingDocs.AI (USD-only, $299 entry) in the BD → IN → VN → PK launch markets.

### 3.5 Persona → track → default-tier mapping

| Onboarding persona (`activities`) | Track | Pricing page shown | Default tier on signup (until they pick a plan) |
|---|---|---|---|
| exporter | Trader | Trader | `payg` (no commitment until they subscribe) |
| importer | Trader | Trader | `payg` |
| agency / sourcing agent | Agency/Services | Agency | `agency_starter` (1 seat) — or a sales-provisioned tier |
| services / freight forwarder | Agency/Services | Agency | `agency_starter` (1 seat) |

The persona only chooses which pricing page a user sees and their default tier; `company.tier` remains the single source of truth for entitlement enforcement.

---

## 4. Implementation

### 4.1 Backend (`apps/api`)

**`company.tier` → 7-value enum** (existing column, new allowed values; widen the enum definition wherever it's declared — model + any migration):
`payg` · `solo` · `business` · `enterprise` · `agency_starter` · `agency_pro` · `agency_enterprise`

**`apps/api/app/services/entitlements.py`** — replace the 3-entry maps:
```python
TIER_QUOTA_LIMITS = {
    "payg": 0,            # no included pool — each validation is a $12 billable event
    "solo": 5,
    "business": 25,
    "enterprise": 100,
    "agency_starter": None,    # None = unlimited (fair-use), via the existing resolve_quota_limit path
    "agency_pro": None,
    "agency_enterprise": None,
}
TIER_SEAT_LIMITS = {
    "payg": 1, "solo": 1, "business": 5, "enterprise": 10,
    "agency_starter": None, "agency_pro": None, "agency_enterprise": None,
}
TIER_OVERAGE_RATE_USD = {        # PAYG has no overage — it is per-use at $12
    "solo": 10, "business": 7, "enterprise": 5,
}
AGENCY_FAIR_USE_SOFT_CAP = {     # advisory only — crossing it logs an alert, does not block
    "agency_starter": 50, "agency_pro": 50,
}
```
- `resolve_quota_limit` / `resolve_seat_limit` keep their `Company.quota_limit` admin-override precedence, then look up the new maps, then default to `business` (the most common paying tier) when the tier string is unrecognised — replaces the current `"sme"` default.
- Quota enforcement: when a Trader-track company hits its included pool, allow the validation but record the overage charge (`UsageRecord` at `TIER_OVERAGE_RATE_USD[tier]`) and surface "you're over — extra LCs at $X, or upgrade" in the response. (Whether Solo also gets a hard block option is left to the implementation plan; default = allow + charge.)
- Agency soft cap: on each validation, if the operator-seat's month-to-date count exceeds `AGENCY_FAIR_USE_SOFT_CAP[tier]`, emit an internal alert/log (no user-facing block).
- PAYG: each validation records a `UsageRecord` at $12.00; settlement is manual via the existing billing flow.

**New endpoint `POST /api/check`** (public, no auth):
- Accepts the same multipart payload as `POST /api/validate` (LC + supporting documents).
- Runs the existing pipeline (`prepare_validation_session` → extraction → AI Examiner → RulHub → Opus veto) but returns a **trimmed** payload: `{ verdict, finding_count, top_findings: [{title, severity} × ≤2], signup_cta: true }`. Withholds the full structured result, the customs-pack PDF, and the full finding list.
- Rate limit: 1 request / IP / 24 h (Redis counter, existing rate-limiter middleware). 2nd request within the window → HTTP 429 with the sign-up CTA in the body.
- Does **not** create a persistent `ValidationSession` tied to a user; if a session row is needed for the pipeline, it is created with a sentinel anonymous owner and is eligible for cleanup.

### 4.2 Frontend (`apps/web`)

**Single source of truth.** `apps/web/src/lib/pricing.ts` becomes canonical and is rewritten to express both tracks (7 tiers + PAYG, each with `prices.monthly` / `prices.yearly` per the 9-currency multipliers, `limits`, `features`, `track: 'trader' | 'agency'`, `popular` flags). Then:
- `apps/web/src/pages/Index.tsx` — delete its hardcoded `pricing` array; import the Trader-track tiers from `lib/pricing.ts`. Fix the "2 vs 5 free validations" FAQ contradiction (no monthly free tier exists — replace with "free public LC check, then plans from $49/mo").
- `apps/web/src/pages/PricingPage.tsx` and `apps/web/src/components/sections/trdr-pricing-section.tsx` — render with a **Trader ↔ Agency toggle** at the top (default Trader). Each track view shows its tiers + the PAYG card + the "free LC check" callout linking to `/check`.
- `apps/web/src/components/entitlements/QuotaStrip.tsx` — read the new `company.tier`; show included / used / remaining plus the overage line ("5 of 5 LCs used — extra LCs at $10 each, or upgrade to Business"). Agency-track companies show "Unlimited (fair use)" instead of a numeric quota.
- `normalizePlanType` and the `tier` field in `apps/web/src/types/billing.ts` + `BillingOverviewPage.tsx` (added 2026-05-10 in commit `d69fa73a`) — fold into the new 7-value model: the legacy `solo → STARTER` / `sme → PROFESSIONAL` mapping is replaced; legacy `sme` resolves to `business`.
- **New page `/check`** — public, brand-themed, in the marketing shell: upload → trimmed results → "Sign up to export this PDF and run more". This is the lead-magnet surface; it is *not* auth-gated.

### 4.3 Migration of existing companies

| Current `company.tier` | New `company.tier` | Note |
|---|---|---|
| `solo` | `solo` | unchanged (5 LCs) |
| `sme` | `business` | **quota cut: 50 → 25.** If any real customer is on `sme`, grandfather them (honour 50 until they actively re-pick a plan) or bump to `enterprise`. Likely a non-issue pre-launch (few/no real paying customers). Flag for Ripon to confirm before running. |
| `enterprise` | `enterprise` | unchanged in name; quota goes from "unlimited" to "100 + $5/LC overage / negotiated above ~150". Same grandfather caveat. |
| (none / null / unknown) | `payg` | new signups default to PAYG until they subscribe |

Run as a one-off data migration (or a backfill script) alongside the `entitlements.py` deploy. No Stripe-catalog sync is required.

### 4.4 Rollout sequence

1. Backend: widen the `company.tier` enum; ship the `entitlements.py` rewrite; ship `POST /api/check`; run the company-tier migration.
2. Frontend: rewrite `lib/pricing.ts`; repoint `Index.tsx`; rebuild `PricingPage` / `trdr-pricing-section` with the Trader/Agency toggle; ship `/check`; update `QuotaStrip`; update `normalizePlanType` / `tier` handling.
3. Verify (see §5). No Stripe work — self-serve checkout remains v1.1; plans provisioned manually at launch.

---

## 5. Testing

- **Unit (`entitlements.py`):** each of the 7 tiers returns the correct quota / seat limit / overage rate; `payg` records a $12 `UsageRecord` per validation; a `business` company at LC #26 is allowed but charged $7 and gets the over-quota message; an `agency_starter` company validating past 25 is not blocked and an alert is logged once it crosses the 50/seat soft cap; unrecognised tier strings default to `business`; legacy `sme` resolves to `business`.
- **Unit (frontend):** `normalizePlanType` / tier→display mapping for all 7 tiers + the legacy `sme` fallback; `lib/pricing.ts` produces consistent per-currency figures from the multipliers.
- **Integration:** `POST /api/check` returns a trimmed result for a valid logged-out upload; a 2nd call from the same IP within 24 h returns 429 with the sign-up CTA; the trimmed payload never includes the full finding list or PDF.
- **Browser (Playwright — the main upload → results path works per existing memory):** pricing page Trader/Agency toggle switches the displayed tiers; `QuotaStrip` shows the right quota + overage line for a Solo, a Business, and an Agency company; `/check` runs end-to-end logged-out and shows the sign-up gate.

---

## 6. Open items for Ripon to confirm before implementation

1. **`sme` migration:** grandfather existing `sme` customers at 50 LCs, or bump to `enterprise`, or accept the cut to `business`/25? (Default in this spec: cut to `business`, flag any affected accounts.)
2. **Solo hard-block option:** should Solo customers be able to opt out of overage and instead hard-block at 5/mo? (Default: no — always allow + charge $10/LC.)
3. **Final price points:** the USD figures above ($12 / $49 / $149 / $699 / $199 / $299) are confirmed; the per-currency localized figures are derived from the stated multipliers — confirm the multipliers are still current or supply updated FX.
4. **`/check` placement:** path `/check` vs `/lcopilot/check` vs a section on the existing `/lcopilot` landing.

---

## 7. Out of scope (explicitly not in this work)

- Self-serve Stripe checkout / subscription management UI (v1.1 backlog — unchanged).
- The other TRDR Hub tools' pricing (LC Builder, Doc Generator, Sanctions Screener, HS Code Finder, etc.) — they are parked; this spec is LCopilot-only. When they launch over the next 6 months they get their own pricing pass.
- Bank-portal pricing (parked).
- Any change to the validation pipeline itself — `/api/check` reuses it as-is.

---

## 8. Implementation status (2026-05-10)

### ✅ Shipped — backend (commit `f16e9ae5`, pushed)

- `app/models/company.py` — `BusinessTier` is now the 7-value billing-tier enum (`payg`/`solo`/`business`/`enterprise`/`agency_starter`/`agency_pro`/`agency_enterprise`); new `BusinessSize` enum (`solo`/`sme`/`enterprise`) for the onboarding Q3 answer; `starting_billing_tier(company_size, *, is_agency)` maps size+persona → starting billing tier; `companies.tier` column default changed `sme` → `payg`.
- `app/schemas/onboarding.py` — `OnboardingCompletePayload.tier` validated against `BUSINESS_SIZE_VALUES` (it's a size answer, not a billing tier).
- `app/services/onboarding_service.py` — `complete_onboarding` writes `company.tier = starting_billing_tier(payload.tier, is_agency=primary_activity in {agent, services})`; raw size still preserved in `event_metadata["company_size"]` / `onboarding_data["tier"]`.
- `app/services/entitlements.py` — `TIER_QUOTA_LIMITS` (payg 0 / solo 5 / business 25 / enterprise 100 / agency_* None), `TIER_SEAT_LIMITS` (1 / 1 / 5 / 10 / None), `TIER_OVERAGE_RATE_USD` (solo $10 / business $7 / enterprise $5 — **display-only**, the quota gate still hard-blocks at the included amount; metered billing is v1.1), `AGENCY_FAIR_USE_SOFT_CAP` (agency_starter/pro 50 LCs/seat/mo — advisory log via `_maybe_soft_cap_alert`, never blocks); unrecognised tier → `business` default; `resolve_overage_rate()` helper.
- `app/routers/entitlements.py` — `GET /api/entitlements/current` now also returns `overage_rate_usd`.
- `app/services/billing_service.py` — `_resolve_tier` recognises the 7 new tiers, maps legacy plan/size strings (incl. legacy `sme` → `business`), defaults to `business`.
- `alembic/versions/20260510_pricing_restructure_tier.py` — rewrites `companies.tier` `'sme'` → `'business'`, changes column default `'sme'` → `'payg'`, logs the `'sme'` row count first. **Must be run on Render after deploy** (trdrhub-api has no auto-migrate hook — `reference_render_migrations`).

### ✅ Shipped — frontend reconciliation (commits `64277e47`, `120ed3c9`, pushed)

- `apps/web/src/lib/pricing.ts` — rewritten as the single source of truth: `PRICING_TIERS` = the 3 trader tiers (solo/business/enterprise) with 9-currency localized monthly+yearly maps, `overageRateUsd`, `upgradeToId`; `AGENCY_TIERS` = the 3 agency per-seat tiers; `PriceTier` gained `track`/`seatBased`/`custom`/`overageRateUsd`/`upgradeToId`; `PAY_PER_USE.lc_validation` USD 8→12 + localized; all existing helper exports preserved; new `getPayPerUseDisplay` / `tiersForTrack` / `ALL_PRICING_TIERS` / `PricingTrack`.
- `apps/web/src/pages/Index.tsx` — landing-page pricing cards derived from `PRICING_TIERS` + `PAY_PER_USE` (no longer a hardcoded array); removed the "Free $0/forever" card; scrubbed the "2 free LCs" / "5 free validations" / "Free tier gives you 5 validations/month" copy → "$12 per LC · no commitment · no card to start".
- `apps/web/src/pages/PricingPage.tsx` — Trader ↔ Agency persona toggle; trader = PAYG callout + Solo + Business⭐ cards + Enterprise wide card; agency = Agency Starter + Agency Pro⭐ (per-seat) + Agency Enterprise (Custom) wide card; shared `<PricingCard>` component; FAQ + header copy rewritten (no "14-day free trial").
- `apps/web/src/components/entitlements/QuotaStrip.tsx` — 7-value tier display names; three states (trader pool → bar + overage line + upgrade hint; PAYG → "$12 per LC" line + "See plans"; agency → "Unlimited (fair use)" pill); bar recolored brand lime.
- `apps/web/src/lib/lcopilot/entitlementsApi.ts` — `CurrentEntitlements.overage_rate_usd`.
- `apps/web/src/types/billing.ts` — `normalizePlanType` folds the 7 new tier strings into the `PlanType` enum (payg/solo→STARTER, business/agency_*→PROFESSIONAL, enterprise/agency_enterprise→ENTERPRISE) + keeps legacy mappings; in-comment note that the billing UI should eventually swap `PlanType` for the raw tier + a display-name map (the labels currently read Starter/Professional/Enterprise).

### 🔲 Pending — public `/api/check` + `/check` page · Agency toggle on secondary pricing components

- `trdr-pricing-section.tsx` / `Pricing.tsx` / `ToolPricingSection.tsx` import the same `lib/pricing.ts` helpers/tiers, so they compile and render the new trader tiers with the new prices — they just lack the Trader/Agency toggle. Polish for the follow-up (mirror `PricingPage.tsx`).
- The billing UI (`BillingOverviewPage` + `PlanCard`/`AlertBanner`/`UpgradeModal`) still labels tiers Starter/Professional/Enterprise via `normalizePlanType` — swap to the raw `company.tier` + a display-name map (see `QuotaStrip.TIER_DISPLAY_NAMES`).
- Public `/api/check` endpoint + `/check` page — see the next subsection.

**Locked numbers (do not re-derive):**

| Trader tier | USD/mo | yearly/mo (~16% off) | LCs incl. | seats | overage |
|---|---|---|---|---|---|
| Pay-as-you-go | $12 / LC set | — | — | 1 | n/a |
| Solo | $49 | $41 | 5 | 1 | $10/LC (display only) |
| Business ⭐ | $149 | $125 | 25 | 5 | $7/LC (display only) |
| Enterprise | $699 | $587 | 100 | 10 | $5/LC (display only) |

| Agency/Services tier | USD / seat / mo | yearly/seat/mo | LCs / seat | soft cap |
|---|---|---|---|---|
| Agency Starter | $199 | $167 | unlimited | 50/seat/mo |
| Agency Pro ⭐ | $299 | $251 | unlimited | 50/seat/mo |
| Agency Enterprise | custom | custom | unlimited | negotiated |

Localization multipliers off USD (same as the current `lib/pricing.ts` table): **BDT ×86, INR ×69, PKR ×172, EUR ×0.93, GBP ×0.80, AED ×3.67, SGD ×1.35, AUD ×1.55**; round to clean figures.

### 🔲 Pending — public `/api/check` endpoint + `/check` page (deferred to a focused follow-up)

Deferred because it's the most plumbing-heavy piece, it's a lead magnet (not the launch-blocker), and a half-wired public endpoint without solid rate-limiting is itself a free-LLM-spend cost risk. Scope unchanged from §3.1 / §4.1 / §4.2. The validation pipeline already uses `get_user_optional` (lenient auth), so `/api/check` can mirror `POST /api/validate/` (in `validate_run.py::validate_doc`) with: forced full run (no intake_only/extract_only), `current_user=None`, IP rate-limit (1/IP/24h, existing rate-limiter middleware), and a trimmed response (`{verdict, finding_count, top_findings:[≤2 × {title, severity}], signup_cta:true}` — withhold the full structured result + PDF + full finding list). New `/check` page in `apps/web` (public, brand-themed, marketing shell, not auth-gated).
