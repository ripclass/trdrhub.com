import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { Terminal, Copy, Check, Server, Lock, Zap, ArrowRight } from "lucide-react";
import { useState } from "react";

const endpoints = [
  { method: "POST", path: "/v1/validate/lc", desc: "Validate a Letter of Credit" },
  { method: "POST", path: "/v1/screen/party", desc: "Screen a party against sanctions" },
  { method: "GET",  path: "/v1/hs-code/search", desc: "Search for HS codes" },
  { method: "POST", path: "/v1/extract/ocr", desc: "Extract data from PDF/Image" },
];

const APIPage = () => {
  const [copied, setCopied] = useState(false);

  const copyCode = () => {
    navigator.clipboard.writeText(`curl -X POST https://api.trdrhub.com/v1/validate/lc \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "document_url": "https://example.com/lc.pdf",
    "ruleset": "ucp600"
  }'`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main className="pt-32 md:pt-48 pb-24 relative min-h-screen">
        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none fixed" />

        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          
          <div className="grid lg:grid-cols-2 gap-16 items-center mb-24">
            {/* Left Content */}
            <div>
              <div className="inline-flex items-center gap-2 mb-6">
                <div className="w-2 h-2 bg-[#B2F273] rounded-full animate-pulse" />
                <span className="text-[#B2F273] font-mono text-xs tracking-widest uppercase">API v1.4 Live</span>
              </div>
              <h1 className="text-4xl md:text-6xl font-bold text-white mb-6 font-display">
                Powerful, RESTful,
                <br />
                <span className="text-[#B2F273] text-glow-sm">Reliable.</span>
              </h1>
              <p className="text-lg text-[#EDF5F2]/60 leading-relaxed mb-8">
                Integrate bank-grade trade validation directly into your ERP, TMS, or custom platform. 
                Built for developers, by developers.
              </p>
              <div className="flex gap-4">
                <Button size="lg" className="bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] font-bold">
                  Get API Keys
                </Button>
                <Button variant="outline" size="lg" className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5">
                  View Full Reference
                </Button>
              </div>
            </div>

            {/* Right Code Block */}
            <div className="relative group">
              <div className="absolute -inset-1 bg-gradient-to-r from-[#B2F273]/20 to-[#00382E] rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-1000" />
              <div className="relative bg-[#001E16] rounded-2xl border border-[#EDF5F2]/10 overflow-hidden shadow-2xl">
                <div className="flex items-center justify-between px-4 py-3 border-b border-[#EDF5F2]/5 bg-[#00261C]">
                  <div className="flex gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50" />
                    <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50" />
                  </div>
                  <div className="flex items-center gap-2 text-xs text-[#EDF5F2]/40 font-mono">
                    <Terminal className="w-3 h-3" />
                    bash
                  </div>
                </div>
                <div className="p-6 overflow-x-auto">
                  <pre className="font-mono text-sm text-[#EDF5F2]/80 leading-relaxed">
                    <span className="text-[#B2F273]">curl</span> -X POST https://api.trdrhub.com/v1/validate/lc \<br/>
                    &nbsp;&nbsp;-H <span className="text-yellow-200">"Authorization: Bearer YOUR_API_KEY"</span> \<br/>
                    &nbsp;&nbsp;-H <span className="text-yellow-200">"Content-Type: application/json"</span> \<br/>
                    &nbsp;&nbsp;-d <span className="text-yellow-200">'{`{`}
    "document_url": "https://example.com/lc.pdf",
    "ruleset": "ucp600"
  {`}'`}</span>
                  </pre>
                </div>
                <button 
                  onClick={copyCode}
                  className="absolute top-14 right-4 p-2 rounded-lg bg-[#EDF5F2]/5 hover:bg-[#EDF5F2]/10 text-[#EDF5F2]/60 hover:text-white transition-colors"
                >
                  {copied ? <Check className="w-4 h-4 text-[#B2F273]" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>

          {/* Features Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-24">
            <div className="p-6 rounded-2xl bg-[#00382E]/20 border border-[#EDF5F2]/5">
              <Zap className="w-8 h-8 text-[#B2F273] mb-4" />
              <h3 className="text-xl font-bold text-white mb-2">Low Latency</h3>
              <p className="text-[#EDF5F2]/60 text-sm">Global edge network ensures sub-100ms response times for critical checks.</p>
            </div>
            <div className="p-6 rounded-2xl bg-[#00382E]/20 border border-[#EDF5F2]/5">
              <Lock className="w-8 h-8 text-[#B2F273] mb-4" />
              <h3 className="text-xl font-bold text-white mb-2">Secure by Default</h3>
              <p className="text-[#EDF5F2]/60 text-sm">TLS 1.3, granular scopes, and IP whitelisting available for all keys.</p>
            </div>
            <div className="p-6 rounded-2xl bg-[#00382E]/20 border border-[#EDF5F2]/5">
              <Server className="w-8 h-8 text-[#B2F273] mb-4" />
              <h3 className="text-xl font-bold text-white mb-2">99.99% Uptime</h3>
              <p className="text-[#EDF5F2]/60 text-sm">Redundant infrastructure designed for mission-critical financial workloads.</p>
            </div>
          </div>

          {/* Endpoints List */}
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl font-bold text-white mb-8 font-display">Core Endpoints</h2>
            <div className="space-y-4">
              {endpoints.map((ep, index) => (
                <div key={index} className="flex items-center gap-4 p-4 rounded-xl bg-[#00261C] border border-[#EDF5F2]/10 hover:border-[#B2F273]/30 transition-colors group cursor-pointer">
                  <span className={`
                    px-3 py-1 rounded text-xs font-bold font-mono w-16 text-center
                    ${ep.method === 'GET' ? 'bg-blue-500/10 text-blue-400' : ''}
                    ${ep.method === 'POST' ? 'bg-green-500/10 text-green-400' : ''}
                  `}>
                    {ep.method}
                  </span>
                  <span className="font-mono text-[#EDF5F2]/80 text-sm flex-1">{ep.path}</span>
                  <span className="text-[#EDF5F2]/40 text-sm">{ep.desc}</span>
                  <ArrowRight className="w-4 h-4 text-[#EDF5F2]/20 group-hover:text-[#B2F273] transition-colors" />
                </div>
              ))}
            </div>
          </div>

        </div>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default APIPage;
