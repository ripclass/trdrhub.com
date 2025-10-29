import { Card, CardContent } from "@/components/ui/card";
import { Star } from "lucide-react";

const testimonials = [
  {
    quote: "TRDR Hub reduced our LC rejection rate by 80%. It's now integral to our operations and has saved us countless hours and substantial costs.",
    author: "Ahmed Rahman",
    title: "Senior Trade Officer",
    company: "Bengal Exports Ltd."
  },
  {
    quote: "The compliance features are outstanding. We can now ensure all our documentation meets international standards before submission to the bank.",
    author: "Sarah Chen",
    title: "Trade Finance Manager", 
    company: "Global Trading Solutions"
  },
  {
    quote: "As a bank, we appreciate the quality and consistency of documents processed through TRDR Hub. It has significantly reduced processing delays.",
    author: "Michael Thompson",
    title: "Director of Trade Finance",
    company: "First Commercial Bank"
  }
];

export function TRDRTestimonialsSection() {
  return (
    <section className="py-20 bg-muted/30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl lg:text-5xl font-bold text-foreground mb-6">
            Trusted by{" "}
            <span className="bg-gradient-primary bg-clip-text text-transparent">
              Trade Professionals
            </span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
            See what banks, exporters, and trade finance professionals are saying about TRDR Hub.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {testimonials.map((testimonial, index) => (
            <Card key={index} className="border border-gray-200/50 hover:border-primary/20 transition-all duration-300 hover:shadow-medium">
              <CardContent className="p-6">
                <div className="flex gap-1 mb-4">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="w-4 h-4 fill-warning text-warning" />
                  ))}
                </div>
                
                <blockquote className="text-foreground mb-6 leading-relaxed">
                  "{testimonial.quote}"
                </blockquote>
                
                <div className="border-t border-gray-200 pt-4">
                  <div className="font-semibold text-foreground">{testimonial.author}</div>
                  <div className="text-sm text-muted-foreground">{testimonial.title}</div>
                  <div className="text-sm font-medium text-primary">{testimonial.company}</div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="text-center mt-12">
          <p className="text-sm text-muted-foreground">
            💼 <strong>Join 500+ professionals</strong> who trust TRDR Hub for their trade finance needs
          </p>
        </div>
      </div>
    </section>
  );
}