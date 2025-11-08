/**
 * Currency conversion utility
 * Uses ECB rates or static conversion table for mock/fallback
 */

export type Currency = "USD" | "EUR" | "GBP" | "BDT" | "INR" | "SGD";

// Static conversion rates (to USD) - updated periodically
// In production, fetch from ECB API or similar
const STATIC_RATES: Record<Currency, number> = {
  USD: 1.0,
  EUR: 0.92,
  GBP: 0.79,
  BDT: 0.0091, // 1 BDT = 0.0091 USD (approx)
  INR: 0.012,
  SGD: 0.74,
};

/**
 * Convert amount from source currency to target currency
 * @param amount Amount in source currency (in smallest unit, e.g., cents)
 * @param from Source currency
 * @param to Target currency
 * @returns Amount in target currency (in smallest unit)
 */
export function convertCurrency(amount: number, from: Currency, to: Currency): number {
  if (from === to) return amount;

  // Convert to USD first, then to target
  const usdAmount = amount * STATIC_RATES[from];
  const targetAmount = usdAmount / STATIC_RATES[to];

  return Math.round(targetAmount);
}

/**
 * Get exchange rate from one currency to another
 */
export function getExchangeRate(from: Currency, to: Currency): number {
  if (from === to) return 1.0;
  return STATIC_RATES[from] / STATIC_RATES[to];
}

/**
 * Format amount in currency's smallest unit to display string
 * @param amount Amount in smallest unit (cents/paisa)
 * @param currency Currency code
 * @returns Formatted string (e.g., "$1,999.00" or "৳15,000")
 */
export function formatCurrencyAmount(amount: number, currency: Currency): string {
  const divisor = currency === "BDT" ? 100 : 100; // Both use 100 as smallest unit divisor
  const value = amount / divisor;

  const formatter = new Intl.NumberFormat(getLocale(currency), {
    style: "currency",
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return formatter.format(value);
}

function getLocale(currency: Currency): string {
  const locales: Record<Currency, string> = {
    USD: "en-US",
    EUR: "de-DE",
    GBP: "en-GB",
    BDT: "en-BD",
    INR: "en-IN",
    SGD: "en-SG",
  };
  return locales[currency] || "en-US";
}

/**
 * Get currency symbol
 */
export function getCurrencySymbol(currency: Currency): string {
  const symbols: Record<Currency, string> = {
    USD: "$",
    EUR: "€",
    GBP: "£",
    BDT: "৳",
    INR: "₹",
    SGD: "S$",
  };
  return symbols[currency] || currency;
}

