/**
 * SubmissionHistoryCard Component
 * 
 * Displays bank submission history with events timeline.
 */

import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { Building2, Receipt } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { exporterApi, type BankSubmissionRead } from "@/api/exporter";

interface SubmissionHistoryCardProps {
  submission: BankSubmissionRead;
  validationSessionId: string;
}

const getStatusVariant = (status: string) => {
  switch (status) {
    case 'accepted':
      return 'default';
    case 'rejected':
    case 'failed':
      return 'destructive';
    case 'cancelled':
      return 'secondary';
    default:
      return 'secondary';
  }
};

export function SubmissionHistoryCard({ 
  submission, 
  validationSessionId 
}: SubmissionHistoryCardProps) {
  const { data: eventsData } = useQuery({
    queryKey: ['exporter-submission-events', submission.id],
    queryFn: () => exporterApi.getSubmissionEvents(submission.id),
    enabled: !!submission.id,
  });
  
  return (
    <Card className="border-l-4 border-l-primary">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-muted-foreground" />
            <span className="font-medium">{submission.bank_name || 'Unknown Bank'}</span>
            <Badge variant={getStatusVariant(submission.status)}>
              {submission.status}
            </Badge>
          </div>
          {submission.receipt_url && (
            <Button variant="outline" size="sm" asChild>
              <a href={submission.receipt_url} target="_blank" rel="noopener noreferrer">
                <Receipt className="w-4 h-4 mr-2" />
                View Receipt
              </a>
            </Button>
          )}
        </div>
        <div className="text-sm text-muted-foreground space-y-1">
          <div>Submitted: {submission.submitted_at ? format(new Date(submission.submitted_at), "MMM d, yyyy 'at' HH:mm") : 'N/A'}</div>
          {submission.note && (
            <div className="mt-2 p-2 bg-muted rounded text-xs">
              <strong>Note:</strong> {submission.note}
            </div>
          )}
        </div>
        {eventsData && eventsData.items.length > 0 && (
          <div className="mt-4 pt-4 border-t">
            <Label className="text-xs text-muted-foreground mb-2 block">Event Timeline</Label>
            <div className="space-y-2">
              {eventsData.items.map((event) => (
                <div key={event.id} className="flex items-center gap-2 text-xs">
                  <div className="w-2 h-2 bg-primary rounded-full"></div>
                  <span className="text-muted-foreground">
                    {format(new Date(event.created_at), "MMM d, HH:mm")} - {event.event_type}
                    {event.actor_name && ` by ${event.actor_name}`}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

