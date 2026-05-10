/**
 * LCopilot Pricing — single source of truth.
 *
 * Restructured 2026-05-10 (spec:
 * docs/superpowers/specs/2026-05-10-lcopilot-pricing-restructure-design.md).
 *
 * Two persona tracks. The persona (Company.business_activities) decides which
 * pricing page a user sees; the billing tier decides what they get.
 *
 *   Trader track (exporter / importer):
 *     Pay-as-you-go — $12 per LC presentation, no commitment (see PAY_PER_USE)
 *     Solo       — $49/mo,  5 LC presentations/mo, 1 seat
 *     Business   — $149/mo, 25/mo, 5 seats, API
 *     Enterprise — $699/mo, 100/mo, 10 seats, integrations + SLA
 *
 *   Agency / Services track (agent / services personas) — priced PER SEAT,
 *   "unlimited" LCs/seat within a fair-use soft cap:
 *     Agency Starter    — $199/seat/mo
 *     Agency Pro        — $299/seat/mo
 *     Agency Enterprise — custom (per-seat with volume discounts)
 *
 * Localized figures are derived from the USD figure via fixed multipliers:
 *   BDT ×86 · INR ×69 · PKR ×172 · EUR ×0.93 · GBP ×0.80 · AED ×3.67 ·
 *   SGD ×1.35 · AUD ×1.55, then rounded to clean values. Yearly billing is
 *   ~16% off the monthly figure (the `yearly` map is per-month-when-billed-
 *   yearly).
 *
 * Backend enforcement of these tiers lives in
 * apps/api/app/services/entitlements.py (TIER_QUOTA_LIMITS etc.) — keep the
 * numbers here in lockstep with that.
 */

// Supported currencies with their symbols
export const CURRENCIES = {
  USD: { symbol: '$', position: 'before', name: 'US Dollar' },
  BDT: { symbol: '৳', position: 'before', name: 'Bangladeshi Taka' },
  INR: { symbol: '₹', position: 'before', name: 'Indian Rupee' },
  PKR: { symbol: 'Rs', position: 'before', name: 'Pakistani Rupee' },
  EUR: { symbol: '€', position: 'before', name: 'Euro' },
  GBP: { symbol: '£', position: 'before', name: 'British Pound' },
  AED: { symbol: 'د.إ', position: 'after', name: 'UAE Dirham' },
  SGD: { symbol: 'S$', position: 'before', name: 'Singapore Dollar' },
  AUD: { symbol: 'A$', position: 'before', name: 'Australian Dollar' },
} as const;

export type CurrencyCode = keyof typeof CURRENCIES;

export type PricingTrack = 'trader' | 'agency';

// Pricing tiers with local pricing
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
  /** Price is "Contact us" (Agency Enterprise) — prices map is zeroed. */
  custom?: boolean;
  /** Per-LC overage rate (USD) shown once the included pool is used.
   *  Display-only for now — the quota gate hard-blocks at the included
   *  amount until self-serve metered billing lands (v1.1). */
  overageRateUsd?: number;
  /** Tier this one upgrades to (for "or upgrade to X" CTAs). */
  upgradeToId?: string;
  prices: {
    monthly: Record<CurrencyCode, number>;
    yearly: Record<CurrencyCode, number>; // Per month when billed yearly
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
    prices: {
      monthly: { USD: 49, BDT: 4200, INR: 3400, PKR: 8400, EUR: 45, GBP: 39, AED: 180, SGD: 66, AUD: 76 },
      yearly:  { USD: 41, BDT: 3500, INR: 2850, PKR: 7050, EUR: 38, GBP: 33, AED: 151, SGD: 55, AUD: 64 },
    },
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
    prices: {
      monthly: { USD: 149, BDT: 12800, INR: 10300, PKR: 25600, EUR: 139, GBP: 119, AED: 547, SGD: 201, AUD: 231 },
      yearly:  { USD: 125, BDT: 10750, INR: 8600,  PKR: 21500, EUR: 116, GBP: 100, AED: 459, SGD: 169, AUD: 194 },
    },
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
    prices: {
      monthly: { USD: 699, BDT: 60100, INR: 48200, PKR: 120200, EUR: 650, GBP: 559, AED: 2565, SGD: 944, AUD: 1083 },
      yearly:  { USD: 587, BDT: 50500, INR: 40500, PKR: 101000, EUR: 546, GBP: 470, AED: 2154, SGD: 792, AUD: 910  },
    },
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
    prices: {
      monthly: { USD: 199, BDT: 17100, INR: 13700, PKR: 34200, EUR: 185, GBP: 159, AED: 730, SGD: 269, AUD: 308 },
      yearly:  { USD: 167, BDT: 14400, INR: 11500, PKR: 28700, EUR: 155, GBP: 134, AED: 613, SGD: 225, AUD: 259 },
    },
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
    prices: {
      monthly: { USD: 299, BDT: 25700, INR: 20600, PKR: 51400, EUR: 278, GBP: 239, AED: 1097, SGD: 404, AUD: 463 },
      yearly:  { USD: 251, BDT: 21600, INR: 17300, PKR: 43200, EUR: 233, GBP: 201, AED: 921,  SGD: 339, AUD: 389 },
    },
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
    prices: {
      monthly: { USD: 0, BDT: 0, INR: 0, PKR: 0, EUR: 0, GBP: 0, AED: 0, SGD: 0, AUD: 0 },
      yearly:  { USD: 0, BDT: 0, INR: 0, PKR: 0, EUR: 0, GBP: 0, AED: 0, SGD: 0, AUD: 0 },
    },
    limits: { lc_validations: 'unlimited', price_checks: 'unlimited', team_members: 'unlimited' },
  },
];

/** All tiers across both tracks. */
export const ALL_PRICING_TIERS: PriceTier[] = [...PRICING_TIERS, ...AGENCY_TIERS];

// ---------------------------------------------------------------------------
// Pay-as-you-go / overage rates (per unit, premium to nudge subscription)
// ---------------------------------------------------------------------------

export const PAY_PER_USE = {
  // $12 per LC presentation (the whole doc set). Trader-track on-ramp + the
  // overage rate when a subscription pool runs out.
  lc_validation: {
    USD: 12, BDT: 1030, INR: 830, PKR: 2060, EUR: 11, GBP: 10, AED: 44, SGD: 16, AUD: 19,
  },
  // The tools below are parked (Price Verify, HS Code Finder, Sanctions
  // Screener launch over the next 6 months) — kept so existing consumers
  // don't break; not advertised.
  price_check: {
    USD: 1, BDT: 86, INR: 69, PKR: 172, EUR: 0.93, GBP: 0.80, AED: 3.67, SGD: 1.35, AUD: 1.55,
  },
  hs_lookup: {
    USD: 0.50, BDT: 43, INR: 35, PKR: 86, EUR: 0.46, GBP: 0.40, AED: 1.84, SGD: 0.68, AUD: 0.78,
  },
  sanctions_screen: {
    USD: 2, BDT: 172, INR: 138, PKR: 344, EUR: 1.86, GBP: 1.60, AED: 7.34, SGD: 2.70, AUD: 3.10,
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function formatPrice(
  amount: number,
  currency: CurrencyCode = 'USD',
  options?: { showCurrency?: boolean }
): string {
  const currencyInfo = CURRENCIES[currency] || CURRENCIES.USD;
  const formattedAmount = amount.toLocaleString();

  if (currencyInfo.position === 'after') {
    return options?.showCurrency
      ? `${formattedAmount} ${currencyInfo.symbol}`
      : `${formattedAmount}${currencyInfo.symbol}`;
  }

  return `${currencyInfo.symbol}${formattedAmount}`;
}

export function getPrice(
  tier: PriceTier,
  currency: CurrencyCode = 'USD',
  billing: 'monthly' | 'yearly' = 'monthly'
): number {
  return tier.prices[billing][currency] ?? tier.prices[billing].USD;
}

export function getPriceDisplay(
  tier: PriceTier,
  currency: CurrencyCode = 'USD',
  billing: 'monthly' | 'yearly' = 'monthly'
): string {
  if (tier.custom) return 'Custom';
  const price = getPrice(tier, currency, billing);
  return formatPrice(price, currency);
}

export function getPayPerUsePrice(
  type: 'lc_validation' | 'price_check' | 'hs_lookup' | 'sanctions_screen',
  currency: CurrencyCode = 'USD'
): number {
  return PAY_PER_USE[type][currency] ?? PAY_PER_USE[type].USD;
}

export function getPayPerUseDisplay(
  type: 'lc_validation' | 'price_check' | 'hs_lookup' | 'sanctions_screen',
  currency: CurrencyCode = 'USD'
): string {
  return formatPrice(getPayPerUsePrice(type, currency), currency);
}

// Get currency from country code
export function getCurrencyFromCountry(countryCode: string): CurrencyCode {
  const countryToCurrency: Record<string, CurrencyCode> = {
    BD: 'BDT',
    IN: 'INR',
    PK: 'PKR',
    US: 'USD',
    GB: 'GBP',
    DE: 'EUR',
    FR: 'EUR',
    IT: 'EUR',
    ES: 'EUR',
    NL: 'EUR',
    AE: 'AED',
    SA: 'AED', // Use AED for Saudi too
    SG: 'SGD',
    AU: 'AUD',
    NZ: 'AUD', // Use AUD for NZ
  };

  return countryToCurrency[countryCode] || 'USD';
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
