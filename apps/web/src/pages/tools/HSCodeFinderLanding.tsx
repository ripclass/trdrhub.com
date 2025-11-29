import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, Calculator, Search, Globe, DollarSign, FileText, Zap, BookOpen, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";

const features = [
  {
    icon: Search,
    title: "AI-Powered Classification",
    description: "Describe your product in plain language. Our AI finds the correct HS code with duty rates and restrictions.",
    bullets: ["Natural language input", "Multi-language support", "99% classification accuracy"],
  },
  {
    icon: Globe,
    title: "Country-Specific Codes",
    description: "Get the right code for your destination. US HTS, EU TARIC, UK Tariff, and 100+ country schedules.",
    bullets: ["US HTS 10-digit", "EU TARIC codes", "Country-specific duties"],
  },
  {
    icon: DollarSign,
    title: "Duty Rate Calculator",
    description: "Instant duty rates with MFN, preferential, and FTA rates. Know your landed cost before you ship.",
    bullets: ["MFN rates", "FTA preferences", "Landed cost estimate"],
  },
  {
    icon: FileText,
    title: "FTA Eligibility Check",
    description: "Check if your product qualifies for preferential treatment under RCEP, CPTPP, USMCA, and 50+ FTAs.",
    bullets: ["Rules of origin", "Cumulation rules", "Documentation required"],
  },
  {
    icon: Shield,
    title: "Restrictions & Controls",
    description: "Know if your product needs licenses, permits, or faces quotas before you ship.",
    bullets: ["Import licenses", "Quota status", "Anti-dumping duties"],
  },
  {
    icon: BookOpen,
    title: "Classification History",
    description: "Save and track your classifications. Export for customs brokers and compliance audits.",
    bullets: ["Classification archive", "PDF export", "Audit trail"],
  },
];

const stats = [
  { value: "98%", label: "Accuracy" },
  { value: "100+", label: "Countries" },
  { value: "<5s", label: "Classification" },
  { value: "Free", label: "To Start" },
];

const HSCodeFinderLanding = () => {
  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      
      <main>
        {/* Hero Section */}
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-purple-500/10 border border-purple-500/20 mb-6">
                <Calculator className="w-4 h-4 text-purple-400" />
                <span className="text-purple-400 text-sm font-medium">Free Tool</span>
              </div>
              
              <h1 className="text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                Find the Right{" "}
                <span className="bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">HS Code</span>{" "}
                in Seconds
              </h1>
              
              <p className="text-lg text-slate-400 mb-8 leading-relaxed max-w-2xl mx-auto">
                Stop guessing tariff codes. Our AI classifies your products with duty rates, FTA eligibility, 
                and import restrictions for 100+ countries.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
                <Button size="lg" className="bg-purple-500 hover:bg-purple-600 text-white font-semibold" asChild>
                  <Link to="/hs-code/search">
                    Find HS Code <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button variant="outline" size="lg" className="border-slate-700 text-slate-300 hover:bg-slate-800" asChild>
                  <Link to="/hs-code/bulk">Bulk Classification</Link>
                </Button>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-slate-400">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  100% Free
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  No Sign-Up Required
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  Instant Results
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Example Search */}
        <section className="py-12 bg-slate-900 border-y border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-2xl mx-auto">
              <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
                <p className="text-slate-400 text-sm mb-4">Try it now - describe your product:</p>
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder="e.g., Cotton t-shirts for men, made in Bangladesh"
                    className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
                  />
                  <Button className="bg-purple-500 hover:bg-purple-600" asChild>
                    <Link to="/hs-code/search">
                      <Search className="w-5 h-5" />
                    </Link>
                  </Button>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <span className="text-xs text-slate-500">Popular:</span>
                  <button className="text-xs text-purple-400 hover:underline">Electronics</button>
                  <button className="text-xs text-purple-400 hover:underline">Textiles</button>
                  <button className="text-xs text-purple-400 hover:underline">Machinery</button>
                  <button className="text-xs text-purple-400 hover:underline">Food products</button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Stats */}
        <section className="py-12 bg-slate-950">
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
        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                More Than Just HS Codes
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Get duty rates, FTA eligibility, and import restrictions - everything you need for customs clearance.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature, idx) => (
                <div key={idx} className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 hover:border-purple-500/30 transition-colors">
                  <div className="w-12 h-12 bg-purple-500/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-purple-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((bullet, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-500">
                        <CheckCircle className="w-4 h-4 text-purple-500" />
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
        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
                Stop Guessing HS Codes
              </h2>
              <p className="text-lg text-slate-400 mb-8">
                Free, instant, accurate. The way tariff classification should be.
              </p>
              <Button size="lg" className="bg-white text-slate-900 hover:bg-slate-100 font-semibold" asChild>
                <Link to="/hs-code/search">
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

