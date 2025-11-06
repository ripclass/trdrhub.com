import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Clock, X } from 'lucide-react';

const mockSessions = [
  { id: 'sess-001', user: 'admin@lcopilot.com', device: 'Chrome on Windows', location: 'New York, US', started: '2 hours ago', lastActive: '2 min ago', status: 'active' },
  { id: 'sess-002', user: 'ops@lcopilot.com', device: 'Firefox on macOS', location: 'San Francisco, US', started: '5 hours ago', lastActive: '30 min ago', status: 'active' },
  { id: 'sess-003', user: 'security@lcopilot.com', device: 'Safari on iOS', location: 'London, UK', started: '1 day ago', lastActive: '2 hours ago', status: 'active' },
];

export function SecuritySessions() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Active Sessions</h2>
        <p className="text-muted-foreground">
          Monitor and manage active user sessions across the platform
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5" />
            Session Management
          </CardTitle>
          <CardDescription>Currently active user sessions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockSessions.map((session) => (
              <div key={session.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground mb-1">{session.user}</p>
                  <p className="text-sm text-muted-foreground mb-2">{session.device} • {session.location}</p>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span>Started: {session.started}</span>
                    <span>•</span>
                    <span>Last active: {session.lastActive}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="default">{session.status}</Badge>
                  <Button variant="outline" size="sm" className="text-destructive">
                    <X className="w-4 h-4 mr-2" />
                    Revoke
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

