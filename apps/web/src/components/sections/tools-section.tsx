import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  Calculator,
  Shield,
  TrendingUp,
  FileCheck,
  Archive,
  Ship,
  ArrowRight,
  FileEdit,
  AlertTriangle,
  Package,
  Landmark,
  BarChart3,
  Globe,
  DollarSign,
  Sparkles,
  Code2
} from "lucide-react";
import { Link } from "react-router-dom";

type ToolStatus = "live" | "coming-soon" | "free";

interface Tool {
  icon: React.ElementType;
  name: string;
  description: string;
  status: ToolStatus;
  link: string;
  buttonText: string;
  badge?: string;
}

interface ToolCategory {
  id: string;
  title: string;
  subtitle: string;
  icon: React.ElementType;
  tools: Tool[];
}

const toolCategories: ToolCategory[] = [
  {
    id: "documents",
    title: "Document Preparation",
    subtitle: "Create, validate, and manage trade documents",
    icon: FileText,
    tools: [
      {
        icon: FileText,
        name: "LCopilot",
        description: "AI-powered Letter of Credit validator. Catch discrepancies before banks do.",
        status: "live",
        link: "/lcopilot",
        buttonText: "Open LCopilot",
        badge: "⭐ Flagship"
      },
      {
        icon: Calculator,
        name: "HS Code & Duty Calculator",
        description: "AI-powered product classification with multi-country duty rates and FTA preferences.",
        status: "coming-soon",
        link: "#",
        buttonText: "Coming Q1 2025"
      },
      {
        icon: FileEdit,
        name: "LC Application Builder",
        description: "Guided wizard to create bank-ready LC applications. Export to any bank format.",
        status: "coming-soon",
        link: "#",
        buttonText: "Coming Q1 2025"
      }
    ]
  },
  {
    id: "compliance",
    title: "Compliance & Validation",
    subtitle: "Stay compliant with sanctions, export controls, and customs",
    icon: Shield,
    tools: [
      {
        icon: Shield,
        name: "Sanctions Screener",
        description: "Screen parties, vessels, and goods against OFAC, EU, UN, and UK sanctions lists instantly.",
        status: "coming-soon",
        link: "#",
        buttonText: "Coming Q1 2025",
        badge: "🔒 Critical"
      },
      {
        icon: Globe,
        name: "CustomsMate",
        description: "Smart customs declarations with auto-extraction from commercial docs. Submit directly to UK CDS, Singapore TradeNet.",
        status: "coming-soon",
        link: "#",
        buttonText: "Coming Q2 2025"
      },
      {
        icon: AlertTriangle,
        name: "Export Control Checker",
        description: "Check if your goods require export licenses. Covers EAR, ITAR, EU Dual-Use, and Wassenaar.",
        status: "coming-soon",
        link: "#",
        buttonText: "Coming Q2 2025"
      }
    ]
  },
  {
    id: "logistics",
    title: "Shipment & Logistics",
    subtitle: "Track shipments and manage transport documents",
    icon: Ship,
    tools: [
      {
        icon: Ship,
        name: "Container & Vessel Tracker",
        description: "Real-time multi-carrier tracking with ETA predictions and delay alerts.",
        status: "coming-soon",
        link: "#",
        buttonText: "Coming Q2 2025"
      },
      {
        icon: Package,
        name: "eBL Manager",
        description: "Manage electronic Bills of Lading across DCSA, BOLERO, essDOCS, and WaveBL from one dashboard.",
        status: "coming-soon",
        link: "#",
        buttonText: "Coming Q2 2025",
        badge: "🚀 Future-Ready"
      },
      {
        icon: FileCheck,
        name: "Shipping Doc Generator",
        description: "Generate LC-compliant invoices, packing lists, and certificates. One data entry, all documents.",
        status: "coming-soon",
        link: "#",
        buttonText: "Coming Q2 2025"
      }
    ]
  },
  {
    id: "finance",
    title: "Finance & Payments",
    subtitle: "Optimize trade finance costs and manage VAT/duties",
    icon: DollarSign,
    tools: [
      {
        icon: Calculator,
        name: "Trade Finance Calculator",
        description: "Estimate LC costs, forfaiting rates, and guarantee fees across scenarios. Free forever.",
        status: "free",
        link: "#",
        buttonText: "Coming Q1 2025",
        badge: "🆓 Free Tool"
      },
      {
        icon: Landmark,
        name: "Bank Fee Comparator",
        description: "Compare trade finance fees across banks. Find the best rates for your transactions.",
        status: "coming-soon",
        link: "#",
        buttonText: "Coming Q3 2025"
      },
      {
        icon: DollarSign,
        name: "VAT & Duty Manager",
        description: "Track VAT refunds, calculate duties, and generate MTD-ready VAT returns automatically.",
        status: "coming-soon",
        link: "#",
        buttonText: "Coming Q3 2025"
      }
    ]
  },
  {
    id: "intelligence",
    title: "Intelligence & Reporting",
    subtitle: "Gain insights and maintain compliance records",
    icon: BarChart3,
    tools: [
      {
        icon: BarChart3,
        name: "Trade Analytics",
        description: "Visualize trade performance, discrepancy patterns, and partner scores. Data-driven decisions.",
        status: "coming-soon",
        link: "#",
        buttonText: "Coming Q3 2025"
      },
      {
        icon: TrendingUp,
        name: "Counterparty Risk (RiskRecon)",
        description: "Automated counterparty risk assessment. Company verification, financial health, and red flag detection.",
        status: "coming-soon",
        link: "#",
        buttonText: "Coming Q2 2025"
      },
      {
        icon: Archive,
        name: "Audit Trail & Digital Vault",
        description: "Secure document storage with version history, complete audit trails, and compliance reporting.",
        status: "coming-soon",
        link: "#",
        buttonText: "Coming Q3 2025"
      }
    ]
  }
];

// Free utility tools
const utilityTools: Tool[] = [
  {
    icon: Code2,
    name: "SWIFT Decoder",
    description: "Paste any MT700/MT707/MT760 message and get human-readable breakdown with field explanations.",
    status: "free",
    link: "#",
    buttonText: "Coming Q1 2025",
    badge: "🆓 Free Tool"
  }
];

function StatusBadge({ status, badge }: { status: ToolStatus; badge?: string }) {
  if (badge) {
    return (
      <Badge variant="secondary" className="text-xs font-medium bg-primary/10 text-primary border-0">
        {badge}
      </Badge>
    );
  }
  
  switch (status) {
    case "live":
      return (
        <Badge className="text-xs font-medium bg-green-500/10 text-green-600 border-0">
          ✅ Live
        </Badge>
      );
    case "free":
      return (
        <Badge className="text-xs font-medium bg-blue-500/10 text-blue-600 border-0">
          🆓 Free
        </Badge>
      );
    case "coming-soon":
      return (
        <Badge variant="secondary" className="text-xs font-medium bg-warning/10 text-warning border-0">
          Coming Soon
        </Badge>
      );
  }
}

function ToolCard({ tool }: { tool: Tool }) {
  const isAvailable = tool.status === "live";
  
  return (
    <Card className="relative overflow-hidden border border-gray-200/50 hover:border-primary/20 transition-all duration-300 hover:shadow-medium group h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between mb-3">
          <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center group-hover:bg-primary/20 transition-colors">
            <tool.icon className="w-5 h-5 text-primary" />
          </div>
          <StatusBadge status={tool.status} badge={tool.badge} />
        </div>
        <CardTitle className="text-lg font-semibold">{tool.name}</CardTitle>
      </CardHeader>
      
      <CardContent className="pt-0 flex-1 flex flex-col">
        <CardDescription className="text-muted-foreground mb-4 leading-relaxed text-sm flex-1">
          {tool.description}
        </CardDescription>
        
        <Button 
          className={`w-full group/btn ${
            isAvailable 
              ? "bg-gradient-primary hover:opacity-90" 
              : "bg-muted text-muted-foreground hover:bg-muted"
          }`}
          disabled={!isAvailable}
          asChild={isAvailable}
          size="sm"
        >
          {isAvailable ? (
            <Link to={tool.link} className="flex items-center justify-center">
              {tool.buttonText}
              <ArrowRight className="w-4 h-4 ml-2 group-hover/btn:translate-x-1 transition-transform" />
            </Link>
          ) : (
            <span>{tool.buttonText}</span>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}

export function ToolsSection() {
  return (
    <section id="tools" className="py-20 bg-muted/30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 bg-primary/10 text-primary px-4 py-2 rounded-full text-sm font-medium mb-6">
            <Sparkles className="w-4 h-4" />
            15 Tools. One Platform.
          </div>
          <h2 className="text-3xl lg:text-5xl font-bold text-foreground mb-6">
            Complete Trade{" "}
            <span className="bg-gradient-primary bg-clip-text text-transparent">
              Operations Suite
            </span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            Everything you need to manage trade documents, ensure compliance, track shipments, 
            and optimize costs — all in one integrated platform.
          </p>
        </div>

        {/* Tool Categories */}
        <div className="space-y-16">
          {toolCategories.map((category) => (
            <div key={category.id}>
              {/* Category Header */}
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                  <category.icon className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-foreground">{category.title}</h3>
                  <p className="text-sm text-muted-foreground">{category.subtitle}</p>
                </div>
              </div>
              
              {/* Tools Grid */}
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {category.tools.map((tool, index) => (
                  <ToolCard key={index} tool={tool} />
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Free Utility Tools */}
        <div className="mt-16 pt-12 border-t border-border">
          <div className="text-center mb-8">
            <h3 className="text-xl font-semibold text-foreground mb-2">
              🛠️ Free Utility Tools
            </h3>
            <p className="text-sm text-muted-foreground">
              Helpful tools for everyday trade finance tasks — free forever
            </p>
          </div>
          
          <div className="max-w-md mx-auto">
            {utilityTools.map((tool, index) => (
              <ToolCard key={index} tool={tool} />
            ))}
          </div>
        </div>

        {/* Bottom CTA */}
        <div className="text-center mt-16 p-8 bg-gradient-to-r from-primary/5 via-primary/10 to-primary/5 rounded-2xl">
          <h3 className="text-2xl font-semibold text-foreground mb-3">
            🚀 New tools launching monthly
          </h3>
          <p className="text-muted-foreground mb-6 max-w-xl mx-auto">
            Join 500+ trade professionals already using TRDR Hub. Get early access to new tools 
            and shape the future of trade operations.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button asChild className="bg-gradient-primary hover:opacity-90">
              <Link to="/signup">
                Get Started Free
                <ArrowRight className="w-4 h-4 ml-2" />
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link to="/lcopilot">
                Try LCopilot Now
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
