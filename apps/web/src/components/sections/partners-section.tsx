export function PartnersSection() {
  const banks = ["HSBC", "DBS", "Standard Chartered", "Citi", "ICBC", "Deutsche Bank"];
  const standards = [
    "ICC Banking Commission",
    "UCP 600 Certified",
    "ISBP 745 Compliant",
    "ISP98 Ready",
    "SWIFT Partner",
    "ISO 20022 Enabled",
  ];

  return (
    <section className="py-16 bg-[#00261C] border-y border-[#EDF5F2]/10">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <p className="text-[#EDF5F2]/40 text-sm font-medium tracking-wide uppercase">
            Trusted by trade professionals worldwide
          </p>
        </div>

        {/* Bank logos */}
        <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-6 mb-8">
          {banks.map((bank) => (
            <div
              key={bank}
              className="text-[#C2B894] font-bold text-lg tracking-tight hover:text-white transition-colors cursor-default"
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
                className="text-[#EDF5F2]/60 text-sm font-medium whitespace-nowrap flex items-center gap-2"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-[#B2F273]/50" />
                {item}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
