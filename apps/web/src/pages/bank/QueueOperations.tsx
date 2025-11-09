import * as React from "react";
import { useSearchParams } from "react-router-dom";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Clock,
  RefreshCw,
  RotateCcw,
  StopCircle,
  Filter,
  Search,
  Save,
  Bookmark,
  Link as LinkIcon,
  AlertCircle,
  CheckCircle2,
  XCircle,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { useJobStatusStream } from "@/hooks/use-job-status-stream";

// Mock data - replace with API calls
const mockJobs = [
  {
    id: "job-1",
    lc_number: "LC-BNK-2024-001",
    client_name: "Global Importers Ltd",
    priority: 5,
    status: "queued" as const,
    queue: "standard",
    attempts: 0,
    maxRetries: 3,
    createdAt: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    scheduledAt: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
  },
  {
    id: "job-2",
    lc_number: "LC-BNK-2024-002",
    client_name: "Trade Partners Inc",
    priority: 8,
    status: "running" as const,
    queue: "priority",
    attempts: 0,
    maxRetries: 3,
    createdAt: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    startedAt: new Date(Date.now() - 1000 * 60 * 10).toISOString(),
  },
  {
    id: "job-3",
    lc_number: "LC-BNK-2024-003",
    client_name: "Export Solutions Co",
    priority: 3,
    status: "failed" as const,
    queue: "standard",
    attempts: 2,
    maxRetries: 3,
    createdAt: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    errorMessage: "Document parsing failed",
  },
  {
    id: "job-4",
    lc_number: "LC-BNK-2024-004",
    client_name: "International Trade Ltd",
    priority: 7,
    status: "succeeded" as const,
    queue: "priority",
    attempts: 0,
    maxRetries: 3,
    createdAt: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    completedAt: new Date(Date.now() - 1000 * 60 * 40).toISOString(),
    durationMs: 180000,
  },
];

type JobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled" | "scheduled";
type JobPriority = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10;
type SavedView = {
  id: string;
  name: string;
  filters: {
    status?: JobStatus[];
    priority?: JobPriority[];
    queue?: string[];
    search?: string;
  };
};

const formatDuration = (job: typeof mockJobs[0]) => {
  if (job.durationMs) {
    if (job.durationMs < 1000) return `${job.durationMs}ms`;
    return `${(job.durationMs / 1000).toFixed(1)}s`;
  }
  if (job.startedAt && job.status === "running") {
    const diff = Date.now() - new Date(job.startedAt).getTime();
    return diff < 1000 ? `${diff}ms` : `${(diff / 1000).toFixed(1)}s`;
  }
  return "-";
};

const formatRelativeTime = (iso: string | undefined) => {
  if (!iso) return "-";
  const diffMs = Date.now() - new Date(iso).getTime();
  if (diffMs < 60_000) return "just now";
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
};

export function QueueOperationsView({ embedded = false }: { embedded?: boolean }) {
  const { toast } = useToast();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  // Use real-time job stream
  const { jobs: streamJobs, isConnected } = useJobStatusStream({ enabled: true });
  
  // Merge stream jobs with mock jobs for now
  const [jobs, setJobs] = React.useState(mockJobs);
  const [loading, setLoading] = React.useState(false);
  
  // Filters from URL
  const [statusFilter, setStatusFilter] = React.useState<string[]>(() => {
    const raw = searchParams.get("status");
    return raw ? raw.split(",").filter(Boolean) : [];
  });
  const [priorityFilter, setPriorityFilter] = React.useState<string[]>(() => {
    const raw = searchParams.get("priority");
    return raw ? raw.split(",").filter(Boolean) : [];
  });
  const [queueFilter, setQueueFilter] = React.useState<string[]>(() => {
    const raw = searchParams.get("queue");
    return raw ? raw.split(",").filter(Boolean) : [];
  });
  const [searchQuery, setSearchQuery] = React.useState(searchParams.get("search") ?? "");
  
  // Saved views
  const [savedViews, setSavedViews] = React.useState<SavedView[]>(() => {
    const stored = localStorage.getItem("bank_queue_saved_views");
    return stored ? JSON.parse(stored) : [];
  });
  const [activeView, setActiveView] = React.useState<string | null>(null);
  
  // Dialogs
  const [retryDialogOpen, setRetryDialogOpen] = React.useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = React.useState(false);
  const [saveViewDialogOpen, setSaveViewDialogOpen] = React.useState(false);
  const [selectedJob, setSelectedJob] = React.useState<typeof mockJobs[0] | null>(null);
  const [actionReason, setActionReason] = React.useState("");
  const [selectedJobs, setSelectedJobs] = React.useState<Set<string>>(new Set());
  const [newViewName, setNewViewName] = React.useState("");

  // Update URL params when filters change
  React.useEffect(() => {
    const params = new URLSearchParams();
    if (statusFilter.length) params.set("status", statusFilter.join(","));
    if (priorityFilter.length) params.set("priority", priorityFilter.join(","));
    if (queueFilter.length) params.set("queue", queueFilter.join(","));
    if (searchQuery) params.set("search", searchQuery);
    if (activeView) params.set("view", activeView);
    
    setSearchParams(params, { replace: true });
  }, [statusFilter, priorityFilter, queueFilter, searchQuery, activeView, setSearchParams]);

  // Apply saved view
  React.useEffect(() => {
    const viewId = searchParams.get("view");
    if (viewId) {
      const view = savedViews.find((v) => v.id === viewId);
      if (view) {
        setActiveView(viewId);
        if (view.filters.status) setStatusFilter(view.filters.status);
        if (view.filters.priority) setPriorityFilter(view.filters.priority.map(String));
        if (view.filters.queue) setQueueFilter(view.filters.queue);
        if (view.filters.search) setSearchQuery(view.filters.search);
      }
    }
  }, [searchParams, savedViews]);

  const filteredJobs = jobs.filter((job) => {
    const matchesStatus = statusFilter.length === 0 || statusFilter.includes(job.status);
    const matchesPriority = priorityFilter.length === 0 || priorityFilter.includes(String(job.priority));
    const matchesQueue = queueFilter.length === 0 || queueFilter.includes(job.queue);
    const matchesSearch =
      searchQuery === "" ||
      job.lc_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.client_name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesPriority && matchesQueue && matchesSearch;
  });

  const handleRetry = async (jobId: string) => {
    if (!actionReason.trim()) {
      toast({
        title: "Reason Required",
        description: "Please provide a reason for retrying this job.",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      // In a real app, call API: await bankApi.retryJob(jobId, actionReason);
      toast({
        title: "Job Retried",
        description: `Job ${jobId} has been queued for retry.`,
      });
      setJobs((prev) =>
        prev.map((j) =>
          j.id === jobId ? { ...j, status: "queued" as const, attempts: 0, errorMessage: undefined } : j
        )
      );
      setRetryDialogOpen(false);
      setActionReason("");
      setSelectedJob(null);
    } catch (error) {
      toast({
        title: "Retry Failed",
        description: "Failed to retry job. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (jobId: string) => {
    if (!actionReason.trim()) {
      toast({
        title: "Reason Required",
        description: "Please provide a reason for cancelling this job.",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      // In a real app, call API: await bankApi.cancelJob(jobId, actionReason);
      toast({
        title: "Job Cancelled",
        description: `Job ${jobId} has been cancelled.`,
      });
      setJobs((prev) =>
        prev.map((j) => (j.id === jobId ? { ...j, status: "cancelled" as const } : j))
      );
      setCancelDialogOpen(false);
      setActionReason("");
      setSelectedJob(null);
    } catch (error) {
      toast({
        title: "Cancel Failed",
        description: "Failed to cancel job. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleBulkRetry = async () => {
    if (selectedJobs.size === 0) return;
    if (!actionReason.trim()) {
      toast({
        title: "Reason Required",
        description: "Please provide a reason for retrying these jobs.",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      // In a real app, call API: await bankApi.bulkRetryJobs(Array.from(selectedJobs), actionReason);
      toast({
        title: "Jobs Retried",
        description: `${selectedJobs.size} job(s) have been queued for retry.`,
      });
      setJobs((prev) =>
        prev.map((j) =>
          selectedJobs.has(j.id) && j.status === "failed"
            ? { ...j, status: "queued" as const, attempts: 0, errorMessage: undefined }
            : j
        )
      );
      setSelectedJobs(new Set());
      setActionReason("");
    } catch (error) {
      toast({
        title: "Bulk Retry Failed",
        description: "Failed to retry jobs. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveView = () => {
    if (!newViewName.trim()) {
      toast({
        title: "View Name Required",
        description: "Please provide a name for this saved view.",
        variant: "destructive",
      });
      return;
    }

    const newView: SavedView = {
      id: `view-${Date.now()}`,
      name: newViewName,
      filters: {
        status: statusFilter.length ? (statusFilter as JobStatus[]) : undefined,
        priority: priorityFilter.length ? (priorityFilter.map(Number) as JobPriority[]) : undefined,
        queue: queueFilter.length ? queueFilter : undefined,
        search: searchQuery || undefined,
      },
    };

    const updated = [...savedViews, newView];
    setSavedViews(updated);
    localStorage.setItem("bank_queue_saved_views", JSON.stringify(updated));
    toast({
      title: "View Saved",
      description: `Saved view "${newViewName}" has been created.`,
    });
    setSaveViewDialogOpen(false);
    setNewViewName("");
  };

  const handleLoadView = (view: SavedView) => {
    setActiveView(view.id);
    if (view.filters.status) setStatusFilter(view.filters.status);
    if (view.filters.priority) setPriorityFilter(view.filters.priority.map(String));
    if (view.filters.queue) setQueueFilter(view.filters.queue);
    if (view.filters.search) setSearchQuery(view.filters.search);
    toast({
      title: "View Loaded",
      description: `Loaded view "${view.name}".`,
    });
  };

  const handleCopyDeepLink = () => {
    const currentUrl = window.location.href;
    navigator.clipboard.writeText(currentUrl);
    toast({
      title: "Link Copied",
      description: "Deep link copied to clipboard.",
    });
  };

  const handlePriorityChange = (jobId: string, newPriority: number) => {
    setJobs((prev) =>
      prev.map((j) => (j.id === jobId ? { ...j, priority: newPriority as JobPriority } : j))
    );
    // In a real app, call API: await bankApi.updateJobPriority(jobId, newPriority);
    toast({
      title: "Priority Updated",
      description: `Job priority updated to ${newPriority}.`,
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Queue Operations</h2>
          <p className="text-muted-foreground">Manage validation jobs with priorities, filters, and saved views.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleCopyDeepLink} className="gap-2">
            <LinkIcon className="h-4 w-4" /> Copy Link
          </Button>
          <Button variant="outline" onClick={() => setSaveViewDialogOpen(true)} className="gap-2">
            <Save className="h-4 w-4" /> Save View
          </Button>
        </div>
      </div>

      {/* Saved Views */}
      {savedViews.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Saved Views</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {savedViews.map((view) => (
                <Button
                  key={view.id}
                  variant={activeView === view.id ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleLoadView(view)}
                  className="gap-2"
                >
                  <Bookmark className="h-3 w-3" />
                  {view.name}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label>Search</Label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="LC number, client..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Status</Label>
              <Select
                value={statusFilter.join(",")}
                onValueChange={(value) => setStatusFilter(value ? value.split(",") : [])}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Statuses</SelectItem>
                  <SelectItem value="queued">Queued</SelectItem>
                  <SelectItem value="running">Running</SelectItem>
                  <SelectItem value="succeeded">Succeeded</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Priority</Label>
              <Select
                value={priorityFilter.join(",")}
                onValueChange={(value) => setPriorityFilter(value ? value.split(",") : [])}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Priorities" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Priorities</SelectItem>
                  <SelectItem value="9,10">High (9-10)</SelectItem>
                  <SelectItem value="7,8">Medium-High (7-8)</SelectItem>
                  <SelectItem value="5,6">Medium (5-6)</SelectItem>
                  <SelectItem value="1,2,3,4">Low (1-4)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Queue</Label>
              <Select
                value={queueFilter.join(",")}
                onValueChange={(value) => setQueueFilter(value ? value.split(",") : [])}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Queues" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Queues</SelectItem>
                  <SelectItem value="priority">Priority</SelectItem>
                  <SelectItem value="standard">Standard</SelectItem>
                  <SelectItem value="bulk">Bulk</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Bulk Actions */}
      {selectedJobs.size > 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {selectedJobs.size} job(s) selected
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleBulkRetry}
                  disabled={loading}
                  className="gap-2"
                >
                  <RotateCcw className="h-4 w-4" /> Retry Selected
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedJobs(new Set())}
                >
                  Clear Selection
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Jobs Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Jobs ({filteredJobs.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <RefreshCw className="h-5 w-5 animate-spin mr-2" /> Loading jobs...
            </div>
          ) : filteredJobs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Clock className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No jobs found matching your filters.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <Checkbox
                      checked={selectedJobs.size === filteredJobs.length && filteredJobs.length > 0}
                      onCheckedChange={(checked) => {
                        if (checked) {
                          setSelectedJobs(new Set(filteredJobs.map((j) => j.id)));
                        } else {
                          setSelectedJobs(new Set());
                        }
                      }}
                    />
                  </TableHead>
                  <TableHead>LC Number</TableHead>
                  <TableHead>Client</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Queue</TableHead>
                  <TableHead>Attempts</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredJobs.map((job) => (
                  <TableRow key={job.id}>
                    <TableCell>
                      <Checkbox
                        checked={selectedJobs.has(job.id)}
                        onCheckedChange={(checked) => {
                          const newSet = new Set(selectedJobs);
                          if (checked) {
                            newSet.add(job.id);
                          } else {
                            newSet.delete(job.id);
                          }
                          setSelectedJobs(newSet);
                        }}
                      />
                    </TableCell>
                    <TableCell className="font-medium">{job.lc_number}</TableCell>
                    <TableCell>{job.client_name}</TableCell>
                    <TableCell>
                      <StatusBadge
                        status={
                          job.status === "succeeded"
                            ? "success"
                            : job.status === "failed"
                            ? "error"
                            : job.status === "running"
                            ? "pending"
                            : "warning"
                        }
                      >
                        {job.status}
                      </StatusBadge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          onClick={() => handlePriorityChange(job.id, Math.max(1, job.priority - 1))}
                          disabled={job.priority <= 1}
                        >
                          <ArrowDown className="h-3 w-3" />
                        </Button>
                        <Badge variant="outline">{job.priority}</Badge>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0"
                          onClick={() => handlePriorityChange(job.id, Math.min(10, job.priority + 1))}
                          disabled={job.priority >= 10}
                        >
                          <ArrowUp className="h-3 w-3" />
                        </Button>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{job.queue}</Badge>
                    </TableCell>
                    <TableCell>
                      {job.attempts}/{job.maxRetries}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatRelativeTime(job.createdAt)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDuration(job)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        {job.status === "failed" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedJob(job);
                              setRetryDialogOpen(true);
                            }}
                            className="gap-2"
                          >
                            <RotateCcw className="h-4 w-4" /> Retry
                          </Button>
                        )}
                        {(job.status === "queued" || job.status === "running") && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedJob(job);
                              setCancelDialogOpen(true);
                            }}
                            className="gap-2"
                          >
                            <StopCircle className="h-4 w-4" /> Cancel
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Retry Dialog */}
      <Dialog open={retryDialogOpen} onOpenChange={setRetryDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Retry Job</DialogTitle>
            <DialogDescription>
              Retry job {selectedJob?.lc_number}. Please provide a reason.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Reason</Label>
              <Textarea
                placeholder="Enter reason for retrying this job..."
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value)}
                rows={3}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setRetryDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => selectedJob && handleRetry(selectedJob.id)} disabled={loading}>
                Retry Job
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Cancel Dialog */}
      <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel Job</DialogTitle>
            <DialogDescription>
              Cancel job {selectedJob?.lc_number}. Please provide a reason.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Reason</Label>
              <Textarea
                placeholder="Enter reason for cancelling this job..."
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value)}
                rows={3}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setCancelDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => selectedJob && handleCancel(selectedJob.id)}
                disabled={loading}
              >
                Cancel Job
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Save View Dialog */}
      <Dialog open={saveViewDialogOpen} onOpenChange={setSaveViewDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Current View</DialogTitle>
            <DialogDescription>
              Save your current filters as a reusable view.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>View Name</Label>
              <Input
                placeholder="e.g., High Priority Failed Jobs"
                value={newViewName}
                onChange={(e) => setNewViewName(e.target.value)}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setSaveViewDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSaveView}>Save View</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

