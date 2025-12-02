import { useState, useEffect } from "react";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check, Star, Users, Zap, Shield, Globe } from "lucide-react";
import { 
  PRICING_TIERS, 
  getPriceDisplay, 
  getPrice, 
  getCurrencyFromCountry,
  CURRENCIES,
  PAY_PER_USE,
  type CurrencyCode 
} from "@/lib/pricing";

const Pricing = () => {
  const [currency, setCurrency] = useState<CurrencyCode>("USD");
  const [detectedCountry, setDetectedCountry] = useState<string>("");
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "yearly">("monthly");

  // Auto-detect country/currency
  useEffect(() => {
    async function detectCurrency() {
      try {
        const res = await fetch("/api/geo");
        const data = await res.json();
        if (data.country) {
          setDetectedCountry(data.country);
          setCurrency(getCurrencyFromCountry(data.country));
        }
      } catch {
        // Default to USD
      }
    }
    detectCurrency();
  }, []);

  const currencyInfo = CURRENCIES[currency];
  const formatPrice = (amount: number) => {
    if (currencyInfo?.position === "after") {
      return `${amount.toLocaleString()} ${currencyInfo.symbol}`;
    }
    return `${currencyInfo?.symbol || "$"}${amount.toLocaleString()}`;
  };

  const addOns = [
    {
      name: "Express Check",
      price: formatPrice(PAY_PER_USE.lc_validation[currency] * 1.5),
      description: "Get results in under 30 seconds",
      icon: Zap
    },
    {
      name: "Dedicated Account Manager",
      price: `${formatPrice(getPrice(PRICING_TIERS[2], currency, "monthly") * 0.3)}/mo`,
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

            {/* Currency indicator */}
            {detectedCountry && (
              <div className="mt-4 flex justify-center">
                <div className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/30 rounded-full px-4 py-2">
                  <Globe className="w-4 h-4" />
                  <span>Showing prices in {currencyInfo?.name || "USD"}</span>
                </div>
              </div>
            )}

            {/* Billing toggle */}
            <div className="flex justify-center mt-6">
              <div className="flex items-center gap-3 bg-card border rounded-full px-4 py-2">
                <span className={`text-sm ${billingPeriod === "monthly" ? "text-foreground font-medium" : "text-muted-foreground"}`}>
                  Monthly
                </span>
                <button
                  onClick={() => setBillingPeriod(p => p === "monthly" ? "yearly" : "monthly")}
                  className={`w-12 h-6 rounded-full p-1 transition-colors ${
                    billingPeriod === "yearly" ? "bg-primary" : "bg-muted"
                  }`}
                >
                  <div
                    className={`w-4 h-4 rounded-full bg-white transition-transform ${
                      billingPeriod === "yearly" ? "translate-x-6" : ""
                    }`}
                  />
                </button>
                <span className={`text-sm flex items-center gap-1 ${billingPeriod === "yearly" ? "text-foreground font-medium" : "text-muted-foreground"}`}>
                  Yearly
                  <Badge variant="secondary" className="text-xs">Save ~15%</Badge>
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Pricing Cards */}
        <section className="py-20">
          <div className="container mx-auto px-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 max-w-7xl mx-auto">
              {PRICING_TIERS.map((plan, index) => {
                const price = getPrice(plan, currency, billingPeriod);
                const priceDisplay = getPriceDisplay(plan, currency, billingPeriod);
                const yearlyTotal = getPrice(plan, currency, "yearly") * 12;

                return (
                  <Card 
                    key={plan.id} 
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
                        {plan.id === "enterprise" ? (
                          <>
                            <span className="text-4xl font-bold text-foreground">Custom</span>
                            <span className="text-muted-foreground ml-1">pricing</span>
                          </>
                        ) : price === 0 ? (
                          <span className="text-4xl font-bold text-foreground">Free</span>
                        ) : (
                          <>
                            <span className="text-4xl font-bold text-foreground">{priceDisplay}</span>
                            <span className="text-muted-foreground">/mo</span>
                          </>
                        )}
                      </div>
                      {billingPeriod === "yearly" && price > 0 && plan.id !== "enterprise" && (
                        <p className="text-xs text-primary pt-2">
                          {formatPrice(yearlyTotal)} billed annually
                        </p>
                      )}
                      <p className="text-sm text-muted-foreground pt-2">
                        {plan.limits.lc_validations === "unlimited" 
                          ? "Unlimited validations" 
                          : `${plan.limits.lc_validations} validations/month`}
                      </p>
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
                        asChild
                      >
                        <a href={plan.id === "enterprise" ? "mailto:sales@trdrhub.com" : "/register"}>
                          {plan.id === "enterprise" ? "Contact Sales" : plan.id === "free" ? "Get Started" : "Start Free Trial"}
                        </a>
                      </Button>
                    </CardContent>
                  </Card>
                );
              })}
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
            <div className="grid md:grid-cols-2 gap-6 max-w-2xl mx-auto">
              <Card>
                <CardContent className="p-8 text-center">
                  <div className="text-3xl font-bold text-foreground mb-2">
                    {formatPrice(PAY_PER_USE.lc_validation[currency])}
                  </div>
                  <div className="text-muted-foreground mb-4">per LC validation</div>
                  <p className="text-sm text-muted-foreground">Full compliance check with UCP600</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-8 text-center">
                  <div className="text-3xl font-bold text-foreground mb-2">
                    {formatPrice(PAY_PER_USE.price_check[currency])}
                  </div>
                  <div className="text-muted-foreground mb-4">per price check</div>
                  <p className="text-sm text-muted-foreground">Market price verification</p>
                </CardContent>
              </Card>
            </div>
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
              <Button size="lg" variant="secondary" asChild>
                <a href="/register">Start Free Trial</a>
              </Button>
              <Button size="lg" variant="outline" className="bg-transparent border-primary-foreground text-primary-foreground hover:bg-primary-foreground hover:text-primary" asChild>
                <a href="mailto:sales@trdrhub.com">Schedule Demo</a>
              </Button>
            </div>
            <p className="text-sm text-primary-foreground/80 mt-6">
              {currency === "BDT" && "🇧🇩 Local payment via SSLCommerz available"}
              {currency === "INR" && "🇮🇳 Local payment via Razorpay available"}
              {currency === "PKR" && "🇵🇰 Local payment options coming soon"}
              {!["BDT", "INR", "PKR"].includes(currency) && "💳 Secure payment via Stripe"}
            </p>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
};

export default Pricing;
