import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Search, Download, Filter } from 'lucide-react';

const mockLogs = [
  { id: 'log-001', user: 'admin@lcopilot.com', action: 'User Login', resource: 'Auth', status: 'success', time: '2 min ago' },
  { id: 'log-002', user: 'ops@lcopilot.com', action: 'Service Restart', resource: 'API Gateway', status: 'success', time: '15 min ago' },
  { id: 'log-003', user: 'security@lcopilot.com', action: 'Access Key Revoked', resource: 'API Key #1234', status: 'success', time: '1 hour ago' },
  { id: 'log-004', user: 'finance@lcopilot.com', action: 'Plan Changed', resource: 'Company ABC', status: 'success', time: '2 hours ago' },
];

export function AuditLogs() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Audit Logs</h2>
        <p className="text-muted-foreground">
          Complete audit trail of all administrative actions and system events
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="w-5 h-5" />
            Audit Trail
          </CardTitle>
          <CardDescription>Filter and search audit logs</CardDescription>
          <div className="flex gap-2 mt-4">
            <Input placeholder="Search logs..." className="max-w-sm" />
            <Button variant="outline" size="sm">
              <Filter className="w-4 h-4 mr-2" />
              Filter
            </Button>
            <Button variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {mockLogs.map((log) => (
              <div key={log.id} className="flex items-center justify-between p-3 border rounded-lg text-sm">
                <div className="flex items-center gap-4">
                  <Badge variant={log.status === 'success' ? 'default' : 'destructive'}>
                    {log.status}
                  </Badge>
                  <span className="text-muted-foreground">{log.user}</span>
                  <span className="font-medium text-foreground">{log.action}</span>
                  <span className="text-muted-foreground">→ {log.resource}</span>
                </div>
                <span className="text-xs text-muted-foreground">{log.time}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

