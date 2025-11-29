import { Check, Zap, Shield, Globe, Bot, FileCheck } from "lucide-react";

const solutions = [
  {
    icon: Bot,
    title: "AI-Powered Validation",
    description: "Our engine checks documents against 3,500+ rules from UCP600, ISBP745, ISP98, and 60+ country regulations. Instantly.",
  },
  {
    icon: Shield,
    title: "Bank-Grade Accuracy",
    description: "99% accuracy rate. We catch discrepancies that humans miss, every time, before banks do.",
  },
  {
    icon: Zap,
    title: "45-Second Processing",
    description: "Upload your documents. Get a full compliance report with actionable fixes in under a minute.",
  },
  {
    icon: Globe,
    title: "Global Coverage",
    description: "Built-in rules for Singapore, UAE, Bangladesh, India, EU, US, and 54 more jurisdictions.",
  },
  {
    icon: FileCheck,
    title: "Complete Document Suite",
    description: "LC, B/L, Invoice, Insurance, CoO, Packing List - we validate them all, cross-checked against each other.",
  },
  {
    icon: Check,
    title: "Actionable Suggestions",
    description: "Don't just see problems - get exact fixes with UCP600 references and SWIFT amendment drafts.",
  },
];

export function SolutionSection() {
  return (
    <section className="py-24 md:py-32 bg-slate-950 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-blue-500/50 to-transparent" />
      <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent" />
      <div className="absolute top-1/2 left-0 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
      <div className="absolute top-1/2 right-0 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section header */}
        <div className="text-center mb-16">
          <p className="text-emerald-400 font-semibold mb-4 tracking-wide uppercase text-sm">Solution</p>
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6 leading-tight">
            Our answer: AI that thinks
            <br />
            <span className="bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">like a trade finance expert</span>
          </h2>
          <p className="text-xl text-slate-400 max-w-3xl mx-auto">
            We're building the document examiner of the 21st century. It reads documents, understands context, and catches discrepancies with superhuman precision.
          </p>
        </div>

        {/* Solution grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto mb-20">
          {solutions.map((solution, index) => (
            <div
              key={index}
              className="group bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-2xl p-8 hover:border-blue-500/50 transition-all duration-300"
            >
              <div className="w-14 h-14 bg-gradient-to-br from-blue-500/20 to-emerald-500/20 rounded-xl flex items-center justify-center mb-6 group-hover:from-blue-500/30 group-hover:to-emerald-500/30 transition-colors">
                <solution.icon className="w-7 h-7 text-blue-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">
                {solution.title}
              </h3>
              <p className="text-slate-400 leading-relaxed">
                {solution.description}
              </p>
            </div>
          ))}
        </div>

        {/* Before/After comparison */}
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Before */}
            <div className="bg-red-950/30 border border-red-900/50 rounded-2xl p-8">
              <div className="text-red-400 font-semibold mb-4 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-red-400" />
                Without TRDR Hub
              </div>
              <ul className="space-y-4">
                <li className="flex items-start gap-3 text-slate-400">
                  <span className="text-red-400 mt-1">✗</span>
                  <span>2-4 hours per LC validation</span>
                </li>
                <li className="flex items-start gap-3 text-slate-400">
                  <span className="text-red-400 mt-1">✗</span>
                  <span>60% first-time rejection rate</span>
                </li>
                <li className="flex items-start gap-3 text-slate-400">
                  <span className="text-red-400 mt-1">✗</span>
                  <span>$75-150 per discrepancy fee</span>
                </li>
                <li className="flex items-start gap-3 text-slate-400">
                  <span className="text-red-400 mt-1">✗</span>
                  <span>Manual rule checking, human error</span>
                </li>
                <li className="flex items-start gap-3 text-slate-400">
                  <span className="text-red-400 mt-1">✗</span>
                  <span>Vague rejection reasons from banks</span>
                </li>
              </ul>
            </div>
            
            {/* After */}
            <div className="bg-emerald-950/30 border border-emerald-900/50 rounded-2xl p-8">
              <div className="text-emerald-400 font-semibold mb-4 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-400" />
                With TRDR Hub
              </div>
              <ul className="space-y-4">
                <li className="flex items-start gap-3 text-slate-300">
                  <span className="text-emerald-400 mt-1">✓</span>
                  <span>45 seconds per LC validation</span>
                </li>
                <li className="flex items-start gap-3 text-slate-300">
                  <span className="text-emerald-400 mt-1">✓</span>
                  <span>95%+ first-time acceptance rate</span>
                </li>
                <li className="flex items-start gap-3 text-slate-300">
                  <span className="text-emerald-400 mt-1">✓</span>
                  <span>Near-zero discrepancy fees</span>
                </li>
                <li className="flex items-start gap-3 text-slate-300">
                  <span className="text-emerald-400 mt-1">✓</span>
                  <span>AI validates against 3,500+ rules</span>
                </li>
                <li className="flex items-start gap-3 text-slate-300">
                  <span className="text-emerald-400 mt-1">✓</span>
                  <span>Clear fixes with UCP600 citations</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

