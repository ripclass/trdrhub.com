import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  FileCheck,
  Send,
  CheckCircle,
  XCircle,
  Clock,
  ArrowLeft,
  FileText,
  AlertTriangle,
  Loader2,
  Mail,
  Edit,
  History,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface WorkflowStatus {
  application_id: string;
  reference_number: string;
  current_status: string;
  available_actions: Array<{
    action: string;
    label: string;
    endpoint: string | null;
  }>;
  workflow_steps: Array<{
    step: string;
    label: string;
    completed: boolean;
  }>;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
}

interface LCApplication {
  id: string;
  reference_number: string;
  name: string | null;
  status: string;
  amount: number;
  currency: string;
  beneficiary_name: string;
  applicant_name: string;
  risk_score: number | null;
  validation_issues: any[];
}

const statusIcons: Record<string, React.ReactNode> = {
  draft: <FileText className="h-5 w-5" />,
  review: <Clock className="h-5 w-5" />,
  submitted: <Send className="h-5 w-5" />,
  approved: <CheckCircle className="h-5 w-5" />,
  rejected: <XCircle className="h-5 w-5" />,
  amended: <Edit className="h-5 w-5" />,
};

const statusColors: Record<string, string> = {
  draft: "bg-slate-500",
  review: "bg-amber-500",
  submitted: "bg-blue-500",
  approved: "bg-emerald-500",
  rejected: "bg-red-500",
  amended: "bg-purple-500",
};

export default function LCWorkflowPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { session } = useAuth();

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [workflow, setWorkflow] = useState<WorkflowStatus | null>(null);
  const [application, setApplication] = useState<LCApplication | null>(null);
  
  // Dialog states
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [submitNotes, setSubmitNotes] = useState("");

  useEffect(() => {
    if (id && session?.access_token) {
      fetchWorkflowStatus();
      fetchApplication();
    }
  }, [id, session?.access_token]);

  const fetchWorkflowStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/lc-builder/applications/${id}/workflow-status`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setWorkflow(data);
      }
    } catch (error) {
      console.error("Error fetching workflow:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchApplication = async () => {
    try {
      const res = await fetch(`${API_BASE}/lc-builder/applications/${id}`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setApplication(data);
      }
    } catch (error) {
      console.error("Error fetching application:", error);
    }
  };

  const handleAction = async (action: string, endpoint: string | null, body?: any) => {
    if (!endpoint) {
      // Handle local actions
      if (action === "edit") {
        navigate(`/lc-builder/dashboard/edit/${id}`);
        return;
      }
      if (action === "export") {
        navigate(`/lc-builder/dashboard/edit/${id}?tab=export`);
        return;
      }
      return;
    }

    setActionLoading(true);
    try {
      const res = await fetch(`${API_BASE}/lc-builder/applications/${id}${endpoint}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
          "Content-Type": "application/json",
        },
        body: body ? JSON.stringify(body) : undefined,
      });

      if (res.ok) {
        const data = await res.json();
        toast({
          title: "Success",
          description: data.message || "Action completed successfully",
        });
        fetchWorkflowStatus();
        fetchApplication();
      } else {
        const error = await res.json();
        throw new Error(error.detail || "Action failed");
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to complete action",
        variant: "destructive",
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleSubmitForReview = async () => {
    await handleAction("submit_for_review", "/submit-for-review", { notes: submitNotes });
    setShowSubmitDialog(false);
    setSubmitNotes("");
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      toast({
        title: "Required",
        description: "Please provide a rejection reason",
        variant: "destructive",
      });
      return;
    }
    await handleAction("reject", `/reject?rejection_reason=${encodeURIComponent(rejectReason)}`);
    setShowRejectDialog(false);
    setRejectReason("");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  if (!workflow || !application) {
    return (
      <div className="min-h-screen bg-slate-950 p-6">
        <p className="text-slate-400">Application not found</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate("/lc-builder/dashboard")}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              <div>
                <h1 className="text-xl font-bold text-white flex items-center gap-2">
                  <FileCheck className="h-5 w-5 text-emerald-400" />
                  Workflow Status
                </h1>
                <p className="text-sm text-slate-400">
                  {workflow.reference_number}
                </p>
              </div>
            </div>
            <Badge className={cn(statusColors[workflow.current_status], "text-white")}>
              {workflow.current_status.toUpperCase()}
            </Badge>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Workflow Progress */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">Workflow Progress</CardTitle>
            <CardDescription>Track your LC application through the approval process</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              {workflow.workflow_steps.map((step, index) => (
                <div key={step.step} className="flex items-center flex-1">
                  <div className="flex flex-col items-center">
                    <div
                      className={cn(
                        "w-10 h-10 rounded-full flex items-center justify-center",
                        step.completed
                          ? "bg-emerald-500 text-white"
                          : workflow.current_status === step.step
                          ? "bg-amber-500 text-white"
                          : "bg-slate-700 text-slate-400"
                      )}
                    >
                      {step.completed ? (
                        <CheckCircle className="h-5 w-5" />
                      ) : (
                        statusIcons[step.step] || <Clock className="h-5 w-5" />
                      )}
                    </div>
                    <span className={cn(
                      "text-sm mt-2",
                      step.completed || workflow.current_status === step.step
                        ? "text-white"
                        : "text-slate-500"
                    )}>
                      {step.label}
                    </span>
                  </div>
                  {index < workflow.workflow_steps.length - 1 && (
                    <div
                      className={cn(
                        "flex-1 h-1 mx-2",
                        step.completed ? "bg-emerald-500" : "bg-slate-700"
                      )}
                    />
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Application Summary */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Application Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-slate-400">Reference</p>
                  <p className="text-white font-medium">{application.reference_number}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Amount</p>
                  <p className="text-emerald-400 font-bold text-lg">
                    {application.currency} {application.amount?.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Beneficiary</p>
                  <p className="text-white">{application.beneficiary_name}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Applicant</p>
                  <p className="text-white">{application.applicant_name}</p>
                </div>
              </div>

              {application.risk_score !== null && (
                <div className="pt-4 border-t border-slate-700">
                  <p className="text-sm text-slate-400 mb-2">Risk Score</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={cn(
                          "h-full rounded-full",
                          application.risk_score <= 20
                            ? "bg-emerald-500"
                            : application.risk_score <= 50
                            ? "bg-amber-500"
                            : "bg-red-500"
                        )}
                        style={{ width: `${application.risk_score}%` }}
                      />
                    </div>
                    <span className={cn(
                      "text-sm font-bold",
                      application.risk_score <= 20
                        ? "text-emerald-400"
                        : application.risk_score <= 50
                        ? "text-amber-400"
                        : "text-red-400"
                    )}>
                      {application.risk_score.toFixed(0)}%
                    </span>
                  </div>
                </div>
              )}

              {application.validation_issues?.length > 0 && (
                <div className="pt-4 border-t border-slate-700">
                  <p className="text-sm text-slate-400 mb-2">
                    <AlertTriangle className="h-4 w-4 inline mr-1 text-amber-400" />
                    {application.validation_issues.length} Validation Issue(s)
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Available Actions */}
          <Card className="bg-slate-800 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Available Actions</CardTitle>
              <CardDescription>Actions you can take on this application</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {workflow.available_actions.map((action) => (
                <Button
                  key={action.action}
                  variant={
                    action.action === "approve"
                      ? "default"
                      : action.action === "reject"
                      ? "destructive"
                      : "outline"
                  }
                  className={cn(
                    "w-full justify-start",
                    action.action === "approve" && "bg-emerald-600 hover:bg-emerald-700",
                    action.action === "submit_for_review" && "bg-blue-600 hover:bg-blue-700 text-white"
                  )}
                  onClick={() => {
                    if (action.action === "submit_for_review" || action.action === "resubmit") {
                      setShowSubmitDialog(true);
                    } else if (action.action === "reject") {
                      setShowRejectDialog(true);
                    } else {
                      handleAction(action.action, action.endpoint);
                    }
                  }}
                  disabled={actionLoading}
                >
                  {actionLoading ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : action.action === "approve" ? (
                    <CheckCircle className="h-4 w-4 mr-2" />
                  ) : action.action === "reject" ? (
                    <XCircle className="h-4 w-4 mr-2" />
                  ) : action.action === "submit_for_review" || action.action === "resubmit" ? (
                    <Send className="h-4 w-4 mr-2" />
                  ) : action.action === "edit" ? (
                    <Edit className="h-4 w-4 mr-2" />
                  ) : action.action === "amend" ? (
                    <History className="h-4 w-4 mr-2" />
                  ) : (
                    <FileText className="h-4 w-4 mr-2" />
                  )}
                  {action.label}
                </Button>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Timeline */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-start gap-4">
                <div className="w-2 h-2 mt-2 rounded-full bg-emerald-500" />
                <div>
                  <p className="text-white">Application Created</p>
                  <p className="text-sm text-slate-400">
                    {new Date(workflow.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
              {workflow.submitted_at && (
                <div className="flex items-start gap-4">
                  <div className="w-2 h-2 mt-2 rounded-full bg-blue-500" />
                  <div>
                    <p className="text-white">Submitted for Review</p>
                    <p className="text-sm text-slate-400">
                      {new Date(workflow.submitted_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              )}
              <div className="flex items-start gap-4">
                <div className="w-2 h-2 mt-2 rounded-full bg-slate-500" />
                <div>
                  <p className="text-white">Last Updated</p>
                  <p className="text-sm text-slate-400">
                    {new Date(workflow.updated_at).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Submit for Review Dialog */}
      <Dialog open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Send className="h-5 w-5 text-blue-400" />
              Submit for Review
            </DialogTitle>
            <DialogDescription>
              Add any notes for the reviewer (optional)
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Textarea
              placeholder="Add notes for the reviewer..."
              value={submitNotes}
              onChange={(e) => setSubmitNotes(e.target.value)}
              rows={4}
            />
            <p className="text-sm text-slate-400 mt-2 flex items-center gap-1">
              <Mail className="h-4 w-4" />
              You will receive an email notification when the status changes.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSubmitDialog(false)}>
              Cancel
            </Button>
            <Button
              className="bg-blue-600 hover:bg-blue-700"
              onClick={handleSubmitForReview}
              disabled={actionLoading}
            >
              {actionLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Submit for Review
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-red-400" />
              Reject Application
            </DialogTitle>
            <DialogDescription>
              Please provide a reason for rejection
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Textarea
              placeholder="Reason for rejection (required)..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={4}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRejectDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={actionLoading || !rejectReason.trim()}
            >
              {actionLoading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Reject Application
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

