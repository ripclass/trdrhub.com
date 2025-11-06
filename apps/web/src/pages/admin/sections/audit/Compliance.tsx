import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Shield, CheckCircle, AlertTriangle } from 'lucide-react';

const complianceChecks = [
  { name: 'GDPR Compliance', status: 'compliant', lastCheck: '2 hours ago', score: 98 },
  { name: 'SOC 2 Type II', status: 'compliant', lastCheck: '1 day ago', score: 95 },
  { name: 'ISO 27001', status: 'review', lastCheck: '3 days ago', score: 88 },
  { name: 'PCI DSS', status: 'compliant', lastCheck: '5 hours ago', score: 100 },
];

export function AuditCompliance() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Compliance Status</h2>
        <p className="text-muted-foreground">
          Compliance certifications and regulatory requirements tracking
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Compliance Checks
          </CardTitle>
          <CardDescription>Current compliance status across all frameworks</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {complianceChecks.map((check) => (
              <div key={check.name} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  {check.status === 'compliant' ? (
                    <CheckCircle className="w-5 h-5 text-success" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-warning" />
                  )}
                  <div>
                    <p className="font-medium text-foreground">{check.name}</p>
                    <p className="text-sm text-muted-foreground">Last checked: {check.lastCheck}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-lg font-semibold text-foreground">{check.score}%</p>
                    <p className="text-xs text-muted-foreground">compliance score</p>
                  </div>
                  <Badge variant={check.status === 'compliant' ? 'default' : 'secondary'}>
                    {check.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

