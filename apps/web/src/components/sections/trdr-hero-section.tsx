import { Button } from "@/components/ui/button";
import { ArrowRight, Play, CheckCircle, XCircle } from "lucide-react";
import { Link } from "react-router-dom";

export function TRDRHeroSection() {
  const scrollToTools = () => {
    document.getElementById('tools')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section id="home" className="relative min-h-[90vh] flex items-center justify-center overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-hero opacity-10" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,hsl(var(--background))_70%)]" />
      
      {/* Floating elements */}
      <div className="absolute top-20 left-10 w-20 h-20 bg-primary/5 rounded-full blur-xl" />
      <div className="absolute bottom-20 right-10 w-32 h-32 bg-accent/5 rounded-full blur-xl" />
      <div className="absolute top-1/2 left-1/4 w-4 h-4 bg-primary/20 rounded-full animate-pulse" />
      <div className="absolute top-1/3 right-1/3 w-6 h-6 bg-accent/20 rounded-full animate-pulse delay-1000" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center max-w-4xl mx-auto">
          
          {/* Pain Point Badge - Creates instant recognition */}
          <div className="inline-flex items-center gap-2 bg-red-500/10 text-red-600 px-4 py-2 rounded-full text-sm font-medium mb-6">
            <XCircle className="w-4 h-4" />
            Tired of $75 discrepancy fees?
          </div>
          
          {/* Headline - Outcome focused, not feature focused */}
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-foreground mb-6 leading-tight">
            Stop Losing Money on{" "}
            <span className="bg-gradient-primary bg-clip-text text-transparent">
              LC Rejections
            </span>
          </h1>
          
          {/* Subhead - The transformation */}
          <p className="text-xl md:text-2xl text-muted-foreground mb-4 max-w-3xl mx-auto">
            Our AI catches discrepancies <strong className="text-foreground">before banks do.</strong>
          </p>
          
          {/* Value prop in one line */}
          <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
            Upload your LC and documents. Get validated in 45 seconds. 
            Ship with confidence.
          </p>

          {/* CTA - One clear primary action */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
            <Button 
              size="lg" 
              className="bg-gradient-primary hover:opacity-90 shadow-medium group text-lg px-8 py-6"
              asChild
            >
              <Link to="/lcopilot">
                Validate Your LC Free
                <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
              </Link>
            </Button>
            <Button variant="outline" size="lg" className="border-primary/20 hover:bg-primary/5 text-lg px-8 py-6" onClick={scrollToTools}>
              <Play className="w-4 h-4 mr-2" />
              See How It Works
            </Button>
          </div>

          {/* Risk Reversal - Remove friction */}
          <p className="text-sm text-muted-foreground mb-10">
            ✓ No credit card required &nbsp;&nbsp; ✓ 3 free validations &nbsp;&nbsp; ✓ Results in 45 seconds
          </p>

          {/* Social Proof - Mini version */}
          <div className="flex flex-col items-center gap-4">
            <div className="flex items-center gap-1">
              {[1,2,3,4,5].map((i) => (
                <svg key={i} className="w-5 h-5 text-yellow-400 fill-current" viewBox="0 0 20 20">
                  <path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z"/>
                </svg>
              ))}
            </div>
            <p className="text-sm text-muted-foreground">
              <strong className="text-foreground">"Saved us $2,400 in discrepancy fees last quarter."</strong>
              <br />
              — Trade Finance Manager, Bangladesh Garment Exporter
            </p>
          </div>

        </div>
      </div>
    </section>
  );
}
