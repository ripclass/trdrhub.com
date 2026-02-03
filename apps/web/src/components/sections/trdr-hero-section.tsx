import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

export function TRDRHeroSection() {
  const scrollToProblems = () => {
    document.getElementById('problems')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section className="relative min-h-screen flex flex-col justify-center overflow-hidden bg-[#00261C]">
      {/* Background Image with Overlay */}
      <div className="absolute inset-0 z-0">
        <img 
          src="https://images.unsplash.com/photo-1494412574643-35d324698b93?q=80&w=2070&auto=format&fit=crop" 
          alt="Global Trade" 
          className="w-full h-full object-cover opacity-20"
        />
        <div className="absolute inset-0 bg-[#00261C]/90 mix-blend-multiply" />
        <div className="absolute inset-0 bg-gradient-to-b from-[#00261C] via-transparent to-[#00261C]" />
      </div>

      {/* Animated gradient orbs - Updated to strict brand colors */}
      <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-[#B2F273]/10 rounded-full blur-[120px] animate-pulse z-0" />
      <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-[#B2F273]/5 rounded-full blur-[120px] animate-pulse delay-1000 z-0" />
      
      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] z-0" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10 pt-40 md:pt-48 pb-20">
        <div className="text-center max-w-5xl mx-auto">
          
          {/* Backed by badge */}
          <div className="mb-10 animate-fade-in-up">
            <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full border border-[#B2F273]/20 bg-[#B2F273]/5 backdrop-blur-sm">
              <span className="text-[#B2F273] font-mono text-xs tracking-wider uppercase">Global Trade Operating System</span>
            </div>
          </div>

          {/* Main headline */}
          <h1 className="text-5xl sm:text-7xl md:text-8xl lg:text-9xl font-bold text-white mb-8 leading-[0.9] tracking-tight font-display animate-fade-in-up delay-100">
            Everything Trade.
            <br />
            <span className="text-[#B2F273] text-glow">
              One Platform.
            </span>
          </h1>
          
          {/* Subheadline */}
          <p className="text-lg sm:text-xl md:text-2xl text-[#EDF5F2]/80 mb-12 max-w-3xl mx-auto leading-relaxed px-4 font-light animate-fade-in-up delay-200">
            15 AI-powered tools for document validation, sanctions screening, and compliance.
            <span className="text-[#B2F273] font-normal"> Stop losing money to errors.</span>
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-20 animate-fade-in-up delay-300">
            <Button 
              size="lg" 
              className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] text-lg px-8 py-7 h-auto font-bold group border-none shadow-[0_0_20px_rgba(178,242,115,0.3)] hover:shadow-[0_0_30px_rgba(178,242,115,0.5)] transition-all duration-300"
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
              className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 hover:border-[#EDF5F2]/40 text-lg px-8 py-7 h-auto bg-transparent backdrop-blur-sm transition-all duration-300"
              onClick={scrollToProblems}
            >
              See How It Works
            </Button>
          </div>

          {/* Trust metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto border-t border-[#EDF5F2]/10 pt-12 animate-fade-in-up delay-500">
            <div className="text-center group hover:-translate-y-1 transition-transform duration-300">
              <div className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-2 font-display group-hover:text-[#B2F273] transition-colors">15</div>
              <div className="text-xs sm:text-sm text-[#EDF5F2]/60 font-mono uppercase tracking-wider">Trade Tools</div>
            </div>
            <div className="text-center group hover:-translate-y-1 transition-transform duration-300">
              <div className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-2 font-display group-hover:text-[#B2F273] transition-colors">3.5k+</div>
              <div className="text-xs sm:text-sm text-[#EDF5F2]/60 font-mono uppercase tracking-wider">Validation Rules</div>
            </div>
            <div className="text-center group hover:-translate-y-1 transition-transform duration-300">
              <div className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-2 font-display group-hover:text-[#B2F273] transition-colors">60+</div>
              <div className="text-xs sm:text-sm text-[#EDF5F2]/60 font-mono uppercase tracking-wider">Countries</div>
            </div>
            <div className="text-center group hover:-translate-y-1 transition-transform duration-300">
              <div className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-2 font-display group-hover:text-[#B2F273] transition-colors">$0</div>
              <div className="text-xs sm:text-sm text-[#EDF5F2]/60 font-mono uppercase tracking-wider">To Start</div>
            </div>
          </div>

        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-3 animate-bounce opacity-50 hover:opacity-100 transition-opacity pointer-events-none md:pointer-events-auto">
        <span className="text-[#EDF5F2] text-xs font-mono tracking-widest uppercase">Scroll</span>
        <div className="w-[1px] h-12 bg-gradient-to-b from-[#B2F273] to-transparent"></div>
      </div>
    </section>
  );
}
