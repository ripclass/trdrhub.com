import * as React from "react";
import { FileCheck, AlertTriangle, FileText, Sparkles, Plus, Eye, Trash2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { getWorkflowPrimaryLabel, type WorkflowDetectionSummary } from "@/lib/exporter/workflowDetection";
import type { LcClassificationRequiredDocument } from "@/types/lcopilot";

export interface LCIntakeState {
  status: "idle" | "uploading" | "resolved" | "invalid" | "ambiguous";
  file: File | null;
  message?: string;
  continuationAllowed?: boolean;
  isLc?: boolean;
  jobId?: string;
  lcSummary?: Record<string, any>;
  lcDetection?: {
    lc_type?: string;
    confidence?: number;
    reason?: string;
    is_draft?: boolean;
    source?: string;
    confidence_mode?: string;
    detection_basis?: string;
  };
  requiredDocumentTypes?: string[];
  documentsRequired?: string[];
  requiredDocumentsDetailed?: LcClassificationRequiredDocument[];
  requirementConditions?: string[];
  unmappedRequirements?: string[];
  specialConditions?: string[];
  detectedDocuments?: Array<{ type: string; filename?: string; document_type_resolution?: string }>;
  error?: {
    error_code?: string;
    title?: string;
    message?: string;
    detail?: string;
    action?: string;
    redirect_url?: string;
    help_text?: string;
  };
}

function formatFileSize(bytes: number) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

export interface LcIntakeCardProps {
  state: LCIntakeState;
  isProcessing: boolean;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onClear: () => void;
}

export function LcIntakeCard({ state, isProcessing, onFileChange, onClear }: LcIntakeCardProps) {
  const { toast } = useToast();
  const isLCResolved = state.status === "resolved" && !!state.continuationAllowed;
  const isLcResolving = state.status === "uploading";

  return (
    <Card className="mb-6 shadow-soft border-0">
      <CardHeader>
        <CardTitle>Step 1 — Upload Letter of Credit</CardTitle>
        <CardDescription>
          Start with the LC. We’ll detect the required supporting documents and unlock the bulk uploader below.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <input
          id="lc-intake-upload"
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          className="hidden"
          onChange={onFileChange}
        />

        {!state.file ? (
          <div
            className={cn(
              "border-2 border-dashed rounded-lg p-5 text-center transition-colors",
              isLcResolving
                ? "border-exporter bg-exporter/5 cursor-default"
                : "border-gray-200 hover:border-exporter/50 hover:bg-secondary/20 cursor-pointer"
            )}
            onClick={() => {
              if (isLcResolving || isProcessing) return;
              const input = document.getElementById("lc-intake-upload") as HTMLInputElement | null;
              input?.click();
            }}
            role="button"
            tabIndex={isLcResolving || isProcessing ? -1 : 0}
            onKeyDown={(e) => {
              if (isLcResolving || isProcessing) return;
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                const input = document.getElementById("lc-intake-upload") as HTMLInputElement | null;
                input?.click();
              }
            }}
          >
            <div className="flex flex-col items-center gap-3">
              <div className="p-3 rounded-full bg-exporter/10">
                <Sparkles className="w-6 h-6 text-exporter" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-foreground">
                  {isLcResolving ? "Resolving Letter of Credit…" : "Upload Letter of Credit"}
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                  {isLcResolving
                    ? "Checking the LC, detecting workflow, and extracting required supporting documents."
                    : "Click anywhere in this box or use the button below."}
                </p>
              </div>
              <div onClick={(e) => e.stopPropagation()}>
                <Button
                  type="button"
                  variant="outline"
                  disabled={isLcResolving || isProcessing}
                  onClick={() => {
                    const input = document.getElementById("lc-intake-upload") as HTMLInputElement | null;
                    input?.click();
                  }}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Choose LC File
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Uploaded-LC card — matches the supporting-doc card shape below */}
            <div className="flex items-center gap-4 p-4 bg-secondary/20 rounded-lg border border-gray-200/50">
              <div className="flex-shrink-0">
                <div
                  className={cn(
                    "p-2 rounded-lg",
                    isLCResolved
                      ? "bg-success/10"
                      : state.status === "invalid"
                      ? "bg-destructive/10"
                      : "bg-exporter/10",
                  )}
                >
                  {isLCResolved ? (
                    <FileCheck className="w-5 h-5 text-success" />
                  ) : state.status === "invalid" ? (
                    <AlertTriangle className="w-5 h-5 text-destructive" />
                  ) : (
                    <FileText className="w-5 h-5 text-exporter" />
                  )}
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <h5 className="font-medium text-foreground truncate">{state.file.name}</h5>
                  <span className="text-sm text-muted-foreground flex-shrink-0">
                    {formatFileSize(state.file.size)}
                  </span>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge
                    variant={
                      isLCResolved
                        ? "default"
                        : state.status === "uploading"
                        ? "outline"
                        : "secondary"
                    }
                    className="text-xs"
                  >
                    {state.status === "uploading"
                      ? "Checking LC…"
                      : isLCResolved
                      ? "LC Resolved"
                      : state.status}
                  </Badge>
                  {state.lcDetection && (
                    <Badge variant="outline" className="text-xs font-medium">
                      {getWorkflowPrimaryLabel(state.lcDetection as WorkflowDetectionSummary)}
                    </Badge>
                  )}
                  {state.lcDetection?.is_draft && (
                    <Badge variant="outline" className="text-xs">
                      Draft LC
                    </Badge>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    if (state.file && state.file.size > 0) {
                      const fileUrl = URL.createObjectURL(state.file);
                      window.open(fileUrl, "_blank");
                      setTimeout(() => URL.revokeObjectURL(fileUrl), 60_000);
                    } else {
                      toast({
                        title: "Preview Unavailable",
                        description: "This LC file cannot be previewed.",
                        variant: "destructive",
                      });
                    }
                  }}
                  disabled={state.status === "uploading"}
                  title="Preview LC"
                >
                  <Eye className="w-4 h-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onClear}
                  disabled={isLcResolving || isProcessing}
                  title="Remove LC"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>

            {(state.message || state.error?.message) && (
              <div
                className={cn(
                  "rounded-md p-3 text-sm border",
                  isLCResolved
                    ? "bg-green-50 border-green-200 text-green-800"
                    : "bg-amber-50 border-amber-200 text-amber-800",
                )}
              >
                {state.error?.message || state.message}
              </div>
            )}

            {Object.keys(state.lcSummary || {}).length > 0 && (
              <div className="grid md:grid-cols-3 gap-3 text-sm">
                {Object.entries(state.lcSummary || {})
                  .slice(0, 6)
                  .map(([key, value]) => (
                    <div
                      key={key}
                      className="rounded bg-background p-3 border border-gray-200/60"
                    >
                      <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
                        {key.replace(/_/g, " ")}
                      </p>
                      <p className="font-medium text-foreground break-words">
                        {String(value)}
                      </p>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
