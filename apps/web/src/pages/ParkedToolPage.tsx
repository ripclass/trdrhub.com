// Parked-tool landing — Phase 4 launch (2026-07).
//
// Launch discipline: one service done properly beats sixteen half-done
// tools. Every tool that isn't LCopilot / Sanctions / CBAM Check / EUDR
// Check routes here (code stays in-tree; only the routes point at this
// page). Polite, honest, and points the visitor at what IS live.
import { Link } from "react-router-dom";
import { ArrowRight, FileCheck, Leaf, ShieldCheck, Wrench } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";

const LIVE_TOOLS = [
  {
    icon: FileCheck,
    name: "LCopilot",
    description: "Your LC pack, checked before the bank sees it — cited report in 24h.",
    href: "/lcopilot",
  },
  {
    icon: ShieldCheck,
    name: "Sanctions Screener",
    description: "Deterministic OFAC / UN / UK OFSI screening, fail-closed.",
    href: "/sanctions",
  },
  {
    icon: Leaf,
    name: "CBAM Check",
    description: "Is your steel, aluminium or cement in scope? Free check + readiness report.",
    href: "/tools/cbam-readiness-check",
  },
  {
    icon: Leaf,
    name: "EUDR Check",
    description: "Leather, coffee, rubber, wood — EU deforestation-rule readiness.",
    href: "/tools/eudr-readiness-check",
  },
];

export default function ParkedToolPage() {
  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main className="pt-40 pb-24">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl mx-auto text-center mb-14">
            <div className="w-14 h-14 bg-[#B2F273]/10 rounded-2xl border border-[#B2F273]/20 flex items-center justify-center mx-auto mb-6">
              <Wrench className="w-7 h-7 text-[#B2F273]" />
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold text-white mb-4 font-display">
              This tool isn't available right now
            </h1>
            <p className="text-[#EDF5F2]/60 text-lg leading-relaxed">
              We'd rather ship a few things that work brilliantly than many that half-work.
              This tool is parked while we focus on the compliance services below — it may
              return once it meets the same bar.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 gap-5 max-w-3xl mx-auto mb-12">
            {LIVE_TOOLS.map((tool) => (
              <Link
                key={tool.name}
                to={tool.href}
                className="group bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-2xl p-6 hover:border-[#B2F273]/50 transition-all duration-300 hover:-translate-y-0.5 text-left"
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-[#B2F273]/10 rounded-lg border border-[#B2F273]/20 flex items-center justify-center">
                    <tool.icon className="w-5 h-5 text-[#B2F273]" />
                  </div>
                  <h2 className="text-white font-bold font-display group-hover:text-[#B2F273] transition-colors">
                    {tool.name}
                  </h2>
                </div>
                <p className="text-[#EDF5F2]/50 text-sm leading-relaxed">{tool.description}</p>
              </Link>
            ))}
          </div>

          <div className="text-center">
            <p className="text-[#EDF5F2]/40 text-sm mb-4">
              Was this tool important to your workflow? Tell us — it directly shapes what
              comes back first.
            </p>
            <Button
              variant="outline"
              className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 bg-transparent"
              asChild
            >
              <a href="mailto:support@trdrhub.com?subject=Parked%20tool%20request">
                Tell us what you need
                <ArrowRight className="w-4 h-4 ml-2" />
              </a>
            </Button>
          </div>
        </div>
      </main>
      <TRDRFooter />
    </div>
  );
}
