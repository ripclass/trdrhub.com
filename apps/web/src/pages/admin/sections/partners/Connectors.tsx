import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Webhook, Plus } from 'lucide-react';

const mockConnectors = [
  { id: 'conn-001', name: 'SWIFT Gateway', type: 'API', status: 'healthy', requests: '12.4K/day', latency: '45ms' },
  { id: 'conn-002', name: 'Customs Portal', type: 'SOAP', status: 'healthy', requests: '3.2K/day', latency: '120ms' },
];

export function PartnersConnectors() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Connectors</h2>
        <p className="text-muted-foreground">
          Manage API connectors and integration endpoints
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Webhook className="w-5 h-5" />
            Active Connectors
          </CardTitle>
          <CardDescription>API and service connectors</CardDescription>
          <Button className="mt-4 w-fit">
            <Plus className="w-4 h-4 mr-2" />
            Add Connector
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockConnectors.map((conn) => (
              <div key={conn.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{conn.name}</p>
                  <p className="text-sm text-muted-foreground">{conn.type} • {conn.requests} • {conn.latency} avg</p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="default">{conn.status}</Badge>
                  <Button variant="outline" size="sm">
                    Test
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

