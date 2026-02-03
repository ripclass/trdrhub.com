import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { 
  Brain, 
  Database, 
  Shield, 
  Zap, 
  FileCode, 
  Globe2, 
  Lock, 
  Cpu, 
  Network, 
  Server, 
  Code2, 
  Workflow,
  CheckCircle2,
  ArrowRight
} from "lucide-react";

const techStack = [
  {
    icon: Brain,
    title: "Context-Aware AI",
    description: "Our proprietary LLM models don't just read text; they understand trade context. Trained on 2M+ trade documents to distinguish between 'Port of Loading' and 'Place of Receipt' with 99.9% accuracy.",
    tags: ["LLM", "NLP", "Computer Vision"]
  },
  {
    icon: Database,
    title: "Universal Rule Engine",
    description: "A deterministic validation layer encoding 3,500+ rules from UCP600, ISBP745, and 60+ country-specific regulations. It catches discrepancies that generic AI models miss.",
    tags: ["Rule Engine", "UCP600", "ISBP745"]
  },
  {
    icon: Shield,
    title: "Bank-Grade Security",
    description: "SOC 2 Type II compliant infrastructure with AES-256 encryption at rest and TLS 1.3 in transit. Your trade data is isolated in dedicated tenant enclaves.",
    tags: ["SOC 2", "AES-256", "Zero Trust"]
  },
  {
    icon: Zap,
    title: "Real-Time Processing",
    description: "Distributed edge computing architecture processes complex 100-page document sets in under 45 seconds. 10x faster than manual review.",
    tags: ["Edge Computing", "Serverless", "Low Latency"]
  },
  {
    icon: FileCode,
    title: "Native ISO 20022",
    description: "Built-in parsing and generation for the modern financial messaging standard. Seamlessly convert between PDF, MT700, and ISO 20022 XML.",
    tags: ["ISO 20022", "MT7xx", "XML/JSON"]
  },
  {
    icon: Globe2,
    title: "Global Knowledge Graph",
    description: "A continuously updated graph of ports, HS codes, sanctions lists, and vessel data. We verify data against ground truth, not just document consistency.",
    tags: ["Knowledge Graph", "Sanctions", "Master Data"]
  }
];

const architectureSteps = [
  {
    icon: Server,
    title: "Ingestion",
    description: "Multi-format support (PDF, Image, Swift, XML) with auto-classification."
  },
  {
    icon: Cpu,
    title: "Extraction",
    description: "Hybrid OCR + AI extraction pipeline with confidence scoring per field."
  },
  {
    icon: Network,
    title: "Validation",
    description: "Cross-document consistency checks and rule-based compliance verification."
  },
  {
    icon: Code2,
    title: "Integration",
    description: "Structured JSON/XML output delivered via API, Webhook, or UI."
  }
];

const TechnologyPage = () => {
  // Force rebuild
  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main className="pt-40 md:pt-48 pb-24 relative min-h-screen">
        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none fixed" />

        {/* Background decoration */}
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
        <div className="absolute top-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          
          {/* Hero Section */}
          <div className="text-center mb-24">
            <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full border border-[#B2F273]/20 bg-[#B2F273]/5 backdrop-blur-sm mb-6">
              <span className="text-[#B2F273] font-mono text-xs tracking-wider uppercase">Under the Hood</span>
            </div>
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-white mb-8 leading-tight font-display">
              Built for the
              <br />
              <span className="text-[#B2F273] text-glow-sm">Future of Trade.</span>
            </h1>
            <p className="text-lg text-[#EDF5F2]/60 max-w-3xl mx-auto font-light leading-relaxed mb-10">
              We've combined state-of-the-art Generative AI with deterministic rule engines to solve the "Hallucination Problem" in trade finance.
            </p>
            <div className="flex justify-center gap-4">
              <Button 
                size="lg" 
                className="bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] px-8 font-bold border-none"
                asChild
              >
                <Link to="/api">
                  Read API Docs
                </Link>
              </Button>
              <Button 
                variant="outline"
                size="lg" 
                className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 hover:border-[#EDF5F2]/40 bg-transparent"
                asChild
              >
                <Link to="/contact">
                  Contact Engineering
                </Link>
              </Button>
            </div>
          </div>

          {/* Architecture Diagram */}
          <div className="mb-32">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-white mb-4 font-display">Processing Pipeline</h2>
              <p className="text-[#EDF5F2]/60">How we turn messy documents into structured data.</p>
            </div>
            
            <div className="relative">
              {/* Connector Line (Desktop) */}
              <div className="hidden md:block absolute top-1/2 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-[#B2F273]/20 to-transparent -translate-y-1/2 z-0" />
              
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 relative z-10">
                {architectureSteps.map((step, index) => (
                  <div key={index} className="group bg-[#00261C] border border-[#EDF5F2]/10 rounded-2xl p-8 text-center hover:border-[#B2F273]/50 transition-all duration-300 relative">
                    <div className="w-16 h-16 bg-[#00382E] rounded-full flex items-center justify-center mx-auto mb-6 group-hover:bg-[#B2F273] transition-colors duration-300 relative z-10 border-4 border-[#00261C]">
                      <step.icon className="w-8 h-8 text-[#EDF5F2]/60 group-hover:text-[#00261C] transition-colors duration-300" />
                    </div>
                    <h3 className="text-xl font-bold text-white mb-3 font-display">{step.title}</h3>
                    <p className="text-sm text-[#EDF5F2]/60">{step.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Core Tech Stack Grid */}
          <div className="mb-32">
            <div className="text-center mb-16">
              <h2 className="text-3xl md:text-5xl font-bold text-white mb-6 font-display">Core Technologies</h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                Our platform is built on a modern, scalable stack designed for accuracy, speed, and security.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {techStack.map((tech, index) => (
                <div 
                  key={index}
                  className="bg-[#00261C] border border-[#EDF5F2]/10 rounded-2xl p-8 hover:border-[#B2F273]/30 transition-all duration-300 group"
                >
                  <div className="flex items-start justify-between mb-6">
                    <div className="w-12 h-12 bg-[#00382E] rounded-lg flex items-center justify-center group-hover:bg-[#B2F273]/20 transition-colors">
                      <tech.icon className="w-6 h-6 text-[#B2F273]" />
                    </div>
                  </div>
                  
                  <h3 className="text-2xl font-bold text-white mb-4 font-display">{tech.title}</h3>
                  <p className="text-[#EDF5F2]/60 leading-relaxed mb-6 min-h-[80px]">
                    {tech.description}
                  </p>
                  
                  <div className="flex flex-wrap gap-2">
                    {tech.tags.map((tag, i) => (
                      <span 
                        key={i} 
                        className="px-3 py-1 bg-[#00382E] rounded-full text-xs font-mono text-[#B2F273]/80 border border-[#B2F273]/10"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Security Section */}
          <div className="bg-[#00382E]/30 border border-[#EDF5F2]/10 rounded-3xl p-8 md:p-16 mb-24 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl" />
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center relative z-10">
              <div>
                <div className="inline-flex items-center gap-2 mb-6">
                  <Lock className="w-5 h-5 text-[#B2F273]" />
                  <span className="text-[#B2F273] font-mono text-xs tracking-widest uppercase">Security First</span>
                </div>
                <h2 className="text-3xl md:text-5xl font-bold text-white mb-6 font-display">
                  Your data is safer than in a bank vault.
                </h2>
                <p className="text-[#EDF5F2]/60 text-lg mb-8 leading-relaxed">
                  We understand that trade documents contain sensitive financial and competitive information. 
                  That's why security isn't an afterthought—it's the foundation of our architecture.
                </p>
                
                <ul className="space-y-4">
                  {[
                    "SOC 2 Type II Certified",
                    "GDPR & CCPA Compliant",
                    "Role-Based Access Control (RBAC)",
                    "Audit Logs for Every Action",
                    "Data Residency Options"
                  ].map((item, i) => (
                    <li key={i} className="flex items-center gap-3 text-white">
                      <CheckCircle2 className="w-5 h-5 text-[#B2F273]" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              <div className="bg-[#00261C] border border-[#EDF5F2]/10 rounded-2xl p-8 relative">
                <div className="absolute inset-0 bg-[linear-gradient(45deg,transparent_25%,rgba(178,242,115,0.05)_50%,transparent_75%,transparent_100%)] bg-[length:250%_250%,100%_100%] animate-[background-position_0s_ease-in-out_infinite] bg-fixed" />
                <div className="space-y-6">
                  <div className="flex items-center justify-between border-b border-[#EDF5F2]/10 pb-4">
                    <span className="text-[#EDF5F2]/60 font-mono text-sm">Encryption</span>
                    <span className="text-[#B2F273] font-mono text-sm">AES-256-GCM</span>
                  </div>
                  <div className="flex items-center justify-between border-b border-[#EDF5F2]/10 pb-4">
                    <span className="text-[#EDF5F2]/60 font-mono text-sm">Transport</span>
                    <span className="text-[#B2F273] font-mono text-sm">TLS 1.3</span>
                  </div>
                  <div className="flex items-center justify-between border-b border-[#EDF5F2]/10 pb-4">
                    <span className="text-[#EDF5F2]/60 font-mono text-sm">Key Management</span>
                    <span className="text-[#B2F273] font-mono text-sm">AWS KMS</span>
                  </div>
                  <div className="flex items-center justify-between pb-2">
                    <span className="text-[#EDF5F2]/60 font-mono text-sm">Penetration Testing</span>
                    <span className="text-[#B2F273] font-mono text-sm">Quarterly</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom CTA */}
          <div className="text-center max-w-3xl mx-auto">
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-8 font-display">
              Ready to integrate?
            </h2>
            <p className="text-[#EDF5F2]/60 mb-10 text-lg">
              Get your API keys and start validating documents in minutes. 
              Our developer-friendly documentation makes integration a breeze.
            </p>
            <Button 
              size="lg" 
              className="bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] px-10 py-6 h-auto font-bold text-lg border-none shadow-[0_0_20px_rgba(178,242,115,0.2)]"
              asChild
            >
              <Link to="/lcopilot">
                Start Building Free
                <ArrowRight className="w-5 h-5 ml-2" />
              </Link>
            </Button>
          </div>

        </div>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default TechnologyPage;
