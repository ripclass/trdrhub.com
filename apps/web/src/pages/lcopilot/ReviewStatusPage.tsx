/**
 * Concierge review status page — Phase 1 launch (2026-07).
 *
 * Customer-facing tracker at /lcopilot/status/:jobId for the
 * service-as-software flow: results are gated behind a specialist review, so
 * this page is what the customer watches between "submitted" and "delivered".
 * Feeds from GET /api/lcopilot/status/{jobId} (owner-scoped), polls every 30s
 * until the report is delivered.
 *
 * Backend: apps/api/app/routers/lcopilot_review.py.
 */

import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  ChevronLeft,
  Clock,
  Download,
  FileSearch,
  Loader2,
  MailQuestion,
  ShieldCheck,
} from "lucide-react";

interface TimelineEvent {
  from_state: string | null;
  to_state: string;
  reason: string | null;
  at: string | null;
}

interface ReviewStatus {
  job_id: string;
  review_state: string | null;
  workflow_type: string | null;
  is_review_job: boolean;
  delivered: boolean;
  delivered_at: string | null;
  reviewer_note: string | null;
  report_available: boolean;
  timeline: TimelineEvent[];
}

const POLL_MS = 30_000;

// Customer-facing steps. engine_complete and under_review are both shown as
// "Specialist review" — the engine/human split is an internal distinction.
const STEPS = [
  { key: "submitted", label: "Received", icon: Check },
  { key: "processing", label: "Document check", icon: FileSearch },
  { key: "under_review", label: "Specialist review", icon: ShieldCheck },
  { key: "delivered", label: "Report delivered", icon: Download },
] as const;

function stepIndexForState(state: string | null): number {
  switch (state) {
    case "submitted":
      return 0;
    case "processing":
      return 1;
    case "engine_complete":
    case "under_review":
    case "needs_info":
      return 2;
    case "delivered":
      return 3;
    default:
      return 0;
  }
}

function resultsHref(status: ReviewStatus): string {
  if ((status.workflow_type || "").startsWith("importer")) {
    return `/lcopilot/import-results/${status.job_id}`;
  }
  return `/lcopilot/results/${status.job_id}`;
}

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ReviewStatusPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [status, setStatus] = useState<ReviewStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  const load = useCallback(async () => {
    if (!jobId) return;
    try {
      const { data } = await api.get<ReviewStatus>(`/api/lcopilot/status/${jobId}`);
      setStatus(data);
      setError(null);
    } catch (err) {
      const anyErr = err as { response?: { status?: number; data?: { detail?: string } } };
      if (anyErr?.response?.status === 403) setError("This submission belongs to another account.");
      else if (anyErr?.response?.status === 404) setError("We couldn't find this submission.");
      else setError(anyErr?.response?.data?.detail || "Couldn't load the status. We'll keep retrying.");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    void load();
  }, [load]);

  // Poll until delivered.
  useEffect(() => {
    if (status?.delivered) return;
    const t = window.setInterval(() => void load(), POLL_MS);
    return () => window.clearInterval(t);
  }, [status?.delivered, load]);

  const downloadReport = async () => {
    if (!jobId) return;
    setDownloading(true);
    try {
      const { data } = await api.get<{ url: string }>(`/api/lcopilot/status/${jobId}/report`);
      window.open(data.url, "_blank", "noopener");
    } catch {
      // Report file missing (rare render failure) — the results page still
      // carries every cited finding.
      window.alert("The report file isn't available right now — your full results page has every finding.");
    } finally {
      setDownloading(false);
    }
  };

  const state = status?.review_state ?? null;
  const activeStep = stepIndexForState(state);
  const needsInfo = state === "needs_info";
  const needsInfoReason =
    needsInfo && status
      ? [...status.timeline].reverse().find((e) => e.to_state === "needs_info")?.reason || null
      : null;

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-2xl px-4 py-10">
        <Link
          to="/lcopilot/dashboard"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-6"
        >
          <ChevronLeft className="h-4 w-4" /> Dashboard
        </Link>

        <h1 className="text-2xl font-bold tracking-tight mb-1">
          {(status?.workflow_type || "").includes("readiness")
            ? "Your readiness report"
            : "Your LC pack review"}
        </h1>
        <p className="text-sm text-muted-foreground mb-8 font-mono">Reference: {jobId}</p>

        {loading ? (
          <Card>
            <CardContent className="py-16 flex items-center justify-center gap-2 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" /> Loading status…
            </CardContent>
          </Card>
        ) : error && !status ? (
          <Card>
            <CardContent className="py-12 text-center">
              <AlertTriangle className="h-8 w-8 mx-auto text-destructive mb-3" />
              <p className="font-medium mb-1">Something's off</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </CardContent>
          </Card>
        ) : status && !status.is_review_job ? (
          // Legacy self-serve job — no review gate; send them to results.
          <Card>
            <CardContent className="py-12 text-center">
              <Check className="h-8 w-8 mx-auto text-green-500 mb-3" />
              <p className="font-medium mb-3">This validation doesn't go through specialist review.</p>
              <Button asChild>
                <Link to={resultsHref(status)}>
                  View results <ArrowRight className="h-4 w-4 ml-2" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        ) : status ? (
          <div className="space-y-6">
            {/* Stepper */}
            <Card>
              <CardContent className="py-8">
                <ol className="space-y-0">
                  {STEPS.map((step, idx) => {
                    const done = idx < activeStep || status.delivered;
                    const current = idx === activeStep && !status.delivered;
                    const Icon = step.icon;
                    return (
                      <li key={step.key} className="relative flex gap-4 pb-8 last:pb-0">
                        {idx < STEPS.length - 1 && (
                          <span
                            className={cn(
                              "absolute left-[15px] top-8 h-[calc(100%-2rem)] w-0.5",
                              done ? "bg-green-500" : "bg-slate-200",
                            )}
                          />
                        )}
                        <span
                          className={cn(
                            "relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2",
                            done
                              ? "border-green-500 bg-green-500 text-white"
                              : current
                                ? "border-blue-500 bg-blue-50 text-blue-600"
                                : "border-slate-200 bg-white text-slate-400",
                          )}
                        >
                          {done ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
                        </span>
                        <div className="pt-1">
                          <p className={cn("text-sm font-medium", current && "text-blue-700")}>{step.label}</p>
                          {current && !needsInfo && (
                            <p className="text-xs text-muted-foreground mt-0.5">
                              {idx === 2
                                ? "A trade documentation specialist is reviewing every finding before it ships. Typical turnaround is within 24 hours of submission."
                                : "In progress — this page updates automatically."}
                            </p>
                          )}
                          {step.key === "delivered" && status.delivered && (
                            <p className="text-xs text-muted-foreground mt-0.5">{formatWhen(status.delivered_at)}</p>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ol>
              </CardContent>
            </Card>

            {/* Needs-info callout */}
            {needsInfo && (
              <Card className="border-amber-300 bg-amber-50">
                <CardContent className="py-5 flex gap-3">
                  <MailQuestion className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-amber-900">We need a little more from you</p>
                    <p className="text-sm text-amber-800 mt-1">
                      {needsInfoReason ||
                        "Our specialist needs more information to finish your review — please check your email."}
                    </p>
                    <p className="text-xs text-amber-700 mt-2">
                      Reply to the email we sent you and your review resumes where it left off.
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Delivered */}
            {status.delivered && (
              <Card className="border-green-300 bg-green-50">
                <CardContent className="py-6">
                  <p className="font-medium text-green-900 mb-1">Your cited report is ready</p>
                  {status.reviewer_note && (
                    <p className="text-sm text-green-800 mb-4 whitespace-pre-wrap">
                      <span className="font-medium">From your reviewer:</span> {status.reviewer_note}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-3">
                    {status.report_available && (
                      <Button onClick={downloadReport} disabled={downloading}>
                        {downloading ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <Download className="h-4 w-4 mr-2" />
                        )}
                        Download report (PDF)
                      </Button>
                    )}
                    {/* Readiness jobs have no LC results screen — the PDF is
                        the deliverable. */}
                    {!(status.workflow_type || "").includes("readiness") && (
                      <Button variant={status.report_available ? "outline" : "default"} asChild>
                        <Link to={resultsHref(status)}>
                          View full results <ArrowRight className="h-4 w-4 ml-2" />
                        </Link>
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Waiting hint */}
            {!status.delivered && !needsInfo && (
              <p className="flex items-center gap-2 text-xs text-muted-foreground justify-center">
                <Clock className="h-3.5 w-3.5" />
                This page refreshes automatically — you'll also get an email the moment your report ships.
              </p>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
