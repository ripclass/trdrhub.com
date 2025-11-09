/**
 * Monitoring Panel - System health KPIs and anomaly detection
 * Restricted to Admin users only
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
  Cell
} from 'recharts';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  TrendingUp,
  TrendingDown,
  Zap,
  Shield,
  Database,
  Globe,
  Bell,
  RefreshCw,
  Download,
  Settings,
  Eye,
  AlertCircle,
  XCircle,
  Timer
} from 'lucide-react';
import { format, subHours, subDays, subMinutes } from 'date-fns';

// Hooks and types
import {
  useSystemKPIs,
  useSystemAlerts,
  useAnomalyDetection,
  useAcknowledgeAlert,
  useResolveAlert,
  useExportMonitoringData
} from '@/hooks/useMonitoring';
import { formatCurrency } from '@/types/billing';
import {
  AlertType,
  AlertSeverity,
  AlertStatus,
  type SystemAlert,
  type SystemKPIs,
  type AnomalyData,
  type MonitoringFilters,
  getAlertSeverityColor,
  getAlertStatusColor
} from '@/types/monitoring';
import { useAuth } from '@/hooks/use-auth';

interface MonitoringPanelProps {
  className?: string;
  showExportOptions?: boolean;
  refreshInterval?: number; // in seconds
}

export function MonitoringPanel({
  className,
  showExportOptions = true,
  refreshInterval = 30
}: MonitoringPanelProps) {
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('24h');
  const [alertFilter, setAlertFilter] = useState<'all' | 'unacknowledged' | 'critical'>('unacknowledged');
  const [viewType, setViewType] = useState<'overview' | 'alerts' | 'anomalies' | 'performance'>('overview');

  const { user } = useAuth();

  // Role-based access control
  const canViewMonitoring = user?.role === 'admin';

  // Queries with auto-refresh
  const { data: systemKPIs, isLoading: kpisLoading, refetch: refetchKPIs } = useSystemKPIs(
    { time_range: timeRange },
    {
      enabled: canViewMonitoring,
      refetchInterval: refreshInterval * 1000
    }
  );

  const { data: systemAlerts, isLoading: alertsLoading, refetch: refetchAlerts } = useSystemAlerts(
    {
      status: alertFilter === 'all' ? undefined :
             alertFilter === 'unacknowledged' ? AlertStatus.UNACKNOWLEDGED : undefined,
      severity: alertFilter === 'critical' ? AlertSeverity.CRITICAL : undefined,
      limit: 50
    },
    {
      enabled: canViewMonitoring,
      refetchInterval: refreshInterval * 1000
    }
  );

  const { data: anomalyData, isLoading: anomalyLoading } = useAnomalyDetection(
    { time_range: timeRange },
    { enabled: canViewMonitoring }
  );

  // Mutations
  const acknowledgeAlert = useAcknowledgeAlert();
  const resolveAlert = useResolveAlert();
  const exportMutation = useExportMonitoringData();

  // Access denied for unauthorized roles
  if (!canViewMonitoring) {
    return (
      <div className={className}>
        <Card>
          <CardContent className="p-8 text-center">
            <Shield className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Access Restricted</h3>
            <p className="text-muted-foreground">
              System monitoring is only available to Admin users.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Mock data for demonstration (replace with real API data)
  const mockKPIs = {
    payment_success_rate: 94.2,
    webhook_error_rate: 2.1,
    quota_breach_count: 7,
    avg_response_time: 245,
    system_uptime: 99.8,
    active_sessions: 342,
    failed_payments_24h: 12,
    api_calls_per_minute: 1250
  };

  const mockAnomalies = Array.from({ length: 24 }, (_, i) => {
    const time = subHours(new Date(), 23 - i);
    return {
      timestamp: format(time, 'HH:mm'),
      quota_breaches: Math.random() > 0.8 ? Math.floor(Math.random() * 5) + 1 : 0,
      payment_failures: Math.random() > 0.7 ? Math.floor(Math.random() * 3) + 1 : 0,
      response_time: 200 + (Math.random() * 300),
      usage_spike: Math.random() > 0.9 ? Math.floor(Math.random() * 500) + 100 : 0
    };
  });

  const mockAlerts = [
    {
      id: '1',
      type: 'QUOTA_BREACH',
      severity: 'HIGH' as AlertSeverity,
      status: 'UNACKNOWLEDGED' as AlertStatus,
      message: 'Company ABC Ltd exceeded quota limit (105/100 validations)',
      timestamp: new Date().toISOString(),
      metadata: { company_id: 'abc-123', usage: 105, limit: 100 }
    },
    {
      id: '2',
      type: 'PAYMENT_FAILURE',
      severity: 'CRITICAL' as AlertSeverity,
      status: 'ACKNOWLEDGED' as AlertStatus,
      message: 'Multiple payment failures detected for invoice INV-2024-001',
      timestamp: subMinutes(new Date(), 15).toISOString(),
      metadata: { invoice_id: 'INV-2024-001', attempts: 3 }
    },
    {
      id: '3',
      type: 'WEBHOOK_ERROR',
      severity: 'MEDIUM' as AlertSeverity,
      status: 'UNACKNOWLEDGED' as AlertStatus,
      message: 'SSLCommerz webhook validation failed',
      timestamp: subMinutes(new Date(), 30).toISOString(),
      metadata: { webhook_url: 'https://api.example.com/webhooks/sslcommerz' }
    }
  ];

  const handleAcknowledgeAlert = (alertId: string) => {
    acknowledgeAlert.mutate({ alertId });
  };

  const handleResolveAlert = (alertId: string) => {
    resolveAlert.mutate({ alertId });
  };

  const handleExport = () => {
    exportMutation.mutate({
      time_range: timeRange,
      include_alerts: true,
      include_kpis: true,
      format: 'xlsx'
    });
  };

  const handleRefresh = () => {
    refetchKPIs();
    refetchAlerts();
  };

  const getSeverityColor = (severity: AlertSeverity) => {
    switch (severity) {
      case 'CRITICAL': return 'bg-red-100 text-red-800 border-red-200';
      case 'HIGH': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'MEDIUM': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'LOW': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = (status: AlertStatus) => {
    switch (status) {
      case 'UNACKNOWLEDGED': return <AlertTriangle className="h-4 w-4 text-red-600" />;
      case 'ACKNOWLEDGED': return <Eye className="h-4 w-4 text-yellow-600" />;
      case 'RESOLVED': return <CheckCircle className="h-4 w-4 text-green-600" />;
      default: return <AlertCircle className="h-4 w-4 text-gray-600" />;
    }
  };

  if (kpisLoading || alertsLoading) {
    return (
      <div className={className}>
        <div className="space-y-6">
          <Skeleton className="h-8 w-64" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
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
            <Activity className="h-6 w-6" />
            System Monitoring
          </h1>
          <p className="text-muted-foreground">
            Real-time system health, performance metrics, and anomaly detection
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Select value={timeRange} onValueChange={(value: '1h' | '6h' | '24h' | '7d') => setTimeRange(value)}>
            <SelectTrigger className="w-[120px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">Last hour</SelectItem>
              <SelectItem value="6h">Last 6 hours</SelectItem>
              <SelectItem value="24h">Last 24 hours</SelectItem>
              <SelectItem value="7d">Last 7 days</SelectItem>
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            onClick={handleRefresh}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>

          {showExportOptions && (
            <Button
              variant="outline"
              onClick={handleExport}
              disabled={exportMutation.isPending}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              {exportMutation.isPending ? 'Exporting...' : 'Export'}
            </Button>
          )}
        </div>
      </div>

      {/* View Type Tabs */}
      <div className="flex items-center space-x-1 mb-6 border-b">
        {[
          { id: 'overview', label: 'Overview', icon: Activity },
          { id: 'alerts', label: 'Alerts', icon: Bell },
          { id: 'anomalies', label: 'Anomalies', icon: TrendingUp },
          { id: 'performance', label: 'Performance', icon: Zap }
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

      {/* System KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Payment Success Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{mockKPIs.payment_success_rate}%</div>
            <div className="flex items-center space-x-1 mt-1">
              <TrendingUp className="h-3 w-3 text-green-600" />
              <span className="text-xs text-green-600">+2.1% vs yesterday</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Webhook Error Rate</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{mockKPIs.webhook_error_rate}%</div>
            <div className="flex items-center space-x-1 mt-1">
              <TrendingDown className="h-3 w-3 text-green-600" />
              <span className="text-xs text-green-600">-0.5% vs yesterday</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Quota Breaches</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{mockKPIs.quota_breach_count}</div>
            <p className="text-xs text-muted-foreground">
              Last 24 hours
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
            <Timer className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{mockKPIs.avg_response_time}ms</div>
            <div className="flex items-center space-x-1 mt-1">
              <TrendingDown className="h-3 w-3 text-green-600" />
              <span className="text-xs text-green-600">-15ms vs yesterday</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Uptime</CardTitle>
            <Globe className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{mockKPIs.system_uptime}%</div>
            <p className="text-xs text-muted-foreground">
              Last 30 days
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Sessions</CardTitle>
            <Activity className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{mockKPIs.active_sessions.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              Current active users
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed Payments</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{mockKPIs.failed_payments_24h}</div>
            <p className="text-xs text-muted-foreground">
              Last 24 hours
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API Calls/Min</CardTitle>
            <Database className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">{mockKPIs.api_calls_per_minute.toLocaleString()}</div>
            <div className="flex items-center space-x-1 mt-1">
              <TrendingUp className="h-3 w-3 text-green-600" />
              <span className="text-xs text-green-600">+12% vs yesterday</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {viewType === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Response Time Trend */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Timer className="h-5 w-5" />
                Response Time Trends
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={mockAnomalies}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-background border rounded-lg shadow-sm p-3">
                            <p className="font-medium">{label}</p>
                            <p className="text-sm">
                              <span className="text-blue-600">Response Time: </span>
                              {Math.round(payload[0].value as number)}ms
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="response_time"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={{ fill: '#3b82f6', r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Recent Alerts */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5" />
                  Recent Alerts
                </CardTitle>
                <Select value={alertFilter} onValueChange={(value: 'all' | 'unacknowledged' | 'critical') => setAlertFilter(value)}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All alerts</SelectItem>
                    <SelectItem value="unacknowledged">Unacknowledged</SelectItem>
                    <SelectItem value="critical">Critical only</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {mockAlerts
                  .filter(alert =>
                    alertFilter === 'all' ||
                    (alertFilter === 'unacknowledged' && alert.status === 'UNACKNOWLEDGED') ||
                    (alertFilter === 'critical' && alert.severity === 'CRITICAL')
                  )
                  .slice(0, 5)
                  .map((alert) => (
                    <div key={alert.id} className="flex items-start space-x-3 p-3 border rounded-lg">
                      <div className="flex-shrink-0 mt-0.5">
                        {getStatusIcon(alert.status)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between">
                          <div>
                            <Badge className={`text-xs ${getSeverityColor(alert.severity)}`}>
                              {alert.severity}
                            </Badge>
                            <p className="text-sm font-medium mt-1">{alert.message}</p>
                            <p className="text-xs text-muted-foreground">
                              {format(new Date(alert.timestamp), 'MMM dd, HH:mm')}
                            </p>
                          </div>
                        </div>
                        {alert.status === 'UNACKNOWLEDGED' && (
                          <div className="flex items-center space-x-2 mt-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleAcknowledgeAlert(alert.id)}
                              disabled={acknowledgeAlert.isPending}
                            >
                              Acknowledge
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => handleResolveAlert(alert.id)}
                              disabled={resolveAlert.isPending}
                            >
                              Resolve
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {viewType === 'anomalies' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Quota Breaches */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <XCircle className="h-5 w-5" />
                Quota Breach Detection
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={mockAnomalies}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-background border rounded-lg shadow-sm p-3">
                            <p className="font-medium">{label}</p>
                            <p className="text-sm">
                              <span className="text-red-600">Breaches: </span>
                              {payload[0].value}
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar dataKey="quota_breaches" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Payment Failures */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                Payment Failure Spikes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={mockAnomalies}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-background border rounded-lg shadow-sm p-3">
                            <p className="font-medium">{label}</p>
                            <p className="text-sm">
                              <span className="text-orange-600">Failures: </span>
                              {payload[0].value}
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="payment_failures"
                    stroke="#f97316"
                    fill="#f97316"
                    fillOpacity={0.1}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      )}

      {/* System Status Footer */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>System Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center space-x-3">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <div>
                <div className="font-medium">Billing Service</div>
                <div className="text-sm text-muted-foreground">All systems operational</div>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <div>
                <div className="font-medium">Payment Gateway</div>
                <div className="text-sm text-muted-foreground">SSLCommerz & Stripe healthy</div>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
              <div>
                <div className="font-medium">Notifications</div>
                <div className="text-sm text-muted-foreground">Minor delays in email delivery</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}