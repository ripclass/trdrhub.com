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
import { AlarmClock, Bell, CheckCircle, Snooze } from "lucide-react";

import { getAdminService } from "@/lib/admin/services";
import type { OpsAlert } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();
const PAGE_SIZE = 8;

const SEVERITY_OPTIONS = [
  { label: "Critical", value: "critical" },
  { label: "High", value: "high" },
  { label: "Medium", value: "medium" },
  { label: "Low", value: "low" },
  { label: "Info", value: "info" },
];

const STATUS_OPTIONS = [
  { label: "Active", value: "active" },
  { label: "Acknowledged", value: "acknowledged" },
  { label: "Resolved", value: "resolved" },
];

function getAlertStatus(alert: OpsAlert): "active" | "acknowledged" | "resolved" {
  if (alert.resolvedAt) return "resolved";
  if (alert.acknowledgedAt) return "acknowledged";
  return "active";
}

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

export default function Alerts() {
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const audit = useAdminAudit("ops-alerts");
  const [page, setPage] = React.useState(() => Math.max(1, Number(searchParams.get("alertsPage") ?? "1")));
  const [severityFilter, setSeverityFilter] = React.useState<string[]>(() => {
    const raw = searchParams.get("alertsSeverity");
    return raw ? raw.split(",").filter(Boolean) : [];
  });
  const [statusFilter, setStatusFilter] = React.useState<string>(searchParams.get("alertsStatus") ?? "active");

  const [alerts, setAlerts] = React.useState<OpsAlert[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [actionId, setActionId] = React.useState<string | null>(null);

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

  const loadAlerts = React.useCallback(() => {
    setLoading(true);
    service
      .listAlerts({
        page,
        pageSize: PAGE_SIZE,
        severity: severityFilter.length ? (severityFilter as OpsAlert["severity"][]) : undefined,
        status: statusFilter as "active" | "acknowledged" | "resolved" | undefined,
      })
      .then((result) => {
        setAlerts(result.items);
        setTotal(result.total);
      })
      .finally(() => setLoading(false));
  }, [page, severityFilter, statusFilter]);

  React.useEffect(() => {
    updateQuery({
      alertsPage: page === 1 ? null : String(page),
      alertsSeverity: severityFilter.length ? severityFilter.join(",") : null,
      alertsStatus: statusFilter === "active" ? null : statusFilter,
    });
    loadAlerts();
  }, [page, severityFilter, statusFilter, loadAlerts, updateQuery]);

  const acknowledge = async (id: string) => {
    setActionId(id);
    const result = await service.acknowledgeAlert(id);
    setActionId(null);
    toast({
      title: result.success ? "Alert acknowledged" : "Unable to acknowledge",
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      await audit("ack_alert", { entityId: id });
      loadAlerts();
    }
  };

  const snooze = async (id: string) => {
    setActionId(id);
    const result = await service.snoozeAlert(id, 30);
    setActionId(null);
    toast({
      title: result.success ? "Alert snoozed" : "Unable to snooze",
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      await audit("snooze_alert", { entityId: id, metadata: { minutes: 30 } });
      loadAlerts();
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Operational alerts"
        description="Centralized view of actionable incidents triggerd by LCopilot watchdogs."
        actions={
          <Button size="sm" variant="outline" onClick={loadAlerts} disabled={loading} className="gap-2">
            <Bell className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
            Refresh
          </Button>
        }
      >
        <AdminFilters
          filterGroups={[
            {
              label: "Severity",
              value: severityFilter,
              options: SEVERITY_OPTIONS,
              multi: true,
              onChange: (value) => {
                const next = Array.isArray(value) ? value : value ? [value] : [];
                setSeverityFilter(next);
                setPage(1);
              },
            },
            {
              label: "Status",
              value: statusFilter,
              options: STATUS_OPTIONS,
              onChange: (value) => {
                setStatusFilter(String(value || "active"));
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
            key: "title",
            header: "Alert",
            render: (alert) => (
              <div className="space-y-1">
                <p className="font-medium text-foreground">{alert.title}</p>
                <p className="text-xs text-muted-foreground">{alert.description}</p>
                {alert.tags && alert.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {alert.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-[10px]">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            ),
          },
          {
            key: "severity",
            header: "Severity",
            render: (alert) => {
              const variant =
                alert.severity === "critical"
                  ? "destructive"
                  : alert.severity === "high"
                    ? "default"
                    : alert.severity === "medium"
                      ? "secondary"
                      : "outline";
              return <Badge variant={variant}>{alert.severity}</Badge>;
            },
          },
          {
            key: "createdAt",
            header: "Raised",
            render: (alert) => <span className="text-sm text-muted-foreground">{formatRelativeTime(alert.createdAt)}</span>,
          },
          {
            key: "source",
            header: "Source",
            render: (alert) => <span className="text-sm text-muted-foreground">{alert.source}</span>,
          },
          {
            key: "status",
            header: "Status",
            render: (alert) => {
              const status = getAlertStatus(alert);
              const variant = status === "resolved" ? "outline" : status === "acknowledged" ? "secondary" : "default";
              return <Badge variant={variant}>{status}</Badge>;
            },
          },
          {
            key: "actions",
            header: "Actions",
            align: "right",
            render: (alert) => {
              const status = getAlertStatus(alert);
              return (
                <div className="flex items-center justify-end gap-2">
                  {status === "active" && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1"
                      onClick={() => acknowledge(alert.id)}
                      disabled={actionId === alert.id}
                    >
                      <CheckCircle className="h-4 w-4" /> Ack
                    </Button>
                  )}
                  {status === "active" && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1"
                      onClick={() => snooze(alert.id)}
                      disabled={actionId === alert.id}
                    >
                      <Snooze className="h-4 w-4" /> Snooze
                    </Button>
                  )}
                  {status !== "active" && alert.acknowledgedAt && (
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <AlarmClock className="h-3.5 w-3.5" />
                      {status === "acknowledged" ? "Awaiting resolution" : "Resolved"}
                    </span>
                  )}
                </div>
              );
            },
          },
        ]}
        data={alerts}
        loading={loading}
        emptyState={<AdminEmptyState title="No alerts" description="Everything looks stable in this timeframe." />}
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

      {loading && alerts.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full" />
          ))}
        </div>
      )}
    </div>
  );
}
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

const mockAlerts = [
  { id: 'alert-001', title: 'High CPU Usage', severity: 'warning', message: 'API Gateway CPU at 85%', time: '5 min ago', status: 'active' },
  { id: 'alert-002', title: 'Failed Jobs', severity: 'critical', message: '3 jobs failed in last hour', time: '12 min ago', status: 'active' },
];

export function OpsAlerts() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">System Alerts</h2>
        <p className="text-muted-foreground">
          Active alerts and system notifications requiring attention
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            Active Alerts
          </CardTitle>
          <CardDescription>2 alerts requiring attention</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockAlerts.map((alert) => (
              <div key={alert.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  {alert.severity === 'critical' ? (
                    <XCircle className="w-5 h-5 text-destructive" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-warning" />
                  )}
                  <div>
                    <p className="font-medium text-foreground">{alert.title}</p>
                    <p className="text-sm text-muted-foreground">{alert.message}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground">{alert.time}</span>
                  <Badge variant={alert.severity === 'critical' ? 'destructive' : 'secondary'}>
                    {alert.severity}
                  </Badge>
                  <Button variant="outline" size="sm">
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Acknowledge
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

