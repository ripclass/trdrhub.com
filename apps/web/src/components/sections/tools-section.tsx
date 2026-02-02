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
  Umbrella,
  DollarSign,
  Anchor
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
    status: "live" as const,
    href: "/doc-generator/dashboard",
    category: "Document & Validation",
    color: "blue",
  },
  {
    icon: Receipt,
    name: "LC Builder",
    tagline: "Error-Free LC Applications",
    description: "Guided LC application builder with clause library, real-time validation, and MT700 preview. 80% fewer rejections.",
    highlights: ["500+ Clauses", "Risk Scoring", "MT700 Preview"],
    status: "live" as const,
    href: "/lc-builder/dashboard",
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
    status: "live" as const,
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
    status: "live" as const,
    href: "/hs-code/dashboard",
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
    tagline: "Track + Vessel Compliance",
    description: "Track containers across 100+ carriers with vessel sanctions screening, AIS gap detection, and LC expiry alerts. Bank-grade compliance.",
    highlights: ["Vessel Screening", "AIS Monitoring", "LC Expiry Alerts"],
    status: "live" as const,
    href: "/tracking/dashboard",
    category: "Logistics & Tracking",
    color: "blue",
    badge: "🏦 Bank Requested",
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
    icon: DollarSign,
    name: "Price Verify",
    tagline: "Catch Price Anomalies",
    description: "Verify trade prices against real-time market data. Detect over/under invoicing and TBML risks. Compliance-ready reports.",
    highlights: ["50+ Commodities", "TBML Detection", "Market Data"],
    status: "live" as const,
    href: "/price-verify/dashboard",
    category: "Intelligence",
    color: "green",
    badge: "🏦 Bank Requested",
  },
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
  blue: { bg: "group-hover:bg-[#F25E3D]/5", border: "group-hover:border-[#F25E3D]/40", text: "group-hover:text-[#F25E3D]", iconBg: "group-hover:bg-[#F25E3D]/20" },
  emerald: { bg: "group-hover:bg-[#B2F273]/5", border: "group-hover:border-[#B2F273]/40", text: "group-hover:text-[#B2F273]", iconBg: "group-hover:bg-[#B2F273]/20" },
  red: { bg: "group-hover:bg-[#F25E3D]/5", border: "group-hover:border-[#F25E3D]/40", text: "group-hover:text-[#F25E3D]", iconBg: "group-hover:bg-[#F25E3D]/20" },
  orange: { bg: "group-hover:bg-[#C2B894]/5", border: "group-hover:border-[#C2B894]/40", text: "group-hover:text-[#C2B894]", iconBg: "group-hover:bg-[#C2B894]/20" },
  purple: { bg: "group-hover:bg-[#C2B894]/5", border: "group-hover:border-[#C2B894]/40", text: "group-hover:text-[#C2B894]", iconBg: "group-hover:bg-[#C2B894]/20" },
  cyan: { bg: "group-hover:bg-[#B2F273]/5", border: "group-hover:border-[#B2F273]/40", text: "group-hover:text-[#B2F273]", iconBg: "group-hover:bg-[#B2F273]/20" },
  green: { bg: "group-hover:bg-[#B2F273]/5", border: "group-hover:border-[#B2F273]/40", text: "group-hover:text-[#B2F273]", iconBg: "group-hover:bg-[#B2F273]/20" },
  yellow: { bg: "group-hover:bg-[#C2B894]/5", border: "group-hover:border-[#C2B894]/40", text: "group-hover:text-[#C2B894]", iconBg: "group-hover:bg-[#C2B894]/20" },
  teal: { bg: "group-hover:bg-[#B2F273]/5", border: "group-hover:border-[#B2F273]/40", text: "group-hover:text-[#B2F273]", iconBg: "group-hover:bg-[#B2F273]/20" },
  indigo: { bg: "group-hover:bg-[#F25E3D]/5", border: "group-hover:border-[#F25E3D]/40", text: "group-hover:text-[#F25E3D]", iconBg: "group-hover:bg-[#F25E3D]/20" },
};

export function ToolsSection() {
  return (
    <section className="py-16 sm:py-24 md:py-32 bg-[#00261C] relative">
      {/* Background decoration */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#F25E3D]/30 to-transparent" />
      <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#F25E3D]/5 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section header */}
        <div className="text-center mb-10 sm:mb-16">
          <p className="text-[#F25E3D] font-semibold mb-3 sm:mb-4 tracking-wide uppercase text-xs sm:text-sm">Platform</p>
          <h2 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-4 sm:mb-6 leading-tight font-display">
            7 Live. 9 Coming.
            <br />
            <span className="text-[#C2B894]">One Platform.</span>
          </h2>
          <p className="text-base sm:text-xl text-[#EDF5F2]/80 max-w-2xl mx-auto px-4">
            Everything you need for trade operations - from document validation to customs clearance.
          </p>
        </div>

        {/* Tools by category */}
        <div className="max-w-7xl mx-auto space-y-10 sm:space-y-16">
          {categories.map((category) => {
            const categoryTools = tools.filter(t => t.category === category);
            return (
              <div key={category}>
                <h3 className="text-xs sm:text-sm font-semibold text-[#EDF5F2]/60 uppercase tracking-wider mb-6 sm:mb-8 pl-3 border-l-2 border-[#F25E3D]">
                  {category}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
                  {categoryTools.map((tool, index) => {
                    const colors = colorMap[tool.color] || colorMap.blue;
                    return (
                      <Link
                        key={index}
                        to={tool.href}
                        className={`group bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-2xl p-5 sm:p-6 hover:bg-[#00382E]/80 transition-all duration-300 relative flex flex-col min-h-[240px] sm:min-h-[280px] ${colors.border} ${colors.bg}`}
                      >
                        {/* Status badge */}
                        <div className="absolute top-5 right-5 flex flex-col items-end gap-1">
                          {tool.status === "live" ? (
                            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#B2F273]/20 text-[#B2F273] border border-[#B2F273]/30">
                              Live
                            </span>
                          ) : (
                            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-[#00261C] text-[#EDF5F2]/40 border border-[#EDF5F2]/10">
                              Coming Soon
                            </span>
                          )}
                          {(tool as any).badge && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#C2B894]/20 text-[#C2B894] border border-[#C2B894]/30">
                              {(tool as any).badge}
                            </span>
                          )}
                        </div>

                        {/* Icon */}
                        <div className={`w-12 sm:w-14 h-12 sm:h-14 bg-[#00261C] rounded-xl flex items-center justify-center mb-4 sm:mb-5 transition-colors ${colors.iconBg}`}>
                          <tool.icon className={`w-6 sm:w-7 h-6 sm:h-7 text-[#EDF5F2]/60 transition-colors ${colors.text}`} />
                        </div>

                        {/* Content */}
                        <div className="flex-1">
                          <h4 className={`text-base sm:text-lg font-bold text-white mb-1 transition-colors ${colors.text} font-display`}>
                            {tool.name}
                          </h4>
                          <p className="text-xs sm:text-sm font-medium text-[#C2B894] mb-2 sm:mb-3">
                            {tool.tagline}
                          </p>
                          <p className="text-xs sm:text-sm text-[#EDF5F2]/60 leading-relaxed mb-3 sm:mb-4">
                            {tool.description}
                          </p>
                        </div>

                        {/* Highlights */}
                        <div className="flex flex-wrap gap-2 mt-auto pt-4 border-t border-[#EDF5F2]/10">
                          {tool.highlights.map((highlight, i) => (
                            <span 
                              key={i} 
                              className="px-2.5 py-1 bg-[#00261C]/80 rounded-lg text-xs text-[#EDF5F2]/50 font-medium"
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
          <p className="text-[#EDF5F2]/60 mb-6">Start with LCopilot today. More tools launching every month.</p>
          <Button 
            size="lg" 
            className="bg-[#F25E3D] text-white hover:bg-[#D94E30] px-8 h-12 font-semibold border-none"
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
