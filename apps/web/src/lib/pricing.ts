/**
 * LCopilot Pricing — single source of truth (USD-only as of 2026-05-11).
 *
 * Phase 1 of "lock to USD". The previous version carried a hardcoded
 * 9-currency price table derived from a fixed FX multiplier (BDT ×86,
 * INR ×69, PKR ×172, …). Those multipliers were three years stale —
 * USD/BDT had drifted from 86 → ~117, USD/INR from 69 → ~85, USD/PKR
 * from 172 → ~280 — so BD/IN/PK customers were being shown prices ~20–40%
 * under USD-equivalent. Rather than maintain a multiplier table (or build a
 * live-FX layer just for marketing), we stopped pretending we know the FX
 * rate at all and rely on Stripe Adaptive Pricing at checkout: the customer
 * sees their local currency at the moment of payment, Stripe handles the
 * FX (~1% conversion fee), we settle in USD.
 *
 * Net effect: one canonical price per tier, zero drift risk, ~400 lines of
 * stale price tables gone.
 *
 * Trader track: PAYG $12/LC · Solo $49/mo (5 LCs, 1 seat) · Business
 * $149/mo (25 LCs, 5 seats, popular) · Enterprise $699/mo (100 LCs, 10
 * seats; volume bands above 150).
 *
 * Agency / Services track (per operator seat, "unlimited" within ~50 LCs/
 * seat/mo fair-use): Agency Starter $199/seat · Agency Pro $299/seat ·
 * Agency Enterprise custom.
 *
 * `yearly` is the per-month figure when billed annually (~16% off monthly).
 *
 * Backend enforcement in `apps/api/app/services/entitlements.py` is
 * already USD-only — no backend change needed for this lock.
 *
 * NOTE: `CURRENCIES`, `CurrencyCode`, `getCurrencyFromCountry`,
 * `formatPrice(_, currency)` etc. are stub-retained so older / parked
 * surfaces (HubBilling, PriceVerifyLanding, Pricing.tsx) keep compiling.
 * Every callable now returns USD regardless of what is passed in.
 */

// Stub-retained for backwards compat. Every surface now renders USD.
export const CURRENCIES = {
  USD: { symbol: '$', position: 'before', name: 'US Dollar' },
} as const;

export type CurrencyCode = keyof typeof CURRENCIES;

export type PricingTrack = 'trader' | 'agency';

export interface PriceTier {
  id: string;
  name: string;
  description: string;
  /** Which persona track this tier belongs to. */
  track: PricingTrack;
  features: string[];
  popular?: boolean;
  /** Agency tiers are priced per operator seat — display "$X / seat / mo". */
  seatBased?: boolean;
  /** Price is "Contact us" (Agency Enterprise) — `prices` is zeroed. */
  custom?: boolean;
  /** Per-LC overage rate (USD) shown once the included pool is used.
   *  Display-only for now — the quota gate hard-blocks at the included
   *  amount until self-serve metered billing lands (v1.1). */
  overageRateUsd?: number;
  /** Tier this one upgrades to (for "or upgrade to X" CTAs). */
  upgradeToId?: string;
  prices: {
    /** Monthly price in USD. */
    monthly: number;
    /** Per-month figure when billed yearly (USD). */
    yearly: number;
  };
  limits: {
    /** LC presentations per month. 'unlimited' for agency tiers (fair use). */
    lc_validations: number | 'unlimited';
    /** Vestigial — the Price Verify tool is parked. Kept so existing
     *  consumers that render it don't break; not advertised. */
    price_checks: number | 'unlimited';
    /** Max seats (members + invites). 'unlimited' for agency (buy as needed). */
    team_members: number | 'unlimited';
  };
}

// ---------------------------------------------------------------------------
// Trader track — subscription tiers (PAYG lives in PAY_PER_USE below)
// ---------------------------------------------------------------------------

export const PRICING_TIERS: PriceTier[] = [
  {
    id: 'solo',
    name: 'Solo',
    description: 'For occasional exporters and importers',
    track: 'trader',
    overageRateUsd: 10,
    upgradeToId: 'business',
    features: [
      '5 LC validations/month',
      'Full UCP600 / ISBP rule coverage',
      'Sanctions screening included',
      'PDF & Excel reports',
      'Validation history',
      '1 user',
      'Email support',
      'Extra LCs at $10 each',
    ],
    prices: { monthly: 49, yearly: 41 },
    limits: { lc_validations: 5, price_checks: 15, team_members: 1 },
  },
  {
    id: 'business',
    name: 'Business',
    description: 'For regular exporters and trade teams',
    track: 'trader',
    popular: true,
    overageRateUsd: 7,
    upgradeToId: 'enterprise',
    features: [
      '25 LC validations/month',
      'Everything in Solo',
      '5 team members',
      'API access',
      'Custom branding on reports',
      'Advanced analytics',
      'Priority support',
      'Extra LCs at $7 each',
    ],
    prices: { monthly: 149, yearly: 125 },
    limits: { lc_validations: 25, price_checks: 80, team_members: 5 },
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    description: 'For trading houses and large organisations',
    track: 'trader',
    overageRateUsd: 5,
    features: [
      '100 LC validations/month',
      'Everything in Business',
      '10 team members',
      'Custom rule sets',
      'ERP / SCM integrations',
      'On-premise option',
      'Dedicated account manager',
      '99.9% SLA',
      'Extra LCs at $5 each · volume bands above 150/mo',
    ],
    prices: { monthly: 699, yearly: 587 },
    limits: { lc_validations: 100, price_checks: 'unlimited', team_members: 10 },
  },
];

// ---------------------------------------------------------------------------
// Agency / Services track — per-operator-seat tiers
// ---------------------------------------------------------------------------

export const AGENCY_TIERS: PriceTier[] = [
  {
    id: 'agency_starter',
    name: 'Agency Starter',
    description: 'For sourcing agents and freight forwarders',
    track: 'agency',
    seatBased: true,
    upgradeToId: 'agency_pro',
    features: [
      'Unlimited LC validations per seat*',
      'Bulk inbox — validate many docs at once',
      'Per-supplier reporting & PDF packs',
      'Up to 25 suppliers / clients in your roster',
      'Buy as many operator seats as you need',
      'Email support',
      '*fair use — ~50 LCs/seat/mo, beyond which we talk volume pricing',
    ],
    prices: { monthly: 199, yearly: 167 },
    limits: { lc_validations: 'unlimited', price_checks: 'unlimited', team_members: 'unlimited' },
  },
  {
    id: 'agency_pro',
    name: 'Agency Pro',
    description: 'For agencies running a large client book',
    track: 'agency',
    seatBased: true,
    popular: true,
    upgradeToId: 'agency_enterprise',
    features: [
      'Unlimited LC validations per seat*',
      'Everything in Agency Starter',
      'Unlimited suppliers / clients',
      'White-label per-client PDFs',
      'API access',
      'Priority support',
      '*fair use — ~50 LCs/seat/mo, beyond which we talk volume pricing',
    ],
    prices: { monthly: 299, yearly: 251 },
    limits: { lc_validations: 'unlimited', price_checks: 'unlimited', team_members: 'unlimited' },
  },
  {
    id: 'agency_enterprise',
    name: 'Agency Enterprise',
    description: 'For large agencies and trade-service networks',
    track: 'agency',
    seatBased: true,
    custom: true,
    features: [
      'Everything in Agency Pro',
      'Per-seat pricing with volume discounts',
      'ERP / TMS integrations',
      'Dedicated account manager',
      'Custom SLA',
      'Negotiated fair-use limits',
    ],
    prices: { monthly: 0, yearly: 0 },
    limits: { lc_validations: 'unlimited', price_checks: 'unlimited', team_members: 'unlimited' },
  },
];

/** All tiers across both tracks. */
export const ALL_PRICING_TIERS: PriceTier[] = [...PRICING_TIERS, ...AGENCY_TIERS];

// ---------------------------------------------------------------------------
// Pay-as-you-go / overage rates (USD per unit, premium to nudge subscription)
// ---------------------------------------------------------------------------

export const PAY_PER_USE = {
  /** $12 per LC presentation (the whole doc set). Trader-track on-ramp +
   *  the overage rate when a subscription pool runs out. */
  lc_validation: 12,
  // The tools below are parked (Price Verify, HS Code Finder, Sanctions
  // Screener launch over the next 6 months) — kept so existing consumers
  // don't break; not advertised.
  price_check: 1,
  hs_lookup: 0.5,
  sanctions_screen: 2,
} as const;

export type PayPerUseUnit = keyof typeof PAY_PER_USE;

// ---------------------------------------------------------------------------
// Helpers — every callable returns USD. The `currency` parameters are kept
// in the signatures only so older / parked call sites keep compiling.
// ---------------------------------------------------------------------------

export function formatPrice(
  amount: number,
  _currency: CurrencyCode = 'USD',
  _options?: { showCurrency?: boolean },
): string {
  return `$${amount.toLocaleString()}`;
}

export function getPrice(
  tier: PriceTier,
  _currency: CurrencyCode = 'USD',
  billing: 'monthly' | 'yearly' = 'monthly',
): number {
  return tier.prices[billing];
}

export function getPriceDisplay(
  tier: PriceTier,
  _currency: CurrencyCode = 'USD',
  billing: 'monthly' | 'yearly' = 'monthly',
): string {
  if (tier.custom) return 'Custom';
  return formatPrice(getPrice(tier, 'USD', billing));
}

export function getPayPerUsePrice(
  type: PayPerUseUnit,
  _currency: CurrencyCode = 'USD',
): number {
  return PAY_PER_USE[type];
}

export function getPayPerUseDisplay(
  type: PayPerUseUnit,
  _currency: CurrencyCode = 'USD',
): string {
  return formatPrice(getPayPerUsePrice(type));
}

/** Stub-retained — every country now resolves to USD. Stripe Adaptive
 *  Pricing handles local-currency presentation at checkout. */
export function getCurrencyFromCountry(_countryCode: string): CurrencyCode {
  return 'USD';
}

// Get tier by ID across both tracks
export function getTierById(tierId: string): PriceTier | undefined {
  return ALL_PRICING_TIERS.find(t => t.id === tierId);
}

/** Tiers for a given persona track (trader = exporter/importer pages,
 *  agency = agent/services pages). */
export function tiersForTrack(track: PricingTrack): PriceTier[] {
  return track === 'agency' ? AGENCY_TIERS : PRICING_TIERS;
}
