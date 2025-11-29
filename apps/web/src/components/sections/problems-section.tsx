import { AlertTriangle, Clock, DollarSign, FileX, RefreshCcw, Ban } from "lucide-react";

const problems = [
  {
    icon: DollarSign,
    title: "Not cheap",
    description: "Every LC discrepancy costs $75-150 in bank fees. With 60% of first submissions rejected, you're bleeding money on every shipment.",
  },
  {
    icon: Clock,
    title: "Not fast",
    description: "Manual document checking takes 2-4 hours per LC. Your trade finance team is drowning in paperwork instead of closing deals.",
  },
  {
    icon: AlertTriangle,
    title: "Not reliable",
    description: "Human checkers miss 20% of discrepancies. Banks catch them. You pay. Again and again.",
  },
  {
    icon: FileX,
    title: "Not standardized",
    description: "Every bank interprets UCP600 differently. What HSBC accepts, Deutsche Bank rejects. No consistency, only chaos.",
  },
  {
    icon: RefreshCcw,
    title: "Not scalable",
    description: "Growing your trade volume means hiring more document checkers. Costs scale linearly with business growth.",
  },
  {
    icon: Ban,
    title: "Not transparent",
    description: "When documents get rejected, you rarely know exactly why until the discrepancy notice arrives. By then, it's too late.",
  },
];

export function ProblemsSection() {
  return (
    <section id="problems" className="py-24 md:py-32 bg-white">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <p className="text-blue-600 font-semibold mb-4 tracking-wide uppercase text-sm">Problem</p>
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-slate-900 mb-6 leading-tight">
            LC processing is broken,
            <br />
            <span className="text-slate-400">and everyone knows it...</span>
          </h2>
        </div>

        {/* Problem cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {problems.map((problem, index) => (
            <div
              key={index}
              className="group relative bg-slate-50 rounded-2xl p-8 hover:bg-slate-100 transition-all duration-300 border border-slate-100 hover:border-slate-200 hover:shadow-lg"
            >
              <div className="w-14 h-14 bg-red-100 rounded-xl flex items-center justify-center mb-6 group-hover:bg-red-200 transition-colors">
                <problem.icon className="w-7 h-7 text-red-600" />
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">
                ...{problem.title}
              </h3>
              <p className="text-slate-600 leading-relaxed">
                {problem.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

