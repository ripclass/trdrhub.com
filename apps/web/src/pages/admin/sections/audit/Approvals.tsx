import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CheckSquare, Check, X } from 'lucide-react';

const mockApprovals = [
  { id: 'appr-001', type: 'Plan Change', requester: 'sales@company.com', details: 'Upgrade to Enterprise plan', time: '1 hour ago', status: 'pending' },
  { id: 'appr-002', type: 'Data Deletion', requester: 'admin@company.com', details: 'Delete user data for GDPR compliance', time: '3 hours ago', status: 'pending' },
  { id: 'appr-003', type: 'API Access', requester: 'dev@company.com', details: 'Request elevated API permissions', time: '5 hours ago', status: 'pending' },
];

export function AuditApprovals() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Pending Approvals</h2>
        <p className="text-muted-foreground">
          Review and approve or reject pending administrative requests
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckSquare className="w-5 h-5" />
            Approval Queue
          </CardTitle>
          <CardDescription>3 requests awaiting approval</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockApprovals.map((approval) => (
              <div key={approval.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="secondary">{approval.type}</Badge>
                    <span className="text-xs text-muted-foreground">{approval.time}</span>
                  </div>
                  <p className="font-medium text-foreground">{approval.details}</p>
                  <p className="text-sm text-muted-foreground">Requested by: {approval.requester}</p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="text-success">
                    <Check className="w-4 h-4 mr-2" />
                    Approve
                  </Button>
                  <Button variant="outline" size="sm" className="text-destructive">
                    <X className="w-4 h-4 mr-2" />
                    Reject
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

