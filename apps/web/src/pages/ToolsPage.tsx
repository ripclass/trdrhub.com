import { useState, useMemo } from "react";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Link } from "react-router-dom";
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
  X
} from "lucide-react";
import { cn } from "@/lib/utils";

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
    href: "/doc-generator/dashboard",
    category: "Document & Validation",
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
    href: "/hs-code/dashboard",
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
    href: "/tracking/dashboard",
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
    href: "/price-verify/dashboard",
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
  "All",
  "Document & Validation",
  "Compliance & Screening", 
  "Classification & Customs",
  "Logistics & Tracking",
  "Finance & Banking",
  "Intelligence",
];

const ToolsPage = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");

  const filteredTools = useMemo(() => {
    return tools.filter((tool) => {
      const matchesSearch = 
        tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        tool.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        tool.tagline.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesCategory = selectedCategory === "All" || tool.category === selectedCategory;

      return matchesSearch && matchesCategory;
    });
  }, [searchQuery, selectedCategory]);

  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main className="pt-24 pb-24 relative min-h-screen">
        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none fixed" />

        {/* Background decoration */}
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
        <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          {/* Header */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full border border-[#B2F273]/20 bg-[#B2F273]/5 backdrop-blur-sm mb-6">
              <span className="text-[#B2F273] font-mono text-xs tracking-wider uppercase">Global Trade Operating System</span>
            </div>
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-white mb-6 leading-tight font-display">
              The Complete
              <br />
              <span className="text-[#B2F273] text-glow-sm">Trade Toolkit.</span>
            </h1>
            <p className="text-lg text-[#EDF5F2]/60 max-w-2xl mx-auto font-light leading-relaxed">
              A unified suite of AI-powered tools designed to digitize, validate, and secure every step of your trade lifecycle.
            </p>
          </div>

          {/* Search and Filter */}
          <div className="max-w-4xl mx-auto mb-16 space-y-8">
            {/* Search Bar */}
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#EDF5F2]/40" />
              <Input 
                type="text" 
                placeholder="Search tools (e.g., 'LC', 'Sanctions', 'Tracker')..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full h-14 pl-12 pr-12 bg-[#00382E]/50 border-[#EDF5F2]/10 text-white placeholder-[#EDF5F2]/30 rounded-xl focus:border-[#B2F273]/50 focus:ring-[#B2F273]/20 text-lg"
              />
              {searchQuery && (
                <button 
                  onClick={() => setSearchQuery("")}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[#EDF5F2]/40 hover:text-white transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>

            {/* Category Pills */}
            <div className="flex flex-wrap justify-center gap-2">
              {categories.map((category) => (
                <button
                  key={category}
                  onClick={() => setSelectedCategory(category)}
                  className={cn(
                    "px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 border",
                    selectedCategory === category
                      ? "bg-[#B2F273] text-[#00261C] border-[#B2F273]"
                      : "bg-[#00382E]/30 text-[#EDF5F2]/60 border-transparent hover:border-[#EDF5F2]/20 hover:text-[#EDF5F2]"
                  )}
                >
                  {category}
                </button>
              ))}
            </div>
          </div>

          {/* Tools Grid */}
          {filteredTools.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredTools.map((tool, index) => (
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
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="text-xl font-bold text-white group-hover:text-[#B2F273] transition-colors duration-300 font-display">
                        {tool.name}
                      </h4>
                      <ArrowRight className="w-4 h-4 text-[#B2F273] opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300" />
                    </div>
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
          ) : (
            <div className="text-center py-20 border border-dashed border-[#EDF5F2]/10 rounded-3xl bg-[#00382E]/20">
              <div className="w-16 h-16 bg-[#00382E] rounded-full flex items-center justify-center mx-auto mb-4">
                <Search className="w-8 h-8 text-[#EDF5F2]/40" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">No tools found</h3>
              <p className="text-[#EDF5F2]/60 max-w-md mx-auto">
                We couldn't find any tools matching "{searchQuery}" in {selectedCategory === 'All' ? 'our catalog' : selectedCategory}.
              </p>
              <Button 
                variant="link" 
                onClick={() => { setSearchQuery(""); setSelectedCategory("All"); }}
                className="text-[#B2F273] mt-4"
              >
                Clear filters
              </Button>
            </div>
          )}

          {/* Bottom CTA */}
          <div className="text-center mt-32 border-t border-[#EDF5F2]/10 pt-20">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-6 font-display">
              Can't find what you need?
            </h2>
            <p className="text-[#EDF5F2]/60 mb-8 font-light max-w-xl mx-auto">
              We're constantly adding new tools based on user feedback. Let us know what you're looking for.
            </p>
            <div className="flex justify-center gap-4">
              <Button 
                size="lg" 
                className="bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] px-8 font-bold border-none"
                asChild
              >
                <Link to="/contact">
                  Request a Tool
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default ToolsPage;
