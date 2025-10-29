import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Activity,
  Users,
  DollarSign,
  Clock,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  Server,
  Shield,
  LogOut
} from 'lucide-react';
import { useAdminAuth } from '@/lib/admin/auth';

// Simple KPI Card component
const SimpleKPICard = ({ title, value, icon, status }: {
  title: string;
  value: string;
  icon: React.ReactNode;
  status: 'good' | 'warning' | 'critical'
}) => {
  const statusColors = {
    good: 'text-green-600',
    warning: 'text-yellow-600',
    critical: 'text-red-600'
  };

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">{title}</p>
            <p className="text-2xl font-bold text-gray-900">{value}</p>
          </div>
          <div className={`${statusColors[status]}`}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default function AdminDashboard() {
  const { user, isAuthenticated, logout } = useAdminAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/admin/login');
    }
  }, [isAuthenticated, navigate]);

  if (!isAuthenticated) {
    return <div>Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-xl font-semibold text-gray-900">Admin Console</h1>
                <p className="text-sm text-gray-600">LCopilot Platform Administration</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900">{user?.name}</p>
                <p className="text-xs text-gray-600">{user?.role?.replace('_', ' ')}</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={logout}
                className="flex items-center gap-2"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        <div className="space-y-8">
          {/* Welcome Section */}
          <div>
            <h2 className="text-3xl font-bold text-gray-900">Welcome back, {user?.name}!</h2>
            <p className="text-gray-600 mt-2">
              Overview of LCopilot platform operations and health
            </p>
          </div>

          {/* KPI Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <SimpleKPICard
              title="System Uptime"
              value="99.9%"
              icon={<Activity className="w-6 h-6" />}
              status="good"
            />

            <SimpleKPICard
              title="Active Users (24h)"
              value="2,547"
              icon={<Users className="w-6 h-6" />}
              status="good"
            />

            <SimpleKPICard
              title="Revenue (24h)"
              value="$12,456"
              icon={<DollarSign className="w-6 h-6" />}
              status="good"
            />

            <SimpleKPICard
              title="P95 Latency"
              value="245ms"
              icon={<Clock className="w-6 h-6" />}
              status="good"
            />
          </div>

          {/* Secondary Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <SimpleKPICard
              title="Error Rate"
              value="0.02%"
              icon={<AlertTriangle className="w-6 h-6" />}
              status="good"
            />

            <SimpleKPICard
              title="Jobs Processed (24h)"
              value="8,932"
              icon={<TrendingUp className="w-6 h-6" />}
              status="good"
            />

            <SimpleKPICard
              title="Active Alerts"
              value="0"
              icon={<CheckCircle className="w-6 h-6" />}
              status="good"
            />
          </div>

          {/* Role-based Features */}
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
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <span className="text-sm font-medium">API Gateway</span>
                    <span className="text-green-600 text-sm">Healthy</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <span className="text-sm font-medium">Database</span>
                    <span className="text-green-600 text-sm">Healthy</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <span className="text-sm font-medium">Queue Service</span>
                    <span className="text-green-600 text-sm">Healthy</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <span className="text-sm font-medium">Storage</span>
                    <span className="text-green-600 text-sm">Healthy</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Role-specific Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>
                  Common administrative tasks for {user?.role?.replace('_', ' ')}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 gap-3">
                  {user?.role === 'super_admin' && (
                    <>
                      <Button variant="outline" className="justify-start">
                        <Users className="w-4 h-4 mr-2" />
                        Manage Users
                      </Button>
                      <Button variant="outline" className="justify-start">
                        <Server className="w-4 h-4 mr-2" />
                        System Configuration
                      </Button>
                    </>
                  )}
                  {(user?.role === 'ops_admin' || user?.role === 'super_admin') && (
                    <>
                      <Button variant="outline" className="justify-start">
                        <Activity className="w-4 h-4 mr-2" />
                        Monitor Jobs
                      </Button>
                      <Button variant="outline" className="justify-start">
                        <TrendingUp className="w-4 h-4 mr-2" />
                        View Metrics
                      </Button>
                    </>
                  )}
                  {(user?.role === 'security_admin' || user?.role === 'super_admin') && (
                    <>
                      <Button variant="outline" className="justify-start">
                        <Shield className="w-4 h-4 mr-2" />
                        Security Audit
                      </Button>
                      <Button variant="outline" className="justify-start">
                        <AlertTriangle className="w-4 h-4 mr-2" />
                        Review Alerts
                      </Button>
                    </>
                  )}
                  {(user?.role === 'finance_admin' || user?.role === 'super_admin') && (
                    <>
                      <Button variant="outline" className="justify-start">
                        <DollarSign className="w-4 h-4 mr-2" />
                        Billing Reports
                      </Button>
                      <Button variant="outline" className="justify-start">
                        <TrendingUp className="w-4 h-4 mr-2" />
                        Revenue Analytics
                      </Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Recent Activity */}
          <Card>
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
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div>
                    <p className="text-sm font-medium">User login</p>
                    <p className="text-xs text-gray-600">admin@lcopilot.com logged in</p>
                  </div>
                  <span className="text-xs text-gray-500">2 minutes ago</span>
                </div>
                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div>
                    <p className="text-sm font-medium">Job completed</p>
                    <p className="text-xs text-gray-600">Document processing job #12345</p>
                  </div>
                  <span className="text-xs text-gray-500">5 minutes ago</span>
                </div>
                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div>
                    <p className="text-sm font-medium">System health check</p>
                    <p className="text-xs text-gray-600">All services healthy</p>
                  </div>
                  <span className="text-xs text-gray-500">10 minutes ago</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}