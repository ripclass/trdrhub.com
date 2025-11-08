/**
 * Billing aggregator service
 * Merges data from multiple providers, deduplicates, and converts currency
 */
import type {
  NormalizedInvoice,
  NormalizedPayment,
  NormalizedRefund,
  NormalizedPayout,
  NormalizedSubscription,
  BillingProviderQueryParams,
  PaginatedBillingResult,
  BillingProvider,
} from "../types";
import { StripeProvider } from "./providers/stripeProvider";
import { SSLCommerzProvider } from "./providers/sslcommerzProvider";
import { convertCurrency, type Currency } from "./fx";

export interface AggregatorConfig {
  providers: BillingProvider[];
  reportingCurrency: Currency;
  enabledProviders?: string[]; // e.g., ["stripe", "sslcommerz"]
}

export class BillingAggregator {
  private providers: BillingProvider[];
  private reportingCurrency: Currency;
  private enabledProviderNames: Set<string>;

  constructor(config: AggregatorConfig) {
    this.providers = config.providers;
    this.reportingCurrency = config.reportingCurrency;
    this.enabledProviderNames = new Set(config.enabledProviders || config.providers.map((p) => p.name));
  }

  /**
   * Get enabled providers
   */
  private getEnabledProviders(): BillingProvider[] {
    return this.providers.filter((p) => this.enabledProviderNames.has(p.name));
  }

  /**
   * Merge and deduplicate invoices from all providers
   */
  async listInvoices(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedInvoice>> {
    const enabledProviders = this.getEnabledProviders();
    const results = await Promise.all(
      enabledProviders.map((provider) => provider.listInvoices(params))
    );

    // Merge all items
    let allItems: NormalizedInvoice[] = [];
    for (const result of results) {
      allItems = allItems.concat(result.items);
    }

    // Deduplicate by (provider, externalId)
    const seen = new Set<string>();
    const uniqueItems = allItems.filter((item) => {
      const key = `${item.provider}:${item.externalId}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    // Convert currency to reporting currency
    const convertedItems = uniqueItems.map((item) => {
      if (item.currency === this.reportingCurrency) return item;
      return {
        ...item,
        amount: convertCurrency(item.amount, item.currency as Currency, this.reportingCurrency),
        taxAmount: convertCurrency(item.taxAmount, item.currency as Currency, this.reportingCurrency),
        totalAmount: convertCurrency(item.totalAmount, item.currency as Currency, this.reportingCurrency),
        currency: this.reportingCurrency,
        lineItems: item.lineItems.map((li) => ({
          ...li,
          unitPrice: convertCurrency(li.unitPrice, item.currency as Currency, this.reportingCurrency),
          amount: convertCurrency(li.amount, item.currency as Currency, this.reportingCurrency),
          taxAmount: li.taxAmount
            ? convertCurrency(li.taxAmount, item.currency as Currency, this.reportingCurrency)
            : undefined,
        })),
      };
    });

    // Sort by issuedAt descending
    convertedItems.sort((a, b) => new Date(b.issuedAt).getTime() - new Date(a.issuedAt).getTime());

    return {
      items: convertedItems,
      hasMore: false, // Simplified for now
      total: convertedItems.length,
    };
  }

  /**
   * Merge and deduplicate payments from all providers
   */
  async listPayments(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedPayment>> {
    const enabledProviders = this.getEnabledProviders();
    const results = await Promise.all(
      enabledProviders.map((provider) => provider.listPayments(params))
    );

    let allItems: NormalizedPayment[] = [];
    for (const result of results) {
      allItems = allItems.concat(result.items);
    }

    const seen = new Set<string>();
    const uniqueItems = allItems.filter((item) => {
      const key = `${item.provider}:${item.externalId}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    const convertedItems = uniqueItems.map((item) => {
      if (item.currency === this.reportingCurrency) return item;
      return {
        ...item,
        amount: convertCurrency(item.amount, item.currency as Currency, this.reportingCurrency),
        currency: this.reportingCurrency,
      };
    });

    convertedItems.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return {
      items: convertedItems,
      hasMore: false,
      total: convertedItems.length,
    };
  }

  /**
   * Merge and deduplicate refunds from all providers
   */
  async listRefunds(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedRefund>> {
    const enabledProviders = this.getEnabledProviders();
    const results = await Promise.all(
      enabledProviders.map((provider) => provider.listRefunds(params))
    );

    let allItems: NormalizedRefund[] = [];
    for (const result of results) {
      allItems = allItems.concat(result.items);
    }

    const seen = new Set<string>();
    const uniqueItems = allItems.filter((item) => {
      const key = `${item.provider}:${item.externalId}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    const convertedItems = uniqueItems.map((item) => {
      if (item.currency === this.reportingCurrency) return item;
      return {
        ...item,
        amount: convertCurrency(item.amount, item.currency as Currency, this.reportingCurrency),
        currency: this.reportingCurrency,
      };
    });

    convertedItems.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return {
      items: convertedItems,
      hasMore: false,
      total: convertedItems.length,
    };
  }

  /**
   * Merge and deduplicate payouts from all providers
   */
  async listPayouts(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedPayout>> {
    const enabledProviders = this.getEnabledProviders();
    const results = await Promise.all(
      enabledProviders.map((provider) => provider.listPayouts(params))
    );

    let allItems: NormalizedPayout[] = [];
    for (const result of results) {
      allItems = allItems.concat(result.items);
    }

    const seen = new Set<string>();
    const uniqueItems = allItems.filter((item) => {
      const key = `${item.provider}:${item.externalId}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    const convertedItems = uniqueItems.map((item) => {
      if (item.currency === this.reportingCurrency) return item;
      return {
        ...item,
        amount: convertCurrency(item.amount, item.currency as Currency, this.reportingCurrency),
        currency: this.reportingCurrency,
      };
    });

    convertedItems.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return {
      items: convertedItems,
      hasMore: false,
      total: convertedItems.length,
    };
  }

  /**
   * Get subscriptions for MRR calculation
   */
  async listSubscriptions(
    params?: BillingProviderQueryParams
  ): Promise<PaginatedBillingResult<NormalizedSubscription>> {
    const enabledProviders = this.getEnabledProviders();
    const results = await Promise.all(
      enabledProviders
        .filter((p) => p.listSubscriptions)
        .map((provider) => provider.listSubscriptions!(params))
    );

    let allItems: NormalizedSubscription[] = [];
    for (const result of results) {
      allItems = allItems.concat(result.items);
    }

    const seen = new Set<string>();
    const uniqueItems = allItems.filter((item) => {
      const key = `${item.provider}:${item.externalId}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    const convertedItems = uniqueItems.map((item) => {
      if (item.currency === this.reportingCurrency) return item;
      return {
        ...item,
        pricePerPeriod: convertCurrency(item.pricePerPeriod, item.currency as Currency, this.reportingCurrency),
        currency: this.reportingCurrency,
      };
    });

    return {
      items: convertedItems,
      hasMore: false,
      total: convertedItems.length,
    };
  }
}

/**
 * Create default aggregator instance
 */
export function createBillingAggregator(reportingCurrency: Currency = "USD"): BillingAggregator {
  const providers: BillingProvider[] = [new StripeProvider(), new SSLCommerzProvider()];
  const enabledProviders = import.meta.env.VITE_BILLING_PROVIDERS
    ? import.meta.env.VITE_BILLING_PROVIDERS.split(",").map((s) => s.trim())
    : ["stripe", "sslcommerz"];

  return new BillingAggregator({
    providers,
    reportingCurrency,
    enabledProviders,
  });
}

