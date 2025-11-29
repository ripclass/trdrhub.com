import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, Route, Clock, Ship, Plane, DollarSign, ChevronDown, Globe, Timer, Leaf, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const features = [
  { icon: Ship, title: "Multi-Carrier Comparison", description: "Compare rates and schedules across 100+ ocean carriers.", bullets: ["Ocean carriers", "Air freight", "Multimodal", "NVOCC options"] },
  { icon: Timer, title: "Transit Time Estimates", description: "Accurate transit times including port dwell and customs.", bullets: ["Port-to-port", "Door-to-door", "Dwell time", "Buffer analysis"] },
  { icon: DollarSign, title: "Cost Comparison", description: "All-in costs including surcharges and port fees.", bullets: ["Base freight", "Surcharges", "Port fees", "Hidden costs"] },
  { icon: Globe, title: "Port Alternatives", description: "Find alternative ports that save time or money.", bullets: ["Nearby ports", "Congestion data", "Rail connections", "Drayage options"] },
  { icon: TrendingUp, title: "Reliability Scores", description: "On-time performance and schedule reliability by carrier.", bullets: ["Schedule reliability", "Blank sailings", "Carrier ratings", "Historical data"] },
  { icon: Leaf, title: "Carbon Footprint", description: "CO2 emissions by route for ESG reporting.", bullets: ["Route emissions", "Carrier comparison", "Alternative modes", "ESG reports"] },
];

const stats = [
  { value: "100+", label: "Carriers" },
  { value: "500+", label: "Port Pairs" },
  { value: "Real-Time", label: "Schedules" },
  { value: "CO2", label: "Tracking" },
];

const pricing = [
  { tier: "Starter", searches: "25/mo", price: "$29/mo", features: ["Basic comparison", "3 carriers", "Transit times"] },
  { tier: "Professional", searches: "100/mo", price: "$79/mo", features: ["All carriers", "Full costs", "Reliability", "CO2"], popular: true },
  { tier: "Enterprise", searches: "Unlimited", price: "$199/mo", features: ["Everything in Pro", "API", "Contract rates", "Integrations"] },
];

const faqs = [
  { q: "Which carriers do you include?", a: "We include 100+ ocean carriers and major air freight providers. Rates are indicative - get exact quotes from carriers for booking." },
  { q: "How current are the schedules?", a: "Schedules are updated daily from carrier feeds. We show announced schedules plus historical reliability data." },
  { q: "Can I compare air vs sea?", a: "Yes! Compare total cost and time for air vs sea vs multimodal options for the same lane." },
];

const RouteOptimizerLanding = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      <main>
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 mb-6">
                <Clock className="w-4 h-4 text-amber-400" />
                <span className="text-amber-400 text-sm font-medium">Coming Q3 2025</span>
              </div>
              
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                Find the{" "}
                <span className="bg-gradient-to-r from-purple-400 to-violet-400 bg-clip-text text-transparent">Best Route</span>{" "}
                for Every Shipment
              </h1>
              
              <p className="text-lg text-slate-400 mb-8 leading-relaxed max-w-2xl mx-auto">
                Compare carriers, transit times, and costs across shipping options. 
                Find the best route by cost, time, or reliability.
              </p>

              <Button size="lg" className="bg-purple-500 hover:bg-purple-600 text-white font-semibold" asChild>
                <Link to="/waitlist?tool=routes">Join Waitlist <ArrowRight className="w-5 h-5 ml-2" /></Link>
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
                <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 hover:border-purple-500/30 transition-colors">
                  <div className="w-12 h-12 bg-purple-500/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-purple-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((b, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-500">
                        <CheckCircle className="w-4 h-4 text-purple-500 shrink-0" />{b}
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
                <div key={idx} className={cn("bg-slate-800/50 border rounded-xl p-6", plan.popular ? "border-purple-500/50 bg-purple-500/5" : "border-slate-700")}>
                  {plan.popular && <span className="text-xs text-purple-400 font-medium">MOST POPULAR</span>}
                  <h3 className="text-lg font-semibold text-white mt-2">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4">{plan.price}</div>
                  <p className="text-slate-400 text-sm mb-4">{plan.searches} searches</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-400">
                        <CheckCircle className="w-4 h-4 text-purple-500" />{f}
                      </li>
                    ))}
                  </ul>
                  <Button className={cn("w-full", plan.popular ? "bg-purple-500 hover:bg-purple-600" : "bg-slate-700 hover:bg-slate-600")} asChild>
                    <Link to="/waitlist?tool=routes">Join Waitlist</Link>
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
            <h2 className="text-3xl font-bold text-white mb-6">Ship Smarter</h2>
            <Button size="lg" className="bg-purple-500 hover:bg-purple-600 text-white font-semibold" asChild>
              <Link to="/waitlist?tool=routes">Join Waitlist <ArrowRight className="w-5 h-5 ml-2" /></Link>
            </Button>
          </div>
        </section>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default RouteOptimizerLanding;

