import { Card, CardContent } from "@/components/ui/card";
import { Shield, Zap, Lock, TrendingUp, XCircle, CheckCircle } from "lucide-react";

// Before/After comparison - shows transformation
const painPoints = [
  {
    before: "Manual document checking (4+ hours)",
    after: "AI validation in 45 seconds"
  },
  {
    before: "$75-150 discrepancy fees per LC",
    after: "Catch errors before submission"
  },
  {
    before: "Juggling 10 different systems",
    after: "One platform for everything"
  },
  {
    before: "Missed sanctions = $1M+ fines",
    after: "Real-time OFAC/EU/UN screening"
  }
];

const features = [
  {
    icon: Shield,
    title: "Bank-Level Compliance",
    description: "UCP600, ISBP745, ISP98, URDG758 — plus 60+ country-specific regulations. The same rules banks use to reject your documents."
  },
  {
    icon: Zap,
    title: "45-Second Validation",
    description: "Upload your LC and docs. Get a complete compliance report before your coffee gets cold. No more 4-hour manual reviews."
  },
  {
    icon: Lock,
    title: "Sanctions Screening",
    description: "Check parties, vessels, and goods against OFAC, EU, UN, and UK lists. One click. Zero compliance anxiety."
  },
  {
    icon: TrendingUp,
    title: "Built for Scale",
    description: "From 1 LC/month to 1,000. Pricing that grows with you. Enterprise-ready from day one."
  }
];

export function WhyTRDRSection() {
  return (
    <section id="about" className="py-20">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section header - Problem focused */}
        <div className="text-center mb-16">
          <p className="text-primary font-medium mb-4">THE PROBLEM</p>
          <h2 className="text-3xl lg:text-5xl font-bold text-foreground mb-6">
            Trade Finance is{" "}
            <span className="bg-gradient-primary bg-clip-text text-transparent">
              Broken
            </span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Exporters lose millions to discrepancy fees, compliance gaps, and manual processes. 
            We built TRDR Hub to fix that.
          </p>
        </div>

        {/* Before/After Comparison - Visual transformation */}
        <div className="max-w-4xl mx-auto mb-20">
          <div className="grid md:grid-cols-2 gap-8">
            {/* Before Column */}
            <div className="bg-red-500/5 border border-red-500/20 rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-red-600 mb-6 flex items-center gap-2">
                <XCircle className="w-5 h-5" />
                Without TRDR Hub
              </h3>
              <ul className="space-y-4">
                {painPoints.map((point, i) => (
                  <li key={i} className="flex items-start gap-3 text-muted-foreground">
                    <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                    <span>{point.before}</span>
                  </li>
                ))}
              </ul>
            </div>
            
            {/* After Column */}
            <div className="bg-green-500/5 border border-green-500/20 rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-green-600 mb-6 flex items-center gap-2">
                <CheckCircle className="w-5 h-5" />
                With TRDR Hub
              </h3>
              <ul className="space-y-4">
                {painPoints.map((point, i) => (
                  <li key={i} className="flex items-start gap-3 text-foreground">
                    <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                    <span>{point.after}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-20">
          {features.map((feature, index) => (
            <Card key={index} className="border border-gray-200/50 hover:border-primary/20 transition-all duration-300 hover:shadow-medium group">
              <CardContent className="p-6 text-center">
                <div className="w-16 h-16 bg-primary/10 rounded-lg flex items-center justify-center mx-auto mb-4 group-hover:bg-primary/20 transition-colors">
                  <feature.icon className="w-8 h-8 text-primary" />
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-3">
                  {feature.title}
                </h3>
                <p className="text-muted-foreground leading-relaxed text-sm">
                  {feature.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Stats section - Specific numbers = credibility */}
        <div className="bg-muted/30 rounded-2xl p-8">
          <div className="grid md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-4xl lg:text-5xl font-bold bg-gradient-primary bg-clip-text text-transparent mb-2">3,500+</div>
              <div className="text-muted-foreground">Validation Rules</div>
              <div className="text-xs text-muted-foreground mt-1">UCP600, ISBP745, ISP98...</div>
            </div>
            <div>
              <div className="text-4xl lg:text-5xl font-bold bg-gradient-primary bg-clip-text text-transparent mb-2">60+</div>
              <div className="text-muted-foreground">Country Rules</div>
              <div className="text-xs text-muted-foreground mt-1">From Bangladesh to UAE</div>
            </div>
            <div>
              <div className="text-4xl lg:text-5xl font-bold bg-gradient-primary bg-clip-text text-transparent mb-2">45s</div>
              <div className="text-muted-foreground">Avg. Validation Time</div>
              <div className="text-xs text-muted-foreground mt-1">vs 4+ hours manual</div>
            </div>
            <div>
              <div className="text-4xl lg:text-5xl font-bold bg-gradient-primary bg-clip-text text-transparent mb-2">$75</div>
              <div className="text-muted-foreground">Saved Per Discrepancy</div>
              <div className="text-xs text-muted-foreground mt-1">Average bank fee avoided</div>
            </div>
          </div>
        </div>
        
      </div>
    </section>
  );
}
