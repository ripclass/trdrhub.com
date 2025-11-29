import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  FileText, 
  Brain, 
  Shield, 
  Zap, 
  CheckCircle,
  AlertTriangle
} from "lucide-react";

const features = [
  {
    icon: Brain,
    title: "AI That Reads Like a Banker",
    description: "Our AI is trained on thousands of LC rejections. It knows exactly what banks look for — and what they reject.",
    benefits: ["Catches 99% of discrepancies", "Learns from every validation", "Explains issues in plain English"]
  },
  {
    icon: Shield,
    title: "3,500+ Compliance Rules",
    description: "UCP600, ISBP745, ISP98, URDG758, plus 60+ country regulations. More rules than most banks use internally.",
    benefits: ["ICC rule library included", "Country-specific checks", "Updated monthly"]
  },
  {
    icon: FileText,
    title: "Any Document, Any Format",
    description: "PDF, scan, photo from your phone — we extract the data. Bengali, Chinese, Arabic? No problem.",
    benefits: ["Multi-language OCR", "Handwriting recognition", "Photo uploads work"]
  },
  {
    icon: Zap,
    title: "45 Seconds, Not 4 Hours",
    description: "Upload your LC and docs. Get a complete compliance report before your coffee gets cold.",
    benefits: ["Instant extraction", "Real-time validation", "Bank-ready reports"]
  },
  {
    icon: AlertTriangle,
    title: "Sanctions Screening Built-In",
    description: "Every validation includes automatic screening against OFAC, EU, UN, and UK sanctions lists.",
    benefits: ["Party name screening", "Vessel & port checks", "Real-time list updates"]
  },
  {
    icon: CheckCircle,
    title: "Bank-Ready Output",
    description: "Get exactly what banks want: clear issue cards, suggested fixes, and compliance certificates.",
    benefits: ["PDF export", "Issue-by-issue breakdown", "Suggested amendments"]
  }
];

export function FeaturesSection() {
  return (
    <section id="features" className="py-20 bg-secondary/30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <p className="text-primary font-medium mb-4">HOW IT WORKS</p>
          <h2 className="text-3xl lg:text-4xl font-bold text-foreground mb-4">
            Upload. Validate.{" "}
            <span className="bg-gradient-primary bg-clip-text text-transparent">
              Ship with confidence.
            </span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Three clicks. 45 seconds. Know exactly what banks will flag — before you submit.
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
                <p className="text-muted-foreground mb-4 leading-relaxed text-sm">
                  {feature.description}
                </p>
                <div className="space-y-2">
                  {feature.benefits.map((benefit, benefitIndex) => (
                    <div key={benefitIndex} className="flex items-center gap-2 text-sm">
                      <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0" />
                      <span className="text-muted-foreground">{benefit}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Simple process steps */}
        <div className="mt-20 max-w-4xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="w-12 h-12 bg-primary text-primary-foreground rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
                1
              </div>
              <h3 className="font-semibold text-foreground mb-2">Upload Documents</h3>
              <p className="text-sm text-muted-foreground">
                Drag & drop your LC and supporting docs. Any format works.
              </p>
            </div>
            <div>
              <div className="w-12 h-12 bg-primary text-primary-foreground rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
                2
              </div>
              <h3 className="font-semibold text-foreground mb-2">AI Validates</h3>
              <p className="text-sm text-muted-foreground">
                3,500+ rules check every field. 45 seconds to complete report.
              </p>
            </div>
            <div>
              <div className="w-12 h-12 bg-primary text-primary-foreground rounded-full flex items-center justify-center mx-auto mb-4 text-xl font-bold">
                3
              </div>
              <h3 className="font-semibold text-foreground mb-2">Fix & Submit</h3>
              <p className="text-sm text-muted-foreground">
                Clear issue cards tell you exactly what to fix. Submit with confidence.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
