export function PartnersSection() {
  return (
    <section className="py-16 bg-slate-100">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <p className="text-slate-500 text-sm font-medium tracking-wide uppercase">
            Trusted by trade professionals worldwide
          </p>
        </div>

        {/* Partner logos - using text placeholders since we don't have actual logos */}
        <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-8">
          {[
            "HSBC",
            "DBS",
            "Standard Chartered",
            "Citi",
            "ICBC",
            "Deutsche Bank",
          ].map((partner) => (
            <div
              key={partner}
              className="text-slate-400 font-bold text-xl tracking-tight opacity-50 hover:opacity-100 transition-opacity"
            >
              {partner}
            </div>
          ))}
        </div>

        {/* Infinite scroll effect - duplicate for animation */}
        <div className="mt-8 overflow-hidden">
          <div className="flex animate-scroll gap-x-12">
            {[
              "ICC Banking Commission",
              "UCP 600 Certified",
              "ISBP 745 Compliant",
              "ISP98 Ready",
              "SWIFT Partner",
              "ISO 20022 Enabled",
              "ICC Banking Commission",
              "UCP 600 Certified",
              "ISBP 745 Compliant",
              "ISP98 Ready",
              "SWIFT Partner",
              "ISO 20022 Enabled",
            ].map((item, index) => (
              <span
                key={index}
                className="text-slate-400 text-sm font-medium whitespace-nowrap"
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

