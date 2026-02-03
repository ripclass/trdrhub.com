import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { ArrowRight, Code2, LineChart, Globe2, Coffee, Zap, Heart } from "lucide-react";

const perks = [
  {
    icon: Globe2,
    title: "Remote-First",
    description: "Work from anywhere. We care about your output, not your IP address."
  },
  {
    icon: Zap,
    title: "High Impact",
    description: "Ship code that moves billions of dollars in real-world trade assets."
  },
  {
    icon: Coffee,
    title: "Holistic Wellness",
    description: "Comprehensive health coverage, mental health days, and gym stipends."
  },
  {
    icon: Heart,
    title: "Ownership",
    description: "Competitive equity packages. When we win, you win."
  }
];

const openRoles = [
  {
    department: "Engineering",
    roles: [
      { title: "Senior Full Stack Engineer", loc: "Remote (APAC)", type: "Full-time" },
      { title: "AI/ML Engineer (NLP)", loc: "Singapore / Remote", type: "Full-time" },
      { title: "Platform Reliability Engineer", loc: "Remote", type: "Full-time" },
    ]
  },
  {
    department: "Product & Design",
    roles: [
      { title: "Senior Product Designer", loc: "Remote", type: "Full-time" },
      { title: "Product Manager (Trade Finance)", loc: "Singapore", type: "Full-time" },
    ]
  },
  {
    department: "GTM",
    roles: [
      { title: "Enterprise Account Executive", loc: "Dubai / Remote", type: "Full-time" },
      { title: "Solutions Engineer", loc: "Mumbai / Remote", type: "Full-time" },
    ]
  }
];

const CareersPage = () => {
  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main className="pt-48 md:pt-48 pb-24 relative min-h-screen">
        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none fixed" />

        {/* Background decoration */}
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
        <div className="absolute top-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          
          {/* Hero Section */}
          <div className="text-center mb-24">
            <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full border border-[#B2F273]/20 bg-[#B2F273]/5 backdrop-blur-sm mb-6">
              <span className="text-[#B2F273] font-mono text-xs tracking-wider uppercase">We're Hiring</span>
            </div>
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-white mb-8 leading-tight font-display">
              Build the Future
              <br />
              <span className="text-[#B2F273] text-glow-sm">of Trade.</span>
            </h1>
            <p className="text-lg text-[#EDF5F2]/60 max-w-2xl mx-auto font-light leading-relaxed mb-10">
              Join a team of engineers, designers, and trade experts working to modernize the $32 trillion global economy.
            </p>
            <Button 
              size="lg" 
              className="bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] px-8 font-bold border-none"
              onClick={() => document.getElementById('roles')?.scrollIntoView({ behavior: 'smooth' })}
            >
              View Open Roles
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </div>

          {/* Perks Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-32">
            {perks.map((perk, index) => (
              <div key={index} className="bg-[#00382E]/30 border border-[#EDF5F2]/10 rounded-2xl p-6 hover:bg-[#00382E]/50 transition-colors">
                <div className="w-12 h-12 bg-[#00261C] rounded-xl flex items-center justify-center mb-4 border border-[#EDF5F2]/5">
                  <perk.icon className="w-6 h-6 text-[#B2F273]" />
                </div>
                <h3 className="text-lg font-bold text-white mb-2 font-display">{perk.title}</h3>
                <p className="text-[#EDF5F2]/60 text-sm leading-relaxed">
                  {perk.description}
                </p>
              </div>
            ))}
          </div>

          {/* Roles Section */}
          <div id="roles" className="max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold text-white mb-12 font-display text-center">Open Positions</h2>
            
            <div className="space-y-12">
              {openRoles.map((dept, index) => (
                <div key={index}>
                  <h3 className="text-[#B2F273] font-mono text-sm tracking-widest uppercase mb-6 border-b border-[#EDF5F2]/10 pb-2">
                    {dept.department}
                  </h3>
                  <div className="space-y-4">
                    {dept.roles.map((role, rIndex) => (
                      <div 
                        key={rIndex}
                        className="group flex flex-col md:flex-row md:items-center justify-between bg-[#00261C] border border-[#EDF5F2]/10 rounded-xl p-6 hover:border-[#B2F273]/50 transition-all duration-300 cursor-pointer"
                      >
                        <div className="mb-4 md:mb-0">
                          <h4 className="text-xl font-bold text-white group-hover:text-[#B2F273] transition-colors font-display">
                            {role.title}
                          </h4>
                          <div className="flex gap-4 mt-2 text-sm text-[#EDF5F2]/60 font-mono">
                            <span>{role.loc}</span>
                            <span>•</span>
                            <span>{role.type}</span>
                          </div>
                        </div>
                        <Button variant="outline" className="border-[#EDF5F2]/20 text-[#EDF5F2] group-hover:bg-[#B2F273] group-hover:text-[#00261C] group-hover:border-[#B2F273] transition-all">
                          Apply Now
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-16 text-center p-8 bg-[#00382E]/20 rounded-2xl border border-dashed border-[#EDF5F2]/10">
              <p className="text-[#EDF5F2]/80 mb-4">
                Don't see your role? We're always looking for exceptional talent.
              </p>
              <a href="mailto:careers@trdrhub.com" className="text-[#B2F273] font-bold hover:underline">
                Email us at careers@trdrhub.com
              </a>
            </div>
          </div>

        </div>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default CareersPage;
