import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Button } from "@/components/ui/button";
import { BookOpen, AlertTriangle, CheckCircle2, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

const articles = [
  { id: "1-5", title: "General Provisions (Articles 1-5)", desc: "Application, definitions, and interpretations." },
  { id: "6-13", title: "Liabilities and Responsibilities (Articles 6-13)", desc: "Issuing bank and confirming bank undertakings." },
  { id: "14-17", title: "Examination of Documents (Articles 14-17)", desc: "Standard for examination of documents." },
  { id: "18-28", title: "Documents (Articles 18-28)", desc: "Commercial invoice, transport documents, insurance." },
  { id: "29-33", title: "Miscellaneous Provisions (Articles 29-33)", desc: "Extension of expiry dates, tolerance in amount." },
  { id: "34-37", title: "Disclaimers (Articles 34-37)", desc: "Effectiveness of documents, transmission and translation." },
  { id: "38-39", title: "Transferable Credits (Articles 38-39)", desc: "Transferability and assignment of proceeds." },
];

const UCP600Page = () => {
  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main className="pt-32 md:pt-48 pb-24 relative min-h-screen">
        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none fixed" />

        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          
          {/* Header */}
          <div className="max-w-4xl mx-auto mb-16 text-center">
            <div className="inline-flex items-center gap-2 mb-6">
              <BookOpen className="w-5 h-5 text-[#B2F273]" />
              <span className="text-[#B2F273] font-mono text-xs tracking-widest uppercase">Digital Guide</span>
            </div>
            <h1 className="text-4xl md:text-6xl font-bold text-white mb-6 font-display">
              The Definitive Guide to
              <br />
              <span className="text-[#B2F273] text-glow-sm">UCP 600.</span>
            </h1>
            <p className="text-lg text-[#EDF5F2]/60 leading-relaxed">
              Uniform Customs and Practice for Documentary Credits (UCP 600) is the set of rules that govern Letters of Credit worldwide. 
              TRDR Hub's engine is built on these 39 articles.
            </p>
          </div>

          {/* Content Grid */}
          <div className="grid lg:grid-cols-3 gap-12 max-w-6xl mx-auto">
            
            {/* Table of Contents */}
            <div className="lg:col-span-2 space-y-4">
              {articles.map((article, index) => (
                <div key={index} className="group p-6 rounded-2xl bg-[#00382E]/30 border border-[#EDF5F2]/10 hover:border-[#B2F273]/30 transition-all cursor-pointer">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-xl font-bold text-white mb-2 group-hover:text-[#B2F273] transition-colors">
                        {article.title}
                      </h3>
                      <p className="text-[#EDF5F2]/60 text-sm">
                        {article.desc}
                      </p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-[#EDF5F2]/20 group-hover:text-[#B2F273] transition-colors mt-1" />
                  </div>
                </div>
              ))}
            </div>

            {/* Sidebar */}
            <div className="space-y-8">
              <div className="p-6 rounded-2xl bg-[#B2F273]/10 border border-[#B2F273]/20">
                <h3 className="text-lg font-bold text-[#B2F273] mb-4 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5" />
                  Why it matters
                </h3>
                <p className="text-[#EDF5F2]/80 text-sm mb-4">
                  70% of documents are rejected on first presentation because of discrepancies against UCP 600 rules.
                </p>
                <ul className="space-y-2 text-sm text-[#EDF5F2]/60">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-[#B2F273] shrink-0 mt-0.5" />
                    Avoid discrepancy fees
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-[#B2F273] shrink-0 mt-0.5" />
                    Speed up payments
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-[#B2F273] shrink-0 mt-0.5" />
                    Reduce operational risk
                  </li>
                </ul>
              </div>

              <div className="p-6 rounded-2xl bg-[#00261C] border border-[#EDF5F2]/10 text-center">
                <h3 className="text-lg font-bold text-white mb-2">Automate UCP 600</h3>
                <p className="text-[#EDF5F2]/60 text-sm mb-6">
                  Don't memorize the rules. Let our AI validate your documents against them instantly.
                </p>
                <Button className="w-full bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] font-bold">
                  Try LCopilot Free
                </Button>
              </div>
            </div>

          </div>
        </div>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default UCP600Page;
