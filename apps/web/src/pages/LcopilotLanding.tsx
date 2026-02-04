import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, Shield, Zap, Globe, FileCheck, Brain, LayoutDashboard, Upload, Download, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";

const roles = [
  {
    id: "exporter",
    title: "I'm an Exporter",
    description: "Validate export LCs against UCP600/ISBP745, catch discrepancies before banks do, and ship with confidence.",
    to: "/lcopilot/exporter-dashboard",
    accent: "from-blue-500 to-blue-600",
    iconBg: "bg-blue-500/20",
    icon: FileCheck,
  },
  {
    id: "importer",
    title: "I'm an Importer",
    description: "Screen supplier documents, manage LC applications, and reduce costly rejections before goods ship.",
    to: "/lcopilot/importer-dashboard",
    accent: "from-emerald-500 to-emerald-600",
    iconBg: "bg-emerald-500/20",
    icon: Shield,
  },
  {
    id: "bank",
    title: "I'm a Bank",
    description: "Automate document examination, monitor compliance quality, and collaborate with clients in real time.",
    to: "/lcopilot/bank-dashboard",
    accent: "from-purple-500 to-purple-600",
    iconBg: "bg-purple-500/20",
    icon: LayoutDashboard,
  },
];

const highlights = [
  {
    icon: <Zap className="w-6 h-6 text-blue-400" />,
    label: "45-Second Validation",
    description: "Upload your documents, get a full compliance report with actionable fixes in under a minute.",
  },
  {
    icon: <Shield className="w-6 h-6 text-emerald-400" />,
    label: "99% Accuracy",
    description: "AI-powered engine validates against 3,500+ rules from UCP600, ISBP745, and 60+ country regulations.",
  },
  {
    icon: <Globe className="w-6 h-6 text-purple-400" />,
    label: "Global Coverage",
    description: "Pre-built rules for Singapore, UAE, Bangladesh, India, EU, US, and 54 more jurisdictions.",
  },
];

const stats = [
  { value: "3,500+", label: "Rules Checked" },
  { value: "45s", label: "Avg. Validation" },
  { value: "99%", label: "Accuracy Rate" },
  { value: "$0", label: "To Start" },
];

export default function LcopilotLanding() {
  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main className="relative min-h-screen">
        {/* Hero Section */}
        <section className="relative pt-48 md:pt-48 pb-24">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-4xl mx-auto text-center">
            <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full border border-[#B2F273]/20 bg-[#B2F273]/5 backdrop-blur-sm mb-6">
              <span className="text-[#B2F273] font-mono text-xs tracking-wider uppercase">AI-Powered LC Validation</span>
            </div>
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-white mb-8 leading-tight font-display">
              Validate LCs in 45 seconds.
              <br />
              <span className="text-[#B2F273] text-glow-sm">Not 4 hours.</span>
            </h1>
            <p className="text-lg text-[#EDF5F2]/60 max-w-2xl mx-auto font-light leading-relaxed mb-10">
              LCopilot checks your documents against UCP600, ISBP745, and 3,500+ validation rules. 
              Catch discrepancies before banks do. Stop paying $75 rejection fees.
            </p>
            </div>
          </div>
        </section>

        {/* Role Cards */}
        <section className="relative py-24 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid gap-6 lg:grid-cols-3">
            {roles.map((role) => (
              <div 
                key={role.id} 
                className="group relative bg-[#00382E]/30 backdrop-blur-sm border border-[#EDF5F2]/10 rounded-3xl p-8 hover:border-[#B2F273]/30 transition-all duration-300 hover:-translate-y-1"
              >
                <div className="flex items-center gap-4 mb-6">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${role.iconBg}`}>
                    <role.icon className="w-6 h-6 text-white" />
                  </div>
                  <h2 className="text-2xl font-bold text-white font-display">{role.title}</h2>
                </div>
                
                <p className="text-[#EDF5F2]/60 text-base leading-relaxed mb-8 min-h-[80px]">
                  {role.description}
                </p>
                
                <div className="flex items-center gap-2 text-sm text-[#EDF5F2]/40 mb-8 font-mono">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  <span>Role-specific dashboard</span>
                </div>
                
                <Button 
                  asChild 
                  size="lg" 
                  className="w-full bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] font-bold border-none"
                >
                  <Link to={role.to} className="flex items-center justify-center gap-2">
                    Get Started <ArrowRight className="w-4 h-4" />
                  </Link>
                </Button>
              </div>
            ))}
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section className="relative py-24 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-5xl font-bold text-white mb-6 font-display">From Chaos to Compliance</h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                Stop manually cross-referencing documents. Let our AI handle the heavy lifting.
              </p>
            </div>
            
            <div className="max-w-5xl mx-auto">
              <div className="grid md:grid-cols-3 gap-8">
                {[
                  {
                    step: "01",
                    icon: Upload,
                    title: "Upload Documents",
                    description: "Drag & drop your LC, Bill of Lading, Invoice, and Packing List. Any format.",
                    time: "10 sec",
                  },
                  {
                    step: "02",
                    icon: Brain,
                    title: "AI Analysis",
                    description: "Our engine extracts data and checks against 3,500+ rules (UCP600, ISBP745) in seconds.",
                    time: "30 sec",
                  },
                  {
                    step: "03",
                    icon: Download,
                    title: "Resolve & Export",
                    description: "Review discrepancies with suggested fixes. Download a clean, bank-ready report.",
                    time: "5 sec",
                  }
                ].map((item, idx) => (
                  <div key={idx} className="relative h-full">
                    <div className="group bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-2xl p-8 hover:border-[#B2F273]/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_10px_40px_-10px_rgba(178,242,115,0.1)] relative overflow-hidden h-full">
                      {/* Hover Glow Effect */}
                      <div className="absolute top-0 right-0 w-32 h-32 bg-[#B2F273]/10 rounded-bl-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
                      
                      <div className="flex items-center justify-between mb-6">
                        <span className="text-5xl font-bold text-[#EDF5F2]/10 font-display group-hover:text-[#B2F273]/20 transition-colors">{item.step}</span>
                        <div className="w-14 h-14 bg-[#B2F273]/10 rounded-xl flex items-center justify-center border border-[#B2F273]/20 group-hover:bg-[#B2F273] group-hover:text-[#00261C] transition-all duration-300 relative z-10">
                          <item.icon className="w-7 h-7 text-[#B2F273] group-hover:text-[#00261C] transition-colors" />
                        </div>
                      </div>
                      
                      <h3 className="text-xl font-bold text-white mb-3 font-display transition-colors duration-300 group-hover:text-[#B2F273]">{item.title}</h3>
                      <p className="text-[#EDF5F2]/60 text-sm leading-relaxed mb-4">{item.description}</p>
                      
                      <div className="inline-flex items-center gap-2 text-xs text-[#EDF5F2]/40 font-mono">
                        <Clock className="w-3 h-3" />
                        {item.time}
                      </div>

                      {/* Bottom Decorative Line */}
                      <div className="absolute bottom-0 left-0 w-0 h-[3px] bg-[#B2F273] group-hover:w-full transition-all duration-500 ease-in-out" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
            </div>
          </div>
        </section>

        {/* Highlights Section */}
        <section className="relative py-24 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid gap-6 lg:grid-cols-3">
            {highlights.map((item, idx) => (
              <div 
                key={idx} 
                className="bg-[#00261C] border border-[#EDF5F2]/10 rounded-2xl p-8 hover:border-[#B2F273]/20 transition-colors"
              >
                <div className="flex items-center gap-4 mb-4">
                  <div className="bg-[#00382E] p-3 rounded-xl border border-[#EDF5F2]/5">
                    {item.icon}
                  </div>
                  <h3 className="text-lg font-bold text-white font-display">{item.label}</h3>
                </div>
                <p className="text-[#EDF5F2]/60 leading-relaxed text-sm">
                  {item.description}
                </p>
              </div>
            ))}
            </div>
          </div>
        </section>

        {/* Stats Section */}
        <section className="relative py-24 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="bg-[#00382E]/30 border border-[#EDF5F2]/10 rounded-3xl p-12 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-[#B2F273]/5 rounded-full blur-3xl" />
            
            <div className="flex flex-col lg:flex-row items-center justify-between gap-12 relative z-10">
              <div className="lg:max-w-xl">
                <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6 font-display">
                  Built for global trade.
                  <br />
                  <span className="text-[#B2F273]">Works everywhere.</span>
                </h2>
                <p className="text-[#EDF5F2]/60 leading-relaxed text-lg">
                  Whether you process one LC a month or hundreds per day, LCopilot pairs AI validation 
                  with human-ready workflows so your teams can ship documents without fear of rejection.
                </p>
              </div>
              
              <div className="grid grid-cols-2 gap-6 w-full lg:w-auto">
                {stats.map((stat) => (
                  <div 
                    key={stat.label} 
                    className="bg-[#00261C] border border-[#EDF5F2]/10 rounded-2xl p-6 text-center min-w-[140px]"
                  >
                    <div className="text-3xl font-bold text-white mb-2 font-display">{stat.value}</div>
                    <div className="text-xs text-[#EDF5F2]/40 font-mono uppercase tracking-wider">{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>
            </div>
          </div>
        </section>

        {/* Bottom CTA */}
        <section className="relative py-24 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center max-w-3xl mx-auto">
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-8 font-display">
              Ready to validate your first LC?
            </h2>
            <p className="text-[#EDF5F2]/60 mb-10 text-lg">
              Free to start. No credit card required. Join 500+ exporters today.
            </p>
            <div className="flex justify-center gap-4">
              <Button 
                size="lg" 
                className="bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] px-10 py-6 h-auto font-bold text-lg border-none shadow-[0_0_20px_rgba(178,242,115,0.2)]"
                asChild
              >
                <Link to="/login">
                  Start Free
                  <ArrowRight className="w-5 h-5 ml-2" />
                </Link>
              </Button>
              <Button 
                variant="outline"
                size="lg" 
                className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 hover:border-[#EDF5F2]/40 bg-transparent px-8 py-6 h-auto"
                asChild
              >
                <Link to="/">
                  Learn More
                </Link>
              </Button>
            </div>
            </div>
          </div>
        </section>
      </main>
      <TRDRFooter />
    </div>
  );
}
