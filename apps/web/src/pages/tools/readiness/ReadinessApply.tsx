/**
 * Paid readiness-report intake — Phase 3 launch (2026-07).
 *
 * /tools/readiness/apply?tool=cbam|eudr|both (RequireAuth). Renders the
 * 10–15 question intake from GET /api/readiness/questions/{tool}, submits to
 * POST /api/readiness/submit, and hands off to the concierge status page at
 * /lcopilot/status/{job_id} — the same tracker LCopilot reviews use.
 *
 * Payment is Phase 5 (Stripe Checkout fires at this submission point);
 * until then submission enters the queue and the operator invoices manually.
 */

import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, CheckCircle, ChevronLeft, HelpCircle, Loader2 } from "lucide-react";

import { api } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { READINESS_REPORTS } from "@/lib/pricing";

interface Question {
  id: string;
  label: string;
  type: string;
  required: boolean;
  options?: { value: string; label: string }[];
  help?: string;
}

const TOOL_META: Record<string, { name: string; productId: string }> = {
  cbam: { name: "CBAM Supplier-Readiness Report", productId: "cbam_report" },
  eudr: { name: "EUDR Readiness Report", productId: "eudr_report" },
  both: { name: "CBAM + EUDR Bundle", productId: "cbam_eudr_bundle" },
};

export default function ReadinessApply() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();

  const toolParam = (searchParams.get("tool") || "cbam").toLowerCase();
  const tool = toolParam in TOOL_META ? toolParam : "cbam";
  const meta = TOOL_META[tool];
  const product = READINESS_REPORTS.find((p) => p.id === meta.productId);

  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const tools = tool === "both" ? ["cbam", "eudr"] : [tool];
    setLoading(true);
    Promise.all(
      tools.map((t) =>
        fetch(`/api/readiness/questions/${t}`).then((r) => (r.ok ? r.json() : Promise.reject())),
      ),
    )
      .then((results) => {
        // Bundle intake = both question sets, deduped on question id (the
        // shared ids like cn_codes_full appear once).
        const seen = new Set<string>();
        const merged: Question[] = [];
        for (const res of results) {
          for (const q of res.intake_questions as Question[]) {
            if (!seen.has(q.id)) {
              seen.add(q.id);
              merged.push(q);
            }
          }
        }
        setQuestions(merged);
        setError(null);
      })
      .catch(() => setError("Couldn't load the intake questions — refresh to retry."))
      .finally(() => setLoading(false));
  }, [tool]);

  const requiredAnswered = useMemo(
    () => questions.filter((q) => q.required).every((q) => (answers[q.id] ?? "").length > 0),
    [questions, answers],
  );

  const submit = async () => {
    setSubmitting(true);
    try {
      const { data } = await api.post("/api/readiness/submit", { tool, answers });
      toast({
        title: "Intake received",
        description: "A specialist reviews every report — yours ships within 24 hours.",
      });
      navigate(data.status_url || `/lcopilot/status/${data.job_id}`);
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast({
        title: "Submission failed",
        description: typeof detail === "string" ? detail : "Please try again or email support@trdrhub.com.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-2xl px-4 py-10">
        <Link
          to={tool === "eudr" ? "/tools/eudr-readiness-check" : "/tools/cbam-readiness-check"}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-6"
        >
          <ChevronLeft className="h-4 w-4" /> Back
        </Link>

        <h1 className="text-2xl font-bold tracking-tight mb-1">{meta.name}</h1>
        <p className="text-sm text-muted-foreground mb-8">
          {product ? `$${product.priceUsd} · ` : ""}Delivered within 24 hours, specialist-reviewed.
          Answer what you can — "don't know" is itself useful readiness data.
        </p>

        {loading ? (
          <Card>
            <CardContent className="py-16 flex items-center justify-center gap-2 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" /> Loading intake…
            </CardContent>
          </Card>
        ) : error ? (
          <Card>
            <CardContent className="py-12 text-center text-sm text-muted-foreground">{error}</CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Intake questionnaire</CardTitle>
              <CardDescription>
                {questions.length} questions about your products, volumes and data readiness.
                No documents needed.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {questions.map((q, idx) => (
                <div key={q.id}>
                  <label className="block text-sm font-medium mb-1.5">
                    {idx + 1}. {q.label}
                    {!q.required && <span className="text-muted-foreground font-normal"> (optional)</span>}
                  </label>
                  {q.help && (
                    <p className="text-xs text-muted-foreground mb-1.5 flex items-center gap-1">
                      <HelpCircle className="w-3 h-3" /> {q.help}
                    </p>
                  )}
                  {q.type === "select" && q.options ? (
                    <select
                      value={answers[q.id] ?? ""}
                      onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
                      className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                      <option value="">Select…</option>
                      {q.options.map((o) => (
                        <option key={o.value} value={o.value}>{o.label}</option>
                      ))}
                    </select>
                  ) : q.id.includes("data_availability") || q.id.includes("origin") ? (
                    <Textarea
                      value={answers[q.id] ?? ""}
                      onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
                      rows={2}
                    />
                  ) : (
                    <Input
                      value={answers[q.id] ?? ""}
                      onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
                    />
                  )}
                </div>
              ))}

              <div className="pt-4 border-t">
                <Button onClick={submit} disabled={!requiredAnswered || submitting} className="w-full h-11">
                  {submitting ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <CheckCircle className="h-4 w-4 mr-2" />
                  )}
                  Submit for review
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
                <p className="text-xs text-muted-foreground mt-3 text-center">
                  Your answers go to our rules engine and a specialist — nothing is shared with
                  anyone else. Advisory assessment, not legal advice. Full refund if the report
                  doesn't help you.
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
