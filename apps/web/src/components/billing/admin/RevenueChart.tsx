/**
 * RevenueChart component - Displays revenue trends and plan breakdown
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  PieChart as PieChartIcon,
  Calendar,
  DollarSign
} from 'lucide-react';
import { format, subMonths, startOfMonth, endOfMonth } from 'date-fns';

// Hooks and types
import { useAdminRevenueTrends, useAdminUsageReport } from '@/hooks/useBilling';
import { formatCurrency, PlanType, PLAN_DEFINITIONS } from '@/types/billing';
import type { AdminUsageReport } from '@/types/billing';

interface RevenueChartProps {
  className?: string;
  period?: 'monthly' | 'quarterly' | 'yearly';
  showPlanBreakdown?: boolean;
}

export function RevenueChart({
  className,
  period = 'monthly',
  showPlanBreakdown = true
}: RevenueChartProps) {
  const [chartType, setChartType] = useState<'line' | 'area' | 'bar'>('area');
  const [timePeriod, setTimePeriod] = useState<'3m' | '6m' | '12m'>('6m');

  // Calculate date range based on selected period
  const getDateRange = () => {
    const endDate = new Date();
    const monthsBack = timePeriod === '3m' ? 3 : timePeriod === '6m' ? 6 : 12;
    const startDate = subMonths(endDate, monthsBack);

    return {
      startDate: format(startDate, 'yyyy-MM-dd'),
      endDate: format(endDate, 'yyyy-MM-dd')
    };
  };

  const { startDate, endDate } = getDateRange();

  // Queries
  const { data: revenueTrends, isLoading: trendsLoading } = useAdminRevenueTrends(startDate, endDate);
  const { data: usageReport, isLoading: reportLoading } = useAdminUsageReport(startDate, endDate);

  // Mock data for demonstration (replace with real API data)
  const mockRevenueData = Array.from({ length: parseInt(timePeriod) }, (_, i) => {
    const date = subMonths(new Date(), (parseInt(timePeriod) - 1) - i);
    const baseRevenue = 800000 + (Math.random() * 400000);

    return {
      month: format(date, 'MMM yyyy'),
      revenue: baseRevenue,
      free: 0,
      starter: baseRevenue * 0.3,
      professional: baseRevenue * 0.5,
      enterprise: baseRevenue * 0.2,
      companies: Math.floor(Math.random() * 50) + 100,
      growth: (Math.random() - 0.5) * 20 // -10% to +10%
    };
  });

  const planBreakdownData = [
    { name: 'Starter', value: 35, revenue: 420000, color: '#3b82f6' },
    { name: 'Professional', value: 45, revenue: 675000, color: '#8b5cf6' },
    { name: 'Enterprise', value: 20, revenue: 300000, color: '#f59e0b' }
  ];

  const totalRevenue = mockRevenueData.reduce((sum, item) => sum + item.revenue, 0);
  const averageRevenue = totalRevenue / mockRevenueData.length;
  const currentMonthRevenue = mockRevenueData[mockRevenueData.length - 1]?.revenue || 0;
  const previousMonthRevenue = mockRevenueData[mockRevenueData.length - 2]?.revenue || 0;
  const monthlyGrowth = previousMonthRevenue ?
    ((currentMonthRevenue - previousMonthRevenue) / previousMonthRevenue) * 100 : 0;

  if (trendsLoading || reportLoading) {
    return (
      <div className={className}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2">
            <CardHeader>
              <div className="h-6 bg-muted rounded animate-pulse w-32" />
            </CardHeader>
            <CardContent>
              <div className="h-64 bg-muted rounded animate-pulse" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <div className="h-6 bg-muted rounded animate-pulse w-24" />
            </CardHeader>
            <CardContent>
              <div className="h-64 bg-muted rounded animate-pulse" />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Revenue Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(totalRevenue)}</div>
            <p className="text-xs text-muted-foreground">
              Last {timePeriod === '3m' ? '3' : timePeriod === '6m' ? '6' : '12'} months
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Monthly Average</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(averageRevenue)}</div>
            <p className="text-xs text-muted-foreground">
              Average per month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">This Month</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(currentMonthRevenue)}</div>
            <div className="flex items-center space-x-1">
              {monthlyGrowth >= 0 ? (
                <TrendingUp className="h-3 w-3 text-green-600" />
              ) : (
                <TrendingDown className="h-3 w-3 text-red-600" />
              )}
              <span className={`text-xs font-medium ${
                monthlyGrowth >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {monthlyGrowth >= 0 ? '+' : ''}{monthlyGrowth.toFixed(1)}%
              </span>
              <span className="text-xs text-muted-foreground">vs last month</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">ARPC</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(averageRevenue / (usageReport?.total_companies || 150))}
            </div>
            <p className="text-xs text-muted-foreground">
              Avg revenue per company
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Revenue Trends Chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Revenue Trends
              </CardTitle>
              <div className="flex items-center space-x-2">
                <Select value={timePeriod} onValueChange={(value: '3m' | '6m' | '12m') => setTimePeriod(value)}>
                  <SelectTrigger className="w-[100px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="3m">3 months</SelectItem>
                    <SelectItem value="6m">6 months</SelectItem>
                    <SelectItem value="12m">12 months</SelectItem>
                  </SelectContent>
                </Select>

                <div className="flex items-center space-x-1">
                  <Button
                    size="sm"
                    variant={chartType === 'line' ? 'default' : 'outline'}
                    onClick={() => setChartType('line')}
                    className="px-2"
                  >
                    Line
                  </Button>
                  <Button
                    size="sm"
                    variant={chartType === 'area' ? 'default' : 'outline'}
                    onClick={() => setChartType('area')}
                    className="px-2"
                  >
                    Area
                  </Button>
                  <Button
                    size="sm"
                    variant={chartType === 'bar' ? 'default' : 'outline'}
                    onClick={() => setChartType('bar')}
                    className="px-2"
                  >
                    Bar
                  </Button>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              {chartType === 'line' ? (
                <LineChart data={mockRevenueData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-background border rounded-lg shadow-sm p-3">
                            <p className="font-medium">{label}</p>
                            <p className="text-sm">
                              <span className="text-blue-600">Revenue: </span>
                              {formatCurrency(payload[0].value as number)}
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="revenue"
                    stroke="#3b82f6"
                    strokeWidth={3}
                    dot={{ fill: '#3b82f6', r: 4 }}
                  />
                </LineChart>
              ) : chartType === 'area' ? (
                <AreaChart data={mockRevenueData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-background border rounded-lg shadow-sm p-3">
                            <p className="font-medium">{label}</p>
                            <p className="text-sm">
                              <span className="text-blue-600">Revenue: </span>
                              {formatCurrency(payload[0].value as number)}
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.1}
                  />
                </AreaChart>
              ) : (
                <BarChart data={mockRevenueData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-background border rounded-lg shadow-sm p-3">
                            <p className="font-medium">{label}</p>
                            <p className="text-sm">
                              <span className="text-blue-600">Revenue: </span>
                              {formatCurrency(payload[0].value as number)}
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar dataKey="revenue" fill="#3b82f6" />
                </BarChart>
              )}
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Plan Revenue Breakdown */}
        {showPlanBreakdown && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PieChartIcon className="h-5 w-5" />
                Revenue by Plan
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={planBreakdownData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="revenue"
                    >
                      {planBreakdownData.map((entry, index) => (
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
                                <span>Revenue: </span>
                                {formatCurrency(data.revenue)}
                              </p>
                              <p className="text-sm">
                                <span>Share: </span>
                                {data.value}%
                              </p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>

                <div className="space-y-3">
                  {planBreakdownData.map((item, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: item.color }}
                        />
                        <span className="text-sm font-medium">{item.name}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium">
                          {formatCurrency(item.revenue)}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {item.value}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Monthly Growth Table */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Monthly Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {mockRevenueData.slice(-6).map((month, index) => (
              <div key={index} className="flex items-center justify-between py-2 border-b last:border-b-0">
                <div className="flex items-center space-x-3">
                  <div>
                    <div className="font-medium">{month.month}</div>
                    <div className="text-sm text-muted-foreground">
                      {month.companies} companies
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <div className="font-medium">{formatCurrency(month.revenue)}</div>
                    <div className="flex items-center space-x-1">
                      {month.growth >= 0 ? (
                        <TrendingUp className="h-3 w-3 text-green-600" />
                      ) : (
                        <TrendingDown className="h-3 w-3 text-red-600" />
                      )}
                      <span className={`text-xs ${
                        month.growth >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {month.growth >= 0 ? '+' : ''}{month.growth.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}