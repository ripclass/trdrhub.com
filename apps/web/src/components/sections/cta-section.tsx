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
    <section className="py-24 md:py-32 bg-slate-950 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 bg-gradient-to-b from-slate-900 to-slate-950" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="max-w-3xl mx-auto text-center">
          {/* Main CTA */}
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6 leading-tight">
            Ready to validate your
            <br />
            <span className="bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
              first LC for free?
            </span>
          </h2>
          <p className="text-xl text-slate-400 mb-10 max-w-xl mx-auto">
            No credit card required. Get your first 5 validations free, forever.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <Button 
              size="lg" 
              className="bg-white text-slate-900 hover:bg-slate-100 text-lg px-8 py-6 h-auto font-semibold group"
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
              className="border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white text-lg px-8 py-6 h-auto"
              asChild
            >
              <Link to="/contact">
                Talk to Sales
              </Link>
            </Button>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-4 mb-12">
            <div className="flex-1 h-px bg-slate-800" />
            <span className="text-slate-500 text-sm">or stay updated</span>
            <div className="flex-1 h-px bg-slate-800" />
          </div>

          {/* Newsletter signup */}
          <div className="max-w-md mx-auto">
            <p className="text-slate-400 mb-4">
              Want to stay up to date? Sign up for our monthly newsletter.
            </p>
            
            {subscribed ? (
              <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4 text-emerald-400">
                Thanks for subscribing! We'll keep you posted.
              </div>
            ) : (
              <form onSubmit={handleSubscribe} className="flex gap-2">
                <div className="relative flex-1">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                  <input
                    type="email"
                    placeholder="your@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
                    required
                  />
                </div>
                <Button type="submit" className="bg-blue-600 hover:bg-blue-700 px-6">
                  Subscribe
                </Button>
              </form>
            )}
            <p className="text-slate-600 text-xs mt-3">
              No spam. Unsubscribe anytime.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
