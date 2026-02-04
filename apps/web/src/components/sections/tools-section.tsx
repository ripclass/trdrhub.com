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
  DollarSign
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
  },
  {
    icon: FileText,
    name: "Doc Generator",
    tagline: "Trade Docs in Minutes",
    description: "Auto-generate compliant commercial invoices, packing lists, and certificates of origin. Pre-filled from your LC data.",
    highlights: ["20+ Doc Types", "LC Pre-fill", "Bank-Ready PDFs"],
    status: "live" as const,
    href: "/doc-generator",
    category: "Document & Validation",
  },
  {
    icon: Receipt,
    name: "LC Builder",
    tagline: "Error-Free LC Applications",
    description: "Guided LC application builder with clause library, real-time validation, and MT700 preview. 80% fewer rejections.",
    highlights: ["500+ Clauses", "Risk Scoring", "MT700 Preview"],
    status: "live" as const,
    href: "/lc-builder",
    category: "Document & Validation",
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
  },

  // Classification & Customs
  {
    icon: Calculator,
    name: "HS Code Finder",
    tagline: "AI Tariff Classification",
    description: "Describe products in plain language. Get HS codes, duty rates, and FTA eligibility for 100+ countries.",
    highlights: ["100+ Countries", "FTA Calculator", "98% Accuracy"],
    status: "live" as const,
    href: "/hs-code",
    category: "Classification & Customs",
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
  },

  // Logistics & Tracking
  {
    icon: Ship,
    name: "Container Tracker",
    tagline: "Track + Vessel Compliance",
    description: "Track containers across 100+ carriers with vessel sanctions screening, AIS gap detection, and LC expiry alerts. Bank-grade compliance.",
    highlights: ["Vessel Screening", "AIS Monitoring", "LC Expiry Alerts"],
    status: "live" as const,
    href: "/tracking",
    category: "Logistics & Tracking",
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
  },

  // Intelligence
  {
    icon: DollarSign,
    name: "Price Verify",
    tagline: "Catch Price Anomalies",
    description: "Verify trade prices against real-time market data. Detect over/under invoicing and TBML risks. Compliance-ready reports.",
    highlights: ["50+ Commodities", "TBML Detection", "Market Data"],
    status: "live" as const,
    href: "/price-verify",
    category: "Intelligence",
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

export function ToolsSection() {
  return (
    <section className="py-24 sm:py-32 bg-[#00261C] relative">
      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />

      {/* Background decoration */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
      <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section header */}
        <div className="text-center mb-20">
          <p className="text-[#B2F273] font-mono text-xs tracking-widest uppercase mb-4">Platform Architecture</p>
          <h2 className="text-4xl md:text-6xl font-bold text-white mb-6 leading-tight font-display">
            7 Live. 9 Coming.
            <br />
            <span className="text-[#B2F273] text-glow-sm">One Platform.</span>
          </h2>
          <p className="text-lg text-[#EDF5F2]/60 max-w-2xl mx-auto px-4 font-light">
            Everything you need for trade operations - from document validation to customs clearance.
          </p>
        </div>

        {/* Tools by category */}
        <div className="max-w-7xl mx-auto space-y-20">
          {categories.map((category) => {
            const categoryTools = tools.filter(t => t.category === category);
            return (
              <div key={category}>
                <div className="flex items-center gap-4 mb-8 pl-2">
                  <div className="w-1 h-6 bg-[#B2F273]" />
                  <h3 className="text-sm font-semibold text-[#EDF5F2]/80 uppercase tracking-wider font-mono">
                    {category}
                  </h3>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {categoryTools.map((tool, index) => (
                    <Link
                      key={index}
                      to={tool.href}
                      className="group bg-[#00261C] border border-[#EDF5F2]/10 rounded-2xl p-6 hover:border-[#B2F273]/50 transition-all duration-300 relative flex flex-col min-h-[280px] hover:-translate-y-1 hover:shadow-[0_10px_40px_-10px_rgba(178,242,115,0.1)] overflow-hidden"
                    >
                      {/* Hover Gradient Overlay */}
                      <div className="absolute inset-0 bg-gradient-to-b from-[#B2F273]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

                      {/* Status badge */}
                      <div className="absolute top-5 right-5 flex flex-col items-end gap-2 z-10">
                        {tool.status === "live" ? (
                          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide bg-[#B2F273]/10 text-[#B2F273] border border-[#B2F273]/20">
                            Live
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide bg-[#EDF5F2]/5 text-[#EDF5F2]/40 border border-[#EDF5F2]/10">
                            Coming Soon
                          </span>
                        )}
                        {(tool as any).badge && (
                          <span className="px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wide bg-[#F25E3D]/10 text-[#F25E3D] border border-[#F25E3D]/20">
                            {(tool as any).badge}
                          </span>
                        )}
                      </div>

                      {/* Icon */}
                      <div className="w-14 h-14 bg-[#00382E] rounded-xl flex items-center justify-center mb-6 group-hover:bg-[#B2F273] transition-colors duration-300 relative z-10">
                        <tool.icon className="w-7 h-7 text-[#EDF5F2]/60 group-hover:text-[#00261C] transition-colors duration-300" />
                      </div>

                      {/* Content */}
                      <div className="flex-1 relative z-10">
                        <h4 className="text-xl font-bold text-white mb-2 group-hover:text-[#B2F273] transition-colors duration-300 font-display">
                          {tool.name}
                        </h4>
                        <p className="text-xs font-mono text-[#B2F273] mb-3 opacity-80">
                          {tool.tagline}
                        </p>
                        <p className="text-sm text-[#EDF5F2]/60 leading-relaxed mb-4 font-light">
                          {tool.description}
                        </p>
                      </div>

                      {/* Highlights */}
                      <div className="flex flex-wrap gap-2 mt-auto pt-4 border-t border-[#EDF5F2]/10 relative z-10">
                        {tool.highlights.map((highlight, i) => (
                          <span 
                            key={i} 
                            className="px-2 py-1 bg-[#00382E] rounded text-[10px] text-[#EDF5F2]/50 font-medium group-hover:text-[#EDF5F2]/80 transition-colors"
                          >
                            {highlight}
                          </span>
                        ))}
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* CTA */}
        <div className="text-center mt-32">
          <p className="text-[#EDF5F2]/60 mb-8 font-light">Start with LCopilot today. More tools launching every month.</p>
          <Button 
            size="lg" 
            className="bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] px-10 py-7 h-auto font-bold text-lg border-none shadow-[0_0_20px_rgba(178,242,115,0.2)] hover:shadow-[0_0_30px_rgba(178,242,115,0.4)] transition-all duration-300"
            asChild
          >
            <Link to="/lcopilot">
              Try LCopilot Free
              <ArrowRight className="w-5 h-5 ml-2" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
