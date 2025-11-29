import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowRight, CheckCircle } from "lucide-react";
import { Link } from "react-router-dom";

const guarantees = [
  "No credit card required",
  "3 free validations",
  "Setup in 2 minutes",
  "Cancel anytime"
];

export function CTASection() {
  return (
    <section className="py-20 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-hero opacity-10" />
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative">
        <Card className="bg-gradient-to-br from-primary/5 via-primary/10 to-primary/5 backdrop-blur-sm border border-primary/20 shadow-strong overflow-hidden">
          <CardContent className="p-12 text-center relative">
            
            {/* Urgency badge */}
            <div className="inline-flex items-center gap-2 bg-yellow-500/10 text-yellow-600 px-4 py-2 rounded-full text-sm font-medium mb-6">
              ⚡ Your next LC could be rejected. Don't risk it.
            </div>
            
            {/* Headline - Future pacing */}
            <h2 className="text-3xl lg:text-5xl font-bold text-foreground mb-6">
              What if your next LC passed{" "}
              <span className="bg-gradient-primary bg-clip-text text-transparent">
                on the first try?
              </span>
            </h2>
            
            {/* Value prop */}
            <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
              Upload your documents now. In 45 seconds, you'll know exactly what banks will flag — 
              <strong className="text-foreground"> before you submit.</strong>
            </p>

            {/* Primary CTA - Big and obvious */}
            <div className="mb-8">
              <Button 
                size="lg" 
                className="bg-gradient-primary hover:opacity-90 shadow-medium group text-lg px-10 py-7 h-auto"
                asChild
              >
                <Link to="/lcopilot">
                  Validate Your LC Now — Free
                  <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                </Link>
              </Button>
            </div>

            {/* Risk Reversal - Remove objections */}
            <div className="flex flex-wrap justify-center gap-4 mb-8">
              {guarantees.map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-muted-foreground">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  <span>{item}</span>
                </div>
              ))}
            </div>

            {/* Social proof - Testimonial snippet */}
            <div className="bg-background/50 rounded-xl p-6 max-w-xl mx-auto">
              <p className="text-foreground italic mb-3">
                "We used to spend 4 hours reviewing each LC. Now it's 45 seconds. 
                The ROI was obvious after the first week."
              </p>
              <div className="flex items-center justify-center gap-3">
                <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center text-primary font-semibold">
                  MR
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-foreground">Mohammad Rahman</p>
                  <p className="text-xs text-muted-foreground">Export Manager, Dhaka Knitwear Ltd</p>
                </div>
              </div>
            </div>

          </CardContent>
        </Card>
      </div>
    </section>
  );
}
