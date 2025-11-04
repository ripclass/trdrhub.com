import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Clock, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { bankApi, BankJob } from "@/api/bank";
import { sanitizeDisplayText } from "@/lib/sanitize";

interface ProcessingQueueProps {
  onJobComplete?: () => void;
}

export function ProcessingQueue({ onJobComplete }: ProcessingQueueProps) {
  const [completedJobs, setCompletedJobs] = useState<Set<string>>(new Set());

  // Poll for jobs every 2 seconds
  const { data: jobsData, isLoading } = useQuery({
    queryKey: ['bank-jobs'],
    queryFn: () => bankApi.getJobs({ status: undefined }), // Get all statuses
    refetchInterval: 2000, // Poll every 2 seconds
  });

  const jobs: BankJob[] = jobsData?.jobs || [];

  // Filter to only pending/processing jobs
  const activeJobs = jobs.filter(
    (job) => job.status === "pending" || job.status === "processing" || job.status === "created"
  );

  // Check for newly completed jobs
  useEffect(() => {
    const completed = jobs.filter(
      (job) => job.status === "completed" && !completedJobs.has(job.id)
    );
    
    if (completed.length > 0 && onJobComplete) {
      completed.forEach((job) => setCompletedJobs((prev) => new Set(prev).add(job.id)));
      // Trigger callback after a short delay
      const timeout = setTimeout(() => {
        onJobComplete();
      }, 1000);
      return () => clearTimeout(timeout);
    }
  }, [jobs, completedJobs, onJobComplete]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending":
      case "created":
        return <Badge variant="secondary">Pending</Badge>;
      case "processing":
        return <Badge variant="default" className="bg-blue-500">Processing</Badge>;
      case "completed":
        return <Badge variant="default" className="bg-green-500">Completed</Badge>;
      case "failed":
        return <Badge variant="destructive">Error</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "pending":
      case "created":
        return <Clock className="w-5 h-5 text-muted-foreground" />;
      case "processing":
        return <Clock className="w-5 h-5 text-blue-500 animate-spin" />;
      case "completed":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "failed":
        return <XCircle className="w-5 h-5 text-destructive" />;
      default:
        return <Clock className="w-5 h-5 text-muted-foreground" />;
    }
  };

  if (isLoading && activeJobs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Processing Queue</CardTitle>
          <CardDescription>Loading jobs...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <Clock className="w-12 h-12 mx-auto text-muted-foreground mb-4 animate-spin" />
            <p className="text-muted-foreground">Loading...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (activeJobs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Processing Queue</CardTitle>
          <CardDescription>
            LC validations will appear here once submitted
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No jobs in queue</p>
            <p className="text-sm text-muted-foreground mt-2">
              Upload LC documents to start validation
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Processing Queue</CardTitle>
        <CardDescription>
          {activeJobs.length} job(s) in progress
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {activeJobs.map((job) => {
            const clientName = sanitizeDisplayText(job.client_name, "Unknown Client");
            const lcNumber = sanitizeDisplayText(job.lc_number, "");
            const submittedAt = job.submitted_at ? new Date(job.submitted_at) : new Date();
            const completedAt = job.completed_at ? new Date(job.completed_at) : undefined;

            return (
              <div
                key={job.id}
                className="p-4 border rounded-lg bg-card space-y-3"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    {getStatusIcon(job.status)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-semibold text-foreground">
                          {clientName}
                        </h4>
                        {getStatusBadge(job.status)}
                      </div>
                      {lcNumber && (
                        <p className="text-sm text-muted-foreground">
                          LC: {lcNumber}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground mt-1">
                        Submitted: {submittedAt.toLocaleString()}
                      </p>
                    </div>
                  </div>
                </div>

                {job.status === "processing" && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Processing...</span>
                      <span className="text-muted-foreground">{job.progress}%</span>
                    </div>
                    <Progress value={job.progress} className="h-2" />
                  </div>
                )}

                {completedAt && (
                  <p className="text-xs text-muted-foreground">
                    Completed: {completedAt.toLocaleString()}
                  </p>
                )}

                {job.status === "failed" && (
                  <div className="flex items-center gap-2 text-sm text-destructive">
                    <AlertCircle className="w-4 h-4" />
                    <span>Validation failed. Please try again.</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
