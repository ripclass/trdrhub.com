import { AlertTriangle, Clock, DollarSign, FileX, Layers, Ban } from "lucide-react";

const problems = [
  {
    icon: DollarSign,
    title: "Not cheap",
    description: "Discrepancy fees, compliance penalties, customs delays, rework costs. Every mistake bleeds money from your margins.",
  },
  {
    icon: Clock,
    title: "Not fast",
    description: "Hours spent validating documents, screening parties, classifying goods, tracking shipments. Your team drowns in manual work.",
  },
  {
    icon: AlertTriangle,
    title: "Not reliable",
    description: "Human error in document prep causes 60% of LC rejections. One missed field, one wrong code - deal delayed.",
  },
  {
    icon: Layers,
    title: "Not connected",
    description: "Data lives in 10 different systems. Excel for docs, email for tracking, PDFs for compliance. Nothing talks to anything.",
  },
  {
    icon: FileX,
    title: "Not standardized",
    description: "Every bank, every country, every shipment has different rules. UCP600, Incoterms, HS codes, sanctions lists - constant complexity.",
  },
  {
    icon: Ban,
    title: "Not transparent",
    description: "Where's my shipment? Will this pass compliance? What fees will I pay? You're always guessing until it's too late.",
  },
];

export function ProblemsSection() {
  return (
    <section id="problems" className="py-16 sm:py-24 md:py-32 bg-[#00261C] relative">
      {/* Top border */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#EDF5F2]/10 to-transparent" />
      
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-10 sm:mb-16">
          <p className="text-[#F25E3D] font-semibold mb-3 sm:mb-4 tracking-wide uppercase text-xs sm:text-sm">Problem</p>
          <h2 className="text-2xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-4 sm:mb-6 leading-tight px-2 font-display">
            International trade is still
            <br />
            <span className="text-[#C2B894]">stuck in the 1990s...</span>
          </h2>
          <p className="text-base sm:text-xl text-[#EDF5F2]/80 max-w-2xl mx-auto px-4">
            $32 trillion in global trade, powered by fax machines, PDFs, and spreadsheets.
          </p>
        </div>

        {/* Problem cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 max-w-6xl mx-auto">
          {problems.map((problem, index) => (
            <div
              key={index}
              className="group relative bg-[#00382E]/50 rounded-2xl p-5 sm:p-8 hover:bg-[#00382E] transition-all duration-300 border border-[#EDF5F2]/10 hover:border-[#F25E3D]/30"
            >
              <div className="w-12 sm:w-14 h-12 sm:h-14 bg-[#F25E3D]/10 rounded-xl flex items-center justify-center mb-4 sm:mb-6 group-hover:bg-[#F25E3D]/20 transition-colors">
                <problem.icon className="w-6 sm:w-7 h-6 sm:h-7 text-[#F25E3D]" />
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-white mb-2 sm:mb-3 font-display">
                ...{problem.title}
              </h3>
              <p className="text-sm sm:text-base text-[#EDF5F2]/60 leading-relaxed">
                {problem.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
