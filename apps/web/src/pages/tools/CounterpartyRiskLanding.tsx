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
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      
      <main>
        {/* Hero Section */}
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden bg-[#00261C]">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-[#B2F273]/10 rounded-full blur-[120px]" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-[100px]" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center mb-12">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#B2F273]/10 border border-[#B2F273]/20 mb-6">
                <Clock className="w-4 h-4 text-[#B2F273]" />
                <span className="text-[#B2F273] text-sm font-medium">Coming Q2 2025</span>
              </div>
              
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight font-display">
                Know Your{" "}
                <span className="text-[#B2F273] text-glow-sm">Trade Partners</span>{" "}
                Before You Deal
              </h1>
              
              <p className="text-lg text-[#EDF5F2]/60 mb-8 leading-relaxed max-w-2xl mx-auto">
                Credit scores, payment history, litigation records, and sanctions screening. 
                Make informed decisions about buyers, suppliers, and banks.
              </p>

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-[#EDF5F2]/60 mb-12">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  500M+ Companies
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  200+ Countries
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  Real-Time Monitoring
                </div>
              </div>
            </div>

            {/* Search Box */}
            <div className="max-w-2xl mx-auto">
              <div className="bg-[#00382E]/80 border border-[#EDF5F2]/10 rounded-2xl p-6 backdrop-blur-md shadow-xl">
                <p className="text-[#EDF5F2]/60 text-sm mb-4">Enter company name or registration number:</p>
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder="e.g., Acme Trading Ltd or GB12345678"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="flex-1 bg-[#00261C] border border-[#EDF5F2]/10 rounded-lg px-4 py-3 text-white placeholder-[#EDF5F2]/30 focus:outline-none focus:border-[#B2F273]/50 transition-colors"
                  />
                  <Button className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] px-6 font-bold" asChild>
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
        <section className="relative py-12 bg-[#00261C] border-y border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 max-w-5xl mx-auto">
              {riskIndicators.map((indicator, idx) => (
                <div key={idx} className="text-center p-4 bg-[#00382E]/50 rounded-xl border border-[#EDF5F2]/10 backdrop-blur-sm">
                  <div className="text-white font-bold text-sm mb-1 font-display">{indicator.name}</div>
                  <div className="text-[#EDF5F2]/60 text-xs">{indicator.description}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Stats */}
        <section className="relative py-12 bg-[#00261C] overflow-hidden">
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

        {/* Problem Statement */}
        <section className="relative py-20 bg-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white text-center mb-12 font-display">
                Bad Counterparties Cost{" "}
                <span className="text-[#B2F273]">Millions</span>
              </h2>
              
              <div className="grid md:grid-cols-2 gap-8">
                <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 backdrop-blur-sm">
                  <h3 className="text-lg font-bold text-white mb-4 font-display">Without Due Diligence</h3>
                  <ul className="space-y-3 text-[#EDF5F2]/60">
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
                <div className="bg-[#B2F273]/5 border border-[#B2F273]/20 rounded-xl p-6 backdrop-blur-sm">
                  <h3 className="text-lg font-bold text-white mb-4 font-display">With Counterparty Risk</h3>
                  <ul className="space-y-3 text-[#EDF5F2]/60">
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Credit scores before you ship
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Sanctions + PEP screening
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Beneficial ownership revealed
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Payment history from peers
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
                Risk Assessment in Three Steps
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                Get comprehensive risk intelligence in minutes, not days.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              {process.map((step, idx) => (
                <div key={idx} className="text-center group">
                  <div className="w-12 h-12 bg-[#B2F273]/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-[#B2F273]/20 group-hover:bg-[#B2F273] transition-colors duration-300">
                    <span className="text-[#B2F273] font-bold font-display group-hover:text-[#00261C] transition-colors">{step.step}</span>
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2 font-display">{step.title}</h3>
                  <p className="text-[#EDF5F2]/60 text-sm">{step.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="relative py-20 bg-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
                Comprehensive Risk Intelligence
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                Everything you need to assess counterparty risk before you trade.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature, idx) => (
                <div key={idx} className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 hover:border-[#B2F273]/30 transition-colors group backdrop-blur-sm">
                  <div className="w-12 h-12 bg-[#B2F273]/10 rounded-lg flex items-center justify-center mb-4 border border-[#B2F273]/20 group-hover:bg-[#B2F273] transition-colors">
                    <feature.icon className="w-6 h-6 text-[#B2F273] group-hover:text-[#00261C] transition-colors" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2 font-display">{feature.title}</h3>
                  <p className="text-[#EDF5F2]/60 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((bullet, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-[#EDF5F2]/50">
                        <CheckCircle className="w-4 h-4 text-[#B2F273] shrink-0" />
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
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
                Simple Pricing
              </h2>
              <p className="text-[#EDF5F2]/60">
                Pay per report or subscribe for volume discounts.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {pricing.map((plan, idx) => (
                <div key={idx} className={cn(
                  "bg-[#00382E]/50 border rounded-xl p-6 backdrop-blur-sm",
                  plan.popular ? "border-[#B2F273] shadow-[0_0_20px_rgba(178,242,115,0.1)]" : "border-[#EDF5F2]/10"
                )}>
                  {plan.popular && (
                    <span className="text-xs text-[#B2F273] font-mono uppercase tracking-wider font-medium">MOST POPULAR</span>
                  )}
                  <h3 className="text-lg font-bold text-white mt-2 font-display">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4 font-display">{plan.price}</div>
                  <p className="text-[#EDF5F2]/60 text-sm mb-4">{plan.reports}</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-[#EDF5F2]/50">
                        <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Button className={cn(
                    "w-full font-bold border-none",
                    plan.popular ? "bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C]" : "bg-[#EDF5F2]/10 hover:bg-[#EDF5F2]/20 text-white"
                  )} asChild>
                    <Link to="/waitlist?tool=risk">Join Waitlist</Link>
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="relative py-20 bg-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white text-center mb-12 font-display">
                Frequently Asked Questions
              </h2>

              <div className="space-y-4">
                {faqs.map((faq, idx) => (
                  <div key={idx} className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl overflow-hidden backdrop-blur-sm">
                    <button
                      className="w-full px-6 py-4 text-left flex items-center justify-between"
                      onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                    >
                      <span className="text-white font-medium font-display">{faq.q}</span>
                      <ChevronDown className={cn(
                        "w-5 h-5 text-[#EDF5F2]/40 transition-transform shrink-0 ml-4",
                        openFaq === idx && "rotate-180"
                      )} />
                    </button>
                    {openFaq === idx && (
                      <div className="px-6 pb-4">
                        <p className="text-[#EDF5F2]/60 text-sm leading-relaxed">{faq.a}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="relative py-20 bg-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-6 font-display">
                Stop Trading Blind
              </h2>
              <p className="text-lg text-[#EDF5F2]/60 mb-8">
                Know your counterparties before you commit. Join the waitlist.
              </p>
              <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
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
