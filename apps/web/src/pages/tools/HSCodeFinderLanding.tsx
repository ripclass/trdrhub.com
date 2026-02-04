import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, Calculator, Search, Globe, DollarSign, FileText, BookOpen, Shield, ChevronDown, Brain, History, Star, Package, Scale } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const features = [
  {
    icon: Brain,
    title: "AI-Powered Classification",
    description: "Describe your product in plain language. Our AI finds the correct HS code with duty rates and restrictions.",
    bullets: ["Natural language input", "Multi-language support", "98% classification accuracy", "Confidence scoring"],
  },
  {
    icon: Globe,
    title: "100+ Country Schedules",
    description: "Get the right code for your destination. US HTS, EU TARIC, UK Tariff, Singapore, and more.",
    bullets: ["US HTS 10-digit codes", "EU TARIC codes", "UK Trade Tariff", "Country-specific duties"],
  },
  {
    icon: DollarSign,
    title: "Instant Duty Calculator",
    description: "Know your landed cost before you ship. MFN rates, preferential rates, and FTA savings.",
    bullets: ["MFN rates by country", "FTA preference finder", "Landed cost estimate", "Anti-dumping duties"],
  },
  {
    icon: Shield,
    title: "FTA Eligibility Check",
    description: "Check if your product qualifies for preferential treatment under RCEP, CPTPP, USMCA, and 50+ FTAs.",
    bullets: ["Rules of origin check", "Cumulation rules", "Required documentation", "Savings calculator"],
  },
  {
    icon: FileText,
    title: "Restrictions & Controls",
    description: "Know if your product needs licenses, permits, or faces quotas before you ship.",
    bullets: ["Import licenses required", "Quota status check", "Restrictions alerts", "Export controls"],
  },
  {
    icon: History,
    title: "Classification History",
    description: "Save and track your classifications. Export for customs brokers and compliance audits.",
    bullets: ["Classification archive", "PDF export", "Share with team", "Audit trail included"],
  },
];

const process = [
  {
    step: "1",
    title: "Describe Your Product",
    description: "Type a description like 'cotton t-shirts for men' or paste your existing HS code to verify",
  },
  {
    step: "2",
    title: "Select Countries",
    description: "Choose your import destination and export origin for accurate duty rates and FTA eligibility",
  },
  {
    step: "3",
    title: "Get Full Details",
    description: "HS code, duty rates, FTA eligibility, restrictions, and required documents - all in one view",
  },
];

const stats = [
  { value: "98%", label: "Accuracy" },
  { value: "100+", label: "Countries" },
  { value: "<5s", label: "Classification" },
  { value: "Free", label: "To Start" },
];

const popularSearches = [
  "Cotton t-shirts",
  "Electronics",
  "Machinery parts",
  "Food products",
  "Chemicals",
  "Auto parts",
];

const pricing = [
  { tier: "Free", lookups: "Unlimited basic", price: "$0", description: "HS codes + MFN rates", features: ["Basic HS lookup", "MFN duty rates", "Single country"] },
  { tier: "Pro", lookups: "Unlimited", price: "$49/mo", description: "Full classification", features: ["AI classification", "100+ countries", "FTA calculator", "PDF export"], popular: true },
  { tier: "Team", lookups: "Unlimited", price: "$149/mo", description: "For trade teams", features: ["Everything in Pro", "5 users", "Classification history", "API access"] },
];

const faqs = [
  {
    q: "How accurate is the AI classification?",
    a: "Our AI achieves 98% accuracy on first suggestion. For complex products, we provide multiple candidate codes ranked by confidence. We recommend reviewing the classification with your customs broker for high-value or novel products.",
  },
  {
    q: "Which countries' tariff schedules do you support?",
    a: "We support 100+ countries including US (HTS), EU (TARIC), UK, China, Japan, India, Australia, Singapore, and more. Each country schedule is updated when the WCO releases amendments.",
  },
  {
    q: "Can I check FTA eligibility?",
    a: "Yes! Select your origin and destination countries, and we'll show you which FTAs apply, the preferential duty rate, rules of origin requirements, and required documentation (Form A, EUR.1, etc.).",
  },
  {
    q: "Is this free to use?",
    a: "Yes, basic search is 100% free - no sign-up required. Free tier includes HS code lookup and MFN duty rates for any single country. Paid plans add AI classification, multi-country comparison, FTA calculator, and classification history.",
  },
  {
    q: "How often are duty rates updated?",
    a: "We sync duty rates monthly with official sources (US ITC, EU TARIC, etc.). FTA rates and preferential programs are updated as changes are published. Anti-dumping and countervailing duties are updated within 48 hours of publication.",
  },
  {
    q: "Can I use this for customs declarations?",
    a: "TRDR HS Code Finder provides classification suggestions and duty rate estimates. Final classification for customs declarations should be verified with your licensed customs broker or through official binding ruling processes.",
  },
];

const HSCodeFinderLanding = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

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
                <Star className="w-4 h-4 text-[#B2F273]" />
                <span className="text-[#B2F273] text-sm font-medium">100% Free Tool</span>
              </div>
              
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight font-display">
                Find the Right{" "}
                <span className="text-[#B2F273] text-glow-sm">HS Code</span>{" "}
                in Seconds
              </h1>
              
              <p className="text-lg text-[#EDF5F2]/60 mb-8 leading-relaxed max-w-2xl mx-auto">
                Stop guessing tariff codes. Our AI classifies your products with duty rates, FTA eligibility, 
                and import restrictions for 100+ countries. Free, instant, accurate.
              </p>

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-[#EDF5F2]/60 mb-12">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  100% Free
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  No Sign-Up Required
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  Instant Results
                </div>
              </div>
            </div>

            {/* Search Box */}
            <div className="max-w-2xl mx-auto">
              <div className="bg-[#00382E]/80 border border-[#EDF5F2]/10 rounded-2xl p-6 backdrop-blur-md shadow-xl">
                <p className="text-[#EDF5F2]/60 text-sm mb-4">Describe your product in plain language:</p>
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder="e.g., Cotton t-shirts for men, made in Bangladesh"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="flex-1 bg-[#00261C] border border-[#EDF5F2]/10 rounded-lg px-4 py-3 text-white placeholder-[#EDF5F2]/30 focus:outline-none focus:border-[#B2F273]/50 transition-colors"
                  />
                  <Button className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] px-6 font-bold" asChild>
                    <Link to={`/hs-code/search?q=${encodeURIComponent(searchQuery)}`}>
                      <Search className="w-5 h-5" />
                    </Link>
                  </Button>
                </div>
                <div className="mt-4 flex flex-wrap gap-2 items-center">
                  <span className="text-xs text-[#EDF5F2]/40">Popular:</span>
                  {popularSearches.map((term, idx) => (
                    <button 
                      key={idx}
                      onClick={() => setSearchQuery(term)}
                      className="text-xs text-[#B2F273] hover:text-[#a3e662] hover:underline transition-colors"
                    >
                      {term}
                    </button>
                  ))}
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
                HS Code Classification is{" "}
                <span className="text-[#B2F273]">Confusing</span>
              </h2>
              
              <div className="grid md:grid-cols-2 gap-8 mb-12">
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <span className="text-red-400 mt-1">✗</span>
                    <div>
                      <p className="text-white font-medium">5,000+ codes to choose from</p>
                      <p className="text-[#EDF5F2]/60 text-sm">Complex hierarchy, overlapping categories, endless notes</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-red-400 mt-1">✗</span>
                    <div>
                      <p className="text-white font-medium">Wrong code = wrong duties</p>
                      <p className="text-[#EDF5F2]/60 text-sm">Overpay or face penalties and delays for underpayment</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-red-400 mt-1">✗</span>
                    <div>
                      <p className="text-white font-medium">Codes differ by country</p>
                      <p className="text-[#EDF5F2]/60 text-sm">6-digit WCO → 8/10-digit national codes with different rules</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-red-400 mt-1">✗</span>
                    <div>
                      <p className="text-white font-medium">FTA savings left on the table</p>
                      <p className="text-[#EDF5F2]/60 text-sm">Most traders don't know which FTAs apply or how to qualify</p>
                    </div>
                  </div>
                </div>
                <div className="bg-[#B2F273]/5 border border-[#B2F273]/20 rounded-xl p-6 backdrop-blur-sm">
                  <h3 className="text-lg font-bold text-white mb-4 font-display">TRDR HS Code Finder solves this</h3>
                  <ul className="space-y-3 text-[#EDF5F2]/60">
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Describe products in plain language
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      AI suggests best matches with confidence scores
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      See duty rates for any country instantly
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Check FTA eligibility and save thousands
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Know restrictions before you ship
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
                Classification in Three Steps
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                No training required. No customs expertise needed. Just type and get results.
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
                More Than Just HS Codes
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                Get duty rates, FTA eligibility, and import restrictions - everything for customs clearance.
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
                Free Forever, Upgrade for More
              </h2>
              <p className="text-[#EDF5F2]/60">
                Basic HS code lookup is always free. Pay only for advanced features.
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
                    <Link to="/hs-code/dashboard">Get Started</Link>
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
                Stop Guessing HS Codes
              </h2>
              <p className="text-lg text-[#EDF5F2]/60 mb-8">
                Free, instant, accurate. The way tariff classification should be.
              </p>
              <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
                <Link to="/hs-code/dashboard">
                  Start Classifying Free <ArrowRight className="w-5 h-5 ml-2" />
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

export default HSCodeFinderLanding;
