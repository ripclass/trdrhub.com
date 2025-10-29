import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/analytics/KpiCard";
import { DateRangePicker } from "@/components/analytics/DateRangePicker";
import { ExportButtons } from "@/components/analytics/ExportButtons";
import { ChartLine } from "@/components/analytics/charts/ChartLine";
import { ChartBar } from "@/components/analytics/charts/ChartBar";
import { NoDataState } from "@/components/analytics/EmptyState";
import { ErrorState } from "@/components/analytics/ErrorState";
import { RoleBadge } from "@/components/analytics/RoleBadge";
import { analyticsApi } from "@/api/analytics";
import { useAuth } from "@/hooks/use-auth";
import type { AnalyticsFilters, SummaryStats, TrendStats } from "@/types/analytics";
import { subDays } from "date-fns";

export default function ExporterAnalyticsPage() {
  const { user } = useAuth();
  const [filters, setFilters] = React.useState<AnalyticsFilters>({
    timeRange: "30d",
    startDate: subDays(new Date(), 30),
    endDate: new Date(),
  });

  const {
    data: summary,
    isLoading: summaryLoading,
    error: summaryError,
    refetch: refetchSummary
  } = useQuery({
    queryKey: ['analytics-summary', filters],
    queryFn: () => analyticsApi.getSummary({
      time_range: filters.timeRange,
      start_date: filters.timeRange === "custom" ? filters.startDate?.toISOString() : undefined,
      end_date: filters.timeRange === "custom" ? filters.endDate?.toISOString() : undefined,
    }),
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });

  const {
    data: trends,
    isLoading: trendsLoading,
    error: trendsError,
  } = useQuery({
    queryKey: ['analytics-trends', filters],
    queryFn: () => analyticsApi.getTrends({
      time_range: filters.timeRange,
      start_date: filters.timeRange === "custom" ? filters.startDate?.toISOString() : undefined,
      end_date: filters.timeRange === "custom" ? filters.endDate?.toISOString() : undefined,
    }),
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });

  const isLoading = summaryLoading || trendsLoading;
  const error = summaryError || trendsError;

  if (!user || user.role !== "exporter") {
    return (
      <div className="container mx-auto py-6">
        <ErrorState
          error="Access denied. This page is for exporters only."
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
              <h1 className="text-3xl font-bold tracking-tight">My Export Analytics</h1>
              <p className="text-muted-foreground">Track your export validation performance</p>
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
          onRetry={refetchSummary}
          className="max-w-md mx-auto"
        />
      </div>
    );
  }

  if (!summary || !trends) {
    return (
      <div className="container mx-auto py-6">
        <NoDataState
          onRefresh={refetchSummary}
          className="max-w-md mx-auto"
        />
      </div>
    );
  }

  const successRate = 100 - summary.rejection_rate;

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold tracking-tight">My Export Analytics</h1>
            <RoleBadge role="exporter" />
          </div>
          <p className="text-muted-foreground">
            Track your export document validation performance and identify improvement opportunities
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
          title="Documents Submitted"
          value={summary.total_jobs}
          change={trends.job_volume_trend}
          icon="file-text"
          description="Total export documents submitted for validation"
        />
        <KpiCard
          title="Validation Success Rate"
          value={`${successRate.toFixed(1)}%`}
          change={trends.success_rate_trend}
          icon="check-circle"
          variant={successRate > 90 ? "success" : successRate > 75 ? "warning" : "error"}
          description="Percentage of documents that passed validation"
        />
        <KpiCard
          title="Avg Processing Time"
          value={summary.avg_processing_time_minutes
            ? `${summary.avg_processing_time_minutes.toFixed(1)}m`
            : "N/A"
          }
          change={trends.processing_time_trend}
          icon="clock"
          description="Average time to complete validation"
        />
        <KpiCard
          title="Rejections"
          value={summary.rejection_count}
          change={trends.discrepancy_trend}
          icon="x-circle"
          variant={summary.rejection_count > 10 ? "error" : summary.rejection_count > 5 ? "warning" : "success"}
          description="Documents rejected due to validation issues"
        />
      </div>

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Document Type Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>My Document Types</CardTitle>
            <CardDescription>
              Distribution of your submitted documents by type
            </CardDescription>
          </CardHeader>
          <CardContent>
            {Object.keys(summary.doc_distribution).length > 0 ? (
              <ChartBar
                data={Object.entries(summary.doc_distribution).map(([key, value]) => ({
                  name: key.replace('_', ' ').toUpperCase(),
                  value
                }))}
                height={300}
                bars={[{ dataKey: 'value', name: 'Documents', color: '#3b82f6' }]}
              />
            ) : (
              <NoDataState />
            )}
          </CardContent>
        </Card>

        {/* Daily Submission Trends */}
        <Card>
          <CardHeader>
            <CardTitle>Daily Submissions</CardTitle>
            <CardDescription>
              Your document submission patterns over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            {trends.daily_volumes.length > 0 ? (
              <ChartLine
                data={trends.daily_volumes}
                height={300}
                lines={[{ dataKey: 'count', name: 'Documents', color: '#3b82f6' }]}
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
          <CardTitle>Validation Performance Over Time</CardTitle>
          <CardDescription>
            Track your validation success rates and identify patterns
          </CardDescription>
        </CardHeader>
        <CardContent>
          {trends.success_rates.length > 0 ? (
            <ChartLine
              data={trends.success_rates}
              height={300}
              lines={[
                { dataKey: 'success_rate', name: 'Success Rate %', color: '#22c55e' },
                { dataKey: 'rejection_rate', name: 'Rejection Rate %', color: '#ef4444' }
              ]}
              xAxisKey="date"
            />
          ) : (
            <NoDataState />
          )}
        </CardContent>
      </Card>

      {/* Processing Time Analysis */}
      <Card>
        <CardHeader>
          <CardTitle>Processing Time Analysis</CardTitle>
          <CardDescription>
            Monitor how processing times vary over time
          </CardDescription>
        </CardHeader>
        <CardContent>
          {trends.processing_times.length > 0 ? (
            <ChartLine
              data={trends.processing_times}
              height={300}
              lines={[{
                dataKey: 'avg_time',
                name: 'Avg Processing Time (min)',
                color: '#f59e0b'
              }]}
              xAxisKey="date"
            />
          ) : (
            <NoDataState />
          )}
        </CardContent>
      </Card>

      {/* Quick Tips */}
      <Card className="border-blue-200 bg-blue-50/50">
        <CardHeader>
          <CardTitle className="text-blue-900">💡 Tips to Improve Your Success Rate</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-blue-800">
          <p>• Ensure all required fields are filled before submission</p>
          <p>• Double-check document formatting matches the expected template</p>
          <p>• Review common rejection reasons in the discrepancies section</p>
          <p>• Submit documents during business hours for faster processing</p>
        </CardContent>
      </Card>
    </div>
  );
}