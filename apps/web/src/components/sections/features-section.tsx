import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  FileText, 
  Brain, 
  Shield, 
  Zap, 
  Globe, 
  Package,
  CheckCircle,
  Clock
} from "lucide-react";

const features = [
  {
    icon: FileText,
    title: "Multi-Format OCR",
    description: "Extract text from PDFs in both English and Bengali using advanced OCR technology.",
    benefits: ["PaddleOCR + Tesseract", "99% Accuracy", "Batch Processing"]
  },
  {
    icon: Brain,
    title: "AI Data Extraction",
    description: "Intelligent field extraction from complex LC documents using advanced LLM models.",
    benefits: ["Kimi-K2 Integration", "Structured Output", "Smart Validation"]
  },
  {
    icon: Shield,
    title: "ICC/UCP600 Compliance",
    description: "Automated validation against international banking rules and regulations.",
    benefits: ["Rule Engine", "Discrepancy Detection", "Compliance Reports"]
  },
  {
    icon: Zap,
    title: "Lightning Fast",
    description: "Process entire LC document sets in under 60 seconds with real-time updates.",
    benefits: ["< 1 Min Processing", "Real-time Status", "Instant Results"]
  },
  {
    icon: Globe,
    title: "Mobile Optimized",
    description: "Work seamlessly on any device - perfect for exporters on the go.",
    benefits: ["Responsive Design", "Touch Friendly", "Offline Capable"]
  },
  {
    icon: Package,
    title: "Document Packaging",
    description: "Generate professional, bank-ready document packages with cover sheets.",
    benefits: ["PDF Merger", "Cover Pages", "Status Reports"]
  }
];

export function FeaturesSection() {
  return (
    <section id="features" className="py-20 bg-secondary/30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 text-sm font-medium text-primary mb-4">
            <CheckCircle className="w-4 h-4" />
            Complete Solution
          </div>
          <h2 className="text-3xl lg:text-4xl font-bold text-foreground mb-4">
            Everything You Need for{" "}
            <span className="bg-gradient-primary bg-clip-text text-transparent">
              LC Validation
            </span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            From document upload to bank-ready packages, our platform handles every step 
            of the LC validation process with precision and speed.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <Card key={index} className="group hover:shadow-medium transition-all duration-300 border-0 shadow-soft">
              <CardHeader>
                <div className="w-12 h-12 bg-gradient-primary rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                  <feature.icon className="w-6 h-6 text-primary-foreground" />
                </div>
                <CardTitle className="text-lg font-semibold text-foreground">
                  {feature.title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground mb-4 leading-relaxed">
                  {feature.description}
                </p>
                <div className="space-y-2">
                  {feature.benefits.map((benefit, benefitIndex) => (
                    <div key={benefitIndex} className="flex items-center gap-2 text-sm">
                      <CheckCircle className="w-3 h-3 text-success flex-shrink-0" />
                      <span className="text-muted-foreground">{benefit}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="mt-16 text-center">
          <Card className="inline-block bg-gradient-primary text-primary-foreground border-0 shadow-strong">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
                  <Clock className="w-6 h-6" />
                </div>
                <div className="text-left">
                  <h3 className="font-semibold mb-1">Ready in Minutes</h3>
                  <p className="text-sm opacity-90">Start validating your LC documents today</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}