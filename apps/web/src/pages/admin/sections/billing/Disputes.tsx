import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle } from 'lucide-react';

const mockDisputes = [
  { id: 'disp-001', company: 'Beta Industries', amount: '$1,499', reason: 'Incorrect invoice amount', date: '1 day ago', status: 'open' },
  { id: 'disp-002', company: 'Gamma Solutions', amount: '$299', reason: 'Service not rendered', date: '3 days ago', status: 'investigating' },
];

export function BillingDisputes() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Billing Disputes</h2>
        <p className="text-muted-foreground">
          Manage and resolve billing disputes and chargebacks
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            Active Disputes
          </CardTitle>
          <CardDescription>Disputes requiring attention</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockDisputes.map((dispute) => (
              <div key={dispute.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{dispute.company}</p>
                  <p className="text-sm text-muted-foreground mb-2">{dispute.reason}</p>
                  <span className="text-xs text-muted-foreground">{dispute.date}</span>
                </div>
                <div className="flex items-center gap-3">
                  <p className="text-lg font-semibold text-destructive">{dispute.amount}</p>
                  <Badge variant={dispute.status === 'open' ? 'destructive' : 'secondary'}>
                    {dispute.status}
                  </Badge>
                  <Button variant="outline" size="sm">
                    Resolve
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

