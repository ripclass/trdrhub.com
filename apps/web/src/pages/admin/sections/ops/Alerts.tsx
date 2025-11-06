import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

const mockAlerts = [
  { id: 'alert-001', title: 'High CPU Usage', severity: 'warning', message: 'API Gateway CPU at 85%', time: '5 min ago', status: 'active' },
  { id: 'alert-002', title: 'Failed Jobs', severity: 'critical', message: '3 jobs failed in last hour', time: '12 min ago', status: 'active' },
];

export function OpsAlerts() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">System Alerts</h2>
        <p className="text-muted-foreground">
          Active alerts and system notifications requiring attention
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            Active Alerts
          </CardTitle>
          <CardDescription>2 alerts requiring attention</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockAlerts.map((alert) => (
              <div key={alert.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  {alert.severity === 'critical' ? (
                    <XCircle className="w-5 h-5 text-destructive" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-warning" />
                  )}
                  <div>
                    <p className="font-medium text-foreground">{alert.title}</p>
                    <p className="text-sm text-muted-foreground">{alert.message}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground">{alert.time}</span>
                  <Badge variant={alert.severity === 'critical' ? 'destructive' : 'secondary'}>
                    {alert.severity}
                  </Badge>
                  <Button variant="outline" size="sm">
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Acknowledge
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

