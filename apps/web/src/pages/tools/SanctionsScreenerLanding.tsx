import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, Shield, Zap, Globe, Search, AlertTriangle, Clock, Database, RefreshCw, Building2, Ship } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";

const features = [
  {
    icon: Database,
    title: "OFAC, EU, UN, UK Lists",
    description: "Screen against all major sanctions lists including OFAC SDN, EU Consolidated, UN Security Council, and UK OFSI.",
    bullets: ["OFAC SDN & Sectoral", "EU 14 Russia packages", "UN 1718 DPRK sanctions"],
  },
  {
    icon: RefreshCw,
    title: "Real-Time Updates",
    description: "Lists are updated within hours of official publication. Never screen against stale data.",
    bullets: ["Daily list synchronization", "Alert on list changes", "Historical screening available"],
  },
  {
    icon: Ship,
    title: "Vessel & Port Screening",
    description: "Screen vessels against sanctioned flags, ownership chains, and AIS dark activity patterns.",
    bullets: ["IMO number lookup", "Flag state verification", "Port call history check"],
  },
  {
    icon: Building2,
    title: "Party Name Matching",
    description: "Fuzzy matching catches spelling variations, transliterations, and aliases that exact matching misses.",
    bullets: ["Multi-language support", "Alias database", "Phonetic matching"],
  },
  {
    icon: AlertTriangle,
    title: "Dual-Use Goods Check",
    description: "Screen goods descriptions against export control lists including EAR, EU 2021/821, and Wassenaar.",
    bullets: ["HS code classification", "ECCN lookup", "End-use screening"],
  },
  {
    icon: Zap,
    title: "Instant Results",
    description: "Get screening results in under 2 seconds. Batch screening available for bulk operations.",
    bullets: ["Single & batch modes", "API access available", "PDF reports"],
  },
];

const stats = [
  { value: "50+", label: "Sanctions Lists" },
  { value: "<2s", label: "Screening Time" },
  { value: "99.9%", label: "Uptime" },
  { value: "24/7", label: "Updates" },
];

const SanctionsScreenerLanding = () => {
  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      
      <main>
        {/* Hero Section */}
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-red-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-orange-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-red-500/10 border border-red-500/20 mb-6">
                <Shield className="w-4 h-4 text-red-400" />
                <span className="text-red-400 text-sm font-medium">Compliance Tool</span>
              </div>
              
              <h1 className="text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                Screen Parties & Goods Against{" "}
                <span className="bg-gradient-to-r from-red-400 to-orange-400 bg-clip-text text-transparent">Global Sanctions</span>
              </h1>
              
              <p className="text-lg text-slate-400 mb-8 leading-relaxed max-w-2xl mx-auto">
                Real-time screening against OFAC, EU, UN, and UK sanctions lists. Catch sanctioned entities, 
                vessels, and controlled goods before they become compliance violations.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
                <Button size="lg" className="bg-red-500 hover:bg-red-600 text-white font-semibold" asChild>
                  <Link to="/sanctions/screen">
                    Start Screening <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button variant="outline" size="lg" className="border-slate-700 text-slate-300 hover:bg-slate-800" asChild>
                  <Link to="/contact">Request Demo</Link>
                </Button>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-slate-400">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  OFAC Compliant
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  Real-Time Updates
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  API Access
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
                  <div className="text-3xl md:text-4xl font-bold text-white mb-1">{stat.value}</div>
                  <div className="text-sm text-slate-500">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                Comprehensive Sanctions Coverage
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Screen against 50+ global sanctions lists with intelligent matching that catches what others miss.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature, idx) => (
                <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 hover:border-red-500/30 transition-colors">
                  <div className="w-12 h-12 bg-red-500/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-red-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((bullet, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-500">
                        <CheckCircle className="w-4 h-4 text-red-500" />
                        {bullet}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
                Don't Risk Sanctions Violations
              </h2>
              <p className="text-lg text-slate-400 mb-8">
                Screen every party, every vessel, every transaction. Free to start.
              </p>
              <Button size="lg" className="bg-white text-slate-900 hover:bg-slate-100 font-semibold" asChild>
                <Link to="/sanctions/screen">
                  Start Free Screening <ArrowRight className="w-5 h-5 ml-2" />
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

export default SanctionsScreenerLanding;

