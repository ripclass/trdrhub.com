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
import { Globe, Monitor, ShieldAlert } from "lucide-react";

import { getAdminService } from "@/lib/admin/services";
import type { SessionRecord } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();
const PAGE_SIZE = 12;

const RISK_OPTIONS = [
  { label: "All risk levels", value: "all" },
  { label: "Low", value: "low" },
  { label: "Medium", value: "medium" },
  { label: "High", value: "high" },
];

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

export default function Sessions() {
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const audit = useAdminAudit("security-sessions");
  const [page, setPage] = React.useState(() => Math.max(1, Number(searchParams.get("sessionsPage") ?? "1")));
  const [riskFilter, setRiskFilter] = React.useState<SessionRecord["riskLevel"] | "all">(
    (searchParams.get("sessionsRisk") as SessionRecord["riskLevel"]) ?? "all",
  );

  const [sessions, setSessions] = React.useState<SessionRecord[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [actionId, setActionId] = React.useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const loadSessions = React.useCallback(() => {
    setLoading(true);
    service
      .listSessions({
        page,
        pageSize: PAGE_SIZE,
        risk: riskFilter === "all" ? undefined : riskFilter,
      })
      .then((result) => {
        setSessions(result.items);
        setTotal(result.total);
      })
      .finally(() => setLoading(false));
  }, [page, riskFilter]);

  const updateQuery = React.useCallback(() => {
    const next = new URLSearchParams(searchParams);
    if (page === 1) next.delete("sessionsPage");
    else next.set("sessionsPage", String(page));
    if (riskFilter === "all") next.delete("sessionsRisk");
    else next.set("sessionsRisk", riskFilter);
    setSearchParams(next, { replace: true });
  }, [page, riskFilter, searchParams, setSearchParams]);

  React.useEffect(() => {
    updateQuery();
    loadSessions();
  }, [updateQuery, loadSessions]);

  const revoke = async (id: string) => {
    setActionId(id);
    const result = await service.revokeSession(id);
    setActionId(null);
    toast({
      title: result.success ? "Session revoked" : "Revoke failed",
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      await audit("revoke_session", { entityId: id });
      loadSessions();
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Session security"
        description="Terminate stale sessions and monitor suspicious access across the platform."
      >
        <AdminFilters
          filterGroups={[
            {
              label: "Risk",
              value: riskFilter,
              options: RISK_OPTIONS,
              onChange: (value) => {
                setRiskFilter((value as SessionRecord["riskLevel"]) || "all");
                setPage(1);
              },
              allowClear: true,
            },
          ]}
          endAdornment={
            <Button size="sm" variant="outline" onClick={loadSessions} disabled={loading} className="gap-2">
              <ShieldAlert className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh
            </Button>
          }
        />
      </AdminToolbar>

      <DataTable
        columns={[
          {
            key: "userId",
            header: "User",
            render: (session) => (
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">{session.userId}</p>
                <p className="text-xs text-muted-foreground">Session {session.id}</p>
              </div>
            ),
          },
          {
            key: "device",
            header: "Device",
            render: (session) => (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Monitor className="h-3.5 w-3.5" />
                <span>{session.device} • {session.platform}</span>
              </div>
            ),
          },
          {
            key: "location",
            header: "Location",
            render: (session) => (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Globe className="h-3.5 w-3.5" />
                <span>{session.location ?? "Unknown"}</span>
              </div>
            ),
          },
          {
            key: "createdAt",
            header: "Started",
            render: (session) => <span className="text-xs text-muted-foreground">{formatRelativeTime(session.createdAt)}</span>,
          },
          {
            key: "lastSeenAt",
            header: "Last seen",
            render: (session) => <span className="text-xs text-muted-foreground">{formatRelativeTime(session.lastSeenAt)}</span>,
          },
          {
            key: "riskLevel",
            header: "Risk",
            render: (session) => (
              <Badge
                variant={
                  session.riskLevel === "high"
                    ? "destructive"
                    : session.riskLevel === "medium"
                      ? "secondary"
                      : "outline"
                }
              >
                {session.riskLevel}
              </Badge>
            ),
          },
          {
            key: "actions",
            header: "Actions",
            align: "right",
            render: (session) => (
              <Button
                variant="outline"
                size="sm"
                className="gap-1 text-rose-600"
                onClick={() => revoke(session.id)}
                disabled={actionId === session.id}
              >
                Terminate
              </Button>
            ),
          },
        ]}
        data={sessions}
        loading={loading}
        emptyState={<AdminEmptyState title="No active sessions" description="All sessions cleared or filtered out." />}
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

      {loading && sessions.length === 0 && (
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
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Clock, X } from 'lucide-react';

const mockSessions = [
  { id: 'sess-001', user: 'admin@lcopilot.com', device: 'Chrome on Windows', location: 'New York, US', started: '2 hours ago', lastActive: '2 min ago', status: 'active' },
  { id: 'sess-002', user: 'ops@lcopilot.com', device: 'Firefox on macOS', location: 'San Francisco, US', started: '5 hours ago', lastActive: '30 min ago', status: 'active' },
  { id: 'sess-003', user: 'security@lcopilot.com', device: 'Safari on iOS', location: 'London, UK', started: '1 day ago', lastActive: '2 hours ago', status: 'active' },
];

export function SecuritySessions() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Active Sessions</h2>
        <p className="text-muted-foreground">
          Monitor and manage active user sessions across the platform
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5" />
            Session Management
          </CardTitle>
          <CardDescription>Currently active user sessions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockSessions.map((session) => (
              <div key={session.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{session.user}</p>
                  <p className="text-sm text-muted-foreground mb-2">{session.device} • {session.location}</p>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span>Started: {session.started}</span>
                    <span>•</span>
                    <span>Last active: {session.lastActive}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="default">{session.status}</Badge>
                  <Button variant="outline" size="sm" className="text-destructive">
                    <X className="w-4 h-4 mr-2" />
                    Revoke
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

