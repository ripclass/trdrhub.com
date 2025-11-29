import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, AlertTriangle, Clock, Users, Building2, Shield, ChevronDown, Search, Globe, FileText, TrendingDown, Eye, Scale } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const features = [
  {
    icon: TrendingDown,
    title: "Credit Risk Scores",
    description: "Proprietary credit scoring for trade counterparties. Know the financial health of buyers, suppliers, and banks.",
    bullets: ["Financial health indicators", "Payment probability scores", "Industry benchmarking", "Trend analysis"],
  },
  {
    icon: Clock,
    title: "Payment Behavior History",
    description: "Track record of on-time payments, delays, and defaults. See how they pay their other suppliers.",
    bullets: ["Days-to-pay trends", "Default history", "Dispute frequency", "Payment pattern analysis"],
  },
  {
    icon: Scale,
    title: "Litigation & Bankruptcy",
    description: "Court records, judgments, liens, and bankruptcy filings across multiple jurisdictions.",
    bullets: ["Active litigation", "Judgment history", "UCC filings", "Bankruptcy alerts"],
  },
  {
    icon: Eye,
    title: "Beneficial Ownership",
    description: "See who really owns and controls the company. Identify hidden connections and related parties.",
    bullets: ["Ultimate beneficial owners", "Corporate structure", "Director networks", "Related party alerts"],
  },
  {
    icon: Shield,
    title: "Sanctions & PEP Screening",
    description: "Screen against global sanctions lists and politically exposed persons databases.",
    bullets: ["OFAC, EU, UN lists", "PEP screening", "Adverse media", "Continuous monitoring"],
  },
  {
    icon: Globe,
    title: "Country Risk Assessment",
    description: "Sovereign risk, currency controls, and political stability for the counterparty's jurisdiction.",
    bullets: ["Sovereign ratings", "Currency risk", "Political stability", "Trade restrictions"],
  },
];

const riskIndicators = [
  { name: "Credit Score", description: "Financial health rating A-F" },
  { name: "Payment Score", description: "Historical payment behavior" },
  { name: "Litigation Risk", description: "Legal exposure assessment" },
  { name: "Sanctions Risk", description: "Compliance screening result" },
  { name: "Country Risk", description: "Jurisdiction stability" },
  { name: "Overall Risk", description: "Composite risk rating" },
];

const process = [
  {
    step: "1",
    title: "Enter Company Details",
    description: "Company name, registration number, or DUNS number",
  },
  {
    step: "2",
    title: "Get Risk Report",
    description: "Instant credit, payment, litigation, and sanctions analysis",
  },
  {
    step: "3",
    title: "Set Up Monitoring",
    description: "Get alerts when risk profile changes",
  },
];

const stats = [
  { value: "500M+", label: "Companies Covered" },
  { value: "200+", label: "Countries" },
  { value: "Real-Time", label: "Monitoring" },
  { value: "6", label: "Risk Indicators" },
];

const pricing = [
  { tier: "Starter", reports: "10 reports/mo", price: "$49/mo", description: "For occasional due diligence", features: ["Basic credit score", "Sanctions check", "PDF reports"] },
  { tier: "Professional", reports: "50 reports/mo", price: "$149/mo", description: "For active traders", features: ["Full risk report", "Payment history", "Beneficial ownership", "Monitoring alerts"], popular: true },
  { tier: "Enterprise", reports: "Unlimited", price: "$399/mo", description: "For banks & corporates", features: ["Everything in Pro", "API access", "Bulk screening", "Custom scoring"] },
];

const faqs = [
  {
    q: "What data sources do you use?",
    a: "We aggregate data from credit bureaus (D&B, Experian), court records, corporate registries, sanctions lists, and payment behavior databases. Coverage varies by country but includes 500M+ companies globally.",
  },
  {
    q: "How current is the data?",
    a: "Sanctions and PEP data is updated daily. Credit scores are refreshed monthly. Court records and corporate filings are updated as filed. You can enable continuous monitoring for real-time alerts.",
  },
  {
    q: "Can I screen my entire supplier base?",
    a: "Yes! Enterprise plans include bulk screening and API access. Upload a CSV of your counterparties and get risk reports for all of them.",
  },
  {
    q: "Do you cover companies outside the US/EU?",
    a: "Yes, we cover 200+ countries. Coverage depth varies - US, EU, UK, and major Asian markets have the most comprehensive data. Emerging markets may have limited payment history.",
  },
  {
    q: "Is this a replacement for KYC/AML compliance?",
    a: "TRDR Counterparty Risk is a screening tool, not a compliance solution. Results should be reviewed by your compliance team. We don't provide legal advice.",
  },
];

const CounterpartyRiskLanding = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [companyName, setCompanyName] = useState("");

  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      
      <main>
        {/* Hero Section */}
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-orange-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center mb-12">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 mb-6">
                <Clock className="w-4 h-4 text-amber-400" />
                <span className="text-amber-400 text-sm font-medium">Coming Q2 2025</span>
              </div>
              
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                Know Your{" "}
                <span className="bg-gradient-to-r from-orange-400 to-amber-400 bg-clip-text text-transparent">Trade Partners</span>{" "}
                Before You Deal
              </h1>
              
              <p className="text-lg text-slate-400 mb-8 leading-relaxed max-w-2xl mx-auto">
                Credit scores, payment history, litigation records, and sanctions screening. 
                Make informed decisions about buyers, suppliers, and banks.
              </p>

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-slate-400 mb-12">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  500M+ Companies
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  200+ Countries
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  Real-Time Monitoring
                </div>
              </div>
            </div>

            {/* Search Box */}
            <div className="max-w-2xl mx-auto">
              <div className="bg-slate-900/80 border border-slate-700 rounded-2xl p-6 backdrop-blur">
                <p className="text-slate-400 text-sm mb-4">Enter company name or registration number:</p>
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder="e.g., Acme Trading Ltd or GB12345678"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 transition-colors"
                  />
                  <Button className="bg-orange-500 hover:bg-orange-600 px-6" asChild>
                    <Link to="/waitlist?tool=risk">
                      <Search className="w-5 h-5" />
                    </Link>
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Risk Indicators Preview */}
        <section className="py-12 bg-slate-900 border-y border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 max-w-5xl mx-auto">
              {riskIndicators.map((indicator, idx) => (
                <div key={idx} className="text-center p-4 bg-slate-800/50 rounded-xl border border-slate-700">
                  <div className="text-white font-medium text-sm mb-1">{indicator.name}</div>
                  <div className="text-slate-500 text-xs">{indicator.description}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Stats */}
        <section className="py-12 bg-slate-950">
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

        {/* Problem Statement */}
        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white text-center mb-12">
                Bad Counterparties Cost{" "}
                <span className="text-orange-400">Millions</span>
              </h2>
              
              <div className="grid md:grid-cols-2 gap-8">
                <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">Without Due Diligence</h3>
                  <ul className="space-y-3 text-slate-400">
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Buyer defaults after shipment
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Supplier is on sanctions list
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Hidden ownership by sanctioned party
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      No visibility into payment behavior
                    </li>
                  </ul>
                </div>
                <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">With Counterparty Risk</h3>
                  <ul className="space-y-3 text-slate-400">
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Credit scores before you ship
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Sanctions + PEP screening
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Beneficial ownership revealed
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Payment history from peers
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4">
                Risk Assessment in Three Steps
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Get comprehensive risk intelligence in minutes, not days.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              {process.map((step, idx) => (
                <div key={idx} className="text-center">
                  <div className="w-12 h-12 bg-orange-500/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-orange-500/20">
                    <span className="text-orange-400 font-bold">{step.step}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{step.title}</h3>
                  <p className="text-slate-400 text-sm">{step.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4">
                Comprehensive Risk Intelligence
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Everything you need to assess counterparty risk before you trade.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature, idx) => (
                <div key={idx} className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 hover:border-orange-500/30 transition-colors">
                  <div className="w-12 h-12 bg-orange-500/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-orange-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((bullet, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-500">
                        <CheckCircle className="w-4 h-4 text-orange-500 shrink-0" />
                        {bullet}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing */}
        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4">
                Simple Pricing
              </h2>
              <p className="text-slate-400">
                Pay per report or subscribe for volume discounts.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {pricing.map((plan, idx) => (
                <div key={idx} className={cn(
                  "bg-slate-900/50 border rounded-xl p-6",
                  plan.popular ? "border-orange-500/50 bg-orange-500/5" : "border-slate-800"
                )}>
                  {plan.popular && (
                    <span className="text-xs text-orange-400 font-medium">MOST POPULAR</span>
                  )}
                  <h3 className="text-lg font-semibold text-white mt-2">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4">{plan.price}</div>
                  <p className="text-slate-400 text-sm mb-4">{plan.reports}</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-400">
                        <CheckCircle className="w-4 h-4 text-orange-500" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Button className={cn(
                    "w-full",
                    plan.popular ? "bg-orange-500 hover:bg-orange-600" : "bg-slate-700 hover:bg-slate-600"
                  )} asChild>
                    <Link to="/waitlist?tool=risk">Join Waitlist</Link>
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white text-center mb-12">
                Frequently Asked Questions
              </h2>

              <div className="space-y-4">
                {faqs.map((faq, idx) => (
                  <div key={idx} className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
                    <button
                      className="w-full px-6 py-4 text-left flex items-center justify-between"
                      onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                    >
                      <span className="text-white font-medium">{faq.q}</span>
                      <ChevronDown className={cn(
                        "w-5 h-5 text-slate-400 transition-transform shrink-0 ml-4",
                        openFaq === idx && "rotate-180"
                      )} />
                    </button>
                    {openFaq === idx && (
                      <div className="px-6 pb-4">
                        <p className="text-slate-400 text-sm leading-relaxed">{faq.a}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 bg-slate-950 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-6">
                Stop Trading Blind
              </h2>
              <p className="text-lg text-slate-400 mb-8">
                Know your counterparties before you commit. Join the waitlist.
              </p>
              <Button size="lg" className="bg-orange-500 hover:bg-orange-600 text-white font-semibold" asChild>
                <Link to="/waitlist?tool=risk">
                  Join Waitlist <ArrowRight className="w-5 h-5 ml-2" />
                </Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      <TRDRFooter />
    </div>
  );
};

export default CounterpartyRiskLanding;

