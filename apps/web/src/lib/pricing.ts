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
    id: 'starter',
    name: 'Starter',
    description: 'The "Toe in Water" plan for small traders',
    features: [
      '10 LC validations/month',
      '30 price checks/month',
      '50 HS code lookups/month',
      '20 sanctions screens/month',
      '2 team members',
      'Email support',
      'PDF/Excel exports',
    ],
    prices: {
      monthly: {
        USD: 49,
        BDT: 4200,    // ~86x
        INR: 3400,    // ~69x
        PKR: 8400,    // ~172x
        EUR: 45,
        GBP: 39,
        AED: 180,
        SGD: 66,
        AUD: 76,
      },
      yearly: {
        USD: 41,      // ~16% discount
        BDT: 3500,
        INR: 2850,
        PKR: 7050,
        EUR: 38,
        GBP: 33,
        AED: 151,
        SGD: 55,
        AUD: 64,
      },
    },
    limits: {
      lc_validations: 10,
      price_checks: 30,
      team_members: 2,
    },
  },
  {
    id: 'growth',
    name: 'Growth',
    description: 'The "Sweet Spot" for growing businesses',
    popular: true,
    features: [
      '30 LC validations/month',
      '80 price checks/month',
      '150 HS code lookups/month',
      '60 sanctions screens/month',
      '5 team members',
      'Priority support',
      'API access',
      'Advanced analytics',
    ],
    prices: {
      monthly: {
        USD: 99,
        BDT: 8500,
        INR: 6800,
        PKR: 17000,
        EUR: 92,
        GBP: 79,
        AED: 365,
        SGD: 134,
        AUD: 153,
      },
      yearly: {
        USD: 83,      // ~16% discount
        BDT: 7100,
        INR: 5700,
        PKR: 14300,
        EUR: 77,
        GBP: 66,
        AED: 305,
        SGD: 112,
        AUD: 128,
      },
    },
    limits: {
      lc_validations: 30,
      price_checks: 80,
      team_members: 5,
    },
  },
  {
    id: 'pro',
    name: 'Pro',
    description: 'For heavy users and trade teams',
    features: [
      '80 LC validations/month',
      '200 price checks/month',
      '400 HS code lookups/month',
      '150 sanctions screens/month',
      '15 team members',
      'Phone & email support',
      'Full API access',
      'Custom branding',
      'SLA guarantee',
    ],
    prices: {
      monthly: {
        USD: 199,
        BDT: 17100,
        INR: 13700,
        PKR: 34200,
        EUR: 185,
        GBP: 159,
        AED: 731,
        SGD: 269,
        AUD: 308,
      },
      yearly: {
        USD: 167,     // ~16% discount
        BDT: 14400,
        INR: 11500,
        PKR: 28700,
        EUR: 155,
        GBP: 133,
        AED: 614,
        SGD: 226,
        AUD: 259,
      },
    },
    limits: {
      lc_validations: 80,
      price_checks: 200,
      team_members: 15,
    },
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    description: 'For large organizations & banks',
    features: [
      'Unlimited LC validations',
      'Unlimited price checks',
      'Unlimited HS lookups',
      'Unlimited sanctions screens',
      'Unlimited team members',
      'Dedicated account manager',
      '24/7 priority support',
      'Custom integrations',
      'On-premise option',
      '99.9% SLA guarantee',
    ],
    prices: {
      monthly: {
        USD: 499,
        BDT: 42900,
        INR: 34400,
        PKR: 85800,
        EUR: 465,
        GBP: 399,
        AED: 1833,
        SGD: 674,
        AUD: 773,
      },
      yearly: {
        USD: 419,     // ~16% discount
        BDT: 36000,
        INR: 28900,
        PKR: 72100,
        EUR: 390,
        GBP: 335,
        AED: 1539,
        SGD: 566,
        AUD: 649,
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
// PAYG prices are premium to encourage subscription
export const PAY_PER_USE = {
  lc_validation: {
    USD: 8,       // Premium PAYG rate
    BDT: 690,     // ~86x
    INR: 550,     // ~69x
    PKR: 1375,    // ~172x
    EUR: 7.4,
    GBP: 6.4,
    AED: 29,
    SGD: 10.8,
    AUD: 12.4,
  },
  price_check: {
    USD: 1,
    BDT: 86,
    INR: 69,
    PKR: 172,
    EUR: 0.93,
    GBP: 0.80,
    AED: 3.67,
    SGD: 1.35,
    AUD: 1.55,
  },
  hs_lookup: {
    USD: 0.50,
    BDT: 43,
    INR: 35,
    PKR: 86,
    EUR: 0.46,
    GBP: 0.40,
    AED: 1.84,
    SGD: 0.68,
    AUD: 0.78,
  },
  sanctions_screen: {
    USD: 2,
    BDT: 172,
    INR: 138,
    PKR: 344,
    EUR: 1.86,
    GBP: 1.60,
    AED: 7.34,
    SGD: 2.70,
    AUD: 3.10,
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
  type: 'lc_validation' | 'price_check' | 'hs_lookup' | 'sanctions_screen',
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

