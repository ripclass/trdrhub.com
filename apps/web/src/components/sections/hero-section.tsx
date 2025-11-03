import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Upload, CheckCircle, Download, Shield } from "lucide-react";
import { Link } from "react-router-dom";
// import heroImage from "@/assets/lc-hero-image.jpg";

export function HeroSection() {
  return (
    <section className="relative py-20 lg:py-32 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-hero opacity-5" />
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <div className="max-w-xl">
            <div className="flex items-center gap-2 text-sm font-medium text-primary mb-4">
              <Shield className="w-4 h-4" />
              Trusted by 500+ Bangladeshi Exporters
            </div>
            <h1 className="text-4xl lg:text-6xl font-bold text-foreground mb-6 leading-tight">
              Avoid Costly LC{" "}
              <span className="bg-gradient-primary bg-clip-text text-transparent">
                Errors
              </span>{" "}
              Get Bank-Ready in Minutes
            </h1>
            <p className="text-lg text-muted-foreground mb-8 leading-relaxed">
              AI-powered Letter of Credit compliance checking for Bangladeshi exporters and importers. 
              Validate documents against ICC/UCP600 rules with 95%+ accuracy.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 mb-8">
              <Button asChild size="lg" className="bg-gradient-exporter hover:opacity-90 shadow-medium">
                <Link to="/lcopilot/exporter-dashboard" className="!text-foreground hover:!text-white font-semibold">I'm an Exporter</Link>
              </Button>
              <Button asChild size="lg" className="bg-gradient-importer hover:opacity-90 shadow-medium">
                <Link to="/lcopilot/importer-dashboard" className="!text-foreground hover:!text-white font-semibold">I'm an Importer</Link>
              </Button>
              <Button asChild size="lg" className="bg-gradient-primary hover:opacity-90 shadow-medium">
                <Link to="/lcopilot/analytics/bank" className="!text-foreground hover:!text-white font-semibold">I'm a Bank / FI</Link>
              </Button>
            </div>
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-success" />
                90%+ Accuracy
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-success" />
                Under 1 Minute
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-success" />
                24/7 Available
              </div>
            </div>
          </div>

          <div className="relative">
            <div className="absolute inset-0 bg-gradient-primary rounded-3xl blur-3xl opacity-20" />
            <Card className="relative bg-card/50 backdrop-blur-sm border-0 shadow-strong overflow-hidden">
              <div className="aspect-video relative">
                <img 
                  src="https://via.placeholder.com/800x450/1a1b23/22c55e?text=LC+Validation+Dashboard" 
                  alt="LC Document Validation Dashboard" 
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-card via-transparent to-transparent" />
                <div className="absolute bottom-4 left-4 right-4">
                  <div className="bg-background/90 backdrop-blur-sm rounded-lg p-4 shadow-medium">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-semibold text-foreground">LC Validation Status</h3>
                      <div className="bg-success/10 text-success px-2 py-1 rounded-full text-xs font-medium">
                        Ready
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <Upload className="w-5 h-5 mx-auto mb-1 text-primary" />
                        <p className="text-xs font-medium">5 Documents</p>
                        <p className="text-xs text-muted-foreground">Uploaded</p>
                      </div>
                      <div>
                        <CheckCircle className="w-5 h-5 mx-auto mb-1 text-success" />
                        <p className="text-xs font-medium">Validated</p>
                        <p className="text-xs text-muted-foreground">100%</p>
                      </div>
                      <div>
                        <Download className="w-5 h-5 mx-auto mb-1 text-info" />
                        <p className="text-xs font-medium">Package</p>
                        <p className="text-xs text-muted-foreground">Ready</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
}