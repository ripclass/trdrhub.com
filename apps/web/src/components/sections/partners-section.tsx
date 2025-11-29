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
    <section className="py-16 bg-slate-900 border-y border-slate-800">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-8">
          <p className="text-slate-500 text-sm font-medium tracking-wide uppercase">
            Trusted by trade professionals worldwide
          </p>
        </div>

        {/* Bank logos */}
        <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-6 mb-8">
          {banks.map((bank) => (
            <div
              key={bank}
              className="text-slate-600 font-bold text-lg tracking-tight hover:text-slate-400 transition-colors cursor-default"
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
                className="text-slate-600 text-sm font-medium whitespace-nowrap flex items-center gap-2"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/50" />
                {item}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
