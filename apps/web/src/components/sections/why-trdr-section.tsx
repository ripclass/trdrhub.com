import { Card, CardContent } from "@/components/ui/card";
import { Shield, Zap, Lock, TrendingUp } from "lucide-react";

const features = [
  {
    icon: Shield,
    title: "Comprehensive Compliance",
    description: "UCP600, ISBP745, ISP98, URDG758, and 60+ country-specific rules. Sanctions screening against OFAC, EU, UN, and UK lists."
  },
  {
    icon: Zap,
    title: "AI-Powered Speed",
    description: "Documents validated in under 60 seconds. From extraction to compliance check — automated end-to-end."
  },
  {
    icon: Lock,
    title: "Bank-Grade Security",
    description: "Enterprise encryption, immutable audit trails, and 7-year document retention. Built for regulated industries."
  },
  {
    icon: TrendingUp,
    title: "One Platform, All Tools",
    description: "LCs, customs, sanctions, tracking, analytics — everything connected. No more juggling 10 different systems."
  }
];

export function WhyTRDRSection() {
  return (
    <section id="about" className="py-20">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl lg:text-5xl font-bold text-foreground mb-6">
            Built for Banks, SMEs, and{" "}
            <span className="bg-gradient-primary bg-clip-text text-transparent">
              Global Trade Professionals
            </span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            Our platform combines cutting-edge technology with deep trade finance expertise 
            to deliver enterprise-grade solutions that scale.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, index) => (
            <Card key={index} className="border border-gray-200/50 hover:border-primary/20 transition-all duration-300 hover:shadow-medium group">
              <CardContent className="p-6 text-center">
                <div className="w-16 h-16 bg-primary/10 rounded-lg flex items-center justify-center mx-auto mb-4 group-hover:bg-primary/20 transition-colors">
                  <feature.icon className="w-8 h-8 text-primary" />
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-3">
                  {feature.title}
                </h3>
                <p className="text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Stats section */}
        <div className="mt-20 grid md:grid-cols-4 gap-8 text-center">
          <div>
            <div className="text-4xl lg:text-5xl font-bold bg-gradient-primary bg-clip-text text-transparent mb-2">15</div>
            <div className="text-muted-foreground">Integrated Tools</div>
          </div>
          <div>
            <div className="text-4xl lg:text-5xl font-bold bg-gradient-primary bg-clip-text text-transparent mb-2">3,500+</div>
            <div className="text-muted-foreground">Validation Rules</div>
          </div>
          <div>
            <div className="text-4xl lg:text-5xl font-bold bg-gradient-primary bg-clip-text text-transparent mb-2">60+</div>
            <div className="text-muted-foreground">Countries Covered</div>
          </div>
          <div>
            <div className="text-4xl lg:text-5xl font-bold bg-gradient-primary bg-clip-text text-transparent mb-2">45s</div>
            <div className="text-muted-foreground">Avg. Processing Time</div>
          </div>
        </div>
      </div>
    </section>
  );
}