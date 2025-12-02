"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check, ArrowRight, Globe } from "lucide-react";
import { 
  getCurrencyFromCountry,
  CURRENCIES,
  type CurrencyCode 
} from "@/lib/pricing";

// Conversion rates from USD (approximate, for display only)
const CONVERSION_RATES: Record<CurrencyCode, number> = {
  USD: 1,
  BDT: 85,      // 1 USD ≈ 85 BDT
  INR: 69,      // 1 USD ≈ 69 INR  (local pricing makes it ~₹1999 for $29)
  PKR: 172,     // 1 USD ≈ 172 PKR
  EUR: 0.92,
  GBP: 0.79,
  AED: 3.67,
  SGD: 1.35,
  AUD: 1.55,
};

interface PricingTier {
  tier: string;
  price: string;           // Base USD price like "$49/mo" or "$0"
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

// Parse USD price string to number
function parseUSDPrice(priceStr: string): number | null {
  const match = priceStr.match(/\$(\d+)/);
  return match ? parseInt(match[1]) : null;
}

// Convert USD to local currency
function convertPrice(usdPrice: number, currency: CurrencyCode): number {
  // Apply special fixed pricing for key markets
  if (currency === "BDT") {
    // BD pricing is ~86x multiplier from USD (৳2500 for $29)
    return Math.round(usdPrice * 86);
  }
  if (currency === "INR") {
    // IN pricing is ~69x multiplier from USD (₹1999 for $29)
    return Math.round(usdPrice * 69);
  }
  if (currency === "PKR") {
    // PK pricing is ~172x multiplier from USD (Rs4999 for $29)
    return Math.round(usdPrice * 172);
  }
  // Default conversion for other currencies
  return Math.round(usdPrice * CONVERSION_RATES[currency]);
}

// Format price in local currency
function formatLocalPrice(priceStr: string, currency: CurrencyCode): string {
  const usdPrice = parseUSDPrice(priceStr);
  if (usdPrice === null || usdPrice === 0) {
    return priceStr.includes("0") ? "Free" : priceStr;
  }

  const localPrice = convertPrice(usdPrice, currency);
  const currencyInfo = CURRENCIES[currency];
  const period = priceStr.includes("/mo") ? "/mo" : "";

  if (currencyInfo?.position === "after") {
    return `${localPrice.toLocaleString()} ${currencyInfo.symbol}${period}`;
  }
  return `${currencyInfo?.symbol || "$"}${localPrice.toLocaleString()}${period}`;
}

export function ToolPricingSection({ 
  title = "Simple, Transparent Pricing",
  subtitle = "Start free, upgrade as you grow",
  tiers,
  toolSlug
}: ToolPricingSectionProps) {
  const [currency, setCurrency] = useState<CurrencyCode>("USD");
  const [detected, setDetected] = useState(false);

  useEffect(() => {
    async function detectCurrency() {
      try {
        const res = await fetch("/api/geo");
        const data = await res.json();
        if (data.country) {
          setCurrency(getCurrencyFromCountry(data.country));
          setDetected(true);
        }
      } catch {
        // Default to USD
      }
    }
    detectCurrency();
  }, []);

  const currencyInfo = CURRENCIES[currency];

  return (
    <section className="py-20 bg-muted/30">
      <div className="container mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-foreground mb-4">{title}</h2>
          <p className="text-lg text-muted-foreground mb-4">{subtitle}</p>
          
          {detected && currency !== "USD" && (
            <div className="inline-flex items-center gap-2 text-sm text-muted-foreground bg-muted rounded-full px-4 py-2">
              <Globe className="w-4 h-4" />
              <span>Prices shown in {currencyInfo?.name}</span>
            </div>
          )}
        </div>

        <div className={`grid gap-6 max-w-5xl mx-auto ${
          tiers.length === 3 ? "md:grid-cols-3" : 
          tiers.length === 4 ? "md:grid-cols-4" : 
          "md:grid-cols-3"
        }`}>
          {tiers.map((tier, index) => {
            const localPrice = formatLocalPrice(tier.price, currency);
            const usageLimit = tier.checks || tier.lookups || tier.docs || tier.lcs || 
                              tier.screens || tier.searches || tier.reports || 
                              tier.containers || tier.calcs || tier.comparisons;

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
                      {localPrice.replace("/mo", "")}
                    </span>
                    {localPrice.includes("/mo") && (
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
                      {tier.price === "$0" ? "Get Started" : "Start Free Trial"}
                      <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                    </a>
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="text-center mt-8">
          <p className="text-sm text-muted-foreground">
            🎯 All paid plans include 14-day free trial • No credit card required
            {currency === "BDT" && " • Pay with bKash/Nagad via SSLCommerz"}
            {currency === "INR" && " • Pay with UPI/Cards via Razorpay"}
          </p>
        </div>
      </div>
    </section>
  );
}

