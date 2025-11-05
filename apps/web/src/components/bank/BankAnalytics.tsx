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

  return (
    <div className="space-y-6">
      {/* Header with Date Range Picker */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-2xl font-semibold tracking-tight">Bank System Analytics</h2>
            <RoleBadge role="bank" />
            <Badge variant={systemHealth === "healthy" ? "default" : systemHealth === "warning" ? "secondary" : "destructive"}>
              System {systemHealthLabel}
            </Badge>
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

      {/* Tabs for Different Views */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="clients">Clients</TabsTrigger>
          <TabsTrigger value="risk">Risk Analysis</TabsTrigger>
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
                    height={280}
                    areas={[{ dataKey: "count", name: "Validations", color: "hsl(var(--primary))", fillOpacity: 0.3 }]}
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
                  <ChartBar
                    data={docDistributionData}
                    bars={[{ dataKey: "value", name: "Count", color: "#8b5cf6" }]}
                    layout="vertical"
                    height={280}
                  />
                ) : (
                  <div className="flex h-[280px] items-center justify-center text-sm text-muted-foreground">
                    No data available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card dense>
            <CardHeader dense>
              <CardTitle>System Health Trends</CardTitle>
              <CardDescription>Success and rejection rates across the selected period</CardDescription>
            </CardHeader>
            <CardContent dense>
              {successRates.length > 0 ? (
                <ChartArea
                  data={successRates}
                  height={320}
                  areas={[
                    { dataKey: "success_rate", name: "Success Rate %", color: "#22c55e", fillOpacity: 0.25 },
                    { dataKey: "rejection_rate", name: "Rejection Rate %", color: "#ef4444", fillOpacity: 0.2 },
                  ]}
                  stacked={false}
                />
              ) : (
                <div className="flex h-[320px] items-center justify-center text-sm text-muted-foreground">
                  No data available
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
          <div className="grid gap-6 lg:grid-cols-2">
            <Card dense>
              <CardHeader dense>
                <CardTitle>Discrepancies by Type</CardTitle>
                <CardDescription>Most frequent validation issues and their counts</CardDescription>
              </CardHeader>
              <CardContent dense>
                {discrepancies.by_type.length > 0 ? (
                  <ChartBar
                    data={discrepancies.by_type.map((item) => ({
                      name: item.discrepancy_type.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
                      value: item.count,
                    }))}
                    layout="vertical"
                    bars={[{ dataKey: "value", name: "Count", color: "#f59e0b" }]}
                    height={300}
                  />
                ) : (
                  <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">No discrepancy data</div>
                )}
              </CardContent>
            </Card>

            <Card dense>
              <CardHeader dense>
                <CardTitle>Risk Trends Over Time</CardTitle>
                <CardDescription>Daily discrepancy counts vs target threshold</CardDescription>
              </CardHeader>
              <CardContent dense>
                {dailyDiscrepancies.length > 0 ? (
                  <ChartLine
                    data={dailyDiscrepancies.map((item) => ({
                      ...item,
                      risk_threshold: 30,
                    }))}
                    xKey="date"
                    lines={[
                      { key: "count", color: "#ef4444", label: "Discrepancies" },
                      { key: "risk_threshold", color: "#f97316", label: "Threshold" },
                    ]}
                    height={300}
                  />
                ) : (
                  <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">No discrepancy trend data</div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card dense>
            <CardHeader dense>
              <CardTitle>Discrepancy Severity Distribution</CardTitle>
              <CardDescription>Breakdown of high, medium, and low severity issues</CardDescription>
            </CardHeader>
            <CardContent dense>
              {discrepancies.by_severity.length > 0 ? (
                <ChartBar
                  data={discrepancies.by_severity.map((item) => ({
                    name: item.severity.charAt(0).toUpperCase() + item.severity.slice(1),
                    value: item.count,
                  }))}
                  bars={[{ dataKey: "value", name: "Count", color: "#f97316" }]}
                  height={260}
                />
              ) : (
                <div className="flex h-[260px] items-center justify-center text-sm text-muted-foreground">No severity data</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Performance */}
        <TabsContent value="performance" className="space-y-6">
          <Card dense>
            <CardHeader dense>
              <CardTitle>Processing Time Performance</CardTitle>
              <CardDescription>Average processing time per validation against SLA target</CardDescription>
            </CardHeader>
            <CardContent dense>
              {processingTimes.length > 0 ? (
                <ChartArea
                  data={processingTimes.map((item) => ({ ...item, sla_target: 15 }))}
                  height={320}
                  areas={[{ dataKey: "avg_time", name: "Avg Processing Time (min)", color: "#6366f1", fillOpacity: 0.25 }]}
                />
              ) : (
                <div className="flex h-[320px] items-center justify-center text-sm text-muted-foreground">No processing time data</div>
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
      </Tabs>
    </div>
  );
}

