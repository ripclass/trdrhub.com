/**
 * /check — the free, logged-out LC discrepancy checker (the lead magnet).
 *
 * Public, brand-themed, in the marketing shell (TRDRHeader / TRDRFooter), NOT
 * auth-gated. Upload an LC plus any supporting documents → POST /api/check →
 * trimmed result (verdict + finding count + the top two findings) → "sign up to
 * see everything / export the PDF" gate.
 *
 * One run per IP per 24 h, enforced server-side; a second attempt within the
 * window comes back as a rate-limit message + sign-up CTA.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  FileText,
  Loader2,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  getCheckAvailability,
  PublicCheckRateLimitedError,
  runPublicCheck,
  type PublicCheckResult,
} from "@/lib/lcopilot/publicCheckApi";

const ACCEPTED = ".pdf,.png,.jpg,.jpeg,.tif,.tiff,.webp";
const MAX_FILES = 12;

type VerdictTone = "good" | "caution" | "warn" | "bad" | "neutral";

function verdictTone(result: PublicCheckResult): VerdictTone {
  const color = (result.verdict_color || "").toLowerCase();
  if (color === "green") return "good";
  if (color === "yellow") return "caution";
  if (color === "orange") return "warn";
  if (color === "red") return "bad";
  const v = (result.verdict || "").toUpperCase();
  if (["SUBMIT", "PASS", "CLEAN", "READY", "ACCEPT"].includes(v)) return "good";
  if (["CAUTION"].includes(v)) return "caution";
  if (["HOLD", "FIX_REQUIRED", "REVIEW_REQUIRED"].includes(v)) return "warn";
  if (["REJECT", "FAIL", "LIKELY_REJECT"].includes(v)) return "bad";
  return "neutral";
}

const TONE_STYLES: Record<VerdictTone, { ring: string; chip: string; dot: string; label: string }> = {
  good: {
    ring: "border-[#B2F273]/40 bg-[#B2F273]/[0.06]",
    chip: "bg-[#B2F273] text-[#00261C]",
    dot: "bg-[#B2F273]",
    label: "Looks clean",
  },
  caution: {
    ring: "border-amber-400/40 bg-amber-400/[0.06]",
    chip: "bg-amber-400 text-[#00261C]",
    dot: "bg-amber-400",
    label: "Minor corrections recommended",
  },
  warn: {
    ring: "border-orange-400/40 bg-orange-400/[0.06]",
    chip: "bg-orange-400 text-[#00261C]",
    dot: "bg-orange-400",
    label: "High discrepancy risk",
  },
  bad: {
    ring: "border-rose-500/40 bg-rose-500/[0.07]",
    chip: "bg-rose-500 text-white",
    dot: "bg-rose-500",
    label: "Likely to be rejected",
  },
  neutral: {
    ring: "border-[#EDF5F2]/15 bg-[#00382E]/30",
    chip: "bg-[#EDF5F2]/15 text-[#EDF5F2]",
    dot: "bg-[#EDF5F2]/40",
    label: "Review the findings",
  },
};

const SEVERITY_LABEL: Record<string, { text: string; cls: string }> = {
  critical: { text: "Critical", cls: "bg-rose-500/15 text-rose-300 border-rose-500/30" },
  major: { text: "Major", cls: "bg-orange-400/15 text-orange-300 border-orange-400/30" },
  discrepancy: { text: "Discrepancy", cls: "bg-orange-400/15 text-orange-300 border-orange-400/30" },
  high: { text: "High", cls: "bg-orange-400/15 text-orange-300 border-orange-400/30" },
  minor: { text: "Minor", cls: "bg-amber-400/15 text-amber-200 border-amber-400/30" },
  advisory: { text: "Advisory", cls: "bg-[#EDF5F2]/10 text-[#EDF5F2]/70 border-[#EDF5F2]/20" },
  info: { text: "Info", cls: "bg-[#EDF5F2]/10 text-[#EDF5F2]/70 border-[#EDF5F2]/20" },
};

function severityChip(severity: string) {
  const meta = SEVERITY_LABEL[(severity || "").toLowerCase()] || {
    text: severity ? severity[0].toUpperCase() + severity.slice(1) : "Finding",
    cls: "bg-[#EDF5F2]/10 text-[#EDF5F2]/70 border-[#EDF5F2]/20",
  };
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium", meta.cls)}>
      {meta.text}
    </span>
  );
}

function humanizeRetry(seconds: number): string {
  if (seconds <= 0) return "shortly";
  const hours = Math.round(seconds / 3600);
  if (hours >= 1) return `in about ${hours} hour${hours === 1 ? "" : "s"}`;
  const mins = Math.max(1, Math.round(seconds / 60));
  return `in about ${mins} minute${mins === 1 ? "" : "s"}`;
}

export default function CheckPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<PublicCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rateLimited, setRateLimited] = useState<{ retryAfter: number } | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    let active = true;
    getCheckAvailability().then((a) => {
      if (active && !a.available) {
        setRateLimited({ retryAfter: a.retry_after_seconds ?? 24 * 60 * 60 });
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const addFiles = useCallback((incoming: FileList | File[] | null) => {
    if (!incoming) return;
    setError(null);
    setFiles((prev) => {
      const next = [...prev];
      for (const f of Array.from(incoming)) {
        if (next.length >= MAX_FILES) break;
        if (!next.some((e) => e.name === f.name && e.size === f.size)) next.push(f);
      }
      return next;
    });
  }, []);

  const removeFile = (idx: number) => setFiles((prev) => prev.filter((_, i) => i !== idx));

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    addFiles(e.dataTransfer.files);
  };

  const submit = async () => {
    if (!files.length || running) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const r = await runPublicCheck(files);
      setResult(r);
    } catch (err) {
      if (err instanceof PublicCheckRateLimitedError) {
        setRateLimited({ retryAfter: err.retryAfterSeconds });
      } else {
        setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
      }
    } finally {
      setRunning(false);
    }
  };

  const resetForAnother = () => {
    setResult(null);
    setFiles([]);
    setError(null);
  };

  const tone = result ? verdictTone(result) : "neutral";
  const toneStyle = TONE_STYLES[tone];

  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />

      {/* Hero */}
      <section className="relative pt-32 pb-10 overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
        <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="max-w-3xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[#B2F273]/20 bg-[#B2F273]/5 backdrop-blur-sm mb-6">
              <Sparkles className="w-3.5 h-3.5 text-[#B2F273]" />
              <span className="text-[#B2F273] font-mono text-xs tracking-wider uppercase">Free LC check · no account</span>
            </div>
            <h1 className="text-4xl sm:text-5xl font-bold text-white tracking-tight">
              Check your Letter of Credit for discrepancies
            </h1>
            <p className="mt-5 text-lg text-[#EDF5F2]/60">
              Upload the LC and your supporting documents. We run the same examiner the paid product uses —
              UCP 600 / ISBP 745, cross-document checks, sanctions screening — and tell you whether the
              presentation is likely to clear. One free check, right here, nothing to install.
            </p>
          </div>
        </div>
      </section>

      {/* Main */}
      <section className="pb-24">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mx-auto">
            {rateLimited ? (
              <RateLimitedCard retryAfter={rateLimited.retryAfter} />
            ) : result ? (
              <div className="space-y-6">
                {/* Verdict card */}
                <div className={cn("rounded-3xl border p-8", toneStyle.ring)}>
                  <div className="flex items-start justify-between gap-4 flex-wrap">
                    <div>
                      <div className="flex items-center gap-3">
                        <span className={cn("inline-flex h-2.5 w-2.5 rounded-full", toneStyle.dot)} />
                        <span className="text-xs font-mono uppercase tracking-widest text-[#EDF5F2]/50">Verdict</span>
                      </div>
                      <div className="mt-2 flex items-center gap-3">
                        <span className={cn("inline-flex items-center rounded-full px-3 py-1 text-sm font-bold uppercase tracking-wider", toneStyle.chip)}>
                          {result.verdict || "Review"}
                        </span>
                      </div>
                      <p className="mt-3 text-[#EDF5F2]/80">
                        {result.verdict_label || toneStyle.label}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-3xl font-bold text-white tabular-nums">{result.finding_count}</div>
                      <div className="text-xs uppercase tracking-widest text-[#EDF5F2]/50">
                        finding{result.finding_count === 1 ? "" : "s"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Top findings */}
                {result.top_findings.length > 0 && (
                  <div className="rounded-3xl border border-[#EDF5F2]/10 bg-[#00382E]/30 p-8">
                    <h2 className="text-sm font-mono uppercase tracking-widest text-[#EDF5F2]/50">
                      {result.finding_count > result.top_findings.length
                        ? `Top ${result.top_findings.length} of ${result.finding_count} findings`
                        : "Findings"}
                    </h2>
                    <ul className="mt-4 space-y-3">
                      {result.top_findings.map((f, i) => (
                        <li key={i} className="flex items-start gap-3 rounded-2xl border border-[#EDF5F2]/10 bg-[#00261C]/40 p-4">
                          <div className="mt-0.5">{severityChip(f.severity)}</div>
                          <p className="text-[#EDF5F2]/90 text-sm leading-relaxed">{f.title}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Sign-up gate */}
                <div className="rounded-3xl border border-[#B2F273]/30 bg-[#B2F273]/[0.06] p-8">
                  <div className="flex items-start gap-3">
                    <ShieldCheck className="w-5 h-5 text-[#B2F273] shrink-0 mt-0.5" />
                    <div>
                      <h3 className="text-white font-semibold text-lg">
                        {result.finding_count > result.top_findings.length
                          ? `See all ${result.finding_count} findings — with the fixes`
                          : "Get the full report"}
                      </h3>
                      <p className="mt-2 text-[#EDF5F2]/70 text-sm leading-relaxed">
                        A free account unlocks every finding with the exact LC clause it breaches and the
                        suggested correction, the per-document breakdown, and a one-click PDF report you can
                        send to your bank or your supplier — plus you can run more checks.
                      </p>
                      <div className="mt-5 flex flex-wrap gap-3">
                        <Button asChild className="bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] font-semibold">
                          <Link to="/register">
                            Create free account <ArrowRight className="ml-1.5 w-4 h-4" />
                          </Link>
                        </Button>
                        <Button asChild variant="outline" className="border-[#EDF5F2]/20 text-white hover:bg-[#EDF5F2]/10">
                          <Link to="/login">I already have one</Link>
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  onClick={resetForAnother}
                  className="text-sm text-[#EDF5F2]/50 hover:text-[#B2F273] transition-colors"
                >
                  ← Check a different document set
                </button>
                <p className="text-xs text-[#EDF5F2]/40">
                  Heads up: the free checker allows one run per visitor per day. Sign up for unlimited checks.
                </p>
              </div>
            ) : (
              <>
                {/* Dropzone */}
                <div
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={onDrop}
                  className={cn(
                    "rounded-3xl border-2 border-dashed p-10 text-center transition-colors",
                    dragOver ? "border-[#B2F273] bg-[#B2F273]/[0.05]" : "border-[#EDF5F2]/15 bg-[#00382E]/20",
                  )}
                >
                  <input
                    ref={inputRef}
                    type="file"
                    accept={ACCEPTED}
                    multiple
                    className="hidden"
                    onChange={(e) => addFiles(e.target.files)}
                  />
                  <div className="mx-auto w-12 h-12 rounded-2xl bg-[#B2F273]/10 flex items-center justify-center">
                    <Upload className="w-5 h-5 text-[#B2F273]" />
                  </div>
                  <p className="mt-4 text-white font-medium">Drop the LC and supporting documents here</p>
                  <p className="mt-1 text-sm text-[#EDF5F2]/50">PDF or image files · up to {MAX_FILES} documents</p>
                  <Button
                    onClick={() => inputRef.current?.click()}
                    variant="outline"
                    className="mt-5 border-[#EDF5F2]/20 text-white hover:bg-[#EDF5F2]/10"
                  >
                    Choose files
                  </Button>
                </div>

                {/* File list */}
                {files.length > 0 && (
                  <ul className="mt-5 space-y-2">
                    {files.map((f, i) => (
                      <li
                        key={`${f.name}-${i}`}
                        className="flex items-center gap-3 rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/30 px-4 py-3"
                      >
                        <FileText className="w-4 h-4 text-[#B2F273] shrink-0" />
                        <span className="text-sm text-[#EDF5F2]/90 truncate flex-1">{f.name}</span>
                        <span className="text-xs text-[#EDF5F2]/40 shrink-0">{(f.size / 1024).toFixed(0)} KB</span>
                        <button
                          onClick={() => removeFile(i)}
                          className="text-[#EDF5F2]/40 hover:text-rose-300 transition-colors"
                          aria-label={`Remove ${f.name}`}
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}

                {error && (
                  <div className="mt-5 rounded-2xl border border-rose-500/30 bg-rose-500/[0.07] px-4 py-3 text-sm text-rose-200">
                    {error}
                  </div>
                )}

                <div className="mt-6 flex items-center justify-between flex-wrap gap-4">
                  <p className="text-xs text-[#EDF5F2]/40 max-w-md">
                    One free check per visitor per day. Your documents are processed to produce the result and
                    are not shared. For unlimited checks and the full report, create a free account.
                  </p>
                  <Button
                    onClick={submit}
                    disabled={!files.length || running}
                    className="bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {running ? (
                      <>
                        <Loader2 className="mr-2 w-4 h-4 animate-spin" /> Checking…
                      </>
                    ) : (
                      <>
                        Check my documents <ArrowRight className="ml-1.5 w-4 h-4" />
                      </>
                    )}
                  </Button>
                </div>

                {running && (
                  <div className="mt-6 rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/30 px-5 py-4 text-sm text-[#EDF5F2]/60">
                    Reading your documents, extracting the LC terms, and running the discrepancy examiner.
                    This usually takes 30–90 seconds — hang tight.
                  </div>
                )}

                {/* Trust strip */}
                <div className="mt-12 grid sm:grid-cols-3 gap-4">
                  {[
                    { icon: ShieldCheck, t: "UCP 600 / ISBP 745", d: "The same rulebook banks examine against." },
                    { icon: CheckCircle2, t: "Cross-document checks", d: "Amounts, ports, dates and parties matched across the set." },
                    { icon: Sparkles, t: "AI examiner + sanctions", d: "Reads the LC's own 46A/47A clauses; screens parties and vessels." },
                  ].map((b) => (
                    <div key={b.t} className="rounded-2xl border border-[#EDF5F2]/10 bg-[#00382E]/20 p-5">
                      <b.icon className="w-4 h-4 text-[#B2F273]" />
                      <p className="mt-3 text-white text-sm font-medium">{b.t}</p>
                      <p className="mt-1 text-xs text-[#EDF5F2]/50 leading-relaxed">{b.d}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </section>

      <TRDRFooter />
    </div>
  );
}

function RateLimitedCard({ retryAfter }: { retryAfter: number }) {
  return (
    <div className="rounded-3xl border border-[#B2F273]/30 bg-[#B2F273]/[0.06] p-8 text-center">
      <div className="mx-auto w-12 h-12 rounded-2xl bg-[#B2F273]/10 flex items-center justify-center">
        <ShieldCheck className="w-5 h-5 text-[#B2F273]" />
      </div>
      <h2 className="mt-5 text-2xl font-bold text-white">You've used today's free LC check</h2>
      <p className="mt-3 text-[#EDF5F2]/60 max-w-md mx-auto">
        The free checker allows one run per visitor per day — you can try again {humanizeRetry(retryAfter)}.
        Create a free account to run as many checks as you need now, see every finding with its fix, and
        export the full PDF report.
      </p>
      <div className="mt-7 flex flex-wrap gap-3 justify-center">
        <Button asChild className="bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] font-semibold">
          <Link to="/register">
            Create free account <ArrowRight className="ml-1.5 w-4 h-4" />
          </Link>
        </Button>
        <Button asChild variant="outline" className="border-[#EDF5F2]/20 text-white hover:bg-[#EDF5F2]/10">
          <Link to="/login">Log in</Link>
        </Button>
      </div>
    </div>
  );
}
