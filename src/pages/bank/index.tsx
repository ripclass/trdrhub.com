import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Shield,
  Database,
  Activity,
  Download,
  CheckCircle,
  AlertCircle,
  Clock,
  BarChart3,
  Settings,
  FileText,
  Users,
  Globe
} from 'lucide-react';

interface SLAMetrics {
  uptime: number;
  responseTime: number;
  errorRate: number;
  throughput: number;
}

interface TenantInfo {
  alias: string;
  name: string;
  environment: string;
  sla_tier: string;
  domain: string;
  billing_enabled: boolean;
  data_region: string;
}

interface OnboardingStatus {
  environment: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  checklist_complete: boolean;
  last_updated: string;
}

const BankPilotDashboard: React.FC = () => {
  const [tenantInfo, setTenantInfo] = useState<TenantInfo | null>(null);
  const [slaMetrics, setSlaMetrics] = useState<SLAMetrics | null>(null);
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate loading tenant information
    setTimeout(() => {
      setTenantInfo({
        alias: 'demo',
        name: 'Bank Demo Tenant',
        environment: 'sandbox',
        sla_tier: 'demo',
        domain: 'demo.enterprise.trdrhub.com',
        billing_enabled: false,
        data_region: 'us-east-1'
      });

      setSlaMetrics({
        uptime: 99.2,
        responseTime: 245,
        errorRate: 0.8,
        throughput: 156
      });

      setOnboardingStatus([
        {
          environment: 'sandbox',
          status: 'completed',
          checklist_complete: true,
          last_updated: '2024-01-15T10:30:00Z'
        },
        {
          environment: 'uat',
          status: 'pending',
          checklist_complete: false,
          last_updated: '2024-01-15T10:30:00Z'
        },
        {
          environment: 'production',
          status: 'pending',
          checklist_complete: false,
          last_updated: '2024-01-15T10:30:00Z'
        }
      ]);

      setLoading(false);
    }, 1000);
  }, []);

  const handleExportReport = async (reportType: string) => {
    try {
      // Simulate report download
      const link = document.createElement('a');
      link.href = `/api/bankpilot/reports/${reportType}.pdf?tenant_alias=${tenantInfo?.alias}`;
      link.download = `${reportType}_${tenantInfo?.alias}_${new Date().toISOString().split('T')[0]}.pdf`;
      link.click();
    } catch (error) {
      console.error('Failed to download report:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'in_progress':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const getSLATierColor = (tier: string) => {
    switch (tier) {
      case 'platinum':
        return 'bg-purple-100 text-purple-800';
      case 'gold':
        return 'bg-yellow-100 text-yellow-800';
      case 'silver':
        return 'bg-gray-100 text-gray-800';
      case 'bronze':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-blue-100 text-blue-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading bank pilot dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Bank Pilot Dashboard</h1>
            <p className="text-gray-600 mt-1">
              {tenantInfo?.name} • {tenantInfo?.domain}
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Badge className={getSLATierColor(tenantInfo?.sla_tier || 'demo')}>
              {tenantInfo?.sla_tier?.toUpperCase()} SLA
            </Badge>
            <Badge variant={tenantInfo?.environment === 'production' ? 'default' : 'secondary'}>
              {tenantInfo?.environment?.toUpperCase()}
            </Badge>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Uptime</p>
                <p className="text-2xl font-bold text-green-600">{slaMetrics?.uptime}%</p>
              </div>
              <Activity className="h-6 w-6 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Response Time</p>
                <p className="text-2xl font-bold text-blue-600">{slaMetrics?.responseTime}ms</p>
              </div>
              <BarChart3 className="h-6 w-6 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Error Rate</p>
                <p className="text-2xl font-bold text-orange-600">{slaMetrics?.errorRate}%</p>
              </div>
              <AlertCircle className="h-6 w-6 text-orange-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Data Region</p>
                <p className="text-2xl font-bold text-purple-600">{tenantInfo?.data_region}</p>
              </div>
              <Globe className="h-6 w-6 text-purple-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="onboarding">Onboarding</TabsTrigger>
          <TabsTrigger value="reports">Reports</TabsTrigger>
          <TabsTrigger value="sla">SLA Monitor</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Tenant Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Settings className="h-5 w-5 mr-2" />
                  Tenant Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">Tenant Alias:</span>
                  <span className="font-mono">{tenantInfo?.alias}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Environment:</span>
                  <Badge variant="secondary">{tenantInfo?.environment}</Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">SLA Tier:</span>
                  <Badge className={getSLATierColor(tenantInfo?.sla_tier || 'demo')}>
                    {tenantInfo?.sla_tier?.toUpperCase()}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Billing:</span>
                  <Badge variant={tenantInfo?.billing_enabled ? 'default' : 'secondary'}>
                    {tenantInfo?.billing_enabled ? 'ENABLED' : 'DISABLED'}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Data Region:</span>
                  <span>{tenantInfo?.data_region}</span>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <FileText className="h-5 w-5 mr-2" />
                  Quick Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  onClick={() => handleExportReport('discrepancies')}
                  className="w-full justify-start"
                  variant="outline"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Export Discrepancies Report
                </Button>
                <Button
                  onClick={() => handleExportReport('audit_trail')}
                  className="w-full justify-start"
                  variant="outline"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Export Audit Trail
                </Button>
                <Button
                  onClick={() => handleExportReport('sla')}
                  className="w-full justify-start"
                  variant="outline"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Export SLA Report
                </Button>
                <Button
                  onClick={() => handleExportReport('residency_dr')}
                  className="w-full justify-start"
                  variant="outline"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Export Compliance Report
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="onboarding" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Environment Onboarding Status</CardTitle>
              <CardDescription>
                Track progression through sandbox → UAT → production environments
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {onboardingStatus.map((status, index) => (
                  <div key={status.environment} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(status.status)}
                      <div>
                        <h3 className="font-medium capitalize">{status.environment}</h3>
                        <p className="text-sm text-gray-600">
                          Last updated: {new Date(status.last_updated).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant={status.checklist_complete ? 'default' : 'secondary'}>
                        {status.checklist_complete ? 'Checklist Complete' : 'Checklist Pending'}
                      </Badge>
                      <Badge variant={
                        status.status === 'completed' ? 'default' :
                        status.status === 'in_progress' ? 'secondary' : 'outline'
                      }>
                        {status.status.replace('_', ' ').toUpperCase()}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="reports" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Regulatory Reports</CardTitle>
                <CardDescription>Download compliance and audit reports</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  onClick={() => handleExportReport('discrepancies')}
                  className="w-full justify-start"
                  variant="outline"
                >
                  <FileText className="h-4 w-4 mr-2" />
                  Discrepancies Report
                </Button>
                <Button
                  onClick={() => handleExportReport('audit_trail')}
                  className="w-full justify-start"
                  variant="outline"
                >
                  <Shield className="h-4 w-4 mr-2" />
                  Audit Trail Report
                </Button>
                <Button
                  onClick={() => handleExportReport('residency_dr')}
                  className="w-full justify-start"
                  variant="outline"
                >
                  <Database className="h-4 w-4 mr-2" />
                  Data Residency & DR Report
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Operational Reports</CardTitle>
                <CardDescription>Performance and operational metrics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  onClick={() => handleExportReport('sla')}
                  className="w-full justify-start"
                  variant="outline"
                >
                  <Activity className="h-4 w-4 mr-2" />
                  SLA Performance Report
                </Button>
                <Button
                  onClick={() => handleExportReport('billing')}
                  className="w-full justify-start"
                  variant="outline"
                >
                  <BarChart3 className="h-4 w-4 mr-2" />
                  Billing Reconciliation
                </Button>
                <Button
                  onClick={() => window.open('/grafana/bank-overview')}
                  className="w-full justify-start"
                  variant="outline"
                >
                  <Activity className="h-4 w-4 mr-2" />
                  Live Dashboards
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="sla" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>SLA Metrics</CardTitle>
                <CardDescription>Current month performance</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Uptime</span>
                    <span>{slaMetrics?.uptime}%</span>
                  </div>
                  <Progress value={slaMetrics?.uptime} className="h-2" />
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Response Time (Target: &lt;500ms)</span>
                    <span>{slaMetrics?.responseTime}ms</span>
                  </div>
                  <Progress
                    value={Math.max(0, 100 - (slaMetrics?.responseTime || 0) / 5)}
                    className="h-2"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Error Rate (Target: &lt;2%)</span>
                    <span>{slaMetrics?.errorRate}%</span>
                  </div>
                  <Progress
                    value={Math.max(0, 100 - (slaMetrics?.errorRate || 0) * 50)}
                    className="h-2"
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>SLA Targets</CardTitle>
                <CardDescription>Your {tenantInfo?.sla_tier} tier commitments</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span>Uptime Target:</span>
                  <span className="font-medium">99.0%</span>
                </div>
                <div className="flex justify-between">
                  <span>Response Time (P95):</span>
                  <span className="font-medium">&lt; 1000ms</span>
                </div>
                <div className="flex justify-between">
                  <span>Error Rate:</span>
                  <span className="font-medium">&lt; 5%</span>
                </div>
                <div className="flex justify-between">
                  <span>Support Hours:</span>
                  <span className="font-medium">Business Hours</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="security" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Shield className="h-5 w-5 mr-2" />
                  Security Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between items-center">
                  <span>mTLS Authentication:</span>
                  <Badge variant={tenantInfo?.environment === 'production' ? 'default' : 'secondary'}>
                    {tenantInfo?.environment === 'production' ? 'ENABLED' : 'DISABLED'}
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span>IP Whitelisting:</span>
                  <Badge variant={tenantInfo?.environment === 'production' ? 'default' : 'secondary'}>
                    {tenantInfo?.environment === 'production' ? 'ENABLED' : 'DISABLED'}
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span>Data Encryption:</span>
                  <Badge variant="default">ENABLED</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span>Network Isolation:</span>
                  <Badge variant="default">ENABLED</Badge>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Database className="h-5 w-5 mr-2" />
                  Data Residency
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span>Primary Region:</span>
                  <span className="font-medium">{tenantInfo?.data_region}</span>
                </div>
                <div className="flex justify-between">
                  <span>Backup Regions:</span>
                  <span className="font-medium">us-east-1b, us-east-1c</span>
                </div>
                <div className="flex justify-between">
                  <span>Last Backup:</span>
                  <span className="font-medium">2 hours ago</span>
                </div>
                <div className="flex justify-between">
                  <span>DR Test Status:</span>
                  <Badge variant="default">PASSED</Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default BankPilotDashboard;