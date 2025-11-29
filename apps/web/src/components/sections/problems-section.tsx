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
    <section id="problems" className="py-24 md:py-32 bg-white">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <p className="text-blue-600 font-semibold mb-4 tracking-wide uppercase text-sm">Problem</p>
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-slate-900 mb-6 leading-tight">
            International trade is still
            <br />
            <span className="text-slate-400">stuck in the 1990s...</span>
          </h2>
          <p className="text-xl text-slate-600 max-w-2xl mx-auto">
            $32 trillion in global trade, powered by fax machines, PDFs, and spreadsheets.
          </p>
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
