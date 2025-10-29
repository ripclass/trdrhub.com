import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { TRDRHeroSection } from "@/components/sections/trdr-hero-section";
import { ToolsSection } from "@/components/sections/tools-section";
import { WhyTRDRSection } from "@/components/sections/why-trdr-section";
import { TRDRTestimonialsSection } from "@/components/sections/trdr-testimonials-section";
import { TRDRPricingSection } from "@/components/sections/trdr-pricing-section";

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-background">
      <TRDRHeader />
      <main>
        <TRDRHeroSection />
        <ToolsSection />
        <WhyTRDRSection />
        <TRDRTestimonialsSection />
        <TRDRPricingSection />
      </main>
      <TRDRFooter />
    </div>
  );
};

export default LandingPage;