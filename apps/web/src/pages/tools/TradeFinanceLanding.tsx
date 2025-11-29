import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, CreditCard, Clock, DollarSign, ChevronDown, Building2, FileText, TrendingUp, Percent, Banknote, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const features = [
  { icon: Banknote, title: "LC Discounting", description: "Get paid early on your confirmed LCs. Competitive discount rates.", bullets: ["Confirmed LCs", "Competitive rates", "Fast funding", "No recourse options"] },
  { icon: FileText, title: "Invoice Factoring", description: "Convert receivables to cash. Non-recourse and recourse options.", bullets: ["Trade receivables", "Up to 90% advance", "Non-recourse", "Selective factoring"] },
  { icon: TrendingUp, title: "Supply Chain Finance", description: "Extend payment terms without impacting suppliers. Reverse factoring.", bullets: ["Reverse factoring", "Approved payables", "Extend terms", "Supplier benefit"] },
  { icon: DollarSign, title: "Pre-Export Finance", description: "Working capital against confirmed export orders.", bullets: ["Confirmed orders", "Up to 80% advance", "Flexible terms", "Multi-currency"] },
  { icon: Building2, title: "Forfaiting", description: "Sell medium-term receivables without recourse.", bullets: ["Deferred payment LCs", "Without recourse", "Fixed rate", "2-7 year terms"] },
  { icon: Percent, title: "Rate Comparison", description: "Compare rates across multiple lenders instantly.", bullets: ["Multiple lenders", "Side-by-side rates", "Fee comparison", "Best deal finder"] },
];

const stats = [
  { value: "20+", label: "Lenders" },
  { value: "$100K+", label: "Min Transaction" },
  { value: "48hrs", label: "Avg Funding" },
  { value: "Competitive", label: "Rates" },
];

const pricing = [
  { tier: "Basic", price: "Free", description: "Rate quotes", features: ["Rate comparison", "3 lenders", "Email quotes"] },
  { tier: "Professional", price: "$99/mo", description: "Full platform", features: ["All lenders", "Application tracking", "Document upload", "Support"], popular: true },
  { tier: "Enterprise", price: "Custom", description: "For corporates", features: ["Everything in Pro", "Dedicated manager", "Custom limits", "API access"] },
];

const faqs = [
  { q: "What types of trade finance do you offer?", a: "We connect you with lenders for LC discounting, invoice factoring, supply chain finance, pre-export finance, and forfaiting." },
  { q: "What's the minimum transaction size?", a: "Most lenders require minimum $100K transactions. Some products available from $25K for established relationships." },
  { q: "How quickly can I get funded?", a: "LC discounting can fund in 24-48 hours. Invoice factoring typically 3-5 days for first transaction, then 24-48 hours." },
  { q: "Do you provide the financing?", a: "No, we're a marketplace connecting you with lenders. We don't hold risk or provide capital directly." },
];

const TradeFinanceLanding = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      <main>
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-green-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 mb-6">
                <Clock className="w-4 h-4 text-amber-400" />
                <span className="text-amber-400 text-sm font-medium">Coming Q3 2025</span>
              </div>
              
              <h1 className="text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                Access{" "}
                <span className="bg-gradient-to-r from-emerald-400 to-green-400 bg-clip-text text-transparent">Trade Finance</span>{" "}
                Solutions
              </h1>
              
              <p className="text-lg text-slate-400 mb-8 leading-relaxed max-w-2xl mx-auto">
                Connect with lenders for LC discounting, invoice factoring, supply chain finance, 
                and forfaiting. Compare rates and fund faster.
              </p>

              <Button size="lg" className="bg-emerald-500 hover:bg-emerald-600 text-white font-semibold" asChild>
                <Link to="/waitlist?tool=finance">Join Waitlist <ArrowRight className="w-5 h-5 ml-2" /></Link>
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
                <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 hover:border-emerald-500/30 transition-colors">
                  <div className="w-12 h-12 bg-emerald-500/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-emerald-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((b, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-500">
                        <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />{b}
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
                <div key={idx} className={cn("bg-slate-800/50 border rounded-xl p-6", plan.popular ? "border-emerald-500/50 bg-emerald-500/5" : "border-slate-700")}>
                  {plan.popular && <span className="text-xs text-emerald-400 font-medium">MOST POPULAR</span>}
                  <h3 className="text-lg font-semibold text-white mt-2">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4">{plan.price}</div>
                  <p className="text-slate-400 text-sm mb-4">{plan.description}</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-400">
                        <CheckCircle className="w-4 h-4 text-emerald-500" />{f}
                      </li>
                    ))}
                  </ul>
                  <Button className={cn("w-full", plan.popular ? "bg-emerald-500 hover:bg-emerald-600" : "bg-slate-700 hover:bg-slate-600")} asChild>
                    <Link to="/waitlist?tool=finance">Join Waitlist</Link>
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
            <h2 className="text-3xl font-bold text-white mb-6">Fund Your Trade Faster</h2>
            <Button size="lg" className="bg-emerald-500 hover:bg-emerald-600 text-white font-semibold" asChild>
              <Link to="/waitlist?tool=finance">Join Waitlist <ArrowRight className="w-5 h-5 ml-2" /></Link>
            </Button>
          </div>
        </section>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default TradeFinanceLanding;

