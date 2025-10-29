import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { KpiCard } from "@/components/analytics/KpiCard";
import { DateRangePicker } from "@/components/analytics/DateRangePicker";
import { ExportButtons } from "@/components/analytics/ExportButtons";
import { ChartLine } from "@/components/analytics/charts/ChartLine";
import { ChartBar } from "@/components/analytics/charts/ChartBar";
import { ChartArea } from "@/components/analytics/charts/ChartArea";
import { EmptyState, NoDataState } from "@/components/analytics/EmptyState";
import { ErrorState } from "@/components/analytics/ErrorState";
import { RoleBadge } from "@/components/analytics/RoleBadge";
import { analyticsApi } from "@/api/analytics";
import { useAuth } from "@/hooks/use-auth";
import type { AnalyticsFilters, AnalyticsDashboard } from "@/types/analytics";
import { subDays } from "date-fns";

export default function AnalyticsPage() {
  const { user } = useAuth();
  const [filters, setFilters] = React.useState<AnalyticsFilters>({
    timeRange: "30d",
    startDate: subDays(new Date(), 30),
    endDate: new Date(),
  });

  const {
    data: dashboard,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: ['analytics-dashboard', filters],
    queryFn: () => analyticsApi.getDashboard({
      time_range: filters.timeRange,
      start_date: filters.timeRange === "custom" ? filters.startDate?.toISOString() : undefined,
      end_date: filters.timeRange === "custom" ? filters.endDate?.toISOString() : undefined,
    }),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });

  if (!user) {
    return (
      <div className="container mx-auto py-6">
        <ErrorState
          error="Please log in to view analytics"
          className="max-w-md mx-auto"
        />
      </div>
    );
  }

  const isExporter = user.role === "exporter";
  const isImporter = user.role === "importer";
  const isBank = user.role === "bank";
  const isAdmin = user.role === "admin";
  const isPersonalView = isExporter || isImporter;
  const isSystemView = isBank || isAdmin;

  if (isLoading) {
    return (
      <div className="container mx-auto py-6">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Analytics Dashboard</h1>
              <p className="text-muted-foreground">Track your validation performance and insights</p>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Card key={i}>
                <CardHeader className="space-y-0 pb-2">
                  <div className="h-4 bg-muted rounded animate-pulse" />
                </CardHeader>
                <CardContent>
                  <div className="h-8 bg-muted rounded animate-pulse mb-2" />
                  <div className="h-3 bg-muted rounded animate-pulse w-2/3" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-6">
        <ErrorState
          error={error as Error}
          onRetry={refetch}
          className="max-w-md mx-auto"
        />
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="container mx-auto py-6">
        <NoDataState
          onRefresh={refetch}
          className="max-w-md mx-auto"
        />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold tracking-tight">
              {isPersonalView ? "My Analytics" : "System Analytics"}
            </h1>
            <RoleBadge role={user.role} />
          </div>
          <p className="text-muted-foreground">
            {isPersonalView
              ? "Track your validation performance and document processing insights"
              : "Monitor system-wide validation metrics and performance trends"
            }
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-2">
          <DateRangePicker
            value={filters}
            onChange={setFilters}
            className="w-full sm:w-auto"
          />
          <ExportButtons filters={filters} />
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Total Jobs"
          value={dashboard.summary.total_jobs}
          change={dashboard.trends.job_volume_trend}
          icon="briefcase"
        />
        <KpiCard
          title="Success Rate"
          value={`${(100 - dashboard.summary.rejection_rate).toFixed(1)}%`}
          change={dashboard.trends.success_rate_trend}
          icon="check-circle"
          variant={dashboard.summary.rejection_rate < 10 ? "success" : dashboard.summary.rejection_rate < 25 ? "warning" : "error"}
        />
        <KpiCard
          title="Avg Processing Time"
          value={dashboard.summary.avg_processing_time_minutes
            ? `${dashboard.summary.avg_processing_time_minutes.toFixed(1)}m`
            : "N/A"
          }
          change={dashboard.trends.processing_time_trend}
          icon="clock"
        />
        <KpiCard
          title="Total Discrepancies"
          value={dashboard.discrepancies.total_discrepancies}
          change={dashboard.trends.discrepancy_trend}
          icon="alert-triangle"
          variant={dashboard.discrepancies.total_discrepancies > 100 ? "error" : "default"}
        />
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="discrepancies">Discrepancies</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          {isSystemView && (
            <>
              <TabsTrigger value="users">Users</TabsTrigger>
              <TabsTrigger value="system">System</TabsTrigger>
            </>
          )}
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Document Distribution */}
            <Card>
              <CardHeader>
                <CardTitle>Document Distribution</CardTitle>
                <CardDescription>
                  Breakdown of validation jobs by document type
                </CardDescription>
              </CardHeader>
              <CardContent>
                {Object.keys(dashboard.summary.doc_distribution).length > 0 ? (
                  <ChartBar
                    data={Object.entries(dashboard.summary.doc_distribution).map(([key, value]) => ({
                      name: key.replace('_', ' ').toUpperCase(),
                      value
                    }))}
                    height={300}
                    bars={[{ dataKey: 'value', name: 'Jobs', color: '#8884d8' }]}
                  />
                ) : (
                  <NoDataState />
                )}
              </CardContent>
            </Card>

            {/* Job Trends */}
            <Card>
              <CardHeader>
                <CardTitle>Job Volume Trends</CardTitle>
                <CardDescription>
                  Daily validation job submissions over time
                </CardDescription>
              </CardHeader>
              <CardContent>
                {dashboard.trends.daily_volumes.length > 0 ? (
                  <ChartLine
                    data={dashboard.trends.daily_volumes}
                    height={300}
                    lines={[{ dataKey: 'count', name: 'Jobs', color: '#8884d8' }]}
                    xAxisKey="date"
                  />
                ) : (
                  <NoDataState />
                )}
              </CardContent>
            </Card>
          </div>

          {/* Success Rate Trends */}
          <Card>
            <CardHeader>
              <CardTitle>Success Rate Over Time</CardTitle>
              <CardDescription>
                Track validation success rates and identify patterns
              </CardDescription>
            </CardHeader>
            <CardContent>
              {dashboard.trends.success_rates.length > 0 ? (
                <ChartArea
                  data={dashboard.trends.success_rates}
                  height={300}
                  areas={[
                    { dataKey: 'success_rate', name: 'Success Rate', color: '#22c55e', fillOpacity: 0.2 },
                    { dataKey: 'rejection_rate', name: 'Rejection Rate', color: '#ef4444', fillOpacity: 0.2 }
                  ]}
                  xAxisKey="date"
                />
              ) : (
                <NoDataState />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Discrepancies Tab */}
        <TabsContent value="discrepancies" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Discrepancy Types */}
            <Card>
              <CardHeader>
                <CardTitle>Discrepancy Types</CardTitle>
                <CardDescription>
                  Most common validation issues by type
                </CardDescription>
              </CardHeader>
              <CardContent>
                {dashboard.discrepancies.by_type.length > 0 ? (
                  <ChartBar
                    data={dashboard.discrepancies.by_type.map(item => ({
                      name: item.discrepancy_type.replace('_', ' '),
                      value: item.count
                    }))}
                    height={300}
                    bars={[{ dataKey: 'value', name: 'Count', color: '#ef4444' }]}
                    layout="vertical"
                  />
                ) : (
                  <NoDataState />
                )}
              </CardContent>
            </Card>

            {/* Discrepancy Trends */}
            <Card>
              <CardHeader>
                <CardTitle>Discrepancy Trends</CardTitle>
                <CardDescription>
                  Daily discrepancy counts over time
                </CardDescription>
              </CardHeader>
              <CardContent>
                {dashboard.trends.daily_discrepancies.length > 0 ? (
                  <ChartLine
                    data={dashboard.trends.daily_discrepancies}
                    height={300}
                    lines={[{ dataKey: 'count', name: 'Discrepancies', color: '#ef4444' }]}
                    xAxisKey="date"
                  />
                ) : (
                  <NoDataState />
                )}
              </CardContent>
            </Card>
          </div>

          {/* Discrepancy Severity */}
          <Card>
            <CardHeader>
              <CardTitle>Discrepancy Severity Distribution</CardTitle>
              <CardDescription>
                Breakdown of discrepancies by severity level
              </CardDescription>
            </CardHeader>
            <CardContent>
              {dashboard.discrepancies.by_severity.length > 0 ? (
                <ChartBar
                  data={dashboard.discrepancies.by_severity.map(item => ({
                    name: item.severity,
                    value: item.count
                  }))}
                  height={250}
                  bars={[
                    {
                      dataKey: 'value',
                      name: 'Count',
                      color: '#f59e0b' // amber for severity
                    }
                  ]}
                />
              ) : (
                <NoDataState />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trends Tab */}
        <TabsContent value="trends" className="space-y-6">
          <div className="grid gap-6">
            {/* Processing Time Trends */}
            <Card>
              <CardHeader>
                <CardTitle>Processing Time Trends</CardTitle>
                <CardDescription>
                  Average processing times over time
                </CardDescription>
              </CardHeader>
              <CardContent>
                {dashboard.trends.processing_times.length > 0 ? (
                  <ChartArea
                    data={dashboard.trends.processing_times}
                    height={350}
                    areas={[{
                      dataKey: 'avg_time',
                      name: 'Avg Processing Time (min)',
                      color: '#6366f1',
                      fillOpacity: 0.3
                    }]}
                    xAxisKey="date"
                  />
                ) : (
                  <NoDataState />
                )}
              </CardContent>
            </Card>

            {/* Combined Trends */}
            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Job Volume vs Success Rate</CardTitle>
                  <CardDescription>
                    Correlation between job volume and success rates
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {dashboard.trends.daily_volumes.length > 0 && dashboard.trends.success_rates.length > 0 ? (
                    <ChartLine
                      data={dashboard.trends.daily_volumes.map((vol, idx) => ({
                        date: vol.date,
                        volume: vol.count,
                        success_rate: dashboard.trends.success_rates[idx]?.success_rate || 0
                      }))}
                      height={300}
                      lines={[
                        { dataKey: 'volume', name: 'Job Volume', color: '#8884d8' },
                        { dataKey: 'success_rate', name: 'Success Rate %', color: '#22c55e' }
                      ]}
                      xAxisKey="date"
                    />
                  ) : (
                    <NoDataState />
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Error Rate Trends</CardTitle>
                  <CardDescription>
                    Track error patterns over time
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {dashboard.trends.success_rates.length > 0 ? (
                    <ChartLine
                      data={dashboard.trends.success_rates}
                      height={300}
                      lines={[{
                        dataKey: 'rejection_rate',
                        name: 'Rejection Rate %',
                        color: '#ef4444'
                      }]}
                      xAxisKey="date"
                    />
                  ) : (
                    <NoDataState />
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Users Tab (System View Only) */}
        {isSystemView && (
          <TabsContent value="users" className="space-y-6">
            <div className="grid gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Top Users by Volume</CardTitle>
                  <CardDescription>
                    Most active users by validation job submissions
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {dashboard.users && dashboard.users.length > 0 ? (
                    <ChartBar
                      data={dashboard.users.slice(0, 10).map(user => ({
                        name: user.username || user.email || `User ${user.user_id}`,
                        value: user.job_count,
                        success_rate: user.success_rate
                      }))}
                      height={400}
                      bars={[{ dataKey: 'value', name: 'Jobs', color: '#8884d8' }]}
                      layout="vertical"
                    />
                  ) : (
                    <NoDataState />
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        )}

        {/* System Tab (Admin Only) */}
        {isAdmin && (
          <TabsContent value="system" className="space-y-6">
            {dashboard.system && (
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                <KpiCard
                  title="Total Users"
                  value={dashboard.system.total_users}
                  icon="users"
                />
                <KpiCard
                  title="Active Users (30d)"
                  value={dashboard.system.active_users}
                  icon="user-check"
                />
                <KpiCard
                  title="System Uptime"
                  value={`${(dashboard.system.uptime_percentage || 0).toFixed(1)}%`}
                  icon="server"
                  variant={dashboard.system.uptime_percentage && dashboard.system.uptime_percentage > 99 ? "success" : "warning"}
                />
                <KpiCard
                  title="Avg Response Time"
                  value={dashboard.system.avg_response_time_ms
                    ? `${dashboard.system.avg_response_time_ms.toFixed(0)}ms`
                    : "N/A"
                  }
                  icon="zap"
                />
                <KpiCard
                  title="Storage Used"
                  value={dashboard.system.storage_used_gb
                    ? `${dashboard.system.storage_used_gb.toFixed(1)}GB`
                    : "N/A"
                  }
                  icon="hard-drive"
                />
                <KpiCard
                  title="API Calls (24h)"
                  value={dashboard.system.api_calls_24h || 0}
                  icon="activity"
                />
              </div>
            )}
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}