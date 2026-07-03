/**
 * CBAM / EUDR readiness landing — Phase 3 launch (2026-07, playbook §3.2).
 *
 * One parametrized landing for both tools: supplier-side framing ("Your EU
 * buyer will ask for this. Be ready before they do."), the free 5-question
 * scope check (no signup; email-gated one-page summary), content anchors
 * (deadlines), and the paid report CTA into /tools/readiness/apply.
 *
 * Copy honesty: verified content anchors only, advisory-not-legal-advice
 * footer, no invented stats.
 */

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  ClipboardCheck,
  Clock,
  HelpCircle,
  Loader2,
  Mail,
  UserCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { cn } from "@/lib/utils";
import { READINESS_REPORTS } from "@/lib/pricing";
import { useSeoMeta, type SeoMeta } from "./useSeoMeta";

// ---------------------------------------------------------------------------
// Types shared with the backend (apps/api/app/routers/readiness.py)
// ---------------------------------------------------------------------------

interface Question {
  id: string;
  label: string;
  type: string;
  required: boolean;
  options?: { value: string; label: string }[];
  help?: string;
}

interface ScopeVerdict {
  verdict: "likely_in_scope" | "likely_out_of_scope" | "borderline";
  reasons: string[];
  deadline_note: string;
}

export interface ReadinessLandingConfig {
  tool: "cbam" | "eudr";
  seo: SeoMeta;
  heroTitle: string;
  heroAccent: string;
  heroSub: string;
  anchors: { title: string; body: string }[];
  reportProductId: string;
}

const VERDICT_STYLES: Record<string, { label: string; cls: string }> = {
  likely_in_scope: { label: "Likely IN scope", cls: "border-red-400/40 bg-red-500/10 text-red-300" },
  borderline: { label: "Borderline — needs a closer look", cls: "border-amber-400/40 bg-amber-500/10 text-amber-300" },
  likely_out_of_scope: { label: "Likely OUT of scope", cls: "border-emerald-400/40 bg-emerald-500/10 text-emerald-300" },
};

// ---------------------------------------------------------------------------
// Free scope-check widget
// ---------------------------------------------------------------------------

function ScopeCheckWidget({ tool }: { tool: "cbam" | "eudr" }) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [verdict, setVerdict] = useState<ScopeVerdict | null>(null);
  const [checking, setChecking] = useState(false);
  const [email, setEmail] = useState("");
  const [emailState, setEmailState] = useState<"idle" | "sending" | "sent" | "failed">("idle");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/readiness/questions/${tool}`)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => setQuestions(d.scope_questions ?? []))
      .catch(() => setError("Couldn't load the checker — refresh to retry."));
  }, [tool]);

  const requiredAnswered = questions
    .filter((q) => q.required)
    .every((q) => (answers[q.id] ?? "").length > 0);

  const runCheck = async () => {
    setChecking(true);
    setError(null);
    setVerdict(null);
    setEmailState("idle");
    try {
      const res = await fetch("/api/readiness/scope-check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool, answers }),
      });
      if (!res.ok) throw new Error();
      setVerdict(await res.json());
    } catch {
      setError("The check failed — please try again in a moment.");
    } finally {
      setChecking(false);
    }
  };

  const sendSummary = async () => {
    if (!email.trim()) return;
    setEmailState("sending");
    try {
      const res = await fetch("/api/readiness/scope-summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool, email: email.trim(), answers }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setEmailState(data.email_sent ? "sent" : "failed");
    } catch {
      setEmailState("failed");
    }
  };

  const vs = verdict ? VERDICT_STYLES[verdict.verdict] : null;

  return (
    <div className="bg-[#00382E]/60 border border-[#B2F273]/20 rounded-2xl p-6 sm:p-8">
      <div className="flex items-center gap-2 mb-1">
        <ClipboardCheck className="w-5 h-5 text-[#B2F273]" />
        <h3 className="text-lg font-bold text-white font-display">
          Am I in scope? — free 60-second check
        </h3>
      </div>
      <p className="text-[#EDF5F2]/50 text-sm mb-6">
        Five questions, instant answer, no signup.
      </p>

      <div className="space-y-4">
        {questions.map((q) => (
          <div key={q.id}>
            <label className="block text-sm text-white font-medium mb-1.5">
              {q.label}
              {!q.required && <span className="text-[#EDF5F2]/40 font-normal"> (optional)</span>}
            </label>
            {q.help && (
              <p className="text-xs text-[#EDF5F2]/40 mb-1.5 flex items-center gap-1">
                <HelpCircle className="w-3 h-3" /> {q.help}
              </p>
            )}
            {q.type === "select" && q.options ? (
              <select
                value={answers[q.id] ?? ""}
                onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
                className="w-full h-10 rounded-lg bg-[#00261C] border border-[#EDF5F2]/15 text-white text-sm px-3 focus:border-[#B2F273]/60 focus:outline-none"
              >
                <option value="">Select…</option>
                {q.options.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            ) : (
              <Input
                value={answers[q.id] ?? ""}
                onChange={(e) => setAnswers((a) => ({ ...a, [q.id]: e.target.value }))}
                className="bg-[#00261C] border-[#EDF5F2]/15 text-white placeholder:text-[#EDF5F2]/30"
                placeholder={q.help || ""}
              />
            )}
          </div>
        ))}
      </div>

      <Button
        onClick={runCheck}
        disabled={!requiredAnswered || checking || questions.length === 0}
        className="w-full mt-6 h-11 bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none"
      >
        {checking ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
        Check my scope
      </Button>

      {error && <p className="text-sm text-red-400 mt-3">{error}</p>}

      {verdict && vs && (
        <div className={cn("mt-6 rounded-xl border p-5", vs.cls)}>
          <p className="font-bold mb-2">{vs.label}</p>
          <ul className="space-y-1.5 text-sm text-[#EDF5F2]/80">
            {verdict.reasons.map((r, i) => (
              <li key={i} className="flex gap-2">
                <span className="shrink-0">•</span>
                {r}
              </li>
            ))}
          </ul>

          {/* Email gate for the one-pager */}
          <div className="mt-5 pt-4 border-t border-white/10">
            {emailState === "sent" ? (
              <p className="text-sm text-[#B2F273] flex items-center gap-2">
                <CheckCircle className="w-4 h-4" /> Summary sent — check your inbox.
              </p>
            ) : (
              <>
                <p className="text-sm text-white font-medium mb-2 flex items-center gap-2">
                  <Mail className="w-4 h-4" />
                  Get this as a one-page summary (with the deadlines) by email
                </p>
                <div className="flex gap-2">
                  <Input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    className="bg-[#00261C] border-[#EDF5F2]/15 text-white placeholder:text-[#EDF5F2]/30"
                  />
                  <Button
                    onClick={sendSummary}
                    disabled={emailState === "sending" || !email.includes("@")}
                    className="bg-[#EDF5F2]/10 hover:bg-[#EDF5F2]/20 text-white border-none shrink-0"
                  >
                    {emailState === "sending" ? <Loader2 className="w-4 h-4 animate-spin" /> : "Send"}
                  </Button>
                </div>
                {emailState === "failed" && (
                  <p className="text-xs text-amber-400 mt-2">
                    Sending failed — email us at support@trdrhub.com and we'll send it manually.
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Landing
// ---------------------------------------------------------------------------

export default function ReadinessLanding(config: ReadinessLandingConfig) {
  useSeoMeta(config.seo);
  const products = READINESS_REPORTS.filter(
    (p) => p.id === config.reportProductId || p.id === "cbam_eudr_bundle",
  );

  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main>
        {/* Hero + scope check */}
        <section className="relative pt-40 md:pt-44 pb-16 overflow-hidden bg-[#00261C]">
          <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-[#B2F273]/10 rounded-full blur-[120px]" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid lg:grid-cols-2 gap-10 lg:gap-16 items-start max-w-6xl mx-auto">
              <div className="pt-4">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#B2F273]/10 border border-[#B2F273]/20 mb-6">
                  <UserCheck className="w-4 h-4 text-[#B2F273]" />
                  <span className="text-[#B2F273] text-sm font-medium">
                    Your EU buyer will ask for this. Be ready before they do.
                  </span>
                </div>
                <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-5 leading-[1.15] tracking-tight font-display">
                  {config.heroTitle}
                  <br />
                  <span className="text-[#B2F273] text-glow-sm">{config.heroAccent}</span>
                </h1>
                <p className="text-lg text-[#EDF5F2]/60 leading-relaxed mb-8">{config.heroSub}</p>

                <div className="space-y-4">
                  {config.anchors.map((a, i) => (
                    <div key={i} className="flex gap-3">
                      <AlertTriangle className="w-5 h-5 text-[#B2F273] shrink-0 mt-0.5" />
                      <div>
                        <p className="text-white font-medium text-sm">{a.title}</p>
                        <p className="text-[#EDF5F2]/50 text-sm">{a.body}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <ScopeCheckWidget tool={config.tool} />
            </div>
          </div>
        </section>

        {/* Paid report */}
        <section className="relative py-20 bg-[#00261C] border-t border-[#EDF5F2]/10">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <p className="text-[#B2F273] font-mono font-semibold mb-3 tracking-wide uppercase text-sm">
                The full readiness report
              </p>
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-3 font-display">
                From "am I in scope?" to "here's exactly what to prepare"
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                A 10–15 question intake about your products, volumes and data — mapped clause by
                clause against the regulation. Every gap cited, every fix concrete, reviewed by a
                specialist before it ships. Delivered within 24 hours as a PDF you can forward to
                your EU buyer.
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto mb-10">
              {products.map((p) => (
                <div
                  key={p.id}
                  className={cn(
                    "relative bg-[#00382E]/50 border rounded-2xl p-6 flex flex-col",
                    p.popular ? "border-[#B2F273] shadow-lg shadow-[#B2F273]/10" : "border-[#EDF5F2]/10",
                  )}
                >
                  {p.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <span className="px-3 py-1 rounded-full text-xs font-semibold font-mono uppercase tracking-wider bg-[#B2F273] text-[#00261C]">
                        Best value
                      </span>
                    </div>
                  )}
                  <h3 className="text-lg font-bold text-white mb-1 font-display text-center">{p.name}</h3>
                  <p className="text-[#EDF5F2]/40 text-xs mb-3 text-center">{p.description}</p>
                  <div className="flex items-baseline justify-center gap-1 mb-1">
                    <span className="text-4xl font-bold text-white font-display">${p.priceUsd}</span>
                    <span className="text-[#EDF5F2]/40 text-sm font-mono">/report</span>
                  </div>
                  <p className="text-[#B2F273] text-xs mb-4 font-mono text-center inline-flex items-center gap-1 justify-center">
                    <Clock className="w-3 h-3" /> {p.turnaround}
                  </p>
                  <ul className="space-y-2 mb-6 flex-1">
                    {p.features.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-[#EDF5F2]/60">
                        <CheckCircle className="w-3.5 h-3.5 text-[#B2F273] shrink-0 mt-0.5" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Button
                    className={cn(
                      "w-full h-10 font-bold text-sm border-none",
                      p.popular
                        ? "bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C]"
                        : "bg-[#EDF5F2]/10 hover:bg-[#EDF5F2]/20 text-white",
                    )}
                    asChild
                  >
                    <Link to={`/tools/readiness/apply?tool=${p.id === "cbam_eudr_bundle" ? "both" : config.tool}`}>
                      Start intake — ${p.priceUsd}
                      <ArrowRight className="w-4 h-4 ml-2" />
                    </Link>
                  </Button>
                </div>
              ))}
            </div>

            <div className="text-center text-xs text-[#EDF5F2]/30 max-w-2xl mx-auto leading-relaxed">
              Readiness reports are an advisory assessment against the regulation — not legal
              advice, and not a formal scope or compliance determination. A specialist reviews
              every report before delivery. Refund in full if it doesn't help you.
            </div>
          </div>
        </section>
      </main>
      <TRDRFooter />
    </div>
  );
}
