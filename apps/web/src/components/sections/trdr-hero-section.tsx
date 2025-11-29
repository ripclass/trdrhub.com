import { Button } from "@/components/ui/button";
import { ArrowRight, ChevronDown } from "lucide-react";
import { Link } from "react-router-dom";

export function TRDRHeroSection() {
  const scrollToProblems = () => {
    document.getElementById('problems')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section className="relative min-h-screen flex flex-col justify-center overflow-hidden bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Animated gradient orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl animate-pulse" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl animate-pulse delay-1000" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-radial from-blue-500/5 to-transparent rounded-full" />
      
      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10 pt-20">
        <div className="text-center max-w-5xl mx-auto">
          
          {/* Backed by badge */}
          <div className="mb-8">
            <p className="text-slate-400 text-sm mb-4">Powered by international standards:</p>
            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 opacity-60">
              <span className="text-slate-300 font-semibold text-sm">UCP600</span>
              <span className="text-slate-500 hidden sm:inline">•</span>
              <span className="text-slate-300 font-semibold text-sm">Incoterms 2020</span>
              <span className="text-slate-500 hidden sm:inline">•</span>
              <span className="text-slate-300 font-semibold text-sm">OFAC/EU/UN</span>
              <span className="text-slate-500 hidden sm:inline">•</span>
              <span className="text-slate-300 font-semibold text-sm">60+ Countries</span>
            </div>
          </div>

          {/* Main headline */}
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold text-white mb-8 leading-[0.9] tracking-tight">
            Everything Trade.
            <br />
            <span className="bg-gradient-to-r from-blue-400 via-emerald-400 to-blue-400 bg-clip-text text-transparent">
              One Platform.
            </span>
          </h1>
          
          {/* Subheadline */}
          <p className="text-xl md:text-2xl text-slate-400 mb-12 max-w-3xl mx-auto leading-relaxed">
            15 AI-powered tools for document validation, sanctions screening, HS classification, shipment tracking, and more.
            <span className="text-white"> Stop losing money to errors and delays.</span>
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <Button 
              size="lg" 
              className="bg-white text-slate-900 hover:bg-slate-100 text-lg px-8 py-6 h-auto font-semibold group"
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
              className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white text-lg px-8 py-6 h-auto"
              onClick={scrollToProblems}
            >
              See How It Works
            </Button>
          </div>

          {/* Trust metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-3xl mx-auto">
            <div className="text-center">
              <div className="text-3xl md:text-4xl font-bold text-white mb-1">15</div>
              <div className="text-sm text-slate-500">Trade Tools</div>
            </div>
            <div className="text-center">
              <div className="text-3xl md:text-4xl font-bold text-white mb-1">3,500+</div>
              <div className="text-sm text-slate-500">Validation Rules</div>
            </div>
            <div className="text-center">
              <div className="text-3xl md:text-4xl font-bold text-white mb-1">60+</div>
              <div className="text-sm text-slate-500">Countries</div>
            </div>
            <div className="text-center">
              <div className="text-3xl md:text-4xl font-bold text-white mb-1">$0</div>
              <div className="text-sm text-slate-500">To Start</div>
            </div>
          </div>

        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 animate-bounce">
        <span className="text-slate-500 text-sm">Scroll to discover</span>
        <ChevronDown className="w-6 h-6 text-slate-500" />
      </div>
    </section>
  );
}
