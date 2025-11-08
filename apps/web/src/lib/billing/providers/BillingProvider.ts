/**
 * BillingProvider interface for abstracting payment provider APIs
 */
import type {
  NormalizedInvoice,
  NormalizedPayment,
  NormalizedRefund,
  NormalizedPayout,
  NormalizedSubscription,
  BillingProviderQueryParams,
  PaginatedBillingResult,
} from "./types";

export interface BillingProvider {
  readonly name: string;

  /**
   * List invoices from this provider
   */
  listInvoices(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedInvoice>>;

  /**
   * List payments from this provider
   */
  listPayments(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedPayment>>;

  /**
   * List refunds from this provider
   */
  listRefunds(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedRefund>>;

  /**
   * List payouts from this provider
   */
  listPayouts(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedPayout>>;

  /**
   * List subscriptions (optional - for MRR calculation)
   */
  listSubscriptions?(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedSubscription>>;
}

