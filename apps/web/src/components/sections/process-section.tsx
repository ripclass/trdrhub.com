import { Card, CardContent } from "@/components/ui/card";
import { Upload, Brain, AlertTriangle, Download } from "lucide-react";

const steps = [
  {
    icon: Upload,
    title: "Upload Documents",
    description: "Upload your LC documents (Bill of Lading, Invoice, Packing List, etc.) in PDF format.",
    details: "Supports up to 10 documents per LC validation"
  },
  {
    icon: Brain,
    title: "AI Processing",
    description: "Our AI extracts and validates data against ICC/UCP600 rules automatically.",
    details: "OCR + LLM processing in under 60 seconds"
  },
  {
    icon: AlertTriangle,
    title: "Review Results",
    description: "Get detailed reports highlighting any discrepancies or compliance issues.",
    details: "Clear explanations and suggested corrections"
  },
  {
    icon: Download,
    title: "Download Package",
    description: "Receive a professional, bank-ready document package with cover sheet.",
    details: "PDF format with validation status report"
  }
];

export function ProcessSection() {
  return (
    <section id="process" className="py-20">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl lg:text-4xl font-bold text-foreground mb-4">
            Simple 4-Step{" "}
            <span className="bg-gradient-primary bg-clip-text text-transparent">
              Validation Process
            </span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Our streamlined process makes LC document validation fast, accurate, and hassle-free.
          </p>
        </div>

        <div className="relative">
          {/* Connection lines */}
          <div className="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-primary opacity-20 -translate-y-1/2" />
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 relative">
            {steps.map((step, index) => (
              <div key={index} className="relative">
                <Card className="text-center shadow-medium hover:shadow-strong transition-all duration-300 border-0 group">
                  <CardContent className="p-8">
                    <div className="w-16 h-16 bg-gradient-primary rounded-2xl flex items-center justify-center mx-auto mb-6 group-hover:scale-110 transition-transform duration-300">
                      <step.icon className="w-8 h-8 text-primary-foreground" />
                    </div>
                    <h3 className="text-xl font-semibold text-foreground mb-3">
                      {step.title}
                    </h3>
                    <p className="text-muted-foreground mb-4 leading-relaxed">
                      {step.description}
                    </p>
                    <div className="bg-secondary/50 rounded-lg p-3">
                      <p className="text-xs font-medium text-primary">
                        {step.details}
                      </p>
                    </div>
                  </CardContent>
                </Card>
                
                {/* Step number */}
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-bold shadow-medium">
                  {index + 1}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-16 text-center">
          <Card className="inline-block bg-card shadow-medium border border-primary/20">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="text-2xl font-bold text-primary">⚡</div>
                <div className="text-left">
                  <h3 className="font-semibold text-foreground">Average Processing Time</h3>
                  <p className="text-sm text-muted-foreground">45 seconds for 5-document LC validation</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}