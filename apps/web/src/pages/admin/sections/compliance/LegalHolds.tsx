import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Folder, Plus } from 'lucide-react';

const mockHolds = [
  { id: 'hold-001', case: 'Investigation #2024-05', entity: 'Acme Corp', records: 1234, created: '15 days ago', status: 'active' },
  { id: 'hold-002', case: 'Audit #2024-01', entity: 'Global Trading', records: 567, created: '45 days ago', status: 'active' },
];

export function ComplianceLegalHolds() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Legal Holds</h2>
        <p className="text-muted-foreground">
          Manage legal holds and preservation requests
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Folder className="w-5 h-5" />
            Active Legal Holds
          </CardTitle>
          <CardDescription>Data preservation orders</CardDescription>
          <Button className="mt-4 w-fit">
            <Plus className="w-4 h-4 mr-2" />
            New Hold
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockHolds.map((hold) => (
              <div key={hold.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{hold.case}</p>
                  <p className="text-sm text-muted-foreground">{hold.entity} • {hold.records} records • Created {hold.created}</p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="default">{hold.status}</Badge>
                  <Button variant="outline" size="sm">
                    View
                  </Button>
                  <Button variant="outline" size="sm" className="text-destructive">
                    Release
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

