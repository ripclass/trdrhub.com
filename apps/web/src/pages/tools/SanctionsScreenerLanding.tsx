// /sanctions landing — rewritten for the 2026-07 launch.
//
// The previous version predated the RulHub wire (Phase 2) and carried a
// fabricated pricing table (Free/$29/$99/$299 tiers that were never sold)
// plus overclaims: "50+ lists", "dark activity detection", "ECCN lookup",
// "OFAC 50% rule applied" (the engine explicitly does NOT resolve
// ownership), "PDF certificates", "<2s", "99.9% uptime". This page now says
// exactly what the screener does: deterministic designated-party screening
// against OFAC SDN / OFAC Consolidated / UN / UK OFSI, fail-closed.
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  ChevronDown,
  Database,
  FileCheck,
  Loader2,
  Search,
  Shield,
  ShieldAlert,
  Ship,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Live quick-screen widget — the hero's interactive card, mirroring the
// CBAM/EUDR scope-check widget. Uses the public quick-screen endpoint
// (5 free checks/day per visitor; free account lifts the cap).
// ---------------------------------------------------------------------------

interface QuickResult {
  query: string;
  status: "clear" | "potential_match" | "match" | "unavailable";
  risk_level: string;
  total_matches: number;
  recommendation: string;
  certificate_id: string;
}

const QUICK_VERDICTS: Record<string, { label: string; cls: string }> = {
  clear: { label: "✅ No matches found", cls: "border-emerald-400/40 bg-emerald-500/10 text-emerald-300" },
  potential_match: { label: "⚠️ Possible match — review required", cls: "border-amber-400/40 bg-amber-500/10 text-amber-300" },
  match: { label: "❌ Match found — do not proceed", cls: "border-red-400/40 bg-red-500/10 text-red-300" },
  unavailable: { label: "⛔ Not screened — do not treat as clear", cls: "border-orange-400/40 bg-orange-500/10 text-orange-300" },
};

function QuickScreenWidget() {
  const [name, setName] = useState("");
  const [type, setType] = useState("party");
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<QuickResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (name.trim().length < 2) return;
    setChecking(true);
    setResult(null);
    setError(null);
    try {
      const params = new URLSearchParams({ query: name.trim(), type });
      const res = await fetch(`/api/sanctions/quick-screen?${params}`, { method: "POST" });
      if (!res.ok) {
        let message = "Screening is unavailable right now — do not treat this as a clear result.";
        try {
          const payload = await res.json();
          message = payload?.detail?.message || message;
        } catch { /* keep default */ }
        setError(message);
        return;
      }
      setResult(await res.json());
    } catch {
      setError("Screening is unavailable right now — do not treat this as a clear result.");
    } finally {
      setChecking(false);
    }
  };

  const verdict = result ? QUICK_VERDICTS[result.status] ?? QUICK_VERDICTS.unavailable : null;

  return (
    <div className="bg-[#00382E]/60 border border-[#B2F273]/20 rounded-2xl p-6 sm:p-8">
      <div className="flex items-center gap-2 mb-1">
        <Search className="w-5 h-5 text-[#B2F273]" />
        <h3 className="text-lg font-bold text-white font-display">Screen a name — free, right now</h3>
      </div>
      <p className="text-[#EDF5F2]/50 text-sm mb-6">
        5 free checks a day, no signup. Free account for unlimited checks during launch.
      </p>

      <div className="space-y-4">
        <div>
          <label className="block text-sm text-white font-medium mb-1.5">What are you screening?</label>
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="w-full h-10 rounded-lg bg-[#00261C] border border-[#EDF5F2]/15 text-white text-sm px-3 focus:border-[#B2F273]/60 focus:outline-none"
          >
            <option value="party">Party / company / person</option>
            <option value="vessel">Vessel (name or IMO)</option>
            <option value="goods">Goods description</option>
          </select>
        </div>
        <div>
          <label className="block text-sm text-white font-medium mb-1.5">Name to screen</label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
            placeholder="e.g. Acme Trading Company Ltd"
            className="bg-[#00261C] border-[#EDF5F2]/15 text-white placeholder:text-[#EDF5F2]/30"
          />
        </div>
      </div>

      <Button
        onClick={run}
        disabled={checking || name.trim().length < 2}
        className="w-full mt-6 h-11 bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none"
      >
        {checking ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
        Screen now
      </Button>

      {error && (
        <div className="mt-5 rounded-xl border border-orange-400/40 bg-orange-500/10 p-4">
          <p className="text-sm font-semibold text-orange-300 mb-1">Not screened — do not treat as clear</p>
          <p className="text-sm text-[#EDF5F2]/70">{error}</p>
        </div>
      )}

      {result && verdict && (
        <div className={cn("mt-5 rounded-xl border p-4", verdict.cls)}>
          <p className="font-bold mb-1">{verdict.label}</p>
          <p className="text-sm text-[#EDF5F2]/70 mb-3">{result.recommendation}</p>
          <div className="flex items-center justify-between text-xs text-[#EDF5F2]/40">
            <span className="font-mono">Ref: {result.certificate_id}</span>
            <Link
              to={type === "vessel" ? "/sanctions/dashboard/screen/vessel" : type === "goods" ? "/sanctions/dashboard/screen/goods" : "/sanctions/dashboard/screen/party"}
              className="text-[#B2F273] hover:underline inline-flex items-center gap-1"
            >
              Full details in the screener <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

const screeningTypes = [
  {
    id: "party",
    title: "Screen a Party",
    description: "Buyers, sellers, banks and agents against the designated-party lists",
    to: "/sanctions/dashboard/screen/party",
    icon: Users,
  },
  {
    id: "vessel",
    title: "Screen a Vessel",
    description: "Vessel names and IMO numbers — exact IMO matching plus tiered name matching",
    to: "/sanctions/dashboard/screen/vessel",
    icon: Ship,
  },
  {
    id: "goods",
    title: "Screen Goods",
    description: "Goods and destination against sanctions-programme rules (embargoes, sectoral restrictions)",
    to: "/sanctions/dashboard/screen/goods",
    icon: Search,
  },
];

const features = [
  {
    icon: Database,
    title: "The lists that matter, screened properly",
    description:
      "OFAC SDN, OFAC Consolidated (Non-SDN), UN Security Council, and UK OFSI designated-party lists, plus a sanctions programme-rules corpus for country and sectoral restrictions. EU consolidated list is being added.",
    bullets: ["OFAC SDN + Consolidated", "UN Security Council", "UK OFSI", "Programme rules (embargoes, sectoral)"],
  },
  {
    icon: Shield,
    title: "Deterministic matching — no AI verdicts",
    description:
      "Tiered name matching: exact → token-sorted key → fuzzy, with exact IMO matching for vessels. Every hit shows its score, match method, and the list entry that fired. No LLM decides whether a hit is real.",
    bullets: ["Exact / key / fuzzy tiers", "IMO-number matching", "Per-hit score + method", "Block / review action per hit"],
  },
  {
    icon: ShieldAlert,
    title: "Fail-closed by design",
    description:
      "If screening can't run — engine down, lists not consulted — you see \"not screened, do not treat as clear\". Never a silent empty result. Every result carries the list as-of dates it was screened against.",
    bullets: ["Unscreened ≠ clear, ever", "List as-of dates on results", "Explicit caveats on every hit", "OFAC 50% ownership NOT resolved — and we say so"],
  },
  {
    icon: FileCheck,
    title: "Built into your document checks",
    description:
      "Every LCopilot pack review runs sanctions screening as part of the compliance bundle — parties in your LC and documents are screened without a separate step. The standalone screener is here when you need a quick check.",
    bullets: ["Included in every LCopilot review", "Single-name quick checks", "Batch CSV — up to 100 rows", "Screening reference id per result"],
  },
];

const process = [
  {
    step: "1",
    title: "Enter details",
    description: "Type a party name, a vessel name or IMO number, or describe your goods and destination",
  },
  {
    step: "2",
    title: "We screen everything",
    description: "All covered lists plus programme rules on every check — no cherry-picking lists",
  },
  {
    step: "3",
    title: "Act on a clear verdict",
    description: "Clear, possible match (review), or match (block) — with the evidence and caveats to act on",
  },
];

const faqs = [
  {
    q: "Which sanctions lists do you cover?",
    a: "OFAC SDN, OFAC Consolidated (Non-SDN), UN Security Council, and UK OFSI designated-party lists, plus a sanctions programme-rules corpus covering country embargoes and sectoral restrictions. The EU consolidated list is pending and not yet screened — we say so rather than claim it. Every result lists exactly which sources were consulted and their as-of dates.",
  },
  {
    q: "What does \"fail-closed\" mean?",
    a: "If a screen can't be completed — the engine is unreachable, or the lists weren't consulted — the result says \"not screened — do not treat as clear\" instead of showing an empty no-hits result. An absence of hits only counts when the screen actually ran.",
  },
  {
    q: "What happens on a potential match?",
    a: "You see the matched list entry, the match score and method (exact, key, or fuzzy), the sanctions programmes involved, a block-or-review action, and the caveats — including that ownership structures (the OFAC 50% rule) are not resolved, so a clear name can still be majority-owned by a designated party. Escalate potential matches to your compliance officer.",
  },
  {
    q: "What does it cost?",
    a: "Anonymous visitors get 5 free checks a day. A free account lifts that during launch, and batch screening (CSV, up to 100 rows per run) needs one. Every paid LCopilot pack review includes sanctions screening as part of the compliance bundle. Need programmatic/API screening at volume? Email support@trdrhub.com.",
  },
  {
    q: "Is this a replacement for legal advice or a compliance programme?",
    a: "No. The screener is a compliance aid — deterministic, audited, and honest about its coverage — but it is not legal advice and not a substitute for your own sanctions-compliance programme. Verify potential matches against the official list entry before acting.",
  },
];

const SanctionsScreenerLanding = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />

      <main>
        {/* Hero — split layout matching the CBAM/EUDR landings: pitch +
            anchors left, live widget right. */}
        <section className="relative pt-40 md:pt-44 pb-16 overflow-hidden bg-[#00261C]">
          <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-[#B2F273]/10 rounded-full blur-[120px]" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid lg:grid-cols-2 gap-10 lg:gap-16 items-start max-w-6xl mx-auto">
              <div className="pt-4">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#B2F273]/10 border border-[#B2F273]/20 mb-6">
                  <Shield className="w-4 h-4 text-[#B2F273]" />
                  <span className="text-[#B2F273] text-sm font-medium">Deterministic · Fail-closed</span>
                </div>
                <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-5 leading-[1.15] tracking-tight font-display">
                  Sanctions screening you can
                  <br />
                  <span className="text-[#B2F273] text-glow-sm">defend in an audit.</span>
                </h1>
                <p className="text-lg text-[#EDF5F2]/60 leading-relaxed mb-8">
                  Deterministic screening against OFAC SDN, OFAC Consolidated, UN and UK OFSI
                  designated-party lists. Every hit carries its evidence; every failure says
                  "not screened" instead of pretending you're clear.
                </p>

                <div className="space-y-4">
                  <div className="flex gap-3">
                    <AlertTriangle className="w-5 h-5 text-[#B2F273] shrink-0 mt-0.5" />
                    <div>
                      <p className="text-white font-medium text-sm">One missed name can freeze a whole transaction</p>
                      <p className="text-[#EDF5F2]/50 text-sm">Banks screen every party on your documents — screen them first, before the LC does it for you.</p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <AlertTriangle className="w-5 h-5 text-[#B2F273] shrink-0 mt-0.5" />
                    <div>
                      <p className="text-white font-medium text-sm">Deterministic matching, evidence on every hit</p>
                      <p className="text-[#EDF5F2]/50 text-sm">Exact → key → fuzzy tiers with score, method and the exact list entry. No AI deciding what's a hit.</p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <AlertTriangle className="w-5 h-5 text-[#B2F273] shrink-0 mt-0.5" />
                    <div>
                      <p className="text-white font-medium text-sm">Fail-closed, always</p>
                      <p className="text-[#EDF5F2]/50 text-sm">If the screen can't run you see "not screened — do not treat as clear". Never a silent empty result.</p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <AlertTriangle className="w-5 h-5 text-[#B2F273] shrink-0 mt-0.5" />
                    <div>
                      <p className="text-white font-medium text-sm">Built into every LCopilot review</p>
                      <p className="text-[#EDF5F2]/50 text-sm">Your $29 pack review screens all parties as part of the compliance bundle.</p>
                    </div>
                  </div>
                </div>
              </div>

              <QuickScreenWidget />
            </div>
          </div>
        </section>

        {/* Screening types */}
        <section className="relative py-16 bg-[#00261C] border-t border-[#EDF5F2]/10">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
              {screeningTypes.map((type) => (
                <div key={type.id} className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-2xl p-6 hover:border-[#B2F273]/30 transition-all group backdrop-blur-sm">
                  <div className="w-12 h-12 bg-[#B2F273]/10 rounded-lg flex items-center justify-center mb-4 border border-[#B2F273]/20 group-hover:bg-[#B2F273] transition-colors">
                    <type.icon className="w-6 h-6 text-[#B2F273] group-hover:text-[#00261C] transition-colors" />
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2 font-display">{type.title}</h3>
                  <p className="text-[#EDF5F2]/60 text-sm mb-4">{type.description}</p>
                  <Button className="w-full bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
                    <Link to={type.to}>
                      Start Screening <ArrowRight className="w-4 h-4 ml-2" />
                    </Link>
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="relative py-20 bg-[#00261C] border-y border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-14">
              <p className="text-[#B2F273] font-mono font-semibold mb-4 tracking-wide uppercase text-sm">
                What it actually does
              </p>
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
                Honest coverage beats a long list of logos
              </h2>
            </div>

            <div className="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto">
              {features.map((feature, idx) => (
                <div key={idx} className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-2xl p-8">
                  <div className="w-12 h-12 bg-[#B2F273]/10 rounded-xl flex items-center justify-center mb-4 border border-[#B2F273]/20">
                    <feature.icon className="w-6 h-6 text-[#B2F273]" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2 font-display">{feature.title}</h3>
                  <p className="text-[#EDF5F2]/60 text-sm leading-relaxed mb-4">{feature.description}</p>
                  <ul className="grid grid-cols-2 gap-1.5">
                    {feature.bullets.map((b, i) => (
                      <li key={i} className="flex items-start gap-1.5 text-xs text-[#EDF5F2]/50">
                        <CheckCircle className="w-3 h-3 text-[#B2F273] shrink-0 mt-0.5" />
                        {b}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <p className="text-[#B2F273] font-mono font-semibold mb-4 tracking-wide uppercase text-sm">How it works</p>
              <h2 className="text-2xl sm:text-3xl font-bold text-white font-display">Three steps, no list cherry-picking</h2>
            </div>
            <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {process.map((p) => (
                <div key={p.step} className="text-center px-4">
                  <div className="w-12 h-12 rounded-full bg-[#B2F273]/10 border border-[#B2F273]/30 text-[#B2F273] font-bold font-display flex items-center justify-center mx-auto mb-4">
                    {p.step}
                  </div>
                  <h3 className="text-white font-bold mb-2 font-display">{p.title}</h3>
                  <p className="text-[#EDF5F2]/50 text-sm">{p.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing — honest launch model, no invented tiers */}
        <section className="relative py-20 bg-[#00261C] border-y border-[#EDF5F2]/10 overflow-hidden">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <p className="text-[#B2F273] font-mono font-semibold mb-4 tracking-wide uppercase text-sm">Pricing</p>
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-3 font-display">
                Free to check. Included where it counts.
              </h2>
            </div>
            <div className="grid md:grid-cols-3 gap-5 max-w-4xl mx-auto">
              <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-2xl p-6 text-center flex flex-col">
                <h3 className="text-lg font-bold text-white font-display mb-1">Single checks</h3>
                <div className="text-4xl font-bold text-white font-display my-3">Free</div>
                <p className="text-[#EDF5F2]/50 text-sm mb-5 flex-1">
                  5 checks a day without an account — unlimited with a free account during launch.
                </p>
                <Button className="bg-[#EDF5F2]/10 hover:bg-[#EDF5F2]/20 text-white border-none" asChild>
                  <Link to="/sanctions/dashboard/screen/party">Screen a name</Link>
                </Button>
              </div>
              <div className="bg-[#00382E]/50 border border-[#B2F273] rounded-2xl p-6 text-center flex flex-col shadow-lg shadow-[#B2F273]/10">
                <h3 className="text-lg font-bold text-white font-display mb-1">Batch screening</h3>
                <div className="text-4xl font-bold text-white font-display my-3">Free<span className="text-base text-[#EDF5F2]/40 font-mono"> · account</span></div>
                <p className="text-[#EDF5F2]/50 text-sm mb-5 flex-1">
                  CSV upload, up to 100 names per run, per-row results and export.
                </p>
                <Button className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
                  <Link to="/sanctions/dashboard/batch">Upload a CSV</Link>
                </Button>
              </div>
              <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-2xl p-6 text-center flex flex-col">
                <h3 className="text-lg font-bold text-white font-display mb-1">In every LC review</h3>
                <div className="text-4xl font-bold text-white font-display my-3">$29<span className="text-base text-[#EDF5F2]/40 font-mono">/pack</span></div>
                <p className="text-[#EDF5F2]/50 text-sm mb-5 flex-1">
                  Every LCopilot pack review screens your parties as part of the compliance bundle.
                </p>
                <Button className="bg-[#EDF5F2]/10 hover:bg-[#EDF5F2]/20 text-white border-none" asChild>
                  <Link to="/lcopilot">See LCopilot</Link>
                </Button>
              </div>
            </div>
            <p className="text-center text-[#EDF5F2]/30 text-xs mt-8">
              Programmatic / API screening at volume?{" "}
              <a href="mailto:support@trdrhub.com" className="text-[#B2F273]/70 hover:text-[#B2F273] underline">
                Talk to us
              </a>
              .
            </p>
          </div>
        </section>

        {/* FAQ */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
              <div className="text-center mb-12">
                <p className="text-[#B2F273] font-mono font-semibold mb-4 tracking-wide uppercase text-sm">FAQ</p>
                <h2 className="text-3xl font-bold text-white font-display">Common questions</h2>
              </div>
              <div className="space-y-3">
                {faqs.map((faq, idx) => (
                  <div key={idx} className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl overflow-hidden hover:border-[#B2F273]/30 transition-colors">
                    <button
                      onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                      className="w-full flex items-center justify-between p-5 text-left"
                    >
                      <span className="font-semibold text-white pr-8 font-display">{faq.q}</span>
                      <ChevronDown className={cn("w-5 h-5 text-[#EDF5F2]/40 transition-transform shrink-0", openFaq === idx && "rotate-180")} />
                    </button>
                    <div className={cn("grid transition-all duration-200", openFaq === idx ? "grid-rows-[1fr]" : "grid-rows-[0fr]")}>
                      <div className="overflow-hidden">
                        <p className="px-5 pb-5 text-[#EDF5F2]/60 text-sm leading-relaxed">{faq.a}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="relative py-20 bg-gradient-to-b from-[#00382E] to-[#00261C] border-t border-[#EDF5F2]/10">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6 font-display">
              Thirty seconds to a defensible answer.
            </h2>
            <Button
              size="lg"
              className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] text-lg px-10 h-14 font-bold border-none"
              asChild
            >
              <Link to="/sanctions/dashboard/screen/party">
                Screen a name — free
                <ArrowRight className="w-5 h-5 ml-2" />
              </Link>
            </Button>
            <p className="text-xs text-[#EDF5F2]/30 max-w-xl mx-auto mt-8 leading-relaxed">
              A screening aid, not legal advice, and not a substitute for your own
              sanctions-compliance programme. Ownership structures (OFAC 50% rule) are not
              resolved. Verify potential matches against the official list entry before acting.
            </p>
          </div>
        </section>
      </main>

      <TRDRFooter />
    </div>
  );
};

export default SanctionsScreenerLanding;
