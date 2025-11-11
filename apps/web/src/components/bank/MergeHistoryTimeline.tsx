/**
 * Merge History Timeline Component
 * Shows the merge history for a validation session
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, GitMerge, ExternalLink, User } from "lucide-react";
import { format } from "date-fns";
import { bankDuplicatesApi, type MergeHistoryItem } from "@/api/bank";
import { useNavigate } from "react-router-dom";

interface MergeHistoryTimelineProps {
  sessionId: string;
}

export function MergeHistoryTimeline({ sessionId }: MergeHistoryTimelineProps) {
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery({
    queryKey: ['merge-history', sessionId],
    queryFn: () => bankDuplicatesApi.getMergeHistory(sessionId),
    enabled: !!sessionId,
  });

  const getMergeTypeBadge = (mergeType: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      duplicate: "destructive",
      amendment: "default",
      correction: "secondary",
      manual: "outline",
    };
    return variants[mergeType] || "outline";
  };

  const getMergeTypeLabel = (mergeType: string) => {
    return mergeType.charAt(0).toUpperCase() + mergeType.slice(1);
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading merge history...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8">
          <p className="text-center text-muted-foreground">
            Failed to load merge history.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.merges.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Merge History</CardTitle>
          <CardDescription>No merge history for this session.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Merge History</CardTitle>
        <CardDescription>
          {data.total_count} merge{data.total_count !== 1 ? 's' : ''} recorded
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {data.merges.map((merge, index) => {
            const isSource = merge.source_session_id === sessionId;
            const otherSessionId = isSource ? merge.target_session_id : merge.source_session_id;
            const isMergedInto = !isSource;

            return (
              <div
                key={merge.id}
                className="flex gap-4 pb-4 border-b last:border-b-0 last:pb-0"
              >
                {/* Timeline Icon */}
                <div className="flex-shrink-0">
                  <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <GitMerge className="h-5 w-5 text-primary" />
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant={getMergeTypeBadge(merge.merge_type)}>
                          {getMergeTypeLabel(merge.merge_type)}
                        </Badge>
                        <span className="text-sm text-muted-foreground">
                          {format(new Date(merge.merged_at), "MMM dd, yyyy HH:mm")}
                        </span>
                      </div>
                      <p className="text-sm font-medium">
                        {isMergedInto
                          ? `Merged into session ${otherSessionId.slice(0, 8)}...`
                          : `Merged session ${otherSessionId.slice(0, 8)}... into this session`}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(`/lcopilot/bank-dashboard/results/${otherSessionId}`)}
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  </div>

                  {merge.merge_reason && (
                    <p className="text-sm text-muted-foreground mb-2">
                      {merge.merge_reason}
                    </p>
                  )}

                  {merge.fields_merged && Object.keys(merge.fields_merged).length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                      {Object.keys(merge.fields_merged).map((field) => (
                        <Badge key={field} variant="outline" className="text-xs">
                          {field.replace(/_/g, ' ')}
                        </Badge>
                      ))}
                    </div>
                  )}

                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <User className="h-3 w-3" />
                    <span>Merged by user {merge.merged_by.slice(0, 8)}...</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

