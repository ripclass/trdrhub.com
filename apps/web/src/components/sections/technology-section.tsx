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
    <section className="py-24 md:py-32 bg-slate-900 relative">
      {/* Top border */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-slate-700 to-transparent" />
      
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <p className="text-emerald-400 font-semibold mb-4 tracking-wide uppercase text-sm">Technology</p>
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6 leading-tight">
            The most comprehensive
            <br />
            <span className="text-slate-500">trade rules engine ever built</span>
          </h2>
        </div>

        {/* Tech stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-8 max-w-5xl mx-auto mb-20">
          {techFeatures.map((feature, index) => (
            <div
              key={index}
              className="text-center p-6 group"
            >
              <div className="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center mb-6 mx-auto group-hover:bg-emerald-500/20 transition-colors">
                <feature.icon className="w-8 h-8 text-slate-400 group-hover:text-emerald-400 transition-colors" />
              </div>
              <div className="text-4xl md:text-5xl font-bold text-white mb-2">
                {feature.stat}
              </div>
              <div className="text-lg font-semibold text-slate-300 mb-2">
                {feature.label}
              </div>
              <p className="text-slate-500 text-sm">
                {feature.description}
              </p>
            </div>
          ))}
        </div>

        {/* Standards banner */}
        <div className="max-w-5xl mx-auto bg-slate-800/50 border border-slate-700 rounded-3xl p-12 relative overflow-hidden">
          {/* Decorative elements */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-3xl" />
          
          <div className="relative z-10 text-center">
            <h3 className="text-2xl md:text-3xl font-bold text-white mb-4">
              Built on International Standards
            </h3>
            <p className="text-slate-400 mb-8 max-w-2xl mx-auto">
              Our engine incorporates every major ICC publication, SWIFT messaging standard, 
              and regulatory framework used in international trade finance.
            </p>
            
            {/* Standards list */}
            <div className="flex flex-wrap items-center justify-center gap-3">
              {standards.map((standard, index) => (
                <span 
                  key={index}
                  className="px-4 py-2 bg-slate-700/50 rounded-full text-sm font-medium text-slate-300 border border-slate-600"
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
