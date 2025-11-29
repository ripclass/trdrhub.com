import { Link, useParams } from "react-router-dom";
import { ArrowRight, Bell, CheckCircle, Clock, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import * as Icons from "lucide-react";

// Tool configurations
const toolConfigs: Record<string, {
  name: string;
  tagline: string;
  description: string;
  icon: keyof typeof Icons;
  color: string;
  features: string[];
  expectedLaunch: string;
}> = {
  "doc-generator": {
    name: "Doc Generator",
    tagline: "Auto-Generate Compliant Shipping Documents",
    description: "Create professional, compliant commercial invoices, packing lists, certificates of origin, and more. Pre-filled from your LC data, formatted to bank standards.",
    icon: "FileText",
    color: "blue",
    features: [
      "Commercial Invoice generation",
      "Packing List with carton breakdown",
      "Certificate of Origin templates",
      "Bill of Lading drafts",
      "Pre-filled from LC extraction",
      "Bank-ready PDF export"
    ],
    expectedLaunch: "Q1 2025"
  },
  "lc-builder": {
    name: "LC Application Builder",
    tagline: "Create Error-Free LC Applications",
    description: "Guided LC application builder with smart defaults, clause libraries, and automatic validation. Reduce application rejections by 80%.",
    icon: "FileEdit",
    color: "emerald",
    features: [
      "Step-by-step LC drafting",
      "Clause library with explanations",
      "Real-time validation",
      "Bank-specific templates",
      "MT700 SWIFT preview",
      "Export to bank format"
    ],
    expectedLaunch: "Q1 2025"
  },
  "counterparty-risk": {
    name: "Counterparty Risk",
    tagline: "Know Your Trade Partners",
    description: "Credit scores, payment history, litigation records, and sanctions screening for your buyers, suppliers, and banks. Make informed trade decisions.",
    icon: "AlertTriangle",
    color: "orange",
    features: [
      "Credit risk scores",
      "Payment behavior history",
      "Litigation & bankruptcy check",
      "Beneficial ownership",
      "Sanctions screening",
      "Country risk assessment"
    ],
    expectedLaunch: "Q2 2025"
  },
  "dual-use": {
    name: "Dual-Use Checker",
    tagline: "Export Control Compliance",
    description: "Screen goods against EAR, EU 2021/821, Wassenaar, and country-specific export control lists. Know if you need an export license.",
    icon: "Shield",
    color: "red",
    features: [
      "EAR/ECCN classification",
      "EU dual-use screening",
      "Wassenaar categories",
      "License determination",
      "End-use screening",
      "Denied parties check"
    ],
    expectedLaunch: "Q2 2025"
  },
  "customs": {
    name: "CustomsMate",
    tagline: "Country Import Requirements",
    description: "Know exactly what's needed for customs clearance in any country. Licenses, permits, documentation, and regulatory requirements in one place.",
    icon: "Globe",
    color: "cyan",
    features: [
      "Country-specific requirements",
      "Required documents checklist",
      "License/permit lookup",
      "Regulatory alerts",
      "Product-specific rules",
      "Broker directory"
    ],
    expectedLaunch: "Q2 2025"
  },
  "duty-calc": {
    name: "Duty Calculator",
    tagline: "Calculate Your Landed Cost",
    description: "Know your total cost before you ship. Duties, taxes, fees, and shipping costs calculated for any origin-destination pair.",
    icon: "Calculator",
    color: "green",
    features: [
      "Duty rate lookup",
      "Tax calculation",
      "FTA savings estimate",
      "Shipping cost estimate",
      "Currency conversion",
      "Landed cost breakdown"
    ],
    expectedLaunch: "Q2 2025"
  },
  "tracking": {
    name: "Container Tracker",
    tagline: "Real-Time Shipment Visibility",
    description: "Track containers across 100+ carriers in real-time. ETAs, port calls, delays, and exceptions in one dashboard.",
    icon: "Ship",
    color: "blue",
    features: [
      "100+ carrier coverage",
      "Real-time ETA updates",
      "Port congestion alerts",
      "Delay notifications",
      "Document status tracking",
      "Multi-shipment dashboard"
    ],
    expectedLaunch: "Q2 2025"
  },
  "routes": {
    name: "Route Optimizer",
    tagline: "Compare Shipping Options",
    description: "Find the best shipping route by cost, time, or reliability. Compare carriers, ports, and transit options.",
    icon: "Route",
    color: "purple",
    features: [
      "Multi-carrier comparison",
      "Transit time estimates",
      "Cost comparison",
      "Port alternatives",
      "Reliability scores",
      "Carbon footprint"
    ],
    expectedLaunch: "Q3 2025"
  },
  "bank-fees": {
    name: "Bank Fee Comparator",
    tagline: "Compare LC Fees Across Banks",
    description: "Stop overpaying for trade finance. Compare LC issuance, amendment, and discrepancy fees across 50+ banks.",
    icon: "Building2",
    color: "yellow",
    features: [
      "LC fee comparison",
      "Amendment charges",
      "Discrepancy fees",
      "Bank ratings",
      "Processing times",
      "Negotiation tips"
    ],
    expectedLaunch: "Q3 2025"
  },
  "finance": {
    name: "Trade Finance",
    tagline: "Access Trade Finance Solutions",
    description: "Connect with lenders for LC financing, invoice factoring, supply chain finance, and forfaiting.",
    icon: "CreditCard",
    color: "emerald",
    features: [
      "LC discounting",
      "Invoice factoring",
      "Supply chain finance",
      "Pre-export finance",
      "Forfaiting",
      "Rate comparison"
    ],
    expectedLaunch: "Q3 2025"
  },
  "insurance": {
    name: "Insurance Quote",
    tagline: "Instant Cargo Insurance",
    description: "Get cargo insurance quotes from multiple underwriters in minutes. Cover your shipments without the paperwork.",
    icon: "ShieldCheck",
    color: "teal",
    features: [
      "Instant quotes",
      "Multiple underwriters",
      "All-risk coverage",
      "Single shipment or annual",
      "Certificate generation",
      "Claims support"
    ],
    expectedLaunch: "Q3 2025"
  },
  "analytics": {
    name: "Trade Analytics",
    tagline: "Insights for Trade Operations",
    description: "Dashboards for trade volume, compliance rates, discrepancy patterns, and operational KPIs.",
    icon: "BarChart3",
    color: "indigo",
    features: [
      "Trade volume trends",
      "Compliance metrics",
      "Discrepancy analysis",
      "Supplier performance",
      "Bank performance",
      "Custom reports"
    ],
    expectedLaunch: "Q3 2025"
  }
};

const colorClasses: Record<string, { bg: string; border: string; text: string; gradient: string }> = {
  blue: { bg: "bg-blue-500/10", border: "border-blue-500/20", text: "text-blue-400", gradient: "from-blue-400 to-blue-500" },
  emerald: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", text: "text-emerald-400", gradient: "from-emerald-400 to-emerald-500" },
  orange: { bg: "bg-orange-500/10", border: "border-orange-500/20", text: "text-orange-400", gradient: "from-orange-400 to-orange-500" },
  red: { bg: "bg-red-500/10", border: "border-red-500/20", text: "text-red-400", gradient: "from-red-400 to-red-500" },
  cyan: { bg: "bg-cyan-500/10", border: "border-cyan-500/20", text: "text-cyan-400", gradient: "from-cyan-400 to-cyan-500" },
  green: { bg: "bg-green-500/10", border: "border-green-500/20", text: "text-green-400", gradient: "from-green-400 to-green-500" },
  purple: { bg: "bg-purple-500/10", border: "border-purple-500/20", text: "text-purple-400", gradient: "from-purple-400 to-purple-500" },
  yellow: { bg: "bg-yellow-500/10", border: "border-yellow-500/20", text: "text-yellow-400", gradient: "from-yellow-400 to-yellow-500" },
  teal: { bg: "bg-teal-500/10", border: "border-teal-500/20", text: "text-teal-400", gradient: "from-teal-400 to-teal-500" },
  indigo: { bg: "bg-indigo-500/10", border: "border-indigo-500/20", text: "text-indigo-400", gradient: "from-indigo-400 to-indigo-500" },
};

interface ComingSoonToolProps {
  toolSlug?: string;
}

const ComingSoonTool = ({ toolSlug }: ComingSoonToolProps) => {
  const params = useParams();
  const slug = toolSlug || params.tool || "doc-generator";
  const config = toolConfigs[slug] || toolConfigs["doc-generator"];
  const colors = colorClasses[config.color] || colorClasses.blue;
  const [email, setEmail] = useState("");
  const [subscribed, setSubscribed] = useState(false);
  
  // Get the icon component
  const IconComponent = (Icons as any)[config.icon] || Icons.Package;

  const handleNotify = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      setSubscribed(true);
      setEmail("");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      
      <main>
        {/* Hero Section */}
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden">
          <div className={`absolute top-0 left-1/4 w-96 h-96 ${colors.bg} rounded-full blur-3xl opacity-50`} />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-slate-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center">
              {/* Back link */}
              <Link to="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-white mb-8 text-sm">
                <ArrowLeft className="w-4 h-4" />
                Back to all tools
              </Link>

              {/* Coming Soon Badge */}
              <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full ${colors.bg} border ${colors.border} mb-6`}>
                <Clock className={`w-4 h-4 ${colors.text}`} />
                <span className={`${colors.text} text-sm font-medium`}>Coming {config.expectedLaunch}</span>
              </div>
              
              {/* Icon */}
              <div className={`w-20 h-20 ${colors.bg} rounded-2xl flex items-center justify-center mx-auto mb-6 border ${colors.border}`}>
                <IconComponent className={`w-10 h-10 ${colors.text}`} />
              </div>

              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                {config.name}
              </h1>
              
              <p className={`text-xl font-medium mb-4 bg-gradient-to-r ${colors.gradient} bg-clip-text text-transparent`}>
                {config.tagline}
              </p>
              
              <p className="text-lg text-slate-400 mb-10 leading-relaxed max-w-2xl mx-auto">
                {config.description}
              </p>

              {/* Notify Form */}
              {subscribed ? (
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-6 max-w-md mx-auto mb-10">
                  <CheckCircle className="w-8 h-8 text-emerald-400 mx-auto mb-3" />
                  <p className="text-emerald-400 font-medium">You're on the list!</p>
                  <p className="text-slate-400 text-sm mt-1">We'll email you when {config.name} launches.</p>
                </div>
              ) : (
                <form onSubmit={handleNotify} className="max-w-md mx-auto mb-10">
                  <p className="text-slate-400 mb-4">Get notified when we launch:</p>
                  <div className="flex gap-3">
                    <input
                      type="email"
                      placeholder="your@email.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                      required
                    />
                    <Button type="submit" className={`bg-gradient-to-r ${colors.gradient} text-white`}>
                      <Bell className="w-5 h-5 mr-2" />
                      Notify Me
                    </Button>
                  </div>
                </form>
              )}

              {/* Features Preview */}
              <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8 max-w-2xl mx-auto">
                <h3 className="text-white font-semibold mb-6">What's Coming</h3>
                <div className="grid grid-cols-2 gap-4">
                  {config.features.map((feature, idx) => (
                    <div key={idx} className="flex items-center gap-3 text-left">
                      <CheckCircle className={`w-5 h-5 ${colors.text} shrink-0`} />
                      <span className="text-slate-300 text-sm">{feature}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-16 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl font-bold text-white mb-4">
                Can't wait? Try our live tools
              </h2>
              <p className="text-slate-400 mb-8">
                LCopilot, Sanctions Screener, and HS Code Finder are available now.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Button size="lg" className="bg-white text-slate-900 hover:bg-slate-100 font-semibold" asChild>
                  <Link to="/lcopilot">
                    Try LCopilot <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button variant="outline" size="lg" className="border-slate-700 text-slate-300 hover:bg-slate-800" asChild>
                  <Link to="/">View All Tools</Link>
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

export default ComingSoonTool;

