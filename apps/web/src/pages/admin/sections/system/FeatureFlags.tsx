import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Flag } from 'lucide-react';

const mockFlags = [
  { id: 'flag-001', name: 'new_dashboard', description: 'Enable new dashboard layout', enabled: true, rollout: 100 },
  { id: 'flag-002', name: 'advanced_analytics', description: 'Advanced analytics features', enabled: true, rollout: 75 },
  { id: 'flag-003', name: 'ai_suggestions', description: 'AI-powered document suggestions', enabled: false, rollout: 0 },
  { id: 'flag-004', name: 'beta_api_v2', description: 'Beta API v2 endpoints', enabled: true, rollout: 25 },
];

export function SystemFeatureFlags() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Feature Flags</h2>
        <p className="text-muted-foreground">
          Control feature rollouts and experiments
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Flag className="w-5 h-5" />
            Feature Toggles
          </CardTitle>
          <CardDescription>Manage feature flags and progressive rollouts</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockFlags.map((flag) => (
              <div key={flag.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1 font-mono text-sm">{flag.name}</p>
                  <p className="text-sm text-muted-foreground">{flag.description}</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-sm font-semibold text-foreground">{flag.rollout}%</p>
                    <p className="text-xs text-muted-foreground">rollout</p>
                  </div>
                  <Badge variant={flag.enabled ? 'default' : 'secondary'}>
                    {flag.enabled ? 'enabled' : 'disabled'}
                  </Badge>
                  <Switch checked={flag.enabled} />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

