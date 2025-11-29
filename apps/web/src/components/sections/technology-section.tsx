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

export function TechnologySection() {
  return (
    <section className="py-24 md:py-32 bg-white relative">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <p className="text-blue-600 font-semibold mb-4 tracking-wide uppercase text-sm">Technology</p>
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-slate-900 mb-6 leading-tight">
            The most comprehensive
            <br />
            <span className="text-slate-400">trade rules engine ever built</span>
          </h2>
        </div>

        {/* Tech stats grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {techFeatures.map((feature, index) => (
            <div
              key={index}
              className="text-center p-6 group"
            >
              <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-6 mx-auto group-hover:bg-blue-50 transition-colors">
                <feature.icon className="w-8 h-8 text-slate-700 group-hover:text-blue-600 transition-colors" />
              </div>
              <div className="text-4xl md:text-5xl font-bold text-slate-900 mb-2">
                {feature.stat}
              </div>
              <div className="text-lg font-semibold text-slate-700 mb-2">
                {feature.label}
              </div>
              <p className="text-slate-500 text-sm">
                {feature.description}
              </p>
            </div>
          ))}
        </div>

        {/* Technology banner */}
        <div className="mt-20 max-w-5xl mx-auto bg-gradient-to-br from-slate-900 to-slate-800 rounded-3xl p-12 relative overflow-hidden">
          {/* Decorative elements */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl" />
          
          <div className="relative z-10 text-center">
            <h3 className="text-2xl md:text-3xl font-bold text-white mb-4">
              Built on International Standards
            </h3>
            <p className="text-slate-400 mb-8 max-w-2xl mx-auto">
              Our engine incorporates every major ICC publication, SWIFT messaging standard, 
              and regulatory framework used in international trade finance.
            </p>
            
            {/* Standards logos */}
            <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-4 text-slate-500">
              <span className="text-sm font-medium">UCP 600</span>
              <span className="text-slate-700">•</span>
              <span className="text-sm font-medium">ISBP 745</span>
              <span className="text-slate-700">•</span>
              <span className="text-sm font-medium">ISP98</span>
              <span className="text-slate-700">•</span>
              <span className="text-sm font-medium">URDG 758</span>
              <span className="text-slate-700">•</span>
              <span className="text-sm font-medium">URC 522</span>
              <span className="text-slate-700">•</span>
              <span className="text-sm font-medium">URR 725</span>
              <span className="text-slate-700">•</span>
              <span className="text-sm font-medium">eUCP 2.1</span>
              <span className="text-slate-700">•</span>
              <span className="text-sm font-medium">Incoterms 2020</span>
              <span className="text-slate-700">•</span>
              <span className="text-sm font-medium">SWIFT MT700</span>
              <span className="text-slate-700">•</span>
              <span className="text-sm font-medium">ISO 20022</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

