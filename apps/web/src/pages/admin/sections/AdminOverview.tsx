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
    good: 'text-success',
    warning: 'text-warning',
    critical: 'text-destructive'
  };

  return (
    <Card className="shadow-soft border-0">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-2">{title}</p>
            <p className="text-2xl font-bold text-foreground">{value}</p>
          </div>
          <div className={`${statusColors[status]}`}>
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export function AdminOverview() {
  const { user } = useAdminAuth();

  return (
    <>
      {/* Welcome Section */}
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Welcome back, {user?.name}!</h2>
        <p className="text-muted-foreground">
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
        <Card className="shadow-soft border-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="w-5 h-5 text-primary" />
              System Status
            </CardTitle>
            <CardDescription>
              Health status of core services and dependencies
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-success/10 rounded-lg">
                <span className="text-sm font-medium">API Gateway</span>
                <span className="text-success text-sm">Healthy</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-success/10 rounded-lg">
                <span className="text-sm font-medium">Database</span>
                <span className="text-success text-sm">Healthy</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-success/10 rounded-lg">
                <span className="text-sm font-medium">Queue Service</span>
                <span className="text-success text-sm">Healthy</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-success/10 rounded-lg">
                <span className="text-sm font-medium">Storage</span>
                <span className="text-success text-sm">Healthy</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Role-specific Actions */}
        <Card className="shadow-soft border-0">
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
      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-success" />
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
                <p className="text-xs text-muted-foreground">admin@lcopilot.com logged in</p>
              </div>
              <span className="text-xs text-muted-foreground">2 minutes ago</span>
            </div>
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <p className="text-sm font-medium">Job completed</p>
                <p className="text-xs text-muted-foreground">Document processing job #12345</p>
              </div>
              <span className="text-xs text-muted-foreground">5 minutes ago</span>
            </div>
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <p className="text-sm font-medium">System health check</p>
                <p className="text-xs text-muted-foreground">All services healthy</p>
              </div>
              <span className="text-xs text-muted-foreground">10 minutes ago</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  );
}

