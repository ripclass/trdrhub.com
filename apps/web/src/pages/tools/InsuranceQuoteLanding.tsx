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
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      <main>
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 mb-6">
                <Clock className="w-4 h-4 text-amber-400" />
                <span className="text-amber-400 text-sm font-medium">Coming Q3 2025</span>
              </div>
              
              <h1 className="text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                <span className="bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text text-transparent">Cargo Insurance</span>{" "}
                in 60 Seconds
              </h1>
              
              <p className="text-lg text-slate-400 mb-8 leading-relaxed max-w-2xl mx-auto">
                Get instant quotes from multiple underwriters. Cover your shipments 
                without the paperwork. Certificates generated immediately.
              </p>

              <Button size="lg" className="bg-teal-500 hover:bg-teal-600 text-white font-semibold" asChild>
                <Link to="/waitlist?tool=insurance">Join Waitlist <ArrowRight className="w-5 h-5 ml-2" /></Link>
              </Button>
            </div>
          </div>
        </section>

        <section className="py-12 bg-slate-900 border-y border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-3xl mx-auto">
              {stats.map((stat, idx) => (
                <div key={idx} className="text-center">
                  <div className="text-3xl md:text-4xl font-bold text-white mb-1">{stat.value}</div>
                  <div className="text-sm text-slate-500">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature, idx) => (
                <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 hover:border-teal-500/30 transition-colors">
                  <div className="w-12 h-12 bg-teal-500/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-teal-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((b, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-500">
                        <CheckCircle className="w-4 h-4 text-teal-500 shrink-0" />{b}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {pricing.map((plan, idx) => (
                <div key={idx} className={cn("bg-slate-800/50 border rounded-xl p-6", plan.popular ? "border-teal-500/50 bg-teal-500/5" : "border-slate-700")}>
                  {plan.popular && <span className="text-xs text-teal-400 font-medium">MOST POPULAR</span>}
                  <h3 className="text-lg font-semibold text-white mt-2">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4">{plan.price}</div>
                  <p className="text-slate-400 text-sm mb-4">{plan.description}</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-400">
                        <CheckCircle className="w-4 h-4 text-teal-500" />{f}
                      </li>
                    ))}
                  </ul>
                  <Button className={cn("w-full", plan.popular ? "bg-teal-500 hover:bg-teal-600" : "bg-slate-700 hover:bg-slate-600")} asChild>
                    <Link to="/waitlist?tool=insurance">Join Waitlist</Link>
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
              <h2 className="text-3xl font-bold text-white text-center mb-12">FAQ</h2>
              <div className="space-y-4">
                {faqs.map((faq, idx) => (
                  <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
                    <button className="w-full px-6 py-4 text-left flex items-center justify-between" onClick={() => setOpenFaq(openFaq === idx ? null : idx)}>
                      <span className="text-white font-medium">{faq.q}</span>
                      <ChevronDown className={cn("w-5 h-5 text-slate-400 transition-transform", openFaq === idx && "rotate-180")} />
                    </button>
                    {openFaq === idx && <div className="px-6 pb-4"><p className="text-slate-400 text-sm">{faq.a}</p></div>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl font-bold text-white mb-6">Ship with Confidence</h2>
            <Button size="lg" className="bg-teal-500 hover:bg-teal-600 text-white font-semibold" asChild>
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

