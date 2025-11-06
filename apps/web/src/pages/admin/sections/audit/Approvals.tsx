import * as React from "react";

import { AdminEmptyState, AdminToolbar } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { Check, FileDiff, X } from "lucide-react";

import { getAdminService } from "@/lib/admin/services/index";
import type { ApprovalRequest, ApprovalStatus } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();
const STATUSES: ApprovalStatus[] = ["pending", "approved", "rejected"];

function formatRelativeTime(iso?: string) {
  if (!iso) return "-";
  const diffMs = Date.now() - new Date(iso).getTime();
  if (diffMs < 60_000) return "just now";
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function DiffPanel({ before, after }: { before?: Record<string, unknown>; after?: Record<string, unknown> }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="rounded-lg border border-border/60 bg-muted/40 p-4">
        <h4 className="text-sm font-medium text-muted-foreground">Before</h4>
        <pre className="mt-2 max-h-64 overflow-auto text-xs text-foreground/70">
          {JSON.stringify(before ?? { note: "No previous state" }, null, 2)}
        </pre>
      </div>
      <div className="rounded-lg border border-border/60 bg-muted/40 p-4">
        <h4 className="text-sm font-medium text-muted-foreground">After</h4>
        <pre className="mt-2 max-h-64 overflow-auto text-xs text-foreground/70">
          {JSON.stringify(after ?? { note: "No requested change" }, null, 2)}
        </pre>
      </div>
    </div>
  );
}

export function AuditApprovals() {
  const { toast } = useToast();
  const audit = useAdminAudit("audit-approvals");
  const [activeTab, setActiveTab] = React.useState<ApprovalStatus>("pending");
  const [approvals, setApprovals] = React.useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [actionId, setActionId] = React.useState<string | null>(null);

  const loadApprovals = React.useCallback(() => {
    setLoading(true);
    service
      .listApprovalRequests({ status: activeTab, page: 1, pageSize: 20 })
      .then((result) => setApprovals(result.items))
      .finally(() => setLoading(false));
  }, [activeTab]);

  React.useEffect(() => {
    loadApprovals();
  }, [loadApprovals]);

  const resolveApproval = async (id: string, outcome: "approve" | "reject") => {
    let reason: string | undefined;
    if (outcome === "reject") {
      reason = window.prompt("Provide rejection reason (optional)") ?? undefined;
    }
    setActionId(id);
    const result = await service.resolveApproval(id, outcome, reason);
    setActionId(null);
    toast({
      title: result.success ? `Request ${outcome}d` : `Failed to ${outcome}`,
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      await audit(outcome === "approve" ? "approve_request" : "reject_request", {
        entityId: id,
        metadata: { reason },
      });
      loadApprovals();
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="Approval workflows"
        description="Maker-checker queue for sensitive administrative changes."
      />

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as ApprovalStatus)}>
        <TabsList className="grid w-full grid-cols-3">
          {STATUSES.map((status) => (
            <TabsTrigger key={status} value={status} className="capitalize">
              {status}
            </TabsTrigger>
          ))}
        </TabsList>

        {STATUSES.map((status) => (
          <TabsContent key={status} value={status} className="mt-6 space-y-4">
            {loading && activeTab === status ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, index) => (
                  <div key={index} className="h-24 rounded-lg border border-border/50 bg-muted/40" />
                ))}
              </div>
            ) : approvals.length === 0 ? (
              <AdminEmptyState
                title={`No ${status} requests`}
                description={
                  status === "pending"
                    ? "You're all caught up."
                    : "No historical entries for this state in the mock dataset."
                }
              />
            ) : (
              approvals.map((approval) => (
                <div
                  key={approval.id}
                  className="flex flex-col gap-4 rounded-lg border border-border/60 bg-card/60 p-4 md:flex-row md:items-center md:justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="secondary" className="capitalize">
                        {approval.type.replace(/_/g, " ")}
                      </Badge>
                      <span className="text-xs text-muted-foreground">Submitted {formatRelativeTime(approval.submittedAt)}</span>
                      <span className="text-xs text-muted-foreground">By {approval.submittedBy}</span>
                    </div>
                    <p className="text-sm text-foreground">
                      {approval.comments?.[0]?.body ?? "Change request awaiting review."}
                    </p>
                    <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                      {approval.approvers.map((approver) => (
                        <Badge key={approver} variant="outline">
                          Approver: {approver}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <div className="flex flex-col items-start gap-2 md:items-end">
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button variant="outline" size="sm" className="gap-2">
                          <FileDiff className="h-4 w-4" /> View diff
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-3xl">
                        <DialogHeader>
                          <DialogTitle>Change details</DialogTitle>
                          <DialogDescription>Review requested modifications before taking action.</DialogDescription>
                        </DialogHeader>
                        <DiffPanel before={approval.before ?? undefined} after={approval.after ?? undefined} />
                      </DialogContent>
                    </Dialog>

                    {status === "pending" ? (
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          className="gap-1 text-emerald-600"
                          onClick={() => resolveApproval(approval.id, "approve")}
                          disabled={actionId === approval.id}
                        >
                          <Check className="h-4 w-4" /> Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="gap-1 text-rose-600"
                          onClick={() => resolveApproval(approval.id, "reject")}
                          disabled={actionId === approval.id}
                        >
                          <X className="h-4 w-4" /> Reject
                        </Button>
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        {status === "approved"
                          ? `Approved ${formatRelativeTime(approval.approvedAt)}.`
                          : `Rejected ${formatRelativeTime(approval.rejectedAt)}.`}
                      </p>
                    )}
                  </div>
                </div>
              ))
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

export default AuditApprovals;
