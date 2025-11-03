import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Clock, CheckCircle, XCircle, AlertCircle } from "lucide-react";

interface ProcessingJob {
  id: string;
  jobId: string;
  clientName: string;
  lcNumber?: string;
  status: "pending" | "processing" | "completed" | "error";
  progress: number;
  submittedAt: Date;
  completedAt?: Date;
}

interface ProcessingQueueProps {
  onJobComplete?: () => void;
}

export function ProcessingQueue({ onJobComplete }: ProcessingQueueProps) {
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [isPolling, setIsPolling] = useState(false);

  // Load jobs from localStorage and simulate progress
  useEffect(() => {
    const loadJobs = () => {
      const stored = localStorage.getItem("bank_validation_jobs");
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          const loaded = parsed.map((j: any) => ({
            ...j,
            submittedAt: new Date(j.submittedAt),
            completedAt: j.completedAt ? new Date(j.completedAt) : undefined,
          }));

          setJobs(loaded);
        } catch (e) {
          console.error("Failed to load jobs:", e);
        }
      }
    };

    loadJobs();
    setIsPolling(true);

    // Poll for updates every 2 seconds and simulate progress
    const interval = setInterval(() => {
      loadJobs();

      // Update job progress (simulate)
      setJobs((prevJobs) => {
        const updated = prevJobs.map((job) => {
          if (job.status === "pending") {
            // Move to processing after 1 second
            const timeSinceSubmit = Date.now() - job.submittedAt.getTime();
            if (timeSinceSubmit > 1000) {
              return { ...job, status: "processing" as const, progress: 10 };
            }
            return job;
          } else if (job.status === "processing") {
            // Simulate progress
            const timeSinceSubmit = Date.now() - job.submittedAt.getTime();
            const progress = Math.min(90, 10 + Math.floor(timeSinceSubmit / 200)); // 0.5% per 100ms
            
            // Complete after ~20 seconds
            if (progress >= 90 || timeSinceSubmit > 20000) {
              // Store result in results
              const result = {
                id: job.id,
                jobId: job.jobId,
                clientName: job.clientName,
                lcNumber: job.lcNumber,
                submittedAt: job.submittedAt.toISOString(),
                completedAt: new Date().toISOString(),
                status: Math.random() > 0.3 ? "compliant" : "discrepancies", // 70% compliant
                complianceScore: Math.floor(Math.random() * 30) + 70, // 70-100%
                discrepancyCount: Math.random() > 0.3 ? Math.floor(Math.random() * 5) : 0,
                documentCount: Math.floor(Math.random() * 5) + 3, // 3-8 documents
              };

              const existingResults = localStorage.getItem("bank_validation_results");
              const results = existingResults ? JSON.parse(existingResults) : [];
              results.unshift(result);
              localStorage.setItem("bank_validation_results", JSON.stringify(results));

              return {
                ...job,
                status: "completed" as const,
                progress: 100,
                completedAt: new Date(),
              };
            }
            return { ...job, progress };
          }
          return job;
        });

        // Persist updated jobs to localStorage
        localStorage.setItem(
          "bank_validation_jobs",
          JSON.stringify(updated.map((j) => ({ ...j, submittedAt: j.submittedAt.toISOString(), completedAt: j.completedAt?.toISOString() })))
        );

        return updated;
      });
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  // Check for completed jobs and trigger callback
  useEffect(() => {
    const hasCompleted = jobs.some((j) => j.status === "completed");
    if (hasCompleted && onJobComplete) {
      const timeout = setTimeout(() => {
        onJobComplete();
      }, 1000);
      return () => clearTimeout(timeout);
    }
  }, [jobs, onJobComplete]);

  const getStatusBadge = (status: ProcessingJob["status"]) => {
    switch (status) {
      case "pending":
        return <Badge variant="secondary">Pending</Badge>;
      case "processing":
        return <Badge variant="default" className="bg-blue-500">Processing</Badge>;
      case "completed":
        return <Badge variant="default" className="bg-green-500">Completed</Badge>;
      case "error":
        return <Badge variant="destructive">Error</Badge>;
    }
  };

  const getStatusIcon = (status: ProcessingJob["status"]) => {
    switch (status) {
      case "pending":
        return <Clock className="w-5 h-5 text-muted-foreground" />;
      case "processing":
        return <Clock className="w-5 h-5 text-blue-500 animate-spin" />;
      case "completed":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "error":
        return <XCircle className="w-5 h-5 text-destructive" />;
    }
  };

  if (jobs.length === 0) {
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
          {jobs.filter((j) => j.status === "processing" || j.status === "pending").length} job(s) in progress
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {jobs.map((job) => (
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
                        {job.clientName}
                      </h4>
                      {getStatusBadge(job.status)}
                    </div>
                    {job.lcNumber && (
                      <p className="text-sm text-muted-foreground">
                        LC: {job.lcNumber}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground mt-1">
                      Submitted: {job.submittedAt.toLocaleString()}
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

              {job.status === "completed" && job.completedAt && (
                <p className="text-xs text-muted-foreground">
                  Completed: {job.completedAt.toLocaleString()}
                </p>
              )}

              {job.status === "error" && (
                <div className="flex items-center gap-2 text-sm text-destructive">
                  <AlertCircle className="w-4 h-4" />
                  <span>Validation failed. Please try again.</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
