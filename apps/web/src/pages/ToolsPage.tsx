import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { ToolsSection } from "@/components/sections/tools-section";

const ToolsPage = () => {
  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      <main>
        <div className="pt-24 pb-12 relative overflow-hidden">
          {/* Background decoration */}
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />
          
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
            <h1 className="text-4xl lg:text-6xl font-bold text-white mb-6">
              Professional{" "}
              <span className="bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
                Trade Tools
              </span>
            </h1>
            <p className="text-xl text-slate-400 max-w-3xl mx-auto">
              Comprehensive suite of AI-powered tools for trade documentation,
              risk assessment, and compliance management.
            </p>
          </div>
        </div>
        <ToolsSection />
      </main>
      <TRDRFooter />
    </div>
  );
};

export default ToolsPage;
