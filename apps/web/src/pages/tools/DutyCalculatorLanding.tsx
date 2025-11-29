import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, Calculator, Clock, DollarSign, Globe, ChevronDown, Percent, TrendingDown, Truck, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const features = [
  { icon: Percent, title: "Duty Rates", description: "MFN and preferential rates for any HS code and destination.", bullets: ["MFN rates", "FTA preferential", "Anti-dumping", "Countervailing"] },
  { icon: DollarSign, title: "Tax Calculation", description: "VAT, GST, excise, and other import taxes by country.", bullets: ["VAT/GST rates", "Excise duties", "Import levies", "Processing fees"] },
  { icon: TrendingDown, title: "FTA Savings", description: "Calculate savings from preferential trade agreements.", bullets: ["FTA eligibility", "Savings estimate", "ROO requirements", "Documentation"] },
  { icon: Truck, title: "Shipping Costs", description: "Estimate freight and handling for landed cost.", bullets: ["Sea freight", "Air freight", "Terminal handling", "Insurance"] },
  { icon: Globe, title: "Currency Conversion", description: "Real-time FX rates for accurate cost estimation.", bullets: ["Live FX rates", "Historical rates", "Multi-currency", "Rate alerts"] },
  { icon: FileText, title: "Cost Breakdown", description: "Detailed breakdown of all landed cost components.", bullets: ["PDF export", "Line-by-line costs", "Comparison mode", "Quote ready"] },
];

const stats = [
  { value: "190+", label: "Countries" },
  { value: "Real-Time", label: "FX Rates" },
  { value: "50+", label: "FTAs" },
  { value: "Free", label: "Basic Calc" },
];

const pricing = [
  { tier: "Free", calcs: "10/mo", price: "$0", description: "Basic calculations", features: ["Duty rates", "Single country", "Basic taxes"] },
  { tier: "Pro", calcs: "100/mo", price: "$39/mo", description: "Full landed cost", features: ["All countries", "FTA calculator", "Shipping est.", "PDF export"], popular: true },
  { tier: "Enterprise", calcs: "Unlimited", price: "$99/mo", description: "For importers", features: ["Everything in Pro", "API access", "Bulk calc", "Custom fees"] },
];

const faqs = [
  { q: "How accurate are the duty rates?", a: "Duty rates are sourced from official tariff schedules and updated monthly. MFN rates are typically 99%+ accurate. FTA rates depend on origin verification." },
  { q: "Do you include all taxes?", a: "We include VAT/GST, excise duties, and major import levies. Some countries have additional local taxes that may not be included." },
  { q: "Can I calculate FTA savings?", a: "Yes! Enter origin and destination to see which FTAs apply and the potential duty savings. We'll also show ROO requirements." },
  { q: "Is shipping cost included?", a: "Pro plans include freight estimates based on weight/volume and route. For exact costs, get quotes from forwarders." },
];

const DutyCalculatorLanding = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      <main>
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-green-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 mb-6">
                <Clock className="w-4 h-4 text-amber-400" />
                <span className="text-amber-400 text-sm font-medium">Coming Q2 2025</span>
              </div>
              
              <h1 className="text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                Know Your{" "}
                <span className="bg-gradient-to-r from-green-400 to-emerald-400 bg-clip-text text-transparent">Landed Cost</span>{" "}
                Before You Ship
              </h1>
              
              <p className="text-lg text-slate-400 mb-8 leading-relaxed max-w-2xl mx-auto">
                Calculate duties, taxes, fees, and shipping for any origin-destination pair. 
                Know your total cost before you commit.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Button size="lg" className="bg-green-500 hover:bg-green-600 text-white font-semibold" asChild>
                  <Link to="/waitlist?tool=duty-calc">Join Waitlist <ArrowRight className="w-5 h-5 ml-2" /></Link>
                </Button>
              </div>
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
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">Complete Landed Cost Breakdown</h2>
            </div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature, idx) => (
                <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 hover:border-green-500/30 transition-colors">
                  <div className="w-12 h-12 bg-green-500/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-green-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((b, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-500">
                        <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />{b}
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
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">Simple Pricing</h2>
            </div>
            <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {pricing.map((plan, idx) => (
                <div key={idx} className={cn("bg-slate-800/50 border rounded-xl p-6", plan.popular ? "border-green-500/50 bg-green-500/5" : "border-slate-700")}>
                  {plan.popular && <span className="text-xs text-green-400 font-medium">MOST POPULAR</span>}
                  <h3 className="text-lg font-semibold text-white mt-2">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4">{plan.price}</div>
                  <p className="text-slate-400 text-sm mb-4">{plan.calcs} calculations</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-400">
                        <CheckCircle className="w-4 h-4 text-green-500" />{f}
                      </li>
                    ))}
                  </ul>
                  <Button className={cn("w-full", plan.popular ? "bg-green-500 hover:bg-green-600" : "bg-slate-700 hover:bg-slate-600")} asChild>
                    <Link to="/waitlist?tool=duty-calc">Join Waitlist</Link>
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
              <h2 className="text-3xl md:text-4xl font-bold text-white text-center mb-12">FAQ</h2>
              <div className="space-y-4">
                {faqs.map((faq, idx) => (
                  <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
                    <button className="w-full px-6 py-4 text-left flex items-center justify-between" onClick={() => setOpenFaq(openFaq === idx ? null : idx)}>
                      <span className="text-white font-medium">{faq.q}</span>
                      <ChevronDown className={cn("w-5 h-5 text-slate-400 transition-transform shrink-0 ml-4", openFaq === idx && "rotate-180")} />
                    </button>
                    {openFaq === idx && <div className="px-6 pb-4"><p className="text-slate-400 text-sm leading-relaxed">{faq.a}</p></div>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">Stop Guessing Landed Costs</h2>
              <Button size="lg" className="bg-green-500 hover:bg-green-600 text-white font-semibold" asChild>
                <Link to="/waitlist?tool=duty-calc">Join Waitlist <ArrowRight className="w-5 h-5 ml-2" /></Link>
              </Button>
            </div>
          </div>
        </section>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default DutyCalculatorLanding;

