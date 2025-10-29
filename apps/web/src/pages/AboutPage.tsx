import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Shield, Users, Globe, Award, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

const AboutPage = () => {
  return (
    <div className="min-h-screen bg-background">
      <TRDRHeader />
      <main>
        {/* Hero Section */}
        <div className="py-20 bg-gradient-hero">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h1 className="text-4xl lg:text-6xl font-bold text-white mb-6">
              About TRDR Hub
            </h1>
            <p className="text-xl text-white/90 max-w-3xl mx-auto">
              The professional platform for Transactional Risk & Data Reconciliation
            </p>
          </div>
        </div>

        {/* Main Content */}
        <div className="py-20">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
              <div className="mb-16">
                <h2 className="text-3xl font-bold text-foreground mb-6">Our Mission</h2>
                <p className="text-lg text-muted-foreground leading-relaxed mb-6">
                  TRDR Hub is the professional platform for Transactional Risk & Data Reconciliation.
                  We help SMEs and banks prevent errors, reduce risk, and stay compliant with global trade rules.
                </p>
                <p className="text-lg text-muted-foreground leading-relaxed">
                  Our AI-powered suite of tools transforms complex trade documentation processes into
                  streamlined, error-free workflows, enabling businesses to focus on growth while maintaining
                  the highest standards of compliance and risk management.
                </p>
              </div>

              <div className="grid md:grid-cols-2 gap-8 mb-16">
                <Card className="border border-gray-200/50 hover:border-primary/20 transition-all duration-300">
                  <CardContent className="p-8">
                    <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                      <Shield className="w-6 h-6 text-primary" />
                    </div>
                    <h3 className="text-xl font-semibold mb-3">Risk Reduction</h3>
                    <p className="text-muted-foreground">
                      Advanced AI algorithms identify potential risks and discrepancies before they
                      become costly problems, protecting your business and reputation.
                    </p>
                  </CardContent>
                </Card>

                <Card className="border border-gray-200/50 hover:border-primary/20 transition-all duration-300">
                  <CardContent className="p-8">
                    <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                      <Users className="w-6 h-6 text-primary" />
                    </div>
                    <h3 className="text-xl font-semibold mb-3">Built for SMEs</h3>
                    <p className="text-muted-foreground">
                      Designed specifically for small and medium enterprises who need enterprise-grade
                      tools without the complexity and cost of traditional solutions.
                    </p>
                  </CardContent>
                </Card>

                <Card className="border border-gray-200/50 hover:border-primary/20 transition-all duration-300">
                  <CardContent className="p-8">
                    <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                      <Globe className="w-6 h-6 text-primary" />
                    </div>
                    <h3 className="text-xl font-semibold mb-3">Global Compliance</h3>
                    <p className="text-muted-foreground">
                      Stay compliant with international trade regulations across multiple jurisdictions
                      with our continuously updated compliance frameworks.
                    </p>
                  </CardContent>
                </Card>

                <Card className="border border-gray-200/50 hover:border-primary/20 transition-all duration-300">
                  <CardContent className="p-8">
                    <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                      <Award className="w-6 h-6 text-primary" />
                    </div>
                    <h3 className="text-xl font-semibold mb-3">Proven Results</h3>
                    <p className="text-muted-foreground">
                      Our platform has helped businesses reduce processing time by 90% and eliminate
                      costly documentation errors, saving thousands in potential penalties.
                    </p>
                  </CardContent>
                </Card>
              </div>

              <div className="text-center">
                <h2 className="text-3xl font-bold text-foreground mb-6">Ready to Get Started?</h2>
                <p className="text-lg text-muted-foreground mb-8">
                  Join hundreds of businesses already using TRDR Hub to streamline their trade operations.
                </p>
                <Link to="/lcopilot/register">
                  <Button className="bg-gradient-primary hover:opacity-90 text-lg px-8 py-3">
                    Start Free Trial
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default AboutPage;