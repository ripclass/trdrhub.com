import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Building, Plus } from 'lucide-react';

const mockPartners = [
  { id: 'part-001', name: 'Swift Network', type: 'Banking', status: 'active', integrations: 5, lastSync: '2 min ago' },
  { id: 'part-002', name: 'TradeConnect', type: 'Trade Finance', status: 'active', integrations: 3, lastSync: '1 hour ago' },
  { id: 'part-003', name: 'CustomsHub', type: 'Customs', status: 'inactive', integrations: 1, lastSync: '5 days ago' },
];

export function PartnersRegistry() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Partner Registry</h2>
        <p className="text-muted-foreground">
          Manage external partner integrations and connections
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building className="w-5 h-5" />
            Registered Partners
          </CardTitle>
          <CardDescription>Active partner integrations</CardDescription>
          <Button className="mt-4 w-fit">
            <Plus className="w-4 h-4 mr-2" />
            Add Partner
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockPartners.map((partner) => (
              <div key={partner.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{partner.name}</p>
                  <p className="text-sm text-muted-foreground">{partner.type} • {partner.integrations} integrations</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground">{partner.lastSync}</span>
                  <Badge variant={partner.status === 'active' ? 'default' : 'secondary'}>
                    {partner.status}
                  </Badge>
                  <Button variant="outline" size="sm">
                    Configure
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

