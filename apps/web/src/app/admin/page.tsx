import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { KPICard } from '@/components/admin/KPICard';
import { AlertSummary } from '@/components/admin/AlertSummary';
import { SystemStatus } from '@/components/admin/SystemStatus';
import { RecentActivity } from '@/components/admin/RecentActivity';
import {
  Activity,
  Users,
  DollarSign,
  Clock,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  Server
} from 'lucide-react';
import { useAdminKPIs, useSystemStatus, useRecentActivity } from '@/lib/admin/api';

export default function AdminDashboard() {
  const { data: kpis, isLoading: kpisLoading } = useAdminKPIs();
  const { data: systemStatus, isLoading: statusLoading } = useSystemStatus();
  const { data: recentActivity, isLoading: activityLoading } = useRecentActivity();

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="text-gray-600">
          Overview of LCopilot platform operations and health
        </p>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          title="Uptime"
          value={kpis?.uptime_percentage ? `${kpis.uptime_percentage.toFixed(2)}%` : '--'}
          trend={kpis?.uptime_percentage >= 99.9 ? 'up' : kpis?.uptime_percentage >= 99 ? 'stable' : 'down'}
          icon={<Activity className="w-5 h-5" />}
          status={kpis?.uptime_percentage >= 99.9 ? 'good' : kpis?.uptime_percentage >= 99 ? 'warning' : 'critical'}
          loading={kpisLoading}
        />

        <KPICard
          title="Active Users (24h)"
          value={kpis?.active_users_24h?.toLocaleString() || '--'}
          trend="up"
          trendValue="+12%"
          icon={<Users className="w-5 h-5" />}
          status="good"
          loading={kpisLoading}
        />

        <KPICard
          title="Revenue (24h)"
          value={kpis?.revenue_24h_usd ? `$${kpis.revenue_24h_usd.toLocaleString()}` : '--'}
          trend="up"
          trendValue="+8.2%"
          icon={<DollarSign className="w-5 h-5" />}
          status="good"
          loading={kpisLoading}
        />

        <KPICard
          title="P95 Latency"
          value={kpis?.p95_latency_ms ? `${kpis.p95_latency_ms}ms` : '--'}
          trend={kpis?.p95_latency_ms <= 300 ? 'stable' : 'up'}
          icon={<Clock className="w-5 h-5" />}
          status={kpis?.p95_latency_ms <= 300 ? 'good' : kpis?.p95_latency_ms <= 500 ? 'warning' : 'critical'}
          loading={kpisLoading}
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <KPICard
          title="Error Rate"
          value={kpis?.error_rate_percentage ? `${kpis.error_rate_percentage.toFixed(2)}%` : '--'}
          trend={kpis?.error_rate_percentage <= 0.1 ? 'down' : 'up'}
          icon={<AlertTriangle className="w-5 h-5" />}
          status={kpis?.error_rate_percentage <= 0.1 ? 'good' : kpis?.error_rate_percentage <= 1 ? 'warning' : 'critical'}
          loading={kpisLoading}
        />

        <KPICard
          title="Jobs Processed (24h)"
          value={kpis?.jobs_processed_24h?.toLocaleString() || '--'}
          trend="up"
          trendValue="+5.1%"
          icon={<TrendingUp className="w-5 h-5" />}
          status="good"
          loading={kpisLoading}
        />

        <KPICard
          title="Active Alerts"
          value={kpis?.alerts_active?.toString() || '--'}
          trend={kpis?.alerts_active === 0 ? 'down' : 'up'}
          icon={kpis?.alerts_active === 0 ? <CheckCircle className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
          status={kpis?.alerts_active === 0 ? 'good' : kpis?.alerts_active <= 5 ? 'warning' : 'critical'}
          loading={kpisLoading}
        />
      </div>

      {/* Dashboard Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* System Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="w-5 h-5 text-blue-600" />
              System Status
            </CardTitle>
            <CardDescription>
              Health status of core services and dependencies
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SystemStatus
              status={systemStatus}
              loading={statusLoading}
            />
          </CardContent>
        </Card>

        {/* Alert Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-600" />
              Active Alerts
            </CardTitle>
            <CardDescription>
              Current alerts requiring attention
            </CardDescription>
          </CardHeader>
          <CardContent>
            <AlertSummary />
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-green-600" />
              Recent Activity
            </CardTitle>
            <CardDescription>
              Latest admin actions and system events
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RecentActivity
              activities={recentActivity}
              loading={activityLoading}
            />
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>
            Common administrative tasks
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button className="p-4 text-left border rounded-lg hover:bg-gray-50 transition-colors">
              <h3 className="font-medium text-gray-900">View Pending Approvals</h3>
              <p className="text-sm text-gray-600 mt-1">
                Review and approve sensitive operations
              </p>
            </button>

            <button className="p-4 text-left border rounded-lg hover:bg-gray-50 transition-colors">
              <h3 className="font-medium text-gray-900">Job Queue Management</h3>
              <p className="text-sm text-gray-600 mt-1">
                Monitor and manage background jobs
              </p>
            </button>

            <button className="p-4 text-left border rounded-lg hover:bg-gray-50 transition-colors">
              <h3 className="font-medium text-gray-900">Audit Log Search</h3>
              <p className="text-sm text-gray-600 mt-1">
                Search and export audit events
              </p>
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}