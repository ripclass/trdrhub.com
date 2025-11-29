import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, Building2, Clock, DollarSign, ChevronDown, Timer, FileText, TrendingDown, Star, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const features = [
  { icon: DollarSign, title: "LC Fee Comparison", description: "Compare issuance, advising, confirmation fees across banks.", bullets: ["Issuance fees", "Confirmation", "Advising", "Negotiation"] },
  { icon: FileText, title: "Amendment Charges", description: "Know the cost of LC amendments before you request them.", bullets: ["Amendment fees", "Extension costs", "Value changes", "Term changes"] },
  { icon: AlertTriangle, title: "Discrepancy Fees", description: "Compare discrepancy handling fees and practices.", bullets: ["Discrepancy fees", "Waiver costs", "Resubmission", "Rejection costs"] },
  { icon: Star, title: "Bank Ratings", description: "User ratings and reviews from actual trade finance users.", bullets: ["Service quality", "Responsiveness", "Expertise", "Issue resolution"] },
  { icon: Timer, title: "Processing Times", description: "Average turnaround times for LC issuance and amendments.", bullets: ["Issuance time", "Amendment time", "Document check", "Payment release"] },
  { icon: TrendingDown, title: "Negotiation Tips", description: "Leverage points for fee negotiation with your bank.", bullets: ["Volume discounts", "Relationship pricing", "Bundled services", "Competitor offers"] },
];

const stats = [
  { value: "50+", label: "Banks" },
  { value: "25+", label: "Countries" },
  { value: "Real", label: "User Reviews" },
  { value: "Updated", label: "Monthly" },
];

const pricing = [
  { tier: "Free", comparisons: "5/mo", price: "$0", features: ["Basic fees", "Top 10 banks", "Fee overview"] },
  { tier: "Pro", comparisons: "50/mo", price: "$29/mo", features: ["All banks", "Processing times", "User ratings", "Export"], popular: true },
  { tier: "Enterprise", comparisons: "Unlimited", price: "$99/mo", features: ["Everything in Pro", "Custom banks", "API access", "Benchmarking"] },
];

const faqs = [
  { q: "Where do you get the fee data?", a: "We aggregate published tariffs and user-submitted data. Fees shown are indicative - actual fees depend on your relationship and volumes." },
  { q: "How accurate are the comparisons?", a: "Published tariffs are accurate; actual fees often differ due to relationship pricing. Use as a starting point for negotiation." },
  { q: "Can I add my bank?", a: "Yes! Submit your bank's fees and help the community. Enterprise plans include custom bank additions." },
];

const BankFeeComparatorLanding = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      <main>
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-yellow-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 mb-6">
                <Clock className="w-4 h-4 text-amber-400" />
                <span className="text-amber-400 text-sm font-medium">Coming Q3 2025</span>
              </div>
              
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                Stop{" "}
                <span className="bg-gradient-to-r from-yellow-400 to-amber-400 bg-clip-text text-transparent">Overpaying</span>{" "}
                for Trade Finance
              </h1>
              
              <p className="text-lg text-slate-400 mb-8 leading-relaxed max-w-2xl mx-auto">
                Compare LC fees, processing times, and service quality across 50+ banks. 
                Know what you should be paying.
              </p>

              <Button size="lg" className="bg-yellow-500 hover:bg-yellow-600 text-slate-900 font-semibold" asChild>
                <Link to="/waitlist?tool=bank-fees">Join Waitlist <ArrowRight className="w-5 h-5 ml-2" /></Link>
              </Button>
            </div>
          </div>
        </section>

        <section className="py-12 bg-slate-900 border-y border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-3xl mx-auto">
              {stats.map((stat, idx) => (
                <div key={idx} className="text-center">
                  <div className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-1">{stat.value}</div>
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
                <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 hover:border-yellow-500/30 transition-colors">
                  <div className="w-12 h-12 bg-yellow-500/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-yellow-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((b, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-500">
                        <CheckCircle className="w-4 h-4 text-yellow-500 shrink-0" />{b}
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
                <div key={idx} className={cn("bg-slate-800/50 border rounded-xl p-6", plan.popular ? "border-yellow-500/50 bg-yellow-500/5" : "border-slate-700")}>
                  {plan.popular && <span className="text-xs text-yellow-400 font-medium">MOST POPULAR</span>}
                  <h3 className="text-lg font-semibold text-white mt-2">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4">{plan.price}</div>
                  <p className="text-slate-400 text-sm mb-4">{plan.comparisons} comparisons</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-400">
                        <CheckCircle className="w-4 h-4 text-yellow-500" />{f}
                      </li>
                    ))}
                  </ul>
                  <Button className={cn("w-full", plan.popular ? "bg-yellow-500 hover:bg-yellow-600 text-slate-900" : "bg-slate-700 hover:bg-slate-600")} asChild>
                    <Link to="/waitlist?tool=bank-fees">Join Waitlist</Link>
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
            <h2 className="text-3xl font-bold text-white mb-6">Pay What Your Trade Finance is Worth</h2>
            <Button size="lg" className="bg-yellow-500 hover:bg-yellow-600 text-slate-900 font-semibold" asChild>
              <Link to="/waitlist?tool=bank-fees">Join Waitlist <ArrowRight className="w-5 h-5 ml-2" /></Link>
            </Button>
          </div>
        </section>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default BankFeeComparatorLanding;

