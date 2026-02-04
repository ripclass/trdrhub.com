import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, Globe, Clock, FileText, AlertTriangle, ChevronDown, Search, Building2, Shield, BookOpen, Bell, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const features = [
  {
    icon: Globe,
    title: "Country Requirements",
    description: "Import requirements for 190+ countries. Know what's needed before you ship.",
    bullets: ["Documentation checklist", "Regulatory requirements", "Prohibited items list", "Country-specific rules"],
  },
  {
    icon: FileText,
    title: "Document Templates",
    description: "Pre-approved document templates for each country. Formatted correctly the first time.",
    bullets: ["Import declarations", "Certificate formats", "Permit applications", "Attestation forms"],
  },
  {
    icon: Shield,
    title: "License & Permit Lookup",
    description: "Know if your product needs import licenses, permits, or special approvals.",
    bullets: ["License requirements", "Permit types", "Application process", "Processing times"],
  },
  {
    icon: AlertTriangle,
    title: "Product Restrictions",
    description: "Check if your product faces restrictions, quotas, or special requirements.",
    bullets: ["Restricted goods list", "Quota status", "Labeling requirements", "Testing/certification"],
  },
  {
    icon: Bell,
    title: "Regulatory Alerts",
    description: "Get notified when import rules change. Never be caught by surprise.",
    bullets: ["Rule change alerts", "New restrictions", "Fee updates", "Process changes"],
  },
  {
    icon: Users,
    title: "Broker Directory",
    description: "Find vetted customs brokers in your destination country.",
    bullets: ["Broker ratings", "Specialty areas", "Contact info", "Fee estimates"],
  },
];

const popularCountries = [
  { code: "US", name: "United States" },
  { code: "EU", name: "European Union" },
  { code: "CN", name: "China" },
  { code: "IN", name: "India" },
  { code: "JP", name: "Japan" },
  { code: "AU", name: "Australia" },
];

const process = [
  {
    step: "1",
    title: "Select Country",
    description: "Choose your import destination from 190+ countries",
  },
  {
    step: "2",
    title: "Enter Product",
    description: "Describe your goods or enter HS code",
  },
  {
    step: "3",
    title: "Get Requirements",
    description: "Documents, licenses, permits, and restrictions",
  },
];

const stats = [
  { value: "190+", label: "Countries" },
  { value: "10,000+", label: "Product Rules" },
  { value: "Daily", label: "Updates" },
  { value: "500+", label: "Brokers" },
];

const pricing = [
  { tier: "Free", lookups: "5/mo", price: "$0", description: "Basic requirements", features: ["Country overview", "Basic docs list", "1 country"] },
  { tier: "Professional", lookups: "50/mo", price: "$49/mo", description: "For importers", features: ["All countries", "Product-specific rules", "License lookup", "Alerts"], popular: true },
  { tier: "Enterprise", lookups: "Unlimited", price: "$149/mo", description: "For freight/3PL", features: ["Everything in Pro", "Broker directory", "API access", "Custom alerts"] },
];

const faqs = [
  {
    q: "How many countries do you cover?",
    a: "We cover 190+ countries with varying depth. Major markets (US, EU, China, India, Japan) have comprehensive coverage including product-specific rules. Smaller markets have general import requirements.",
  },
  {
    q: "How current is the information?",
    a: "We update requirements daily from official sources (customs authorities, trade ministries). Major rule changes are reflected within 24-48 hours. Subscribe to alerts for your markets.",
  },
  {
    q: "Can I check product-specific requirements?",
    a: "Yes! Enter your HS code or product description to get requirements specific to your goods, including any licenses, permits, testing, labeling, or certification requirements.",
  },
  {
    q: "Do you provide customs broker recommendations?",
    a: "Professional and Enterprise plans include access to our vetted broker directory with ratings, specialties, and contact information for brokers in each country.",
  },
  {
    q: "Is this a replacement for a customs broker?",
    a: "No, CustomsMate is an information tool. For actual customs clearance, you still need a licensed broker. We help you understand requirements and find qualified brokers.",
  },
];

const CustomsMateLanding = () => {
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
                <span className="text-[#B2F273] text-sm font-medium">Coming Q2 2025</span>
              </div>
              
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight font-display">
                Import Requirements for{" "}
                <span className="text-[#B2F273] text-glow-sm">Any Country</span>
              </h1>
              
              <p className="text-lg text-[#EDF5F2]/60 mb-8 leading-relaxed max-w-2xl mx-auto">
                Know exactly what's needed for customs clearance. Documents, licenses, permits, 
                and restrictions for 190+ countries. Never get stopped at customs again.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
                <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
                  <Link to="/waitlist?tool=customs">
                    Join Waitlist <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button variant="outline" size="lg" className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 bg-transparent" asChild>
                  <Link to="/contact">Request Demo</Link>
                </Button>
              </div>

              {/* Popular Countries */}
              <div className="flex flex-wrap items-center justify-center gap-3 mt-8">
                <span className="text-[#EDF5F2]/60 text-sm">Popular:</span>
                {popularCountries.map((country, idx) => (
                  <span key={idx} className="px-3 py-1 bg-[#00382E]/50 rounded-full text-[#B2F273] text-sm border border-[#B2F273]/20">
                    {country.name}
                  </span>
                ))}
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

        {/* How It Works */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
                Requirements in Three Steps
              </h2>
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
                Everything for Customs Clearance
              </h2>
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
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">Simple Pricing</h2>
            </div>

            <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {pricing.map((plan, idx) => (
                <div key={idx} className={cn(
                  "bg-[#00382E]/50 border rounded-xl p-6 backdrop-blur-sm",
                  plan.popular ? "border-[#B2F273] shadow-[0_0_20px_rgba(178,242,115,0.1)]" : "border-[#EDF5F2]/10"
                )}>
                  {plan.popular && <span className="text-xs text-[#B2F273] font-mono uppercase tracking-wider font-medium">MOST POPULAR</span>}
                  <h3 className="text-lg font-bold text-white mt-2 font-display">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4 font-display">{plan.price}</div>
                  <p className="text-[#EDF5F2]/60 text-sm mb-4">{plan.lookups} lookups</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-[#EDF5F2]/50">
                        <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Button className={cn("w-full font-bold border-none", plan.popular ? "bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C]" : "bg-[#EDF5F2]/10 hover:bg-[#EDF5F2]/20 text-white")} asChild>
                    <Link to="/waitlist?tool=customs">Join Waitlist</Link>
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
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white text-center mb-12 font-display">FAQ</h2>
              <div className="space-y-4">
                {faqs.map((faq, idx) => (
                  <div key={idx} className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl overflow-hidden backdrop-blur-sm">
                    <button className="w-full px-6 py-4 text-left flex items-center justify-between" onClick={() => setOpenFaq(openFaq === idx ? null : idx)}>
                      <span className="text-white font-medium font-display">{faq.q}</span>
                      <ChevronDown className={cn("w-5 h-5 text-[#EDF5F2]/40 transition-transform shrink-0 ml-4", openFaq === idx && "rotate-180")} />
                    </button>
                    {openFaq === idx && <div className="px-6 pb-4"><p className="text-[#EDF5F2]/60 text-sm leading-relaxed">{faq.a}</p></div>}
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
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-6 font-display">Clear Customs Without Surprises</h2>
              <p className="text-lg text-[#EDF5F2]/60 mb-8">Know the requirements before you ship.</p>
              <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
                <Link to="/waitlist?tool=customs">Join Waitlist <ArrowRight className="w-5 h-5 ml-2" /></Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      <TRDRFooter />
    </div>
  );
};

export default CustomsMateLanding;
