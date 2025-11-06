import * as React from "react";

import { AdminEmptyState, AdminFilters, AdminToolbar, DataTable } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { Globe2, RefreshCw } from "lucide-react";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services";
import type { WebhookDelivery } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();
const PAGE_SIZE = 15;

const STATUS_OPTIONS = [
  { label: "All statuses", value: "all" },
  { label: "Delivered", value: "delivered" },
  { label: "Pending", value: "pending" },
  { label: "Failed", value: "failed" },
];

export function PartnersWebhooks() {
  const enabled = isAdminFeatureEnabled("partners");
  const { toast } = useToast();
  const [statusFilter, setStatusFilter] = React.useState<WebhookDelivery["status"] | "all">("all");
  const [page, setPage] = React.useState(1);
  const [deliveries, setDeliveries] = React.useState<WebhookDelivery[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [actionId, setActionId] = React.useState<string | null>(null);
  const audit = useAdminAudit("partners-webhooks");

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const loadDeliveries = React.useCallback(() => {
    if (!enabled) return;
    setLoading(true);
    service
      .listWebhookDeliveries({
        page,
        pageSize: PAGE_SIZE,
        status: statusFilter === "all" ? undefined : statusFilter,
      })
      .then((result) => {
        setDeliveries(result.items);
        setTotal(result.total);
      })
      .finally(() => setLoading(false));
  }, [enabled, page, statusFilter]);

  React.useEffect(() => {
    loadDeliveries();
  }, [loadDeliveries]);

  const handleRedeliver = async (id: string) => {
    setActionId(id);
    const result = await service.redeliverWebhook(id);
    await audit("redeliver_webhook", { entityId: id, metadata: { success: result.success } });
    setActionId(null);
    toast({
      title: result.success ? "Redelivery queued" : "Redelivery failed",
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) loadDeliveries();
  };

  if (!enabled) {
    return (
      <div className="rounded-lg border border-dashed border-blue-500/40 bg-blue-500/5 p-6 text-sm text-blue-600">
        Turn on the <strong>partners</strong> flag to monitor webhook deliveries.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Outbound webhooks"
        description="Replay failed deliveries and monitor subscriber endpoints."
      >
        <AdminFilters
          filterGroups={[
            {
              label: "Status",
              value: statusFilter,
              options: STATUS_OPTIONS,
              onChange: (value) => {
                setStatusFilter((value as WebhookDelivery["status"]) || "all");
                setPage(1);
              },
              allowClear: true,
            },
          ]}
          endAdornment={
            <Button size="sm" variant="outline" onClick={loadDeliveries} disabled={loading} className="gap-2">
              <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh
            </Button>
          }
        />
      </AdminToolbar>

      <DataTable
        columns={[
          {
            key: "event",
            header: "Event",
            render: (delivery) => (
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">{delivery.event}</p>
                <p className="text-xs font-mono text-muted-foreground">{delivery.endpoint}</p>
              </div>
            ),
          },
          {
            key: "sentAt",
            header: "Last attempt",
            render: (delivery) => (
              <span className="text-xs text-muted-foreground">
                {delivery.sentAt ? new Date(delivery.sentAt).toLocaleString() : "—"}
              </span>
            ),
          },
          {
            key: "responseCode",
            header: "Response",
            render: (delivery) => (
              <span className="text-xs text-muted-foreground">{delivery.responseCode ?? "—"}</span>
            ),
          },
          {
            key: "retryCount",
            header: "Retries",
            render: (delivery) => <span className="text-xs text-muted-foreground">{delivery.retryCount}</span>,
          },
          {
            key: "status",
            header: "Status",
            render: (delivery) => (
              <Badge
                variant={
                  delivery.status === "failed"
                    ? "destructive"
                    : delivery.status === "pending"
                      ? "secondary"
                      : "outline"
                }
              >
                {delivery.status}
              </Badge>
            ),
          },
          {
            key: "actions",
            header: "Actions",
            align: "right",
            render: (delivery) => (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleRedeliver(delivery.id)}
                disabled={actionId === delivery.id}
                className="gap-1"
              >
                Redeliver
              </Button>
            ),
          },
        ]}
        data={deliveries}
        loading={loading}
        emptyState={<AdminEmptyState title="No deliveries" description="No webhook events in this timeframe." />}
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

      {loading && deliveries.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>
      )}

      <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-xs text-muted-foreground">
        <p className="font-medium text-foreground">Webhook hygiene</p>
        <p className="mt-1">Rotate signing secrets regularly and monitor failure spikes to prevent notification drift.</p>
      </div>
    </div>
  );
}

export default PartnersWebhooks;
