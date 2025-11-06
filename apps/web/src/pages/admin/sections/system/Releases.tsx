import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { FileText } from 'lucide-react';

const mockReleases = [
  { version: 'v2.5.0', date: '2 days ago', type: 'major', changes: ['New dashboard layout', 'Advanced analytics', '5 bug fixes'], status: 'deployed' },
  { version: 'v2.4.3', date: '1 week ago', type: 'patch', changes: ['Security updates', 'Performance improvements'], status: 'deployed' },
  { version: 'v2.4.2', date: '2 weeks ago', type: 'patch', changes: ['Bug fixes', 'UI tweaks'], status: 'deployed' },
];

export function SystemReleases() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">System Releases</h2>
        <p className="text-muted-foreground">
          Track platform releases and deployment history
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Release History
          </CardTitle>
          <CardDescription>Recent platform updates and deployments</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {mockReleases.map((release) => (
              <div key={release.version} className="p-4 border rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <p className="font-mono font-semibold text-foreground">{release.version}</p>
                    <Badge variant={release.type === 'major' ? 'default' : 'outline'}>
                      {release.type}
                    </Badge>
                    <Badge variant="secondary">{release.status}</Badge>
                  </div>
                  <span className="text-sm text-muted-foreground">{release.date}</span>
                </div>
                <ul className="space-y-1">
                  {release.changes.map((change, idx) => (
                    <li key={idx} className="text-sm text-muted-foreground flex items-center gap-2">
                      <span className="text-primary">•</span> {change}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

