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
  Users,
  AlertTriangle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

const tools = [
  // Document & Validation
  {
    icon: FileCheck,
    name: "LCopilot",
    description: "AI validates LCs against UCP600, ISBP745, and 3,500+ rules in 45 seconds",
    status: "live" as const,
    href: "/lcopilot",
    category: "Document & Validation",
  },
  {
    icon: FileText,
    name: "Doc Generator",
    description: "Auto-generate compliant invoices, packing lists, and shipping docs",
    status: "coming" as const,
    href: "/doc-generator",
    category: "Document & Validation",
  },
  {
    icon: Receipt,
    name: "LC Builder",
    description: "Create error-free LC applications with guided templates",
    status: "coming" as const,
    href: "/lc-builder",
    category: "Document & Validation",
  },
  
  // Compliance & Screening
  {
    icon: Search,
    name: "Sanctions Screener",
    description: "Real-time OFAC, EU, UN sanctions screening for parties and goods",
    status: "coming" as const,
    href: "/sanctions",
    category: "Compliance & Screening",
  },
  {
    icon: AlertTriangle,
    name: "Counterparty Risk",
    description: "Credit scores, payment history, and risk ratings for trade partners",
    status: "coming" as const,
    href: "/risk",
    category: "Compliance & Screening",
  },
  {
    icon: Shield,
    name: "Dual-Use Checker",
    description: "Screen goods against export control lists (EAR, EU, Wassenaar)",
    status: "coming" as const,
    href: "/dual-use",
    category: "Compliance & Screening",
  },

  // Classification & Customs
  {
    icon: Calculator,
    name: "HS Code Finder",
    description: "AI-powered tariff classification with duty rates and FTA eligibility",
    status: "coming" as const,
    href: "/hs-code",
    category: "Classification & Customs",
  },
  {
    icon: Globe,
    name: "CustomsMate",
    description: "Country-specific import requirements, licenses, and documentation",
    status: "coming" as const,
    href: "/customs",
    category: "Classification & Customs",
  },
  {
    icon: Scale,
    name: "Duty Calculator",
    description: "Calculate landed costs with duties, taxes, and fees by destination",
    status: "coming" as const,
    href: "/duty-calc",
    category: "Classification & Customs",
  },

  // Logistics & Tracking
  {
    icon: Ship,
    name: "Container Tracker",
    description: "Real-time visibility across 100+ carriers and all major ports",
    status: "coming" as const,
    href: "/tracking",
    category: "Logistics & Tracking",
  },
  {
    icon: Truck,
    name: "Route Optimizer",
    description: "Compare shipping routes, transit times, and freight costs",
    status: "coming" as const,
    href: "/routes",
    category: "Logistics & Tracking",
  },

  // Finance & Banking
  {
    icon: Building2,
    name: "Bank Fee Comparator",
    description: "Compare LC fees, charges, and terms across 50+ banks",
    status: "coming" as const,
    href: "/bank-fees",
    category: "Finance & Banking",
  },
  {
    icon: CreditCard,
    name: "Trade Finance",
    description: "Connect with lenders for LC financing, forfaiting, and factoring",
    status: "coming" as const,
    href: "/finance",
    category: "Finance & Banking",
  },
  {
    icon: Receipt,
    name: "Insurance Quote",
    description: "Instant cargo insurance quotes from multiple underwriters",
    status: "coming" as const,
    href: "/insurance",
    category: "Finance & Banking",
  },

  // Intelligence
  {
    icon: BarChart3,
    name: "Trade Analytics",
    description: "Dashboards for trade volume, costs, compliance rates, and trends",
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
        <div className="max-w-6xl mx-auto space-y-12">
          {categories.map((category) => {
            const categoryTools = tools.filter(t => t.category === category);
            return (
              <div key={category}>
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-6 pl-2 border-l-2 border-blue-500">
                  {category}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {categoryTools.map((tool, index) => (
                    <Link
                      key={index}
                      to={tool.href}
                      className={`group bg-slate-900/50 border border-slate-800 rounded-xl p-6 hover:border-blue-500/50 hover:bg-slate-900 transition-all duration-300 relative ${
                        tool.status === "coming" ? "opacity-75" : ""
                      }`}
                    >
                      {/* Status badge */}
                      <div className="absolute top-4 right-4">
                        {tool.status === "live" ? (
                          <span className="px-2 py-1 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            Live
                          </span>
                        ) : (
                          <span className="px-2 py-1 rounded-full text-xs font-medium bg-slate-700/50 text-slate-400">
                            Coming Soon
                          </span>
                        )}
                      </div>

                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-slate-800 rounded-lg flex items-center justify-center shrink-0 group-hover:bg-blue-500/20 transition-colors">
                          <tool.icon className="w-6 h-6 text-slate-400 group-hover:text-blue-400 transition-colors" />
                        </div>
                        <div className="pt-1">
                          <h4 className="font-semibold text-white mb-1 group-hover:text-blue-400 transition-colors">
                            {tool.name}
                          </h4>
                          <p className="text-sm text-slate-500 leading-relaxed">
                            {tool.description}
                          </p>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* CTA */}
        <div className="text-center mt-16">
          <p className="text-slate-500 mb-6">Start with our live tools today. More launching every month.</p>
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
