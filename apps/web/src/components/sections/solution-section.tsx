import { Check, Zap, Shield, Globe, Bot, Workflow, ArrowRight, FileX } from "lucide-react";

const solutions = [
  {
    icon: Bot,
    name: "AI Core",
    description: "Proprietary ML models trained on millions of trade documents. It doesn't just read; it understands context.",
  },
  {
    icon: Workflow,
    name: "Unified Workflow",
    description: "One dashboard for LCs, collections, payments, and logistics. Stop switching between 10 different tabs.",
  },
  {
    icon: Zap,
    name: "Real-Time Velocity",
    description: "What took days now takes seconds. Instant validation, screening, and document generation.",
  },
  {
    icon: Globe,
    name: "Global Rulebook",
    description: "Built-in compliance for 60+ countries and all major ICC standards (UCP600, ISBP745).",
  },
  {
    icon: Shield,
    name: "Defense Grade",
    description: "Bank-level encryption (AES-256) and SOC 2 Type II compliance. Your data is safer than in a filing cabinet.",
  },
  {
    icon: Check,
    name: "Decision Intelligence",
    description: "Don't just get errors. Get fixes. Our engine suggests specific corrections to prevent rejections.",
  },
];

export function SolutionSection() {
  return (
    <section className="py-24 sm:py-32 bg-[#00261C] relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-[#B2F273]/5 rounded-full blur-[100px] -translate-y-1/2 translate-x-1/3" />
      <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-[#B2F273]/5 rounded-full blur-[100px] translate-y-1/2 -translate-x-1/3" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section header */}
        <div className="text-center mb-20">
          <div className="inline-flex items-center gap-2 mb-6">
            <div className="w-2 h-2 bg-[#B2F273] rounded-full animate-pulse" />
            <p className="text-[#B2F273] font-mono text-xs tracking-widest uppercase">The Operating System</p>
          </div>
          
          <h2 className="text-4xl md:text-6xl lg:text-7xl font-bold text-white mb-8 leading-[0.95] font-display tracking-tight">
            One platform for
            <br />
            <span className="text-[#B2F273] text-glow">everything trade.</span>
          </h2>
          <p className="text-lg md:text-xl text-[#EDF5F2]/60 max-w-3xl mx-auto font-light leading-relaxed">
            We've digitized the entire trade lifecycle. From the first PO to final settlement, 
            <span className="text-white font-medium"> TRDR Hub</span> handles the complexity so you can handle the business.
          </p>
        </div>

        {/* Solution grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-7xl mx-auto mb-24">
          {solutions.map((solution, index) => (
            <div
              key={index}
              className="group bg-[#00261C] border border-[#EDF5F2]/10 rounded-2xl p-8 hover:border-[#B2F273]/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_10px_40px_-10px_rgba(178,242,115,0.1)]"
            >
              <div className="flex items-start justify-between mb-6">
                <div className="w-14 h-14 bg-[#B2F273]/10 rounded-xl flex items-center justify-center group-hover:bg-[#B2F273] transition-colors duration-300">
                  <solution.icon className="w-7 h-7 text-[#B2F273] group-hover:text-[#00261C] transition-colors duration-300" />
                </div>
                <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 transform translate-x-2 group-hover:translate-x-0">
                  <ArrowRight className="w-5 h-5 text-[#B2F273]" />
                </div>
              </div>
              
              <h3 className="text-xl font-bold text-white mb-3 font-display group-hover:text-[#B2F273] transition-colors duration-300">
                {solution.name}
              </h3>
              <p className="text-[#EDF5F2]/60 leading-relaxed text-sm">
                {solution.description}
              </p>
            </div>
          ))}
        </div>

        {/* Comparison Section */}
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center relative">
            {/* Connector Line (Desktop) */}
            <div className="hidden md:block absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
              <div className="w-12 h-12 bg-[#00261C] rounded-full border border-[#EDF5F2]/20 flex items-center justify-center">
                <ArrowRight className="w-5 h-5 text-[#EDF5F2]/40" />
              </div>
            </div>

            {/* Before (Legacy) */}
            <div className="bg-[#00261C] border border-[#EDF5F2]/5 rounded-3xl p-8 md:p-12 relative overflow-hidden opacity-60 hover:opacity-80 transition-opacity duration-500">
              <div className="absolute top-0 right-0 p-6 opacity-10">
                <FileX className="w-32 h-32 text-white" />
              </div>
              
              <h3 className="text-2xl font-bold text-white mb-8 font-display flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-[#EDF5F2]/40" />
                Legacy Process
              </h3>
              
              <ul className="space-y-6 relative z-10">
                {[
                  "Hours per document set validation",
                  "60% first-time rejection rate",
                  "Manual sanctions checks (or none)",
                  "Spreadsheets for shipment tracking",
                  "Guessing HS codes manually"
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-4 text-[#EDF5F2]/40 font-mono text-sm">
                    <span className="text-[#F25E3D] text-lg leading-none">×</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            
            {/* After (TRDR Hub) */}
            <div className="bg-[#00261C] border border-[#B2F273]/30 rounded-3xl p-8 md:p-12 relative overflow-hidden shadow-[0_0_50px_-20px_rgba(178,242,115,0.2)]">
              <div className="absolute inset-0 bg-gradient-to-br from-[#B2F273]/5 to-transparent pointer-events-none" />
              <div className="absolute top-0 right-0 p-6 opacity-10">
                <Zap className="w-32 h-32 text-[#B2F273]" />
              </div>

              <h3 className="text-2xl font-bold text-white mb-8 font-display flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-[#B2F273] animate-pulse" />
                With TRDR Hub
              </h3>
              
              <ul className="space-y-6 relative z-10">
                {[
                  "45-second AI validation",
                  "95%+ first-time acceptance",
                  "Real-time OFAC/EU/UN screening",
                  "Live container tracking dashboard",
                  "AI-powered HS code classification"
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-4 text-white font-medium text-sm">
                    <span className="text-[#B2F273] text-lg leading-none">✓</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
