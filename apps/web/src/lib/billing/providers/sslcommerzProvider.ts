/**
 * SSLCommerz provider implementation
 * Calls backend API to fetch SSLCommerz billing data
 */
import type { BillingProvider } from "./BillingProvider";
import type {
  NormalizedInvoice,
  NormalizedPayment,
  NormalizedRefund,
  NormalizedPayout,
  BillingProviderQueryParams,
  PaginatedBillingResult,
} from "../types";

export class SSLCommerzProvider implements BillingProvider {
  readonly name = "sslcommerz";

  async listInvoices(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedInvoice>> {
    // TODO: Call backend API endpoint /billing/admin/sslcommerz/invoices when available
    // SSLCommerz doesn't have native invoices, so we'll derive from transactions
    return this.getMockInvoices(params);
  }

  async listPayments(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedPayment>> {
    // TODO: Call backend API endpoint /billing/admin/sslcommerz/payments when available
    return this.getMockPayments(params);
  }

  async listRefunds(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedRefund>> {
    // TODO: Call backend API endpoint /billing/admin/sslcommerz/refunds when available
    return this.getMockRefunds(params);
  }

  async listPayouts(params?: BillingProviderQueryParams): Promise<PaginatedBillingResult<NormalizedPayout>> {
    // TODO: SSLCommerz payouts are typically manual or via bank transfer
    // Return empty or mock data
    return this.getMockPayouts(params);
  }

  // Mock implementations (to be replaced with real API calls)
  private getMockInvoices(params?: BillingProviderQueryParams): PaginatedBillingResult<NormalizedInvoice> {
    const now = new Date();
    const items: NormalizedInvoice[] = Array.from({ length: 8 }).map((_, i) => {
      const date = new Date(now);
      date.setDate(date.getDate() - i * 7);
      return {
        id: `inv_ssl_${i + 1}`,
        provider: "sslcommerz",
        externalId: `tran_${i + 1}`,
        invoiceNumber: `SSL-INV-${String(i + 1).padStart(6, "0")}`,
        customerId: `cust_${i + 1}`,
        customerName: `Customer ${i + 1}`,
        customerEmail: `customer${i + 1}@example.com`,
        amount: 1500000, // 15,000 BDT in paisa (smallest unit)
        currency: "BDT",
        status: i % 4 === 0 ? "paid" : i % 4 === 1 ? "open" : i % 4 === 2 ? "void" : "uncollectible",
        issuedAt: date.toISOString(),
        dueAt: new Date(date.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        paidAt: i % 4 === 0 ? new Date(date.getTime() + 1 * 24 * 60 * 60 * 1000).toISOString() : null,
        periodStart: date.toISOString(),
        periodEnd: new Date(date.getTime() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        lineItems: [
          {
            id: `li_ssl_${i + 1}`,
            description: "LCopilot Starter Plan",
            quantity: 1,
            unitPrice: 1500000,
            amount: 1500000,
            taxRate: 0.0, // VAT may apply in Bangladesh
            taxAmount: 0,
          },
        ],
        taxAmount: 0,
        totalAmount: 1500000,
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
    const items: NormalizedPayment[] = Array.from({ length: 12 }).map((_, i) => {
      const date = new Date(now);
      date.setDate(date.getDate() - i * 2);
      return {
        id: `pay_ssl_${i + 1}`,
        provider: "sslcommerz",
        externalId: `tran_${i + 1}`,
        invoiceId: `inv_ssl_${Math.floor(i / 2) + 1}`,
        customerId: `cust_${i + 1}`,
        customerName: `Customer ${i + 1}`,
        amount: 1500000,
        currency: "BDT",
        status: i % 4 === 0 ? "succeeded" : i % 4 === 1 ? "pending" : i % 4 === 2 ? "failed" : "canceled",
        paymentMethod: ["card", "mobile_banking", "bank_transfer"][i % 3],
        paymentMethodDetails: {},
        processedAt: i % 4 === 0 ? date.toISOString() : null,
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
    const items: NormalizedRefund[] = Array.from({ length: 3 }).map((_, i) => {
      const date = new Date(now);
      date.setDate(date.getDate() - i * 15);
      return {
        id: `ref_ssl_${i + 1}`,
        provider: "sslcommerz",
        externalId: `ref_${i + 1}`,
        paymentId: `pay_ssl_${i + 1}`,
        invoiceId: `inv_ssl_${i + 1}`,
        amount: 300000, // Partial refund
        currency: "BDT",
        status: i % 2 === 0 ? "succeeded" : "pending",
        reason: "Service issue",
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
    // SSLCommerz payouts are typically manual bank transfers
    const now = new Date();
    const items: NormalizedPayout[] = Array.from({ length: 4 }).map((_, i) => {
      const date = new Date(now);
      date.setDate(date.getDate() - i * 14);
      return {
        id: `po_ssl_${i + 1}`,
        provider: "sslcommerz",
        externalId: `payout_${i + 1}`,
        amount: 50000000, // 500,000 BDT in paisa
        currency: "BDT",
        status: i % 2 === 0 ? "paid" : "pending",
        arrivalDate: i % 2 === 0 ? new Date(date.getTime() + 3 * 24 * 60 * 60 * 1000).toISOString() : null,
        description: "Bi-weekly payout",
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
}

