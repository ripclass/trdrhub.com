import * as React from "react";
import { useSearchParams } from "react-router-dom";

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
import { GitCommit } from "lucide-react";

import { getAdminService } from "@/lib/admin/services";
import type { ReleaseRecord } from "@/lib/admin/types";

const service = getAdminService();
const PAGE_SIZE = 10;

const nowIso = new Date().toISOString();
const FALLBACK_RELEASES: ReleaseRecord[] = [
  {
    id: "release-fallback-1",
    version: "v2.24.0",
    deployedAt: nowIso,
    environment: "production",
    author: "CI/CD",
    summary: "Deployment summary placeholder for mock data.",
    commitSha: "abc123",
    status: "succeeded",
    services: [
      { name: "web", previousVersion: "v2.23.0" },
      { name: "api", previousVersion: "v2.23.0" },
    ],
  },
  {
    id: "release-fallback-2",
    version: "v2.23.1",
    deployedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    environment: "staging",
    author: "Sarah Jenkins",
    summary: "Deployment summary placeholder for mock data.",
    commitSha: "def456",
    status: "in_progress",
    services: [{ name: "web", previousVersion: "v2.23.0" }],
  },
  {
    id: "release-fallback-3",
    version: "v2.23.0",
    deployedAt: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
    environment: "production",
    author: "DevOps Bot",
    summary: "Deployment summary placeholder for mock data.",
    commitSha: "ghi789",
    status: "failed",
    services: [{ name: "api", previousVersion: "v2.22.4" }],
  },
];

const ENVIRONMENTS = [
  { label: "All environments", value: "all" },
  { label: "Production", value: "production" },
  { label: "Staging", value: "staging" },
  { label: "Sandbox", value: "sandbox" },
];

export function SystemReleases() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [environment, setEnvironment] = React.useState<string>(searchParams.get("releasesEnv") ?? "all");
  const [page, setPage] = React.useState(() => Math.max(1, Number(searchParams.get("releasesPage") ?? "1")));
  const [releases, setReleases] = React.useState<ReleaseRecord[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const loadReleases = React.useCallback(() => {
    setLoading(true);
    service
      .listReleases({
        page,
        pageSize: PAGE_SIZE,
        environment: environment === "all" ? undefined : environment,
      })
      .then((result) => {
        setError(null);
        setReleases(result.items);
        setTotal(result.total);
      })
      .catch((error) => {
        console.error("Failed to load releases", error);
        setError("Unable to load releases. Showing cached mock data.");
        setReleases(FALLBACK_RELEASES);
        setTotal(FALLBACK_RELEASES.length);
      })
      .finally(() => setLoading(false));
  }, [page, environment]);

  const updateQuery = React.useCallback(() => {
    const next = new URLSearchParams(searchParams);
    if (page === 1) next.delete("releasesPage");
    else next.set("releasesPage", String(page));
    if (environment === "all") next.delete("releasesEnv");
    else next.set("releasesEnv", environment);
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true });
    }
  }, [page, environment, searchParams, setSearchParams]);

  React.useEffect(() => {
    updateQuery();
    loadReleases();
  }, [updateQuery, loadReleases]);

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Deployment history"
        description="Recent application releases with status and linked services."
        actions={
          <Button size="sm" variant="outline" onClick={loadReleases} disabled={loading} className="gap-2">
            <GitCommit className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh
          </Button>
        }
      >
        <AdminFilters
          filterGroups={[
            {
              label: "Environment",
              value: environment,
              options: ENVIRONMENTS,
              onChange: (value) => {
                setEnvironment((value as string) ?? "all");
                setPage(1);
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

      <DataTable
        columns={[
          {
            key: "version",
            header: "Release",
            render: (release) => (
              <div className="space-y-1">
                <p className="font-mono text-sm font-medium text-foreground">{release.version}</p>
                <p className="text-xs text-muted-foreground">Commit {release.commitSha}</p>
              </div>
            ),
          },
          {
            key: "environment",
            header: "Environment",
            render: (release) => <Badge variant="outline">{release.environment}</Badge>,
          },
          {
            key: "deployedAt",
            header: "Deployed",
            render: (release) => <span className="text-xs text-muted-foreground">{new Date(release.deployedAt).toLocaleString()}</span>,
          },
          {
            key: "status",
            header: "Status",
            render: (release) => (
              <Badge
                variant={
                  release.status === "succeeded"
                    ? "default"
                    : release.status === "failed"
                      ? "destructive"
                      : "secondary"
                }
              >
                {release.status}
              </Badge>
            ),
          },
          {
            key: "summary",
            header: "Summary",
            render: (release) => <span className="text-sm text-muted-foreground">{release.summary}</span>,
          },
        ]}
        data={releases}
        loading={loading}
        emptyState={<AdminEmptyState title="No releases" description="No deployments found for the selected filters." />}
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

      {loading && releases.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>
      )}
    </div>
  );
}

export default SystemReleases;
