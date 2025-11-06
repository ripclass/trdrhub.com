import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity, Server, Database, Zap, CheckCircle, XCircle } from 'lucide-react';

const mockServices = [
  { name: 'API Gateway', status: 'healthy', uptime: '99.98%', latency: '45ms' },
  { name: 'Database Primary', status: 'healthy', uptime: '99.99%', latency: '12ms' },
  { name: 'Queue Service', status: 'healthy', uptime: '99.95%', latency: '8ms' },
  { name: 'Storage', status: 'healthy', uptime: '100%', latency: '28ms' },
  { name: 'Cache (Redis)', status: 'healthy', uptime: '99.97%', latency: '3ms' },
];

const mockMetrics = [
  { label: 'CPU Usage', value: '34%', trend: 'stable' },
  { label: 'Memory Usage', value: '62%', trend: 'stable' },
  { label: 'Disk I/O', value: '18%', trend: 'down' },
  { label: 'Network I/O', value: '42%', trend: 'up' },
];

export function OpsMonitoring() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">System Monitoring</h2>
        <p className="text-muted-foreground">
          Real-time health and performance metrics for all platform services
        </p>
      </div>

      {/* Service Health */}
      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="w-5 h-5" />
            Service Health
          </CardTitle>
          <CardDescription>Status of all platform services</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockServices.map((service) => (
              <div key={service.name} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  {service.status === 'healthy' ? (
                    <CheckCircle className="w-5 h-5 text-success" />
                  ) : (
                    <XCircle className="w-5 h-5 text-destructive" />
                  )}
                  <div>
                    <p className="font-medium text-foreground">{service.name}</p>
                    <p className="text-sm text-muted-foreground">Uptime: {service.uptime}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm font-medium text-foreground">{service.latency}</p>
                    <p className="text-xs text-muted-foreground">avg latency</p>
                  </div>
                  <Badge variant={service.status === 'healthy' ? 'default' : 'destructive'}>
                    {service.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Resource Utilization */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card className="shadow-soft border-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Resource Utilization
            </CardTitle>
            <CardDescription>Current system resource usage</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockMetrics.map((metric) => (
                <div key={metric.label} className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">{metric.label}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-semibold text-foreground">{metric.value}</span>
                    <Badge variant="outline">{metric.trend}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-soft border-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="w-5 h-5" />
              Performance Metrics
            </CardTitle>
            <CardDescription>Last 24 hours</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Requests/sec</span>
                <span className="text-sm font-semibold text-foreground">1,245</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Error Rate</span>
                <span className="text-sm font-semibold text-success">0.02%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">P95 Latency</span>
                <span className="text-sm font-semibold text-foreground">245ms</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">P99 Latency</span>
                <span className="text-sm font-semibold text-foreground">580ms</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}

