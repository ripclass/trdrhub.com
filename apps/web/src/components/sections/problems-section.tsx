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
    <section id="problems" className="py-24 sm:py-32 bg-[#00261C] relative overflow-hidden">
      {/* Background Noise/Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.02)_1px,transparent_1px)] bg-[size:40px_40px] opacity-50" />
      <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-b from-[#00261C] to-transparent z-10" />
      <div className="absolute bottom-0 left-0 w-full h-32 bg-gradient-to-t from-[#00261C] to-transparent z-10" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-20">
        {/* Section header */}
        <div className="text-center mb-20">
          <div className="inline-flex items-center gap-2 mb-6">
            <div className="w-2 h-2 bg-[#F25E3D] rounded-full animate-pulse" />
            <p className="text-[#F25E3D] font-mono text-xs tracking-widest uppercase">System Critical</p>
          </div>
          
          <h2 className="text-4xl md:text-6xl lg:text-7xl font-bold text-white mb-8 leading-[0.95] font-display tracking-tight">
            The Paperwork
            <br />
            <span className="text-[#F25E3D] text-glow-sm">Bottleneck.</span>
          </h2>
          <p className="text-lg md:text-xl text-[#EDF5F2]/60 max-w-2xl mx-auto font-light leading-relaxed">
            <span className="text-white font-medium">$32 trillion</span> in global trade, held back by 1990s infrastructure.
          </p>
        </div>

        {/* Problem cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-1 bg-[#EDF5F2]/5 p-[1px] rounded-3xl overflow-hidden border border-[#EDF5F2]/10 shadow-2xl">
          {problems.map((problem, index) => (
            <div
              key={index}
              className="group relative bg-[#00261C] p-8 md:p-10 hover:bg-[#00382E] transition-all duration-500 ease-out"
            >
              {/* Hover Glow Effect */}
              <div className="absolute top-0 right-0 w-32 h-32 bg-[#B2F273]/5 rounded-bl-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
              
              {/* Header: Icon & Label */}
              <div className="flex items-start justify-between mb-8">
                <div className="w-12 h-12 rounded-lg bg-[#F25E3D]/10 flex items-center justify-center border border-[#F25E3D]/20 group-hover:bg-[#B2F273]/10 group-hover:border-[#B2F273]/30 transition-all duration-300">
                  <problem.icon className="w-6 h-6 text-[#F25E3D] group-hover:text-[#B2F273] transition-colors duration-300" />
                </div>
                <span className="text-[#EDF5F2]/20 font-mono text-xs tracking-widest group-hover:text-[#B2F273]/50 transition-colors duration-300">
                  {problem.label}
                </span>
              </div>

              {/* Content */}
              <h3 className="text-xl md:text-2xl font-bold text-white mb-4 font-display group-hover:text-[#B2F273] transition-colors duration-300">
                {problem.title}
              </h3>
              <p className="text-[#EDF5F2]/60 leading-relaxed text-sm md:text-base group-hover:text-[#EDF5F2]/90 transition-colors duration-300">
                {problem.description}
              </p>

              {/* Bottom Decorative Line */}
              <div className="absolute bottom-0 left-0 w-0 h-[2px] bg-[#B2F273] group-hover:w-full transition-all duration-500 ease-in-out opacity-50" />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
