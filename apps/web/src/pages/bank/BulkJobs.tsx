/**
 * Bank Bulk Jobs component for templated runs, scheduling, and throttling.
 */
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
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Plus,
  Play,
  Pause,
  Trash2,
  FileText,
  Clock,
  Settings,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Copy,
  Calendar,
  Gauge,
} from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { useBankAuth } from "@/lib/bank/auth";
import { bankBulkJobsApi, type BulkJob, type BulkTemplate, type BulkJobCreate, type BulkTemplateCreate } from "@/api/bank-bulk-jobs";
import { format } from "date-fns";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export function BulkJobsView({ embedded = false }: { embedded?: boolean }) {
  const { toast } = useToast();
  const { user } = useBankAuth();
  const [searchParams] = useSearchParams();
  const [activeTab, setActiveTab] = React.useState<"jobs" | "templates">("jobs");
  const [createJobDialogOpen, setCreateJobDialogOpen] = React.useState(false);
  const [createTemplateDialogOpen, setCreateTemplateDialogOpen] = React.useState(false);
  const [selectedJob, setSelectedJob] = React.useState<BulkJob | null>(null);
  const [selectedTemplate, setSelectedTemplate] = React.useState<BulkTemplate | null>(null);
  const queryClient = useQueryClient();

  // Load jobs
  const { data: jobsData, isLoading: jobsLoading, refetch: refetchJobs } = useQuery({
    queryKey: ["bank-bulk-jobs"],
    queryFn: () => bankBulkJobsApi.list({ limit: 100 }),
    refetchInterval: 5000, // Refresh every 5 seconds for running jobs
  });

  // Load templates
  const { data: templatesData, isLoading: templatesLoading, refetch: refetchTemplates } = useQuery({
    queryKey: ["bank-bulk-templates"],
    queryFn: () => bankBulkJobsApi.listTemplates({ include_public: true }),
  });

  const jobs = jobsData?.items || [];
  const templates = templatesData?.items || [];

  // Create job mutation
  const createJobMutation = useMutation({
    mutationFn: (data: BulkJobCreate) => bankBulkJobsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-bulk-jobs"] });
      setCreateJobDialogOpen(false);
      toast({
        title: "Bulk Job Created",
        description: "Bulk job has been created and queued for processing.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Create Failed",
        description: error.response?.data?.detail || "Failed to create bulk job.",
        variant: "destructive",
      });
    },
  });

  // Cancel job mutation
  const cancelJobMutation = useMutation({
    mutationFn: (jobId: string) => bankBulkJobsApi.cancel(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-bulk-jobs"] });
      toast({
        title: "Job Cancelled",
        description: "Bulk job has been cancelled.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Cancel Failed",
        description: error.response?.data?.detail || "Failed to cancel job.",
        variant: "destructive",
      });
    },
  });

  // Create template mutation
  const createTemplateMutation = useMutation({
    mutationFn: (data: BulkTemplateCreate) => bankBulkJobsApi.createTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-bulk-templates"] });
      setCreateTemplateDialogOpen(false);
      toast({
        title: "Template Created",
        description: "Bulk job template has been created.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Create Failed",
        description: error.response?.data?.detail || "Failed to create template.",
        variant: "destructive",
      });
    },
  });

  // Delete template mutation
  const deleteTemplateMutation = useMutation({
    mutationFn: (templateId: string) => bankBulkJobsApi.deleteTemplate(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-bulk-templates"] });
      toast({
        title: "Template Deleted",
        description: "Template has been deleted.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Delete Failed",
        description: error.response?.data?.detail || "Failed to delete template.",
        variant: "destructive",
      });
    },
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "pending":
        return <StatusBadge status="info">Pending</StatusBadge>;
      case "running":
        return <StatusBadge status="warning">Running</StatusBadge>;
      case "succeeded":
        return <StatusBadge status="success">Succeeded</StatusBadge>;
      case "failed":
        return <StatusBadge status="destructive">Failed</StatusBadge>;
      case "partial":
        return <StatusBadge status="warning">Partial</StatusBadge>;
      case "cancelled":
        return <StatusBadge status="info">Cancelled</StatusBadge>;
      default:
        return <StatusBadge status="info">{status}</StatusBadge>;
    }
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return "-";
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Bulk Jobs</h2>
          <p className="text-muted-foreground">
            Create and manage templated bulk processing jobs with scheduling and throttling controls.
          </p>
        </div>
        <div className="flex gap-2">
          {activeTab === "jobs" && (
            <Button onClick={() => setCreateJobDialogOpen(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              New Bulk Job
            </Button>
          )}
          {activeTab === "templates" && (
            <Button onClick={() => setCreateTemplateDialogOpen(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              New Template
            </Button>
          )}
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as typeof activeTab)} className="w-full">
        <TabsList>
          <TabsTrigger value="jobs">Bulk Jobs ({jobs.length})</TabsTrigger>
          <TabsTrigger value="templates">Templates ({templates.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="jobs" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Bulk Processing Jobs</CardTitle>
              <CardDescription>View and manage bulk LC processing jobs</CardDescription>
            </CardHeader>
            <CardContent>
              {jobsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-5 w-5 animate-spin mr-2" />
                  Loading jobs...
                </div>
              ) : jobs.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p>No bulk jobs yet</p>
                  <p className="text-sm">Create your first bulk job to get started</p>
                  <Button onClick={() => setCreateJobDialogOpen(true)} className="mt-4" variant="outline">
                    <Plus className="h-4 w-4 mr-2" />
                    Create Bulk Job
                  </Button>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Progress</TableHead>
                      <TableHead>Items</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {jobs.map((job) => (
                      <TableRow key={job.id}>
                        <TableCell className="font-medium">{job.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{job.job_type.replace(/_/g, " ")}</Badge>
                        </TableCell>
                        <TableCell>{getStatusBadge(job.status)}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Progress value={job.progress_percent} className="w-24" />
                            <span className="text-sm text-muted-foreground">{job.progress_percent.toFixed(0)}%</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">
                            <div>{job.processed_items} / {job.total_items}</div>
                            <div className="text-muted-foreground text-xs">
                              ✓ {job.succeeded_items} • ✗ {job.failed_items} • ⊘ {job.skipped_items}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDuration(job.duration_seconds)}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {format(new Date(job.created_at), "MMM d, yyyy HH:mm")}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            {job.status === "running" && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => cancelJobMutation.mutate(job.id)}
                                className="text-destructive hover:text-destructive"
                              >
                                <Pause className="h-4 w-4" />
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
        </TabsContent>

        <TabsContent value="templates" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Bulk Job Templates</CardTitle>
              <CardDescription>Create reusable templates for bulk processing jobs</CardDescription>
            </CardHeader>
            <CardContent>
              {templatesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-5 w-5 animate-spin mr-2" />
                  Loading templates...
                </div>
              ) : templates.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p>No templates yet</p>
                  <p className="text-sm">Create your first template to speed up bulk job creation</p>
                  <Button onClick={() => setCreateTemplateDialogOpen(true)} className="mt-4" variant="outline">
                    <Plus className="h-4 w-4 mr-2" />
                    Create Template
                  </Button>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Usage</TableHead>
                      <TableHead>Visibility</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {templates.map((template) => (
                      <TableRow key={template.id}>
                        <TableCell className="font-medium">{template.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{template.job_type.replace(/_/g, " ")}</Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          Used {template.usage_count} time{template.usage_count !== 1 ? "s" : ""}
                          {template.last_used_at && (
                            <div className="text-xs text-muted-foreground">
                              Last: {format(new Date(template.last_used_at), "MMM d, yyyy")}
                            </div>
                          )}
                        </TableCell>
                        <TableCell>
                          {template.is_public ? (
                            <Badge variant="secondary">Public</Badge>
                          ) : (
                            <Badge variant="outline">Private</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {format(new Date(template.created_at), "MMM d, yyyy")}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedTemplate(template);
                                setCreateJobDialogOpen(true);
                              }}
                            >
                              <Play className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => deleteTemplateMutation.mutate(template.id)}
                              className="text-destructive hover:text-destructive"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Create Bulk Job Dialog */}
      <CreateBulkJobDialog
        open={createJobDialogOpen}
        onOpenChange={setCreateJobDialogOpen}
        templates={templates}
        selectedTemplate={selectedTemplate}
        onCreate={createJobMutation.mutate}
      />

      {/* Create Template Dialog */}
      <CreateTemplateDialog
        open={createTemplateDialogOpen}
        onOpenChange={setCreateTemplateDialogOpen}
        onCreate={createTemplateMutation.mutate}
      />
    </div>
  );
}

// Create Bulk Job Dialog Component
function CreateBulkJobDialog({
  open,
  onOpenChange,
  templates,
  selectedTemplate,
  onCreate,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  templates: BulkTemplate[];
  selectedTemplate: BulkTemplate | null;
  onCreate: (data: BulkJobCreate) => void;
}) {
  const [name, setName] = React.useState("");
  const [jobType, setJobType] = React.useState<"lc_validation" | "doc_verification" | "risk_analysis">("lc_validation");
  const [templateId, setTemplateId] = React.useState<string>("");
  const [priority, setPriority] = React.useState(5);
  const [throttleRate, setThrottleRate] = React.useState<number | undefined>(undefined);
  const [maxConcurrent, setMaxConcurrent] = React.useState<number | undefined>(undefined);
  const [scheduledAt, setScheduledAt] = React.useState("");
  const [description, setDescription] = React.useState("");

  React.useEffect(() => {
    if (selectedTemplate) {
      setTemplateId(selectedTemplate.id);
      setJobType(selectedTemplate.job_type as any);
    }
  }, [selectedTemplate, open]);

  const handleSubmit = () => {
    if (!name.trim()) {
      return;
    }

    onCreate({
      name,
      job_type: jobType,
      template_id: templateId || undefined,
      priority,
      config: {
        description: description || undefined,
        throttle_rate: throttleRate,
        max_concurrent: maxConcurrent,
      },
      scheduled_at: scheduledAt ? new Date(scheduledAt).toISOString() : undefined,
    });

    // Reset form
    setName("");
    setJobType("lc_validation");
    setTemplateId("");
    setPriority(5);
    setThrottleRate(undefined);
    setMaxConcurrent(undefined);
    setScheduledAt("");
    setDescription("");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Bulk Job</DialogTitle>
          <DialogDescription>Create a new bulk processing job with optional template, scheduling, and throttling.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Job Name *</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Q1 2024 LC Validation Batch"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Job Type *</Label>
              <Select value={jobType} onValueChange={(value: any) => setJobType(value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="lc_validation">LC Validation</SelectItem>
                  <SelectItem value="doc_verification">Document Verification</SelectItem>
                  <SelectItem value="risk_analysis">Risk Analysis</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Template (Optional)</Label>
              <Select value={templateId} onValueChange={setTemplateId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a template" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">None</SelectItem>
                  {templates.filter((t) => t.job_type === jobType).map((t) => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Priority</Label>
              <Select value={priority.toString()} onValueChange={(v) => setPriority(parseInt(v))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">Low (0)</SelectItem>
                  <SelectItem value="5">Normal (5)</SelectItem>
                  <SelectItem value="8">High (8)</SelectItem>
                  <SelectItem value="10">Critical (10)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Throttle Rate (items/min)</Label>
              <Input
                type="number"
                value={throttleRate || ""}
                onChange={(e) => setThrottleRate(e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder="e.g., 100"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Max Concurrent Items</Label>
            <Input
              type="number"
              value={maxConcurrent || ""}
              onChange={(e) => setMaxConcurrent(e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="e.g., 10"
            />
          </div>

          <div className="space-y-2">
            <Label>Schedule (Optional)</Label>
            <Input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label>Description</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description for this bulk job"
              rows={3}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!name.trim()}>
            Create Job
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Create Template Dialog Component
function CreateTemplateDialog({
  open,
  onOpenChange,
  onCreate,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (data: BulkTemplateCreate) => void;
}) {
  const [name, setName] = React.useState("");
  const [jobType, setJobType] = React.useState<"lc_validation" | "doc_verification" | "risk_analysis">("lc_validation");
  const [description, setDescription] = React.useState("");
  const [isPublic, setIsPublic] = React.useState(false);
  const [configTemplate, setConfigTemplate] = React.useState("{}");

  const handleSubmit = () => {
    if (!name.trim()) {
      return;
    }

    try {
      const config = JSON.parse(configTemplate);
      onCreate({
        name,
        job_type: jobType,
        description: description || undefined,
        config_template: config,
        is_public: isPublic,
      });

      // Reset form
      setName("");
      setJobType("lc_validation");
      setDescription("");
      setIsPublic(false);
      setConfigTemplate("{}");
    } catch (error) {
      // Handle JSON parse error
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Bulk Job Template</DialogTitle>
          <DialogDescription>Create a reusable template for bulk processing jobs.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Template Name *</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Standard LC Validation Template"
            />
          </div>

          <div className="space-y-2">
            <Label>Job Type *</Label>
            <Select value={jobType} onValueChange={(value: any) => setJobType(value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="lc_validation">LC Validation</SelectItem>
                <SelectItem value="doc_verification">Document Verification</SelectItem>
                <SelectItem value="risk_analysis">Risk Analysis</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Description</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label>Configuration Template (JSON) *</Label>
            <Textarea
              value={configTemplate}
              onChange={(e) => setConfigTemplate(e.target.value)}
              placeholder='{"throttle_rate": 100, "max_concurrent": 10, "retry_on_failure": true}'
              rows={6}
              className="font-mono text-sm"
            />
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="is_public"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
              className="rounded"
            />
            <Label htmlFor="is_public" className="cursor-pointer">
              Make template public (visible to all banks)
            </Label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!name.trim()}>
            Create Template
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

