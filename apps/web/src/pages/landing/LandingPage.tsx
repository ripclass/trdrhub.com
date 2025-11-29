import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { TRDRHeroSection } from "@/components/sections/trdr-hero-section";
import { ProblemsSection } from "@/components/sections/problems-section";
import { SolutionSection } from "@/components/sections/solution-section";
import { ToolsSection } from "@/components/sections/tools-section";
import { TechnologySection } from "@/components/sections/technology-section";
import { WhyTRDRSection } from "@/components/sections/why-trdr-section";
import { PartnersSection } from "@/components/sections/partners-section";
import { FAQSection } from "@/components/sections/faq-section";
import { CTASection } from "@/components/sections/cta-section";

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-background">
      <TRDRHeader />
      <main>
        <TRDRHeroSection />
        <ProblemsSection />
        <SolutionSection />
        <ToolsSection />
        <TechnologySection />
        <WhyTRDRSection />
        <PartnersSection />
        <FAQSection />
        <CTASection />
      </main>
      <TRDRFooter />
    </div>
  );
};

export default LandingPage;
