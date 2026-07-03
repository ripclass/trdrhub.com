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
  job_id: string;
  review_state: string;
  workflow_type: string | null;
  user_id: string | null;
  company_id: string | null;
  finding_count: number;
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
  findings: Finding[];
  timeline: TimelineEvent[];
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

const STATE_STYLES: Record<string, string> = {
  engine_complete: "bg-blue-100 text-blue-800 border-blue-200",
  under_review: "bg-purple-100 text-purple-800 border-purple-200",
  needs_info: "bg-amber-100 text-amber-800 border-amber-200",
  delivered: "bg-green-100 text-green-800 border-green-200",
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
}: {
  edit: EditState | null;
  onClose: () => void;
  onSave: (payload: Record<string, string>) => void;
  busy: boolean;
}) {
  const [severity, setSeverity] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [fix, setFix] = React.useState("");
  const [note, setNote] = React.useState("");

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
            <Label>Reviewer note {isAnnotate ? "" : "(optional)"}</Label>
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
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
      const { data } = await api.get<{ count: number; items: QueueItem[] }>("/api/admin/review-queue");
      setItems(data.items ?? []);
    } catch (err) {
      setListError(errMessage(err));
    } finally {
      setLoadingList(false);
    }
  }, []);

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

  // ------------------------------------------------------------------ list

  if (!selectedId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Review Queue</h1>
            <p className="text-muted-foreground text-sm">
              Customer LC reports awaiting specialist review before delivery.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => void loadList()} disabled={loadingList}>
            <RefreshCw className={cn("h-4 w-4 mr-2", loadingList && "animate-spin")} />
            Refresh
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
                      <span className="font-mono text-xs text-muted-foreground truncate">{item.job_id}</span>
                      <StateBadge state={item.review_state} />
                    </div>
                    <div className="text-sm mt-1">
                      {(item.workflow_type || "validation").replace(/_/g, " ")} ·{" "}
                      <span className="font-medium">{item.finding_count}</span> finding{item.finding_count === 1 ? "" : "s"}
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground text-right">
                    <div>Submitted {formatWhen(item.submitted_at)}</div>
                    <div>In state since {formatWhen(item.state_changed_at)}</div>
                  </div>
                  <Button size="sm" variant="secondary">
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

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => setSelectedId(null)}>
            <ArrowLeft className="h-4 w-4 mr-1" /> Queue
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight font-mono">{selectedId.slice(0, 8)}…</h1>
              {detail && <StateBadge state={detail.review_state} />}
            </div>
            {detail && (
              <p className="text-muted-foreground text-xs">
                {(detail.workflow_type || "validation").replace(/_/g, " ")} · {detail.findings.length} finding
                {detail.findings.length === 1 ? "" : "s"}
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
                <Button size="sm" variant="outline" onClick={saveNote} disabled={busy || !deliverable}>
                  Save note
                </Button>
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

      <EditFindingDialog edit={edit} onClose={() => setEdit(null)} onSave={saveEdit} busy={busy} />

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
