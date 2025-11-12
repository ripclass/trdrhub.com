import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { TRDRHeroSection } from "@/components/sections/trdr-hero-section";
import { ToolsSection } from "@/components/sections/tools-section";
import { WhyTRDRSection } from "@/components/sections/why-trdr-section";
import { TRDRTestimonialsSection } from "@/components/sections/trdr-testimonials-section";
import { FeaturesSection } from "@/components/sections/features-section";
import { ProcessSection } from "@/components/sections/process-section";
import { CTASection } from "@/components/sections/cta-section";

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-background">
      <TRDRHeader />
      <main>
        <TRDRHeroSection />
        <FeaturesSection />
        <ProcessSection />
        <ToolsSection />
        <WhyTRDRSection />
        <TRDRTestimonialsSection />
        <CTASection />
      </main>
      <TRDRFooter />
    </div>
  );
};

export default LandingPage;