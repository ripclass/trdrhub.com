import { 
  FileCheck, 
  Search, 
  Calculator, 
  FileText, 
  Ship, 
  Building2,
  Shield,
  ArrowRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

const flagshipTools = [
  {
    icon: FileCheck,
    name: "LCopilot",
    tagline: "AI LC Validation",
    description: "Upload documents, get instant discrepancy detection with UCP600 citations and suggested fixes.",
    status: "live" as const,
    href: "/lcopilot",
    badge: "FLAGSHIP",
  },
  {
    icon: Search,
    name: "Sanctions Screener",
    tagline: "OFAC • EU • UN",
    description: "Screen parties and goods against global sanctions lists in real-time.",
    status: "live" as const,
    href: "/sanctions",
    badge: null,
  },
  {
    icon: Calculator,
    name: "HS Code Finder",
    tagline: "AI Classification",
    description: "Find the right HS code for any product with AI-powered classification.",
    status: "live" as const,
    href: "/hs-code",
    badge: "FREE",
  },
];

const comingSoonTools = [
  {
    icon: FileText,
    name: "Doc Generator",
    description: "Auto-generate compliant shipping documents",
  },
  {
    icon: Ship,
    name: "Container Tracker",
    description: "Real-time shipment tracking",
  },
  {
    icon: Building2,
    name: "Bank Fee Comparator",
    description: "Compare LC fees across banks",
  },
  {
    icon: Shield,
    name: "Insurance Quote",
    description: "Instant cargo insurance quotes",
  },
];

export function ToolsSection() {
  return (
    <section className="py-24 md:py-32 bg-slate-50">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16">
          <p className="text-blue-600 font-semibold mb-4 tracking-wide uppercase text-sm">Platform</p>
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-slate-900 mb-6 leading-tight">
            15 Tools.
            <br />
            <span className="text-slate-400">One Platform.</span>
          </h2>
          <p className="text-xl text-slate-600 max-w-2xl mx-auto">
            Everything you need for trade operations - from document validation to customs clearance.
          </p>
        </div>

        {/* Flagship tools */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto mb-12">
          {flagshipTools.map((tool, index) => (
            <Link
              key={index}
              to={tool.href}
              className="group bg-white border border-slate-200 rounded-2xl p-8 hover:border-blue-500 hover:shadow-xl transition-all duration-300 relative overflow-hidden"
            >
              {tool.badge && (
                <div className={`absolute top-4 right-4 px-3 py-1 rounded-full text-xs font-bold ${
                  tool.badge === "FLAGSHIP" 
                    ? "bg-blue-100 text-blue-600" 
                    : "bg-emerald-100 text-emerald-600"
                }`}>
                  {tool.badge}
                </div>
              )}
              <div className="w-14 h-14 bg-slate-100 rounded-xl flex items-center justify-center mb-6 group-hover:bg-blue-50 transition-colors">
                <tool.icon className="w-7 h-7 text-slate-700 group-hover:text-blue-600 transition-colors" />
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-1">
                {tool.name}
              </h3>
              <p className="text-sm text-slate-500 mb-3">{tool.tagline}</p>
              <p className="text-slate-600 leading-relaxed mb-6">
                {tool.description}
              </p>
              <div className="flex items-center text-blue-600 font-medium group-hover:gap-2 transition-all">
                {tool.status === "live" ? "Try Now" : "Coming Soon"}
                <ArrowRight className="w-4 h-4 ml-1 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </Link>
          ))}
        </div>

        {/* Coming soon tools - compact grid */}
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-slate-500 mb-6 text-sm font-medium">COMING Q1-Q3 2025</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {comingSoonTools.map((tool, index) => (
              <div
                key={index}
                className="bg-white border border-slate-200 rounded-xl p-5 opacity-75 hover:opacity-100 transition-opacity"
              >
                <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center mb-4">
                  <tool.icon className="w-5 h-5 text-slate-500" />
                </div>
                <h3 className="font-semibold text-slate-900 text-sm mb-1">
                  {tool.name}
                </h3>
                <p className="text-slate-500 text-xs leading-relaxed">
                  {tool.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="text-center mt-16">
          <Button 
            size="lg" 
            className="bg-slate-900 hover:bg-slate-800 text-white px-8 h-12"
            asChild
          >
            <Link to="/lcopilot">
              Explore All Tools
              <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
