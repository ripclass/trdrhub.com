import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Check, ArrowRight } from "lucide-react";
import {
  PRICING_TIERS,
  getPriceDisplay,
  getPrice,
  getPayPerUseDisplay,
} from "@/lib/pricing";

export function TRDRPricingSection() {
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "yearly">("monthly");

  const displayPlans = PRICING_TIERS;
  const paygDisplay = getPayPerUseDisplay("lc_validation");

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
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto mb-8">
            Pay-as-you-go from {paygDisplay} per LC — no commitment, no card to start. Subscribe and save up to ~50% per LC.
          </p>

          {/* Billing Period Toggle */}
          <div className="flex items-center justify-center gap-4 mb-4">
            <div className="flex items-center gap-3 bg-muted/50 rounded-full px-4 py-2">
              <span className={`text-sm ${billingPeriod === "monthly" ? "text-foreground font-medium" : "text-muted-foreground"}`}>
                Monthly
              </span>
              <button
                onClick={() => setBillingPeriod((p) => (p === "monthly" ? "yearly" : "monthly"))}
                className={`w-12 h-6 rounded-full p-1 transition-colors ${
                  billingPeriod === "yearly" ? "bg-primary" : "bg-muted"
                }`}
                aria-label="Toggle yearly billing"
              >
                <div
                  className={`w-4 h-4 rounded-full bg-white transition-transform ${
                    billingPeriod === "yearly" ? "translate-x-6" : ""
                  }`}
                />
              </button>
              <span className={`text-sm flex items-center gap-1 ${billingPeriod === "yearly" ? "text-foreground font-medium" : "text-muted-foreground"}`}>
                Yearly
                <span className="text-xs text-primary font-medium">Save ~16%</span>
              </span>
            </div>
          </div>

          {/* Currency note — Stripe Adaptive Pricing handles local currency at checkout */}
          <p className="text-xs text-muted-foreground max-w-xl mx-auto">
            Charged in USD. At checkout, Stripe lets you pay in your local currency at today's FX rate (~1% conversion fee).
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {displayPlans.map((plan) => {
            const price = getPrice(plan, "USD", billingPeriod);
            const priceDisplay = getPriceDisplay(plan, "USD", billingPeriod);
            const yearlyTotal = getPrice(plan, "USD", "yearly") * 12;

            return (
              <Card
                key={plan.id}
                className={`relative border transition-all duration-300 hover:shadow-medium ${
                  plan.popular
                    ? "border-primary/50 shadow-medium scale-105"
                    : "border-border hover:border-primary/20"
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
                    <span className="text-4xl font-bold text-foreground">{priceDisplay}</span>
                    <span className="text-muted-foreground ml-2">/month</span>
                  </div>
                  {plan.id === "enterprise" && (
                    <p className="text-xs text-muted-foreground mt-1">Volume bands above 150 LCs/mo</p>
                  )}
                  {billingPeriod === "yearly" && price > 0 && (
                    <p className="text-xs text-primary mt-1">
                      ${yearlyTotal.toLocaleString()} billed annually
                    </p>
                  )}
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
                    <a href={plan.id === "enterprise" ? "mailto:sales@trdrhub.com?subject=Enterprise Plan Inquiry" : "/register"} className="flex items-center justify-center">
                      {plan.id === "enterprise" ? "Talk to Sales" : `Start ${plan.name}`}
                      <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                    </a>
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="text-center mt-12">
          <p className="text-sm text-muted-foreground mb-4">
            🎯 <strong>No card required to start</strong> • Pay-as-you-go from {paygDisplay}/LC • Metered per LC presentation
          </p>
          <p className="text-xs text-muted-foreground">
            Local payment via SSLCommerz (BDT) and Razorpay (INR) supported at checkout • Enterprise volume pricing available above 150 LCs/mo
          </p>
        </div>
      </div>
    </section>
  );
}
