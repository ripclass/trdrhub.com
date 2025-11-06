import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Zap, RefreshCw, Trash2, Eye } from 'lucide-react';

const mockJobs = [
  { id: 'job-001', type: 'Document Processing', status: 'completed', duration: '2.3s', time: '2 min ago' },
  { id: 'job-002', type: 'Email Notification', status: 'running', duration: '1.1s', time: '5 min ago' },
  { id: 'job-003', type: 'Report Generation', status: 'failed', duration: '8.2s', time: '10 min ago' },
  { id: 'job-004', type: 'Data Backup', status: 'queued', duration: '-', time: '15 min ago' },
];

export function OpsJobs() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Jobs & Queue</h2>
        <p className="text-muted-foreground">
          Monitor and manage background jobs and queue processing
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="w-5 h-5" />
            Recent Jobs
          </CardTitle>
          <CardDescription>Latest background job executions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockJobs.map((job) => (
              <div key={job.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <p className="font-medium text-foreground">{job.type}</p>
                  <p className="text-sm text-muted-foreground">ID: {job.id} • Duration: {job.duration}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground">{job.time}</span>
                  <Badge 
                    variant={
                      job.status === 'completed' ? 'default' : 
                      job.status === 'running' ? 'secondary' : 
                      job.status === 'failed' ? 'destructive' : 'outline'
                    }
                  >
                    {job.status}
                  </Badge>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      <Eye className="w-4 h-4" />
                    </Button>
                    {job.status === 'failed' && (
                      <Button variant="outline" size="sm">
                        <RefreshCw className="w-4 h-4" />
                      </Button>
                    )}
                    {job.status === 'queued' && (
                      <Button variant="outline" size="sm">
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
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

