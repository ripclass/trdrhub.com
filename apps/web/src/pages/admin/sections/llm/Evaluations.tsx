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

export default function Evaluations() {
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TestTube } from 'lucide-react';

const mockEvals = [
  { id: 'eval-001', name: 'Document Analysis Quality', model: 'GPT-4', score: 94.2, date: '2 days ago', status: 'passed' },
  { id: 'eval-002', name: 'Risk Detection Accuracy', model: 'Claude', score: 91.8, date: '5 days ago', status: 'passed' },
  { id: 'eval-003', name: 'Response Latency', model: 'GPT-3.5', score: 78.5, date: '1 week ago', status: 'review' },
];

export function LLMEvaluations() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">LLM Evaluations</h2>
        <p className="text-muted-foreground">
          Performance and quality metrics for AI models
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TestTube className="w-5 h-5" />
            Evaluation Results
          </CardTitle>
          <CardDescription>Recent model performance evaluations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockEvals.map((eval_) => (
              <div key={eval_.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{eval_.name}</p>
                  <p className="text-sm text-muted-foreground">{eval_.model} • {eval_.date}</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-2xl font-bold text-foreground">{eval_.score}</p>
                    <p className="text-xs text-muted-foreground">score</p>
                  </div>
                  <Badge variant={eval_.status === 'passed' ? 'default' : 'secondary'}>
                    {eval_.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

