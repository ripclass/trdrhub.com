// Concierge review queue — Phase 1 launch (2026-07).
//
// Operator surface for the service-as-software flow: every customer LCopilot
// job lands here (state engine_complete/under_review/needs_info) before the
// customer can see results. The operator curates findings (edit / suppress /
// annotate), attaches a summary note, and hits Approve & Deliver — which
// generates the cited PDF report, opens the customer gate, and emails them.
//
// Backend: apps/api/app/routers/lcopilot_review.py (require_sysadmin).
// Finding edits mutate structured_result.issues in place — the single source
// of truth for both the customer results UI and the delivered report.
import * as React from "react";

import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  EyeOff,
  MessageSquarePlus,
  Pencil,
  RefreshCw,
  Send,
  StickyNote,
} from "lucide-react";

// ---------------------------------------------------------------------------
// API types (mirror lcopilot_review.py payloads)
// ---------------------------------------------------------------------------

interface QueueItem {
  customer_email?: string | null;
  customer_name?: string | null;
  job_id: string;
  review_state: string;
  workflow_type: string | null;
  user_id: string | null;
  company_id: string | null;
  finding_count: number;
  payment_status?: string | null;
  submitted_at: string | null;
  state_changed_at: string | null;
}

interface TimelineEvent {
  from_state: string | null;
  to_state: string;
  reason: string | null;
  at: string | null;
}

interface Finding {
  id?: string;
  __discrepancy_uuid?: string;
  rule?: string;
  rule_id?: string;
  title?: string;
  message?: string;
  description?: string;
  severity?: string;
  expected?: string;
  actual?: string;
  found?: string;
  found_evidence?: string;
  clause_cited?: string;
  suggestion?: string;
  suggested_fix?: string;
  reviewer_note?: string;
  documentName?: string;
  document_type?: string;
  ucp_reference?: string | null;
  isbp_reference?: string | null;
  [key: string]: unknown;
}

interface ReviewDetail {
  job_id: string;
  review_state: string;
  review_note: string | null;
  workflow_type: string | null;
  payment_status?: string | null;
  payment_product_id?: string | null;
  findings: Finding[];
  documents?: Array<{
    id: string;
    document_type: string;
    filename: string;
    content_type: string;
    file_size: number;
    download_url: string | null;
  }>;
  timeline: TimelineEvent[];
  structured_result?: {
    intake_answers?: Record<string, unknown>;
    _engine_error?: string;
    readiness_summary?: { gaps?: number; partial?: number; in_place?: number; rules_consulted?: number };
    [key: string]: unknown;
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function findingId(f: Finding): string | null {
  const id = f.id || f.__discrepancy_uuid || f.rule || f.rule_id;
  return id ? String(id) : null;
}

function findingTitle(f: Finding): string {
  return f.title || f.message || f.description || f.rule || "Finding";
}

function findingBody(f: Finding): string {
  const body = f.description || f.message || "";
  return body === findingTitle(f) ? "" : body;
}

function findingEvidence(f: Finding): string {
  return f.found_evidence || f.actual || f.found || "";
}

function findingFix(f: Finding): string {
  return f.suggested_fix || f.suggestion || "";
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: "bg-red-100 text-red-800 border-red-200",
  major: "bg-orange-100 text-orange-800 border-orange-200",
  warning: "bg-amber-100 text-amber-800 border-amber-200",
  minor: "bg-yellow-50 text-yellow-800 border-yellow-200",
  info: "bg-blue-50 text-blue-800 border-blue-200",
};

function SeverityBadge({ severity }: { severity?: string }) {
  const s = (severity || "minor").toLowerCase();
  return (
    <Badge variant="outline" className={cn("uppercase text-[10px] tracking-wide", SEVERITY_STYLES[s] || SEVERITY_STYLES.minor)}>
      {s}
    </Badge>
  );
}

// Theme-safe, on-palette state colors (opacity shades render correctly in
// both light and dark; purple was off-brand — audit 2026-07-07).
const STATE_STYLES: Record<string, string> = {
  engine_complete: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30",
  under_review: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30",
  needs_info: "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/30",
  delivered: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
};

function StateBadge({ state }: { state?: string | null }) {
  if (!state) return null;
  return (
    <Badge variant="outline" className={cn("text-xs", STATE_STYLES[state] || "")}>
      {state.replace(/_/g, " ")}
    </Badge>
  );
}

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function errMessage(err: unknown): string {
  const anyErr = err as { response?: { data?: { detail?: string } }; message?: string };
  return anyErr?.response?.data?.detail || anyErr?.message || "Request failed";
}

// ---------------------------------------------------------------------------
// Edit-finding dialog
// ---------------------------------------------------------------------------

interface EditState {
  finding: Finding;
  mode: "edit" | "annotate";
}

function EditFindingDialog({
  edit,
  onClose,
  onSave,
  busy,
  onSuggest,
}: {
  edit: EditState | null;
  onClose: () => void;
  onSave: (payload: Record<string, string>) => void;
  busy: boolean;
  onSuggest?: (finding: Finding) => Promise<string | null>;
}) {
  const [severity, setSeverity] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [fix, setFix] = React.useState("");
  const [note, setNote] = React.useState("");
  const [suggesting, setSuggesting] = React.useState(false);

  React.useEffect(() => {
    if (edit) {
      setSeverity(edit.finding.severity || "");
      setMessage(findingTitle(edit.finding));
      setFix(findingFix(edit.finding));
      setNote(edit.finding.reviewer_note || "");
    }
  }, [edit]);

  if (!edit) return null;
  const isAnnotate = edit.mode === "annotate";

  const handleSave = () => {
    const payload: Record<string, string> = { action: edit.mode };
    if (isAnnotate) {
      if (note.trim()) payload.reviewer_note = note.trim();
    } else {
      if (severity && severity !== (edit.finding.severity || "")) payload.severity = severity;
      if (message.trim() && message.trim() !== findingTitle(edit.finding)) payload.message = message.trim();
      if (fix.trim() && fix.trim() !== findingFix(edit.finding)) payload.suggested_fix = fix.trim();
      if (note.trim()) payload.reviewer_note = note.trim();
    }
    onSave(payload);
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isAnnotate ? "Annotate finding" : "Edit finding"}</DialogTitle>
          <DialogDescription className="line-clamp-2">{findingTitle(edit.finding)}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          {!isAnnotate && (
            <>
              <div className="space-y-1.5">
                <Label>Severity</Label>
                <Select value={severity} onValueChange={setSeverity}>
                  <SelectTrigger>
                    <SelectValue placeholder="Keep current severity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="critical">Critical</SelectItem>
                    <SelectItem value="major">Major</SelectItem>
                    <SelectItem value="minor">Minor</SelectItem>
                    <SelectItem value="info">Info</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Finding text</Label>
                <Textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3} />
              </div>
              <div className="space-y-1.5">
                <Label>Suggested fix</Label>
                <Textarea value={fix} onChange={(e) => setFix(e.target.value)} rows={2} />
              </div>
            </>
          )}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label>Reviewer note {isAnnotate ? "" : "(optional)"}</Label>
              {onSuggest && (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="h-7 text-xs"
                  disabled={suggesting || busy}
                  onClick={async () => {
                    setSuggesting(true);
                    const text = await onSuggest(edit.finding);
                    if (text) setNote(text);
                    setSuggesting(false);
                  }}
                >
                  {suggesting ? "Drafting..." : "AI draft"}
                </Button>
              )}
            </div>
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={4}
              placeholder="Visible on the finding in the delivered report"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={busy || (isAnnotate && !note.trim())}>
            {busy ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Main section
// ---------------------------------------------------------------------------

export function ReviewQueue() {
  const { toast } = useToast();

  const [items, setItems] = React.useState<QueueItem[]>([]);
  const [loadingList, setLoadingList] = React.useState(true);
  const [listError, setListError] = React.useState<string | null>(null);
  // "queue" = jobs to review; "awaiting_payment" = submitted jobs whose
  // customer hasn't paid yet (offline payers get marked paid here).
  const [view, setView] = React.useState<"queue" | "awaiting_payment">("queue");

  const [selectedId, setSelectedId] = React.useState<string | null>(null);
  const [detail, setDetail] = React.useState<ReviewDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = React.useState(false);

  const [note, setNote] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [edit, setEdit] = React.useState<EditState | null>(null);
  const [needsInfoOpen, setNeedsInfoOpen] = React.useState(false);
  const [needsInfoReason, setNeedsInfoReason] = React.useState("");
  const [deliverOpen, setDeliverOpen] = React.useState(false);

  const loadList = React.useCallback(async () => {
    setLoadingList(true);
    setListError(null);
    try {
      const url =
        view === "awaiting_payment"
          ? "/api/admin/review-queue?state=submitted"
          : "/api/admin/review-queue";
      const { data } = await api.get<{ count: number; items: QueueItem[] }>(url);
      setItems(data.items ?? []);
    } catch (err) {
      setListError(errMessage(err));
    } finally {
      setLoadingList(false);
    }
  }, [view]);

  const loadDetail = React.useCallback(async (jobId: string) => {
    setLoadingDetail(true);
    try {
      const { data } = await api.get<ReviewDetail>(`/api/admin/review-queue/${jobId}`);
      setDetail(data);
      setNote(data.review_note || "");
    } catch (err) {
      toast({ title: "Failed to load job", description: errMessage(err), variant: "destructive" });
      setSelectedId(null);
    } finally {
      setLoadingDetail(false);
    }
  }, [toast]);

  React.useEffect(() => {
    void loadList();
  }, [loadList]);

  React.useEffect(() => {
    if (selectedId) void loadDetail(selectedId);
    else setDetail(null);
  }, [selectedId, loadDetail]);

  const runAction = async (fn: () => Promise<void>, successMsg: string) => {
    setBusy(true);
    try {
      await fn();
      toast({ title: successMsg });
    } catch (err) {
      toast({ title: "Action failed", description: errMessage(err), variant: "destructive" });
    } finally {
      setBusy(false);
    }
  };

  const suppressFinding = (f: Finding) => {
    const fid = findingId(f);
    if (!fid || !selectedId) return;
    void runAction(async () => {
      await api.post(`/api/admin/review-queue/${selectedId}/findings/${encodeURIComponent(fid)}`, {
        action: "suppress",
      });
      await loadDetail(selectedId);
    }, "Finding suppressed");
  };

  const saveEdit = (payload: Record<string, string>) => {
    if (!edit || !selectedId) return;
    const fid = findingId(edit.finding);
    if (!fid) return;
    void runAction(async () => {
      await api.post(`/api/admin/review-queue/${selectedId}/findings/${encodeURIComponent(fid)}`, payload);
      setEdit(null);
      await loadDetail(selectedId);
    }, "Finding updated");
  };

  const saveNote = () => {
    if (!selectedId) return;
    void runAction(async () => {
      await api.post(`/api/admin/review-queue/${selectedId}/note`, { note });
    }, "Note saved");
  };

  const [suggestBusy, setSuggestBusy] = React.useState(false);
  const suggestText = React.useCallback(
    async (kind: "annotation" | "summary", findingIdArg?: string): Promise<string | null> => {
      if (!selectedId) return null;
      try {
        const res = await api.post(`/api/admin/review-queue/${selectedId}/suggest`, {
          kind,
          finding_id: findingIdArg,
        });
        return (res.data && res.data.suggestion) || null;
      } catch (err) {
        toast({ title: "AI draft failed", description: errMessage(err), variant: "destructive" });
        return null;
      }
    },
    [selectedId, toast],
  );

  const draftSummary = async () => {
    setSuggestBusy(true);
    const text = await suggestText("summary");
    if (text) setNote(text);
    setSuggestBusy(false);
  };

  const [intakeOpen, setIntakeOpen] = React.useState(false);
  const [intakeEmail, setIntakeEmail] = React.useState("");
  const [intakeName, setIntakeName] = React.useState("");
  const [intakeFiles, setIntakeFiles] = React.useState<FileList | null>(null);
  const [intakeBusy, setIntakeBusy] = React.useState(false);

  const submitIntake = async () => {
    if (!intakeEmail.trim() || !intakeFiles || intakeFiles.length === 0) return;
    setIntakeBusy(true);
    try {
      const form = new FormData();
      Array.from(intakeFiles).forEach((f) => form.append("files", f));
      form.append("customer_email", intakeEmail.trim());
      if (intakeName.trim()) form.append("customer_name", intakeName.trim());
      const res = await api.post("/api/admin/review-queue/intake", form, {
        timeout: 20 * 60 * 1000,
      });
      toast({
        title: "Engine run complete",
        description: `Job ${String(res.data?.job_id || "").slice(0, 8)} is in the queue for ${intakeEmail.trim()}.`,
      });
      setIntakeOpen(false);
      setIntakeEmail("");
      setIntakeName("");
      setIntakeFiles(null);
      await loadList();
    } catch (err) {
      toast({ title: "Intake failed", description: errMessage(err), variant: "destructive" });
    } finally {
      setIntakeBusy(false);
    }
  };

  const sendNeedsInfo = () => {
    if (!selectedId || !needsInfoReason.trim()) return;
    void runAction(async () => {
      await api.post(`/api/admin/review-queue/${selectedId}/needs-info`, { reason: needsInfoReason.trim() });
      setNeedsInfoOpen(false);
      setNeedsInfoReason("");
      await loadDetail(selectedId);
      await loadList();
    }, "Marked as needs info");
  };

  const deliver = () => {
    if (!selectedId) return;
    void runAction(async () => {
      // Body is Optional[ReviewNote] server-side — an empty object would 422
      // on the required `note` field, so omit the body entirely when blank.
      await api.post(
        `/api/admin/review-queue/${selectedId}/deliver`,
        note.trim() ? { note: note.trim() } : undefined,
      );
      setDeliverOpen(false);
      await loadList();
      setSelectedId(null);
    }, "Report delivered to customer");
  };

  // CBAM/EUDR readiness jobs: re-run the rules engine (used when the intake
  // arrived while the rules API was unreachable — findings lack citations).
  const rerunEngine = () => {
    if (!selectedId) return;
    void runAction(async () => {
      await api.post(`/api/admin/review-queue/${selectedId}/rerun-engine`);
      await loadDetail(selectedId);
    }, "Engine re-run complete");
  };

  // Offline payment (bank transfer / bKash / invoice) — records it and
  // advances the job into the review queue.
  const markPaid = () => {
    if (!selectedId) return;
    void runAction(async () => {
      await api.post(`/api/admin/review-queue/${selectedId}/mark-paid`);
      await loadDetail(selectedId);
      await loadList();
    }, "Offline payment recorded — job is now in the review queue");
  };

  // ------------------------------------------------------------------ list

  if (!selectedId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Review Queue</h1>
            <p className="text-muted-foreground text-sm">
              {view === "queue"
                ? "Customer reports awaiting specialist review before delivery."
                : "Submitted jobs whose payment hasn't cleared — record offline payments here."}
            </p>
          </div>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => setIntakeOpen(true)}>
              Email intake
            </Button>
            <Button variant="outline" size="sm" onClick={() => void loadList()} disabled={loadingList}>
              <RefreshCw className={cn("h-4 w-4 mr-2", loadingList && "animate-spin")} />
              Refresh
            </Button>
          </div>
        </div>

        <div className="flex gap-2">
          <Button
            size="sm"
            variant={view === "queue" ? "default" : "outline"}
            onClick={() => setView("queue")}
          >
            To review
          </Button>
          <Button
            size="sm"
            variant={view === "awaiting_payment" ? "default" : "outline"}
            onClick={() => setView("awaiting_payment")}
          >
            Awaiting payment
          </Button>
        </div>

        {loadingList ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        ) : listError ? (
          <Card>
            <CardContent className="py-8 text-center">
              <AlertTriangle className="h-8 w-8 mx-auto text-destructive mb-2" />
              <p className="text-sm text-muted-foreground">{listError}</p>
            </CardContent>
          </Card>
        ) : items.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <CheckCircle2 className="h-8 w-8 mx-auto text-green-500 mb-2" />
              <p className="font-medium">Queue is clear</p>
              <p className="text-sm text-muted-foreground">
                New customer submissions appear here once the engine finishes.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <Card
                key={item.job_id}
                className="cursor-pointer hover:border-primary/50 transition-colors"
                onClick={() => setSelectedId(item.job_id)}
              >
                <CardContent className="py-4 flex flex-wrap items-center gap-x-6 gap-y-2">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">
                        {item.customer_name || item.customer_email || "Unknown customer"}
                      </span>
                      <StateBadge state={item.review_state} />
                      {item.payment_status === "pending" && (
                        <Badge variant="outline" className="text-xs bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/30">
                          awaiting payment
                        </Badge>
                      )}
                      {item.payment_status === "refunded" && (
                        <Badge variant="outline" className="text-xs bg-muted text-muted-foreground border-border">
                          refunded
                        </Badge>
                      )}
                    </div>
                    <div className="text-sm mt-1 text-muted-foreground">
                      {item.customer_name && item.customer_email ? <>{item.customer_email} · </> : null}
                      {(item.workflow_type || "validation").replace(/_/g, " ")} ·{" "}
                      <span className="font-medium text-foreground">{item.finding_count}</span> finding{item.finding_count === 1 ? "" : "s"}
                      {" · "}
                      <span className="font-mono text-xs">{item.job_id.slice(0, 8)}</span>
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground text-right">
                    <div>Submitted {formatWhen(item.submitted_at)}</div>
                    <div>In state since {formatWhen(item.state_changed_at)}</div>
                  </div>
                  <Button size="sm" variant="secondary" onClick={() => setSelectedId(item.job_id)}>
                    Review
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ---------------------------------------------------------------- detail

  const deliverable =
    detail && ["under_review", "engine_complete"].includes(detail.review_state);
  const detailCustomer = (detail as (ReviewDetail & { customer_email?: string | null }) | null)?.customer_email;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => setSelectedId(null)}>
            <ArrowLeft className="h-4 w-4 mr-1" /> Queue
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight">
                {detailCustomer || `Job ${selectedId.slice(0, 8)}`}
              </h1>
              {detail && <StateBadge state={detail.review_state} />}
            </div>
            {detail && (
              <p className="text-muted-foreground text-xs">
                {(detail.workflow_type || "validation").replace(/_/g, " ")} · {detail.findings.length} finding
                {detail.findings.length === 1 ? "" : "s"} · <span className="font-mono">{selectedId.slice(0, 8)}</span>
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setNeedsInfoOpen(true)} disabled={busy || !deliverable}>
            <MessageSquarePlus className="h-4 w-4 mr-2" /> Needs info
          </Button>
          <Button size="sm" onClick={() => setDeliverOpen(true)} disabled={busy || !deliverable}>
            <Send className="h-4 w-4 mr-2" /> Approve &amp; Deliver
          </Button>
        </div>
      </div>

      {loadingDetail || !detail ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
          {/* Findings */}
          <div className="space-y-3">
            {detail.findings.length === 0 ? (
              <Card>
                <CardContent className="py-10 text-center">
                  <CheckCircle2 className="h-8 w-8 mx-auto text-green-500 mb-2" />
                  <p className="font-medium">No findings</p>
                  <p className="text-sm text-muted-foreground">
                    The engine found no discrepancies (or all were suppressed). Deliver when ready.
                  </p>
                </CardContent>
              </Card>
            ) : (
              detail.findings.map((f, idx) => {
                const fid = findingId(f);
                return (
                  <Card key={fid || idx}>
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <SeverityBadge severity={f.severity} />
                            {(f.rule || f.rule_id) && (
                              <span className="font-mono text-[11px] text-muted-foreground">{f.rule || f.rule_id}</span>
                            )}
                            {(f.documentName || f.document_type) && (
                              <Badge variant="secondary" className="text-[10px]">
                                {String(f.documentName || f.document_type).replace(/_/g, " ")}
                              </Badge>
                            )}
                          </div>
                          <CardTitle className="text-sm leading-snug">{findingTitle(f)}</CardTitle>
                        </div>
                        <div className="flex shrink-0 gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Edit"
                            disabled={busy || !fid || !deliverable}
                            onClick={() => setEdit({ finding: f, mode: "edit" })}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Annotate"
                            disabled={busy || !fid || !deliverable}
                            onClick={() => setEdit({ finding: f, mode: "annotate" })}
                          >
                            <StickyNote className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Suppress (remove from delivered report)"
                            disabled={busy || !fid || !deliverable}
                            onClick={() => {
                              if (window.confirm("Suppress this finding? It will not appear in the delivered report.")) {
                                suppressFinding(f);
                              }
                            }}
                          >
                            <EyeOff className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm">
                      {findingBody(f) && <p className="text-muted-foreground">{findingBody(f)}</p>}
                      {f.clause_cited && (
                        <p>
                          <span className="font-medium">LC clause:</span>{" "}
                          <span className="text-muted-foreground">{f.clause_cited}</span>
                        </p>
                      )}
                      {f.expected && (
                        <p>
                          <span className="font-medium">Expected:</span>{" "}
                          <span className="text-muted-foreground">{f.expected}</span>
                        </p>
                      )}
                      {findingEvidence(f) && (
                        <p>
                          <span className="font-medium">Found:</span>{" "}
                          <span className="text-muted-foreground">{findingEvidence(f)}</span>
                        </p>
                      )}
                      {findingFix(f) && (
                        <p>
                          <span className="font-medium">Suggested fix:</span>{" "}
                          <span className="text-muted-foreground">{findingFix(f)}</span>
                        </p>
                      )}
                      {(f.ucp_reference || f.isbp_reference) && (
                        <p className="text-xs text-muted-foreground">
                          {[f.ucp_reference, f.isbp_reference].filter(Boolean).join(" · ")}
                        </p>
                      )}
                      {f.reviewer_note && (
                        <p className="rounded-md bg-muted px-3 py-2 text-xs">
                          <span className="font-medium">Reviewer note:</span> {f.reviewer_note}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                );
              })
            )}
          </div>

          {/* Side panel: note + timeline */}
          <div className="space-y-6">
            {/* Awaiting payment: record offline settlements (bank transfer /
                bKash / invoice) to move the job into the review flow. */}
            {detail.payment_status === "pending" && (
              <Card className="border-orange-300 bg-orange-50">
                <CardContent className="py-4 space-y-3">
                  <p className="text-sm font-medium text-orange-900 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" /> Awaiting payment
                  </p>
                  <p className="text-xs text-orange-800">
                    The customer hasn't paid through the app. If they paid offline
                    (bank transfer, bKash, invoice), record it — the job then enters
                    your review flow and the customer is notified.
                  </p>
                  <Button size="sm" variant="outline" onClick={markPaid} disabled={busy}>
                    Mark paid (offline)
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Readiness jobs: engine health + intake answers for the operator */}
            {(detail.workflow_type || "").includes("readiness") && (
              <>
                {detail.structured_result?._engine_error && (
                  <Card className="border-orange-300 bg-orange-50">
                    <CardContent className="py-4 space-y-3">
                      <p className="text-sm font-medium text-orange-900 flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4" /> Rules engine was unreachable at intake
                      </p>
                      <p className="text-xs text-orange-800">
                        Findings below lack citations. Re-run before delivering.
                      </p>
                      <Button size="sm" variant="outline" onClick={rerunEngine} disabled={busy}>
                        <RefreshCw className={cn("h-4 w-4 mr-2", busy && "animate-spin")} />
                        Re-run engine
                      </Button>
                    </CardContent>
                  </Card>
                )}
                {detail.structured_result?.intake_answers && (
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm">Intake answers</CardTitle>
                      <CardDescription className="text-xs">
                        What the customer told us — the basis of every finding.
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <dl className="space-y-2 text-xs max-h-72 overflow-y-auto">
                        {Object.entries(detail.structured_result.intake_answers).map(([k, v]) => (
                          <div key={k}>
                            <dt className="font-medium text-muted-foreground">{k.replace(/_/g, " ")}</dt>
                            <dd className="text-foreground">{String(v || "—")}</dd>
                          </div>
                        ))}
                      </dl>
                    </CardContent>
                  </Card>
                )}
              </>
            )}

            {detail?.documents && detail.documents.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">Uploaded documents</CardTitle>
                  <CardDescription className="text-xs">
                    The customer's actual files — cross-check every finding against the source.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {detail.documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm"
                    >
                      <div className="min-w-0">
                        <p className="truncate font-medium">{doc.filename}</p>
                        <p className="text-xs text-muted-foreground">
                          {doc.document_type} - {Math.max(1, Math.round(doc.file_size / 1024))} KB
                        </p>
                      </div>
                      {doc.download_url ? (
                        <Button asChild size="sm" variant="outline">
                          <a href={doc.download_url} target="_blank" rel="noreferrer">
                            View
                          </a>
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">unavailable</span>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Reviewer summary note</CardTitle>
                <CardDescription className="text-xs">
                  Shown to the customer on the delivered report.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  rows={5}
                  placeholder="e.g. Two critical discrepancies need fixing before presentation — see findings 1 and 3."
                  disabled={!deliverable}
                />
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={saveNote} disabled={busy || !deliverable}>
                    Save note
                  </Button>
                  <Button size="sm" variant="ghost" onClick={draftSummary} disabled={suggestBusy || busy || !deliverable}>
                    {suggestBusy ? "Drafting..." : "AI draft"}
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="space-y-2 text-xs">
                  {detail.timeline.length === 0 && <li className="text-muted-foreground">No events yet.</li>}
                  {detail.timeline.map((e, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="mt-1 h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
                      <div>
                        <span className="font-medium">{e.to_state.replace(/_/g, " ")}</span>
                        <span className="text-muted-foreground"> · {formatWhen(e.at)}</span>
                        {e.reason && <div className="text-muted-foreground">{e.reason}</div>}
                      </div>
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      <EditFindingDialog edit={edit} onClose={() => setEdit(null)} onSave={saveEdit} busy={busy} onSuggest={(f) => suggestText("annotation", findingId(f) ?? undefined)} />

      {/* Email intake dialog — run the engine on documents a customer emailed in */}
      <Dialog open={intakeOpen} onOpenChange={(open) => !intakeBusy && setIntakeOpen(open)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Email intake</DialogTitle>
            <DialogDescription>
              Upload the documents a customer emailed you. The engine runs and the job
              joins this queue; the customer email is stamped on it for delivery.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>Customer email</Label>
              <Input
                type="email"
                value={intakeEmail}
                onChange={(e) => setIntakeEmail(e.target.value)}
                placeholder="customer@company.com"
                disabled={intakeBusy}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Customer name (optional)</Label>
              <Input
                value={intakeName}
                onChange={(e) => setIntakeName(e.target.value)}
                placeholder="Company or contact name"
                disabled={intakeBusy}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Documents (LC + supporting)</Label>
              <Input
                type="file"
                multiple
                accept=".pdf"
                onChange={(e) => setIntakeFiles(e.target.files)}
                disabled={intakeBusy}
              />
              {intakeFiles && intakeFiles.length > 0 && (
                <p className="text-xs text-muted-foreground">{intakeFiles.length} file(s) selected</p>
              )}
            </div>
            {intakeBusy && (
              <p className="text-xs text-muted-foreground">
                Engine running — this takes a few minutes. You can close this dialog;
                the job will appear in the queue when done.
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIntakeOpen(false)} disabled={intakeBusy}>
              Cancel
            </Button>
            <Button onClick={submitIntake} disabled={intakeBusy || !intakeEmail.trim() || !intakeFiles || intakeFiles.length === 0}>
              {intakeBusy ? "Running engine..." : "Run engine"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Needs info dialog */}
      <Dialog open={needsInfoOpen} onOpenChange={setNeedsInfoOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Request more information</DialogTitle>
            <DialogDescription>
              The customer is notified and the job leaves the active queue until they respond.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={needsInfoReason}
            onChange={(e) => setNeedsInfoReason(e.target.value)}
            rows={3}
            placeholder="What do you need from the customer?"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setNeedsInfoOpen(false)} disabled={busy}>
              Cancel
            </Button>
            <Button onClick={sendNeedsInfo} disabled={busy || !needsInfoReason.trim()}>
              {busy ? "Sending…" : "Send request"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Deliver dialog */}
      <Dialog open={deliverOpen} onOpenChange={setDeliverOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Approve &amp; Deliver</DialogTitle>
            <DialogDescription>
              Generates the cited PDF report from the current findings, opens the customer's results, and emails
              them. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {detail && (
            <div className="text-sm space-y-1">
              <p>
                <span className="font-medium">{detail.findings.length}</span> finding
                {detail.findings.length === 1 ? "" : "s"} will be delivered.
              </p>
              {note.trim() ? (
                <p className="text-muted-foreground line-clamp-3">Note: {note.trim()}</p>
              ) : (
                <p className="text-muted-foreground">No reviewer note attached.</p>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeliverOpen(false)} disabled={busy}>
              Cancel
            </Button>
            <Button onClick={deliver} disabled={busy}>
              {busy ? "Delivering…" : "Deliver report"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
