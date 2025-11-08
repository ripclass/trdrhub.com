/**
 * Tax engine for calculating tax summaries
 * Supports Stripe Tax (if enabled) or manual tax rate mapping
 */
import type { NormalizedInvoice, NormalizedPayment } from "../types";
import type { Currency } from "./fx";

export interface TaxSummary {
  jurisdiction: string; // e.g., "US-CA", "BD-DH", "GB"
  country: string;
  region?: string;
  taxCollected: number; // in cents
  taxRate: number; // percentage (e.g., 0.20 for 20%)
  transactionCount: number;
  currency: Currency;
}

export interface TaxEngineConfig {
  stripeTaxEnabled: boolean;
  manualRates?: Record<string, number>; // jurisdiction -> rate (e.g., "US-CA" -> 0.0875)
  defaultRate?: number;
}

/**
 * Calculate tax summaries from invoices and payments
 */
export function calculateTaxSummaries(
  invoices: NormalizedInvoice[],
  payments: NormalizedPayment[],
  config: TaxEngineConfig
): TaxSummary[] {
  const jurisdictionMap = new Map<string, TaxSummary>();

  // Process invoices (they have tax amounts)
  for (const invoice of invoices) {
    if (invoice.status !== "paid" || !invoice.paidAt) continue;

    // Determine jurisdiction from invoice metadata or customer location
    const jurisdiction = getJurisdictionFromInvoice(invoice, config);
    const existing = jurisdictionMap.get(jurisdiction) || {
      jurisdiction,
      country: jurisdiction.split("-")[0] || "UNKNOWN",
      region: jurisdiction.includes("-") ? jurisdiction.split("-")[1] : undefined,
      taxCollected: 0,
      taxRate: config.manualRates?.[jurisdiction] || config.defaultRate || 0,
      transactionCount: 0,
      currency: invoice.currency as Currency,
    };

    existing.taxCollected += invoice.taxAmount || 0;
    existing.transactionCount += 1;
    jurisdictionMap.set(jurisdiction, existing);
  }

  // Process payments (may have tax info in metadata)
  for (const payment of payments) {
    if (payment.status !== "succeeded") continue;

    const jurisdiction = getJurisdictionFromPayment(payment, config);
    const existing = jurisdictionMap.get(jurisdiction) || {
      jurisdiction,
      country: jurisdiction.split("-")[0] || "UNKNOWN",
      region: jurisdiction.includes("-") ? jurisdiction.split("-")[1] : undefined,
      taxCollected: 0,
      taxRate: config.manualRates?.[jurisdiction] || config.defaultRate || 0,
      transactionCount: 0,
      currency: payment.currency as Currency,
    };

    // If payment has tax info in metadata, use it
    const taxAmount = (payment.metadata?.tax_amount as number) || 0;
    if (taxAmount > 0) {
      existing.taxCollected += taxAmount;
      existing.transactionCount += 1;
      jurisdictionMap.set(jurisdiction, existing);
    }
  }

  return Array.from(jurisdictionMap.values()).sort((a, b) => {
    if (a.country !== b.country) return a.country.localeCompare(b.country);
    return (a.region || "").localeCompare(b.region || "");
  });
}

/**
 * Get jurisdiction from invoice metadata or customer location
 */
function getJurisdictionFromInvoice(invoice: NormalizedInvoice, config: TaxEngineConfig): string {
  // Check metadata for Stripe Tax jurisdiction
  if (config.stripeTaxEnabled && invoice.metadata?.tax_jurisdiction) {
    return String(invoice.metadata.tax_jurisdiction);
  }

  // Check customer location from metadata
  const country = (invoice.metadata?.customer_country as string) || "US";
  const region = invoice.metadata?.customer_region as string | undefined;

  if (region) {
    return `${country}-${region}`;
  }

  return country;
}

/**
 * Get jurisdiction from payment metadata
 */
function getJurisdictionFromPayment(payment: NormalizedPayment, config: TaxEngineConfig): string {
  if (config.stripeTaxEnabled && payment.metadata?.tax_jurisdiction) {
    return String(payment.metadata.tax_jurisdiction);
  }

  const country = (payment.metadata?.customer_country as string) || "US";
  const region = payment.metadata?.customer_region as string | undefined;

  if (region) {
    return `${country}-${region}`;
  }

  return country;
}

/**
 * Default manual tax rates (can be overridden via config)
 */
export const DEFAULT_TAX_RATES: Record<string, number> = {
  "US-CA": 0.0875, // California 8.75%
  "US-NY": 0.08, // New York 8%
  "US-TX": 0.0625, // Texas 6.25%
  "GB": 0.20, // UK VAT 20%
  "BD": 0.15, // Bangladesh VAT 15%
  "IN": 0.18, // India GST 18%
  "SG": 0.09, // Singapore GST 9%
  "US": 0.0, // Default US (varies by state)
  "EU": 0.20, // Default EU VAT
};

/**
 * Create tax engine config from environment
 */
export function createTaxEngineConfig(): TaxEngineConfig {
  const stripeTaxEnabled = import.meta.env.VITE_STRIPE_TAX_ENABLED === "true";
  const manualRates = DEFAULT_TAX_RATES; // Can be overridden from env/config

  return {
    stripeTaxEnabled,
    manualRates,
    defaultRate: 0.0,
  };
}

