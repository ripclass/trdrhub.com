// Homepage tools grid — Phase 4 rebuild (2026-07 launch).
//
// Only the four live tools (LCopilot, Sanctions Screener, CBAM Check,
// EUDR Check) + the RulGPT cross-link. Everything else is parked — see
// pages/ParkedToolPage.tsx. Do not re-add parked tools here without them
// passing the works-e2e / zero-maintenance / no-dilution bar.
import { Link } from "react-router-dom";
import { ArrowRight, ClipboardCheck, FileCheck, Leaf, MessageCircle, ShieldCheck, TreeDeciduous } from "lucide-react";
import { Button } from "@/components/ui/button";

const liveTools = [
  {
    icon: ClipboardCheck,
    name: "Proofline",
    tagline: "Verified Trade Clearance",
    description:
      "Check the parties, order, shipment, documents, credentials and payment evidence together, then receive a specialist-reviewed decision and action list.",
    href: "/proofline",
    price: "per trade case",
  },
  {
    icon: FileCheck,
    name: "LCopilot",
    tagline: "LC pack review — the flagship",
    description:
      "Send your LC, invoice, B/L and packing list. A cited discrepancy report — every finding referenced to UCP 600 / ISBP 821, with the fix — comes back within 24 hours, specialist-reviewed.",
    href: "/lcopilot",
    price: "from $29 per pack",
  },
  {
    icon: ShieldCheck,
    name: "Sanctions Screener",
    tagline: "Designated-party screening",
    description:
      "Deterministic screening against OFAC SDN, OFAC Consolidated, UN and UK OFSI lists — single names or batch. Fail-closed: an unscreened result is never shown as clear.",
    href: "/sanctions",
    price: "included with LCopilot",
  },
  {
    icon: Leaf,
    name: "CBAM Check",
    tagline: "EU carbon border readiness",
    description:
      "Exporting steel, aluminium, cement, fertilisers or hydrogen to the EU? Free instant scope check, plus a cited supplier-readiness report your EU buyer can use.",
    href: "/tools/cbam-readiness-check",
    price: "free check · report $149",
  },
  {
    icon: TreeDeciduous,
    name: "EUDR Check",
    tagline: "EU deforestation-rule readiness",
    description:
      "Leather, coffee, cocoa, rubber, palm, soy or wood products heading to the EU? Check your scope free, then map your geolocation and legality gaps before your buyer asks.",
    href: "/tools/eudr-readiness-check",
    price: "free check · report $149",
  },
];

export function ToolsSection() {
  return (
    <section id="tools" className="py-24 bg-[#00261C] relative overflow-hidden">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
      <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center mb-14">
          <p className="text-[#B2F273] font-mono font-semibold mb-4 tracking-wide uppercase text-sm">
            What's live today
          </p>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-4 font-display">
            Five things. Done properly.
          </h2>
          <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto text-lg">
            We ship compliance services that hold up in front of a bank or a buyer —
            not a wall of half-finished tools.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto mb-12">
          {liveTools.map((tool) => (
            <Link
              key={tool.name}
              to={tool.href}
              className="group bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-2xl p-8 hover:border-[#B2F273]/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_10px_40px_-10px_rgba(178,242,115,0.1)] relative overflow-hidden"
            >
              <div className="flex items-start justify-between mb-5">
                <div className="w-14 h-14 bg-[#B2F273]/10 rounded-xl flex items-center justify-center border border-[#B2F273]/20 group-hover:bg-[#B2F273] transition-colors duration-300">
                  <tool.icon className="w-7 h-7 text-[#B2F273] group-hover:text-[#00261C] transition-colors" />
                </div>
                <span className="px-2.5 py-1 bg-[#B2F273]/10 rounded-full text-xs font-medium text-[#B2F273] border border-[#B2F273]/20 font-mono">
                  {tool.price}
                </span>
              </div>
              <p className="text-[#EDF5F2]/40 text-xs font-mono uppercase tracking-wider mb-1">{tool.tagline}</p>
              <h3 className="text-2xl font-bold text-white mb-3 font-display group-hover:text-[#B2F273] transition-colors">
                {tool.name}
              </h3>
              <p className="text-[#EDF5F2]/60 text-sm leading-relaxed mb-4">{tool.description}</p>
              <span className="inline-flex items-center gap-1.5 text-[#B2F273] text-sm font-medium">
                Open {tool.name}
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </span>
              <div className="absolute bottom-0 left-0 w-0 h-[3px] bg-[#B2F273] group-hover:w-full transition-all duration-500 ease-in-out" />
            </Link>
          ))}
        </div>

        {/* RulGPT cross-link */}
        <div className="max-w-5xl mx-auto">
          <div className="bg-gradient-to-r from-[#00382E] to-[#00261C] border border-[#EDF5F2]/10 rounded-2xl p-6 md:p-8 flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-[#B2F273]/10 rounded-xl border border-[#B2F273]/20 flex items-center justify-center shrink-0">
                <MessageCircle className="w-6 h-6 text-[#B2F273]" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-white font-display mb-1">
                  Just have a question? Ask RulGPT — free.
                </h3>
                <p className="text-[#EDF5F2]/60 text-sm">
                  Cited answers on UCP 600, ISBP 821, URDG 758, ISP98 and sanctions — plus a
                  paste-your-MT700 interpreter. No document check needed.
                </p>
              </div>
            </div>
            <Button
              className="bg-[#EDF5F2]/10 hover:bg-[#EDF5F2]/20 text-white border-none shrink-0"
              asChild
            >
              <a href="https://tfrules.com" target="_blank" rel="noopener noreferrer">
                Ask RulGPT
                <ArrowRight className="w-4 h-4 ml-2" />
              </a>
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
