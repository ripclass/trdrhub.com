import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { KpiCard } from "@/components/analytics/KpiCard";
import { DateRangePicker } from "@/components/analytics/DateRangePicker";
import { ExportButtons } from "@/components/analytics/ExportButtons";
import { ChartLine } from "@/components/analytics/charts/ChartLine";
import { ChartBar } from "@/components/analytics/charts/ChartBar";
import { ChartArea } from "@/components/analytics/charts/ChartArea";
import { NoDataState } from "@/components/analytics/EmptyState";
import { ErrorState } from "@/components/analytics/ErrorState";
import { RoleBadge } from "@/components/analytics/RoleBadge";
import { analyticsApi } from "@/api/analytics";
import { useAuth } from "@/hooks/use-auth";
import type { AnalyticsFilters, AnalyticsDashboard } from "@/types/analytics";
import { subDays } from "date-fns";
import { TrendingUp, AlertTriangle, Users, FileText, Clock } from "lucide-react";

// Inline cn function to avoid import/bundling issues
function cn(...classes: (string | undefined | null | boolean | Record<string, boolean>)[]): string {
  return classes
    .filter(Boolean)
    .map((cls) => {
      if (typeof cls === 'string') return cls;
      if (typeof cls === 'object' && cls !== null) {
        return Object.entries(cls)
          .filter(([_, val]) => val)
          .map(([key]) => key)
          .join(' ');
      }
      return '';
    })
    .filter(Boolean)
    .join(' ');
}

export function BankAnalytics() {
  const { user } = useAuth();
  const isBank = !!user && user.role === "bank";
  const [filters, setFilters] = React.useState<AnalyticsFilters>({
    timeRange: "30d",
    startDate: subDays(new Date(), 30),
    endDate: new Date(),
  });

  // When not a bank user, show a public demo (no API calls)
  const demoDashboard: AnalyticsDashboard = {
    summary: {
      total_jobs: 12540,
      rejection_rate: 8.7,
      avg_processing_time_minutes: 12.4,
      doc_distribution: { lc: 7420, invoice: 3200, bl: 1920 },
    },
    trends: {
      job_volume_trend: 4.6,
      success_rate_trend: 1.8,
      processing_time_trend: -0.9,
      daily_volumes: Array.from({ length: 14 }).map((_, i) => ({
        date: subDays(new Date(), 13 - i).toISOString().slice(0, 10),
        count: 700 + Math.round(Math.sin(i / 2) * 80),
      })),
      success_rates: Array.from({ length: 14 }).map((_, i) => ({
        date: subDays(new Date(), 13 - i).toISOString().slice(0, 10),
        success_rate: 91 + Math.sin(i / 3) * 3,
        rejection_rate: 9 - Math.sin(i / 3) * 3,
      })),
      processing_times: Array.from({ length: 14 }).map((_, i) => ({
        date: subDays(new Date(), 13 - i).toISOString().slice(0, 10),
        avg_time: 12 + Math.cos(i / 4),
      })),
      daily_discrepancies: Array.from({ length: 14 }).map((_, i) => ({
        date: subDays(new Date(), 13 - i).toISOString().slice(0, 10),
        count: 60 + Math.round(Math.cos(i / 2) * 20),
      })),
    },
    users: Array.from({ length: 12 }).map((_, i) => ({
      user_id: `u${i + 1}`,
      username: `Client ${i + 1}`,
      email: undefined as unknown as string,
      role: "exporter",
      job_count: 100 - i * 5,
      success_rate: 80 + (i % 4) * 5,
    })),
    discrepancies: {
      total_discrepancies: 260,
      by_type: [
        { discrepancy_type: "late_shipment", count: 75 },
        { discrepancy_type: "amount_mismatch", count: 58 },
        { discrepancy_type: "missing_docs", count: 42 },
        { discrepancy_type: "expiry_issue", count: 28 },
      ],
      by_severity: [
        { severity: "high", count: 65 },
        { severity: "medium", count: 110 },
        { severity: "low", count: 85 },
      ],
    },
  } as unknown as AnalyticsDashboard;

  const query = useQuery({
    queryKey: ['analytics-dashboard', filters],
    queryFn: () => analyticsApi.getDashboard({
      time_range: filters.timeRange,
      start_date: filters.timeRange === "custom" ? filters.startDate?.toISOString() : undefined,
      end_date: filters.timeRange === "custom" ? filters.endDate?.toISOString() : undefined,
    }),
    staleTime: 5 * 60 * 1000,
    retry: 2,
    enabled: isBank,
  });

  const dashboard = (isBank ? query.data : demoDashboard) as AnalyticsDashboard | undefined;
  const isLoading = isBank ? query.isLoading : false;
  const error = isBank ? query.error : undefined;
  const refetch = query.refetch;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h2 className="text-2xl font-semibold tracking-tight">Bank Analytics</h2>
            <p className="text-sm text-muted-foreground">Loading...</p>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} dense>
              <CardHeader dense>
                <div className="h-4 w-24 bg-muted animate-pulse rounded" />
              </CardHeader>
              <CardContent dense>
                <div className="h-8 w-32 bg-muted animate-pulse rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} onRetry={refetch} />;
  }

  if (!dashboard) {
    return <NoDataState />;
  }

  const jobTrend = Number((dashboard as any)?.trends?.job_volume_trend ?? 0);
  const successTrend = Number((dashboard as any)?.trends?.success_rate_trend ?? 0);
  const processingTrend = Number((dashboard as any)?.trends?.processing_time_trend ?? 0);
  const rejectionTrend = -successTrend;
  const avgProcessingMinutes = dashboard.summary.avg_processing_time_minutes ?? 0;

  return (
    <div className="space-y-6">
      {/* Header with Date Range Picker */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-2xl font-semibold tracking-tight">Bank Analytics</h2>
          <p className="text-sm text-muted-foreground">
            Comprehensive validation metrics and insights
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DateRangePicker value={filters} onChange={setFilters} />
          <ExportButtons
            data={dashboard}
            filename={`bank-analytics-${filters.timeRange}`}
            disabled={!dashboard}
          />
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Total Validations"
          value={dashboard.summary.total_jobs.toLocaleString()}
          icon={<FileText className="h-4 w-4" />}
          change={Math.abs(jobTrend)}
          changeType={jobTrend === 0 ? undefined : jobTrend > 0 ? "increase" : "decrease"}
          description="Total LC validations processed"
        />
        <KpiCard
          title="Success Rate"
          value={`${(100 - dashboard.summary.rejection_rate).toFixed(1)}%`}
          icon={<TrendingUp className="h-4 w-4" />}
          change={Math.abs(successTrend)}
          changeType={successTrend === 0 ? undefined : successTrend > 0 ? "increase" : "decrease"}
          description="Percentage of validations passed"
        />
        <KpiCard
          title="Rejection Rate"
          value={`${dashboard.summary.rejection_rate.toFixed(1)}%`}
          icon={<AlertTriangle className="h-4 w-4" />}
          change={Math.abs(rejectionTrend)}
          changeType={rejectionTrend === 0 ? undefined : rejectionTrend > 0 ? "increase" : "decrease"}
          description="Percentage of validations rejected"
        />
        <KpiCard
          title="Avg Processing Time"
          value={`${avgProcessingMinutes.toFixed(1)}m`}
          icon={<Clock className="h-4 w-4" />}
          change={Math.abs(processingTrend)}
          changeType={processingTrend === 0 ? undefined : processingTrend > 0 ? "increase" : "decrease"}
          description="Average time per validation"
        />
      </div>

      {/* Tabs for Different Views */}
      <Tabs defaultValue="trends" className="space-y-4">
        <TabsList>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="clients">Clients</TabsTrigger>
          <TabsTrigger value="discrepancies">Discrepancies</TabsTrigger>
        </TabsList>

        {/* Trends Tab */}
        <TabsContent value="trends" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card dense>
              <CardHeader dense>
                <CardTitle>Daily Validation Volume</CardTitle>
                <CardDescription>Number of validations processed per day</CardDescription>
              </CardHeader>
              <CardContent dense>
                <ChartArea
                  data={dashboard.trends.daily_volumes}
                  xKey="date"
                  yKey="count"
                  height={250}
                  color="hsl(var(--primary))"
                />
              </CardContent>
            </Card>

            <Card dense>
              <CardHeader dense>
                <CardTitle>Success vs Rejection Rate</CardTitle>
                <CardDescription>Daily success and rejection percentages</CardDescription>
              </CardHeader>
              <CardContent dense>
                <ChartLine
                  data={dashboard.trends.success_rates}
                  xKey="date"
                  lines={[
                    { key: "success_rate", color: "hsl(var(--success))", label: "Success Rate" },
                    { key: "rejection_rate", color: "hsl(var(--destructive))", label: "Rejection Rate" },
                  ]}
                  height={250}
                  yAxisFormatter={(value) => `${value.toFixed(0)}%`}
                />
              </CardContent>
            </Card>

            <Card dense>
              <CardHeader dense>
                <CardTitle>Processing Time Trend</CardTitle>
                <CardDescription>Average processing time per validation</CardDescription>
              </CardHeader>
              <CardContent dense>
                <ChartLine
                  data={dashboard.trends.processing_times}
                  xKey="date"
                  lines={[{ key: "avg_time", color: "hsl(var(--info))", label: "Avg Time" }]}
                  height={250}
                  yAxisFormatter={(value) => `${value.toFixed(1)}m`}
                />
              </CardContent>
            </Card>

            <Card dense>
              <CardHeader dense>
                <CardTitle>Daily Discrepancies</CardTitle>
                <CardDescription>Number of discrepancies found per day</CardDescription>
              </CardHeader>
              <CardContent dense>
                <ChartBar
                  data={dashboard.trends.daily_discrepancies}
                  xKey="date"
                  yKey="count"
                  height={250}
                  color="hsl(var(--warning))"
                />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Clients Tab */}
        <TabsContent value="clients" className="space-y-4">
          <Card dense>
            <CardHeader dense>
              <CardTitle>Top Clients by Validation Volume</CardTitle>
              <CardDescription>
                Clients ranked by total number of validations
              </CardDescription>
            </CardHeader>
            <CardContent dense>
              <div className="space-y-4">
                {dashboard.users.slice(0, 10).map((client) => (
                  <div key={client.user_id} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-muted">
                        <Users className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-sm font-medium leading-none">{client.username}</p>
                        <p className="text-xs text-muted-foreground">
                          {client.job_count} validations
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={client.success_rate >= 90 ? "default" : "secondary"}
                        className="text-xs"
                      >
                        {client.success_rate.toFixed(1)}% success
                      </Badge>
                      <RoleBadge role={client.role} />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Discrepancies Tab */}
        <TabsContent value="discrepancies" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card dense>
              <CardHeader dense>
                <CardTitle>Discrepancies by Type</CardTitle>
                <CardDescription>
                  Total: {dashboard.discrepancies.total_discrepancies.toLocaleString()}
                </CardDescription>
              </CardHeader>
              <CardContent dense>
                <ChartBar
                  data={dashboard.discrepancies.by_type}
                  xKey="discrepancy_type"
                  yKey="count"
                  height={250}
                  color="hsl(var(--warning))"
                  xAxisFormatter={(value) =>
                    value.toString().replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())
                  }
                />
              </CardContent>
            </Card>

            <Card dense>
              <CardHeader dense>
                <CardTitle>Discrepancies by Severity</CardTitle>
                <CardDescription>Distribution of discrepancy severity levels</CardDescription>
              </CardHeader>
              <CardContent dense>
                <ChartBar
                  data={dashboard.discrepancies.by_severity}
                  xKey="severity"
                  yKey="count"
                  height={250}
                  xAxisFormatter={(value) => value.toString().charAt(0).toUpperCase() + value.toString().slice(1)}
                />
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

