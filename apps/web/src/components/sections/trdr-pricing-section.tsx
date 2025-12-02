"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Check, ArrowRight, Globe, ChevronDown } from "lucide-react";
import { 
  PRICING_TIERS, 
  getPriceDisplay, 
  getPrice, 
  getCurrencyFromCountry,
  CURRENCIES,
  type CurrencyCode 
} from "@/lib/pricing";

// Currency options for manual selection
const CURRENCY_OPTIONS: { code: CurrencyCode; flag: string; label: string }[] = [
  { code: "BDT", flag: "🇧🇩", label: "Bangladesh (৳)" },
  { code: "INR", flag: "🇮🇳", label: "India (₹)" },
  { code: "PKR", flag: "🇵🇰", label: "Pakistan (Rs)" },
  { code: "USD", flag: "🇺🇸", label: "USD ($)" },
  { code: "EUR", flag: "🇪🇺", label: "Euro (€)" },
  { code: "GBP", flag: "🇬🇧", label: "UK (£)" },
  { code: "AED", flag: "🇦🇪", label: "UAE (د.إ)" },
  { code: "SGD", flag: "🇸🇬", label: "Singapore (S$)" },
];

export function TRDRPricingSection() {
  const [currency, setCurrency] = useState<CurrencyCode>("USD");
  const [showCurrencyPicker, setShowCurrencyPicker] = useState(false);
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "yearly">("monthly");

  // Try to auto-detect country/currency on mount
  useEffect(() => {
    async function detectCurrency() {
      try {
        // Try geo API first
        const res = await fetch("/api/geo");
        if (res.ok) {
          const data = await res.json();
          if (data.country && data.detected) {
            setCurrency(getCurrencyFromCountry(data.country));
            return;
          }
        }
      } catch {
        // Geo API failed, try timezone detection as fallback
      }
      
      // Fallback: detect from timezone
      try {
        const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        if (tz.includes("Dhaka") || tz.includes("Asia/Dhaka")) {
          setCurrency("BDT");
        } else if (tz.includes("Kolkata") || tz.includes("Asia/Kolkata") || tz.includes("Mumbai")) {
          setCurrency("INR");
        } else if (tz.includes("Karachi") || tz.includes("Asia/Karachi")) {
          setCurrency("PKR");
        } else if (tz.includes("Dubai") || tz.includes("Asia/Dubai")) {
          setCurrency("AED");
        } else if (tz.includes("Singapore")) {
          setCurrency("SGD");
        } else if (tz.includes("London") || tz.includes("Europe/London")) {
          setCurrency("GBP");
        } else if (tz.includes("Europe/")) {
          setCurrency("EUR");
        }
        // else stay USD
      } catch {
        // Default to USD
      }
    }
    detectCurrency();
  }, []);

  const displayPlans = PRICING_TIERS.filter(t => t.id !== "free"); // Hide free tier on landing

  const currencyInfo = CURRENCIES[currency];
  const selectedCurrencyOption = CURRENCY_OPTIONS.find(c => c.code === currency) || CURRENCY_OPTIONS[3];

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
            Choose the plan that fits your business needs. All plans include a 14-day free trial.
          </p>

          {/* Currency & Billing Toggle */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
            {/* Currency Selector */}
            <div className="relative">
              <button
                onClick={() => setShowCurrencyPicker(!showCurrencyPicker)}
                className="flex items-center gap-2 bg-muted/50 hover:bg-muted/70 rounded-full px-4 py-2 text-sm transition-colors"
              >
                <span>{selectedCurrencyOption.flag}</span>
                <span className="text-foreground">{selectedCurrencyOption.label}</span>
                <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${showCurrencyPicker ? 'rotate-180' : ''}`} />
              </button>
              
              {showCurrencyPicker && (
                <div className="absolute top-full left-0 mt-2 bg-card border rounded-lg shadow-lg z-50 min-w-[180px]">
                  {CURRENCY_OPTIONS.map((option) => (
                    <button
                      key={option.code}
                      onClick={() => {
                        setCurrency(option.code);
                        setShowCurrencyPicker(false);
                      }}
                      className={`w-full flex items-center gap-2 px-4 py-2 text-sm hover:bg-muted/50 transition-colors first:rounded-t-lg last:rounded-b-lg ${
                        currency === option.code ? "bg-muted/30 text-primary" : "text-foreground"
                      }`}
                    >
                      <span>{option.flag}</span>
                      <span>{option.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Billing Period Toggle */}
            <div className="flex items-center gap-3 bg-muted/50 rounded-full px-4 py-2">
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
                <span className="text-xs text-primary font-medium">Save ~15%</span>
              </span>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto">
          {displayPlans.map((plan, index) => {
            const price = getPrice(plan, currency, billingPeriod);
            const priceDisplay = getPriceDisplay(plan, currency, billingPeriod);
            const yearlyTotal = getPrice(plan, currency, "yearly") * 12;

            return (
              <Card 
                key={plan.id} 
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
                    {plan.id === "enterprise" ? (
                      <>
                        <span className="text-4xl font-bold text-foreground">Custom</span>
                        <span className="text-muted-foreground ml-2">pricing</span>
                      </>
                    ) : (
                      <>
                        <span className="text-4xl font-bold text-foreground">{priceDisplay}</span>
                        <span className="text-muted-foreground ml-2">/month</span>
                      </>
                    )}
                  </div>
                  {billingPeriod === "yearly" && plan.id !== "enterprise" && price > 0 && (
                    <p className="text-xs text-primary mt-1">
                      {currencyInfo?.symbol}{yearlyTotal.toLocaleString()} billed annually
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
                      {plan.id === "enterprise" ? "Contact Sales" : "Start Free Trial"}
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
            🎯 <strong>14-day free trial</strong> on all plans • No credit card required
          </p>
          <p className="text-xs text-muted-foreground">
            {currency === "BDT" && "Local payment via SSLCommerz available • "}
            {currency === "INR" && "Local payment via Razorpay available • "}
            Prices shown in {currencyInfo?.name || "USD"}
            {currency !== "USD" && " • Enterprise pricing customized to your requirements"}
          </p>
        </div>
      </div>
    </section>
  );
}
