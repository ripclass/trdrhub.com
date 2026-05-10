import { useState, useEffect } from "react";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Button } from "@/components/ui/button";
import { Check, ArrowRight, ChevronDown, HelpCircle, Building2, Zap, Sparkles } from "lucide-react";
import {
  getPriceDisplay,
  getPrice,
  getPayPerUseDisplay,
  getCurrencyFromCountry,
  tiersForTrack,
  CURRENCIES,
  type CurrencyCode,
  type PricingTrack,
  type PriceTier,
} from "@/lib/pricing";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";

const ENTERPRISE_IDS = new Set(["enterprise", "agency_enterprise"]);

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
    answer: "Yes — upgrade or downgrade at any time. We meter per LC presentation (the LC plus all its supporting documents, validated together), so a 2-doc set and a 30-doc set both count as one."
  },
  {
    question: "What payment methods do you accept?",
    answer: "All major credit cards (Visa, Mastercard, Amex). For Bangladesh, India, and Pakistan we also support local payment methods via SSLCommerz and Razorpay."
  },
  {
    question: "Is there a free option?",
    answer: "There's no permanent free plan, but you can run a quick LC check without signing up, and pay-as-you-go is just $12 per LC presentation with no commitment and no card to start. Subscriptions start at $49/mo."
  },
  {
    question: "What happens if I exceed my plan's included LCs?",
    answer: "We'll flag it before you hit the limit. Solo overage is $10/LC, Business $7/LC, Enterprise $5/LC — or upgrade to the next tier for a better per-LC rate. Agency / Services seats are unlimited within fair use."
  }
];

function PricingCard({
  tier,
  currency,
  billingPeriod,
  currencySymbol,
}: {
  tier: PriceTier;
  currency: CurrencyCode;
  billingPeriod: "monthly" | "yearly";
  currencySymbol?: string;
}) {
  const priceDisplay = tier.custom
    ? "Custom"
    : getPriceDisplay(tier, currency, billingPeriod);
  const price = tier.custom ? 0 : getPrice(tier, currency, billingPeriod);
  const yearlyTotal = tier.custom ? 0 : getPrice(tier, currency, "yearly") * 12;
  const period = tier.seatBased ? "/seat/mo" : "/mo";

  return (
    <div
      className={cn(
        "relative bg-[#00261C] border rounded-3xl p-8 flex flex-col transition-all duration-300 group",
        tier.popular
          ? "border-[#B2F273] shadow-[0_0_40px_-10px_rgba(178,242,115,0.2)] md:scale-105 z-10"
          : "border-[#EDF5F2]/10 hover:border-[#EDF5F2]/20 hover:bg-[#00382E]/30"
      )}
    >
      {tier.popular && (
        <div className="absolute -top-4 left-1/2 -translate-x-1/2">
          <span className="bg-[#B2F273] text-[#00261C] px-4 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
            Most Popular
          </span>
        </div>
      )}
      <div className="mb-8">
        <h3 className="text-xl font-bold text-white mb-2 font-display">{tier.name}</h3>
        <p className="text-[#EDF5F2]/60 text-sm h-10">{tier.description}</p>
      </div>
      <div className="mb-8">
        <div className="flex items-baseline gap-1">
          <span className="text-4xl md:text-5xl font-bold text-white font-display tracking-tight">
            {priceDisplay}
          </span>
          {!tier.custom && <span className="text-[#EDF5F2]/40">{period}</span>}
        </div>
        {!tier.custom && billingPeriod === "yearly" && price > 0 && (
          <p className="text-xs text-[#B2F273] mt-2 font-mono">
            Billed {currencySymbol}{yearlyTotal.toLocaleString()}/yr{tier.seatBased ? " per seat" : ""}
          </p>
        )}
      </div>
      <div className="flex-1 mb-8">
        <ul className="space-y-4">
          {tier.features.map((feature, i) => (
            <li key={i} className="flex items-start gap-3">
              <div className={cn(
                "w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5",
                tier.popular ? "bg-[#B2F273]" : "bg-[#00382E] border border-[#EDF5F2]/10"
              )}>
                <Check className={cn("w-3 h-3", tier.popular ? "text-[#00261C]" : "text-[#EDF5F2]/60")} />
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
          tier.popular ? "bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662]" : "bg-[#EDF5F2]/5 text-white hover:bg-[#EDF5F2]/10"
        )}
        asChild
      >
        <Link to={tier.custom ? "/contact" : "/register"}>
          {tier.custom ? "Contact Sales" : `Start ${tier.name}`}
          <ArrowRight className="w-4 h-4 ml-2" />
        </Link>
      </Button>
    </div>
  );
}

const PricingPage = () => {
  const [currency, setCurrency] = useState<CurrencyCode>("USD");
  const [showCurrencyPicker, setShowCurrencyPicker] = useState(false);
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "yearly">("monthly");
  const [track, setTrack] = useState<PricingTrack>("trader");

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

  // Tier set for the selected persona track. Enterprise (or Agency
  // Enterprise) renders in the wide card below; the rest go in the grid.
  const trackTiers = tiersForTrack(track);
  const gridTiers = trackTiers.filter(t => !ENTERPRISE_IDS.has(t.id));
  const enterpriseTier = trackTiers.find(t => ENTERPRISE_IDS.has(t.id));
  const paygDisplay = getPayPerUseDisplay("lc_validation", currency);

  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main className="pt-48 md:pt-48 pb-24 relative min-h-screen">
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
              Metered per LC presentation. Pay-as-you-go from {paygDisplay} per LC — no commitment, no card to start. Cancel anytime.
            </p>

            {/* Track toggle — Trader vs Agency/Services */}
            <div className="flex justify-center mb-6">
              <div className="flex items-center gap-1 bg-[#00382E] border border-[#EDF5F2]/10 rounded-full px-1.5 py-1.5">
                <button
                  onClick={() => setTrack("trader")}
                  className={cn(
                    "px-4 py-1.5 rounded-full text-sm font-medium transition-all",
                    track === "trader" ? "bg-[#B2F273] text-[#00261C]" : "text-[#EDF5F2]/60 hover:text-white"
                  )}
                >
                  Exporters & Importers
                </button>
                <button
                  onClick={() => setTrack("agency")}
                  className={cn(
                    "px-4 py-1.5 rounded-full text-sm font-medium transition-all",
                    track === "agency" ? "bg-[#B2F273] text-[#00261C]" : "text-[#EDF5F2]/60 hover:text-white"
                  )}
                >
                  Agencies & Services
                </button>
              </div>
            </div>

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

          {/* Pay-as-you-go callout (trader track only) */}
          {track === "trader" && (
            <div className="max-w-6xl mx-auto mb-8">
              <div className="bg-[#00382E]/40 border border-[#EDF5F2]/10 rounded-2xl px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-[#B2F273]/10 rounded-lg flex items-center justify-center shrink-0">
                    <Zap className="w-4 h-4 text-[#B2F273]" />
                  </div>
                  <div>
                    <p className="text-white font-semibold text-sm">Pay-as-you-go — {paygDisplay} per LC presentation</p>
                    <p className="text-[#EDF5F2]/50 text-xs">No subscription. Full rule coverage, sanctions screening, PDF report. Subscribe later to cut the per-LC cost.</p>
                  </div>
                </div>
                <Button size="sm" className="bg-[#EDF5F2]/10 hover:bg-[#EDF5F2]/20 text-white border-none shrink-0" asChild>
                  <Link to="/register">Get Started</Link>
                </Button>
              </div>
            </div>
          )}

          {/* Free LC check callout — the public, no-account lead magnet */}
          <div className="max-w-6xl mx-auto mb-8">
            <div className="bg-[#B2F273]/[0.06] border border-[#B2F273]/25 rounded-2xl px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 bg-[#B2F273]/15 rounded-lg flex items-center justify-center shrink-0">
                  <Sparkles className="w-4 h-4 text-[#B2F273]" />
                </div>
                <div>
                  <p className="text-white font-semibold text-sm">Want to try it first? Run a free LC check — no account needed.</p>
                  <p className="text-[#EDF5F2]/50 text-xs">Upload an LC and its documents, get the verdict and the top findings. One free check per day.</p>
                </div>
              </div>
              <Button size="sm" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-semibold border-none shrink-0" asChild>
                <Link to="/check">Check an LC free</Link>
              </Button>
            </div>
          </div>

          {/* Pricing Grid */}
          <div className={cn(
            "grid grid-cols-1 gap-8 max-w-6xl mx-auto mb-12",
            gridTiers.length >= 2 ? "md:grid-cols-2" : "md:grid-cols-1",
          )}>
            {gridTiers.map((plan) => (
              <PricingCard
                key={plan.id}
                tier={plan}
                currency={currency}
                billingPeriod={billingPeriod}
                currencySymbol={currencyInfo?.symbol}
              />
            ))}
          </div>

          {/* Enterprise / Agency Enterprise wide card */}
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
                      <h3 className="text-2xl font-bold text-white font-display">{enterpriseTier.name}</h3>
                    </div>
                    <p className="text-[#EDF5F2]/60 text-lg mb-8 max-w-xl">
                      {enterpriseTier.description}. Custom integrations, SLA guarantees, dedicated support.
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {enterpriseTier.features.map((feature, i) => (
                        <div key={i} className="flex items-center gap-3">
                          <Check className="w-4 h-4 text-[#B2F273] shrink-0" />
                          <span className="text-[#EDF5F2]/80 text-sm">{feature}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="w-full md:w-auto flex flex-col items-center gap-4">
                    <div className="text-center mb-2">
                      {enterpriseTier.custom ? (
                        <>
                          <span className="text-3xl font-bold text-white font-display">Custom</span>
                          <p className="text-[#EDF5F2]/40 text-sm">Per-seat with volume discounts</p>
                        </>
                      ) : (
                        <>
                          <span className="text-3xl font-bold text-white font-display">
                            {getPriceDisplay(enterpriseTier, currency, billingPeriod)}
                          </span>
                          <span className="text-[#EDF5F2]/40 text-sm">/mo</span>
                          <p className="text-[#EDF5F2]/40 text-xs mt-1">Volume bands above 150 LCs/mo</p>
                        </>
                      )}
                    </div>
                    <Button
                      size="lg"
                      className="bg-white text-[#00261C] hover:bg-[#EDF5F2] px-8 font-bold border-none min-w-[200px]"
                      asChild
                    >
                      <Link to="/contact">
                        {enterpriseTier.custom ? "Contact Sales" : "Talk to Sales"}
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
