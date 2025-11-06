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
import { FlaskConical } from "lucide-react";

import { isAdminFeatureEnabled } from "@/config/featureFlags";
import { getAdminService } from "@/lib/admin/services";
import type { EvaluationRun } from "@/lib/admin/types";

const service = getAdminService();
const PAGE_SIZE = 10;

const STATUS_OPTIONS = [
  { label: "All statuses", value: "all" },
  { label: "Completed", value: "completed" },
  { label: "Running", value: "running" },
  { label: "Pending", value: "pending" },
  { label: "Failed", value: "failed" },
];

export function LLMEvaluations() {
  const enabled = isAdminFeatureEnabled("llm");
  const { toast } = useToast();
  const [page, setPage] = React.useState(1);
  const [statusFilter, setStatusFilter] = React.useState<EvaluationRun["status"] | "all">("all");

  const [runs, setRuns] = React.useState<EvaluationRun[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const loadRuns = React.useCallback(() => {
    if (!enabled) return;
    setLoading(true);
    service
      .listEvaluationRuns({
        page,
        pageSize: PAGE_SIZE,
        status: statusFilter === "all" ? undefined : [statusFilter],
      })
      .then((result) => {
        setRuns(result.items);
        setTotal(result.total);
      })
      .finally(() => setLoading(false));
  }, [enabled, page, statusFilter]);

  React.useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  if (!enabled) {
    return (
      <div className="rounded-lg border border-dashed border-purple-500/40 bg-purple-500/5 p-6 text-sm text-purple-600">
        Switch on the <strong>llm</strong> feature flag to review evaluation runs.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Evaluation runs"
        description="Quality, latency and cost regression results for model releases."
        actions={
          <Button size="sm" variant="outline" onClick={loadRuns} disabled={loading} className="gap-2">
            <FlaskConical className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh
          </Button>
        }
      >
        <AdminFilters
          filterGroups={[
            {
              label: "Status",
              value: statusFilter,
              options: STATUS_OPTIONS,
              onChange: (value) => {
                setStatusFilter((value as EvaluationRun["status"]) || "all");
                setPage(1);
              },
              allowClear: true,
            },
          ]}
        />
      </AdminToolbar>

      <DataTable
        columns={[
          {
            key: "name",
            header: "Evaluation",
            render: (run) => (
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">{run.name}</p>
                <p className="text-xs text-muted-foreground">Dataset: {run.dataset}</p>
              </div>
            ),
          },
          {
            key: "model",
            header: "Model",
            render: (run) => <span className="text-sm text-muted-foreground">{run.model}</span>,
          },
          {
            key: "metrics",
            header: "Metrics",
            render: (run) => (
              <div className="grid gap-1 text-xs text-muted-foreground">
                {run.metrics.accuracy !== undefined && <span>Accuracy: {(run.metrics.accuracy * 100).toFixed(1)}%</span>}
                {run.metrics.latencyMs !== undefined && <span>Latency: {run.metrics.latencyMs}ms</span>}
                {run.metrics.cost !== undefined && <span>Cost: ${run.metrics.cost.toFixed(2)}</span>}
                {run.metrics.score !== undefined && <span>Score: {(run.metrics.score * 100).toFixed(1)}%</span>}
              </div>
            ),
          },
          {
            key: "startedAt",
            header: "Started",
            render: (run) => <span className="text-xs text-muted-foreground">{new Date(run.startedAt).toLocaleString()}</span>,
          },
          {
            key: "status",
            header: "Status",
            render: (run) => (
              <Badge
                variant={
                  run.status === "completed"
                    ? "default"
                    : run.status === "failed"
                      ? "destructive"
                      : "secondary"
                }
              >
                {run.status}
              </Badge>
            ),
          },
        ]}
        data={runs}
        loading={loading}
        emptyState={<AdminEmptyState title="No evaluation runs" description="When model regressions finish they will appear here." />}
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

      {loading && runs.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>
      )}
    </div>
  );
}

export default LLMEvaluations;
