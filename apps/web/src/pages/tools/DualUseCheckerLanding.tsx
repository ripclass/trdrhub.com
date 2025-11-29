import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, Shield, Clock, AlertTriangle, FileText, Globe, ChevronDown, Search, Scale, Lock, Eye, Ban, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const features = [
  {
    icon: Scale,
    title: "EAR/ECCN Classification",
    description: "Screen goods against the US Export Administration Regulations. Get ECCN classification and license requirements.",
    bullets: ["ECCN lookup", "EAR99 determination", "License exception check", "De minimis calculations"],
  },
  {
    icon: Globe,
    title: "EU Dual-Use Screening",
    description: "Check against EU 2021/821 dual-use regulation. Get control list classification for EU exports.",
    bullets: ["Annex I categories", "Control list numbers", "Catch-all provisions", "National control lists"],
  },
  {
    icon: BookOpen,
    title: "Wassenaar Categories",
    description: "Classify against Wassenaar Arrangement categories for conventional arms and dual-use items.",
    bullets: ["10 category system", "Munitions list", "Sensitive items", "Very sensitive items"],
  },
  {
    icon: FileText,
    title: "License Determination",
    description: "Know if you need an export license before you ship. Get guidance on license types and exemptions.",
    bullets: ["License required Y/N", "License exception eligibility", "NLR guidance", "Deemed export rules"],
  },
  {
    icon: Eye,
    title: "End-Use Screening",
    description: "Screen end-users, end-uses, and ultimate consignees against restricted activities.",
    bullets: ["Military end-use", "Nuclear end-use", "WMD proliferation", "Red flag indicators"],
  },
  {
    icon: Ban,
    title: "Denied Parties Check",
    description: "Screen against BIS Entity List, Denied Persons List, and Unverified List.",
    bullets: ["Entity List", "Denied Persons", "Unverified List", "Military End-User List"],
  },
];

const controlRegimes = [
  { name: "EAR (US)", description: "Export Administration Regulations" },
  { name: "EU 2021/821", description: "EU Dual-Use Regulation" },
  { name: "Wassenaar", description: "Conventional Arms & Dual-Use" },
  { name: "MTCR", description: "Missile Technology" },
  { name: "NSG", description: "Nuclear Suppliers Group" },
  { name: "CWC", description: "Chemical Weapons" },
];

const process = [
  {
    step: "1",
    title: "Describe Your Product",
    description: "Enter product description, HS code, or technical specifications",
  },
  {
    step: "2",
    title: "Select Destination",
    description: "Choose export destination and end-user details",
  },
  {
    step: "3",
    title: "Get Classification",
    description: "Receive ECCN, control list classification, and license guidance",
  },
];

const stats = [
  { value: "6", label: "Control Regimes" },
  { value: "10,000+", label: "Controlled Items" },
  { value: "240+", label: "Destinations" },
  { value: "<30s", label: "Classification" },
];

const pricing = [
  { tier: "Starter", checks: "25 checks/mo", price: "$49/mo", description: "For occasional exporters", features: ["Basic classification", "EAR screening", "PDF reports"] },
  { tier: "Professional", checks: "100 checks/mo", price: "$149/mo", description: "For regular exporters", features: ["All control regimes", "License guidance", "End-use screening", "API access"], popular: true },
  { tier: "Enterprise", checks: "Unlimited", price: "$399/mo", description: "For manufacturers", features: ["Everything in Pro", "Product library", "Bulk classification", "Compliance dashboard"] },
];

const faqs = [
  {
    q: "What export control regimes do you cover?",
    a: "We cover EAR (US), EU 2021/821, Wassenaar Arrangement, MTCR, NSG, CWC, and Australia Group. We also include national control lists for major exporting countries.",
  },
  {
    q: "How accurate is the classification?",
    a: "Our AI classification achieves 90%+ accuracy for common items. Complex items may require human review. We always recommend confirming critical classifications with your export compliance counsel.",
  },
  {
    q: "Can you help with license applications?",
    a: "We provide guidance on license requirements and exemptions. Actual license applications must be filed with the relevant authority (BIS, BAFA, etc.). Enterprise plans include consultation support.",
  },
  {
    q: "Do you cover deemed exports?",
    a: "Yes, we help identify deemed export situations (technology transfers to foreign nationals) and provide guidance on license requirements for deemed exports.",
  },
  {
    q: "How do you handle catch-all controls?",
    a: "We screen for catch-all triggers including military end-use, WMD end-use, and embargoed destinations. We flag items that may require a license even if not on a control list.",
  },
];

const DualUseCheckerLanding = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [productDesc, setProductDesc] = useState("");

  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      
      <main>
        {/* Hero Section */}
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-red-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-rose-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center mb-12">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 mb-6">
                <Clock className="w-4 h-4 text-amber-400" />
                <span className="text-amber-400 text-sm font-medium">Coming Q2 2025</span>
              </div>
              
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                Know If You Need an{" "}
                <span className="bg-gradient-to-r from-red-400 to-rose-400 bg-clip-text text-transparent">Export License</span>
              </h1>
              
              <p className="text-lg text-slate-400 mb-8 leading-relaxed max-w-2xl mx-auto">
                Screen goods against EAR, EU 2021/821, Wassenaar, and other export control regimes. 
                Get ECCN classification and license guidance before you ship.
              </p>

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-slate-400 mb-12">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  6 Control Regimes
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  10,000+ Items
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  License Guidance
                </div>
              </div>
            </div>

            {/* Search Box */}
            <div className="max-w-2xl mx-auto">
              <div className="bg-slate-900/80 border border-slate-700 rounded-2xl p-6 backdrop-blur">
                <p className="text-slate-400 text-sm mb-4">Describe your product or enter HS code:</p>
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder="e.g., CNC milling machine, 5-axis, for aerospace components"
                    value={productDesc}
                    onChange={(e) => setProductDesc(e.target.value)}
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-red-500 transition-colors"
                  />
                  <Button className="bg-red-500 hover:bg-red-600 px-6" asChild>
                    <Link to="/waitlist?tool=dual-use">
                      <Search className="w-5 h-5" />
                    </Link>
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Control Regimes */}
        <section className="py-12 bg-slate-900 border-y border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 max-w-5xl mx-auto">
              {controlRegimes.map((regime, idx) => (
                <div key={idx} className="text-center p-4 bg-slate-800/50 rounded-xl border border-slate-700">
                  <div className="text-white font-medium text-sm mb-1">{regime.name}</div>
                  <div className="text-slate-500 text-xs">{regime.description}</div>
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
                Export Violations Mean{" "}
                <span className="text-red-400">Criminal Penalties</span>
              </h2>
              
              <div className="grid md:grid-cols-2 gap-8">
                <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">The Risks</h3>
                  <ul className="space-y-3 text-slate-400">
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      $1M+ fines per violation
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Criminal prosecution possible
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Export privileges revoked
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Reputational damage
                    </li>
                  </ul>
                </div>
                <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">With Dual-Use Checker</h3>
                  <ul className="space-y-3 text-slate-400">
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Pre-shipment classification
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      License requirement clarity
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      End-user screening
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Audit trail for compliance
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
                Classification in Three Steps
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Get export control classification before you quote or ship.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              {process.map((step, idx) => (
                <div key={idx} className="text-center">
                  <div className="w-12 h-12 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-red-500/20">
                    <span className="text-red-400 font-bold">{step.step}</span>
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
                Comprehensive Export Control Coverage
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                All major control regimes, license guidance, and end-use screening.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature, idx) => (
                <div key={idx} className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 hover:border-red-500/30 transition-colors">
                  <div className="w-12 h-12 bg-red-500/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-red-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((bullet, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-500">
                        <CheckCircle className="w-4 h-4 text-red-500 shrink-0" />
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
                Pay per classification or subscribe for volume.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {pricing.map((plan, idx) => (
                <div key={idx} className={cn(
                  "bg-slate-900/50 border rounded-xl p-6",
                  plan.popular ? "border-red-500/50 bg-red-500/5" : "border-slate-800"
                )}>
                  {plan.popular && (
                    <span className="text-xs text-red-400 font-medium">MOST POPULAR</span>
                  )}
                  <h3 className="text-lg font-semibold text-white mt-2">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4">{plan.price}</div>
                  <p className="text-slate-400 text-sm mb-4">{plan.checks}</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-400">
                        <CheckCircle className="w-4 h-4 text-red-500" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Button className={cn(
                    "w-full",
                    plan.popular ? "bg-red-500 hover:bg-red-600" : "bg-slate-700 hover:bg-slate-600"
                  )} asChild>
                    <Link to="/waitlist?tool=dual-use">Join Waitlist</Link>
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
                Export with Confidence
              </h2>
              <p className="text-lg text-slate-400 mb-8">
                Know your export control obligations before you ship.
              </p>
              <Button size="lg" className="bg-red-500 hover:bg-red-600 text-white font-semibold" asChild>
                <Link to="/waitlist?tool=dual-use">
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

export default DualUseCheckerLanding;

