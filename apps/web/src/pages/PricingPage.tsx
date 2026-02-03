import { useState, useEffect } from "react";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Button } from "@/components/ui/button";
import { Check, ArrowRight, ChevronDown, HelpCircle, Building2 } from "lucide-react";
import { 
  PRICING_TIERS, 
  getPriceDisplay, 
  getPrice, 
  getCurrencyFromCountry,
  CURRENCIES,
  type CurrencyCode 
} from "@/lib/pricing";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";

// Currency options for manual selection
const CURRENCY_OPTIONS: { code: CurrencyCode; flag: string; label: string }[] = [
  { code: "USD", flag: "🇺🇸", label: "USD ($)" },
  { code: "BDT", flag: "🇧🇩", label: "Bangladesh (৳)" },
  { code: "INR", flag: "🇮🇳", label: "India (₹)" },
  { code: "PKR", flag: "🇵🇰", label: "Pakistan (Rs)" },
  { code: "EUR", flag: "🇪🇺", label: "Euro (€)" },
  { code: "GBP", flag: "🇬🇧", label: "UK (£)" },
  { code: "AED", flag: "🇦🇪", label: "UAE (د.إ)" },
  { code: "SGD", flag: "🇸🇬", label: "Singapore (S$)" },
];

const faqs = [
  {
    question: "Can I switch plans later?",
    answer: "Yes, you can upgrade or downgrade your plan at any time. Prorated charges will be applied automatically."
  },
  {
    question: "What payment methods do you accept?",
    answer: "We accept all major credit cards (Visa, Mastercard, Amex). For Bangladesh, India, and Pakistan, we also support local payment methods via SSLCommerz and Razorpay."
  },
  {
    question: "Is there a free trial?",
    answer: "Yes, all paid plans come with a 14-day free trial. No credit card is required to start testing the platform."
  },
  {
    question: "What happens if I exceed my limits?",
    answer: "We'll notify you when you're close to your limit. You can either upgrade your plan or pay for overages at our standard pay-per-use rates."
  }
];

const PricingPage = () => {
  const [currency, setCurrency] = useState<CurrencyCode>("USD");
  const [showCurrencyPicker, setShowCurrencyPicker] = useState(false);
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "yearly">("monthly");

  // Auto-detect currency
  useEffect(() => {
    async function detectCurrency() {
      try {
        const res = await fetch("/api/geo");
        if (res.ok) {
          const data = await res.json();
          if (data.country && data.detected) {
            setCurrency(getCurrencyFromCountry(data.country));
            return;
          }
        }
      } catch {
        // Fallback to timezone
        try {
          const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
          if (tz.includes("Dhaka")) setCurrency("BDT");
          else if (tz.includes("Kolkata") || tz.includes("Mumbai")) setCurrency("INR");
          else if (tz.includes("Karachi")) setCurrency("PKR");
          else if (tz.includes("Dubai")) setCurrency("AED");
          else if (tz.includes("Singapore")) setCurrency("SGD");
          else if (tz.includes("London")) setCurrency("GBP");
          else if (tz.includes("Europe/")) setCurrency("EUR");
        } catch {}
      }
    }
    detectCurrency();
  }, []);

  const selectedCurrencyOption = CURRENCY_OPTIONS.find(c => c.code === currency) || CURRENCY_OPTIONS[0];
  const currencyInfo = CURRENCIES[currency];

  // Filter out Enterprise for the main grid, we'll show it separately
  const mainTiers = PRICING_TIERS.filter(t => t.id !== 'enterprise');
  const enterpriseTier = PRICING_TIERS.find(t => t.id === 'enterprise');

  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main className="pt-32 md:pt-48 pb-24 relative min-h-screen">
        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none fixed" />

        {/* Background decoration */}
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
        <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          
          {/* Header */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full border border-[#B2F273]/20 bg-[#B2F273]/5 backdrop-blur-sm mb-6">
              <span className="text-[#B2F273] font-mono text-xs tracking-wider uppercase">Transparent Pricing</span>
            </div>
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-white mb-6 leading-tight font-display">
              Plans that scale
              <br />
              <span className="text-[#B2F273] text-glow-sm">with your trade volume.</span>
            </h1>
            <p className="text-lg text-[#EDF5F2]/60 max-w-2xl mx-auto font-light leading-relaxed mb-10">
              Start with a 14-day free trial. No credit card required. Cancel anytime.
            </p>

            {/* Controls */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              {/* Currency Selector */}
              <div className="relative">
                <button
                  onClick={() => setShowCurrencyPicker(!showCurrencyPicker)}
                  className="flex items-center gap-2 bg-[#00382E] border border-[#EDF5F2]/10 hover:border-[#B2F273]/50 rounded-full px-4 py-2.5 text-sm transition-all text-white min-w-[160px] justify-between"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{selectedCurrencyOption.flag}</span>
                    <span>{selectedCurrencyOption.label}</span>
                  </div>
                  <ChevronDown className={cn("w-4 h-4 text-[#EDF5F2]/40 transition-transform", showCurrencyPicker && "rotate-180")} />
                </button>
                
                {showCurrencyPicker && (
                  <div className="absolute top-full left-0 mt-2 bg-[#00382E] border border-[#EDF5F2]/10 rounded-xl shadow-xl z-50 min-w-[180px] overflow-hidden py-1">
                    {CURRENCY_OPTIONS.map((option) => (
                      <button
                        key={option.code}
                        onClick={() => {
                          setCurrency(option.code);
                          setShowCurrencyPicker(false);
                        }}
                        className={cn(
                          "w-full flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-[#B2F273]/10 transition-colors text-left",
                          currency === option.code ? "text-[#B2F273]" : "text-[#EDF5F2]/80"
                        )}
                      >
                        <span className="text-lg">{option.flag}</span>
                        <span>{option.label}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Billing Toggle */}
              <div className="flex items-center gap-3 bg-[#00382E] border border-[#EDF5F2]/10 rounded-full px-1.5 py-1.5">
                <button
                  onClick={() => setBillingPeriod("monthly")}
                  className={cn(
                    "px-4 py-1.5 rounded-full text-sm font-medium transition-all",
                    billingPeriod === "monthly" 
                      ? "bg-[#B2F273] text-[#00261C]" 
                      : "text-[#EDF5F2]/60 hover:text-white"
                  )}
                >
                  Monthly
                </button>
                <button
                  onClick={() => setBillingPeriod("yearly")}
                  className={cn(
                    "px-4 py-1.5 rounded-full text-sm font-medium transition-all flex items-center gap-2",
                    billingPeriod === "yearly" 
                      ? "bg-[#B2F273] text-[#00261C]" 
                      : "text-[#EDF5F2]/60 hover:text-white"
                  )}
                >
                  Yearly
                  <span className={cn(
                    "text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wide",
                    billingPeriod === "yearly" ? "bg-[#00261C]/20 text-[#00261C]" : "bg-[#B2F273] text-[#00261C]"
                  )}>
                    -16%
                  </span>
                </button>
              </div>
            </div>
          </div>

          {/* Pricing Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto mb-12">
            {mainTiers.map((plan) => {
              const priceDisplay = getPriceDisplay(plan, currency, billingPeriod);
              const price = getPrice(plan, currency, billingPeriod);
              const yearlyTotal = getPrice(plan, currency, "yearly") * 12;

              return (
                <div 
                  key={plan.id}
                  className={cn(
                    "relative bg-[#00261C] border rounded-3xl p-8 flex flex-col transition-all duration-300 group",
                    plan.popular 
                      ? "border-[#B2F273] shadow-[0_0_40px_-10px_rgba(178,242,115,0.2)] scale-105 z-10" 
                      : "border-[#EDF5F2]/10 hover:border-[#EDF5F2]/20 hover:bg-[#00382E]/30"
                  )}
                >
                  {plan.popular && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                      <span className="bg-[#B2F273] text-[#00261C] px-4 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
                        Most Popular
                      </span>
                    </div>
                  )}

                  <div className="mb-8">
                    <h3 className="text-xl font-bold text-white mb-2 font-display">{plan.name}</h3>
                    <p className="text-[#EDF5F2]/60 text-sm h-10">{plan.description}</p>
                  </div>

                  <div className="mb-8">
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl md:text-5xl font-bold text-white font-display tracking-tight">
                        {priceDisplay}
                      </span>
                      <span className="text-[#EDF5F2]/40">/mo</span>
                    </div>
                    {billingPeriod === "yearly" && price > 0 && (
                      <p className="text-xs text-[#B2F273] mt-2 font-mono">
                        Billed {currencyInfo?.symbol}{yearlyTotal.toLocaleString()} yearly
                      </p>
                    )}
                  </div>

                  <div className="flex-1 mb-8">
                    <ul className="space-y-4">
                      {plan.features.map((feature, i) => (
                        <li key={i} className="flex items-start gap-3">
                          <div className={cn(
                            "w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5",
                            plan.popular ? "bg-[#B2F273]" : "bg-[#00382E] border border-[#EDF5F2]/10"
                          )}>
                            <Check className={cn(
                              "w-3 h-3",
                              plan.popular ? "text-[#00261C]" : "text-[#EDF5F2]/60"
                            )} />
                          </div>
                          <span className="text-[#EDF5F2]/80 text-sm leading-relaxed">{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <Button 
                    size="lg"
                    className={cn(
                      "w-full font-bold h-12 border-none transition-all duration-300",
                      plan.popular 
                        ? "bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662]" 
                        : "bg-[#EDF5F2]/5 text-white hover:bg-[#EDF5F2]/10"
                    )}
                    asChild
                  >
                    <Link to="/register">
                      Start Free Trial
                      <ArrowRight className="w-4 h-4 ml-2" />
                    </Link>
                  </Button>
                </div>
              );
            })}
          </div>

          {/* Enterprise Card */}
          {enterpriseTier && (
            <div className="max-w-6xl mx-auto mb-24">
              <div className="bg-[#00382E]/30 border border-[#EDF5F2]/10 rounded-3xl p-8 md:p-12 relative overflow-hidden group hover:border-[#B2F273]/30 transition-colors">
                <div className="absolute top-0 right-0 w-64 h-64 bg-[#B2F273]/5 rounded-full blur-3xl" />
                
                <div className="flex flex-col md:flex-row gap-12 items-center relative z-10">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 bg-[#B2F273]/10 rounded-xl flex items-center justify-center">
                        <Building2 className="w-5 h-5 text-[#B2F273]" />
                      </div>
                      <h3 className="text-2xl font-bold text-white font-display">Enterprise</h3>
                    </div>
                    <p className="text-[#EDF5F2]/60 text-lg mb-8 max-w-xl">
                      For banks and large organizations requiring custom integrations, SLA guarantees, and dedicated support.
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {enterpriseTier.features.map((feature, i) => (
                        <div key={i} className="flex items-center gap-3">
                          <Check className="w-4 h-4 text-[#B2F273]" />
                          <span className="text-[#EDF5F2]/80 text-sm">{feature}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  <div className="w-full md:w-auto flex flex-col items-center gap-4">
                    <div className="text-center mb-2">
                      <span className="text-3xl font-bold text-white font-display">Custom</span>
                      <p className="text-[#EDF5F2]/40 text-sm">Volume-based pricing</p>
                    </div>
                    <Button 
                      size="lg"
                      className="bg-white text-[#00261C] hover:bg-[#EDF5F2] px-8 font-bold border-none min-w-[200px]"
                      asChild
                    >
                      <Link to="/contact">
                        Contact Sales
                      </Link>
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* FAQ Section */}
          <div className="max-w-3xl mx-auto mb-24">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-white mb-4 font-display">Frequently Asked Questions</h2>
              <p className="text-[#EDF5F2]/60">Everything you need to know about our pricing.</p>
            </div>
            
            <div className="space-y-4">
              {faqs.map((faq, index) => (
                <div key={index} className="bg-[#00382E]/20 border border-[#EDF5F2]/10 rounded-2xl p-6 hover:bg-[#00382E]/40 transition-colors">
                  <h3 className="text-lg font-bold text-white mb-2 flex items-start gap-3">
                    <HelpCircle className="w-5 h-5 text-[#B2F273] shrink-0 mt-1" />
                    {faq.question}
                  </h3>
                  <p className="text-[#EDF5F2]/60 pl-8 leading-relaxed">
                    {faq.answer}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Trust Footer */}
          <div className="text-center border-t border-[#EDF5F2]/10 pt-16">
            <p className="text-[#EDF5F2]/40 text-sm font-mono uppercase tracking-widest mb-8">
              Trusted by trade teams at
            </p>
            <div className="flex flex-wrap justify-center gap-x-12 gap-y-8 opacity-50 grayscale hover:grayscale-0 transition-all duration-500">
              {["HSBC", "Standard Chartered", "Maersk", "CMA CGM", "DB Schenker"].map((brand) => (
                <span key={brand} className="text-xl font-bold text-white/80">{brand}</span>
              ))}
            </div>
          </div>

        </div>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default PricingPage;
