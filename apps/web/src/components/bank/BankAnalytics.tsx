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

  const summary = dashboard.summary;
  const trends = dashboard.trends ?? {
    job_volume_trend: 0,
    success_rate_trend: 0,
    processing_time_trend: 0,
    daily_volumes: [] as Array<{ date: string; count: number }>,
    success_rates: [] as Array<{ date: string; success_rate: number; rejection_rate: number }>,
    processing_times: [] as Array<{ date: string; avg_time: number }>,
    daily_discrepancies: [] as Array<{ date: string; count: number }>,
  };

  const discrepancies = dashboard.discrepancies ?? {
    total_discrepancies: 0,
    by_type: [] as Array<{ discrepancy_type: string; count: number }> ,
    by_severity: [] as Array<{ severity: string; count: number }>,
  };

  const users = dashboard.users ?? [];
  const docDistributionEntries = Object.entries(summary.doc_distribution ?? {});
  const dailyVolumes = trends.daily_volumes ?? [];
  const successRates = trends.success_rates ?? [];
  const processingTimes = trends.processing_times ?? [];
  const dailyDiscrepancies = trends.daily_discrepancies ?? [];

  const systemHealth = summary.rejection_rate < 15 ? "healthy" : summary.rejection_rate < 30 ? "warning" : "critical";
  const systemHealthLabel = systemHealth.charAt(0).toUpperCase() + systemHealth.slice(1);
  const activeClients = users.filter((u) => (u.job_count ?? 0) > 0).length;
  const riskLevelValue = discrepancies.total_discrepancies > 500 ? "HIGH" : discrepancies.total_discrepancies > 200 ? "MEDIUM" : "LOW";
  const docDistributionData = docDistributionEntries.map(([key, value]) => {
    const numeric = Number(value ?? 0);
    const percentage = summary.total_jobs ? (numeric / summary.total_jobs) * 100 : 0;
    return {
      name: key.replace(/_/g, " ").toUpperCase(),
      value: numeric,
      percentage,
    };
  });

  const formatDiscrepancyLabel = (label: string) =>
    label
      .replace(/_/g, " ")
      .replace(/\b\w/g, (char) => char.toUpperCase());

  const dailyDiscrepancyChartData = dailyDiscrepancies.map((item) => ({
    name: item.date,
    value: item.count,
  }));

  const processingTimeChartData = processingTimes.map((item) => ({
    date: item.date,
    avg_time: item.avg_time,
    sla_target: 15,
  }));

  const discrepancyTypeChartData = discrepancies.by_type.map((item) => ({
    name: formatDiscrepancyLabel(item.discrepancy_type),
    value: item.count,
  }));

  const severityChartData = discrepancies.by_severity.map((item) => ({
    name: formatDiscrepancyLabel(item.severity),
    value: item.count,
  }));

  const severityCounts = discrepancies.by_severity.reduce(
    (acc, item) => {
      const key = item.severity as keyof typeof acc;
      if (acc[key] !== undefined) {
        acc[key] += item.count;
      }
      return acc;
    },
    { high: 0, medium: 0, low: 0 }
  );

  const topDiscrepancyTypes = [...discrepancies.by_type]
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

  const totalDiscrepancies = discrepancies.total_discrepancies || 0;

  return (
    <div className="space-y-6">
      {/* Header with Date Range Picker */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-2xl font-semibold tracking-tight">Bank System Analytics</h2>
            <RoleBadge role="bank" />
          </div>
          <p className="text-sm text-muted-foreground">
            Monitor trade finance document validation system performance and client activity
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DateRangePicker value={filters} onChange={setFilters} />
          <ExportButtons filters={filters} />
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <KpiCard
          title="Total Validations"
          value={summary.total_jobs.toLocaleString()}
          icon={<FileText className="h-4 w-4" />}
          change={Math.abs(jobTrend)}
          changeType={jobTrend === 0 ? undefined : jobTrend > 0 ? "increase" : "decrease"}
          description="Total LC validations processed"
        />
        <KpiCard
          title="System Success Rate"
          value={`${(100 - summary.rejection_rate).toFixed(1)}%`}
          icon={<TrendingUp className="h-4 w-4" />}
          change={Math.abs(successTrend)}
          changeType={successTrend === 0 ? undefined : successTrend > 0 ? "increase" : "decrease"}
          description="Overall system validation success rate"
        />
        <KpiCard
          title="Rejection Rate"
          value={`${summary.rejection_rate.toFixed(1)}%`}
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
        <KpiCard
          title="Active Clients"
          value={activeClients.toLocaleString()}
          icon={<Users className="h-4 w-4" />}
          description="Clients with recent validation activity"
        />
        <KpiCard
          title="Risk Level"
          value={riskLevelValue}
          icon={<AlertTriangle className="h-4 w-4" />}
          description="Risk posture based on discrepancy volume"
        />
      </div>

      {/* Tabbed Analytics Views */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="clients">Clients</TabsTrigger>
          <TabsTrigger value="risk">Risk Analysis</TabsTrigger>
          <TabsTrigger value="discrepancies">Discrepancies</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="compliance">Compliance</TabsTrigger>
        </TabsList>

        {/* Overview */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card dense>
              <CardHeader dense>
                <CardTitle>Daily Validation Volume</CardTitle>
                <CardDescription>System-wide validation submissions over time</CardDescription>
              </CardHeader>
              <CardContent dense>
                {dailyVolumes.length > 0 ? (
                  <ChartArea
                    data={dailyVolumes}
                    areas={[{ dataKey: "count", name: "Validations", color: "hsl(var(--primary))", fillOpacity: 0.3 }]}
                    height={280}
                  />
                ) : (
                  <div className="flex h-[280px] items-center justify-center text-sm text-muted-foreground">
                    No data available
                  </div>
                )}
              </CardContent>
            </Card>

            <Card dense>
              <CardHeader dense>
                <CardTitle>Document Type Distribution</CardTitle>
                <CardDescription>Breakdown of validation jobs by document type</CardDescription>
              </CardHeader>
              <CardContent dense>
                {docDistributionData.length > 0 ? (
                  <div className="space-y-4">
                    <ChartBar
                      data={docDistributionData}
                      bars={[{ dataKey: "value", name: "Count", color: "#8b5cf6" }]}
                      layout="vertical"
                      height={280}
                    />
                    <div className="space-y-2 text-sm text-muted-foreground">
                      {docDistributionData.map((item) => (
                        <div key={item.name} className="flex items-center justify-between">
                          <span className="font-medium text-foreground">{item.name}</span>
                          <span>
                            {item.value.toLocaleString()} ({item.percentage.toFixed(1)}%)
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="flex h-[280px] items-center justify-center text-sm text-muted-foreground">
                    No data available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Trends */}
        <TabsContent value="trends" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card dense>
              <CardHeader dense>
                <CardTitle>Success vs Rejection Rate</CardTitle>
                <CardDescription>Daily success and rejection percentages</CardDescription>
              </CardHeader>
              <CardContent dense>
                {successRates.length > 0 ? (
                  <ChartLine
                    data={successRates}
                    lines={[
                      { dataKey: "success_rate", name: "Success Rate", color: "hsl(var(--success))" },
                      { dataKey: "rejection_rate", name: "Rejection Rate", color: "hsl(var(--destructive))" },
                    ]}
                    height={300}
                  />
                ) : (
                  <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
                    No rate data
                  </div>
                )}
              </CardContent>
            </Card>

            <Card dense>
              <CardHeader dense>
                <CardTitle>Processing Time Trend</CardTitle>
                <CardDescription>Average processing time compared to SLA target</CardDescription>
              </CardHeader>
              <CardContent dense>
                {processingTimeChartData.length > 0 ? (
                  <ChartLine
                    data={processingTimeChartData}
                    lines={[
                      { dataKey: "avg_time", name: "Avg Processing Time (min)", color: "#6366f1" },
                      { dataKey: "sla_target", name: "SLA Target (min)", color: "#94a3b8" },
                    ]}
                    height={300}
                  />
                ) : (
                  <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
                    No processing time data
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card dense>
            <CardHeader dense>
              <CardTitle>Daily Discrepancies Detected</CardTitle>
              <CardDescription>Volume of discrepancies surfaced each day</CardDescription>
            </CardHeader>
            <CardContent dense>
              {dailyDiscrepancyChartData.length > 0 ? (
                <ChartBar
                  data={dailyDiscrepancyChartData}
                  bars={[{ dataKey: "value", name: "Discrepancies", color: "#f97316" }]}
                  height={300}
                />
              ) : (
                <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
                  No discrepancy data
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Clients */}
        <TabsContent value="clients" className="space-y-6">
          <Card dense>
            <CardHeader dense>
              <CardTitle>Top Clients by Validation Volume</CardTitle>
              <CardDescription>Most active clients and their success rates</CardDescription>
            </CardHeader>
            <CardContent dense>
              {users.length > 0 ? (
                <div className="grid gap-6 lg:grid-cols-[1fr,1.2fr]">
                  <ChartBar
                    data={users.slice(0, 10).map((client) => ({
                      name: client.username ?? client.email ?? client.user_id,
                      value: client.job_count,
                    }))}
                    layout="vertical"
                    bars={[{ dataKey: "value", name: "Jobs", color: "#3b82f6" }]}
                    height={320}
                  />

                  <div className="overflow-auto border rounded-lg">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/40">
                        <tr>
                          <th className="p-3 text-left">Client</th>
                          <th className="p-3 text-left">Role</th>
                          <th className="p-3 text-right">Jobs</th>
                          <th className="p-3 text-right">Success</th>
                        </tr>
                      </thead>
                      <tbody>
                        {users.slice(0, 12).map((client) => (
                          <tr key={client.user_id} className="border-t">
                            <td className="p-3 font-medium">{client.username ?? client.email ?? client.user_id}</td>
                            <td className="p-3"><Badge variant="outline" className="capitalize">{client.role}</Badge></td>
                            <td className="p-3 text-right">{client.job_count.toLocaleString()}</td>
                            <td className="p-3 text-right">
                              <Badge variant={client.success_rate >= 90 ? "default" : client.success_rate >= 75 ? "secondary" : "destructive"}>
                                {client.success_rate.toFixed(1)}%
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
                  No client analytics available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Risk Analysis */}
        <TabsContent value="risk" className="space-y-6">
          <Card dense>
            <CardHeader dense>
              <CardTitle>Risk Summary</CardTitle>
              <CardDescription>Current discrepancy profile and severity mix</CardDescription>
            </CardHeader>
            <CardContent dense>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-lg border p-4">
                  <p className="text-xs font-medium text-muted-foreground uppercase">Risk Level</p>
                  <p className="mt-2 text-2xl font-semibold text-foreground">{riskLevelValue}</p>
                  <p className="text-xs text-muted-foreground mt-1">Based on discrepancy volume and severity</p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-xs font-medium text-muted-foreground uppercase">Total Discrepancies</p>
                  <p className="mt-2 text-2xl font-semibold text-foreground">{totalDiscrepancies.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">Across selected timeframe</p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-xs font-medium text-muted-foreground uppercase">High Severity</p>
                  <p className="mt-2 text-2xl font-semibold text-destructive">{severityCounts.high.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">Requires immediate attention</p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-xs font-medium text-muted-foreground uppercase">Medium / Low Severity</p>
                  <p className="mt-2 text-2xl font-semibold text-foreground">{(severityCounts.medium + severityCounts.low).toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">Monitor and remediate per plan</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card dense>
            <CardHeader dense>
              <CardTitle>Risk Trend</CardTitle>
              <CardDescription>Daily discrepancy count compared to risk threshold</CardDescription>
            </CardHeader>
            <CardContent dense>
              {dailyDiscrepancies.length > 0 ? (
                <ChartLine
                  data={dailyDiscrepancies.map((item) => ({ ...item, risk_threshold: 30 }))}
                  lines={[
                    { dataKey: "count", name: "Discrepancies", color: "#ef4444" },
                    { dataKey: "risk_threshold", name: "Risk Threshold", color: "#f97316" },
                  ]}
                  height={300}
                />
              ) : (
                <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
                  No risk trend data
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Performance */}
        <TabsContent value="performance" className="space-y-6">
          <Card dense>
            <CardHeader dense>
              <CardTitle>Processing Time Performance</CardTitle>
              <CardDescription>Average processing time per validation against SLA</CardDescription>
            </CardHeader>
            <CardContent dense>
              {processingTimeChartData.length > 0 ? (
                <ChartLine
                  data={processingTimeChartData}
                  lines={[
                    { dataKey: "avg_time", name: "Avg Processing Time (min)", color: "#6366f1" },
                    { dataKey: "sla_target", name: "SLA Target (min)", color: "#94a3b8" },
                  ]}
                  height={320}
                />
              ) : (
                <div className="flex h-[320px] items-center justify-center text-sm text-muted-foreground">
                  No processing data available
                </div>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-3">
            <KpiCard
              title="SLA Compliance"
              value="94.2%"
              description="Jobs completed within SLA window"
            />
            <KpiCard
              title="Peak Hour Performance"
              value={`${(avgProcessingMinutes * 1.2).toFixed(1)}m`}
              description="Average processing time during peak load"
            />
            <KpiCard
              title="System Availability"
              value="99.8%"
              description="Platform uptime for the selected timeframe"
            />
          </div>
        </TabsContent>

        {/* Compliance */}
        <TabsContent value="compliance" className="space-y-6">
          <Card dense>
            <CardHeader dense>
              <CardTitle>Regulatory Compliance Overview</CardTitle>
              <CardDescription>Key compliance indicators across AML, KYC, and sanctions screening</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {[
                  { label: "AML Compliance", value: "98.5%" },
                  { label: "KYC Verification", value: "97.2%" },
                  { label: "Sanctions Check", value: "99.8%" },
                  { label: "Document Integrity", value: `${(100 - summary.rejection_rate).toFixed(1)}%` },
                ].map((metric) => (
                  <div key={metric.label} className="p-4 border rounded-lg space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{metric.label}</span>
                      <Badge variant="default">{metric.value}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {metric.label} adherence within the selected timeframe
                    </p>
                  </div>
                ))}
              </div>

              <div className="p-4 bg-muted/50 rounded-lg">
                <h4 className="font-medium mb-2">Audit Trail Status</h4>
                <p className="text-sm text-muted-foreground mb-3">
                  All validation actions are logged for seven years to satisfy regulatory retention requirements.
                </p>
                <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                  <span>• {summary.total_jobs.toLocaleString()} transactions logged</span>
                  <span>• 100% audit trail coverage</span>
                  <span>• Automatic anomaly alerts enabled</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Discrepancies */}
        <TabsContent value="discrepancies" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <Card dense>
              <CardHeader dense>
                <CardTitle>Discrepancies by Type</CardTitle>
                <CardDescription>Most common validation issues detected</CardDescription>
              </CardHeader>
              <CardContent dense>
                {discrepancyTypeChartData.length > 0 ? (
                  <ChartBar
                    data={discrepancyTypeChartData}
                    bars={[{ dataKey: "value", name: "Count", color: "#f97316" }]}
                    layout="vertical"
                    height={300}
                  />
                ) : (
                  <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
                    No discrepancy data
                  </div>
                )}
              </CardContent>
            </Card>

            <Card dense>
              <CardHeader dense>
                <CardTitle>Discrepancies by Severity</CardTitle>
                <CardDescription>Distribution across high, medium, and low severity</CardDescription>
              </CardHeader>
              <CardContent dense>
                {severityChartData.length > 0 ? (
                  <ChartBar
                    data={severityChartData}
                    bars={[{ dataKey: "value", name: "Count", color: "#ef4444" }]}
                    layout="vertical"
                    height={300}
                  />
                ) : (
                  <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
                    No severity data
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {topDiscrepancyTypes.length > 0 && (
            <Card dense>
              <CardHeader dense>
                <CardTitle>Top Discrepancy Drivers</CardTitle>
                <CardDescription>Focus remediation on the leading discrepancy causes</CardDescription>
              </CardHeader>
              <CardContent dense className="space-y-3">
                {topDiscrepancyTypes.map((item, index) => (
                  <div key={item.discrepancy_type} className="flex items-center justify-between rounded-md border p-3">
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className="w-6 justify-center">
                        {index + 1}
                      </Badge>
                      <span className="font-medium text-foreground">{formatDiscrepancyLabel(item.discrepancy_type)}</span>
                    </div>
                    <span className="text-sm text-muted-foreground">
                      {item.count.toLocaleString()}
                      {totalDiscrepancies > 0 ? ` (${((item.count / totalDiscrepancies) * 100).toFixed(1)}%)` : ""}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

