import { FileCode, Database, Brain, Globe2, Shield, Zap } from "lucide-react";

const techFeatures = [
  {
    icon: Brain,
    stat: "3,500+",
    label: "Validation Rules",
    description: "UCP600, ISBP745, ISP98, URDG758, and country-specific regulations",
  },
  {
    icon: Globe2,
    stat: "60+",
    label: "Countries Covered",
    description: "Pre-built rules for major trading nations and regional blocs",
  },
  {
    icon: Database,
    stat: "15",
    label: "ICC Rulebooks",
    description: "Complete coverage of documentary credit standards",
  },
  {
    icon: Zap,
    stat: "45s",
    label: "Average Processing",
    description: "From upload to full compliance report",
  },
  {
    icon: Shield,
    stat: "99%",
    label: "Accuracy Rate",
    description: "Bank-grade precision on discrepancy detection",
  },
  {
    icon: FileCode,
    stat: "ISO20022",
    label: "Ready",
    description: "Native XML parsing for modern LC formats",
  },
];

const standards = [
  "UCP 600", "ISBP 745", "ISP98", "URDG 758", "URC 522", 
  "URR 725", "eUCP 2.1", "Incoterms 2020", "SWIFT MT700", "ISO 20022"
];

export function TechnologySection() {
  return (
    <section className="py-24 md:py-32 bg-[#EDF5F2] relative">
      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(0,38,28,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,38,28,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />

      {/* Top border */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#00261C]/10 to-transparent" />
      
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <p className="text-[#00261C] font-mono text-xs tracking-widest uppercase mb-4">Technology</p>
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-[#00261C] mb-6 leading-tight font-display">
            The most comprehensive
            <br />
            <span className="text-[#00261C]/60">trade rules engine ever built</span>
          </h2>
        </div>

        {/* Tech stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-8 max-w-5xl mx-auto mb-20">
          {techFeatures.map((feature, index) => (
            <div
              key={index}
              className="text-center p-6 group"
            >
              <div className="w-16 h-16 bg-[#00261C]/5 rounded-2xl flex items-center justify-center mb-6 mx-auto group-hover:bg-[#00261C] transition-all duration-300 border border-[#00261C]/5 group-hover:border-[#00261C]">
                <feature.icon className="w-8 h-8 text-[#00261C]/60 group-hover:text-[#B2F273] transition-colors duration-300" />
              </div>
              <div className="text-4xl md:text-5xl font-bold text-[#00261C] mb-2 font-display">
                {feature.stat}
              </div>
              <div className="text-lg font-semibold text-[#00261C]/80 mb-2 font-display">
                {feature.label}
              </div>
              <p className="text-[#00261C]/60 text-sm">
                {feature.description}
              </p>
            </div>
          ))}
        </div>

        {/* Standards banner */}
        <div className="max-w-5xl mx-auto bg-white border border-[#00261C]/10 rounded-3xl p-12 relative overflow-hidden shadow-sm">
          {/* Decorative elements */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-[#B2F273]/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-[#B2F273]/10 rounded-full blur-3xl" />
          
          <div className="relative z-10 text-center">
            <h3 className="text-2xl md:text-3xl font-bold text-[#00261C] mb-4 font-display">
              Built on International Standards
            </h3>
            <p className="text-[#00261C]/70 mb-8 max-w-2xl mx-auto">
              Our engine incorporates every major ICC publication, SWIFT messaging standard, 
              and regulatory framework used in international trade finance.
            </p>
            
            {/* Standards list */}
            <div className="flex flex-wrap items-center justify-center gap-3">
              {standards.map((standard, index) => (
                <span 
                  key={index}
                  className="px-4 py-2 bg-[#EDF5F2] rounded-full text-sm font-medium text-[#00261C]/80 border border-[#00261C]/10 hover:bg-[#00261C] hover:text-[#B2F273] hover:border-[#00261C] transition-all duration-300 cursor-default"
                >
                  {standard}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
