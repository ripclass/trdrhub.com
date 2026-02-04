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
import { ToolPricingSection } from "@/components/tools/ToolPricingSection";

export default function PriceVerifyLanding() {
  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      
      {/* Hero Section */}
      <section className="pt-24 sm:pt-32 pb-12 sm:pb-20 relative overflow-hidden bg-[#00261C]">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
        <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/10 rounded-full blur-3xl" />
        
        <div className="container mx-auto px-4 sm:px-6 relative z-10">
          <div className="max-w-4xl mx-auto text-center">
            <Badge className="mb-6 bg-[#B2F273]/10 text-[#B2F273] border-[#B2F273]/20 px-4 py-1.5">
              🏦 Built for Banks • Direct Request
            </Badge>
            
            <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight font-display">
              Catch Price Anomalies
              <br />
              <span className="text-[#B2F273] text-glow-sm">Before They Become Problems</span>
            </h1>
            
            <p className="text-lg sm:text-xl text-[#EDF5F2]/60 mb-8 max-w-2xl mx-auto">
              Verify trade document prices against real-time market data. Detect over/under invoicing 
              and trade-based money laundering risks in seconds.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
              <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold px-8 h-12" asChild>
                <Link to="/price-verify/dashboard">
                  Open Dashboard
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 px-8 h-12 bg-transparent">
                View Demo
              </Button>
            </div>
            
            {/* Trust indicators */}
            <div className="flex flex-wrap justify-center gap-6 text-sm text-[#EDF5F2]/60">
              <span className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                50+ Commodities
              </span>
              <span className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                Real-Time Market Data
              </span>
              <span className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                TBML Detection
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 sm:py-16 border-y border-[#EDF5F2]/10 bg-[#00261C] overflow-hidden relative">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
        <div className="container mx-auto px-4 sm:px-6 relative z-10">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-2xl sm:text-4xl font-bold text-white mb-2 font-display">50+</div>
              <div className="text-sm text-[#EDF5F2]/60 font-mono uppercase tracking-wider">Commodities Covered</div>
            </div>
            <div>
              <div className="text-2xl sm:text-4xl font-bold text-white mb-2 font-display">&lt;30s</div>
              <div className="text-sm text-[#EDF5F2]/60 font-mono uppercase tracking-wider">Verification Time</div>
            </div>
            <div>
              <div className="text-2xl sm:text-4xl font-bold text-white mb-2 font-display">±15%</div>
              <div className="text-sm text-[#EDF5F2]/60 font-mono uppercase tracking-wider">Variance Tolerance</div>
            </div>
            <div>
              <div className="text-2xl sm:text-4xl font-bold text-white mb-2 font-display">6+</div>
              <div className="text-sm text-[#EDF5F2]/60 font-mono uppercase tracking-wider">Data Sources</div>
            </div>
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="py-12 sm:py-20 bg-[#00261C] overflow-hidden relative">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
        
        <div className="container mx-auto px-4 sm:px-6 relative z-10">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-10 sm:mb-16 text-center font-display">
              Trade-Based Money Laundering is a
              <br />
              <span className="text-[#B2F273]">$2 Trillion Problem</span>
            </h2>
            
            <div className="grid md:grid-cols-2 gap-6 sm:gap-8">
              <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 backdrop-blur-sm">
                <AlertTriangle className="w-10 h-10 text-red-400 mb-4" />
                <h3 className="text-lg font-bold text-white mb-2 font-display">Over-Invoicing</h3>
                <p className="text-[#EDF5F2]/60 text-sm">
                  Importers pay inflated prices, moving excess funds abroad illegally. 
                  Without market data, banks can't detect these anomalies.
                </p>
              </div>
              
              <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 backdrop-blur-sm">
                <AlertTriangle className="w-10 h-10 text-orange-400 mb-4" />
                <h3 className="text-lg font-bold text-white mb-2 font-display">Under-Invoicing</h3>
                <p className="text-[#EDF5F2]/60 text-sm">
                  Exporters receive below-market payments, evading taxes and capital controls. 
                  Manual checks miss 90% of cases.
                </p>
              </div>
              
              <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 backdrop-blur-sm">
                <Clock className="w-10 h-10 text-yellow-400 mb-4" />
                <h3 className="text-lg font-bold text-white mb-2 font-display">Manual Process</h3>
                <p className="text-[#EDF5F2]/60 text-sm">
                  Banks spend 30-60 minutes per transaction Googling prices. 
                  Results are inconsistent and undocumented.
                </p>
              </div>
              
              <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 backdrop-blur-sm">
                <Shield className="w-10 h-10 text-blue-400 mb-4" />
                <h3 className="text-lg font-bold text-white mb-2 font-display">Regulatory Pressure</h3>
                <p className="text-[#EDF5F2]/60 text-sm">
                  FATF guidelines require price verification. 
                  Banks need auditable compliance records.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Solution Section */}
      <section className="py-12 sm:py-20 bg-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden relative">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

        <div className="container mx-auto px-4 sm:px-6 relative z-10">
          <div className="max-w-4xl mx-auto text-center mb-10 sm:mb-16">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
              Verify Prices in <span className="text-[#B2F273]">Under 30 Seconds</span>
            </h2>
            <p className="text-[#EDF5F2]/60">
              Upload documents or enter prices manually. Get instant market comparisons.
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-6 sm:gap-8 max-w-5xl mx-auto">
            <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 text-center backdrop-blur-sm">
              <div className="w-12 h-12 bg-[#B2F273]/10 rounded-xl flex items-center justify-center mx-auto mb-4 border border-[#B2F273]/20">
                <FileText className="w-6 h-6 text-[#B2F273]" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2 font-display">1. Upload Document</h3>
              <p className="text-[#EDF5F2]/60 text-sm">
                Drop your invoice, LC, or contract. We extract commodity, quantity, and price automatically.
              </p>
            </div>
            
            <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 text-center backdrop-blur-sm">
              <div className="w-12 h-12 bg-[#B2F273]/10 rounded-xl flex items-center justify-center mx-auto mb-4 border border-[#B2F273]/20">
                <TrendingUp className="w-6 h-6 text-[#B2F273]" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2 font-display">2. Compare to Market</h3>
              <p className="text-[#EDF5F2]/60 text-sm">
                We check ICE, LME, USDA, and industry indices. Real-time and historical data.
              </p>
            </div>
            
            <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 text-center backdrop-blur-sm">
              <div className="w-12 h-12 bg-[#B2F273]/10 rounded-xl flex items-center justify-center mx-auto mb-4 border border-[#B2F273]/20">
                <BarChart3 className="w-6 h-6 text-[#B2F273]" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2 font-display">3. Get Verdict</h3>
              <p className="text-[#EDF5F2]/60 text-sm">
                Clear variance analysis with risk flags. Download compliance-ready PDF reports.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Commodities Section */}
      <section className="py-12 sm:py-20 bg-[#00261C] overflow-hidden relative">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

        <div className="container mx-auto px-4 sm:px-6 relative z-10">
          <div className="max-w-4xl mx-auto text-center mb-10 sm:mb-16">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
              50+ Commodities. <span className="text-[#B2F273]">Bangladesh Focus.</span>
            </h2>
            <p className="text-[#EDF5F2]/60">
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
              <div key={i} className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-4 text-center backdrop-blur-sm hover:border-[#B2F273]/30 transition-colors">
                <div className="text-2xl mb-2">{commodity.icon}</div>
                <div className="text-sm text-[#EDF5F2]/80">{commodity.name}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* For Banks Section */}
      <section className="py-12 sm:py-20 bg-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden relative">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

        <div className="container mx-auto px-4 sm:px-6 relative z-10">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-center gap-3 mb-6">
              <Building2 className="w-8 h-8 text-[#B2F273]" />
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white font-display">
                Built for <span className="text-[#B2F273]">Banks</span>
              </h2>
            </div>
            <p className="text-[#EDF5F2]/60 text-center mb-10 sm:mb-12">
              Direct feedback from trade finance departments shaped every feature.
            </p>
            
            <div className="grid md:grid-cols-2 gap-6">
              <div className="flex items-start gap-4 p-4 bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl backdrop-blur-sm">
                <CheckCircle className="w-6 h-6 text-[#B2F273] flex-shrink-0 mt-1" />
                <div>
                  <h4 className="font-bold text-white mb-1 font-display">TBML Risk Scoring</h4>
                  <p className="text-sm text-[#EDF5F2]/60">Auto-flag transactions with &gt;25% variance for enhanced due diligence.</p>
                </div>
              </div>
              
              <div className="flex items-start gap-4 p-4 bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl backdrop-blur-sm">
                <CheckCircle className="w-6 h-6 text-[#B2F273] flex-shrink-0 mt-1" />
                <div>
                  <h4 className="font-bold text-white mb-1 font-display">Audit Trail</h4>
                  <p className="text-sm text-[#EDF5F2]/60">Every price check logged with timestamp, user, and source data for regulators.</p>
                </div>
              </div>
              
              <div className="flex items-start gap-4 p-4 bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl backdrop-blur-sm">
                <CheckCircle className="w-6 h-6 text-[#B2F273] flex-shrink-0 mt-1" />
                <div>
                  <h4 className="font-bold text-white mb-1 font-display">LCopilot Integration</h4>
                  <p className="text-sm text-[#EDF5F2]/60">Auto-verify prices when processing LC documents. One seamless workflow.</p>
                </div>
              </div>
              
              <div className="flex items-start gap-4 p-4 bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl backdrop-blur-sm">
                <CheckCircle className="w-6 h-6 text-[#B2F273] flex-shrink-0 mt-1" />
                <div>
                  <h4 className="font-bold text-white mb-1 font-display">Multi-Source Verification</h4>
                  <p className="text-sm text-[#EDF5F2]/60">ICE, LME, USDA, FAO, and industry indices. Never rely on a single source.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section - With Localized Currency */}
      <ToolPricingSection 
        title="Simple, Transparent Pricing"
        subtitle="Start free. Scale as you grow."
        tiers={[
          { tier: "Free", price: "$0", checks: "10/month", features: ["Basic verification", "3 commodities", "PDF reports"] },
          { tier: "Starter", price: "$49/mo", checks: "100/month", features: ["All commodities", "Historical data", "Email support"] },
          { tier: "Professional", price: "$149/mo", checks: "500/month", features: ["API access", "LCopilot integration", "Priority support"], popular: true },
          { tier: "Enterprise", price: "Custom", checks: "Unlimited", features: ["Custom commodities", "Dedicated support", "On-premise option"] },
        ]}
        toolSlug="price-verify"
      />

      {/* CTA Section */}
      <section className="py-12 sm:py-20 bg-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden relative">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

        <div className="container mx-auto px-4 sm:px-6 relative z-10">
          <div className="max-w-2xl mx-auto text-center">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
              Stop Googling Prices.
              <br />
              <span className="text-[#B2F273]">Get Verified Market Data.</span>
            </h2>
            <p className="text-[#EDF5F2]/60 mb-8">
              Join the waitlist for early access and launch pricing.
            </p>
            <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold px-8 h-12" asChild>
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
