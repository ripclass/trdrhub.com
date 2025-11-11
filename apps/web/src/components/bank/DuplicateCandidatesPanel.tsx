/**
 * Duplicate Candidates Panel Component
 * Shows duplicate candidates for a validation session with similarity scores
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Copy,
  ExternalLink,
  Merge,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { format } from "date-fns";
import { bankDuplicatesApi, type DuplicateCandidate } from "@/api/bank";
import { useNavigate } from "react-router-dom";

interface DuplicateCandidatesPanelProps {
  sessionId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onMerge?: (candidate: DuplicateCandidate) => void;
}

export function DuplicateCandidatesPanel({
  sessionId,
  open,
  onOpenChange,
  onMerge,
}: DuplicateCandidatesPanelProps) {
  const { toast } = useToast();
  const navigate = useNavigate();

  const { data, isLoading, error } = useQuery({
    queryKey: ['duplicate-candidates', sessionId],
    queryFn: () => bankDuplicatesApi.getCandidates(sessionId, 0.7, 10),
    enabled: open && !!sessionId,
  });

  const handleViewSession = (candidateSessionId: string) => {
    navigate(`/lcopilot/bank-dashboard/results/${candidateSessionId}`);
    onOpenChange(false);
  };

  const handleMerge = (candidate: DuplicateCandidate) => {
    if (onMerge) {
      onMerge(candidate);
    }
  };

  const getSimilarityColor = (score: number) => {
    if (score >= 0.85) return "text-red-600";
    if (score >= 0.70) return "text-orange-600";
    return "text-yellow-600";
  };

  const getSimilarityBadgeVariant = (score: number): "default" | "secondary" | "destructive" => {
    if (score >= 0.85) return "destructive";
    if (score >= 0.70) return "default";
    return "secondary";
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Duplicate Candidates</DialogTitle>
          <DialogDescription>
            Sessions with similar LC data. Higher similarity scores indicate likely duplicates.
          </DialogDescription>
        </DialogHeader>

        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading candidates...</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-4 bg-destructive/10 text-destructive rounded-lg">
            <AlertCircle className="h-5 w-5" />
            <span>Failed to load duplicate candidates. Please try again.</span>
          </div>
        )}

        {data && data.candidates.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <Copy className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No duplicate candidates found.</p>
            <p className="text-sm mt-2">This LC appears to be unique.</p>
          </div>
        )}

        {data && data.candidates.length > 0 && (
          <div className="space-y-4">
            {data.candidates.map((candidate) => (
              <div
                key={candidate.session_id}
                className="border rounded-lg p-4 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="font-semibold">{candidate.lc_number}</h4>
                      {candidate.client_name && (
                        <span className="text-sm text-muted-foreground">
                          {candidate.client_name}
                        </span>
                      )}
                    </div>
                    {candidate.completed_at && (
                      <p className="text-xs text-muted-foreground">
                        Completed: {format(new Date(candidate.completed_at), "MMM dd, yyyy HH:mm")}
                      </p>
                    )}
                  </div>
                  <Badge
                    variant={getSimilarityBadgeVariant(candidate.similarity_score)}
                    className="ml-2"
                  >
                    {(candidate.similarity_score * 100).toFixed(0)}% match
                  </Badge>
                </div>

                {/* Similarity Score Progress */}
                <div className="mb-3">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-muted-foreground">Overall Similarity</span>
                    <span className={getSimilarityColor(candidate.similarity_score)}>
                      {(candidate.similarity_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <Progress value={candidate.similarity_score * 100} className="h-2" />
                </div>

                {/* Detailed Similarity Scores */}
                {(candidate.content_similarity || candidate.metadata_similarity) && (
                  <div className="grid grid-cols-2 gap-4 mb-3 text-xs">
                    {candidate.content_similarity !== undefined && (
                      <div>
                        <span className="text-muted-foreground">Content: </span>
                        <span className="font-medium">
                          {(candidate.content_similarity * 100).toFixed(0)}%
                        </span>
                      </div>
                    )}
                    {candidate.metadata_similarity !== undefined && (
                      <div>
                        <span className="text-muted-foreground">Metadata: </span>
                        <span className="font-medium">
                          {(candidate.metadata_similarity * 100).toFixed(0)}%
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {/* Field Matches Preview */}
                {candidate.field_matches && Object.keys(candidate.field_matches).length > 0 && (
                  <div className="mb-3">
                    <p className="text-xs font-medium mb-1">Matching Fields:</p>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(candidate.field_matches)
                        .filter(([_, match]: [string, any]) => match.score > 0.8)
                        .slice(0, 5)
                        .map(([field]) => (
                          <Badge key={field} variant="outline" className="text-xs">
                            {field.replace(/_/g, ' ')}
                          </Badge>
                        ))}
                      {Object.keys(candidate.field_matches).length > 5 && (
                        <Badge variant="outline" className="text-xs">
                          +{Object.keys(candidate.field_matches).length - 5} more
                        </Badge>
                      )}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-2 pt-2 border-t">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleViewSession(candidate.session_id)}
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    View Session
                  </Button>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => handleMerge(candidate)}
                  >
                    <Merge className="h-4 w-4 mr-2" />
                    Merge
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

