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
  AlertTriangle,
  Clock,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Filter,
  Search,
  Eye,
  MessageSquare,
  User,
  Calendar,
  History,
  Download,
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
import { generateCSV } from "@/lib/csv";

// Mock audit log data - replace with API calls
const mockDiscrepancyAuditLogs = [
  {
    id: "audit-1",
    workflow_id: "workflow-1",
    action: "created",
    actor_id: "user-1",
    details: { initial_status: "open", priority: "high" },
    created_at: "2024-01-18T10:00:00Z",
  },
  {
    id: "audit-2",
    workflow_id: "workflow-1",
    action: "updated",
    actor_id: "user-2",
    details: { old_status: "open", new_status: "in_progress", new_assigned_to: "user-2" },
    created_at: "2024-01-18T11:00:00Z",
  },
  {
    id: "audit-3",
    workflow_id: "workflow-1",
    action: "comment_added",
    actor_id: "user-2",
    details: { comment_id: "comment-1", comment_snippet: "Contacting client for clarification" },
    created_at: "2024-01-18T11:15:00Z",
  },
];

// Mock data - replace with API calls
const mockDiscrepancies = [
  {
    id: "workflow-1",
    discrepancy_id: "disc-1",
    lc_number: "LC-BNK-2024-001",
    validation_session_id: "session-1",
    status: "open",
    assigned_to: null,
    due_date: "2024-01-20T17:00:00Z",
    priority: "high",
    resolution_notes: null,
    created_at: "2024-01-18T10:00:00Z",
    updated_at: "2024-01-18T14:00:00Z",
    resolved_at: null,
    resolved_by: null,
    metadata_: { client_id: "client-1", document_type: "commercial_invoice" },
  },
  {
    id: "workflow-2",
    discrepancy_id: "disc-2",
    lc_number: "LC-BNK-2024-002",
    validation_session_id: "session-2",
    status: "in_progress",
    assigned_to: "user-1",
    due_date: "2024-01-19T17:00:00Z",
    priority: "critical",
    resolution_notes: "Working with client to resolve",
    created_at: "2024-01-17T09:00:00Z",
    updated_at: "2024-01-18T11:00:00Z",
    resolved_at: null,
    resolved_by: null,
    metadata_: { client_id: "client-2", document_type: "bill_of_lading" },
  },
  {
    id: "workflow-3",
    discrepancy_id: "disc-3",
    lc_number: "LC-BNK-2024-003",
    validation_session_id: "session-3",
    status: "resolved",
    assigned_to: "user-2",
    due_date: "2024-01-18T17:00:00Z",
    priority: "medium",
    resolution_notes: "Client provided corrected document",
    created_at: "2024-01-16T08:00:00Z",
    updated_at: "2024-01-17T15:00:00Z",
    resolved_at: "2024-01-17T15:00:00Z",
    resolved_by: "user-2",
    metadata_: { client_id: "client-3", document_type: "certificate_of_origin" },
  },
];

const formatTimeAgo = (dateString: string) => {
  const date = new Date(dateString);
  const now = new Date();
  const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

  if (diffInHours < 1) return "Just now";
  if (diffInHours < 24) return `${diffInHours}h ago`;

  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays < 7) return `${diffInDays}d ago`;

  return date.toLocaleDateString();
};

const getStatusColor = (status: string) => {
  switch (status) {
    case "resolved":
      return "success";
    case "rejected":
      return "destructive";
    case "open":
      return "info";
    case "in_progress":
      return "warning";
    case "closed":
      return "secondary";
    default:
      return "secondary";
  }
};

const getPriorityColor = (priority: string) => {
  switch (priority) {
    case "critical":
      return "destructive";
    case "high":
      return "default";
    case "medium":
      return "secondary";
    case "low":
      return "outline";
    default:
      return "secondary";
  }
};

export function DiscrepanciesView({ embedded = false }: { embedded?: boolean }) {
  const { toast } = useToast();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const [loading, setLoading] = React.useState(false);
  const [discrepancies, setDiscrepancies] = React.useState(mockDiscrepancies);
  const [statusFilter, setStatusFilter] = React.useState<string>("all");
  const [priorityFilter, setPriorityFilter] = React.useState<string>("all");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [selectedDiscrepancy, setSelectedDiscrepancy] = React.useState<typeof mockDiscrepancies[0] | null>(null);
  const [commentDialogOpen, setCommentDialogOpen] = React.useState(false);
  const [assignDialogOpen, setAssignDialogOpen] = React.useState(false);
  const [resolveDialogOpen, setResolveDialogOpen] = React.useState(false);
  const [commentText, setCommentText] = React.useState("");
  const [resolutionNotes, setResolutionNotes] = React.useState("");
  const [selectedDiscrepancyForAudit, setSelectedDiscrepancyForAudit] = React.useState<typeof mockDiscrepancies[0] | null>(null);
  const [auditLogs, setAuditLogs] = React.useState(mockDiscrepancyAuditLogs);
  const [auditDialogOpen, setAuditDialogOpen] = React.useState(false);

  // In a real app, fetch discrepancies from API
  React.useEffect(() => {
    // Example: Fetch discrepancies
    // setLoading(true);
    // getBankWorkflowService().listDiscrepancyWorkflows({ status: statusFilter, priority: priorityFilter }).then(setDiscrepancies).finally(() => setLoading(false));
  }, [statusFilter, priorityFilter]);

  const filteredDiscrepancies = discrepancies.filter((workflow) => {
    if (statusFilter !== "all" && workflow.status !== statusFilter) return false;
    if (priorityFilter !== "all" && workflow.priority !== priorityFilter) return false;
    if (searchQuery && !workflow.lc_number.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const handleAssign = (workflowId: string) => {
    toast({
      title: "Discrepancy Assigned",
      description: `Discrepancy ${workflowId} has been assigned to you.`,
    });
    // In a real app, call API to assign
    setDiscrepancies((prev) =>
      prev.map((w) => (w.id === workflowId ? { ...w, assigned_to: user?.id || "user-1", status: "in_progress" as const } : w))
    );
    setAssignDialogOpen(false);
  };

  const handleResolve = (workflowId: string) => {
    if (!resolutionNotes.trim()) {
      toast({
        title: "Resolution Notes Required",
        description: "Please provide resolution notes before resolving.",
        variant: "destructive",
      });
      return;
    }

    toast({
      title: "Discrepancy Resolved",
      description: `Discrepancy ${workflowId} has been resolved.`,
    });
    // In a real app, call API to resolve
    setDiscrepancies((prev) =>
      prev.map((w) =>
        w.id === workflowId
          ? {
              ...w,
              status: "resolved" as const,
              resolved_at: new Date().toISOString(),
              resolved_by: user?.id || "user-1",
              resolution_notes: resolutionNotes,
            }
          : w
      )
    );
    setResolutionNotes("");
    setResolveDialogOpen(false);
  };

  const handleAddComment = () => {
    if (!selectedDiscrepancy || !commentText.trim()) return;

    toast({
      title: "Comment Added",
      description: `Comment added to discrepancy ${selectedDiscrepancy.lc_number}.`,
    });
    setCommentText("");
    setCommentDialogOpen(false);
    // In a real app, call API to add comment
  };

  const handleViewAuditLogs = (workflow: typeof mockDiscrepancies[0]) => {
    setSelectedDiscrepancyForAudit(workflow);
    // In a real app, fetch audit logs for this workflow
    // getBankWorkflowService().getDiscrepancyWorkflowAuditLogs(workflow.id).then(setAuditLogs);
    setAuditDialogOpen(true);
  };

  const handleExportAuditLogs = () => {
    if (!selectedDiscrepancyForAudit) return;

    const headers = ["Timestamp", "Action", "Actor", "Details"];
    const rows = auditLogs.map((log) => [
      new Date(log.created_at).toLocaleString(),
      log.action,
      log.actor_id || "System",
      JSON.stringify(log.details),
    ]);

    const csv = generateCSV([headers, ...rows]);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `discrepancy-audit-${selectedDiscrepancyForAudit.lc_number}-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);

    toast({
      title: "Audit Logs Exported",
      description: `Audit logs for ${selectedDiscrepancyForAudit.lc_number} have been exported.`,
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Discrepancy Workflow</h2>
          <p className="text-muted-foreground">Track and resolve LC validation discrepancies.</p>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Filter className="h-4 w-4" /> Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Status</Label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="open">Open</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="resolved">Resolved</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                  <SelectItem value="closed">Closed</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Priority</Label>
              <Select value={priorityFilter} onValueChange={setPriorityFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All Priorities" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Priorities</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Search LC Number</Label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Discrepancies Table */}
      <Card>
        <CardHeader>
          <CardTitle>Discrepancies ({filteredDiscrepancies.length})</CardTitle>
          <CardDescription>Manage discrepancy resolution workflow</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <RefreshCw className="h-5 w-5 animate-spin mr-2" /> Loading discrepancies...
            </div>
          ) : filteredDiscrepancies.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No discrepancies found</p>
              <p className="text-sm">Adjust your filters to see more results</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>LC Number</TableHead>
                  <TableHead>Document Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Assigned To</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Last Updated</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredDiscrepancies.map((workflow) => (
                  <TableRow key={workflow.id}>
                    <TableCell className="font-medium">{workflow.lc_number}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{workflow.metadata_.document_type || "N/A"}</Badge>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={getStatusColor(workflow.status)}>{workflow.status}</StatusBadge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={getPriorityColor(workflow.priority)}>{workflow.priority}</Badge>
                    </TableCell>
                    <TableCell>
                      {workflow.assigned_to ? (
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4" />
                          User {workflow.assigned_to.slice(-4)}
                        </div>
                      ) : (
                        <span className="text-muted-foreground">Unassigned</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {workflow.due_date ? (
                        <div className="flex items-center gap-2">
                          <Calendar className="h-4 w-4" />
                          {new Date(workflow.due_date).toLocaleDateString()}
                        </div>
                      ) : (
                        "N/A"
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{formatTimeAgo(workflow.updated_at)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewAuditLogs(workflow)}
                          tooltip="View Audit Logs"
                        >
                          <History className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedDiscrepancy(workflow);
                            setCommentDialogOpen(true);
                          }}
                        >
                          <MessageSquare className="h-4 w-4" />
                        </Button>
                        {!workflow.assigned_to && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedDiscrepancy(workflow);
                              setAssignDialogOpen(true);
                            }}
                          >
                            <User className="h-4 w-4 mr-1" /> Assign
                          </Button>
                        )}
                        {workflow.status === "in_progress" && (
                          <Button
                            variant="default"
                            size="sm"
                            onClick={() => {
                              setSelectedDiscrepancy(workflow);
                              setResolveDialogOpen(true);
                            }}
                          >
                            <CheckCircle2 className="h-4 w-4 mr-1" /> Resolve
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

      {/* Comment Dialog */}
      <Dialog open={commentDialogOpen} onOpenChange={setCommentDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Comment</DialogTitle>
            <DialogDescription>
              Add a comment to discrepancy {selectedDiscrepancy?.lc_number}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Comment</Label>
              <Textarea
                placeholder="Enter your comment..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                rows={4}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setCommentDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleAddComment} disabled={!commentText.trim()}>
                Add Comment
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Assign Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Discrepancy</DialogTitle>
            <DialogDescription>
              Assign discrepancy {selectedDiscrepancy?.lc_number} to yourself?
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setAssignDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => selectedDiscrepancy && handleAssign(selectedDiscrepancy.id)}>
              Assign to Me
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Resolve Dialog */}
      <Dialog open={resolveDialogOpen} onOpenChange={setResolveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Resolve Discrepancy</DialogTitle>
            <DialogDescription>
              Provide resolution notes for discrepancy {selectedDiscrepancy?.lc_number}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Resolution Notes</Label>
              <Textarea
                placeholder="Enter resolution notes..."
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                rows={4}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setResolveDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => selectedDiscrepancy && handleResolve(selectedDiscrepancy.id)} disabled={!resolutionNotes.trim()}>
                Resolve
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Audit Logs Dialog */}
      <Dialog open={auditDialogOpen} onOpenChange={setAuditDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <div>
                <DialogTitle>Audit Logs</DialogTitle>
                <DialogDescription>
                  Complete audit trail for discrepancy {selectedDiscrepancyForAudit?.lc_number}
                </DialogDescription>
              </div>
              <Button variant="outline" size="sm" onClick={handleExportAuditLogs} className="gap-2">
                <Download className="h-4 w-4" /> Export CSV
              </Button>
            </div>
          </DialogHeader>
          <div className="space-y-4">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditLogs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="text-sm">{new Date(log.created_at).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{log.action}</Badge>
                    </TableCell>
                    <TableCell className="text-sm">{log.actor_id ? `User ${log.actor_id.slice(-4)}` : "System"}</TableCell>
                    <TableCell className="text-sm">
                      <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                        {JSON.stringify(log.details, null, 2)}
                      </pre>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

