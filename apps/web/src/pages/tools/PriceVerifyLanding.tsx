import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  DollarSign, 
  ArrowRight, 
  CheckCircle, 
  AlertTriangle, 
  TrendingUp,
  Building2,
  Shield,
  FileText,
  BarChart3,
  Globe,
  Zap,
  Clock
} from "lucide-react";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";

export default function PriceVerifyLanding() {
  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      
      {/* Hero Section */}
      <section className="pt-24 sm:pt-32 pb-12 sm:pb-20 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-green-500/5 via-transparent to-transparent" />
        <div className="absolute top-1/4 right-0 w-96 h-96 bg-green-500/10 rounded-full blur-3xl" />
        
        <div className="container mx-auto px-4 sm:px-6 relative z-10">
          <div className="max-w-4xl mx-auto text-center">
            <Badge className="mb-6 bg-amber-500/20 text-amber-400 border-amber-500/30 px-4 py-1.5">
              🏦 Built for Banks • Direct Request
            </Badge>
            
            <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
              Catch Price Anomalies
              <br />
              <span className="text-green-400">Before They Become Problems</span>
            </h1>
            
            <p className="text-lg sm:text-xl text-slate-400 mb-8 max-w-2xl mx-auto">
              Verify trade document prices against real-time market data. Detect over/under invoicing 
              and trade-based money laundering risks in seconds.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
              <Button size="lg" className="bg-green-500 hover:bg-green-600 text-white px-8 h-12" asChild>
                <Link to="/price-verify/tool">
                  Try It Free
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" className="border-slate-700 text-white hover:bg-slate-800 px-8 h-12">
                View Demo
              </Button>
            </div>
            
            {/* Trust indicators */}
            <div className="flex flex-wrap justify-center gap-6 text-sm text-slate-500">
              <span className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                50+ Commodities
              </span>
              <span className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                Real-Time Market Data
              </span>
              <span className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-500" />
                TBML Detection
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 sm:py-16 border-y border-slate-800 bg-slate-900/50">
        <div className="container mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-2xl sm:text-4xl font-bold text-white mb-2">50+</div>
              <div className="text-sm text-slate-400">Commodities Covered</div>
            </div>
            <div>
              <div className="text-2xl sm:text-4xl font-bold text-white mb-2">&lt;30s</div>
              <div className="text-sm text-slate-400">Verification Time</div>
            </div>
            <div>
              <div className="text-2xl sm:text-4xl font-bold text-white mb-2">±15%</div>
              <div className="text-sm text-slate-400">Variance Tolerance</div>
            </div>
            <div>
              <div className="text-2xl sm:text-4xl font-bold text-white mb-2">6+</div>
              <div className="text-sm text-slate-400">Data Sources</div>
            </div>
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="py-12 sm:py-20">
        <div className="container mx-auto px-4 sm:px-6">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-10 sm:mb-16 text-center">
              Trade-Based Money Laundering is a
              <br />
              <span className="text-red-400">$2 Trillion Problem</span>
            </h2>
            
            <div className="grid md:grid-cols-2 gap-6 sm:gap-8">
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <AlertTriangle className="w-10 h-10 text-red-400 mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">Over-Invoicing</h3>
                <p className="text-slate-400 text-sm">
                  Importers pay inflated prices, moving excess funds abroad illegally. 
                  Without market data, banks can't detect these anomalies.
                </p>
              </div>
              
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <AlertTriangle className="w-10 h-10 text-orange-400 mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">Under-Invoicing</h3>
                <p className="text-slate-400 text-sm">
                  Exporters receive below-market payments, evading taxes and capital controls. 
                  Manual checks miss 90% of cases.
                </p>
              </div>
              
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <Clock className="w-10 h-10 text-yellow-400 mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">Manual Process</h3>
                <p className="text-slate-400 text-sm">
                  Banks spend 30-60 minutes per transaction Googling prices. 
                  Results are inconsistent and undocumented.
                </p>
              </div>
              
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <Shield className="w-10 h-10 text-blue-400 mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">Regulatory Pressure</h3>
                <p className="text-slate-400 text-sm">
                  FATF guidelines require price verification. 
                  Banks need auditable compliance records.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Solution Section */}
      <section className="py-12 sm:py-20 bg-slate-900/30">
        <div className="container mx-auto px-4 sm:px-6">
          <div className="max-w-4xl mx-auto text-center mb-10 sm:mb-16">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4">
              Verify Prices in <span className="text-green-400">Under 30 Seconds</span>
            </h2>
            <p className="text-slate-400">
              Upload documents or enter prices manually. Get instant market comparisons.
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-6 sm:gap-8 max-w-5xl mx-auto">
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 text-center">
              <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                <FileText className="w-6 h-6 text-green-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">1. Upload Document</h3>
              <p className="text-slate-400 text-sm">
                Drop your invoice, LC, or contract. We extract commodity, quantity, and price automatically.
              </p>
            </div>
            
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 text-center">
              <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                <TrendingUp className="w-6 h-6 text-green-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">2. Compare to Market</h3>
              <p className="text-slate-400 text-sm">
                We check ICE, LME, USDA, and industry indices. Real-time and historical data.
              </p>
            </div>
            
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 text-center">
              <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
                <BarChart3 className="w-6 h-6 text-green-400" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">3. Get Verdict</h3>
              <p className="text-slate-400 text-sm">
                Clear variance analysis with risk flags. Download compliance-ready PDF reports.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Commodities Section */}
      <section className="py-12 sm:py-20">
        <div className="container mx-auto px-4 sm:px-6">
          <div className="max-w-4xl mx-auto text-center mb-10 sm:mb-16">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4">
              50+ Commodities. <span className="text-green-400">Bangladesh Focus.</span>
            </h2>
            <p className="text-slate-400">
              Optimized for Bangladesh's top export and import categories.
            </p>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 max-w-5xl mx-auto">
            {[
              { name: "Raw Cotton", icon: "🧶" },
              { name: "Steel Coils", icon: "🔩" },
              { name: "Garments", icon: "👕" },
              { name: "Rice & Grains", icon: "🌾" },
              { name: "Fuel Oil", icon: "⛽" },
              { name: "Chemicals", icon: "🧪" },
            ].map((commodity, i) => (
              <div key={i} className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-center">
                <div className="text-2xl mb-2">{commodity.icon}</div>
                <div className="text-sm text-slate-300">{commodity.name}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* For Banks Section */}
      <section className="py-12 sm:py-20 bg-slate-900/30">
        <div className="container mx-auto px-4 sm:px-6">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-center gap-3 mb-6">
              <Building2 className="w-8 h-8 text-amber-400" />
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white">
                Built for <span className="text-amber-400">Banks</span>
              </h2>
            </div>
            <p className="text-slate-400 text-center mb-10 sm:mb-12">
              Direct feedback from trade finance departments shaped every feature.
            </p>
            
            <div className="grid md:grid-cols-2 gap-6">
              <div className="flex items-start gap-4 p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
                <CheckCircle className="w-6 h-6 text-green-400 flex-shrink-0 mt-1" />
                <div>
                  <h4 className="font-semibold text-white mb-1">TBML Risk Scoring</h4>
                  <p className="text-sm text-slate-400">Auto-flag transactions with &gt;25% variance for enhanced due diligence.</p>
                </div>
              </div>
              
              <div className="flex items-start gap-4 p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
                <CheckCircle className="w-6 h-6 text-green-400 flex-shrink-0 mt-1" />
                <div>
                  <h4 className="font-semibold text-white mb-1">Audit Trail</h4>
                  <p className="text-sm text-slate-400">Every price check logged with timestamp, user, and source data for regulators.</p>
                </div>
              </div>
              
              <div className="flex items-start gap-4 p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
                <CheckCircle className="w-6 h-6 text-green-400 flex-shrink-0 mt-1" />
                <div>
                  <h4 className="font-semibold text-white mb-1">LCopilot Integration</h4>
                  <p className="text-sm text-slate-400">Auto-verify prices when processing LC documents. One seamless workflow.</p>
                </div>
              </div>
              
              <div className="flex items-start gap-4 p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
                <CheckCircle className="w-6 h-6 text-green-400 flex-shrink-0 mt-1" />
                <div>
                  <h4 className="font-semibold text-white mb-1">Multi-Source Verification</h4>
                  <p className="text-sm text-slate-400">ICE, LME, USDA, FAO, and industry indices. Never rely on a single source.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-12 sm:py-20">
        <div className="container mx-auto px-4 sm:px-6">
          <div className="max-w-4xl mx-auto text-center mb-10 sm:mb-16">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4">
              Simple, Transparent Pricing
            </h2>
            <p className="text-slate-400">
              Start free. Scale as you grow.
            </p>
          </div>
          
          <div className="grid md:grid-cols-4 gap-6 max-w-5xl mx-auto">
            {[
              { tier: "Free", price: "$0", checks: "10/month", features: ["Basic verification", "3 commodities", "PDF reports"] },
              { tier: "Starter", price: "$49", checks: "100/month", features: ["All commodities", "Historical data", "Email support"] },
              { tier: "Professional", price: "$149", checks: "500/month", features: ["API access", "LCopilot integration", "Priority support"], popular: true },
              { tier: "Enterprise", price: "Custom", checks: "Unlimited", features: ["Custom commodities", "Dedicated support", "On-premise option"] },
            ].map((plan, i) => (
              <div key={i} className={`bg-slate-900/50 border rounded-xl p-6 relative ${plan.popular ? 'border-green-500' : 'border-slate-800'}`}>
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-green-500 text-white border-0">Most Popular</Badge>
                  </div>
                )}
                <div className="text-sm text-slate-400 mb-2">{plan.tier}</div>
                <div className="text-2xl font-bold text-white mb-1">{plan.price}</div>
                <div className="text-xs text-slate-500 mb-4">{plan.checks}</div>
                <ul className="space-y-2">
                  {plan.features.map((feature, j) => (
                    <li key={j} className="text-sm text-slate-400 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-green-500" />
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-12 sm:py-20 bg-gradient-to-b from-slate-900/50 to-slate-950">
        <div className="container mx-auto px-4 sm:px-6">
          <div className="max-w-2xl mx-auto text-center">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4">
              Stop Googling Prices.
              <br />
              <span className="text-green-400">Get Verified Market Data.</span>
            </h2>
            <p className="text-slate-400 mb-8">
              Join the waitlist for early access and launch pricing.
            </p>
            <Button size="lg" className="bg-green-500 hover:bg-green-600 text-white px-8 h-12" asChild>
              <Link to="/price-verify/tool">
                Start Verifying Prices
                <ArrowRight className="w-4 h-4 ml-2" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      <TRDRFooter />
    </div>
  );
}

