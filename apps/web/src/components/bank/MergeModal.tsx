/**
 * Merge Modal Component
 * Allows users to merge two validation sessions
 */
import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Loader2, AlertTriangle } from "lucide-react";
import { bankDuplicatesApi, type DuplicateCandidate, type MergeRequest } from "@/api/bank";

interface MergeModalProps {
  sourceSessionId: string;
  candidate: DuplicateCandidate;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function MergeModal({
  sourceSessionId,
  candidate,
  open,
  onOpenChange,
  onSuccess,
}: MergeModalProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [mergeType, setMergeType] = React.useState<string>("duplicate");
  const [mergeReason, setMergeReason] = React.useState<string>("");
  const [fieldsToMerge, setFieldsToMerge] = React.useState<Set<string>>(
    new Set(["extracted_data", "validation_results", "documents"])
  );

  const mergeMutation = useMutation({
    mutationFn: (request: MergeRequest) => bankDuplicatesApi.merge(request),
    onSuccess: () => {
      toast({
        title: "Sessions Merged",
        description: `Successfully merged session ${candidate.session_id} into ${sourceSessionId}.`,
      });
      queryClient.invalidateQueries({ queryKey: ['duplicate-candidates', sourceSessionId] });
      queryClient.invalidateQueries({ queryKey: ['bank-results'] });
      queryClient.invalidateQueries({ queryKey: ['merge-history', sourceSessionId] });
      queryClient.invalidateQueries({ queryKey: ['merge-history', candidate.session_id] });
      onOpenChange(false);
      onSuccess?.();
    },
    onError: (error: any) => {
      toast({
        title: "Merge Failed",
        description: error.message || "Failed to merge sessions. Please try again.",
        variant: "destructive",
      });
    },
  });

  const handleMerge = () => {
    const request: MergeRequest = {
      source_session_id: candidate.session_id,
      target_session_id: sourceSessionId,
      merge_type: mergeType as any,
      merge_reason: mergeReason || undefined,
      fields_to_merge: fieldsToMerge.size > 0 ? Array.from(fieldsToMerge) : undefined,
    };
    mergeMutation.mutate(request);
  };

  const toggleField = (field: string) => {
    const newFields = new Set(fieldsToMerge);
    if (newFields.has(field)) {
      newFields.delete(field);
    } else {
      newFields.add(field);
    }
    setFieldsToMerge(newFields);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Merge Sessions</DialogTitle>
          <DialogDescription>
            Merge session <strong>{candidate.lc_number}</strong> into the current session.
            This will combine data from both sessions.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Merge Type */}
          <div className="space-y-2">
            <Label htmlFor="merge-type">Merge Type</Label>
            <Select value={mergeType} onValueChange={setMergeType}>
              <SelectTrigger id="merge-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="duplicate">Duplicate</SelectItem>
                <SelectItem value="amendment">Amendment</SelectItem>
                <SelectItem value="correction">Correction</SelectItem>
                <SelectItem value="manual">Manual</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Merge Reason */}
          <div className="space-y-2">
            <Label htmlFor="merge-reason">Reason (Optional)</Label>
            <Textarea
              id="merge-reason"
              placeholder="Explain why these sessions should be merged..."
              value={mergeReason}
              onChange={(e) => setMergeReason(e.target.value)}
              rows={3}
            />
          </div>

          {/* Fields to Merge */}
          <div className="space-y-2">
            <Label>Fields to Merge</Label>
            <div className="space-y-2 border rounded-lg p-4">
              {[
                { id: "extracted_data", label: "Extracted Data", description: "LC metadata and extracted fields" },
                { id: "validation_results", label: "Validation Results", description: "Discrepancies and compliance scores" },
                { id: "documents", label: "Documents", description: "Uploaded documents and files" },
              ].map((field) => (
                <div key={field.id} className="flex items-start space-x-3">
                  <Checkbox
                    id={field.id}
                    checked={fieldsToMerge.has(field.id)}
                    onCheckedChange={() => toggleField(field.id)}
                  />
                  <div className="flex-1">
                    <Label
                      htmlFor={field.id}
                      className="font-medium cursor-pointer"
                    >
                      {field.label}
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      {field.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Warning */}
          <div className="flex items-start gap-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 mt-0.5" />
            <div className="flex-1 text-sm">
              <p className="font-medium text-yellow-800 dark:text-yellow-200 mb-1">
                Merge Warning
              </p>
              <p className="text-yellow-700 dark:text-yellow-300">
                Merging sessions will create a permanent record in the merge history.
                The source session data will be preserved but marked as merged.
              </p>
            </div>
          </div>

          {/* Similarity Info */}
          <div className="text-sm text-muted-foreground">
            <p>
              Similarity Score: <strong>{(candidate.similarity_score * 100).toFixed(1)}%</strong>
            </p>
            {candidate.content_similarity && (
              <p>
                Content Similarity: <strong>{(candidate.content_similarity * 100).toFixed(1)}%</strong>
              </p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleMerge}
            disabled={mergeMutation.isPending || fieldsToMerge.size === 0}
          >
            {mergeMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Merge Sessions
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

