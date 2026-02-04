import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, ShieldCheck, Clock, ChevronDown, Ship, Plane, FileText, Zap, Globe, Umbrella } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const features = [
  { icon: Zap, title: "Instant Quotes", description: "Get quotes from multiple underwriters in under 60 seconds.", bullets: ["60-second quotes", "Multiple options", "Competitive rates", "Instant comparison"] },
  { icon: Globe, title: "Multiple Underwriters", description: "Access top cargo insurers through one platform.", bullets: ["Lloyd's syndicates", "Major insurers", "Specialist markets", "Best rates"] },
  { icon: Umbrella, title: "All-Risk Coverage", description: "Comprehensive ICC(A) coverage plus additional protections.", bullets: ["ICC(A) all-risks", "War risk", "Strikes risk", "Extended coverage"] },
  { icon: Ship, title: "Any Shipment Type", description: "Cover sea, air, and land shipments. Single or annual policies.", bullets: ["Sea freight", "Air freight", "Land transport", "Multimodal"] },
  { icon: FileText, title: "Certificate Generation", description: "Generate insurance certificates instantly for bank presentation.", bullets: ["Instant certificates", "Bank-ready format", "LC compliant", "Digital delivery"] },
  { icon: ShieldCheck, title: "Claims Support", description: "Expert claims handling when things go wrong.", bullets: ["Claims guidance", "Documentation help", "Surveyor network", "Fast settlement"] },
];

const stats = [
  { value: "60s", label: "Quote Time" },
  { value: "10+", label: "Underwriters" },
  { value: "Instant", label: "Certificates" },
  { value: "24/7", label: "Claims" },
];

const pricing = [
  { tier: "Pay Per Shipment", price: "From 0.1%", description: "Single shipments", features: ["One-off coverage", "Instant certificate", "Basic claims support"] },
  { tier: "Annual Policy", price: "Custom", description: "Regular shippers", features: ["All shipments covered", "Volume discounts", "Priority claims", "Declarations"], popular: true },
  { tier: "Corporate", price: "Custom", description: "Large traders", features: ["Everything in Annual", "Custom terms", "Global program", "Dedicated handler"] },
];

const faqs = [
  { q: "What coverage do you offer?", a: "We offer ICC(A) all-risks coverage as standard, plus war risk, strikes, and extended coverage options. Coverage can be customized to your needs." },
  { q: "How quickly can I get a certificate?", a: "Insurance certificates are generated instantly after purchase. Digital certificates are delivered immediately; paper certificates can be couriered." },
  { q: "What's the claims process?", a: "Report claims through our platform. We guide you through documentation, connect you with surveyors, and track your claim to settlement." },
  { q: "Can I insure goods already in transit?", a: "Coverage typically needs to attach before goods begin transit. For goods already shipped, contact us for backdated coverage options." },
];

const InsuranceQuoteLanding = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main>
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden bg-[#00261C]">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-[#B2F273]/10 rounded-full blur-[120px]" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-[100px]" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#B2F273]/10 border border-[#B2F273]/20 mb-6">
                <Clock className="w-4 h-4 text-[#B2F273]" />
                <span className="text-[#B2F273] text-sm font-medium">Coming Q3 2025</span>
              </div>
              
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight font-display">
                <span className="text-[#B2F273] text-glow-sm">Cargo Insurance</span>{" "}
                in 60 Seconds
              </h1>
              
              <p className="text-lg text-[#EDF5F2]/60 mb-8 leading-relaxed max-w-2xl mx-auto">
                Get instant quotes from multiple underwriters. Cover your shipments 
                without the paperwork. Certificates generated immediately.
              </p>

              <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
                <Link to="/waitlist?tool=insurance">Join Waitlist <ArrowRight className="w-5 h-5 ml-2" /></Link>
              </Button>
            </div>
          </div>
        </section>

        <section className="relative py-12 bg-[#00261C] border-y border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-3xl mx-auto">
              {stats.map((stat, idx) => (
                <div key={idx} className="text-center">
                  <div className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-1 font-display">{stat.value}</div>
                  <div className="text-sm text-[#EDF5F2]/60 font-mono uppercase tracking-wider">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature, idx) => (
                <div key={idx} className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 hover:border-[#B2F273]/30 transition-colors backdrop-blur-sm group">
                  <div className="w-12 h-12 bg-[#B2F273]/10 rounded-lg flex items-center justify-center mb-4 border border-[#B2F273]/20 group-hover:bg-[#B2F273] transition-colors">
                    <feature.icon className="w-6 h-6 text-[#B2F273] group-hover:text-[#00261C] transition-colors" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2 font-display">{feature.title}</h3>
                  <p className="text-[#EDF5F2]/60 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((b, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-[#EDF5F2]/50">
                        <CheckCircle className="w-4 h-4 text-[#B2F273] shrink-0" />{b}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="relative py-20 bg-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {pricing.map((plan, idx) => (
                <div key={idx} className={cn("bg-[#00382E]/50 border rounded-xl p-6 backdrop-blur-sm", plan.popular ? "border-[#B2F273] shadow-[0_0_20px_rgba(178,242,115,0.1)]" : "border-[#EDF5F2]/10")}>
                  {plan.popular && <span className="text-xs text-[#B2F273] font-mono uppercase tracking-wider font-medium">MOST POPULAR</span>}
                  <h3 className="text-lg font-bold text-white mt-2 font-display">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4 font-display">{plan.price}</div>
                  <p className="text-[#EDF5F2]/60 text-sm mb-4">{plan.description}</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-[#EDF5F2]/50">
                        <CheckCircle className="w-4 h-4 text-[#B2F273]" />{f}
                      </li>
                    ))}
                  </ul>
                  <Button className={cn("w-full font-bold border-none", plan.popular ? "bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C]" : "bg-[#EDF5F2]/10 hover:bg-[#EDF5F2]/20 text-white")} asChild>
                    <Link to="/waitlist?tool=insurance">Join Waitlist</Link>
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white text-center mb-12 font-display">FAQ</h2>
              <div className="space-y-4">
                {faqs.map((faq, idx) => (
                  <div key={idx} className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl overflow-hidden backdrop-blur-sm">
                    <button className="w-full px-6 py-4 text-left flex items-center justify-between" onClick={() => setOpenFaq(openFaq === idx ? null : idx)}>
                      <span className="text-white font-medium font-display">{faq.q}</span>
                      <ChevronDown className={cn("w-5 h-5 text-slate-400 transition-transform", openFaq === idx && "rotate-180")} />
                    </button>
                    {openFaq === idx && <div className="px-6 pb-4"><p className="text-[#EDF5F2]/60 text-sm leading-relaxed">{faq.a}</p></div>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="relative py-20 bg-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-6 font-display">Ship with Confidence</h2>
            <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
              <Link to="/waitlist?tool=insurance">Join Waitlist <ArrowRight className="w-5 h-5 ml-2" /></Link>
            </Button>
          </div>
        </section>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default InsuranceQuoteLanding;
