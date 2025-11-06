import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Database } from 'lucide-react';

const mockPolicies = [
  { id: 'ret-001', type: 'User Data', retention: '7 years', size: '1.2TB', lastPurge: '30 days ago', status: 'active' },
  { id: 'ret-002', type: 'Transaction Records', retention: '10 years', size: '3.5TB', lastPurge: '60 days ago', status: 'active' },
  { id: 'ret-003', type: 'Audit Logs', retention: '5 years', size: '500GB', lastPurge: '90 days ago', status: 'active' },
];

export function ComplianceRetention() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Data Retention</h2>
        <p className="text-muted-foreground">
          Configure data retention policies and automated purging
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            Retention Policies
          </CardTitle>
          <CardDescription>Active retention and purge policies</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockPolicies.map((policy) => (
              <div key={policy.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{policy.type}</p>
                  <p className="text-sm text-muted-foreground">Retention: {policy.retention} • Last purge: {policy.lastPurge}</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-sm font-semibold text-foreground">{policy.size}</p>
                    <p className="text-xs text-muted-foreground">stored</p>
                  </div>
                  <Badge variant="default">{policy.status}</Badge>
                  <Button variant="outline" size="sm">
                    Edit
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

