import { Lock, Cpu, TrendingUp } from "lucide-react";

const differentiators = [
  {
    icon: Lock,
    title: "Proprietary Rule Engine",
    description: "Our rule engine is the result of 2+ years of encoding ICC publications, bank interpretations, and country regulations. No one else has this depth.",
  },
  {
    icon: Cpu,
    title: "AI That Understands Context",
    description: "We don't just match strings. Our AI understands that 'Chattogram' and 'Chittagong' are the same port, and 'USD 100,000' and '100,000.00 US$' are the same amount.",
  },
  {
    icon: TrendingUp,
    title: "Designed for Scale",
    description: "Process 10 LCs or 10,000. Our infrastructure handles volume without compromising speed or accuracy. Pay only for what you use.",
  },
];

export function WhyTRDRSection() {
  return (
    <section className="py-24 md:py-32 bg-[#00261C] relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section header */}
        <div className="text-center mb-16">
          <p className="text-[#B2F273] font-semibold mb-4 tracking-wide uppercase text-sm">Why Us</p>
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6 leading-tight font-display">
            Transforming a trillion-dollar
            <br />
            <span className="text-[#EDF5F2]/60">paper-pushing industry</span>
          </h2>
        </div>

        {/* Differentiators */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {differentiators.map((item, index) => (
            <div
              key={index}
              className="text-center p-8"
            >
              <div className="w-16 h-16 bg-gradient-to-br from-[#B2F273]/20 to-[#00382E]/20 rounded-2xl flex items-center justify-center mb-6 mx-auto">
                <item.icon className="w-8 h-8 text-[#B2F273]" />
              </div>
              <h3 className="text-xl font-bold text-white mb-4 font-display">
                {item.title}
              </h3>
              <p className="text-[#EDF5F2]/60 leading-relaxed">
                {item.description}
              </p>
            </div>
          ))}
        </div>

        {/* Quote/Testimonial */}
        <div className="mt-20 max-w-3xl mx-auto text-center">
          <blockquote className="text-2xl md:text-3xl text-white font-medium leading-relaxed mb-6 font-display">
            "We validated 247 LCs last quarter with TRDR Hub. Zero discrepancy fees. 
            <span className="text-[#B2F273]"> That's $18,000 saved.</span>"
          </blockquote>
          <div className="text-[#EDF5F2]/60">
            <span className="font-semibold text-white">Sarah Chen</span>
            <span className="mx-2">•</span>
            <span>Trade Finance Manager, Singapore</span>
          </div>
        </div>
      </div>
    </section>
  );
}
