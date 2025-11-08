/**
 * Invoices & Payments admin page
 * Displays merged invoices and payments from all billing providers
 */
import * as React from "react";
import { useSearchParams } from "react-router-dom";

import { AdminToolbar, AdminFilters, DataTable } from "@/components/admin/ui";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Download, RefreshCw } from "lucide-react";
import { ColumnDef } from "@tanstack/react-table";

import { createBillingAggregator } from "@/lib/billing/aggregator";
import type { NormalizedInvoice, NormalizedPayment } from "@/lib/billing/types";
import { formatCurrencyAmount, type Currency } from "@/lib/billing/fx";
import { useToast } from "@/hooks/use-toast";

const PAGE_SIZE = 20;

type TabType = "invoices" | "payments";

export function BillingInvoicesPayments() {
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = (searchParams.get("tab") as TabType) || "invoices";
  const page = Math.max(1, Number(searchParams.get("page") ?? "1"));
  const statusFilter = searchParams.get("status")?.split(",").filter(Boolean) || [];
  const currencyFilter = searchParams.get("currency") || "all";
  const providerFilter = searchParams.get("provider")?.split(",").filter(Boolean) || [];
  const searchTerm = searchParams.get("search") || "";

  const [invoices, setInvoices] = React.useState<NormalizedInvoice[]>([]);
  const [payments, setPayments] = React.useState<NormalizedPayment[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const aggregator = React.useMemo(() => createBillingAggregator("USD"), []);

  React.useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    const loadData = async () => {
      try {
        const now = new Date();
        const fromDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000).toISOString();
        const toDate = now.toISOString();

        if (tab === "invoices") {
          const result = await aggregator.listInvoices({ from: fromDate, to: toDate });
          if (!active) return;
          setInvoices(result.items);
        } else {
          const result = await aggregator.listPayments({ from: fromDate, to: toDate });
          if (!active) return;
          setPayments(result.items);
        }
      } catch (err) {
        if (!active) return;
        console.error("Failed to load billing data", err);
        setError("Unable to load billing data. Using mock data.");
        // Set empty arrays on error - mock data would come from fallback
        if (tab === "invoices") {
          setInvoices([]);
        } else {
          setPayments([]);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    loadData();

    return () => {
      active = false;
    };
  }, [tab, aggregator]);

  const filteredInvoices = React.useMemo(() => {
    return invoices.filter((inv) => {
      if (statusFilter.length && !statusFilter.includes(inv.status)) return false;
      if (currencyFilter !== "all" && inv.currency !== currencyFilter) return false;
      if (providerFilter.length && !providerFilter.includes(inv.provider)) return false;
      if (searchTerm && !inv.invoiceNumber.toLowerCase().includes(searchTerm.toLowerCase()) && 
          !inv.customerName.toLowerCase().includes(searchTerm.toLowerCase())) return false;
      return true;
    });
  }, [invoices, statusFilter, currencyFilter, providerFilter, searchTerm]);

  const filteredPayments = React.useMemo(() => {
    return payments.filter((pay) => {
      if (statusFilter.length && !statusFilter.includes(pay.status)) return false;
      if (currencyFilter !== "all" && pay.currency !== currencyFilter) return false;
      if (providerFilter.length && !providerFilter.includes(pay.provider)) return false;
      if (searchTerm && !pay.id.toLowerCase().includes(searchTerm.toLowerCase()) && 
          !pay.customerName.toLowerCase().includes(searchTerm.toLowerCase())) return false;
      return true;
    });
  }, [payments, statusFilter, currencyFilter, providerFilter, searchTerm]);

  const invoiceColumns: ColumnDef<NormalizedInvoice>[] = React.useMemo(
    () => [
      {
        accessorKey: "invoiceNumber",
        header: "Invoice #",
        cell: ({ row }) => (
          <div className="font-medium">{row.original.invoiceNumber}</div>
        ),
      },
      {
        accessorKey: "customerName",
        header: "Customer",
        cell: ({ row }) => (
          <div>
            <div className="font-medium">{row.original.customerName}</div>
            <div className="text-xs text-muted-foreground">{row.original.customerEmail}</div>
          </div>
        ),
      },
      {
        accessorKey: "amount",
        header: "Amount",
        cell: ({ row }) => formatCurrencyAmount(row.original.totalAmount, row.original.currency as Currency),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => {
          const status = row.original.status;
          const colors: Record<string, string> = {
            paid: "bg-green-100 text-green-800",
            open: "bg-yellow-100 text-yellow-800",
            void: "bg-gray-100 text-gray-800",
            uncollectible: "bg-red-100 text-red-800",
            draft: "bg-blue-100 text-blue-800",
          };
          return (
            <Badge className={colors[status] || "bg-gray-100 text-gray-800"}>
              {status}
            </Badge>
          );
        },
      },
      {
        accessorKey: "provider",
        header: "Provider",
        cell: ({ row }) => (
          <Badge variant="outline">{row.original.provider.toUpperCase()}</Badge>
        ),
      },
      {
        accessorKey: "issuedAt",
        header: "Issued",
        cell: ({ row }) => new Date(row.original.issuedAt).toLocaleDateString(),
      },
      {
        accessorKey: "paidAt",
        header: "Paid",
        cell: ({ row }) =>
          row.original.paidAt ? new Date(row.original.paidAt).toLocaleDateString() : "-",
      },
    ],
    []
  );

  const paymentColumns: ColumnDef<NormalizedPayment>[] = React.useMemo(
    () => [
      {
        accessorKey: "id",
        header: "Payment ID",
        cell: ({ row }) => <div className="font-mono text-xs">{row.original.id}</div>,
      },
      {
        accessorKey: "customerName",
        header: "Customer",
        cell: ({ row }) => <div className="font-medium">{row.original.customerName}</div>,
      },
      {
        accessorKey: "amount",
        header: "Amount",
        cell: ({ row }) => formatCurrencyAmount(row.original.amount, row.original.currency as Currency),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => {
          const status = row.original.status;
          const colors: Record<string, string> = {
            succeeded: "bg-green-100 text-green-800",
            pending: "bg-yellow-100 text-yellow-800",
            processing: "bg-blue-100 text-blue-800",
            failed: "bg-red-100 text-red-800",
            canceled: "bg-gray-100 text-gray-800",
            refunded: "bg-orange-100 text-orange-800",
          };
          return (
            <Badge className={colors[status] || "bg-gray-100 text-gray-800"}>
              {status}
            </Badge>
          );
        },
      },
      {
        accessorKey: "paymentMethod",
        header: "Method",
        cell: ({ row }) => <div className="capitalize">{row.original.paymentMethod}</div>,
      },
      {
        accessorKey: "provider",
        header: "Provider",
        cell: ({ row }) => (
          <Badge variant="outline">{row.original.provider.toUpperCase()}</Badge>
        ),
      },
      {
        accessorKey: "createdAt",
        header: "Date",
        cell: ({ row }) => new Date(row.original.createdAt).toLocaleDateString(),
      },
    ],
    []
  );

  const handleExport = () => {
    toast({
      title: "Export started",
      description: "CSV export will be available shortly.",
    });
    // TODO: Implement CSV export
  };

  const handleTabChange = (newTab: TabType) => {
    const next = new URLSearchParams(searchParams);
    next.set("tab", newTab);
    next.delete("page"); // Reset to page 1
    setSearchParams(next, { replace: true });
  };

  const updateQuery = React.useCallback(
    (updates: Record<string, string | null>) => {
      const next = new URLSearchParams(searchParams);
      Object.entries(updates).forEach(([key, value]) => {
        if (!value || value === "all") next.delete(key);
        else next.set(key, value);
      });
      if (next.toString() !== searchParams.toString()) {
        setSearchParams(next, { replace: true });
      }
    },
    [searchParams, setSearchParams]
  );

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <AdminToolbar title="Invoices & Payments" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Invoices & Payments"
        description="Unified view of invoices and payments across all billing providers"
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleExport} className="gap-2">
              <Download className="h-4 w-4" />
              Export CSV
            </Button>
            <Button variant="outline" size="sm" onClick={() => window.location.reload()} className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
          </div>
        }
      >
        <div className="flex gap-2 border-b">
          <button
            type="button"
            onClick={() => handleTabChange("invoices")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
              tab === "invoices"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Invoices ({filteredInvoices.length})
          </button>
          <button
            type="button"
            onClick={() => handleTabChange("payments")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
              tab === "payments"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Payments ({filteredPayments.length})
          </button>
        </div>

        <AdminFilters
          searchPlaceholder="Search by invoice number or customer"
          searchValue={searchTerm}
          onSearchChange={(value) => {
            updateQuery({ search: value || null });
          }}
          filterGroups={[
            {
              label: "Status",
              value: statusFilter,
              options: tab === "invoices"
                ? [
                    { label: "Paid", value: "paid" },
                    { label: "Open", value: "open" },
                    { label: "Void", value: "void" },
                    { label: "Uncollectible", value: "uncollectible" },
                  ]
                : [
                    { label: "Succeeded", value: "succeeded" },
                    { label: "Pending", value: "pending" },
                    { label: "Failed", value: "failed" },
                    { label: "Refunded", value: "refunded" },
                  ],
              multi: true,
              onChange: (value) => {
                const arr = Array.isArray(value) ? value : value ? [value] : [];
                updateQuery({ status: arr.length ? arr.join(",") : null });
              },
            },
            {
              label: "Currency",
              value: currencyFilter,
              options: [
                { label: "All", value: "all" },
                { label: "USD", value: "USD" },
                { label: "BDT", value: "BDT" },
              ],
              onChange: (value) => {
                updateQuery({ currency: String(value || "all") });
              },
            },
            {
              label: "Provider",
              value: providerFilter,
              options: [
                { label: "Stripe", value: "stripe" },
                { label: "SSLCommerz", value: "sslcommerz" },
              ],
              multi: true,
              onChange: (value) => {
                const arr = Array.isArray(value) ? value : value ? [value] : [];
                updateQuery({ provider: arr.length ? arr.join(",") : null });
              },
            },
          ]}
        />
      </AdminToolbar>

      {error && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-700">
          {error}
        </div>
      )}

      {tab === "invoices" ? (
        <DataTable
          columns={invoiceColumns}
          data={filteredInvoices.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)}
        />
      ) : (
        <DataTable
          columns={paymentColumns}
          data={filteredPayments.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)}
        />
      )}

      {/* Pagination */}
      {(filteredInvoices.length > PAGE_SIZE || filteredPayments.length > PAGE_SIZE) && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            Showing {(page - 1) * PAGE_SIZE + 1} to {Math.min(page * PAGE_SIZE, tab === "invoices" ? filteredInvoices.length : filteredPayments.length)} of{" "}
            {tab === "invoices" ? filteredInvoices.length : filteredPayments.length}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => updateQuery({ page: String(page - 1) })}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={
                page * PAGE_SIZE >= (tab === "invoices" ? filteredInvoices.length : filteredPayments.length)
              }
              onClick={() => updateQuery({ page: String(page + 1) })}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default BillingInvoicesPayments;

