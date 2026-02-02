import { AlertTriangle, Clock, DollarSign, FileX, Layers, Ban } from "lucide-react";

const problems = [
  {
    icon: DollarSign,
    label: "01_COST",
    title: "Cost Hemorrhage",
    description: "Discrepancy fees, compliance penalties, customs delays. Every mistake bleeds money from your margins.",
  },
  {
    icon: Clock,
    label: "02_SPEED",
    title: "Velocity Loss",
    description: "Hours spent validating documents, screening parties, classifying goods. Your team drowns in manual work.",
  },
  {
    icon: AlertTriangle,
    label: "03_RISK",
    title: "Compliance Failure",
    description: "Human error causes 60% of LC rejections. One missed field, one wrong code - deal delayed.",
  },
  {
    icon: Layers,
    label: "04_DATA",
    title: "Siloed Intelligence",
    description: "Data lives in 10 different systems. Excel, email, PDFs. Nothing talks to anything.",
  },
  {
    icon: FileX,
    label: "05_STANDARDS",
    title: "Rule Complexity",
    description: "Every bank, country, and shipment has different rules. UCP600, Incoterms, HS codes - constant chaos.",
  },
  {
    icon: Ban,
    label: "06_VISIBILITY",
    title: "Black Box Operations",
    description: "Where's my shipment? Will this pass compliance? You're always guessing until it's too late.",
  },
];

export function ProblemsSection() {
  return (
    <section id="problems" className="py-24 sm:py-32 bg-[#EDF5F2] relative overflow-hidden">
      {/* Background Noise/Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(0,38,28,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,38,28,0.03)_1px,transparent_1px)] bg-[size:40px_40px] opacity-100" />
      <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-b from-[#EDF5F2] to-transparent z-10" />
      <div className="absolute bottom-0 left-0 w-full h-32 bg-gradient-to-t from-[#EDF5F2] to-transparent z-10" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-20">
        {/* Section header */}
        <div className="text-center mb-20">
          <div className="inline-flex items-center gap-2 mb-6">
            <div className="w-2 h-2 bg-[#00261C] rounded-full animate-pulse" />
            <p className="text-[#00261C] font-mono text-xs tracking-widest uppercase">System Critical</p>
          </div>
          
          <h2 className="text-4xl md:text-6xl lg:text-7xl font-bold text-[#00261C] mb-8 leading-[0.95] font-display tracking-tight">
            The Paperwork
            <br />
            <span className="text-[#00261C]">Bottleneck.</span>
          </h2>
          <p className="text-lg md:text-xl text-[#00261C]/80 max-w-2xl mx-auto font-light leading-relaxed">
            <span className="text-[#00261C] font-semibold">$32 trillion</span> in global trade, held back by 1990s infrastructure.
          </p>
        </div>

        {/* Problem cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-7xl mx-auto mb-24">
          {problems.map((problem, index) => (
            <div
              key={index}
              className="group bg-[#EDF5F2] border border-[#00261C]/10 rounded-2xl p-8 hover:border-[#B2F273]/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_10px_40px_-10px_rgba(0,38,28,0.1)] relative overflow-hidden"
            >
              {/* Hover Glow Effect */}
              <div className="absolute top-0 right-0 w-32 h-32 bg-[#B2F273]/10 rounded-bl-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
              
              {/* Header: Icon & Label */}
              <div className="flex items-start justify-between mb-6">
                <div className="w-14 h-14 bg-[#00261C]/5 rounded-xl flex items-center justify-center border border-[#00261C]/10 group-hover:bg-[#00261C] group-hover:border-[#00261C] transition-all duration-300">
                  <problem.icon className="w-7 h-7 text-[#00261C] group-hover:text-[#B2F273] transition-colors duration-300" />
                </div>
                <span className="text-[#00261C]/40 font-mono text-xs tracking-widest group-hover:text-[#00261C] transition-colors duration-300">
                  {problem.label}
                </span>
              </div>

              {/* Content */}
              <h3 className="text-xl md:text-2xl font-bold text-[#00261C] mb-3 font-display transition-colors duration-300">
                {problem.title}
              </h3>
              <p className="text-[#00261C]/70 leading-relaxed text-sm md:text-base group-hover:text-[#00261C] transition-colors duration-300">
                {problem.description}
              </p>

              {/* Bottom Decorative Line */}
              <div className="absolute bottom-0 left-0 w-0 h-[3px] bg-[#00261C] group-hover:w-full transition-all duration-500 ease-in-out" />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
