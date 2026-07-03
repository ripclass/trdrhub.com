// Homepage closing CTA — Phase 4 rebuild (2026-07 launch).
//
// The fake newsletter form (thanked the visitor, stored nothing) is gone.
// Primary CTA = LCopilot concierge; secondary = the real /check lead magnet.
import { Button } from "@/components/ui/button";
import { ArrowRight, Mail } from "lucide-react";
import { Link } from "react-router-dom";

export function CTASection() {
  return (
    <section className="py-24 md:py-32 bg-[#EDF5F2] relative overflow-hidden">
      {/* Background Noise/Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(0,38,28,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,38,28,0.03)_1px,transparent_1px)] bg-[size:40px_40px] opacity-100" />
      <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-b from-[#EDF5F2] to-transparent z-10" />
      <div className="absolute bottom-0 left-0 w-full h-32 bg-gradient-to-t from-[#EDF5F2] to-transparent z-10" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-20">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-[#00261C] mb-6 leading-tight font-display">
            Present clean documents,
            <br />
            <span className="text-[#00261C]">the first time.</span>
          </h2>
          <p className="text-xl text-[#00261C]/80 mb-10 max-w-xl mx-auto">
            Send your LC pack — your cited report is back within 24 hours, reviewed by a
            specialist. Or run one free LC check per day, no card, no signup.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
            <Button
              size="lg"
              className="bg-[#00261C] text-[#B2F273] hover:bg-[#00382E] text-lg px-8 py-6 h-auto font-semibold group border-none shadow-xl"
              asChild
            >
              <Link to="/lcopilot">
                Get your pack checked — $29
                <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
              </Link>
            </Button>
            <Button
              variant="outline"
              size="lg"
              className="border-[#00261C]/20 text-[#00261C] hover:bg-[#00261C] hover:text-[#B2F273] hover:border-[#00261C] text-lg px-8 py-6 h-auto bg-transparent transition-colors"
              asChild
            >
              <Link to="/check">Run a free LC check</Link>
            </Button>
          </div>

          <p className="text-[#00261C]/50 text-sm flex items-center justify-center gap-2">
            <Mail className="w-4 h-4" />
            Prefer email? Send your documents to{" "}
            <a href="mailto:support@trdrhub.com" className="font-semibold underline hover:no-underline">
              support@trdrhub.com
            </a>
          </p>
        </div>
      </div>
    </section>
  );
}
