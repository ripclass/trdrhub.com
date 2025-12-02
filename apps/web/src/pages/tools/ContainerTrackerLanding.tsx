import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, Ship, Clock, Bell, Globe, MapPin, ChevronDown, Calendar, AlertTriangle, Anchor, FileText, BarChart3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const features = [
  {
    icon: Globe,
    title: "100+ Carrier Coverage",
    description: "Track containers across Maersk, MSC, CMA CGM, Hapag-Lloyd, ONE, Evergreen, and 100+ more carriers.",
    bullets: ["Top 20 carriers included", "Regional carriers", "Feeder services", "NVO/NVOCC coverage"],
  },
  {
    icon: MapPin,
    title: "Real-Time Location",
    description: "Live position updates from AIS data and carrier systems. See exactly where your container is.",
    bullets: ["AIS position data", "Port arrival/departure", "Terminal gate events", "Rail/truck segments"],
  },
  {
    icon: Calendar,
    title: "Accurate ETAs",
    description: "Machine learning ETAs that account for port congestion, weather, and vessel schedules.",
    bullets: ["ML-powered predictions", "Port congestion factored", "Weather delays included", "Rolling updates"],
  },
  {
    icon: Bell,
    title: "Proactive Alerts",
    description: "Get notified of delays, exceptions, and milestones before they become problems.",
    bullets: ["Delay notifications", "Exception alerts", "Milestone updates", "Custom alert rules"],
  },
  {
    icon: FileText,
    title: "Document Status",
    description: "Track B/L release, customs clearance, and documentation status alongside physical tracking.",
    bullets: ["B/L release status", "Customs clearance", "Holds & exceptions", "Release coordination"],
  },
  {
    icon: BarChart3,
    title: "Analytics Dashboard",
    description: "Carrier performance, port delays, and transit time analytics across your shipments.",
    bullets: ["Carrier scorecards", "Port delay trends", "Transit time analysis", "Exception reports"],
  },
];

const process = [
  {
    step: "1",
    title: "Enter Container Number",
    description: "Paste your container number, B/L, or booking reference",
  },
  {
    step: "2",
    title: "Get Live Status",
    description: "See current location, vessel, ETA, and any exceptions",
  },
  {
    step: "3",
    title: "Set Up Alerts",
    description: "Get notified of delays, arrivals, and milestones automatically",
  },
];

const stats = [
  { value: "100+", label: "Carriers" },
  { value: "95%", label: "ETA Accuracy" },
  { value: "Real-Time", label: "Updates" },
  { value: "Free", label: "Basic Tier" },
];

const carriers = [
  "Maersk", "MSC", "CMA CGM", "Hapag-Lloyd", "ONE", "Evergreen", 
  "COSCO", "Yang Ming", "HMM", "ZIM", "PIL", "Wan Hai"
];

const pricing = [
  { tier: "Free", containers: "10/mo", price: "$0", description: "For occasional shippers", features: ["Basic tracking", "Email alerts", "7-day history"] },
  { tier: "Professional", containers: "100/mo", price: "$49/mo", description: "For regular shippers", features: ["Advanced ETA", "SMS alerts", "Analytics", "API access"], popular: true },
  { tier: "Enterprise", containers: "Unlimited", price: "$199/mo", description: "For freight & 3PL", features: ["Everything in Pro", "White-label", "Integrations", "Dedicated support"] },
];

const faqs = [
  {
    q: "Which carriers do you support?",
    a: "We support 100+ ocean carriers including all major lines (Maersk, MSC, CMA CGM, Hapag-Lloyd, ONE, Evergreen, COSCO, Yang Ming, HMM, ZIM) plus regional carriers and feeder services. Rail and truck tracking is available in select regions.",
  },
  {
    q: "How accurate are the ETAs?",
    a: "Our ML-powered ETAs achieve 95% accuracy within ±1 day for final port arrival. We factor in port congestion, weather patterns, vessel schedules, and historical performance data.",
  },
  {
    q: "Can I track by B/L number?",
    a: "Yes! You can track using container number, B/L number, booking reference, or carrier reference. We automatically match across carriers.",
  },
  {
    q: "How do alerts work?",
    a: "Set up custom alerts for departure, arrival, delays, exceptions, or custom milestones. Receive notifications via email, SMS, webhook, or in-app. Configure thresholds (e.g., alert if delay > 2 days).",
  },
  {
    q: "Can I integrate with my TMS or ERP?",
    a: "Yes, Professional and Enterprise plans include API access for real-time tracking data. We support webhooks, REST API, and pre-built integrations with common platforms.",
  },
];

const ContainerTrackerLanding = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [containerNumber, setContainerNumber] = useState("");

  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      
      <main>
        {/* Hero Section */}
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center mb-12">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-6">
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                <span className="text-emerald-400 text-sm font-medium">Now Available</span>
              </div>
              
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                Track Every Container,{" "}
                <span className="bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">Every Carrier</span>
              </h1>
              
              <p className="text-lg text-slate-400 mb-8 leading-relaxed max-w-2xl mx-auto">
                Real-time container tracking across 100+ carriers. Live ETAs, delay alerts, 
                and exception notifications in one dashboard.
              </p>

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-slate-400 mb-12">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  100+ Carriers
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  Real-Time Updates
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  ML-Powered ETAs
                </div>
              </div>
            </div>

            {/* Search Box */}
            <div className="max-w-2xl mx-auto">
              <div className="bg-slate-900/80 border border-slate-700 rounded-2xl p-6 backdrop-blur">
                <p className="text-slate-400 text-sm mb-4">Enter container number, B/L, or booking reference:</p>
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder="e.g., MSCU1234567 or MAEU123456789"
                    value={containerNumber}
                    onChange={(e) => setContainerNumber(e.target.value)}
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                  />
                  <Button className="bg-blue-500 hover:bg-blue-600 px-6" asChild>
                    <Link to="/tracking/dashboard">
                      <Ship className="w-5 h-5 mr-2" />
                      Track
                    </Link>
                  </Button>
                </div>
                <div className="mt-4 flex flex-wrap gap-2 items-center">
                  <span className="text-xs text-slate-500">Supported carriers:</span>
                  {carriers.slice(0, 6).map((carrier, idx) => (
                    <span key={idx} className="text-xs text-blue-400">{carrier}</span>
                  ))}
                  <span className="text-xs text-slate-500">+100 more</span>
                </div>
              </div>
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
                Shipment Visibility is{" "}
                <span className="text-blue-400">Fragmented</span>
              </h2>
              
              <div className="grid md:grid-cols-2 gap-8">
                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">Without TRDR</h3>
                  <ul className="space-y-3 text-slate-400">
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Login to 10 carrier portals daily
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      ETAs always wrong at port congestion
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Find out about delays after the fact
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      No single view of all shipments
                    </li>
                  </ul>
                </div>
                <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">With Container Tracker</h3>
                  <ul className="space-y-3 text-slate-400">
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      All carriers in one dashboard
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      ML-adjusted ETAs with 95% accuracy
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Proactive delay alerts
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Portfolio view + analytics
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
                Track in Three Steps
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Enter your reference, get instant visibility.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              {process.map((step, idx) => (
                <div key={idx} className="text-center">
                  <div className="w-12 h-12 bg-blue-500/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-blue-500/20">
                    <span className="text-blue-400 font-bold">{step.step}</span>
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
                Complete Shipment Visibility
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Real-time tracking, intelligent ETAs, and proactive alerts.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature, idx) => (
                <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 hover:border-blue-500/30 transition-colors">
                  <div className="w-12 h-12 bg-blue-500/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-blue-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((bullet, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-500">
                        <CheckCircle className="w-4 h-4 text-blue-500 shrink-0" />
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
                Free tier for occasional tracking. Scale as you grow.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {pricing.map((plan, idx) => (
                <div key={idx} className={cn(
                  "bg-slate-800/50 border rounded-xl p-6",
                  plan.popular ? "border-blue-500/50 bg-blue-500/5" : "border-slate-700"
                )}>
                  {plan.popular && (
                    <span className="text-xs text-blue-400 font-medium">MOST POPULAR</span>
                  )}
                  <h3 className="text-lg font-semibold text-white mt-2">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4">{plan.price}</div>
                  <p className="text-slate-400 text-sm mb-4">{plan.containers}</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-400">
                        <CheckCircle className="w-4 h-4 text-blue-500" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Button className={cn(
                    "w-full",
                    plan.popular ? "bg-blue-500 hover:bg-blue-600" : "bg-slate-700 hover:bg-slate-600"
                  )} asChild>
                    <Link to="/tracking/dashboard">{plan.tier === "Free" ? "Get Started" : "Start Free Trial"}</Link>
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
                Never Lose Track of a Shipment Again
              </h2>
              <p className="text-lg text-slate-400 mb-8">
                Join the waitlist for early access.
              </p>
              <Button size="lg" className="bg-blue-500 hover:bg-blue-600 text-white font-semibold" asChild>
                <Link to="/tracking/dashboard">
                  Start Tracking <ArrowRight className="w-5 h-5 ml-2" />
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

export default ContainerTrackerLanding;

