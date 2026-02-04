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
                Know If You Need an{" "}
                <span className="text-[#B2F273] text-glow-sm">Export License</span>
              </h1>
              
              <p className="text-lg text-[#EDF5F2]/60 mb-8 leading-relaxed max-w-2xl mx-auto">
                Screen goods against EAR, EU 2021/821, Wassenaar, and other export control regimes. 
                Get ECCN classification and license guidance before you ship.
              </p>

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-[#EDF5F2]/60 mb-12">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  6 Control Regimes
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  10,000+ Items
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  License Guidance
                </div>
              </div>
            </div>

            {/* Search Box */}
            <div className="max-w-2xl mx-auto">
              <div className="bg-[#00382E]/80 border border-[#EDF5F2]/10 rounded-2xl p-6 backdrop-blur-md shadow-xl">
                <p className="text-[#EDF5F2]/60 text-sm mb-4">Describe your product or enter HS code:</p>
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder="e.g., CNC milling machine, 5-axis, for aerospace components"
                    value={productDesc}
                    onChange={(e) => setProductDesc(e.target.value)}
                    className="flex-1 bg-[#00261C] border border-[#EDF5F2]/10 rounded-lg px-4 py-3 text-white placeholder-[#EDF5F2]/30 focus:outline-none focus:border-[#B2F273]/50 transition-colors"
                  />
                  <Button className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] px-6 font-bold" asChild>
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
        <section className="relative py-12 bg-[#00261C] border-y border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 max-w-5xl mx-auto">
              {controlRegimes.map((regime, idx) => (
                <div key={idx} className="text-center p-4 bg-[#00382E]/50 rounded-xl border border-[#EDF5F2]/10 backdrop-blur-sm">
                  <div className="text-white font-bold text-sm mb-1 font-display">{regime.name}</div>
                  <div className="text-[#EDF5F2]/60 text-xs">{regime.description}</div>
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
                Export Violations Mean{" "}
                <span className="text-[#B2F273]">Criminal Penalties</span>
              </h2>
              
              <div className="grid md:grid-cols-2 gap-8">
                <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 backdrop-blur-sm">
                  <h3 className="text-lg font-bold text-white mb-4 font-display">The Risks</h3>
                  <ul className="space-y-3 text-[#EDF5F2]/60">
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
                <div className="bg-[#B2F273]/5 border border-[#B2F273]/20 rounded-xl p-6 backdrop-blur-sm">
                  <h3 className="text-lg font-bold text-white mb-4 font-display">With Dual-Use Checker</h3>
                  <ul className="space-y-3 text-[#EDF5F2]/60">
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Pre-shipment classification
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      License requirement clarity
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      End-user screening
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Audit trail for compliance
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
                Classification in Three Steps
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                Get export control classification before you quote or ship.
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
                Comprehensive Export Control Coverage
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                All major control regimes, license guidance, and end-use screening.
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
                Pay per classification or subscribe for volume.
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
                  <p className="text-[#EDF5F2]/60 text-sm mb-4">{plan.checks}</p>
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
                    <Link to="/waitlist?tool=dual-use">Join Waitlist</Link>
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
                Export with Confidence
              </h2>
              <p className="text-lg text-[#EDF5F2]/60 mb-8">
                Know your export control obligations before you ship.
              </p>
              <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
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
