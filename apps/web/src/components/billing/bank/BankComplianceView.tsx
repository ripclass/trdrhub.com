/**
 * Bank Compliance View - SME-wide metrics and compliance tracking
 * Restricted to Bank + Admin roles only
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
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
  Building2,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  DollarSign,
  Users,
  Activity,
  Calendar,
  FileText,
  BarChart3,
  PieChart as PieChartIcon,
  ShieldCheck,
  AlertCircle,
  Download,
  Filter
} from 'lucide-react';
import { format, subMonths, startOfMonth, endOfMonth, subDays } from 'date-fns';

// Hooks and types
import { useBankComplianceReport, useSMEMetrics, useExportComplianceData } from '@/hooks/useBilling';
import { formatCurrency, PlanType, PLAN_DEFINITIONS } from '@/types/billing';
import type { BankComplianceReport, SMEMetrics, ComplianceFilters } from '@/types/billing';
import { useAuth } from '@/hooks/use-auth';

interface BankComplianceViewProps {
  className?: string;
  showExportOptions?: boolean;
}

export function BankComplianceView({
  className,
  showExportOptions = true
}: BankComplianceViewProps) {
  const [timePeriod, setTimePeriod] = useState<'1m' | '3m' | '6m' | '12m'>('3m');
  const [viewType, setViewType] = useState<'overview' | 'compliance' | 'revenue' | 'companies'>('overview');
  const [filters, setFilters] = useState<ComplianceFilters>({
    period: timePeriod,
    include_inactive: false
  });

  const { user } = useAuth();

  // Role-based access control
  const canViewBankData = user?.role === 'bank' || user?.role === 'admin';

  // Calculate date range based on selected period
  const getDateRange = () => {
    const endDate = new Date();
    const monthsBack = timePeriod === '1m' ? 1 : timePeriod === '3m' ? 3 : timePeriod === '6m' ? 6 : 12;
    const startDate = subMonths(endDate, monthsBack);

    return {
      startDate: format(startDate, 'yyyy-MM-dd'),
      endDate: format(endDate, 'yyyy-MM-dd')
    };
  };

  const { startDate, endDate } = getDateRange();

  // Queries
  const { data: complianceReport, isLoading: complianceLoading } = useBankComplianceReport(
    { ...filters, start_date: startDate, end_date: endDate },
    { enabled: canViewBankData }
  );
  const { data: smeMetrics, isLoading: metricsLoading } = useSMEMetrics(
    { period: timePeriod },
    { enabled: canViewBankData }
  );

  // Mutations
  const exportMutation = useExportComplianceData();

  // Access denied for unauthorized roles
  if (!canViewBankData) {
    return (
      <div className={className}>
        <Card>
          <CardContent className="p-8 text-center">
            <ShieldCheck className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Access Restricted</h3>
            <p className="text-muted-foreground">
              Bank compliance view is only available to Bank and Admin users.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Mock data for demonstration (replace with real API data)
  const mockSMEMetrics = {
    total_companies: 147,
    active_companies: 134,
    total_usage: 8650,
    total_revenue: 10380000, // BDT
    compliance_score: 94.2,
    avg_monthly_usage: 2883,
    top_plan: PlanType.PROFESSIONAL,
    usage_growth: 12.5, // percentage
    revenue_growth: 8.3
  };

  const mockComplianceData = Array.from({ length: parseInt(timePeriod) }, (_, i) => {
    const date = subMonths(new Date(), (parseInt(timePeriod) - 1) - i);
    const baseUsage = 2500 + (Math.random() * 1000);
    const baseRevenue = baseUsage * 1200;

    return {
      month: format(date, 'MMM yyyy'),
      total_usage: Math.floor(baseUsage),
      total_revenue: Math.floor(baseRevenue),
      active_companies: 120 + Math.floor(Math.random() * 20),
      compliance_score: 90 + (Math.random() * 8),
      avg_cost_per_company: Math.floor(baseRevenue / (120 + Math.random() * 20))
    };
  });

  const planDistributionData = [
    { name: 'Starter', companies: 45, revenue: 675000, color: '#3b82f6', percentage: 30.6 },
    { name: 'Professional', companies: 67, revenue: 3015000, color: '#8b5cf6', percentage: 45.6 },
    { name: 'Enterprise', companies: 22, revenue: 6600000, color: '#f59e0b', percentage: 15.0 },
    { name: 'Free', companies: 13, revenue: 0, color: '#6b7280', percentage: 8.8 }
  ];

  const complianceMetrics = [
    { metric: 'Data Retention', score: 98, status: 'excellent', trend: 'up' },
    { metric: 'Payment Compliance', score: 92, status: 'good', trend: 'stable' },
    { metric: 'Usage Monitoring', score: 96, status: 'excellent', trend: 'up' },
    { metric: 'Audit Trail', score: 89, status: 'good', trend: 'down' }
  ];

  const handleExport = () => {
    exportMutation.mutate({
      ...filters,
      start_date: startDate,
      end_date: endDate,
      format: 'xlsx'
    });
  };

  const handlePeriodChange = (period: '1m' | '3m' | '6m' | '12m') => {
    setTimePeriod(period);
    setFilters(prev => ({ ...prev, period }));
  };

  if (complianceLoading || metricsLoading) {
    return (
      <div className={className}>
        <div className="space-y-6">
          <Skeleton className="h-8 w-64" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
    <div className={className}>
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Building2 className="h-6 w-6" />
            SME Banking Compliance
          </h1>
          <p className="text-muted-foreground">
            Aggregate metrics and compliance tracking for all SME clients using LC validation services
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Select value={timePeriod} onValueChange={handlePeriodChange}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1m">Last month</SelectItem>
              <SelectItem value="3m">Last 3 months</SelectItem>
              <SelectItem value="6m">Last 6 months</SelectItem>
              <SelectItem value="12m">Last 12 months</SelectItem>
            </SelectContent>
          </Select>

          {showExportOptions && (
            <Button
              variant="outline"
              onClick={handleExport}
              disabled={exportMutation.isPending}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              {exportMutation.isPending ? 'Exporting...' : 'Export Report'}
            </Button>
          )}
        </div>
      </div>

      {/* View Type Tabs */}
      <div className="flex items-center space-x-1 mb-6 border-b">
        {[
          { id: 'overview', label: 'Overview', icon: BarChart3 },
          { id: 'compliance', label: 'Compliance', icon: ShieldCheck },
          { id: 'revenue', label: 'Revenue', icon: DollarSign },
          { id: 'companies', label: 'Companies', icon: Building2 }
        ].map(({ id, label, icon: Icon }) => (
          <Button
            key={id}
            variant={viewType === id ? 'default' : 'ghost'}
            onClick={() => setViewType(id as any)}
            className="gap-2"
          >
            <Icon className="h-4 w-4" />
            {label}
          </Button>
        ))}
      </div>

      {/* Overview Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total SME Clients</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockSMEMetrics.total_companies}</div>
            <div className="flex items-center space-x-1 mt-1">
              <Badge variant="outline" className="text-green-600">
                {mockSMEMetrics.active_companies} active
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Usage</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockSMEMetrics.total_usage.toLocaleString()}</div>
            <div className="flex items-center space-x-1 mt-1">
              <TrendingUp className="h-3 w-3 text-green-600" />
              <span className="text-xs text-green-600">
                +{mockSMEMetrics.usage_growth}% vs last period
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(mockSMEMetrics.total_revenue)}
            </div>
            <div className="flex items-center space-x-1 mt-1">
              <TrendingUp className="h-3 w-3 text-green-600" />
              <span className="text-xs text-green-600">
                +{mockSMEMetrics.revenue_growth}% vs last period
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Compliance Score</CardTitle>
            <ShieldCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {mockSMEMetrics.compliance_score}%
            </div>
            <p className="text-xs text-muted-foreground">
              Excellent compliance rating
            </p>
          </CardContent>
        </Card>
      </div>

      {viewType === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Usage Trends */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                SME Usage Trends
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={mockComplianceData}>
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
                              <span className="text-blue-600">Usage: </span>
                              {(payload[0].value as number).toLocaleString()} validations
                            </p>
                            <p className="text-sm">
                              <span className="text-green-600">Revenue: </span>
                              {formatCurrency(payload[1].value as number)}
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="total_usage"
                    stackId="1"
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.1}
                  />
                  <Area
                    type="monotone"
                    dataKey="total_revenue"
                    stackId="2"
                    stroke="#10b981"
                    fill="#10b981"
                    fillOpacity={0.1}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Plan Distribution */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PieChartIcon className="h-5 w-5" />
                Plan Distribution
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={planDistributionData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="companies"
                    >
                      {planDistributionData.map((entry, index) => (
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
                                <span>Companies: </span>
                                {data.companies} ({data.percentage}%)
                              </p>
                              <p className="text-sm">
                                <span>Revenue: </span>
                                {formatCurrency(data.revenue)}
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
                  {planDistributionData.map((item, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: item.color }}
                        />
                        <span className="text-sm font-medium">{item.name}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium">{item.companies}</div>
                        <div className="text-xs text-muted-foreground">
                          {item.percentage}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {viewType === 'compliance' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Compliance Metrics */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5" />
                Compliance Metrics
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {complianceMetrics.map((metric, index) => (
                  <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className={`w-2 h-2 rounded-full ${
                        metric.status === 'excellent' ? 'bg-green-500' :
                        metric.status === 'good' ? 'bg-blue-500' : 'bg-yellow-500'
                      }`} />
                      <div>
                        <div className="font-medium">{metric.metric}</div>
                        <div className="text-sm text-muted-foreground">
                          {metric.status === 'excellent' ? 'Excellent' :
                           metric.status === 'good' ? 'Good' : 'Needs Attention'}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-lg font-bold">{metric.score}%</span>
                      {metric.trend === 'up' ? (
                        <TrendingUp className="h-4 w-4 text-green-600" />
                      ) : metric.trend === 'down' ? (
                        <TrendingDown className="h-4 w-4 text-red-600" />
                      ) : (
                        <div className="w-4 h-4 rounded-full bg-gray-300" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Compliance Score Trend */}
          <Card>
            <CardHeader>
              <CardTitle>Compliance Score Trend</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={mockComplianceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis domain={[80, 100]} fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-background border rounded-lg shadow-sm p-3">
                            <p className="font-medium">{label}</p>
                            <p className="text-sm">
                              <span className="text-green-600">Score: </span>
                              {(payload[0].value as number).toFixed(1)}%
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="compliance_score"
                    stroke="#10b981"
                    strokeWidth={3}
                    dot={{ fill: '#10b981', r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Monthly Performance Summary */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Monthly Performance Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {mockComplianceData.slice(-6).map((month, index) => (
              <div key={index} className="flex items-center justify-between py-3 border-b last:border-b-0">
                <div className="flex items-center space-x-4">
                  <div>
                    <div className="font-medium">{month.month}</div>
                    <div className="text-sm text-muted-foreground">
                      {month.active_companies} active companies
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-6">
                  <div className="text-right">
                    <div className="text-sm font-medium">
                      {month.total_usage.toLocaleString()} validations
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatCurrency(month.total_revenue)}
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-sm font-medium">
                      {month.compliance_score.toFixed(1)}%
                    </div>
                    <div className="text-xs text-muted-foreground">
                      compliance score
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-sm font-medium">
                      {formatCurrency(month.avg_cost_per_company)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      avg per company
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