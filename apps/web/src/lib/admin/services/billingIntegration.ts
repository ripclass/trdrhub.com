/**
 * Billing service integration for admin console
 * Bridges aggregator data to admin service interface
 */
import type { BillingSummary, TimeRange } from "../types";
import { createBillingAggregator } from "../../billing/aggregator";
import { calculateRecognition, getDeferredRevenueBalance } from "../../billing/recognition";
import { calculateTaxSummaries, createTaxEngineConfig } from "../../billing/tax";
import type { Currency } from "../../billing/fx";

let aggregatorInstance: ReturnType<typeof createBillingAggregator> | null = null;

function getAggregator(currency: Currency = "USD") {
  if (!aggregatorInstance) {
    aggregatorInstance = createBillingAggregator(currency);
  }
  return aggregatorInstance;
}

/**
 * Get billing summary from aggregator
 * Falls back to mock if aggregator fails
 */
export async function getBillingSummaryFromAggregator(
  range?: TimeRange,
  currency?: string
): Promise<BillingSummary | null> {
  try {
    const reportingCurrency = (currency as Currency) || "USD";
    const aggregator = getAggregator(reportingCurrency);

    // Calculate date range
    const now = new Date();
    const toDate = now.toISOString();
    let fromDate: string;
    switch (range) {
      case "7d":
        fromDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString();
        break;
      case "30d":
        fromDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString();
        break;
      case "90d":
        fromDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000).toISOString();
        break;
      default:
        fromDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString();
    }

    // Fetch data from aggregator
    const [invoices, payments, refunds, subscriptions] = await Promise.all([
      aggregator.listInvoices({ from: fromDate, to: toDate }),
      aggregator.listPayments({ from: fromDate, to: toDate }),
      aggregator.listRefunds({ from: fromDate, to: toDate }),
      aggregator.listSubscriptions({ from: fromDate, to: toDate }),
    ]);

    // Calculate MRR from active subscriptions
    const activeSubscriptions = subscriptions.items.filter((sub) => sub.status === "active");
    const mrrCents = activeSubscriptions.reduce((sum, sub) => {
      // Convert period price to monthly (assuming monthly periods for now)
      return sum + sub.pricePerPeriod;
    }, 0);

    // ARR = MRR * 12
    const arrCents = mrrCents * 12;

    // Month-to-date revenue: sum of paid invoices this month
    const monthStart = new Date();
    monthStart.setDate(1);
    monthStart.setHours(0, 0, 0, 0);
    const monthStartIso = monthStart.toISOString();

    const paidInvoicesThisMonth = invoices.items.filter(
      (inv) => inv.status === "paid" && inv.paidAt && inv.paidAt >= monthStartIso
    );
    const monthToDateCents = paidInvoicesThisMonth.reduce((sum, inv) => sum + inv.totalAmount, 0);

    // Refunds this month
    const refundsThisMonth = refunds.items.filter(
      (ref) => ref.status === "succeeded" && ref.processedAt && ref.processedAt >= monthStartIso
    );
    const refundsCents = refundsThisMonth.reduce((sum, ref) => sum + ref.amount, 0);

    // Net revenue = MTD - refunds
    const netRevenueCents = monthToDateCents - refundsCents;

    // Disputes: count invoices with uncollectible status
    const disputesOpen = invoices.items.filter((inv) => inv.status === "uncollectible").length;

    // Invoices this month
    const invoicesThisMonth = invoices.items.filter((inv) => inv.issuedAt >= monthStartIso).length;

    // Adjustments pending: count open invoices
    const adjustmentsPending = invoices.items.filter((inv) => inv.status === "open").length;

    return {
      mrrCents,
      arrCents,
      monthToDateCents,
      netRevenueCents,
      refundsCents,
      disputesOpen,
      invoicesThisMonth,
      adjustmentsPending,
    };
  } catch (error) {
    console.error("Failed to get billing summary from aggregator", error);
    return null; // Fallback to mock
  }
}

/**
 * Get recognition data for date range
 */
export async function getRecognitionData(fromDate: string, toDate: string) {
  try {
    const aggregator = getAggregator("USD");
    const invoices = await aggregator.listInvoices({ from: fromDate, to: toDate });
    return calculateRecognition(invoices.items, fromDate, toDate);
  } catch (error) {
    console.error("Failed to get recognition data", error);
    return null;
  }
}

/**
 * Get tax summaries for date range
 */
export async function getTaxSummaries(fromDate: string, toDate: string) {
  try {
    const aggregator = getAggregator("USD");
    const [invoices, payments] = await Promise.all([
      aggregator.listInvoices({ from: fromDate, to: toDate }),
      aggregator.listPayments({ from: fromDate, to: toDate }),
    ]);

    const config = createTaxEngineConfig();
    return calculateTaxSummaries(invoices.items, payments.items, config);
  } catch (error) {
    console.error("Failed to get tax summaries", error);
    return [];
  }
}

