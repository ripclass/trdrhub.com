import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { DollarSign, Plus } from 'lucide-react';

const mockAdjustments = [
  { id: 'adj-001', company: 'Acme Corp', type: 'credit', amount: '$500', reason: 'Service disruption compensation', date: '2 days ago', status: 'applied' },
  { id: 'adj-002', company: 'Tech Solutions', type: 'charge', amount: '$200', reason: 'Additional API usage', date: '5 days ago', status: 'applied' },
  { id: 'adj-003', company: 'Global Trading', type: 'credit', amount: '$1,000', reason: 'Annual discount', date: '1 week ago', status: 'pending' },
];

export function BillingAdjustments() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Billing Adjustments</h2>
        <p className="text-muted-foreground">
          Manage credits, refunds, and manual billing adjustments
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="w-5 h-5" />
            Recent Adjustments
          </CardTitle>
          <CardDescription>Manual billing modifications and credits</CardDescription>
          <Button className="mt-4 w-fit">
            <Plus className="w-4 h-4 mr-2" />
            New Adjustment
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockAdjustments.map((adjustment) => (
              <div key={adjustment.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{adjustment.company}</p>
                  <p className="text-sm text-muted-foreground mb-2">{adjustment.reason}</p>
                  <span className="text-xs text-muted-foreground">{adjustment.date}</span>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={adjustment.type === 'credit' ? 'default' : 'secondary'}>
                    {adjustment.type}
                  </Badge>
                  <p className={`text-lg font-semibold ${adjustment.type === 'credit' ? 'text-success' : 'text-foreground'}`}>
                    {adjustment.type === 'credit' ? '-' : '+'}{adjustment.amount}
                  </p>
                  <Badge variant={adjustment.status === 'applied' ? 'default' : 'outline'}>
                    {adjustment.status}
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

