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
    <section className="py-16 sm:py-24 md:py-32 bg-[#00261C] relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#F25E3D]/50 to-transparent" />
      <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/50 to-transparent" />
      <div className="absolute top-1/2 left-0 w-96 h-96 bg-[#F25E3D]/5 rounded-full blur-3xl" />
      <div className="absolute top-1/2 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section header */}
        <div className="text-center mb-10 sm:mb-16">
          <p className="text-[#B2F273] font-semibold mb-3 sm:mb-4 tracking-wide uppercase text-xs sm:text-sm">Solution</p>
          <h2 className="text-2xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-4 sm:mb-6 leading-tight px-2 font-display">
            One platform for
            <br />
            <span className="bg-gradient-to-r from-[#F25E3D] to-[#B2F273] bg-clip-text text-transparent">everything trade</span>
          </h2>
          <p className="text-base sm:text-xl text-[#EDF5F2]/80 max-w-3xl mx-auto px-4">
            We're building the operating system for international trade. AI-powered tools that automate the boring, catch the risky, and accelerate the slow.
          </p>
        </div>

        {/* Solution grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 max-w-6xl mx-auto mb-12 sm:mb-20">
          {solutions.map((solution, index) => (
            <div
              key={index}
              className="group bg-[#00382E]/50 backdrop-blur-sm border border-[#EDF5F2]/10 rounded-2xl p-5 sm:p-8 hover:border-[#F25E3D]/50 transition-all duration-300"
            >
              <div className="w-12 sm:w-14 h-12 sm:h-14 bg-gradient-to-br from-[#F25E3D]/20 to-[#B2F273]/20 rounded-xl flex items-center justify-center mb-4 sm:mb-6 group-hover:from-[#F25E3D]/30 group-hover:to-[#B2F273]/30 transition-colors">
                <solution.icon className="w-6 sm:w-7 h-6 sm:h-7 text-[#F25E3D]" />
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-white mb-2 sm:mb-3 font-display">
                {solution.name}
              </h3>
              <p className="text-sm sm:text-base text-[#EDF5F2]/60 leading-relaxed">
                {solution.description}
              </p>
            </div>
          ))}
        </div>

        {/* Before/After comparison */}
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-8">
            {/* Before */}
            <div className="bg-[#F25E3D]/10 border border-[#F25E3D]/20 rounded-2xl p-5 sm:p-8">
              <div className="text-[#F25E3D] font-semibold mb-3 sm:mb-4 flex items-center gap-2 text-sm sm:text-base">
                <div className="w-2 h-2 rounded-full bg-[#F25E3D]" />
                Without TRDR Hub
              </div>
              <ul className="space-y-3 sm:space-y-4">
                <li className="flex items-start gap-3 text-sm sm:text-base text-[#EDF5F2]/60">
                  <span className="text-[#F25E3D] mt-0.5">✗</span>
                  <span>Hours per document set validation</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-[#EDF5F2]/60">
                  <span className="text-[#F25E3D] mt-0.5">✗</span>
                  <span>60% first-time rejection rate</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-[#EDF5F2]/60">
                  <span className="text-[#F25E3D] mt-0.5">✗</span>
                  <span>Manual sanctions checks (or none)</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-[#EDF5F2]/60">
                  <span className="text-[#F25E3D] mt-0.5">✗</span>
                  <span>Spreadsheets for shipment tracking</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-[#EDF5F2]/60">
                  <span className="text-[#F25E3D] mt-0.5">✗</span>
                  <span>Guessing HS codes, hoping they're right</span>
                </li>
              </ul>
            </div>
            
            {/* After */}
            <div className="bg-[#B2F273]/10 border border-[#B2F273]/20 rounded-2xl p-5 sm:p-8">
              <div className="text-[#B2F273] font-semibold mb-3 sm:mb-4 flex items-center gap-2 text-sm sm:text-base">
                <div className="w-2 h-2 rounded-full bg-[#B2F273]" />
                With TRDR Hub
              </div>
              <ul className="space-y-3 sm:space-y-4">
                <li className="flex items-start gap-3 text-sm sm:text-base text-[#EDF5F2]">
                  <span className="text-[#B2F273] mt-0.5">✓</span>
                  <span>45-second AI validation</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-[#EDF5F2]">
                  <span className="text-[#B2F273] mt-0.5">✓</span>
                  <span>95%+ first-time acceptance</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-[#EDF5F2]">
                  <span className="text-[#B2F273] mt-0.5">✓</span>
                  <span>Real-time OFAC/EU/UN screening</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-[#EDF5F2]">
                  <span className="text-[#B2F273] mt-0.5">✓</span>
                  <span>Live container tracking dashboard</span>
                </li>
                <li className="flex items-start gap-3 text-sm sm:text-base text-[#EDF5F2]">
                  <span className="text-[#B2F273] mt-0.5">✓</span>
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
