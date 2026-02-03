import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { 
  Shield, 
  Users, 
  Globe, 
  Award, 
  ArrowRight,
  TrendingUp,
  Building2,
  HeartHandshake,
  Lightbulb
} from "lucide-react";

const stats = [
  { label: "Trade Volume Secured", value: "$32T", sub: "Global Market Gap" },
  { label: "Documents Validated", value: "2M+", sub: "Training Dataset" },
  { label: "Countries Covered", value: "60+", sub: "Regulatory Frameworks" },
  { label: "Accuracy Rate", value: "99.9%", sub: "Discrepancy Detection" },
];

const values = [
  {
    icon: Shield,
    title: "Zero Tolerance for Error",
    description: "In trade finance, a single typo can cost millions. We build systems that treat every character as critical infrastructure."
  },
  {
    icon: Users,
    title: "Democratizing Access",
    description: "Sophisticated compliance tools shouldn't be reserved for Tier 1 banks. We bring enterprise-grade tech to every exporter."
  },
  {
    icon: Lightbulb,
    title: "Deterministic AI",
    description: "We don't believe in 'hallucinations' when money is on the line. Our AI is grounded in hard rules and verifiable facts."
  },
  {
    icon: HeartHandshake,
    title: "Partner, Not Vendor",
    description: "We succeed only when our users ship faster, get paid sooner, and sleep better. Your growth is our north star."
  }
];

const AboutPage = () => {
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
          
          {/* Hero Section */}
          <div className="text-center mb-24">
            <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full border border-[#B2F273]/20 bg-[#B2F273]/5 backdrop-blur-sm mb-6">
              <span className="text-[#B2F273] font-mono text-xs tracking-wider uppercase">Our Mission</span>
            </div>
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-white mb-8 leading-tight font-display">
              Rewriting the Operating System
              <br />
              <span className="text-[#B2F273] text-glow-sm">of Global Trade.</span>
            </h1>
            <p className="text-lg text-[#EDF5F2]/60 max-w-3xl mx-auto font-light leading-relaxed">
              Global trade is a $32 trillion industry running on paper, PDFs, and email. 
              We're building the digital infrastructure to make it instant, error-free, and accessible to everyone.
            </p>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-32 border-y border-[#EDF5F2]/10 py-12">
            {stats.map((stat, index) => (
              <div key={index} className="text-center">
                <div className="text-4xl md:text-5xl font-bold text-white mb-2 font-display">{stat.value}</div>
                <div className="text-[#B2F273] font-bold mb-1">{stat.label}</div>
                <div className="text-[#EDF5F2]/40 text-xs font-mono uppercase tracking-wider">{stat.sub}</div>
              </div>
            ))}
          </div>

          {/* Story Section */}
          <div className="max-w-4xl mx-auto mb-32">
            <div className="bg-[#00382E]/30 border border-[#EDF5F2]/10 rounded-3xl p-8 md:p-12 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-[#B2F273]/5 rounded-full blur-3xl" />
              
              <h2 className="text-3xl font-bold text-white mb-6 font-display">Why We Built TRDR Hub</h2>
              <div className="space-y-6 text-[#EDF5F2]/80 leading-relaxed text-lg">
                <p>
                  Every year, <strong>4 billion</strong> trade documents circulate the globe. 
                  <strong> 70%</strong> of them contain errors on the first presentation.
                </p>
                <p>
                  For a small exporter in Bangladesh or Vietnam, a single discrepancy in a Letter of Credit isn't just an annoyance—it's an existential threat. It means delayed payments, stranded cargo, and expensive penalties.
                </p>
                <p>
                  We saw brilliant businesses being held back not by their products, but by paperwork. The existing tools were either too expensive (enterprise ERPs) or too simple (basic PDF editors).
                </p>
                <p>
                  So we built <strong>TRDR Hub</strong>: A platform that combines the precision of a bank's compliance department with the speed of modern software. We're not just validating documents; we're validating the trust that powers the global economy.
                </p>
              </div>
            </div>
          </div>

          {/* Values Grid */}
          <div className="mb-32">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-5xl font-bold text-white mb-6 font-display">Our DNA</h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                The principles that guide every line of code we write and every decision we make.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">
              {values.map((value, index) => (
                <div 
                  key={index}
                  className="bg-[#00261C] border border-[#EDF5F2]/10 rounded-2xl p-8 hover:border-[#B2F273]/30 transition-all duration-300 group"
                >
                  <div className="w-12 h-12 bg-[#00382E] rounded-lg flex items-center justify-center mb-6 group-hover:bg-[#B2F273]/20 transition-colors">
                    <value.icon className="w-6 h-6 text-[#B2F273]" />
                  </div>
                  <h3 className="text-xl font-bold text-white mb-3 font-display">{value.title}</h3>
                  <p className="text-[#EDF5F2]/60 leading-relaxed">
                    {value.description}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Bottom CTA */}
          <div className="text-center max-w-3xl mx-auto">
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-8 font-display">
              Join the revolution.
            </h2>
            <p className="text-[#EDF5F2]/60 mb-10 text-lg">
              Whether you're an exporter looking to grow, or a developer looking to build, there's a place for you at TRDR Hub.
            </p>
            <div className="flex justify-center gap-4">
              <Button 
                size="lg" 
                className="bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] px-8 font-bold border-none"
                asChild
              >
                <Link to="/lcopilot">
                  Start Using TRDR
                  <ArrowRight className="w-5 h-5 ml-2" />
                </Link>
              </Button>
              <Button 
                variant="outline"
                size="lg" 
                className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 hover:border-[#EDF5F2]/40 bg-transparent"
                asChild
              >
                <Link to="/contact">
                  Contact Us
                </Link>
              </Button>
            </div>
          </div>

        </div>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default AboutPage;
