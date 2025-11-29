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
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      
      <main>
        {/* Hero Section */}
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center mb-12">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 mb-6">
                <Clock className="w-4 h-4 text-amber-400" />
                <span className="text-amber-400 text-sm font-medium">Coming Q3 2025</span>
              </div>
              
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                Turn Trade Data into{" "}
                <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">Actionable Insights</span>
              </h1>
              
              <p className="text-lg text-slate-400 mb-8 leading-relaxed max-w-2xl mx-auto">
                Dashboards for trade volume, compliance rates, supplier performance, and operational KPIs. 
                Know where you're winning and where you're leaking money.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
                <Button size="lg" className="bg-indigo-500 hover:bg-indigo-600 text-white font-semibold" asChild>
                  <Link to="/waitlist?tool=analytics">
                    Join Waitlist <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button variant="outline" size="lg" className="border-slate-700 text-slate-300 hover:bg-slate-800" asChild>
                  <Link to="/contact">Request Demo</Link>
                </Button>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-slate-400">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  50+ Metrics
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  Custom Dashboards
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  API Access
                </div>
              </div>
            </div>

            {/* Metrics Preview */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 max-w-4xl mx-auto">
              {metrics.map((metric, idx) => (
                <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 hover:border-indigo-500/30 transition-colors">
                  <h3 className="text-white font-medium text-sm mb-1">{metric.name}</h3>
                  <p className="text-slate-500 text-xs">{metric.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Stats */}
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

        {/* Problem Statement */}
        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white text-center mb-12">
                Trade Operations are a{" "}
                <span className="text-indigo-400">Black Box</span>
              </h2>
              
              <div className="grid md:grid-cols-2 gap-8">
                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">Without Analytics</h3>
                  <ul className="space-y-3 text-slate-400">
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
                <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">With Trade Analytics</h3>
                  <ul className="space-y-3 text-slate-400">
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Real-time compliance dashboards
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Supplier scorecards and rankings
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Bank performance comparisons
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Automated scheduled reports
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4">
                From Data to Insights in Minutes
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Connect your data, pick your metrics, build your dashboards.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              {process.map((step, idx) => (
                <div key={idx} className="text-center">
                  <div className="w-12 h-12 bg-indigo-500/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-indigo-500/20">
                    <span className="text-indigo-400 font-bold">{step.step}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{step.title}</h3>
                  <p className="text-slate-400 text-sm">{step.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4">
                Everything for Trade Intelligence
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Pre-built metrics, custom dashboards, and automated reports.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature, idx) => (
                <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 hover:border-indigo-500/30 transition-colors">
                  <div className="w-12 h-12 bg-indigo-500/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-indigo-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((bullet, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-500">
                        <CheckCircle className="w-4 h-4 text-indigo-500 shrink-0" />
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
        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4">
                Simple Pricing
              </h2>
              <p className="text-slate-400">
                Start small, scale with your data needs.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {pricing.map((plan, idx) => (
                <div key={idx} className={cn(
                  "bg-slate-800/50 border rounded-xl p-6",
                  plan.popular ? "border-indigo-500/50 bg-indigo-500/5" : "border-slate-700"
                )}>
                  {plan.popular && (
                    <span className="text-xs text-indigo-400 font-medium">MOST POPULAR</span>
                  )}
                  <h3 className="text-lg font-semibold text-white mt-2">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4">{plan.price}</div>
                  <p className="text-slate-400 text-sm mb-4">{plan.description}</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-400">
                        <CheckCircle className="w-4 h-4 text-indigo-500" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Button className={cn(
                    "w-full",
                    plan.popular ? "bg-indigo-500 hover:bg-indigo-600" : "bg-slate-700 hover:bg-slate-600"
                  )} asChild>
                    <Link to="/waitlist?tool=analytics">Join Waitlist</Link>
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white text-center mb-12">
                Frequently Asked Questions
              </h2>

              <div className="space-y-4">
                {faqs.map((faq, idx) => (
                  <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
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
        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-6">
                Make Data-Driven Trade Decisions
              </h2>
              <p className="text-lg text-slate-400 mb-8">
                Join the waitlist for early access.
              </p>
              <Button size="lg" className="bg-indigo-500 hover:bg-indigo-600 text-white font-semibold" asChild>
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

