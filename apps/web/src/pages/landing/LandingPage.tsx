// Homepage — Phase 4 rebuild (2026-07 launch): hero = LCopilot service
// framing, then the four live tools + RulGPT cross-link. PartnersSection
// removed — it name-dropped banks we have no relationship with (honesty
// rubric: no "trusted by banks").
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { TRDRHeroSection } from "@/components/sections/trdr-hero-section";
import { ProblemsSection } from "@/components/sections/problems-section";
import { ToolsSection } from "@/components/sections/tools-section";
import { FAQSection } from "@/components/sections/faq-section";
import { CTASection } from "@/components/sections/cta-section";

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-background">
      <TRDRHeader />
      <main>
        <TRDRHeroSection />
        <ToolsSection />
        <ProblemsSection />
        <FAQSection />
        <CTASection />
      </main>
      <TRDRFooter />
    </div>
  );
};

export default LandingPage;
