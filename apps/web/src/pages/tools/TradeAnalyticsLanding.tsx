import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, BarChart3, Clock, TrendingUp, PieChart, LineChart, ChevronDown, FileText, Users, Building2, AlertTriangle, Target, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const features = [
  {
    icon: TrendingUp,
    title: "Trade Volume Analytics",
    description: "Track shipment volumes, values, and trends across time, destinations, and product categories.",
    bullets: ["Monthly/quarterly trends", "YoY comparisons", "By country/product", "Value vs volume"],
  },
  {
    icon: Target,
    title: "Compliance Metrics",
    description: "Monitor LC compliance rates, discrepancy patterns, and first-time acceptance rates.",
    bullets: ["Compliance rate trends", "Discrepancy breakdown", "Root cause analysis", "Improvement tracking"],
  },
  {
    icon: Users,
    title: "Supplier Scorecards",
    description: "Rate and compare supplier performance on delivery, documentation, and quality.",
    bullets: ["On-time delivery %", "Doc accuracy rate", "Quality metrics", "Risk scoring"],
  },
  {
    icon: Building2,
    title: "Bank Performance",
    description: "Track bank processing times, fee trends, and first-presentation acceptance.",
    bullets: ["Processing time trends", "Fee comparison", "Acceptance rates", "Amendment frequency"],
  },
  {
    icon: PieChart,
    title: "Custom Dashboards",
    description: "Build custom dashboards with the metrics that matter to your business.",
    bullets: ["Drag-and-drop builder", "Widget library", "Share with team", "Schedule reports"],
  },
  {
    icon: FileText,
    title: "Export & Reports",
    description: "Generate PDF reports, Excel exports, and scheduled email digests.",
    bullets: ["PDF reports", "Excel export", "Scheduled emails", "API data access"],
  },
];

const metrics = [
  { name: "Trade Volume", description: "Shipments by month, country, product" },
  { name: "LC Compliance Rate", description: "First-presentation acceptance %" },
  { name: "Discrepancy Analysis", description: "Types, frequency, root causes" },
  { name: "Processing Time", description: "Bank turnaround trends" },
  { name: "Supplier Performance", description: "Delivery, docs, quality" },
  { name: "Cost Analysis", description: "Fees, duties, shipping trends" },
];

const process = [
  {
    step: "1",
    title: "Connect Data",
    description: "Import from LCopilot, upload CSVs, or connect via API",
  },
  {
    step: "2",
    title: "Choose Metrics",
    description: "Select from 50+ pre-built metrics or create custom calculations",
  },
  {
    step: "3",
    title: "Build Dashboards",
    description: "Drag and drop charts, set up alerts, schedule reports",
  },
];

const stats = [
  { value: "50+", label: "Pre-Built Metrics" },
  { value: "Real-Time", label: "Data Sync" },
  { value: "PDF/Excel", label: "Export Options" },
  { value: "API", label: "Access" },
];

const pricing = [
  { tier: "Starter", price: "$49/mo", description: "For small traders", features: ["10 dashboards", "Basic metrics", "Monthly reports", "Email support"] },
  { tier: "Professional", price: "$149/mo", description: "For active traders", features: ["Unlimited dashboards", "All metrics", "Custom reports", "API access"], popular: true },
  { tier: "Enterprise", price: "$399/mo", description: "For large operations", features: ["Everything in Pro", "Custom metrics", "White-label", "Dedicated support"] },
];

const faqs = [
  {
    q: "What data sources do you support?",
    a: "We integrate with LCopilot data automatically. You can also import data via CSV upload, Excel import, or connect your ERP/TMS via API. We support common formats from SAP, Oracle, and other trade systems.",
  },
  {
    q: "Can I create custom metrics?",
    a: "Yes! Professional and Enterprise plans include a formula builder for custom metrics. Combine any data fields with mathematical operations, time-based calculations, and conditional logic.",
  },
  {
    q: "How often is data updated?",
    a: "LCopilot data syncs in real-time. Imported data updates on your schedule - hourly, daily, or on-demand. API connections can be configured for real-time or batch updates.",
  },
  {
    q: "Can I share dashboards with my team?",
    a: "Yes, all plans include dashboard sharing. Control access by user or role. Enterprise plans add presentation mode, external sharing links, and embedded analytics.",
  },
  {
    q: "Do you offer benchmarking?",
    a: "Enterprise plans include industry benchmarking - compare your compliance rates, processing times, and costs against anonymized industry averages.",
  },
];

const TradeAnalyticsLanding = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

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
                <span className="text-[#B2F273] text-sm font-medium">Coming Q3 2025</span>
              </div>
              
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight font-display">
                Turn Trade Data into{" "}
                <span className="text-[#B2F273] text-glow-sm">Actionable Insights</span>
              </h1>
              
              <p className="text-lg text-[#EDF5F2]/60 mb-8 leading-relaxed max-w-2xl mx-auto">
                Dashboards for trade volume, compliance rates, supplier performance, and operational KPIs. 
                Know where you're winning and where you're leaking money.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
                <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
                  <Link to="/waitlist?tool=analytics">
                    Join Waitlist <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button variant="outline" size="lg" className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 bg-transparent" asChild>
                  <Link to="/contact">Request Demo</Link>
                </Button>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-[#EDF5F2]/60">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  50+ Metrics
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  Custom Dashboards
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  API Access
                </div>
              </div>
            </div>

            {/* Metrics Preview */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 max-w-4xl mx-auto">
              {metrics.map((metric, idx) => (
                <div key={idx} className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-4 hover:border-[#B2F273]/30 transition-colors backdrop-blur-sm">
                  <h3 className="text-white font-bold text-sm mb-1 font-display">{metric.name}</h3>
                  <p className="text-[#EDF5F2]/60 text-xs">{metric.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Stats */}
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

        {/* Problem Statement */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white text-center mb-12 font-display">
                Trade Operations are a{" "}
                <span className="text-[#B2F273]">Black Box</span>
              </h2>
              
              <div className="grid md:grid-cols-2 gap-8">
                <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 backdrop-blur-sm">
                  <h3 className="text-lg font-bold text-white mb-4 font-display">Without Analytics</h3>
                  <ul className="space-y-3 text-[#EDF5F2]/60">
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      No visibility into compliance trends
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Can't compare supplier performance
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Bank fees and times are a mystery
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Manual Excel reports take hours
                    </li>
                  </ul>
                </div>
                <div className="bg-[#B2F273]/5 border border-[#B2F273]/20 rounded-xl p-6 backdrop-blur-sm">
                  <h3 className="text-lg font-bold text-white mb-4 font-display">With Trade Analytics</h3>
                  <ul className="space-y-3 text-[#EDF5F2]/60">
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Real-time compliance dashboards
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Supplier scorecards and rankings
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Bank performance comparisons
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Automated scheduled reports
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="relative py-20 bg-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
                From Data to Insights in Minutes
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                Connect your data, pick your metrics, build your dashboards.
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
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
                Everything for Trade Intelligence
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                Pre-built metrics, custom dashboards, and automated reports.
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
        <section className="relative py-20 bg-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
                Simple Pricing
              </h2>
              <p className="text-[#EDF5F2]/60">
                Start small, scale with your data needs.
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
                  <p className="text-[#EDF5F2]/60 text-sm mb-4">{plan.description}</p>
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
                    <Link to="/waitlist?tool=analytics">Join Waitlist</Link>
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
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
                Make Data-Driven Trade Decisions
              </h2>
              <p className="text-lg text-[#EDF5F2]/60 mb-8">
                Join the waitlist for early access.
              </p>
              <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
                <Link to="/waitlist?tool=analytics">
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

export default TradeAnalyticsLanding;
