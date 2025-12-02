/**
 * Localized Pricing Configuration
 * 
 * Fixed local pricing for supported countries.
 * Rest of world defaults to USD.
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

// Pricing tiers with local pricing
export interface PriceTier {
  id: string;
  name: string;
  description: string;
  features: string[];
  popular?: boolean;
  prices: {
    monthly: Record<CurrencyCode, number>;
    yearly: Record<CurrencyCode, number>; // Per month when billed yearly
  };
  limits: {
    lc_validations: number | 'unlimited';
    price_checks: number | 'unlimited';
    team_members: number | 'unlimited';
  };
}

export const PRICING_TIERS: PriceTier[] = [
  {
    id: 'free',
    name: 'Free',
    description: 'Try TRDR Hub with limited features',
    features: [
      '5 LC validations/month',
      '10 price checks/month',
      '1 team member',
      'Email support',
    ],
    prices: {
      monthly: { USD: 0, BDT: 0, INR: 0, PKR: 0, EUR: 0, GBP: 0, AED: 0, SGD: 0, AUD: 0 },
      yearly: { USD: 0, BDT: 0, INR: 0, PKR: 0, EUR: 0, GBP: 0, AED: 0, SGD: 0, AUD: 0 },
    },
    limits: {
      lc_validations: 5,
      price_checks: 10,
      team_members: 1,
    },
  },
  {
    id: 'starter',
    name: 'Starter',
    description: 'For small trading businesses',
    popular: true,
    features: [
      '50 LC validations/month',
      '100 price checks/month',
      '3 team members',
      'Priority email support',
      'Export reports (PDF/Excel)',
    ],
    prices: {
      monthly: {
        USD: 29,
        BDT: 2500,
        INR: 1999,
        PKR: 4999,
        EUR: 27,
        GBP: 23,
        AED: 109,
        SGD: 39,
        AUD: 45,
      },
      yearly: {
        USD: 24,      // ~17% discount
        BDT: 2100,
        INR: 1699,
        PKR: 4199,
        EUR: 23,
        GBP: 19,
        AED: 92,
        SGD: 33,
        AUD: 38,
      },
    },
    limits: {
      lc_validations: 50,
      price_checks: 100,
      team_members: 3,
    },
  },
  {
    id: 'pro',
    name: 'Pro',
    description: 'For growing trade operations',
    features: [
      '200 LC validations/month',
      '500 price checks/month',
      '10 team members',
      'Phone & email support',
      'API access',
      'Custom branding',
      'Advanced analytics',
    ],
    prices: {
      monthly: {
        USD: 99,
        BDT: 8500,
        INR: 6999,
        PKR: 16999,
        EUR: 92,
        GBP: 79,
        AED: 369,
        SGD: 135,
        AUD: 155,
      },
      yearly: {
        USD: 84,
        BDT: 7200,
        INR: 5999,
        PKR: 14499,
        EUR: 78,
        GBP: 67,
        AED: 314,
        SGD: 115,
        AUD: 132,
      },
    },
    limits: {
      lc_validations: 200,
      price_checks: 500,
      team_members: 10,
    },
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    description: 'For large organizations',
    features: [
      'Unlimited LC validations',
      'Unlimited price checks',
      'Unlimited team members',
      'Dedicated account manager',
      '24/7 priority support',
      'Custom integrations',
      'SLA guarantee',
      'On-premise option',
    ],
    prices: {
      monthly: {
        USD: 499,
        BDT: 42000,
        INR: 35000,
        PKR: 85000,
        EUR: 465,
        GBP: 399,
        AED: 1850,
        SGD: 680,
        AUD: 780,
      },
      yearly: {
        USD: 420,
        BDT: 35000,
        INR: 29000,
        PKR: 71000,
        EUR: 390,
        GBP: 335,
        AED: 1550,
        SGD: 570,
        AUD: 655,
      },
    },
    limits: {
      lc_validations: 'unlimited',
      price_checks: 'unlimited',
      team_members: 'unlimited',
    },
  },
];

// Pay-per-use pricing (for overage or pay-as-you-go)
export const PAY_PER_USE = {
  lc_validation: {
    USD: 2,
    BDT: 170,
    INR: 149,
    PKR: 350,
    EUR: 1.85,
    GBP: 1.60,
    AED: 7.5,
    SGD: 2.70,
    AUD: 3.10,
  },
  price_check: {
    USD: 0.50,
    BDT: 42,
    INR: 35,
    PKR: 85,
    EUR: 0.46,
    GBP: 0.40,
    AED: 1.85,
    SGD: 0.68,
    AUD: 0.78,
  },
};

// Helper functions
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
  const price = getPrice(tier, currency, billing);
  return formatPrice(price, currency);
}

export function getPayPerUsePrice(
  type: 'lc_validation' | 'price_check',
  currency: CurrencyCode = 'USD'
): number {
  return PAY_PER_USE[type][currency] ?? PAY_PER_USE[type].USD;
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

// Get tier by ID
export function getTierById(tierId: string): PriceTier | undefined {
  return PRICING_TIERS.find(t => t.id === tierId);
}

