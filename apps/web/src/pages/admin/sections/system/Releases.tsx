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

const ENVIRONMENTS = [
  { label: "All environments", value: "all" },
  { label: "Production", value: "production" },
  { label: "Staging", value: "staging" },
  { label: "Sandbox", value: "sandbox" },
];

export default function Releases() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [environment, setEnvironment] = React.useState<string>(searchParams.get("releasesEnv") ?? "all");
  const [page, setPage] = React.useState(() => Math.max(1, Number(searchParams.get("releasesPage") ?? "1")));
  const [releases, setReleases] = React.useState<ReleaseRecord[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);

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
        setReleases(result.items);
        setTotal(result.total);
      })
      .finally(() => setLoading(false));
  }, [page, environment]);

  const updateQuery = React.useCallback(() => {
    const next = new URLSearchParams(searchParams);
    if (page === 1) next.delete("releasesPage");
    else next.set("releasesPage", String(page));
    if (environment === "all") next.delete("releasesEnv");
    else next.set("releasesEnv", environment);
    setSearchParams(next, { replace: true });
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { FileText } from 'lucide-react';

const mockReleases = [
  { version: 'v2.5.0', date: '2 days ago', type: 'major', changes: ['New dashboard layout', 'Advanced analytics', '5 bug fixes'], status: 'deployed' },
  { version: 'v2.4.3', date: '1 week ago', type: 'patch', changes: ['Security updates', 'Performance improvements'], status: 'deployed' },
  { version: 'v2.4.2', date: '2 weeks ago', type: 'patch', changes: ['Bug fixes', 'UI tweaks'], status: 'deployed' },
];

export function SystemReleases() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">System Releases</h2>
        <p className="text-muted-foreground">
          Track platform releases and deployment history
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Release History
          </CardTitle>
          <CardDescription>Recent platform updates and deployments</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {mockReleases.map((release) => (
              <div key={release.version} className="p-4 border rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <p className="font-mono font-semibold text-foreground">{release.version}</p>
                    <Badge variant={release.type === 'major' ? 'default' : 'outline'}>
                      {release.type}
                    </Badge>
                    <Badge variant="secondary">{release.status}</Badge>
                  </div>
                  <span className="text-sm text-muted-foreground">{release.date}</span>
                </div>
                <ul className="space-y-1">
                  {release.changes.map((change, idx) => (
                    <li key={idx} className="text-sm text-muted-foreground flex items-center gap-2">
                      <span className="text-primary">•</span> {change}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

