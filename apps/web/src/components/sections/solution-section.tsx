import { Check, Zap, Shield, Globe, Bot, Workflow } from "lucide-react";

const solutions = [
  {
    icon: Bot,
    name: "AI-Powered",
    description: "Machine learning validates documents, classifies goods, screens parties, and catches errors humans miss.",
  },
  {
    icon: Workflow,
    name: "All-in-One Platform",
    description: "15 tools for the entire trade lifecycle - from LC application to customs clearance to payment tracking.",
  },
  {
    icon: Zap,
    name: "Instant Results",
    description: "What took hours now takes seconds. Validate documents in 45s. Screen parties in 2s. Generate docs in minutes.",
  },
  {
    icon: Globe,
    name: "Global Coverage",
    description: "Built-in rules for 60+ countries, all ICC publications, OFAC/EU/UN sanctions, and major trade agreements.",
  },
  {
    icon: Shield,
    name: "Compliance Built-In",
    description: "UCP600, ISBP745, Incoterms 2020, HS classification, sanctions screening - all automated, all up-to-date.",
  },
  {
    icon: Check,
    name: "Actionable Intelligence",
    description: "Don't just see problems - get specific fixes, alternative routes, risk scores, and cost comparisons.",
  },
];

export function SolutionSection() {
  return (
    <section className="py-16 sm:py-24 md:py-32 bg-slate-950 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-blue-500/50 to-transparent" />
      <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent" />
      <div className="absolute top-1/2 left-0 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
      <div className="absolute top-1/2 right-0 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section header */}
        <div className="text-center mb-10 sm:mb-16">
          <p className="text-emerald-400 font-semibold mb-3 sm:mb-4 tracking-wide uppercase text-xs sm:text-sm">Solution</p>
          <h2 className="text-2xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-4 sm:mb-6 leading-tight px-2">
            One platform for
            <br />
            <span className="bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">everything trade</span>
          </h2>
          <p className="text-base sm:text-xl text-slate-400 max-w-3xl mx-auto px-4">
            We're building the operating system for international trade. AI-powered tools that automate the boring, catch the risky, and accelerate the slow.
          </p>
        </div>

        {/* Solution grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 max-w-6xl mx-auto mb-12 sm:mb-20">
          {solutions.map((solution, index) => (
            <div
              key={index}
              className="group bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-2xl p-5 sm:p-8 hover:border-blue-500/50 transition-all duration-300"
            >
              <div className="w-12 sm:w-14 h-12 sm:h-14 bg-gradient-to-br from-blue-500/20 to-emerald-500/20 rounded-xl flex items-center justify-center mb-4 sm:mb-6 group-hover:from-blue-500/30 group-hover:to-emerald-500/30 transition-colors">
                <solution.icon className="w-6 sm:w-7 h-6 sm:h-7 text-blue-400" />
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-white mb-2 sm:mb-3">
                {solution.name}
              </h3>
              <p className="text-sm sm:text-base text-slate-400 leading-relaxed">
                {solution.description}
              </p>
            </div>
          ))}
        </div>

        {/* Before/After comparison */}
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-8">
            {/* Before */}
            <div className="bg-red-950/30 border border-red-900/50 rounded-2xl p-5 sm:p-8">
              <div className="text-red-400 font-semibold mb-3 sm:mb-4 flex items-center gap-2 text-sm sm:text-base">
                <div className="w-2 h-2 rounded-full bg-red-400" />
                Without TRDR Hub
              </div>
              <ul className="space-y-3 sm:space-y-4">
                <li className="flex items-start gap-3 text-sm sm:text-base text-slate-400">
                  <span className="text-red-400 mt-0.5">✗</span>
                  <span>Hours per document set validation</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-slate-400">
                  <span className="text-red-400 mt-0.5">✗</span>
                  <span>60% first-time rejection rate</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-slate-400">
                  <span className="text-red-400 mt-0.5">✗</span>
                  <span>Manual sanctions checks (or none)</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-slate-400">
                  <span className="text-red-400 mt-0.5">✗</span>
                  <span>Spreadsheets for shipment tracking</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-slate-400">
                  <span className="text-red-400 mt-0.5">✗</span>
                  <span>Guessing HS codes, hoping they're right</span>
                </li>
              </ul>
            </div>
            
            {/* After */}
            <div className="bg-emerald-950/30 border border-emerald-900/50 rounded-2xl p-5 sm:p-8">
              <div className="text-emerald-400 font-semibold mb-3 sm:mb-4 flex items-center gap-2 text-sm sm:text-base">
                <div className="w-2 h-2 rounded-full bg-emerald-400" />
                With TRDR Hub
              </div>
              <ul className="space-y-3 sm:space-y-4">
                <li className="flex items-start gap-3 text-sm sm:text-base text-slate-300">
                  <span className="text-emerald-400 mt-0.5">✓</span>
                  <span>45-second AI validation</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-slate-300">
                  <span className="text-emerald-400 mt-0.5">✓</span>
                  <span>95%+ first-time acceptance</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-slate-300">
                  <span className="text-emerald-400 mt-0.5">✓</span>
                  <span>Real-time OFAC/EU/UN screening</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-slate-300">
                  <span className="text-emerald-400 mt-0.5">✓</span>
                  <span>Live container tracking dashboard</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-slate-300">
                  <span className="text-emerald-400 mt-0.5">✓</span>
                  <span>AI-powered HS code classification</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
