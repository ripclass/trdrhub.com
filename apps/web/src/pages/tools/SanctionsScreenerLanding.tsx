import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, Shield, Zap, AlertTriangle, Database, RefreshCw, Building2, Ship, ChevronDown, Users, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const screeningTypes = [
  {
    id: "party",
    title: "Screen a Party",
    description: "Check buyers, sellers, banks, and agents against sanctions lists",
    to: "/sanctions/dashboard/screen/party",
    icon: Users,
    accent: "from-red-500 to-red-600",
  },
  {
    id: "vessel",
    title: "Screen a Vessel",
    description: "Verify vessels against sanctioned flags, owners, and dark activity patterns",
    to: "/sanctions/dashboard/screen/vessel",
    icon: Ship,
    accent: "from-orange-500 to-orange-600",
  },
  {
    id: "goods",
    title: "Screen Goods",
    description: "Check HS codes against dual-use and export control lists",
    to: "/sanctions/dashboard/screen/goods",
    icon: AlertTriangle,
    accent: "from-yellow-500 to-yellow-600",
  },
];

const features = [
  {
    icon: Database,
    title: "50+ Global Sanctions Lists",
    description: "Screen against OFAC SDN, EU Consolidated, UN Security Council, UK OFSI, and dozens more.",
    bullets: ["OFAC SDN & Sectoral Lists", "EU 14 Russia packages", "UN 1718 DPRK sanctions", "UK OFSI & Magnitsky"],
  },
  {
    icon: RefreshCw,
    title: "Updated Within Hours",
    description: "Lists are synced within hours of official publication. Never screen against stale data.",
    bullets: ["Daily list synchronization", "Alert on list changes", "Historical screening available", "Timestamp on every result"],
  },
  {
    icon: Ship,
    title: "Vessel & Port Screening",
    description: "Screen vessels against sanctioned flags, ownership chains, and AIS dark activity patterns.",
    bullets: ["IMO number lookup", "Flag state verification", "Ownership chain analysis", "Dark activity detection"],
  },
  {
    icon: Users,
    title: "Intelligent Name Matching",
    description: "Fuzzy matching catches spelling variations, transliterations, and aliases that exact matching misses.",
    bullets: ["Multi-language support", "Alias database included", "Phonetic matching", "OFAC 50% rule applied"],
  },
  {
    icon: AlertTriangle,
    title: "Dual-Use Goods Check",
    description: "Screen goods descriptions against export control lists including EAR, EU 2021/821, and Wassenaar.",
    bullets: ["HS code classification", "ECCN lookup", "End-use screening", "License determination"],
  },
  {
    icon: Zap,
    title: "Results in Under 2 Seconds",
    description: "Instant screening for single queries. Batch upload for bulk operations. API for integration.",
    bullets: ["Single & batch modes", "API access available", "PDF certificate download", "Audit trail included"],
  },
];

const process = [
  {
    step: "1",
    title: "Enter Details",
    description: "Type a party name, paste an IMO number, or describe your goods",
  },
  {
    step: "2",
    title: "Select Lists",
    description: "Choose which sanctions lists to screen against (we recommend all)",
  },
  {
    step: "3",
    title: "Get Results",
    description: "Instant clear/match status with downloadable compliance certificate",
  },
];

const stats = [
  { value: "50+", label: "Sanctions Lists" },
  { value: "<2s", label: "Screening Time" },
  { value: "99.9%", label: "Uptime" },
  { value: "Daily", label: "List Updates" },
];

const pricing = [
  { tier: "Free", screens: "10", price: "$0", description: "Try before you commit" },
  { tier: "Starter", screens: "100", price: "$29/mo", description: "For occasional traders" },
  { tier: "Professional", screens: "500", price: "$99/mo", description: "For active exporters", popular: true },
  { tier: "Enterprise", screens: "Unlimited", price: "$299/mo", description: "For banks & freight" },
];

const faqs = [
  {
    q: "Which sanctions lists do you cover?",
    a: "We cover 50+ lists including OFAC SDN, EU Consolidated, UN Security Council, UK OFSI, Australia DFAT, Canada SEMA, and more. We also include sectoral sanctions (SSI, CAPTA) and entity-based lists (BIS Entity List, EAR).",
  },
  {
    q: "How quickly are lists updated?",
    a: "Lists are synchronized within hours of official publication. OFAC typically updates daily, EU weekly, and UN as published. Every screening result includes a timestamp showing when the lists were last updated.",
  },
  {
    q: "Can I integrate with my ERP or compliance system?",
    a: "Yes, our Professional and Enterprise plans include API access for real-time screening from your existing systems. We provide REST API documentation and sample code.",
  },
  {
    q: "What happens when there's a potential match?",
    a: "We show you the match details including the list source, match confidence score, and the specific entry that triggered the match. You can download a PDF report for your compliance records.",
  },
  {
    q: "Is this a replacement for legal advice?",
    a: "No. TRDR Sanctions Screener is a screening aid, not legal advice. Results should be verified with your compliance team. We update lists regularly but cannot guarantee real-time accuracy.",
  },
];

const SanctionsScreenerLanding = () => {
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
            <div className="max-w-3xl mx-auto text-center mb-16">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#B2F273]/10 border border-[#B2F273]/20 mb-6">
                <Shield className="w-4 h-4 text-[#B2F273]" />
                <span className="text-[#B2F273] text-sm font-medium">Compliance Tool</span>
              </div>
              
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight font-display">
                Screen Parties & Goods in{" "}
                <span className="text-[#B2F273] text-glow-sm">Seconds</span>
              </h1>
              
              <p className="text-lg text-[#EDF5F2]/60 mb-8 leading-relaxed max-w-2xl mx-auto">
                Enterprise sanctions screening without the enterprise price tag. Check parties, vessels, 
                and goods against OFAC, EU, UN, and 50+ global sanctions lists.
              </p>

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-[#EDF5F2]/60 mb-12">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  OFAC SDN + Sectoral
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  EU 14 Russia Packages
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  Vessel Dark Activity
                </div>
              </div>
            </div>

            {/* Screening Type Cards */}
            <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
              {screeningTypes.map((type) => (
                <div key={type.id} className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 hover:border-[#B2F273]/30 transition-all group backdrop-blur-sm">
                  <div className="w-12 h-12 bg-[#B2F273]/10 rounded-lg flex items-center justify-center mb-4 border border-[#B2F273]/20 group-hover:bg-[#B2F273] transition-colors">
                    <type.icon className="w-6 h-6 text-[#B2F273] group-hover:text-[#00261C] transition-colors" />
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2 font-display">{type.title}</h3>
                  <p className="text-[#EDF5F2]/60 text-sm mb-4">{type.description}</p>
                  <Button className="w-full bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
                    <Link to={type.to}>
                      Start Screening <ArrowRight className="w-4 h-4 ml-2" />
                    </Link>
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Stats */}
        <section className="relative py-12 bg-[#00261C] border-y border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto">
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
                Enterprise Tools at Enterprise Prices?{" "}
                <span className="text-[#B2F273]">Not Anymore.</span>
              </h2>
              
              <div className="grid md:grid-cols-2 gap-8">
                <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 backdrop-blur-sm">
                  <h3 className="text-lg font-bold text-white mb-4 font-display">Without TRDR</h3>
                  <ul className="space-y-3 text-[#EDF5F2]/60">
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Dow Jones/World-Check costs $10K+/year
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Manual Google searches miss aliases
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Vessel screening requires separate tools
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      No audit trail for compliance
                    </li>
                  </ul>
                </div>
                <div className="bg-[#B2F273]/5 border border-[#B2F273]/20 rounded-xl p-6 backdrop-blur-sm">
                  <h3 className="text-lg font-bold text-white mb-4 font-display">With TRDR</h3>
                  <ul className="space-y-3 text-[#EDF5F2]/60">
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Starting at $29/month (not $10K)
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Fuzzy matching catches 98% of variations
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Party + vessel + goods in one tool
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Downloadable compliance certificates
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
                Screen in Three Steps
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                No training required. No complex setup. Just type and screen.
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
                Comprehensive Sanctions Coverage
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                More lists, better matching, faster results than tools costing 10x more.
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
                Simple, Transparent Pricing
              </h2>
              <p className="text-[#EDF5F2]/60">
                Start free. Upgrade when you need more.
              </p>
            </div>

            <div className="grid md:grid-cols-4 gap-6 max-w-5xl mx-auto">
              {pricing.map((plan, idx) => (
                <div key={idx} className={cn(
                  "bg-[#00382E]/50 border rounded-xl p-6 text-center backdrop-blur-sm",
                  plan.popular ? "border-[#B2F273] shadow-[0_0_20px_rgba(178,242,115,0.1)]" : "border-[#EDF5F2]/10"
                )}>
                  {plan.popular && (
                    <span className="text-xs text-[#B2F273] font-mono uppercase tracking-wider font-medium">MOST POPULAR</span>
                  )}
                  <h3 className="text-lg font-bold text-white mt-2 font-display">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4 font-display">{plan.price}</div>
                  <p className="text-[#EDF5F2]/60 text-sm mb-2">{plan.screens} screens/mo</p>
                  <p className="text-[#EDF5F2]/40 text-xs">{plan.description}</p>
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
                Don't Risk Sanctions Violations
              </h2>
              <p className="text-lg text-[#EDF5F2]/60 mb-8">
                Screen every party, every vessel, every transaction. Start free today.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
                  <Link to="/sanctions/dashboard">
                    Start Free Screening <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button variant="outline" size="lg" className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 bg-transparent" asChild>
                  <Link to="/contact">Request Demo</Link>
                </Button>
              </div>
            </div>
          </div>
        </section>
      </main>

      <TRDRFooter />
    </div>
  );
};

export default SanctionsScreenerLanding;

