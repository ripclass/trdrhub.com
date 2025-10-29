import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowRight, Shield, Users, Zap } from "lucide-react";

const stats = [
  {
    icon: Users,
    value: "500+",
    label: "Active Exporters"
  },
  {
    icon: Shield,
    value: "99.2%",
    label: "Accuracy Rate"
  },
  {
    icon: Zap,
    value: "45s",
    label: "Avg. Processing"
  }
];

export function CTASection() {
  return (
    <section className="py-20 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-hero opacity-10" />
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative">
        <Card className="bg-card/50 backdrop-blur-sm border border-primary/20 shadow-strong">
          <CardContent className="p-12 text-center">
            <h2 className="text-3xl lg:text-5xl font-bold text-foreground mb-6">
              Ready to Validate Your{" "}
              <span className="bg-gradient-primary bg-clip-text text-transparent">
                LC Documents?
              </span>
            </h2>
            <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
              Join hundreds of Bangladeshi exporters who trust our platform for fast, 
              accurate LC document validation. Get started in under 2 minutes.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
              <Button size="lg" className="bg-gradient-primary hover:opacity-90 shadow-medium group">
                Start Free Trial
                <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
              </Button>
              <Button variant="outline" size="lg" className="border-primary/20 hover:bg-primary/5">
                View Pricing
              </Button>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-2xl mx-auto">
              {stats.map((stat, index) => (
                <div key={index} className="text-center">
                  <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mx-auto mb-3">
                    <stat.icon className="w-6 h-6 text-primary" />
                  </div>
                  <div className="text-2xl font-bold text-foreground mb-1">{stat.value}</div>
                  <div className="text-sm text-muted-foreground">{stat.label}</div>
                </div>
              ))}
            </div>

            <div className="mt-8 pt-8 border-t border-gray-200/50">
              <p className="text-sm text-muted-foreground">
                🚀 <strong>Limited Time:</strong> Free validation for your first 5 LC documents
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}