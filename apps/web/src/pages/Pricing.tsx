import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check, Star, Users, Zap, Shield } from "lucide-react";

const Pricing = () => {
  const plans = [
    {
      name: "SME Starter",
      price: "৳2,500",
      period: "/month",
      description: "Perfect for small exporters getting started",
      checks: "10 document checks/month",
      features: [
        "Basic compliance checking",
        "Standard PDF reports",
        "Email support",
        "Basic document templates",
        "Mobile app access"
      ],
      cta: "Start Free Trial",
      popular: false,
      theme: "default"
    },
    {
      name: "Growth",
      price: "৳6,500",
      period: "/month",
      description: "For growing businesses with regular shipments",
      checks: "30 document checks/month",
      features: [
        "Advanced compliance checking",
        "Priority processing",
        "Custom branded reports",
        "Phone & email support",
        "Document templates library",
        "API access",
        "Team collaboration (5 users)"
      ],
      cta: "Start Free Trial",
      popular: true,
      theme: "primary"
    },
    {
      name: "Enterprise",
      price: "৳15,000",
      period: "/month",
      description: "For large organizations with high volume",
      checks: "75+ document checks/month",
      features: [
        "Enterprise compliance engine",
        "Instant processing",
        "White-label solutions",
        "Dedicated account manager",
        "Custom integrations",
        "Advanced analytics",
        "Unlimited team members",
        "SLA guarantee"
      ],
      cta: "Contact Sales",
      popular: false,
      theme: "secondary"
    }
  ];

  const addOns = [
    {
      name: "Express Check",
      price: "৳300",
      description: "Get results in under 30 seconds",
      icon: Zap
    },
    {
      name: "Dedicated Account Manager",
      price: "৳10,000/mo",
      description: "For 50+ LCs per month",
      icon: Users
    },
    {
      name: "Custom Integration",
      price: "Contact us",
      description: "API integration with your ERP system",
      icon: Shield
    }
  ];

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="pt-16">
        {/* Hero Section */}
        <section className="py-20 bg-gradient-hero">
          <div className="container mx-auto px-4 text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-6">
              Choose Your Plan
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
              Transparent pricing for businesses of all sizes. Start with our free trial and scale as you grow.
            </p>
            <div className="inline-flex items-center gap-2 bg-card border rounded-full px-4 py-2">
              <Star className="w-4 h-4 text-yellow-500 fill-current" />
              <span className="text-sm text-foreground">All plans include 14-day free trial</span>
            </div>
          </div>
        </section>

        {/* Pricing Cards */}
        <section className="py-20">
          <div className="container mx-auto px-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
              {plans.map((plan, index) => (
                <Card 
                  key={index} 
                  className={`relative ${plan.popular ? 'border-primary shadow-strong scale-105' : 'border-gray-200'} transition-all duration-300 hover:shadow-medium`}
                >
                  {plan.popular && (
                    <Badge className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-primary text-primary-foreground">
                      Most Popular
                    </Badge>
                  )}
                  <CardHeader className="text-center pb-8">
                    <CardTitle className="text-2xl font-bold text-foreground">
                      {plan.name}
                    </CardTitle>
                    <CardDescription className="text-muted-foreground">
                      {plan.description}
                    </CardDescription>
                    <div className="pt-4">
                      <span className="text-4xl font-bold text-foreground">{plan.price}</span>
                      <span className="text-muted-foreground">{plan.period}</span>
                    </div>
                    <p className="text-sm text-muted-foreground pt-2">{plan.checks}</p>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <ul className="space-y-3">
                      {plan.features.map((feature, idx) => (
                        <li key={idx} className="flex items-center gap-3">
                          <Check className="w-4 h-4 text-success shrink-0" />
                          <span className="text-sm text-foreground">{feature}</span>
                        </li>
                      ))}
                    </ul>
                    <Button 
                      className={`w-full ${plan.popular ? 'bg-gradient-primary' : ''}`}
                      variant={plan.popular ? "default" : "outline"}
                    >
                      {plan.cta}
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* Pay Per Use */}
        <section className="py-16 bg-muted/30">
          <div className="container mx-auto px-4 text-center">
            <h2 className="text-3xl font-bold text-foreground mb-4">
              Pay Per Use
            </h2>
            <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
              For occasional users or to supplement your monthly plan
            </p>
            <Card className="max-w-md mx-auto">
              <CardContent className="p-8 text-center">
                <div className="text-3xl font-bold text-foreground mb-2">৳1,200</div>
                <div className="text-muted-foreground mb-6">per document check</div>
                <Button variant="outline" className="w-full">
                  Buy Credits
                </Button>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Add-ons */}
        <section className="py-20">
          <div className="container mx-auto px-4">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-foreground mb-4">
                Add-on Services
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Enhance your experience with premium add-ons
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              {addOns.map((addon, index) => (
                <Card key={index} className="text-center border-gray-200 hover:shadow-medium transition-all duration-300">
                  <CardContent className="p-8">
                    <addon.icon className="w-12 h-12 text-primary mx-auto mb-4" />
                    <h3 className="text-xl font-semibold text-foreground mb-2">
                      {addon.name}
                    </h3>
                    <p className="text-muted-foreground mb-4">
                      {addon.description}
                    </p>
                    <div className="text-2xl font-bold text-foreground">
                      {addon.price}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-20 bg-gradient-primary">
          <div className="container mx-auto px-4 text-center">
            <h2 className="text-3xl font-bold text-primary-foreground mb-4">
              Ready to Get Started?
            </h2>
            <p className="text-lg text-primary-foreground/90 mb-8 max-w-2xl mx-auto">
              Join hundreds of exporters and importers who trust us with their LC compliance
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="lg" variant="secondary">
                Start Free Trial
              </Button>
              <Button size="lg" variant="outline" className="bg-transparent border-primary-foreground text-primary-foreground hover:bg-primary-foreground hover:text-primary">
                Schedule Demo
              </Button>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
};

export default Pricing;