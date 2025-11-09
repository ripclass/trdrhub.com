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
  FileCheck,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  Filter,
  Search,
  Eye,
  MessageSquare,
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
const mockAuditLogs = [
  {
    id: "audit-1",
    approval_id: "approval-1",
    action: "created",
    actor_id: "user-1",
    details: { initial_status: "pending", initial_stage: "analyst_review" },
    created_at: "2024-01-18T10:00:00Z",
  },
  {
    id: "audit-2",
    approval_id: "approval-1",
    action: "updated",
    actor_id: "user-2",
    details: { old_status: "pending", new_status: "approved", old_stage: "analyst_review", new_stage: "senior_review" },
    created_at: "2024-01-18T14:00:00Z",
  },
  {
    id: "audit-3",
    approval_id: "approval-1",
    action: "comment_added",
    actor_id: "user-2",
    details: { comment_id: "comment-1", comment_snippet: "Looks good, proceeding to next stage" },
    created_at: "2024-01-18T14:15:00Z",
  },
];

// Mock data - replace with API calls
const mockApprovals = [
  {
    id: "approval-1",
    lc_number: "LC-BNK-2024-001",
    validation_session_id: "session-1",
    status: "pending",
    current_stage: "analyst_review",
    assigned_to: null,
    created_at: "2024-01-18T10:00:00Z",
    updated_at: "2024-01-18T14:00:00Z",
    last_action_at: "2024-01-18T14:00:00Z",
    due_date: "2024-01-20T17:00:00Z",
    metadata_: { priority: "high", client_id: "client-1" },
  },
  {
    id: "approval-2",
    lc_number: "LC-BNK-2024-002",
    validation_session_id: "session-2",
    status: "approved",
    current_stage: "final_approval",
    assigned_to: "user-1",
    created_at: "2024-01-17T09:00:00Z",
    updated_at: "2024-01-18T11:00:00Z",
    last_action_at: "2024-01-18T11:00:00Z",
    due_date: "2024-01-19T17:00:00Z",
    metadata_: { priority: "medium", client_id: "client-2" },
  },
  {
    id: "approval-3",
    lc_number: "LC-BNK-2024-003",
    validation_session_id: "session-3",
    status: "rejected",
    current_stage: "senior_review",
    assigned_to: "user-2",
    created_at: "2024-01-16T08:00:00Z",
    updated_at: "2024-01-17T15:00:00Z",
    last_action_at: "2024-01-17T15:00:00Z",
    due_date: "2024-01-18T17:00:00Z",
    metadata_: { priority: "critical", client_id: "client-3" },
  },
];

const APPROVAL_STAGES = {
  analyst_review: "Analyst Review",
  senior_review: "Senior Review",
  compliance_approval: "Compliance Approval",
  final_approval: "Final Approval",
};

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
    case "approved":
      return "success";
    case "rejected":
      return "error";
    case "pending":
      return "pending";
    case "reopened":
      return "warning";
    case "escalated":
      return "warning";
    default:
      return "warning";
  }
};

export function ApprovalsView({ embedded = false }: { embedded?: boolean }) {
  const { toast } = useToast();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const [loading, setLoading] = React.useState(false);
  const [approvals, setApprovals] = React.useState(mockApprovals);
  const [statusFilter, setStatusFilter] = React.useState<string>("all");
  const [stageFilter, setStageFilter] = React.useState<string>("all");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [selectedApproval, setSelectedApproval] = React.useState<typeof mockApprovals[0] | null>(null);
  const [commentDialogOpen, setCommentDialogOpen] = React.useState(false);
  const [commentText, setCommentText] = React.useState("");
  const [selectedApprovalForAudit, setSelectedApprovalForAudit] = React.useState<typeof mockApprovals[0] | null>(null);
  const [auditLogs, setAuditLogs] = React.useState(mockAuditLogs);
  const [auditDialogOpen, setAuditDialogOpen] = React.useState(false);

  // In a real app, fetch approvals from API
  React.useEffect(() => {
    // Example: Fetch approvals
    // setLoading(true);
    // getBankWorkflowService().listApprovals({ status: statusFilter, current_stage: stageFilter }).then(setApprovals).finally(() => setLoading(false));
  }, [statusFilter, stageFilter]);

  const filteredApprovals = approvals.filter((approval) => {
    if (statusFilter !== "all" && approval.status !== statusFilter) return false;
    if (stageFilter !== "all" && approval.current_stage !== stageFilter) return false;
    if (searchQuery && !approval.lc_number.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const handleApprove = (approvalId: string) => {
    toast({
      title: "Approval Submitted",
      description: `LC ${approvalId} has been approved.`,
    });
    // In a real app, call API to approve
    setApprovals((prev) =>
      prev.map((a) => (a.id === approvalId ? { ...a, status: "approved" as const } : a))
    );
  };

  const handleReject = (approvalId: string) => {
    toast({
      title: "Rejection Submitted",
      description: `LC ${approvalId} has been rejected.`,
    });
    // In a real app, call API to reject
    setApprovals((prev) =>
      prev.map((a) => (a.id === approvalId ? { ...a, status: "rejected" as const } : a))
    );
  };

  const handleReopen = (approvalId: string) => {
    toast({
      title: "Approval Reopened",
      description: `LC ${approvalId} has been reopened for review.`,
    });
    // In a real app, call API to reopen
    setApprovals((prev) =>
      prev.map((a) => (a.id === approvalId ? { ...a, status: "reopened" as const } : a))
    );
  };

  const handleAddComment = () => {
    if (!selectedApproval || !commentText.trim()) return;

    toast({
      title: "Comment Added",
      description: `Comment added to approval ${selectedApproval.lc_number}.`,
    });
    setCommentText("");
    setCommentDialogOpen(false);
    // In a real app, call API to add comment
  };

  const handleViewAuditLogs = (approval: typeof mockApprovals[0]) => {
    setSelectedApprovalForAudit(approval);
    // In a real app, fetch audit logs for this approval
    // getBankWorkflowService().getApprovalAuditLogs(approval.id).then(setAuditLogs);
    setAuditDialogOpen(true);
  };

  const handleExportAuditLogs = () => {
    if (!selectedApprovalForAudit) return;

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
    a.download = `approval-audit-${selectedApprovalForAudit.lc_number}-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);

    toast({
      title: "Audit Logs Exported",
      description: `Audit logs for ${selectedApprovalForAudit.lc_number} have been exported.`,
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">LC Approvals</h2>
          <p className="text-muted-foreground">Review and approve LC validations through multi-stage workflow.</p>
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
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                  <SelectItem value="reopened">Reopened</SelectItem>
                  <SelectItem value="escalated">Escalated</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Stage</Label>
              <Select value={stageFilter} onValueChange={setStageFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All Stages" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Stages</SelectItem>
                  <SelectItem value="analyst_review">Analyst Review</SelectItem>
                  <SelectItem value="senior_review">Senior Review</SelectItem>
                  <SelectItem value="compliance_approval">Compliance Approval</SelectItem>
                  <SelectItem value="final_approval">Final Approval</SelectItem>
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

      {/* Approvals Table */}
      <Card>
        <CardHeader>
          <CardTitle>Approvals ({filteredApprovals.length})</CardTitle>
          <CardDescription>Manage LC approval workflow</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <RefreshCw className="h-5 w-5 animate-spin mr-2" /> Loading approvals...
            </div>
          ) : filteredApprovals.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileCheck className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No approvals found</p>
              <p className="text-sm">Adjust your filters to see more results</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>LC Number</TableHead>
                  <TableHead>Stage</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Assigned To</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead>Last Action</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredApprovals.map((approval) => (
                  <TableRow key={approval.id}>
                    <TableCell className="font-medium">{approval.lc_number}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{APPROVAL_STAGES[approval.current_stage as keyof typeof APPROVAL_STAGES]}</Badge>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={getStatusColor(approval.status)}>{approval.status}</StatusBadge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={approval.metadata_.priority === "critical" ? "destructive" : approval.metadata_.priority === "high" ? "default" : "secondary"}>
                        {approval.metadata_.priority}
                      </Badge>
                    </TableCell>
                    <TableCell>{approval.assigned_to ? `User ${approval.assigned_to.slice(-4)}` : "Unassigned"}</TableCell>
                    <TableCell>{approval.due_date ? new Date(approval.due_date).toLocaleDateString() : "N/A"}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{formatTimeAgo(approval.last_action_at)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewAuditLogs(approval)}
                          tooltip="View Audit Logs"
                        >
                          <History className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedApproval(approval);
                            setCommentDialogOpen(true);
                          }}
                        >
                          <MessageSquare className="h-4 w-4" />
                        </Button>
                        {approval.status === "pending" && (
                          <>
                            <Button variant="default" size="sm" onClick={() => handleApprove(approval.id)}>
                              <CheckCircle2 className="h-4 w-4 mr-1" /> Approve
                            </Button>
                            <Button variant="destructive" size="sm" onClick={() => handleReject(approval.id)}>
                              <XCircle className="h-4 w-4 mr-1" /> Reject
                            </Button>
                          </>
                        )}
                        {approval.status === "rejected" && (
                          <Button variant="outline" size="sm" onClick={() => handleReopen(approval.id)}>
                            <RefreshCw className="h-4 w-4 mr-1" /> Reopen
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
              Add a comment to approval {selectedApproval?.lc_number}
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

      {/* Audit Logs Dialog */}
      <Dialog open={auditDialogOpen} onOpenChange={setAuditDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <div>
                <DialogTitle>Audit Logs</DialogTitle>
                <DialogDescription>
                  Complete audit trail for approval {selectedApprovalForAudit?.lc_number}
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

