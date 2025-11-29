import { 
  FileCheck, 
  Search, 
  Calculator, 
  FileText, 
  Ship, 
  Building2,
  Shield,
  ArrowRight,
  Receipt,
  Truck,
  Scale,
  Globe,
  CreditCard,
  BarChart3,
  AlertTriangle,
  Umbrella
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

const tools = [
  // Document & Validation
  {
    icon: FileCheck,
    name: "LCopilot",
    tagline: "LC Validation in 45 Seconds",
    description: "AI validates Letters of Credit against UCP600, ISBP745, and 3,500+ trade rules. Catch discrepancies before banks do.",
    highlights: ["3,500+ Rules", "UCP600 + ISBP745", "Bank-Grade AI"],
    status: "live" as const,
    href: "/lcopilot",
    category: "Document & Validation",
    color: "blue",
  },
  {
    icon: FileText,
    name: "Doc Generator",
    tagline: "Trade Docs in Minutes",
    description: "Auto-generate compliant commercial invoices, packing lists, and certificates of origin. Pre-filled from your LC data.",
    highlights: ["20+ Doc Types", "LC Pre-fill", "Bank-Ready PDFs"],
    status: "coming" as const,
    href: "/doc-generator",
    category: "Document & Validation",
    color: "blue",
  },
  {
    icon: Receipt,
    name: "LC Builder",
    tagline: "Error-Free LC Applications",
    description: "Guided LC application builder with clause library, real-time validation, and MT700 preview. 80% fewer rejections.",
    highlights: ["500+ Clauses", "Risk Scoring", "MT700 Preview"],
    status: "coming" as const,
    href: "/lc-builder",
    category: "Document & Validation",
    color: "emerald",
  },
  
  // Compliance & Screening
  {
    icon: Search,
    name: "Sanctions Screener",
    tagline: "Screen in Under 2 Seconds",
    description: "Real-time screening against OFAC, EU, UN, and 50+ global sanctions lists. Parties, vessels, and goods.",
    highlights: ["50+ Lists", "Vessel Screening", "Fuzzy Matching"],
    status: "coming" as const,
    href: "/sanctions",
    category: "Compliance & Screening",
    color: "red",
  },
  {
    icon: AlertTriangle,
    name: "Counterparty Risk",
    tagline: "Know Before You Trade",
    description: "Credit scores, payment history, litigation records, and beneficial ownership for buyers, suppliers, and banks.",
    highlights: ["500M+ Companies", "Payment History", "Ownership Data"],
    status: "coming" as const,
    href: "/risk",
    category: "Compliance & Screening",
    color: "orange",
  },
  {
    icon: Shield,
    name: "Dual-Use Checker",
    tagline: "Export Control Compliance",
    description: "Screen goods against EAR, EU 2021/821, and Wassenaar. ECCN classification and license determination.",
    highlights: ["6 Regimes", "ECCN Lookup", "License Guidance"],
    status: "coming" as const,
    href: "/dual-use",
    category: "Compliance & Screening",
    color: "red",
  },

  // Classification & Customs
  {
    icon: Calculator,
    name: "HS Code Finder",
    tagline: "AI Tariff Classification",
    description: "Describe products in plain language. Get HS codes, duty rates, and FTA eligibility for 100+ countries.",
    highlights: ["100+ Countries", "FTA Calculator", "98% Accuracy"],
    status: "coming" as const,
    href: "/hs-code",
    category: "Classification & Customs",
    color: "purple",
  },
  {
    icon: Globe,
    name: "CustomsMate",
    tagline: "Import Requirements Database",
    description: "Know exactly what's needed for customs clearance. Documents, licenses, permits, and restrictions by country.",
    highlights: ["190+ Countries", "License Lookup", "Broker Directory"],
    status: "coming" as const,
    href: "/customs",
    category: "Classification & Customs",
    color: "cyan",
  },
  {
    icon: Scale,
    name: "Duty Calculator",
    tagline: "Know Your Landed Cost",
    description: "Calculate duties, taxes, and fees for any origin-destination pair. FTA savings calculator included.",
    highlights: ["Real-Time FX", "FTA Savings", "Full Breakdown"],
    status: "coming" as const,
    href: "/duty-calc",
    category: "Classification & Customs",
    color: "green",
  },

  // Logistics & Tracking
  {
    icon: Ship,
    name: "Container Tracker",
    tagline: "Real-Time Visibility",
    description: "Track containers across 100+ carriers. ML-powered ETAs, delay alerts, and document status in one dashboard.",
    highlights: ["100+ Carriers", "95% ETA Accuracy", "Proactive Alerts"],
    status: "coming" as const,
    href: "/tracking",
    category: "Logistics & Tracking",
    color: "blue",
  },
  {
    icon: Truck,
    name: "Route Optimizer",
    tagline: "Best Route, Best Price",
    description: "Compare carriers, transit times, and costs. Reliability scores and CO2 tracking for ESG reporting.",
    highlights: ["Multi-Carrier", "CO2 Tracking", "Reliability Data"],
    status: "coming" as const,
    href: "/routes",
    category: "Logistics & Tracking",
    color: "purple",
  },

  // Finance & Banking
  {
    icon: Building2,
    name: "Bank Fee Comparator",
    tagline: "Stop Overpaying",
    description: "Compare LC issuance, amendment, and discrepancy fees across 50+ banks. User ratings and processing times.",
    highlights: ["50+ Banks", "User Ratings", "Fee History"],
    status: "coming" as const,
    href: "/bank-fees",
    category: "Finance & Banking",
    color: "yellow",
  },
  {
    icon: CreditCard,
    name: "Trade Finance",
    tagline: "Fund Faster",
    description: "Connect with lenders for LC discounting, invoice factoring, supply chain finance, and forfaiting.",
    highlights: ["20+ Lenders", "48hr Funding", "Rate Comparison"],
    status: "coming" as const,
    href: "/finance",
    category: "Finance & Banking",
    color: "emerald",
  },
  {
    icon: Umbrella,
    name: "Insurance Quote",
    tagline: "Cover in 60 Seconds",
    description: "Instant cargo insurance quotes from multiple underwriters. Certificates generated immediately.",
    highlights: ["10+ Insurers", "Instant Certs", "Claims Support"],
    status: "coming" as const,
    href: "/insurance",
    category: "Finance & Banking",
    color: "teal",
  },

  // Intelligence
  {
    icon: BarChart3,
    name: "Trade Analytics",
    tagline: "Data-Driven Decisions",
    description: "Dashboards for trade volume, compliance rates, supplier performance, and operational KPIs.",
    highlights: ["50+ Metrics", "Custom Dashboards", "API Access"],
    status: "coming" as const,
    href: "/analytics",
    category: "Intelligence",
    color: "indigo",
  },
];

const categories = [
  "Document & Validation",
  "Compliance & Screening", 
  "Classification & Customs",
  "Logistics & Tracking",
  "Finance & Banking",
  "Intelligence",
];

const colorMap: Record<string, { bg: string; border: string; text: string; iconBg: string }> = {
  blue: { bg: "group-hover:bg-blue-500/5", border: "group-hover:border-blue-500/40", text: "group-hover:text-blue-400", iconBg: "group-hover:bg-blue-500/20" },
  emerald: { bg: "group-hover:bg-emerald-500/5", border: "group-hover:border-emerald-500/40", text: "group-hover:text-emerald-400", iconBg: "group-hover:bg-emerald-500/20" },
  red: { bg: "group-hover:bg-red-500/5", border: "group-hover:border-red-500/40", text: "group-hover:text-red-400", iconBg: "group-hover:bg-red-500/20" },
  orange: { bg: "group-hover:bg-orange-500/5", border: "group-hover:border-orange-500/40", text: "group-hover:text-orange-400", iconBg: "group-hover:bg-orange-500/20" },
  purple: { bg: "group-hover:bg-purple-500/5", border: "group-hover:border-purple-500/40", text: "group-hover:text-purple-400", iconBg: "group-hover:bg-purple-500/20" },
  cyan: { bg: "group-hover:bg-cyan-500/5", border: "group-hover:border-cyan-500/40", text: "group-hover:text-cyan-400", iconBg: "group-hover:bg-cyan-500/20" },
  green: { bg: "group-hover:bg-green-500/5", border: "group-hover:border-green-500/40", text: "group-hover:text-green-400", iconBg: "group-hover:bg-green-500/20" },
  yellow: { bg: "group-hover:bg-yellow-500/5", border: "group-hover:border-yellow-500/40", text: "group-hover:text-yellow-400", iconBg: "group-hover:bg-yellow-500/20" },
  teal: { bg: "group-hover:bg-teal-500/5", border: "group-hover:border-teal-500/40", text: "group-hover:text-teal-400", iconBg: "group-hover:bg-teal-500/20" },
  indigo: { bg: "group-hover:bg-indigo-500/5", border: "group-hover:border-indigo-500/40", text: "group-hover:text-indigo-400", iconBg: "group-hover:bg-indigo-500/20" },
};

export function ToolsSection() {
  return (
    <section className="py-24 md:py-32 bg-slate-950 relative">
      {/* Background decoration */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-blue-500/30 to-transparent" />
      <div className="absolute top-1/4 right-0 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 left-0 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section header */}
        <div className="text-center mb-16">
          <p className="text-blue-400 font-semibold mb-4 tracking-wide uppercase text-sm">Platform</p>
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6 leading-tight">
            15 Tools.
            <br />
            <span className="text-slate-500">One Platform.</span>
          </h2>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            Everything you need for trade operations - from document validation to customs clearance.
          </p>
        </div>

        {/* Tools by category */}
        <div className="max-w-7xl mx-auto space-y-16">
          {categories.map((category) => {
            const categoryTools = tools.filter(t => t.category === category);
            return (
              <div key={category}>
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-8 pl-3 border-l-2 border-blue-500">
                  {category}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {categoryTools.map((tool, index) => {
                    const colors = colorMap[tool.color] || colorMap.blue;
                    return (
                      <Link
                        key={index}
                        to={tool.href}
                        className={`group bg-slate-900/50 border border-slate-800 rounded-2xl p-6 hover:bg-slate-900/80 transition-all duration-300 relative flex flex-col min-h-[280px] ${colors.border} ${colors.bg}`}
                      >
                        {/* Status badge */}
                        <div className="absolute top-5 right-5">
                          {tool.status === "live" ? (
                            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                              Live
                            </span>
                          ) : (
                            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
                              Coming Soon
                            </span>
                          )}
                        </div>

                        {/* Icon */}
                        <div className={`w-14 h-14 bg-slate-800 rounded-xl flex items-center justify-center mb-5 transition-colors ${colors.iconBg}`}>
                          <tool.icon className={`w-7 h-7 text-slate-400 transition-colors ${colors.text}`} />
                        </div>

                        {/* Content */}
                        <div className="flex-1">
                          <h4 className={`text-lg font-bold text-white mb-1 transition-colors ${colors.text}`}>
                            {tool.name}
                          </h4>
                          <p className="text-sm font-medium text-slate-400 mb-3">
                            {tool.tagline}
                          </p>
                          <p className="text-sm text-slate-500 leading-relaxed mb-4">
                            {tool.description}
                          </p>
                        </div>

                        {/* Highlights */}
                        <div className="flex flex-wrap gap-2 mt-auto pt-4 border-t border-slate-800/50">
                          {tool.highlights.map((highlight, i) => (
                            <span 
                              key={i} 
                              className="px-2.5 py-1 bg-slate-800/80 rounded-lg text-xs text-slate-400 font-medium"
                            >
                              {highlight}
                            </span>
                          ))}
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* CTA */}
        <div className="text-center mt-20">
          <p className="text-slate-500 mb-6">Start with LCopilot today. More tools launching every month.</p>
          <Button 
            size="lg" 
            className="bg-white text-slate-900 hover:bg-slate-100 px-8 h-12 font-semibold"
            asChild
          >
            <Link to="/lcopilot">
              Try LCopilot Free
              <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
