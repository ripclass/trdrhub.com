/**
 * Billing Usage Page - detailed usage analytics and records
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import {
  TrendingUp,
  Calendar,
  Download,
  Activity,
  DollarSign,
  BarChart3,
  PieChart as PieChartIcon
} from 'lucide-react';
import { format, subDays, startOfMonth, endOfMonth } from 'date-fns';

// Billing components
import { BillingNav, BillingBreadcrumb } from '@/components/billing/BillingNav';
import { UsageTable } from '@/components/billing/UsageTable';
import { QuotaMeter } from '@/components/billing/QuotaMeter';

// Hooks
import {
  useBillingInfo,
  useUsageStats,
  useUsageRecords,
  useExportUsageData
} from '@/hooks/useBilling';

// Types
import { formatCurrency } from '@/types/billing';
import type { UsageRecordsFilters } from '@/types/billing';

export function BillingUsagePage() {
  const [filters, setFilters] = useState<UsageRecordsFilters>({
    page: 1,
    per_page: 25
  });

  const [chartView, setChartView] = useState<'trend' | 'breakdown' | 'cost'>('trend');

  // Queries
  const { data: billingInfo } = useBillingInfo();
  const { data: usageStats, isLoading: statsLoading } = useUsageStats();
  const { data: usageRecords } = useUsageRecords(filters);
  const exportMutation = useExportUsageData();

  // Mock data for charts (in real app, this would come from API)
  const trendData = Array.from({ length: 30 }, (_, i) => {
    const date = subDays(new Date(), 29 - i);
    return {
      date: format(date, 'MMM dd'),
      usage: Math.floor(Math.random() * 15) + 1,
      cost: (Math.floor(Math.random() * 15) + 1) * 1200
    };
  });

  const actionBreakdownData = [
    { name: 'LC Validation', value: 45, cost: 54000, color: '#10b981' },
    { name: 'Re-check', value: 12, cost: 14400, color: '#3b82f6' },
    { name: 'Import Draft', value: 8, cost: 8000, color: '#8b5cf6' },
    { name: 'Import Bundle', value: 3, cost: 5400, color: '#f59e0b' }
  ];

  const monthlyTrendData = Array.from({ length: 12 }, (_, i) => {
    const date = new Date();
    date.setMonth(date.getMonth() - (11 - i));
    return {
      month: format(date, 'MMM'),
      usage: Math.floor(Math.random() * 80) + 20,
      cost: (Math.floor(Math.random() * 80) + 20) * 1200
    };
  });

  const handleExport = () => {
    exportMutation.mutate(filters);
  };

  const handleFilterChange = (newFilters: UsageRecordsFilters) => {
    setFilters(newFilters);
  };

  if (statsLoading || !usageStats) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <BillingBreadcrumb />
        <div className="space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-12 w-full" />
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Breadcrumb */}
      <BillingBreadcrumb />

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Usage Analytics</h1>
          <p className="text-muted-foreground">
            Detailed usage history and trends for your LC validation services
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            onClick={handleExport}
            disabled={exportMutation.isPending}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            {exportMutation.isPending ? 'Exporting...' : 'Export CSV'}
          </Button>
        </div>
      </div>

      {/* Navigation */}
      <BillingNav />

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">This Month</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{usageStats.current_month}</div>
            <p className="text-xs text-muted-foreground">
              validations used
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">This Week</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{usageStats.current_week}</div>
            <p className="text-xs text-muted-foreground">
              validations this week
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(usageStats.total_cost)}
            </div>
            <p className="text-xs text-muted-foreground">
              lifetime spending
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Daily Average</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Math.round(usageStats.current_month / new Date().getDate())}
            </div>
            <p className="text-xs text-muted-foreground">
              validations per day
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Usage Trends Chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Usage Trends
              </CardTitle>
              <div className="flex items-center space-x-1">
                <Button
                  size="sm"
                  variant={chartView === 'trend' ? 'default' : 'outline'}
                  onClick={() => setChartView('trend')}
                >
                  Trend
                </Button>
                <Button
                  size="sm"
                  variant={chartView === 'cost' ? 'default' : 'outline'}
                  onClick={() => setChartView('cost')}
                >
                  Cost
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              {chartView === 'trend' ? (
                <AreaChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-background border rounded-lg shadow-sm p-3">
                            <p className="font-medium">{label}</p>
                            <p className="text-sm">
                              <span className="text-green-600">Usage: </span>
                              {payload[0].value} validations
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="usage"
                    stroke="#10b981"
                    fill="#10b981"
                    fillOpacity={0.1}
                  />
                </AreaChart>
              ) : (
                <BarChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-background border rounded-lg shadow-sm p-3">
                            <p className="font-medium">{label}</p>
                            <p className="text-sm">
                              <span className="text-purple-600">Cost: </span>
                              {formatCurrency(payload[0].value as number)}
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar dataKey="cost" fill="#8b5cf6" />
                </BarChart>
              )}
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Action Breakdown & Quota */}
        <div className="space-y-6">
          {/* Quota Meter */}
          {billingInfo && (
            <QuotaMeter
              usage={usageStats}
              plan={billingInfo.plan}
              showCost={false}
            />
          )}

          {/* Action Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PieChartIcon className="h-5 w-5" />
                Usage by Type
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <ResponsiveContainer width="100%" height={180}>
                  <PieChart>
                    <Pie
                      data={actionBreakdownData}
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {actionBreakdownData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="bg-background border rounded-lg shadow-sm p-3">
                              <p className="font-medium">{data.name}</p>
                              <p className="text-sm">
                                <span>Count: </span>
                                {data.value} validations
                              </p>
                              <p className="text-sm">
                                <span>Cost: </span>
                                {formatCurrency(data.cost)}
                              </p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>

                <div className="space-y-2">
                  {actionBreakdownData.map((item, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: item.color }}
                        />
                        <span className="text-sm">{item.name}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium">{item.value}</div>
                        <div className="text-xs text-muted-foreground">
                          {formatCurrency(item.cost)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Detailed Usage Table */}
      <UsageTable
        initialFilters={filters}
        onRowClick={(record) => {
          console.log('Usage record clicked:', record);
          // Could open a modal with detailed information
        }}
      />
    </div>
  );
}

export default BillingUsagePage;