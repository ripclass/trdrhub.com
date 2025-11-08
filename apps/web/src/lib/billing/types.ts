/**
 * Normalized billing domain types for admin console
 * These types abstract provider-specific details (Stripe, SSLCommerz)
 */

export type BillingProvider = "stripe" | "sslcommerz";

export type InvoiceStatus = "draft" | "open" | "paid" | "void" | "uncollectible";

export type PaymentStatus = "pending" | "processing" | "succeeded" | "failed" | "canceled" | "refunded";

export type RefundStatus = "pending" | "succeeded" | "failed" | "canceled";

export type PayoutStatus = "pending" | "paid" | "failed" | "canceled";

export interface NormalizedInvoice {
  id: string;
  provider: BillingProvider;
  externalId: string; // Provider-specific ID (e.g., Stripe invoice ID)
  invoiceNumber: string;
  customerId: string;
  customerName: string;
  customerEmail: string;
  amount: number; // in cents
  currency: string;
  status: InvoiceStatus;
  issuedAt: string; // ISO 8601
  dueAt: string | null;
  paidAt: string | null;
  periodStart: string | null; // Service period start (for recognition)
  periodEnd: string | null; // Service period end (for recognition)
  lineItems: InvoiceLineItem[];
  taxAmount: number; // in cents
  totalAmount: number; // amount + tax, in cents
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface InvoiceLineItem {
  id: string;
  description: string;
  quantity: number;
  unitPrice: number; // in cents
  amount: number; // in cents
  taxRate?: number; // percentage (e.g., 0.20 for 20%)
  taxAmount?: number; // in cents
}

export interface NormalizedPayment {
  id: string;
  provider: BillingProvider;
  externalId: string;
  invoiceId: string | null;
  customerId: string;
  customerName: string;
  amount: number; // in cents
  currency: string;
  status: PaymentStatus;
  paymentMethod: string; // e.g., "card", "bank_transfer"
  paymentMethodDetails?: Record<string, unknown>;
  processedAt: string | null;
  createdAt: string;
  metadata: Record<string, unknown>;
}

export interface NormalizedRefund {
  id: string;
  provider: BillingProvider;
  externalId: string;
  paymentId: string;
  invoiceId: string | null;
  amount: number; // in cents
  currency: string;
  status: RefundStatus;
  reason: string | null;
  processedAt: string | null;
  createdAt: string;
  metadata: Record<string, unknown>;
}

export interface NormalizedPayout {
  id: string;
  provider: BillingProvider;
  externalId: string;
  amount: number; // in cents
  currency: string;
  status: PayoutStatus;
  arrivalDate: string | null; // When funds arrive
  description: string | null;
  createdAt: string;
  metadata: Record<string, unknown>;
}

export interface NormalizedSubscription {
  id: string;
  provider: BillingProvider;
  externalId: string;
  customerId: string;
  status: "active" | "canceled" | "past_due" | "unpaid" | "trialing";
  currentPeriodStart: string;
  currentPeriodEnd: string;
  cancelAtPeriodEnd: boolean;
  canceledAt: string | null;
  planId: string;
  planName: string;
  pricePerPeriod: number; // in cents
  currency: string;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface BillingProviderQueryParams {
  from?: string; // ISO 8601 date
  to?: string; // ISO 8601 date
  status?: string | string[];
  limit?: number;
  cursor?: string; // For pagination
}

export interface PaginatedBillingResult<T> {
  items: T[];
  hasMore: boolean;
  nextCursor?: string;
  total?: number;
}

