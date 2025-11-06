import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Globe, Plus } from 'lucide-react';

const mockWebhooks = [
  { id: 'wh-001', url: 'https://api.partner.com/webhook', event: 'document.processed', status: 'active', lastTrigger: '2 min ago', successRate: '99.8%' },
  { id: 'wh-002', url: 'https://external.system/events', event: 'payment.completed', status: 'active', lastTrigger: '1 hour ago', successRate: '100%' },
];

export function PartnersWebhooks() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Webhooks</h2>
        <p className="text-muted-foreground">
          Configure webhook endpoints for real-time event notifications
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="w-5 h-5" />
            Webhook Endpoints
          </CardTitle>
          <CardDescription>Outbound event notifications</CardDescription>
          <Button className="mt-4 w-fit">
            <Plus className="w-4 h-4 mr-2" />
            Add Webhook
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockWebhooks.map((webhook) => (
              <div key={webhook.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{webhook.event}</p>
                  <p className="text-sm text-muted-foreground font-mono">{webhook.url}</p>
                  <p className="text-xs text-muted-foreground mt-1">Last triggered: {webhook.lastTrigger}</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-sm font-semibold text-success">{webhook.successRate}</p>
                    <p className="text-xs text-muted-foreground">success rate</p>
                  </div>
                  <Badge variant="default">{webhook.status}</Badge>
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

