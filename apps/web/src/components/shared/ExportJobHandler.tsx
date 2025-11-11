/**
 * ExportJobHandler Component
 * Handles async export jobs with polling and progress display
 */
import * as React from "react";
import { useToast } from "@/hooks/use-toast";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Loader2, Download, CheckCircle2, XCircle } from "lucide-react";
import { bankApi } from "@/api/bank";

interface ExportJobHandlerProps {
  jobId: string | null;
  onComplete?: (downloadUrl: string) => void;
  onError?: () => void;
  onClear?: () => void;
}

export function ExportJobHandler({
  jobId,
  onComplete,
  onError,
  onClear,
}: ExportJobHandlerProps) {
  const { toast } = useToast();

  // Poll job status
  const { data: jobStatus, isLoading } = useQuery({
    queryKey: ['export-job', jobId],
    queryFn: () => bankApi.getExportJobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'COMPLETED' || data?.status === 'FAILED') {
        return false; // Stop polling when done
      }
      return 2000; // Poll every 2 seconds
    },
  });

  React.useEffect(() => {
    if (jobStatus?.status === 'COMPLETED' && jobStatus.download_url) {
      toast({
        title: "Export Ready",
        description: "Your export is ready for download.",
      });
      onComplete?.(jobStatus.download_url);
    } else if (jobStatus?.status === 'FAILED') {
      toast({
        title: "Export Failed",
        description: jobStatus.error || "Failed to generate export. Please try again.",
        variant: "destructive",
      });
      onError?.();
    }
  }, [jobStatus, toast, onComplete, onError]);

  if (!jobId) return null;

  const status = jobStatus?.status || 'PENDING';
  const progress = jobStatus?.progress || 0;

  return (
    <div className="flex items-center gap-4 p-4 bg-muted rounded-lg">
      <div className="flex-1">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium">
            {status === 'PENDING' && 'Preparing export...'}
            {status === 'PROCESSING' && 'Generating export...'}
            {status === 'COMPLETED' && 'Export ready!'}
            {status === 'FAILED' && 'Export failed'}
          </span>
          {status === 'COMPLETED' && (
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          )}
          {status === 'FAILED' && (
            <XCircle className="h-4 w-4 text-red-500" />
          )}
          {(status === 'PENDING' || status === 'PROCESSING') && (
            <Loader2 className="h-4 w-4 animate-spin" />
          )}
        </div>
        {(status === 'PENDING' || status === 'PROCESSING') && (
          <Progress value={progress} className="h-2" />
        )}
        {jobStatus?.total_rows && (
          <p className="text-xs text-muted-foreground mt-1">
            Processing {jobStatus.total_rows.toLocaleString()} rows...
          </p>
        )}
      </div>
      {status === 'COMPLETED' && jobStatus?.download_url && (
        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={() => {
              window.open(jobStatus.download_url, '_blank');
            }}
          >
            <Download className="h-4 w-4 mr-2" />
            Download
          </Button>
          {onClear && (
            <Button size="sm" variant="outline" onClick={onClear}>
              Close
            </Button>
          )}
        </div>
      )}
      {status === 'FAILED' && onClear && (
        <Button size="sm" variant="outline" onClick={onClear}>
          Close
        </Button>
      )}
    </div>
  );
}

