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
                <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                <span className="text-[#B2F273] text-sm font-medium">Now Available</span>
              </div>
              
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight font-display">
                Track Every Container,{" "}
                <span className="text-[#B2F273] text-glow-sm">Every Carrier</span>
              </h1>
              
              <p className="text-lg text-[#EDF5F2]/60 mb-8 leading-relaxed max-w-2xl mx-auto">
                Real-time container tracking across 100+ carriers. Live ETAs, delay alerts, 
                and exception notifications in one dashboard.
              </p>

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-[#EDF5F2]/60 mb-12">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  100+ Carriers
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  Real-Time Updates
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  ML-Powered ETAs
                </div>
              </div>
            </div>

            {/* Search Box */}
            <div className="max-w-2xl mx-auto">
              <div className="bg-[#00382E]/80 border border-[#EDF5F2]/10 rounded-2xl p-6 backdrop-blur-md shadow-xl">
                <p className="text-[#EDF5F2]/60 text-sm mb-4">Enter container number, B/L, or booking reference:</p>
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder="e.g., MSCU1234567 or MAEU123456789"
                    value={containerNumber}
                    onChange={(e) => setContainerNumber(e.target.value)}
                    className="flex-1 bg-[#00261C] border border-[#EDF5F2]/10 rounded-lg px-4 py-3 text-white placeholder-[#EDF5F2]/30 focus:outline-none focus:border-[#B2F273]/50 transition-colors"
                  />
                  <Button className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] px-6 font-bold" asChild>
                    <Link to="/tracking/dashboard">
                      <Ship className="w-5 h-5 mr-2" />
                      Track
                    </Link>
                  </Button>
                </div>
                <div className="mt-4 flex flex-wrap gap-2 items-center">
                  <span className="text-xs text-[#EDF5F2]/40">Supported carriers:</span>
                  {carriers.slice(0, 6).map((carrier, idx) => (
                    <span key={idx} className="text-xs text-[#B2F273]">{carrier}</span>
                  ))}
                  <span className="text-xs text-[#EDF5F2]/40">+100 more</span>
                </div>
              </div>
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
                Shipment Visibility is{" "}
                <span className="text-[#B2F273]">Fragmented</span>
              </h2>
              
              <div className="grid md:grid-cols-2 gap-8">
                <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 backdrop-blur-sm">
                  <h3 className="text-lg font-bold text-white mb-4 font-display">Without TRDR</h3>
                  <ul className="space-y-3 text-[#EDF5F2]/60">
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
                <div className="bg-[#B2F273]/5 border border-[#B2F273]/20 rounded-xl p-6 backdrop-blur-sm">
                  <h3 className="text-lg font-bold text-white mb-4 font-display">With Container Tracker</h3>
                  <ul className="space-y-3 text-[#EDF5F2]/60">
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      All carriers in one dashboard
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      ML-adjusted ETAs with 95% accuracy
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Proactive delay alerts
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Portfolio view + analytics
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
                Track in Three Steps
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                Enter your reference, get instant visibility.
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
                Complete Shipment Visibility
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                Real-time tracking, intelligent ETAs, and proactive alerts.
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
                Free tier for occasional tracking. Scale as you grow.
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
                  <p className="text-[#EDF5F2]/60 text-sm mb-4">{plan.containers}</p>
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
                    <Link to="/tracking/dashboard">{plan.tier === "Free" ? "Get Started" : "Start Free Trial"}</Link>
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
                Never Lose Track of a Shipment Again
              </h2>
              <p className="text-lg text-[#EDF5F2]/60 mb-8">
                Join the waitlist for early access.
              </p>
              <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
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
