import * as React from "react";
import { useSearchParams } from "react-router-dom";

import { AdminFilters, AdminToolbar, DataTable, AdminEmptyState } from "@/components/admin/ui";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { RefreshCw, RotateCcw, StopCircle } from "lucide-react";

import { getAdminService } from "@/lib/admin/services";
import type { JobStatus, OpsJob } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();
const PAGE_SIZE = 10;

const JOB_STATUS_OPTIONS: { label: string; value: JobStatus }[] = [
  { label: "Queued", value: "queued" },
  { label: "Running", value: "running" },
  { label: "Succeeded", value: "succeeded" },
  { label: "Failed", value: "failed" },
  { label: "Cancelled", value: "cancelled" },
  { label: "Scheduled", value: "scheduled" },
];

function formatDuration(job: OpsJob) {
  if (job.durationMs) {
    if (job.durationMs < 1000) return `${job.durationMs}ms`;
    return `${(job.durationMs / 1000).toFixed(1)}s`;
  }
  if (job.startedAt && job.status === "running") {
    const diff = Date.now() - new Date(job.startedAt).getTime();
    return diff < 1000 ? `${diff}ms` : `${(diff / 1000).toFixed(1)}s`;
  }
  return "-";
}

function formatRelativeTime(iso: string | undefined) {
  if (!iso) return "-";
  const diffMs = Date.now() - new Date(iso).getTime();
  if (diffMs < 60_000) return "just now";
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

export default function Jobs() {
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const audit = useAdminAudit("ops-jobs");

  const [page, setPage] = React.useState(() => Math.max(1, Number(searchParams.get("jobsPage") ?? "1")));
  const [searchTerm, setSearchTerm] = React.useState(searchParams.get("jobsSearch") ?? "");
  const [statusFilter, setStatusFilter] = React.useState<string[]>(() => {
    const raw = searchParams.get("jobsStatus");
    return raw ? raw.split(",").filter(Boolean) : [];
  });

  const [jobs, setJobs] = React.useState<OpsJob[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [actionJobId, setActionJobId] = React.useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const updateQuery = React.useCallback(
    (updates: Record<string, string | null>) => {
      const next = new URLSearchParams(searchParams);
      Object.entries(updates).forEach(([key, value]) => {
        if (value === null || value === "") next.delete(key);
        else next.set(key, value);
      });
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const loadJobs = React.useCallback(() => {
    setLoading(true);
    const status = statusFilter.filter(Boolean) as JobStatus[];
    service
      .listJobs({
        page,
        pageSize: PAGE_SIZE,
        status: status.length ? status : undefined,
        search: searchTerm || undefined,
      })
      .then((result) => {
        setJobs(result.items);
        setTotal(result.total);
      })
      .finally(() => setLoading(false));
  }, [page, searchTerm, statusFilter]);

  React.useEffect(() => {
    updateQuery({
      jobsPage: page === 1 ? null : String(page),
      jobsSearch: searchTerm || null,
      jobsStatus: statusFilter.length ? statusFilter.join(",") : null,
    });
    loadJobs();
  }, [page, searchTerm, statusFilter, loadJobs, updateQuery]);

  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    setPage(1);
  };

  const handleStatusChange = (value: string | string[]) => {
    const values = Array.isArray(value) ? value : value ? [value] : [];
    setStatusFilter(values);
    setPage(1);
  };

  const handleRetry = async (jobId: string) => {
    setActionJobId(jobId);
    const result = await service.retryJob(jobId);
    setActionJobId(null);
    toast({
      title: result.success ? "Job re-queued" : "Retry failed",
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      await audit("retry_job", { entityId: jobId });
      loadJobs();
    }
  };

  const handleCancel = async (jobId: string) => {
    setActionJobId(jobId);
    const result = await service.cancelJob(jobId);
    setActionJobId(null);
    toast({
      title: result.success ? "Job cancelled" : "Cancel failed",
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      await audit("cancel_job", { entityId: jobId });
      loadJobs();
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Job orchestration"
        description="Inspect, retry or cancel background workflows powering LCopilot."
        actions={
          <Button variant="outline" size="sm" onClick={loadJobs} disabled={loading} className="gap-2">
            <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
            Refresh
          </Button>
        }
      >
        <AdminFilters
          searchPlaceholder="Search jobs by id or name"
          searchValue={searchTerm}
          onSearchChange={handleSearchChange}
          filterGroups={[
            {
              label: "Status",
              value: statusFilter,
              options: JOB_STATUS_OPTIONS,
              multi: true,
              onChange: handleStatusChange,
            },
          ]}
        />
      </AdminToolbar>

      <DataTable
        columns={[
          {
            key: "name",
            header: "Job",
            render: (job) => (
              <div className="space-y-1">
                <p className="font-medium text-foreground">{job.name}</p>
                <p className="text-xs text-muted-foreground">#{job.id}</p>
              </div>
            ),
          },
          {
            key: "queue",
            header: "Queue",
            render: (job) => <Badge variant="outline">{job.queue}</Badge>,
          },
          {
            key: "status",
            header: "Status",
            render: (job) => {
              const variant =
                job.status === "succeeded"
                  ? "outline"
                  : job.status === "failed"
                    ? "destructive"
                    : job.status === "running"
                      ? "secondary"
                      : "default";
              return <Badge variant={variant}>{job.status}</Badge>;
            },
          },
          {
            key: "retries",
            header: "Retries",
            render: (job) => (
              <span className="text-sm text-muted-foreground">{job.retries}/{job.maxRetries}</span>
            ),
          },
          {
            key: "duration",
            header: "Duration",
            render: (job) => <span className="text-sm text-muted-foreground">{formatDuration(job)}</span>,
          },
          {
            key: "createdAt",
            header: "Created",
            render: (job) => <span className="text-sm text-muted-foreground">{formatRelativeTime(job.createdAt)}</span>,
          },
          {
            key: "actions",
            header: "Actions",
            align: "right",
            render: (job) => (
              <div className="flex items-center justify-end gap-2">
                {job.status === "failed" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleRetry(job.id)}
                    disabled={actionJobId === job.id}
                    className="gap-1"
                  >
                    <RotateCcw className="h-4 w-4" /> Retry
                  </Button>
                )}
                {job.status === "queued" && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleCancel(job.id)}
                    disabled={actionJobId === job.id}
                    className="gap-1"
                  >
                    <StopCircle className="h-4 w-4" /> Cancel
                  </Button>
                )}
              </div>
            ),
          },
        ]}
        data={jobs}
        loading={loading}
        emptyState={<AdminEmptyState title="No jobs found" description="Adjust filters to see more runs." />}
        footer={
          total > PAGE_SIZE && (
            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    onClick={(event) => {
                      event.preventDefault();
                      if (page > 1) setPage(page - 1);
                    }}
                    className={page === 1 ? "pointer-events-none opacity-50" : undefined}
                    href="#"
                  />
                </PaginationItem>
                <PaginationItem>
                  <span className="text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </span>
                </PaginationItem>
                <PaginationItem>
                  <PaginationNext
                    onClick={(event) => {
                      event.preventDefault();
                      if (page < totalPages) setPage(page + 1);
                    }}
                    className={page >= totalPages ? "pointer-events-none opacity-50" : undefined}
                    href="#"
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          )
        }
      />

      {loading && jobs.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full" />
          ))}
        </div>
      )}
    </div>
  );
}

