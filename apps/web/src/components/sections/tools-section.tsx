import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  FileText,
  Calculator,
  Shield,
  TrendingUp,
  FileCheck,
  AlertTriangle,
  Archive,
  Ship,
  ArrowRight
} from "lucide-react";
import { Link } from "react-router-dom";

const tools = [
  {
    icon: FileText,
    name: "LCopilot",
    description: "AI-powered Letter of Credit validator. Avoid costly errors and get bank-ready in minutes.",
    status: "available",
    link: "/lcopilot",
    buttonText: "Open LCopilot"
  },
  {
    icon: Calculator,
    name: "HS Code & Duty Calculator",
    description: "Automatically classify products and calculate import duties with real-time tariff data.",
    status: "coming-soon",
    link: "#",
    buttonText: "Coming Soon"
  },
  {
    icon: Shield,
    name: "CustomsMate",
    description: "Streamline customs documentation and ensure compliance with local regulations.",
    status: "coming-soon",
    link: "#",
    buttonText: "Coming Soon"
  },
  {
    icon: TrendingUp,
    name: "RiskRecon",
    description: "Advanced risk assessment and reconciliation for complex trade transactions.",
    status: "coming-soon",
    link: "#",
    buttonText: "Coming Soon"
  },
  {
    icon: FileCheck,
    name: "VAT Return Auto-Generator",
    description: "Generate accurate VAT returns automatically from your trade documentation.",
    status: "coming-soon",
    link: "#",
    buttonText: "Coming Soon"
  },
  {
    icon: AlertTriangle,
    name: "Alert & Reminder System",
    description: "Never miss critical deadlines with intelligent notifications and reminders.",
    status: "coming-soon",
    link: "#",
    buttonText: "Coming Soon"
  },
  {
    icon: Archive,
    name: "Audit Trail / Digital Locker",
    description: "Secure, compliant document storage with comprehensive audit trails.",
    status: "coming-soon",
    link: "#",
    buttonText: "Coming Soon"
  },
  {
    icon: Ship,
    name: "Container/Vessel Tracker",
    description: "Real-time tracking of shipments with automated status updates and alerts.",
    status: "coming-soon",
    link: "#",
    buttonText: "Coming Soon"
  }
];

export function ToolsSection() {
  return (
    <section id="tools" className="py-20 bg-muted/30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl lg:text-5xl font-bold text-foreground mb-6">
            Comprehensive Trade{" "}
            <span className="bg-gradient-primary bg-clip-text text-transparent">
              Risk Management Suite
            </span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            Everything you need to manage trade documentation, assess risk, and ensure compliance - 
            all in one integrated platform.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {tools.map((tool, index) => (
            <Card 
              key={index} 
              className="relative overflow-hidden border border-gray-200/50 hover:border-primary/20 transition-all duration-300 hover:shadow-medium group"
            >
              {tool.status === "coming-soon" && (
                <div className="absolute top-4 right-4 bg-warning/10 text-warning px-2 py-1 rounded-full text-xs font-medium">
                  Coming Soon
                </div>
              )}
              
              <CardHeader className="pb-4">
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                  <tool.icon className="w-6 h-6 text-primary" />
                </div>
                <CardTitle className="text-xl font-semibold">{tool.name}</CardTitle>
              </CardHeader>
              
              <CardContent className="pt-0">
                <CardDescription className="text-muted-foreground mb-6 leading-relaxed">
                  {tool.description}
                </CardDescription>
                
                <Button 
                  className={`w-full group/btn ${
                    tool.status === "available" 
                      ? "bg-gradient-primary hover:opacity-90" 
                      : "bg-muted text-muted-foreground cursor-not-allowed"
                  }`}
                  disabled={tool.status === "coming-soon"}
                  asChild={tool.status === "available"}
                >
                  {tool.status === "available" ? (
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
          ))}
        </div>

        <div className="text-center mt-12">
          <p className="text-sm text-muted-foreground">
            🚀 <strong>New tools launching monthly</strong> - Join our platform to get early access
          </p>
        </div>
      </div>
    </section>
  );
}