import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check, ArrowRight } from "lucide-react";

interface PricingTier {
  tier: string;
  price: string;           // USD price string like "$49/mo" or "$0"
  description?: string;
  features: string[];
  popular?: boolean;
  checks?: string;
  lookups?: string;
  docs?: string;
  lcs?: string;
  screens?: string;
  searches?: string;
  reports?: string;
  containers?: string;
  calcs?: string;
  comparisons?: string;
}

interface ToolPricingSectionProps {
  title?: string;
  subtitle?: string;
  tiers: PricingTier[];
  toolSlug?: string;
}

/**
 * Generic per-tool pricing section. Used by tool landing pages (currently
 * only `/price-verify`, which is a parked tool — Price Verify launches
 * later in the roadmap).
 *
 * USD-only since 2026-05-11 (Phase 1 of "lock to USD") — Stripe Adaptive
 * Pricing handles local-currency conversion at checkout. The previous
 * version maintained its own per-currency conversion table (USD/BDT/INR/
 * PKR/EUR/GBP) with stale FX multipliers; that's gone.
 */
export function ToolPricingSection({
  title = "Simple, Transparent Pricing",
  subtitle = "Pay-as-you-go from $12 per LC. Subscriptions starting at $49/mo.",
  tiers,
}: ToolPricingSectionProps) {
  return (
    <section className="py-20 bg-muted/30">
      <div className="container mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-foreground mb-4">{title}</h2>
          <p className="text-lg text-muted-foreground mb-2">{subtitle}</p>
          <p className="text-xs text-muted-foreground max-w-xl mx-auto">
            Charged in USD. At checkout, Stripe lets you pay in your local currency at today's FX rate (~1% conversion fee).
          </p>
        </div>

        <div
          className={`grid gap-6 max-w-5xl mx-auto ${
            tiers.length === 4 ? "md:grid-cols-4" : "md:grid-cols-3"
          }`}
        >
          {tiers.map((tier, index) => {
            const isFree = tier.price === "$0" || /^\$0\b/.test(tier.price);
            const usageLimit =
              tier.checks ||
              tier.lookups ||
              tier.docs ||
              tier.lcs ||
              tier.screens ||
              tier.searches ||
              tier.reports ||
              tier.containers ||
              tier.calcs ||
              tier.comparisons;

            return (
              <Card
                key={index}
                className={`relative transition-all duration-300 hover:shadow-lg ${
                  tier.popular
                    ? "border-primary shadow-lg scale-105 z-10"
                    : "border-gray-200"
                }`}
              >
                {tier.popular && (
                  <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary">
                    Most Popular
                  </Badge>
                )}

                <CardHeader className="text-center pb-4">
                  <CardTitle className="text-xl font-bold">{tier.tier}</CardTitle>
                  {tier.description && (
                    <CardDescription className="text-sm">
                      {tier.description}
                    </CardDescription>
                  )}
                  <div className="mt-4">
                    <span className="text-3xl font-bold text-foreground">
                      {tier.price.replace("/mo", "")}
                    </span>
                    {tier.price.includes("/mo") && (
                      <span className="text-muted-foreground">/mo</span>
                    )}
                  </div>
                  {usageLimit && (
                    <p className="text-sm text-muted-foreground mt-1">{usageLimit}</p>
                  )}
                </CardHeader>

                <CardContent className="pt-0">
                  <ul className="space-y-2 mb-6">
                    {tier.features.map((feature, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm">
                        <Check className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                        <span className="text-muted-foreground">{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <Button
                    className={`w-full group ${tier.popular ? "bg-primary" : ""}`}
                    variant={tier.popular ? "default" : "outline"}
                    asChild
                  >
                    <a href="/register">
                      {isFree ? "Get Started" : `Start ${tier.tier}`}
                      <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                    </a>
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </section>
  );
}
