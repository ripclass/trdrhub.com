import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, Book, Code2, Terminal, FileText, ArrowRight, Zap, Shield } from "lucide-react";
import { Link } from "react-router-dom";

const categories = [
  {
    icon: Zap,
    title: "Quick Start",
    description: "Get up and running with TRDR Hub in less than 5 minutes.",
    link: "/docs/quick-start"
  },
  {
    icon: Code2,
    title: "API Reference",
    description: "Detailed endpoints, parameters, and response schemas.",
    link: "/api"
  },
  {
    icon: Terminal,
    title: "SDKs & Libraries",
    description: "Official client libraries for Node.js, Python, and Go.",
    link: "/docs/sdks"
  },
  {
    icon: Shield,
    title: "Compliance Guides",
    description: "Best practices for UCP600, sanctions, and export controls.",
    link: "/guides/ucp600"
  }
];

const popularArticles = [
  "Authentication & Rate Limiting",
  "Validating your first Letter of Credit",
  "Webhooks & Events",
  "Handling Validation Errors",
  "Sanctions Screening Logic"
];

const DocsPage = () => {
  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main className="pt-40 md:pt-48 pb-24 relative min-h-screen">
        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none fixed" />

        {/* Background decoration */}
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
        
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          
          {/* Hero Section */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full border border-[#B2F273]/20 bg-[#B2F273]/5 backdrop-blur-sm mb-6">
              <span className="text-[#B2F273] font-mono text-xs tracking-wider uppercase">Developer Hub</span>
            </div>
            <h1 className="text-4xl md:text-6xl font-bold text-white mb-6 font-display">
              Documentation
            </h1>
            <p className="text-lg text-[#EDF5F2]/60 max-w-2xl mx-auto font-light leading-relaxed mb-10">
              Everything you need to integrate TRDR Hub's trade validation engine into your applications.
            </p>

            {/* Search Bar */}
            <div className="max-w-2xl mx-auto relative mb-12">
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-[#B2F273]/20 to-[#00382E] rounded-xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200" />
                <div className="relative">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#EDF5F2]/40" />
                  <Input 
                    type="text" 
                    placeholder="Search documentation (e.g. 'webhooks', 'rate limits')..." 
                    className="w-full h-14 pl-12 pr-4 bg-[#00261C] border border-[#EDF5F2]/10 text-white placeholder-[#EDF5F2]/30 rounded-xl focus:border-[#B2F273]/50 focus:ring-[#B2F273]/20 text-lg"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Categories Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto mb-20">
            {categories.map((cat, index) => (
              <Link 
                key={index} 
                to={cat.link}
                className="group bg-[#00382E]/30 border border-[#EDF5F2]/10 rounded-2xl p-8 hover:border-[#B2F273]/30 transition-all duration-300 hover:bg-[#00382E]/50"
              >
                <div className="flex items-start gap-6">
                  <div className="w-12 h-12 bg-[#00261C] rounded-xl flex items-center justify-center shrink-0 border border-[#EDF5F2]/5 group-hover:border-[#B2F273]/20 transition-colors">
                    <cat.icon className="w-6 h-6 text-[#B2F273]" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white mb-2 font-display group-hover:text-[#B2F273] transition-colors">
                      {cat.title}
                    </h3>
                    <p className="text-[#EDF5F2]/60 leading-relaxed">
                      {cat.description}
                    </p>
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Popular Articles */}
          <div className="max-w-3xl mx-auto">
            <h2 className="text-2xl font-bold text-white mb-6 font-display">Popular Articles</h2>
            <div className="grid gap-4">
              {popularArticles.map((article, index) => (
                <Link 
                  key={index}
                  to="#"
                  className="flex items-center justify-between p-4 rounded-xl bg-[#00261C] border border-[#EDF5F2]/5 hover:border-[#B2F273]/30 transition-all group"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="w-4 h-4 text-[#EDF5F2]/40 group-hover:text-[#B2F273] transition-colors" />
                    <span className="text-[#EDF5F2]/80 group-hover:text-white transition-colors">{article}</span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-[#EDF5F2]/20 group-hover:text-[#B2F273] transition-colors" />
                </Link>
              ))}
            </div>
          </div>

        </div>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default DocsPage;
