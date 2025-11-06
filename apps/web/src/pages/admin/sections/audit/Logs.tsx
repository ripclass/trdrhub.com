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
import { Download, RefreshCw } from "lucide-react";

import { getAdminService } from "@/lib/admin/services";
import type { AuditLogEntry } from "@/lib/admin/types";
import { generateCSV } from "@/lib/csv";

const service = getAdminService();
const PAGE_SIZE = 12;

function formatRelativeTime(iso: string) {
  const diffMs = Date.now() - new Date(iso).getTime();
  if (diffMs < 60_000) return "just now";
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

export default function AuditLogs() {
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const [page, setPage] = React.useState(() => Math.max(1, Number(searchParams.get("auditPage") ?? "1")));
  const [searchTerm, setSearchTerm] = React.useState(searchParams.get("auditSearch") ?? "");
  const [actorFilter, setActorFilter] = React.useState(searchParams.get("auditActor") ?? "all");
  const [actionFilter, setActionFilter] = React.useState(searchParams.get("auditAction") ?? "all");

  const [logs, setLogs] = React.useState<AuditLogEntry[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [availableActors, setAvailableActors] = React.useState<string[]>([]);
  const [availableActions, setAvailableActions] = React.useState<string[]>([]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const updateQuery = React.useCallback(
    (updates: Record<string, string | null>) => {
      const next = new URLSearchParams(searchParams);
      Object.entries(updates).forEach(([key, value]) => {
        if (!value) next.delete(key);
        else next.set(key, value);
      });
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const loadLogs = React.useCallback(() => {
    setLoading(true);
    service
      .listAuditLogs({
        page,
        pageSize: PAGE_SIZE,
        search: searchTerm || undefined,
        actor: actorFilter !== "all" ? actorFilter : undefined,
        action: actionFilter !== "all" ? actionFilter : undefined,
      })
      .then((result) => {
        setLogs(result.items);
        setTotal(result.total);
        setAvailableActors((prev) => {
          const actors = Array.from(new Set(result.items.map((item) => item.actor.email)));
          return actors.length ? actors : prev;
        });
        setAvailableActions((prev) => {
          const actions = Array.from(new Set(result.items.map((item) => item.action)));
          return actions.length ? actions : prev;
        });
      })
      .finally(() => setLoading(false));
  }, [page, searchTerm, actorFilter, actionFilter]);

  React.useEffect(() => {
    updateQuery({
      auditPage: page === 1 ? null : String(page),
      auditSearch: searchTerm || null,
      auditActor: actorFilter !== "all" ? actorFilter : null,
      auditAction: actionFilter !== "all" ? actionFilter : null,
    });
    loadLogs();
  }, [page, searchTerm, actorFilter, actionFilter, loadLogs, updateQuery]);

  const handleExport = () => {
    if (!logs.length) {
      toast({ title: "Nothing to export", description: "Adjust filters to load audit entries first." });
      return;
    }
    const rows = [
      ["Timestamp", "Actor", "Email", "Action", "Entity", "Entity ID", "Summary", "IP", "User Agent"],
      ...logs.map((log) => [
        new Date(log.createdAt).toISOString(),
        log.actor.name,
        log.actor.email,
        log.action,
        log.entity,
        log.entityId,
        log.summary,
        log.ip ?? "",
        log.userAgent ?? "",
      ]),
    ];
    const blob = new Blob([generateCSV(rows)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `audit-log-${Date.now()}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
    toast({ title: "Export ready", description: "Current view downloaded as CSV." });
  };

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Audit log"
        description="Immutable record of privileged actions across LCopilot."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadLogs} disabled={loading} className="gap-2">
              <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={handleExport} className="gap-2">
              <Download className="h-4 w-4" /> Export CSV
            </Button>
          </div>
        }
      >
        <AdminFilters
          searchPlaceholder="Search actions, emails or entities"
          searchValue={searchTerm}
          onSearchChange={(value) => {
            setSearchTerm(value);
            setPage(1);
          }}
          filterGroups={[
            {
              label: "Actor",
              value: actorFilter,
              options: ["all", ...availableActors].map((email) => ({ label: email === "all" ? "All actors" : email, value: email })),
              onChange: (value) => {
                setActorFilter(String(value || "all"));
                setPage(1);
              },
              allowClear: true,
            },
            {
              label: "Action",
              value: actionFilter,
              options: ["all", ...availableActions].map((action) => ({ label: action === "all" ? "All actions" : action, value: action })),
              onChange: (value) => {
                setActionFilter(String(value || "all"));
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
            key: "actor",
            header: "Actor",
            render: (log) => (
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">{log.actor.name}</p>
                <p className="text-xs text-muted-foreground">{log.actor.email}</p>
              </div>
            ),
          },
          {
            key: "action",
            header: "Action",
            render: (log) => <span className="text-sm text-foreground">{log.action}</span>,
          },
          {
            key: "entity",
            header: "Entity",
            render: (log) => (
              <div className="space-y-1 text-xs text-muted-foreground">
                <p>{log.entity}</p>
                <p>#{log.entityId}</p>
              </div>
            ),
          },
          {
            key: "summary",
            header: "Summary",
            render: (log) => <span className="text-sm text-muted-foreground">{log.summary}</span>,
          },
          {
            key: "createdAt",
            header: "When",
            render: (log) => <span className="text-sm text-muted-foreground">{formatRelativeTime(log.createdAt)}</span>,
          },
          {
            key: "metadata",
            header: "Session",
            render: (log) => (
              <div className="space-y-1 text-xs text-muted-foreground">
                {log.ip && <p>IP: {log.ip}</p>}
                {log.userAgent && <p className="max-w-[220px] truncate">UA: {log.userAgent}</p>}
              </div>
            ),
          },
        ]}
        data={logs}
        loading={loading}
        emptyState={<AdminEmptyState title="No audit entries" description="Try widening your search or time window." />}
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

      {loading && logs.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>
      )}
    </div>
  );
}
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Search, Download, Filter } from 'lucide-react';

const mockLogs = [
  { id: 'log-001', user: 'admin@lcopilot.com', action: 'User Login', resource: 'Auth', status: 'success', time: '2 min ago' },
  { id: 'log-002', user: 'ops@lcopilot.com', action: 'Service Restart', resource: 'API Gateway', status: 'success', time: '15 min ago' },
  { id: 'log-003', user: 'security@lcopilot.com', action: 'Access Key Revoked', resource: 'API Key #1234', status: 'success', time: '1 hour ago' },
  { id: 'log-004', user: 'finance@lcopilot.com', action: 'Plan Changed', resource: 'Company ABC', status: 'success', time: '2 hours ago' },
];

export function AuditLogs() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Audit Logs</h2>
        <p className="text-muted-foreground">
          Complete audit trail of all administrative actions and system events
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="w-5 h-5" />
            Audit Trail
          </CardTitle>
          <CardDescription>Filter and search audit logs</CardDescription>
          <div className="flex gap-2 mt-4">
            <Input placeholder="Search logs..." className="max-w-sm" />
            <Button variant="outline" size="sm">
              <Filter className="w-4 h-4 mr-2" />
              Filter
            </Button>
            <Button variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {mockLogs.map((log) => (
              <div key={log.id} className="flex items-center justify-between p-3 border rounded-lg text-sm">
                <div className="flex items-center gap-4">
                  <Badge variant={log.status === 'success' ? 'default' : 'destructive'}>
                    {log.status}
                  </Badge>
                  <span className="text-muted-foreground">{log.user}</span>
                  <span className="font-medium text-foreground">{log.action}</span>
                  <span className="text-muted-foreground">→ {log.resource}</span>
                </div>
                <span className="text-xs text-muted-foreground">{log.time}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

