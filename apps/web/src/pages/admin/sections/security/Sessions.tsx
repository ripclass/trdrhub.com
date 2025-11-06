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

const nowIso = new Date().toISOString();
const FALLBACK_SESSIONS: SessionRecord[] = [
  {
    id: "session-fallback-1",
    userId: "admin-fallback-1",
    createdAt: nowIso,
    lastSeenAt: nowIso,
    ipAddress: "172.16.0.12",
    location: "New York, USA",
    userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0)",
    device: "MacBook Pro",
    platform: "macOS",
    riskLevel: "low",
  },
  {
    id: "session-fallback-2",
    userId: "admin-fallback-2",
    createdAt: nowIso,
    lastSeenAt: nowIso,
    ipAddress: "172.16.4.54",
    location: "London, UK",
    userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    device: "Windows Desktop",
    platform: "windows",
    riskLevel: "medium",
  },
  {
    id: "session-fallback-3",
    userId: "admin-fallback-3",
    createdAt: nowIso,
    lastSeenAt: nowIso,
    ipAddress: "172.16.12.89",
    location: "Singapore",
    userAgent: "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X)",
    device: "iPad",
    platform: "ios",
    riskLevel: "high",
  },
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

export function SecuritySessions() {
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
  const [error, setError] = React.useState<string | null>(null);

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
        setError(null);
        setSessions(result.items);
        setTotal(result.total);
      })
      .catch((error) => {
        console.error("Failed to load sessions", error);
        setError("Unable to load sessions. Showing cached mock data.");
        setSessions(FALLBACK_SESSIONS);
        setTotal(FALLBACK_SESSIONS.length);
      })
      .finally(() => setLoading(false));
  }, [page, riskFilter]);

  const updateQuery = React.useCallback(() => {
    const next = new URLSearchParams(searchParams);
    if (page === 1) next.delete("sessionsPage");
    else next.set("sessionsPage", String(page));
    if (riskFilter === "all") next.delete("sessionsRisk");
    else next.set("sessionsRisk", riskFilter);
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true });
    }
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

      {error && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-700">
          {error}
        </div>
      )}

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

export default SecuritySessions;
