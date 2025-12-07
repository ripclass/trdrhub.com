/**
 * History Tab Component
 * Shows submission history for the LC to banks
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { History, Building2, Loader2 } from "lucide-react";
import { SubmissionHistoryCard } from "../SubmissionHistoryCard";
import type { BankSubmissionRead } from "@/api/exporter";

interface HistoryTabProps {
  submissionsLoading: boolean;
  submissionsData: { items: BankSubmissionRead[] } | undefined;
  validationSessionId: string;
}

export function HistoryTab({
  submissionsLoading,
  submissionsData,
  validationSessionId,
}: HistoryTabProps) {
  return (
    <Card className="shadow-soft border-0">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <History className="w-5 h-5" />
          Submission History
        </CardTitle>
        <CardDescription>
          Track all submissions of this LC to banks
        </CardDescription>
      </CardHeader>
      <CardContent>
        {submissionsLoading ? (
          <div className="text-center py-12">
            <Loader2 className="w-8 h-8 mx-auto text-muted-foreground mb-4 animate-spin" />
            <p className="text-muted-foreground">Loading submission history...</p>
          </div>
        ) : !submissionsData || submissionsData.items.length === 0 ? (
          <div className="text-center py-12">
            <Building2 className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground mb-2">No submissions yet</p>
            <p className="text-sm text-muted-foreground">
              Submit this LC to a bank to track its submission history
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {submissionsData.items.map((submission) => (
              <SubmissionHistoryCard 
                key={submission.id} 
                submission={submission}
                validationSessionId={validationSessionId}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
