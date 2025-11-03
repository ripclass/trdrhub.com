import { Link } from "react-router-dom";
import { ArrowRight, BarChart3, CheckCircle, FileText, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const roles = [
  {
    id: "exporter",
    title: "I'm an Exporter",
    description: "Validate export LCs, generate discrepancy reports, and prepare bank-ready packages in minutes.",
    to: "/lcopilot/exporter-dashboard",
    accent: "bg-gradient-exporter",
  },
  {
    id: "importer",
    title: "I'm an Importer",
    description: "Screen supplier submissions, manage drafts, and reduce costly discrepancies before shipment.",
    to: "/lcopilot/importer-dashboard",
    accent: "bg-gradient-importer",
  },
  {
    id: "bank",
    title: "I'm a Bank / FI",
    description:
      "Monitor system-wide LC quality, automate compliance review, and collaborate with clients in real time.",
    to: "/lcopilot/analytics/bank",
    accent: "bg-gradient-primary",
  },
];

const highlights = [
  {
    icon: <FileText className="w-5 h-5 text-primary" />,
    label: "95%+ accuracy",
    description: "AI-assisted ICC / UCP600 rules engine tuned for South Asian trade workflows.",
  },
  {
    icon: <Shield className="w-5 h-5 text-success" />,
    label: "Bank approved",
    description: "Built with partner banks to shorten LC turnaround and reduce operational risk.",
  },
  {
    icon: <BarChart3 className="w-5 h-5 text-info" />,
    label: "Actionable analytics",
    description: "Track discrepancy patterns, supplier performance, and internal SLAs in one dashboard.",
  },
];

const stats = [
  { value: "500+", label: "LCs processed" },
  { value: "< 60s", label: "Avg. validation time" },
  { value: "70%", label: "Fewer discrepancy escalations" },
];

export default function LcopilotLanding() {
  return (
    <div className="min-h-screen bg-background">
      <div className="bg-gradient-hero/10">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
          <div className="max-w-3xl">
            <Badge variant="secondary" className="mb-4 px-3 py-1 text-sm">
              LC Validation Copilot
            </Badge>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground mb-6">
              Bank-ready LC checks for Exporters, Importers, and Financial Institutions.
            </h1>
            <p className="text-lg text-muted-foreground mb-10 leading-relaxed">
              LCopilot combines AI-driven document analysis with compliance workflows built with Bangladeshi banks.
              Choose your journey below to get started.
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            {roles.map((role) => (
              <Card key={role.id} className="relative overflow-hidden border-border/50 shadow-soft">
                <div className={`absolute inset-x-0 top-0 h-1 ${role.accent}`} />
                <CardHeader className="space-y-3">
                  <CardTitle className="text-2xl font-semibold text-foreground">{role.title}</CardTitle>
                  <CardDescription className="text-muted-foreground text-base leading-relaxed">
                    {role.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <CheckCircle className="w-4 h-4 text-success" />
                    Tailored guidance • Role-specific dashboards
                  </div>
                  <Button asChild size="lg" className={`${role.accent} hover:opacity-90 text-foreground`}> 
                    <Link to={role.to} className="flex items-center justify-center gap-2">
                      Continue <ArrowRight className="w-4 h-4" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>

      <div className="border-t border-border/60 bg-card/30">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="grid gap-8 lg:grid-cols-3">
            {highlights.map((item, idx) => (
              <Card key={idx} className="border-border/50 shadow-sm">
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="bg-secondary/30 p-3 rounded-lg">{item.icon}</div>
                    <h3 className="text-lg font-semibold text-foreground">{item.label}</h3>
                  </div>
                  <p className="text-muted-foreground leading-relaxed text-sm sm:text-base">
                    {item.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-gradient-primary/5">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="flex flex-col lg:flex-row items-center justify-between gap-10">
            <div>
              <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
                Purpose-built for Bangladeshi trade operators.
              </h2>
              <p className="text-muted-foreground max-w-2xl leading-relaxed">
                Whether you process one LC a month or hundreds per day, LCopilot pairs automated validation with
                human-ready workflows so your teams can collaborate with clients and banks without friction.
              </p>
            </div>
            <div className="flex flex-wrap gap-6">
              {stats.map((stat) => (
                <Card key={stat.label} className="w-48 border-border/60 shadow-soft">
                  <CardContent className="p-6 text-center space-y-3">
                    <div className="text-3xl font-bold text-foreground">{stat.value}</div>
                    <div className="text-sm text-muted-foreground uppercase tracking-wide">{stat.label}</div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

