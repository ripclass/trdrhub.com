import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Check, ArrowRight } from "lucide-react";

const plans = [
  {
    name: "Starter",
    description: "Perfect for SMEs and small exporters",
    price: "$49",
    period: "per month",
    features: [
      "Up to 25 LC validations/month",
      "Basic compliance checking",
      "Email support",
      "Standard processing speed",
      "Document templates",
      "Basic reporting"
    ],
    buttonText: "Start Free Trial",
    popular: false
  },
  {
    name: "Professional",
    description: "Ideal for high-volume exporters",
    price: "$149",
    period: "per month",
    features: [
      "Up to 100 LC validations/month",
      "Advanced compliance suite",
      "Priority support",
      "Fast processing speed",
      "Custom document templates",
      "Advanced analytics",
      "API access",
      "Multi-user accounts"
    ],
    buttonText: "Start Free Trial",
    popular: true
  },
  {
    name: "Enterprise",
    description: "For banks and large institutions",
    price: "Custom",
    period: "pricing",
    features: [
      "Unlimited LC validations",
      "Full compliance automation",
      "Dedicated account manager",
      "Priority processing",
      "Custom integrations",
      "White-label options",
      "SLA guarantees",
      "Custom training"
    ],
    buttonText: "Contact Sales",
    popular: false
  }
];

export function TRDRPricingSection() {
  return (
    <section id="pricing" className="py-20">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl lg:text-5xl font-bold text-foreground mb-6">
            Simple, Transparent{" "}
            <span className="bg-gradient-primary bg-clip-text text-transparent">
              Pricing
            </span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            Choose the plan that fits your business needs. All plans include a 14-day free trial.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {plans.map((plan, index) => (
            <Card 
              key={index} 
              className={`relative border transition-all duration-300 hover:shadow-medium ${
                plan.popular 
                  ? "border-primary/50 shadow-medium scale-105" 
                  : "border-gray-200/50 hover:border-primary/20"
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <div className="bg-gradient-primary text-primary-foreground px-4 py-1 rounded-full text-sm font-medium">
                    Most Popular
                  </div>
                </div>
              )}
              
              <CardHeader className="pb-4">
                <CardTitle className="text-2xl font-bold">{plan.name}</CardTitle>
                <CardDescription className="text-muted-foreground">
                  {plan.description}
                </CardDescription>
                <div className="mt-4">
                  <span className="text-4xl font-bold text-foreground">{plan.price}</span>
                  <span className="text-muted-foreground ml-2">/{plan.period}</span>
                </div>
              </CardHeader>
              
              <CardContent className="pt-0">
                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-center gap-3">
                      <Check className="w-4 h-4 text-success flex-shrink-0" />
                      <span className="text-sm text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>
                
                <Button 
                  className={`w-full group ${
                    plan.popular 
                      ? "bg-gradient-primary hover:opacity-90" 
                      : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                  }`}
                  asChild
                >
                  <a href="/register" className="flex items-center justify-center">
                    {plan.buttonText}
                    <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                  </a>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="text-center mt-12">
          <p className="text-sm text-muted-foreground mb-4">
            🎯 <strong>14-day free trial</strong> on all plans • No credit card required
          </p>
          <p className="text-xs text-muted-foreground">
            All prices are in USD. Enterprise pricing is customized based on your specific requirements.
          </p>
        </div>
      </div>
    </section>
  );
}