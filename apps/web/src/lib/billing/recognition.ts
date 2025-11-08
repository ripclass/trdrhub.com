/**
 * Revenue recognition engine
 * Implements accrual accounting: recognizes revenue over service period
 */
import type { NormalizedInvoice } from "../types";

export interface RecognizedRevenue {
  date: string; // ISO 8601 date (YYYY-MM-DD)
  recognizedAmount: number; // in cents
  deferredAmount: number; // in cents
  invoiceId: string;
  customerId: string;
}

export interface RecognitionSummary {
  totalRecognized: number; // in cents
  totalDeferred: number; // in cents
  dailyBreakdown: RecognizedRevenue[];
  monthlyBreakdown: Array<{
    month: string; // YYYY-MM
    recognized: number;
    deferred: number;
  }>;
}

/**
 * Calculate revenue recognition for invoices
 * Uses straight-line method over service period
 */
export function calculateRecognition(
  invoices: NormalizedInvoice[],
  fromDate?: string,
  toDate?: string
): RecognitionSummary {
  const from = fromDate ? new Date(fromDate) : new Date(0);
  const to = toDate ? new Date(toDate) : new Date();

  const dailyBreakdown: Map<string, RecognizedRevenue> = new Map();
  let totalRecognized = 0;
  let totalDeferred = 0;

  for (const invoice of invoices) {
    if (!invoice.periodStart || !invoice.periodEnd) {
      // No service period - recognize immediately if paid
      if (invoice.status === "paid" && invoice.paidAt) {
        const paidDate = invoice.paidAt.split("T")[0];
        const existing = dailyBreakdown.get(paidDate) || {
          date: paidDate,
          recognizedAmount: 0,
          deferredAmount: 0,
          invoiceId: invoice.id,
          customerId: invoice.customerId,
        };
        existing.recognizedAmount += invoice.totalAmount;
        totalRecognized += invoice.totalAmount;
        dailyBreakdown.set(paidDate, existing);
      }
      continue;
    }

    const periodStart = new Date(invoice.periodStart);
    const periodEnd = new Date(invoice.periodEnd);
    const periodDays = Math.max(1, Math.ceil((periodEnd.getTime() - periodStart.getTime()) / (1000 * 60 * 60 * 24)));
    const dailyAmount = Math.round(invoice.totalAmount / periodDays);

    // Distribute revenue across service period days
    for (let d = 0; d < periodDays; d++) {
      const currentDate = new Date(periodStart);
      currentDate.setDate(currentDate.getDate() + d);
      const dateStr = currentDate.toISOString().split("T")[0];

      if (currentDate < from || currentDate > to) continue;

      const existing = dailyBreakdown.get(dateStr) || {
        date: dateStr,
        recognizedAmount: 0,
        deferredAmount: 0,
        invoiceId: invoice.id,
        customerId: invoice.customerId,
      };

      // If invoice is paid and payment date has passed, recognize; otherwise defer
      const isPaid = invoice.status === "paid" && invoice.paidAt;
      const paidDate = isPaid ? new Date(invoice.paidAt) : null;
      const isRecognized = isPaid && paidDate && currentDate >= paidDate;

      if (isRecognized) {
        existing.recognizedAmount += dailyAmount;
        totalRecognized += dailyAmount;
      } else {
        existing.deferredAmount += dailyAmount;
        totalDeferred += dailyAmount;
      }

      dailyBreakdown.set(dateStr, existing);
    }
  }

  // Aggregate by month
  const monthlyMap = new Map<string, { recognized: number; deferred: number }>();
  for (const [dateStr, revenue] of dailyBreakdown.entries()) {
    const month = dateStr.substring(0, 7); // YYYY-MM
    const existing = monthlyMap.get(month) || { recognized: 0, deferred: 0 };
    existing.recognized += revenue.recognizedAmount;
    existing.deferred += revenue.deferredAmount;
    monthlyMap.set(month, existing);
  }

  const monthlyBreakdown = Array.from(monthlyMap.entries())
    .map(([month, amounts]) => ({
      month,
      recognized: amounts.recognized,
      deferred: amounts.deferred,
    }))
    .sort((a, b) => a.month.localeCompare(b.month));

  return {
    totalRecognized,
    totalDeferred,
    dailyBreakdown: Array.from(dailyBreakdown.values()).sort((a, b) => a.date.localeCompare(b.date)),
    monthlyBreakdown,
  };
}

/**
 * Get deferred revenue balance as of a specific date
 */
export function getDeferredRevenueBalance(invoices: NormalizedInvoice[], asOfDate: string): number {
  const asOf = new Date(asOfDate);
  let deferred = 0;

  for (const invoice of invoices) {
    if (!invoice.periodStart || !invoice.periodEnd) continue;
    if (invoice.status === "void" || invoice.status === "uncollectible") continue;

    const periodStart = new Date(invoice.periodStart);
    const periodEnd = new Date(invoice.periodEnd);

    // If invoice period hasn't started, all is deferred
    if (asOf < periodStart) {
      deferred += invoice.totalAmount;
      continue;
    }

    // If invoice period has ended, nothing is deferred
    if (asOf >= periodEnd) {
      continue;
    }

    // Calculate portion still deferred
    const totalDays = Math.max(
      1,
      Math.ceil((periodEnd.getTime() - periodStart.getTime()) / (1000 * 60 * 60 * 24))
    );
    const daysElapsed = Math.max(0, Math.ceil((asOf.getTime() - periodStart.getTime()) / (1000 * 60 * 60 * 24)));
    const daysRemaining = totalDays - daysElapsed;
    const deferredPortion = Math.round((invoice.totalAmount * daysRemaining) / totalDays);

    deferred += deferredPortion;
  }

  return deferred;
}

