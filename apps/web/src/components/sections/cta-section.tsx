import { Button } from "@/components/ui/button";
import { ArrowRight, Mail } from "lucide-react";
import { Link } from "react-router-dom";
import { useState } from "react";

export function CTASection() {
  const [email, setEmail] = useState("");
  const [subscribed, setSubscribed] = useState(false);

  const handleSubscribe = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      setSubscribed(true);
      setEmail("");
    }
  };

  return (
    <section className="py-24 md:py-32 bg-[#EDF5F2] relative overflow-hidden">
      {/* Background Noise/Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(0,38,28,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,38,28,0.03)_1px,transparent_1px)] bg-[size:40px_40px] opacity-100" />
      <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-b from-[#EDF5F2] to-transparent z-10" />
      <div className="absolute bottom-0 left-0 w-full h-32 bg-gradient-to-t from-[#EDF5F2] to-transparent z-10" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-20">
        <div className="max-w-3xl mx-auto text-center">
          {/* Main CTA */}
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-[#00261C] mb-6 leading-tight font-display">
            Ready to validate your
            <br />
            <span className="text-[#00261C]">
              first LC for free?
            </span>
          </h2>
          <p className="text-xl text-[#00261C]/80 mb-10 max-w-xl mx-auto">
            No credit card required. Get your first 5 validations free, forever.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <Button 
              size="lg" 
              className="bg-[#00261C] text-[#B2F273] hover:bg-[#00382E] text-lg px-8 py-6 h-auto font-semibold group border-none shadow-xl"
              asChild
            >
              <Link to="/lcopilot">
                Start Validating Now
                <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
              </Link>
            </Button>
            <Button 
              variant="outline" 
              size="lg" 
              className="border-[#00261C]/20 text-[#00261C] hover:bg-[#00261C] hover:text-[#B2F273] hover:border-[#00261C] text-lg px-8 py-6 h-auto bg-transparent transition-colors"
              asChild
            >
              <Link to="/contact">
                Talk to Sales
              </Link>
            </Button>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-4 mb-12">
            <div className="flex-1 h-px bg-[#00261C]/10" />
            <span className="text-[#00261C]/40 text-sm">or stay updated</span>
            <div className="flex-1 h-px bg-[#00261C]/10" />
          </div>

          {/* Newsletter signup */}
          <div className="max-w-md mx-auto">
            <p className="text-[#00261C]/60 mb-4">
              Want to stay up to date? Sign up for our monthly newsletter.
            </p>
            
            {subscribed ? (
              <div className="bg-[#B2F273]/20 border border-[#B2F273] rounded-lg p-4 text-[#00261C] font-medium">
                Thanks for subscribing! We'll keep you posted.
              </div>
            ) : (
              <form onSubmit={handleSubscribe} className="flex gap-2 items-stretch">
                <div className="relative flex-1">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[#00261C]/40" />
                  <input
                    type="email"
                    placeholder="your@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full h-12 bg-white border border-[#00261C]/10 rounded-lg pl-10 pr-4 text-[#00261C] placeholder-[#00261C]/30 focus:outline-none focus:border-[#00261C] focus:ring-1 focus:ring-[#00261C] transition-all shadow-sm"
                    required
                  />
                </div>
                <Button type="submit" className="h-12 bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] px-6 border-none font-bold font-mono uppercase tracking-wider">
                  Subscribe
                </Button>
              </form>
            )}
            <p className="text-[#00261C]/40 text-xs mt-3">
              No spam. Unsubscribe anytime.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
