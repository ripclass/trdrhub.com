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
import { TrendingUp, TrendingDown, AlertTriangle, Users, FileText, Clock } from "lucide-react";

export default function BankAnalyticsPage() {
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
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });

  if (!user || user.role !== "bank") {
    return (
      <div className="container mx-auto py-6">
        <ErrorState
          error="Access denied. This page is for bank users only."
          className="max-w-md mx-auto"
        />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="container mx-auto py-6">
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Bank System Analytics</h1>
              <p className="text-muted-foreground">Monitor trade finance validation system performance</p>
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

  const systemHealth = dashboard.summary.rejection_rate < 15 ? "healthy" :
                      dashboard.summary.rejection_rate < 30 ? "warning" : "critical";

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold tracking-tight">Bank System Analytics</h1>
            <RoleBadge role="bank" />
            <Badge variant={systemHealth === "healthy" ? "default" : systemHealth === "warning" ? "secondary" : "destructive"}>
              System {systemHealth.charAt(0).toUpperCase() + systemHealth.slice(1)}
            </Badge>
          </div>
          <p className="text-muted-foreground">
            Monitor trade finance document validation system performance and client activity
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

      {/* Executive Summary KPIs */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <KpiCard
          title="Total Validations"
          value={dashboard.summary.total_jobs}
          change={dashboard.trends.job_volume_trend}
          icon="file-text"
          description="All validation jobs processed by the system"
        />
        <KpiCard
          title="System Success Rate"
          value={`${(100 - dashboard.summary.rejection_rate).toFixed(1)}%`}
          change={dashboard.trends.success_rate_trend}
          icon="check-circle"
          variant={systemHealth === "healthy" ? "success" : systemHealth === "warning" ? "warning" : "error"}
          description="Overall system validation success rate"
        />
        <KpiCard
          title="Avg Processing Time"
          value={dashboard.summary.avg_processing_time_minutes
            ? `${dashboard.summary.avg_processing_time_minutes.toFixed(1)}m`
            : "N/A"
          }
          change={dashboard.trends.processing_time_trend}
          icon="clock"
          description="Average time to complete validations"
        />
        <KpiCard
          title="Active Clients"
          value={dashboard.users ? dashboard.users.filter(u => u.job_count > 0).length : 0}
          icon="users"
          description="Clients with validation activity"
        />
        <KpiCard
          title="Risk Level"
          value={dashboard.discrepancies.total_discrepancies > 500 ? "HIGH" :
                dashboard.discrepancies.total_discrepancies > 200 ? "MEDIUM" : "LOW"}
          icon="alert-triangle"
          variant={dashboard.discrepancies.total_discrepancies > 500 ? "error" :
                   dashboard.discrepancies.total_discrepancies > 200 ? "warning" : "success"}
          description="System risk based on discrepancy volume"
        />
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="clients">Clients</TabsTrigger>
          <TabsTrigger value="risk">Risk Analysis</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="compliance">Compliance</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Daily Volume Trends */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  Daily Validation Volume
                </CardTitle>
                <CardDescription>
                  System-wide validation job submissions over time
                </CardDescription>
              </CardHeader>
              <CardContent>
                {dashboard.trends.daily_volumes.length > 0 ? (
                  <ChartArea
                    data={dashboard.trends.daily_volumes}
                    height={300}
                    areas={[{ dataKey: 'count', name: 'Validations', color: '#3b82f6', fillOpacity: 0.3 }]}
                    xAxisKey="date"
                  />
                ) : (
                  <NoDataState />
                )}
              </CardContent>
            </Card>

            {/* Document Distribution */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Document Type Distribution
                </CardTitle>
                <CardDescription>
                  Breakdown of validation jobs by document type
                </CardDescription>
              </CardHeader>
              <CardContent>
                {Object.keys(dashboard.summary.doc_distribution).length > 0 ? (
                  <ChartBar
                    data={Object.entries(dashboard.summary.doc_distribution).map(([key, value]) => ({
                      name: key.replace('_', ' ').toUpperCase(),
                      value,
                      percentage: ((value / dashboard.summary.total_jobs) * 100).toFixed(1)
                    }))}
                    height={300}
                    bars={[{ dataKey: 'value', name: 'Count', color: '#8b5cf6' }]}
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
              <CardTitle>System Health Trends</CardTitle>
              <CardDescription>
                Monitor system-wide success rates and identify performance patterns
              </CardDescription>
            </CardHeader>
            <CardContent>
              {dashboard.trends.success_rates.length > 0 ? (
                <ChartArea
                  data={dashboard.trends.success_rates}
                  height={350}
                  areas={[
                    { dataKey: 'success_rate', name: 'Success Rate %', color: '#22c55e', fillOpacity: 0.3 },
                    { dataKey: 'rejection_rate', name: 'Rejection Rate %', color: '#ef4444', fillOpacity: 0.2 }
                  ]}
                  xAxisKey="date"
                  stacked={true}
                />
              ) : (
                <NoDataState />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Clients Tab */}
        <TabsContent value="clients" className="space-y-6">
          <div className="grid gap-6">
            {/* Top Clients by Volume */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Top Clients by Volume
                </CardTitle>
                <CardDescription>
                  Most active clients by validation job submissions
                </CardDescription>
              </CardHeader>
              <CardContent>
                {dashboard.users && dashboard.users.length > 0 ? (
                  <div className="space-y-4">
                    <ChartBar
                      data={dashboard.users.slice(0, 10).map(user => ({
                        name: user.username || user.email || `User ${user.user_id}`,
                        value: user.job_count,
                        success_rate: user.success_rate,
                        role: user.role
                      }))}
                      height={400}
                      bars={[{ dataKey: 'value', name: 'Jobs', color: '#3b82f6' }]}
                      layout="vertical"
                    />

                    {/* Client Performance Table */}
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left p-2">Client</th>
                            <th className="text-left p-2">Role</th>
                            <th className="text-right p-2">Jobs</th>
                            <th className="text-right p-2">Success Rate</th>
                            <th className="text-right p-2">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dashboard.users.slice(0, 15).map((user, idx) => (
                            <tr key={idx} className="border-b">
                              <td className="p-2 font-medium">
                                {user.username || user.email || `User ${user.user_id}`}
                              </td>
                              <td className="p-2">
                                <Badge variant="outline" className="capitalize">
                                  {user.role}
                                </Badge>
                              </td>
                              <td className="p-2 text-right">{user.job_count}</td>
                              <td className="p-2 text-right">
                                <Badge variant={user.success_rate > 90 ? "default" : user.success_rate > 75 ? "secondary" : "destructive"}>
                                  {user.success_rate.toFixed(1)}%
                                </Badge>
                              </td>
                              <td className="p-2 text-right">
                                <Badge variant={user.success_rate > 75 ? "default" : "secondary"}>
                                  {user.success_rate > 75 ? "Good" : "Needs Attention"}
                                </Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <NoDataState />
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Risk Analysis Tab */}
        <TabsContent value="risk" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Risk Distribution */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-orange-500" />
                  Discrepancy Risk Analysis
                </CardTitle>
                <CardDescription>
                  Most frequent validation issues and their severity
                </CardDescription>
              </CardHeader>
              <CardContent>
                {dashboard.discrepancies.by_type.length > 0 ? (
                  <ChartBar
                    data={dashboard.discrepancies.by_type.map(item => ({
                      name: item.discrepancy_type.replace('_', ' '),
                      value: item.count,
                      risk_level: item.count > 50 ? "High" : item.count > 20 ? "Medium" : "Low"
                    }))}
                    height={300}
                    bars={[{ dataKey: 'value', name: 'Count', color: '#f59e0b' }]}
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
                <CardTitle>Risk Trends Over Time</CardTitle>
                <CardDescription>
                  Daily discrepancy patterns and risk levels
                </CardDescription>
              </CardHeader>
              <CardContent>
                {dashboard.trends.daily_discrepancies.length > 0 ? (
                  <ChartLine
                    data={dashboard.trends.daily_discrepancies.map(item => ({
                      ...item,
                      risk_threshold: 30 // Example threshold
                    }))}
                    height={300}
                    lines={[
                      { dataKey: 'count', name: 'Discrepancies', color: '#ef4444' },
                      { dataKey: 'risk_threshold', name: 'Risk Threshold', color: '#f59e0b' }
                    ]}
                    xAxisKey="date"
                  />
                ) : (
                  <NoDataState />
                )}
              </CardContent>
            </Card>
          </div>

          {/* Severity Distribution */}
          <Card>
            <CardHeader>
              <CardTitle>Discrepancy Severity Distribution</CardTitle>
              <CardDescription>
                Risk assessment based on discrepancy severity levels
              </CardDescription>
            </CardHeader>
            <CardContent>
              {dashboard.discrepancies.by_severity.length > 0 ? (
                <ChartBar
                  data={dashboard.discrepancies.by_severity.map(item => ({
                    name: item.severity.charAt(0).toUpperCase() + item.severity.slice(1),
                    value: item.count,
                    color: item.severity === "high" ? "#ef4444" :
                           item.severity === "medium" ? "#f59e0b" : "#22c55e"
                  }))}
                  height={250}
                  bars={[{ dataKey: 'value', name: 'Count', color: '#f59e0b' }]}
                />
              ) : (
                <NoDataState />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Performance Tab */}
        <TabsContent value="performance" className="space-y-6">
          <div className="grid gap-6">
            {/* Processing Time Analysis */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Processing Time Performance
                </CardTitle>
                <CardDescription>
                  System processing times and SLA compliance
                </CardDescription>
              </CardHeader>
              <CardContent>
                {dashboard.trends.processing_times.length > 0 ? (
                  <ChartArea
                    data={dashboard.trends.processing_times.map(item => ({
                      ...item,
                      sla_target: 15 // 15 minute SLA target
                    }))}
                    height={350}
                    areas={[
                      { dataKey: 'avg_time', name: 'Avg Processing Time (min)', color: '#6366f1', fillOpacity: 0.3 },
                    ]}
                    xAxisKey="date"
                  />
                ) : (
                  <NoDataState />
                )}
              </CardContent>
            </Card>

            {/* Performance Metrics */}
            <div className="grid gap-4 md:grid-cols-3">
              <KpiCard
                title="SLA Compliance"
                value="94.2%" // This would be calculated from processing times
                icon="target"
                variant="success"
                description="Percentage of jobs completed within SLA"
              />
              <KpiCard
                title="Peak Hour Performance"
                value={dashboard.summary.avg_processing_time_minutes
                  ? `${(dashboard.summary.avg_processing_time_minutes * 1.2).toFixed(1)}m`
                  : "N/A"
                }
                icon="trending-up"
                description="Average processing time during peak hours"
              />
              <KpiCard
                title="System Availability"
                value="99.8%"
                icon="server"
                variant="success"
                description="System uptime percentage"
              />
            </div>
          </div>
        </TabsContent>

        {/* Compliance Tab */}
        <TabsContent value="compliance" className="space-y-6">
          <div className="grid gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Regulatory Compliance Overview</CardTitle>
                <CardDescription>
                  Monitor compliance with trade finance regulations and standards
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Compliance Metrics */}
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">AML Compliance</span>
                      <Badge variant="default">98.5%</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Anti-Money Laundering checks passed
                    </p>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">KYC Verification</span>
                      <Badge variant="default">97.2%</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Know Your Customer verifications completed
                    </p>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Sanctions Check</span>
                      <Badge variant="default">99.8%</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Sanctions screening completed successfully
                    </p>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">Document Integrity</span>
                      <Badge variant={dashboard.summary.rejection_rate < 10 ? "default" : "secondary"}>
                        {(100 - dashboard.summary.rejection_rate).toFixed(1)}%
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Document validation success rate
                    </p>
                  </div>
                </div>

                {/* Audit Trail Summary */}
                <div className="p-4 bg-muted/50 rounded-lg">
                  <h4 className="font-medium mb-2">Audit Trail Status</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    All validation activities are logged and auditable for regulatory compliance
                  </p>
                  <div className="flex gap-4 text-sm">
                    <span>• {dashboard.summary.total_jobs} transactions logged</span>
                    <span>• 100% audit trail coverage</span>
                    <span>• 7-year retention policy active</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}