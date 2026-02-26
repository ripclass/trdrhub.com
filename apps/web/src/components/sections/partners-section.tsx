export function PartnersSection() {
  const banks = ["SME Exporters", "Importers", "C&F Agents", "Freight Forwarders", "Trade Teams", "Compliance Ops"];
  const standards = [
    "Built on UCP 600",
    "Built on ISBP 745",
    "ISO 20022 Ready",
    "MT700 Aware",
    "Private Beta",
    "Versioned Rules Engine",
  ];

  return (
    <section className="py-16 bg-[#00261C] border-y border-[#EDF5F2]/10 relative overflow-hidden">
      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
      
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center mb-8">
          <p className="text-[#B2F273] text-sm font-medium tracking-wide uppercase">
Built for trade professionals worldwide (private beta)
          </p>
        </div>

        {/* Bank logos */}
        <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-6 mb-8">
          {banks.map((bank) => (
            <div
              key={bank}
              className="text-[#EDF5F2]/60 font-bold text-lg tracking-tight hover:text-[#B2F273] transition-colors cursor-default"
            >
              {bank}
            </div>
          ))}
        </div>

        {/* Standards ticker */}
        <div className="overflow-hidden">
          <div className="flex animate-scroll gap-x-8">
            {[...standards, ...standards].map((item, index) => (
              <span
                key={index}
                className="text-[#EDF5F2]/40 text-sm font-medium whitespace-nowrap flex items-center gap-2"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-[#B2F273]/30" />
                {item}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
