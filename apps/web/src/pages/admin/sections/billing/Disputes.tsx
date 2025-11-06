import * as React from "react";
import { useSearchParams } from "react-router-dom";

import { AdminEmptyState, AdminFilters, AdminToolbar, DataTable } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { AlertCircle, CheckCircle2, ShieldHalf } from "lucide-react";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services/index";
import type { BillingDispute } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();
const PAGE_SIZE = 10;

const STATUS_OPTIONS = [
  { label: "All statuses", value: "all" },
  { label: "Open", value: "open" },
  { label: "Under review", value: "under_review" },
  { label: "Won", value: "won" },
  { label: "Lost", value: "lost" },
];

export function BillingDisputes() {
  const enabled = isAdminFeatureEnabled("billing");
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const audit = useAdminAudit("billing-disputes");
  const [page, setPage] = React.useState(() => Math.max(1, Number(searchParams.get("disputesPage") ?? "1")));
  const [statusFilter, setStatusFilter] = React.useState<BillingDispute["status"] | "all">(
    (searchParams.get("disputesStatus") as BillingDispute["status"]) ?? "open",
  );

  const [disputes, setDisputes] = React.useState<BillingDispute[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [actionId, setActionId] = React.useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const loadDisputes = React.useCallback(() => {
    if (!enabled) return;
    setLoading(true);
    service
      .listBillingDisputes({
        page,
        pageSize: PAGE_SIZE,
        status: statusFilter === "all" ? undefined : [statusFilter],
      })
      .then((result) => {
        setDisputes(result.items);
        setTotal(result.total);
      })
      .finally(() => setLoading(false));
  }, [enabled, page, statusFilter]);

  const updateQuery = React.useCallback(() => {
    const next = new URLSearchParams(searchParams);
    if (page === 1) next.delete("disputesPage");
    else next.set("disputesPage", String(page));
    if (statusFilter === "all") next.delete("disputesStatus");
    else next.set("disputesStatus", statusFilter);
    setSearchParams(next, { replace: true });
  }, [page, statusFilter, searchParams, setSearchParams]);

  React.useEffect(() => {
    updateQuery();
    loadDisputes();
  }, [updateQuery, loadDisputes]);

  const handleResolve = async (id: string, outcome: "won" | "lost" | "write_off") => {
    setActionId(id);
    const result = await service.resolveDispute(id, outcome);
    setActionId(null);
    toast({
      title: result.success ? `Marked ${outcome}` : "Unable to update dispute",
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      await audit("resolve_dispute", { entityId: id, metadata: { outcome } });
      loadDisputes();
    }
  };

  if (!enabled) {
    return (
      <div className="rounded-lg border border-dashed border-amber-500/40 bg-amber-500/5 p-6 text-sm text-amber-600">
        Billing disputes are hidden while the billing module flag is disabled.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Dispute resolution"
        description="Coordinate evidence submission timelines and final rulings."
      >
        <AdminFilters
          filterGroups={[
            {
              label: "Status",
              value: statusFilter,
              options: STATUS_OPTIONS,
              onChange: (value) => {
                setStatusFilter((value as BillingDispute["status"]) || "all");
                setPage(1);
              },
              allowClear: true,
            },
          ]}
          endAdornment={
            <Button size="sm" variant="outline" onClick={loadDisputes} disabled={loading} className="gap-2">
              <ShieldHalf className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh
            </Button>
          }
        />
      </AdminToolbar>

      <DataTable
        columns={[
          {
            key: "customer",
            header: "Customer",
            render: (dispute) => (
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">{dispute.customer}</p>
                <p className="text-xs text-muted-foreground">Opened {new Date(dispute.openedAt).toLocaleString()}</p>
              </div>
            ),
          },
          {
            key: "amount",
            header: "Amount",
            render: (dispute) => (
              <span className="text-sm font-semibold text-rose-600">
                {dispute.currency} {(dispute.amount / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
            ),
          },
          {
            key: "reason",
            header: "Reason",
            render: (dispute) => <span className="text-sm text-muted-foreground">{dispute.reason}</span>,
          },
          {
            key: "status",
            header: "Status",
            render: (dispute) => (
              <Badge
                variant={
                  dispute.status === "open"
                    ? "destructive"
                    : dispute.status === "under_review"
                      ? "secondary"
                      : "outline"
                }
              >
                {dispute.status}
              </Badge>
            ),
          },
          {
            key: "actions",
            header: "Actions",
            align: "right",
            render: (dispute) => (
              <div className="flex items-center justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={actionId === dispute.id}
                  onClick={() => handleResolve(dispute.id, "won")}
                  className="gap-1 text-emerald-600"
                >
                  <CheckCircle2 className="h-4 w-4" /> Win
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={actionId === dispute.id}
                  onClick={() => handleResolve(dispute.id, "lost")}
                  className="gap-1 text-rose-600"
                >
                  Lose
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={actionId === dispute.id}
                  onClick={() => handleResolve(dispute.id, "write_off")}
                  className="gap-1 text-amber-600"
                >
                  Write off
                </Button>
              </div>
            ),
          },
        ]}
        data={disputes}
        loading={loading}
        emptyState={<AdminEmptyState title="No disputes" description="No open or historical disputes in this view." />}
        footer={
          total > PAGE_SIZE && (
            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    href="#"
                    className={page === 1 ? "pointer-events-none opacity-50" : undefined}
                    onClick={(event) => {
                      event.preventDefault();
                      if (page > 1) setPage(page - 1);
                    }}
                  />
                </PaginationItem>
                <PaginationItem>
                  <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
                </PaginationItem>
                <PaginationItem>
                  <PaginationNext
                    href="#"
                    className={page >= totalPages ? "pointer-events-none opacity-50" : undefined}
                    onClick={(event) => {
                      event.preventDefault();
                      if (page < totalPages) setPage(page + 1);
                    }}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          )
        }
      />

      {loading && disputes.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>
      )}

      <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-xs text-muted-foreground">
        <p className="font-medium text-foreground">Evidence reminders</p>
        <p className="mt-1">Evidence due within 3 business days for open disputes. Coordinate with finance to upload documentation.</p>
      </div>
    </div>
  );
}

export default BillingDisputes;
