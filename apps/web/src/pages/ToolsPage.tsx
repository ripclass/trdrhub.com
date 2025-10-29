import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { ToolsSection } from "@/components/sections/tools-section";

const ToolsPage = () => {
  return (
    <div className="min-h-screen bg-background">
      <TRDRHeader />
      <main>
        <div className="py-20 bg-gradient-hero">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h1 className="text-4xl lg:text-6xl font-bold text-white mb-6">
              Professional Trade Tools
            </h1>
            <p className="text-xl text-white/90 max-w-3xl mx-auto">
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