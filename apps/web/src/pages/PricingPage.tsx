import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { TRDRPricingSection } from "@/components/sections/trdr-pricing-section";

const PricingPage = () => {
  return (
    <div className="min-h-screen bg-background">
      <TRDRHeader />
      <main>
        <div className="py-20 bg-gradient-hero">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h1 className="text-4xl lg:text-6xl font-bold text-white mb-6">
              Pricing Plans
            </h1>
            <p className="text-xl text-white/90 max-w-3xl mx-auto">
              Choose the perfect plan for your business needs. Start with our 14-day free trial,
              no credit card required.
            </p>
          </div>
        </div>
        <TRDRPricingSection />
      </main>
      <TRDRFooter />
    </div>
  );
};

export default PricingPage;