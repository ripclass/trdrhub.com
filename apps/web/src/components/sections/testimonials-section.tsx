import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Star, Quote } from "lucide-react";

const testimonials = [
  {
    name: "Rashida Begum",
    role: "Export Manager",
    company: "Bengal Textiles Ltd.",
    content: "LCopilot saved us ৳2.5 lakh in potential bank charges. The AI catches discrepancies we missed manually. Now our documents are always bank-ready.",
    rating: 5,
    avatar: "RB",
    type: "exporter"
  },
  {
    name: "Karim Hassan",
    role: "Trade Finance Head",
    company: "Dhaka Import Co.",
    content: "As an importer, this tool helps me review LC terms before finalization. It flags risky clauses and ensures compliance. Essential for our operations.",
    rating: 5,
    avatar: "KH",
    type: "importer"
  },
  {
    name: "Fatima Ahmed",
    role: "Documentation Officer",
    company: "Green Valley Exports",
    content: "Processing time reduced from 2 hours to 5 minutes. The detailed discrepancy reports help us fix issues before submission. Incredible efficiency gain.",
    rating: 5,
    avatar: "FA",
    type: "exporter"
  }
];

const stats = [
  { value: "500+", label: "Happy Customers" },
  { value: "10,000+", label: "Documents Processed" },
  { value: "৳50L+", label: "Bank Charges Saved" },
  { value: "99.2%", label: "Accuracy Rate" }
];

export function TestimonialsSection() {
  return (
    <section className="py-20 bg-muted/30">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16">
          <h2 className="text-3xl lg:text-4xl font-bold text-foreground mb-4">
            Trusted by Leading Exporters & Importers
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Join hundreds of businesses who have eliminated costly LC errors with our platform
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-16">
          {stats.map((stat, index) => (
            <div key={index} className="text-center">
              <div className="text-3xl font-bold text-primary mb-2">{stat.value}</div>
              <div className="text-sm text-muted-foreground">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* Testimonials */}
        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {testimonials.map((testimonial, index) => (
            <Card key={index} className="relative border-gray-200 hover:shadow-medium transition-all duration-300">
              <CardContent className="p-6">
                <div className="absolute top-4 right-4">
                  <Quote className="w-8 h-8 text-primary/20" />
                </div>
                
                <div className="flex items-center mb-4">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} className="w-4 h-4 text-yellow-400 fill-current" />
                  ))}
                </div>

                <p className="text-muted-foreground mb-6 leading-relaxed">
                  "{testimonial.content}"
                </p>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
                      <span className="text-sm font-semibold text-primary">
                        {testimonial.avatar}
                      </span>
                    </div>
                    <div>
                      <div className="font-semibold text-foreground">{testimonial.name}</div>
                      <div className="text-sm text-muted-foreground">{testimonial.role}</div>
                      <div className="text-xs text-muted-foreground">{testimonial.company}</div>
                    </div>
                  </div>
                  <Badge 
                    variant="outline" 
                    className={testimonial.type === 'exporter' ? 'border-exporter text-exporter' : 'border-importer text-importer'}
                  >
                    {testimonial.type === 'exporter' ? 'Exporter' : 'Importer'}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* CTA */}
        <div className="text-center mt-16">
          <div className="inline-flex items-center gap-2 bg-success/10 text-success px-4 py-2 rounded-full text-sm font-medium mb-4">
            <Star className="w-4 h-4 fill-current" />
            <span>4.9/5 average rating from 500+ reviews</span>
          </div>
        </div>
      </div>
    </section>
  );
}