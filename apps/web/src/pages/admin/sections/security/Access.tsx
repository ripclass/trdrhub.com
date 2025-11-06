import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Lock, Plus, Copy, Trash2 } from 'lucide-react';

const mockApiKeys = [
  { id: 'key-001', name: 'Production API Key', key: 'lc_prod_***************abc123', created: '30 days ago', lastUsed: '5 min ago', status: 'active' },
  { id: 'key-002', name: 'Staging API Key', key: 'lc_stag_***************def456', created: '15 days ago', lastUsed: '2 hours ago', status: 'active' },
  { id: 'key-003', name: 'Legacy Integration', key: 'lc_prod_***************ghi789', created: '90 days ago', lastUsed: '30 days ago', status: 'inactive' },
];

export function SecurityAccess() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">API Keys</h2>
        <p className="text-muted-foreground">
          Manage API keys and access tokens for system integrations
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="w-5 h-5" />
            API Key Management
          </CardTitle>
          <CardDescription>Active API keys and their usage</CardDescription>
          <Button className="mt-4 w-fit">
            <Plus className="w-4 h-4 mr-2" />
            Generate New Key
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockApiKeys.map((apiKey) => (
              <div key={apiKey.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{apiKey.name}</p>
                  <p className="text-sm font-mono text-muted-foreground mb-2">{apiKey.key}</p>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span>Created: {apiKey.created}</span>
                    <span>•</span>
                    <span>Last used: {apiKey.lastUsed}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={apiKey.status === 'active' ? 'default' : 'secondary'}>
                    {apiKey.status}
                  </Badge>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      <Copy className="w-4 h-4" />
                    </Button>
                    <Button variant="outline" size="sm" className="text-destructive">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

