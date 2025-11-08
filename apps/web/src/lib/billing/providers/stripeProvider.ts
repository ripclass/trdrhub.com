/**
 * Stripe provider implementation
 * Calls backend API to fetch Stripe billing data
 */
import type { BillingProvider } from "./BillingProvider";
import type {
  NormalizedInvoice,
  NormalizedPayment,
  NormalizedRefund,
  NormalizedPayout,
  NormalizedSubscription,
  BillingProviderQueryParams,
  PaginatedBillingResult,
} from "../types";
import { api } from "@/api/client";

export class StripeProvider implements BillingProvider {
  readonly name = "stripe";

  async listInvoices(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedInvoice>> {
    // TODO: Call backend API endpoint /billing/admin/stripe/invoices when available
    // For now, return mock data that matches the normalized format
    return this.getMockInvoices(params);
  }

  async listPayments(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedPayment>> {
    // TODO: Call backend API endpoint /billing/admin/stripe/payments when available
    return this.getMockPayments(params);
  }

  async listRefunds(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedRefund>> {
    // TODO: Call backend API endpoint /billing/admin/stripe/refunds when available
    return this.getMockRefunds(params);
  }

  async listPayouts(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedPayout>> {
    // TODO: Call backend API endpoint /billing/admin/stripe/payouts when available
    return this.getMockPayouts(params);
  }

  async listSubscriptions(
    params?: BillingProviderQueryParams
  ): Promise<PaginatedBillingResult<NormalizedSubscription>> {
    // TODO: Call backend API endpoint /billing/admin/stripe/subscriptions when available
    return this.getMockSubscriptions(params);
  }

  // Mock implementations (to be replaced with real API calls)
  private getMockInvoices(params?: BillingProviderQueryParams): PaginatedBillingResult<NormalizedInvoice> {
    const now = new Date();
    const items: NormalizedInvoice[] = Array.from({ length: 10 }).map((_, i) => {
      const date = new Date(now);
      date.setDate(date.getDate() - i * 7);
      return {
        id: `inv_stripe_${i + 1}`,
        provider: "stripe",
        externalId: `in_${i + 1}`,
        invoiceNumber: `INV-${String(i + 1).padStart(6, "0")}`,
        customerId: `cus_${i + 1}`,
        customerName: `Customer ${i + 1}`,
        customerEmail: `customer${i + 1}@example.com`,
        amount: 199900, // $1999.00 in cents
        currency: "USD",
        status: i % 4 === 0 ? "paid" : i % 4 === 1 ? "open" : i % 4 === 2 ? "void" : "uncollectible",
        issuedAt: date.toISOString(),
        dueAt: new Date(date.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        paidAt: i % 4 === 0 ? new Date(date.getTime() + 2 * 24 * 60 * 60 * 1000).toISOString() : null,
        periodStart: date.toISOString(),
        periodEnd: new Date(date.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        lineItems: [
          {
            id: `li_${i + 1}`,
            description: "LCopilot Professional Plan",
            quantity: 1,
            unitPrice: 199900,
            amount: 199900,
            taxRate: 0.0, // Stripe Tax handled separately if enabled
            taxAmount: 0,
          },
        ],
        taxAmount: 0,
        totalAmount: 199900,
        metadata: {},
        createdAt: date.toISOString(),
        updatedAt: date.toISOString(),
      };
    });

    return {
      items: items.filter((item) => {
        if (params?.status) {
          const statuses = Array.isArray(params.status) ? params.status : [params.status];
          if (!statuses.includes(item.status)) return false;
        }
        if (params?.from && item.issuedAt < params.from) return false;
        if (params?.to && item.issuedAt > params.to) return false;
        return true;
      }),
      hasMore: false,
    };
  }

  private getMockPayments(params?: BillingProviderQueryParams): PaginatedBillingResult<NormalizedPayment> {
    const now = new Date();
    const items: NormalizedPayment[] = Array.from({ length: 15 }).map((_, i) => {
      const date = new Date(now);
      date.setDate(date.getDate() - i * 3);
      return {
        id: `pay_stripe_${i + 1}`,
        provider: "stripe",
        externalId: `pi_${i + 1}`,
        invoiceId: `inv_stripe_${Math.floor(i / 2) + 1}`,
        customerId: `cus_${i + 1}`,
        customerName: `Customer ${i + 1}`,
        amount: 199900,
        currency: "USD",
        status: i % 5 === 0 ? "succeeded" : i % 5 === 1 ? "pending" : i % 5 === 2 ? "failed" : "refunded",
        paymentMethod: "card",
        paymentMethodDetails: { brand: "visa", last4: "4242" },
        processedAt: i % 5 === 0 ? date.toISOString() : null,
        createdAt: date.toISOString(),
        metadata: {},
      };
    });

    return {
      items: items.filter((item) => {
        if (params?.status) {
          const statuses = Array.isArray(params.status) ? params.status : [params.status];
          if (!statuses.includes(item.status)) return false;
        }
        if (params?.from && item.createdAt < params.from) return false;
        if (params?.to && item.createdAt > params.to) return false;
        return true;
      }),
      hasMore: false,
    };
  }

  private getMockRefunds(params?: BillingProviderQueryParams): PaginatedBillingResult<NormalizedRefund> {
    const now = new Date();
    const items: NormalizedRefund[] = Array.from({ length: 5 }).map((_, i) => {
      const date = new Date(now);
      date.setDate(date.getDate() - i * 10);
      return {
        id: `ref_stripe_${i + 1}`,
        provider: "stripe",
        externalId: `re_${i + 1}`,
        paymentId: `pay_stripe_${i + 1}`,
        invoiceId: `inv_stripe_${i + 1}`,
        amount: 50000, // Partial refund
        currency: "USD",
        status: i % 2 === 0 ? "succeeded" : "pending",
        reason: "Customer request",
        processedAt: i % 2 === 0 ? date.toISOString() : null,
        createdAt: date.toISOString(),
        metadata: {},
      };
    });

    return {
      items: items.filter((item) => {
        if (params?.status) {
          const statuses = Array.isArray(params.status) ? params.status : [params.status];
          if (!statuses.includes(item.status)) return false;
        }
        if (params?.from && item.createdAt < params.from) return false;
        if (params?.to && item.createdAt > params.to) return false;
        return true;
      }),
      hasMore: false,
    };
  }

  private getMockPayouts(params?: BillingProviderQueryParams): PaginatedBillingResult<NormalizedPayout> {
    const now = new Date();
    const items: NormalizedPayout[] = Array.from({ length: 8 }).map((_, i) => {
      const date = new Date(now);
      date.setDate(date.getDate() - i * 7);
      return {
        id: `po_stripe_${i + 1}`,
        provider: "stripe",
        externalId: `po_${i + 1}`,
        amount: 5000000, // $50,000 in cents
        currency: "USD",
        status: i % 3 === 0 ? "paid" : i % 3 === 1 ? "pending" : "failed",
        arrivalDate: i % 3 === 0 ? new Date(date.getTime() + 2 * 24 * 60 * 60 * 1000).toISOString() : null,
        description: "Weekly payout",
        createdAt: date.toISOString(),
        metadata: {},
      };
    });

    return {
      items: items.filter((item) => {
        if (params?.status) {
          const statuses = Array.isArray(params.status) ? params.status : [params.status];
          if (!statuses.includes(item.status)) return false;
        }
        if (params?.from && item.createdAt < params.from) return false;
        if (params?.to && item.createdAt > params.to) return false;
        return true;
      }),
      hasMore: false,
    };
  }

  private getMockSubscriptions(
    params?: BillingProviderQueryParams
  ): PaginatedBillingResult<NormalizedSubscription> {
    const now = new Date();
    const items: NormalizedSubscription[] = Array.from({ length: 20 }).map((_, i) => {
      const start = new Date(now);
      start.setMonth(start.getMonth() - i);
      const end = new Date(start);
      end.setMonth(end.getMonth() + 1);
      return {
        id: `sub_stripe_${i + 1}`,
        provider: "stripe",
        externalId: `sub_${i + 1}`,
        customerId: `cus_${i + 1}`,
        status: i % 5 === 0 ? "active" : i % 5 === 1 ? "canceled" : i % 5 === 2 ? "past_due" : "trialing",
        currentPeriodStart: start.toISOString(),
        currentPeriodEnd: end.toISOString(),
        cancelAtPeriodEnd: i % 3 === 0,
        canceledAt: i % 5 === 1 ? new Date(start.getTime() + 10 * 24 * 60 * 60 * 1000).toISOString() : null,
        planId: `plan_${(i % 3) + 1}`,
        planName: ["Starter", "Professional", "Enterprise"][i % 3],
        pricePerPeriod: [199900, 499900, 999900][i % 3],
        currency: "USD",
        metadata: {},
        createdAt: start.toISOString(),
        updatedAt: start.toISOString(),
      };
    });

    return {
      items: items.filter((item) => {
        if (params?.status) {
          const statuses = Array.isArray(params.status) ? params.status : [params.status];
          if (!statuses.includes(item.status)) return false;
        }
        if (params?.from && item.currentPeriodStart < params.from) return false;
        if (params?.to && item.currentPeriodStart > params.to) return false;
        return true;
      }),
      hasMore: false,
    };
  }
}

