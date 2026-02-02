import { Button } from "@/components/ui/button";
import { ArrowRight, ChevronDown } from "lucide-react";
import { Link } from "react-router-dom";

export function TRDRHeroSection() {
  const scrollToProblems = () => {
    document.getElementById('problems')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section className="relative min-h-screen flex flex-col justify-center overflow-hidden bg-[#00261C]">
      {/* Animated gradient orbs - Updated to strict brand colors */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[#B2F273]/10 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl animate-pulse delay-1000" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-radial from-[#B2F273]/5 to-transparent rounded-full" />
      
      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:64px_64px]" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10 pt-20">
        <div className="text-center max-w-5xl mx-auto">
          
          {/* Backed by badge */}
          <div className="mb-8">
            <p className="text-[#EDF5F2]/60 text-sm mb-4">Powered by international standards:</p>
            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 opacity-80">
              <span className="text-[#EDF5F2] font-semibold text-sm">UCP600</span>
              <span className="text-[#B2F273] hidden sm:inline">•</span>
              <span className="text-[#EDF5F2] font-semibold text-sm">Incoterms 2020</span>
              <span className="text-[#B2F273] hidden sm:inline">•</span>
              <span className="text-[#EDF5F2] font-semibold text-sm">OFAC/EU/UN</span>
              <span className="text-[#B2F273] hidden sm:inline">•</span>
              <span className="text-[#EDF5F2] font-semibold text-sm">60+ Countries</span>
            </div>
          </div>

          {/* Main headline */}
          <h1 className="text-3xl sm:text-5xl md:text-7xl lg:text-8xl font-bold text-white mb-6 sm:mb-8 leading-[0.95] tracking-tight font-display">
            Everything Trade.
            <br />
            <span className="text-[#B2F273]">
              One Platform.
            </span>
          </h1>
          
          {/* Subheadline */}
          <p className="text-base sm:text-xl md:text-2xl text-[#EDF5F2]/80 mb-8 sm:mb-12 max-w-3xl mx-auto leading-relaxed px-2">
            15 AI-powered tools for document validation, sanctions screening, HS classification, shipment tracking, and more.
            <span className="text-white"> Stop losing money to errors and delays.</span>
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <Button 
              size="lg" 
              className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] text-lg px-8 py-6 h-auto font-semibold group border-none"
              asChild
            >
              <Link to="/lcopilot">
                Start Free
                <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
              </Link>
            </Button>
            <Button 
              variant="outline" 
              size="lg" 
              className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/10 text-lg px-8 py-6 h-auto bg-transparent"
              onClick={scrollToProblems}
            >
              See How It Works
            </Button>
          </div>

          {/* Trust metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-8 max-w-3xl mx-auto border-t border-[#EDF5F2]/10 pt-12">
            <div className="text-center">
              <div className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-1 font-display">15</div>
              <div className="text-xs sm:text-sm text-[#EDF5F2]/60">Trade Tools</div>
            </div>
            <div className="text-center">
              <div className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-1 font-display">3,500+</div>
              <div className="text-xs sm:text-sm text-[#EDF5F2]/60">Validation Rules</div>
            </div>
            <div className="text-center">
              <div className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-1 font-display">60+</div>
              <div className="text-xs sm:text-sm text-[#EDF5F2]/60">Countries</div>
            </div>
            <div className="text-center">
              <div className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-1 font-display">$0</div>
              <div className="text-xs sm:text-sm text-[#EDF5F2]/60">To Start</div>
            </div>
          </div>

        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 animate-bounce">
        <span className="text-[#EDF5F2]/40 text-sm">Scroll to discover</span>
        <ChevronDown className="w-6 h-6 text-[#B2F273]" />
      </div>
    </section>
  );
}
