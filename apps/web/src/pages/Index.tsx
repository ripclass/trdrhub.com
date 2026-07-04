// /lcopilot landing — concierge rewrite, 2026-07 launch (GTM playbook §3.1).
//
// The front door reads as a service: send your LC pack, get back a cited
// discrepancy report within 24 hours, reviewed by a specialist before it
// ships. AI is the how, not the headline. Honesty rules in force: ISBP 821
// (never 745), no invented user counts / savings / accuracy stats, no
// "trusted by banks", advisory-not-legal-advice footer.
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  ChevronDown,
  Clock,
  Download,
  FileCheck,
  FileSearch,
  Lock,
  Mail,
  ShieldCheck,
  Upload,
  UserCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { CONCIERGE_REPORTS } from "@/lib/pricing";
import { useRuleCount } from "@/lib/useRuleCount";

const SAMPLE_REPORT_HREF = "/samples/lcopilot-sample-report.pdf";
// Stable concierge entry: authed → upload, anonymous → fast-path signup.
const START_HREF = "/lcopilot/start-review";

const steps = [
  {
    step: "01",
    icon: Upload,
    title: "Send your documents",
    description:
      "Upload your LC, invoice, bill of lading and packing list — or email the pack to support@trdrhub.com. PDF, scan or photo, MT700 or ISO 20022.",
  },
  {
    step: "02",
    icon: FileSearch,
    title: "Engine check + specialist review",
    description:
      "Our rules engine examines the set against {{RULES}} verified examination rules. Then a trade documentation specialist reviews every report before it ships — nothing goes out unread.",
  },
  {
    step: "03",
    icon: FileCheck,
    title: "Fix issues before you present",
    description:
      "You get a cited discrepancy report — every finding referenced to UCP 600 / ISBP 821, with the exact fix — before you present. Not after the rejection.",
  },
];

const trustAnchors = [
  {
    icon: UserCheck,
    title: "A specialist reviews every report",
    description:
      "No report ships unread. A trade documentation specialist checks every finding before it reaches you.",
  },
  {
    icon: Lock,
    title: "Confidential by default",
    description:
      "Your documents are used only to produce your report. We'll sign an NDA on request.",
  },
  {
    icon: ShieldCheck,
    title: "Refund if not satisfied",
    description:
      "If the report doesn't help you, tell us and we'll refund it in full. No forms, no friction.",
  },
  {
    icon: Download,
    title: "See exactly what you'll get",
    description: "Download a sample report (redacted from a real review) before you spend a dollar.",
  },
];

const faqs = [
  {
    question: "What exactly do I get back?",
    answer:
      "A cited discrepancy report: every finding grouped by severity, referenced to the UCP 600 article or ISBP 821 paragraph it derives from, quoting the LC clause and the evidence found in your document, with a suggested fix. On the $49 tier you also get a bank-ready compliance memo written to forward as-is. Download the sample report on this page to see the format.",
  },
  {
    question: "Who reviews my documents?",
    answer:
      "Our rules engine runs the examination, and a trade documentation specialist reviews every report before it's delivered. You're never handed raw machine output.",
  },
  {
    question: "How fast is 'within 24 hours'?",
    answer:
      "Standard reviews are delivered within 24 hours of submission — usually much faster. If you're up against a presentation deadline, Priority Review guarantees 6-hour turnaround.",
  },
  {
    question: "Do you cover the import side too?",
    answer:
      "Yes. Exporters ask 'will my presentation comply?'; importers ask 'is this LC safe to accept?' — risky clauses, soft clauses, document requirements you can't actually meet. Same price, same turnaround, either side.",
  },
  {
    question: "What document formats do you accept?",
    answer:
      "PDF, scanned image, or a phone photo. LCs in MT700, ISO 20022, or plain PDF. If we can't read something, we'll ask — we won't guess.",
  },
  {
    question: "Is my data confidential?",
    answer:
      "Yes. Your documents are used only to produce your report and are handled under our confidentiality terms. We're happy to sign an NDA before you send anything.",
  },
  {
    question: "What if I'm not satisfied?",
    answer: "Full refund, no questions. If a report doesn't help you present cleaner documents, we don't want your money.",
  },
];

const Index = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(0);
  const ruleCount = useRuleCount();

  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />

      <main>
        {/* Hero — split layout matching the CBAM/EUDR landings: pitch +
            anchors left, interactive "try it free" card right. */}
        <section className="relative pt-40 md:pt-44 pb-16 overflow-hidden bg-[#00261C]">
          <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-[#B2F273]/10 rounded-full blur-[120px]" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid lg:grid-cols-2 gap-10 lg:gap-16 items-start max-w-6xl mx-auto">
              <div className="pt-4">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#B2F273]/10 border border-[#B2F273]/20 mb-6">
                  <UserCheck className="w-4 h-4 text-[#B2F273]" />
                  <span className="text-[#B2F273] text-sm font-medium">
                    A specialist reviews every report before it ships
                  </span>
                </div>
                <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-5 leading-[1.15] tracking-tight font-display">
                  Your LC pack, checked
                  <br />
                  <span className="text-[#B2F273] text-glow-sm">before the bank sees it.</span>
                </h1>
                <p className="text-lg text-[#EDF5F2]/60 leading-relaxed mb-8">
                  Send your LC, invoice, bill of lading and packing list. Get back a cited
                  discrepancy report within 24 hours — every finding referenced to{" "}
                  <span className="text-white font-medium">UCP 600 / ISBP 821</span>, with the
                  fix — before you present.
                </p>

                <div className="space-y-4">
                  <div className="flex gap-3">
                    <AlertTriangle className="w-5 h-5 text-[#B2F273] shrink-0 mt-0.5" />
                    <div>
                      <p className="text-white font-medium text-sm">A refused presentation costs fees, days, and leverage</p>
                      <p className="text-[#EDF5F2]/50 text-sm">
                        One inconsistent date, one missing notation, one unsigned invoice — and
                        you're paying discrepancy fees and negotiating from the back foot.
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <AlertTriangle className="w-5 h-5 text-[#B2F273] shrink-0 mt-0.5" />
                    <div>
                      <p className="text-white font-medium text-sm">Every finding cited, with the fix</p>
                      <p className="text-[#EDF5F2]/50 text-sm">
                        Rule reference, the LC clause, the evidence in your document, and exactly
                        what to change — not a vague warning.
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <AlertTriangle className="w-5 h-5 text-[#B2F273] shrink-0 mt-0.5" />
                    <div>
                      <p className="text-white font-medium text-sm">Export and import sides, same rigor</p>
                      <p className="text-[#EDF5F2]/50 text-sm">
                        "Will my presentation comply?" and "is this LC safe to accept?" — both
                        covered, same price, same 24 hours.
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <AlertTriangle className="w-5 h-5 text-[#B2F273] shrink-0 mt-0.5" />
                    <div>
                      <p className="text-white font-medium text-sm">Confidential, refundable</p>
                      <p className="text-[#EDF5F2]/50 text-sm">
                        NDA on request; full refund if the report doesn't help you.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Try-it-free card — the hero's interactive panel */}
              <div className="bg-[#00382E]/60 border border-[#B2F273]/20 rounded-2xl p-6 sm:p-8">
                <div className="flex items-center gap-2 mb-1">
                  <FileCheck className="w-5 h-5 text-[#B2F273]" />
                  <h3 className="text-lg font-bold text-white font-display">Try it before you spend a dollar</h3>
                </div>
                <p className="text-[#EDF5F2]/50 text-sm mb-6">
                  Two free ways to see exactly what you'd get.
                </p>

                <div className="space-y-4">
                  <div className="bg-[#00261C] border border-[#EDF5F2]/10 rounded-xl p-5">
                    <p className="text-white font-medium text-sm mb-1">Run a free LC check</p>
                    <p className="text-[#EDF5F2]/50 text-xs mb-4">
                      Upload one LC, get an instant machine check — one run a day, no signup,
                      no card.
                    </p>
                    <Button className="w-full h-10 bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
                      <Link to="/check">
                        Check an LC free
                        <ArrowRight className="w-4 h-4 ml-2" />
                      </Link>
                    </Button>
                  </div>

                  <div className="bg-[#00261C] border border-[#EDF5F2]/10 rounded-xl p-5">
                    <p className="text-white font-medium text-sm mb-1">See a real delivered report</p>
                    <p className="text-[#EDF5F2]/50 text-xs mb-4">
                      A redacted report from an actual review — severity-grouped findings,
                      citations, fixes.
                    </p>
                    <Button
                      variant="outline"
                      className="w-full h-10 border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 bg-transparent"
                      asChild
                    >
                      <a href={SAMPLE_REPORT_HREF} download>
                        <Download className="w-4 h-4 mr-2" />
                        Download the sample (PDF)
                      </a>
                    </Button>
                  </div>

                  <div className="pt-4 border-t border-[#EDF5F2]/10 text-center">
                    <p className="text-[#EDF5F2]/50 text-xs mb-3">
                      Ready for the real thing? Full pack review from{" "}
                      <span className="text-white font-semibold">$29</span> · delivered within 24h.
                    </p>
                    <Button className="w-full h-11 bg-[#EDF5F2]/10 hover:bg-[#B2F273] text-white hover:text-[#00261C] font-bold border-none transition-colors" asChild>
                      <Link to={START_HREF}>
                        Get your pack checked — $29
                        <ArrowRight className="w-4 h-4 ml-2" />
                      </Link>
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12 sm:mb-16">
              <p className="text-[#B2F273] font-mono font-semibold mb-3 sm:mb-4 tracking-wide uppercase text-xs sm:text-sm">How it works</p>
              <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-3 sm:mb-4 font-display">
                Three steps to a clean presentation
              </h2>
            </div>

            <div className="max-w-5xl mx-auto">
              <div className="grid md:grid-cols-3 gap-8">
                {steps.map((item, idx) => (
                  <div key={idx} className="relative h-full">
                    <div className="group bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-2xl p-8 hover:border-[#B2F273]/50 transition-all duration-300 hover:-translate-y-1 relative overflow-hidden h-full">
                      <div className="flex items-center justify-between mb-6">
                        <span className="text-5xl font-bold text-[#EDF5F2]/10 font-display group-hover:text-[#B2F273]/20 transition-colors">{item.step}</span>
                        <div className="w-14 h-14 bg-[#B2F273]/10 rounded-xl flex items-center justify-center border border-[#B2F273]/20 group-hover:bg-[#B2F273] transition-all duration-300 relative z-10">
                          <item.icon className="w-7 h-7 text-[#B2F273] group-hover:text-[#00261C] transition-colors" />
                        </div>
                      </div>
                      <h3 className="text-xl font-bold text-white mb-3 font-display group-hover:text-[#B2F273] transition-colors">{item.title}</h3>
                      <p className="text-[#EDF5F2]/60 text-sm leading-relaxed">{item.description.replace("{{RULES}}", ruleCount)}</p>
                      <div className="absolute bottom-0 left-0 w-0 h-[3px] bg-[#B2F273] group-hover:w-full transition-all duration-500 ease-in-out" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="text-center mt-10 text-sm text-[#EDF5F2]/40 flex items-center justify-center gap-2">
              <Mail className="w-4 h-4" />
              Prefer email? Send your pack to{" "}
              <a href="mailto:support@trdrhub.com" className="text-[#B2F273] hover:underline">support@trdrhub.com</a>
              — we'll take it from there.
            </div>
          </div>
        </section>

        {/* Both sides of the LC */}
        <section className="relative py-20 bg-[#00261C] border-y border-[#EDF5F2]/10 overflow-hidden">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12">
              <p className="text-[#B2F273] font-mono font-semibold mb-4 tracking-wide uppercase text-sm">Both sides of the credit</p>
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
                Exporting or importing — same check, same rigor
              </h2>
            </div>
            <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
              <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-2xl p-8">
                <h3 className="text-xl font-bold text-white mb-3 font-display">Exporters &amp; beneficiaries</h3>
                <p className="text-[#EDF5F2]/60 text-sm leading-relaxed mb-4">
                  "Will my presentation comply?" We examine your full document set against the LC's
                  terms before your bank does — so discrepancy fees and refusals stay theoretical.
                </p>
                <ul className="space-y-2 text-sm text-[#EDF5F2]/60">
                  {["Document-by-document examination", "Cross-document consistency (amounts, dates, ports, parties)", "Every finding cited, with the fix"].map((f) => (
                    <li key={f} className="flex items-start gap-2">
                      <CheckCircle className="w-4 h-4 text-[#B2F273] shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-2xl p-8">
                <h3 className="text-xl font-bold text-white mb-3 font-display">Importers &amp; applicants</h3>
                <p className="text-[#EDF5F2]/60 text-sm leading-relaxed mb-4">
                  "Is this LC safe to accept?" We flag risky clauses, soft clauses, and document
                  requirements you can't actually meet — before you're committed to them.
                </p>
                <ul className="space-y-2 text-sm text-[#EDF5F2]/60">
                  {["Draft LC risk review before you sign off", "Soft-clause and trap-clause detection", "Supplier document pre-check on the same transaction"].map((f) => (
                    <li key={f} className="flex items-start gap-2">
                      <CheckCircle className="w-4 h-4 text-[#B2F273] shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* Pricing */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-10 sm:mb-16">
              <p className="text-[#B2F273] font-mono font-semibold mb-3 sm:mb-4 tracking-wide uppercase text-xs sm:text-sm">Pricing</p>
              <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-3 sm:mb-4 font-display">
                One report. One price. No subscription.
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto text-base sm:text-lg px-4">
                Pay per review — a fraction of a single discrepancy fee. Prices in USD; pay in your
                local currency at checkout.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-5 max-w-4xl mx-auto mb-8">
              {CONCIERGE_REPORTS.map((plan) => (
                <div
                  key={plan.id}
                  className={cn(
                    "relative bg-[#00382E]/50 border rounded-2xl p-6 flex flex-col",
                    plan.popular ? "border-[#B2F273] shadow-lg shadow-[#B2F273]/10" : "border-[#EDF5F2]/10",
                  )}
                >
                  {plan.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <span className="px-3 py-1 rounded-full text-xs font-semibold font-mono uppercase tracking-wider bg-[#B2F273] text-[#00261C]">
                        Most popular
                      </span>
                    </div>
                  )}

                  <div className="text-center mb-5">
                    <h3 className="text-lg font-bold text-white mb-1 font-display">{plan.name}</h3>
                    <p className="text-[#EDF5F2]/40 text-xs mb-3">{plan.description}</p>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-4xl font-bold text-white font-display">${plan.priceUsd}</span>
                      <span className="text-[#EDF5F2]/40 text-sm font-mono">/report</span>
                    </div>
                    <p className="text-[#B2F273] text-xs mt-2 font-mono inline-flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {plan.turnaround}
                    </p>
                  </div>

                  <ul className="space-y-2 mb-6 flex-1">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-[#EDF5F2]/60">
                        <CheckCircle className="w-3.5 h-3.5 text-[#B2F273] shrink-0 mt-0.5" />
                        {feature}
                      </li>
                    ))}
                  </ul>

                  <Button
                    className={cn(
                      "w-full h-10 font-bold text-sm border-none",
                      plan.popular
                        ? "bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C]"
                        : "bg-[#EDF5F2]/10 hover:bg-[#EDF5F2]/20 text-white",
                    )}
                    asChild
                  >
                    <Link to={START_HREF}>Start — ${plan.priceUsd}</Link>
                  </Button>
                </div>
              ))}
            </div>

            <div className="text-center text-sm text-[#EDF5F2]/40 space-y-2">
              <p>
                Checking LCs every week? <Link to="/contact" className="text-[#B2F273] hover:underline">Talk to us</Link> about a monthly arrangement.
              </p>
            </div>
          </div>
        </section>

        {/* Trust anchors */}
        <section className="relative py-20 bg-[#00261C] border-y border-[#EDF5F2]/10 overflow-hidden">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12">
              <p className="text-[#B2F273] font-mono font-semibold mb-4 tracking-wide uppercase text-sm">Why trust the report</p>
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
                Built to be forwarded, not filed
              </h2>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 max-w-5xl mx-auto">
              {trustAnchors.map((anchor, idx) => (
                <div key={idx} className="bg-[#00382E]/30 border border-[#EDF5F2]/10 rounded-2xl p-6">
                  <div className="w-12 h-12 bg-[#B2F273]/10 rounded-xl flex items-center justify-center mb-4 border border-[#B2F273]/20">
                    <anchor.icon className="w-6 h-6 text-[#B2F273]" />
                  </div>
                  <h3 className="text-white font-bold mb-2 font-display text-sm">{anchor.title}</h3>
                  <p className="text-[#EDF5F2]/50 text-xs leading-relaxed">{anchor.description}</p>
                </div>
              ))}
            </div>
            <div className="text-center mt-8">
              <Button
                variant="outline"
                className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 bg-transparent"
                asChild
              >
                <a href={SAMPLE_REPORT_HREF} download>
                  <Download className="w-4 h-4 mr-2" />
                  Sample report (redacted)
                </a>
              </Button>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto">
              <div className="text-center mb-12">
                <p className="text-[#B2F273] font-mono font-semibold mb-4 tracking-wide uppercase text-sm">FAQ</p>
                <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 font-display">Common questions</h2>
              </div>

              <div className="space-y-3">
                {faqs.map((faq, idx) => (
                  <div
                    key={idx}
                    className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl overflow-hidden hover:border-[#B2F273]/30 transition-colors"
                  >
                    <button
                      onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                      className="w-full flex items-center justify-between p-5 text-left"
                    >
                      <span className="font-semibold text-white pr-8 font-display">{faq.question}</span>
                      <ChevronDown
                        className={cn(
                          "w-5 h-5 text-[#EDF5F2]/40 transition-transform shrink-0",
                          openFaq === idx && "rotate-180",
                        )}
                      />
                    </button>
                    <div className={cn("grid transition-all duration-200", openFaq === idx ? "grid-rows-[1fr]" : "grid-rows-[0fr]")}>
                      <div className="overflow-hidden">
                        <p className="px-5 pb-5 text-[#EDF5F2]/60 text-sm leading-relaxed">{faq.answer}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="relative py-20 bg-gradient-to-b from-[#00382E] to-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-6 leading-tight font-display">
                Present clean documents,
                <br />
                <span className="bg-gradient-to-r from-[#B2F273] to-[#a3e662] bg-clip-text text-transparent">the first time.</span>
              </h2>

              <p className="text-xl text-[#EDF5F2]/60 mb-8 max-w-xl mx-auto">
                Send your pack now — your cited report is back within 24 hours, reviewed by a specialist.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center mb-10">
                <Button
                  size="lg"
                  className="bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] text-lg px-10 h-14 font-bold border-none"
                  asChild
                >
                  <Link to={START_HREF}>
                    Get your pack checked — $29
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 text-lg px-10 h-14 bg-transparent"
                  asChild
                >
                  <a href="mailto:support@trdrhub.com">Email your documents</a>
                </Button>
              </div>

              <p className="text-xs text-[#EDF5F2]/30 max-w-2xl mx-auto leading-relaxed">
                LCopilot reports are an advisory document pre-check — not legal advice, and not a
                bank's determination of compliance. Findings reference UCP 600 and ISBP 821.
              </p>
            </div>
          </div>
        </section>
      </main>

      <TRDRFooter />
    </div>
  );
};

export default Index;
