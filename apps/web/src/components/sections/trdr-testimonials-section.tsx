import { Card, CardContent } from "@/components/ui/card";
import { Star, TrendingDown, Clock, DollarSign } from "lucide-react";

const testimonials = [
  {
    quote: "We were paying $300-400 in discrepancy fees per shipment. Last quarter? Zero. TRDR Hub pays for itself in the first week.",
    author: "Kamal Hossain",
    title: "Export Director",
    company: "Dhaka Garments International",
    metric: { icon: DollarSign, value: "$2,400", label: "Saved in fees (Q3)" },
    avatar: "KH"
  },
  {
    quote: "Our document reviewer used to spend 4 hours per LC checking compliance. Now it's a 2-minute upload. She handles 3x the volume.",
    author: "Priya Sharma",
    title: "Trade Finance Manager", 
    company: "Mumbai Textile Exports",
    metric: { icon: Clock, value: "4hrs → 2min", label: "Review time" },
    avatar: "PS"
  },
  {
    quote: "As a bank, we notice immediately when documents come from TRDR Hub users. Clean, compliant, ready to process. Fewer queries, faster payments.",
    author: "James Wong",
    title: "VP Trade Operations",
    company: "Regional Commercial Bank",
    metric: { icon: TrendingDown, value: "80%", label: "Fewer queries" },
    avatar: "JW"
  }
];

export function TRDRTestimonialsSection() {
  return (
    <section className="py-20 bg-muted/30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <p className="text-primary font-medium mb-4">REAL RESULTS</p>
          <h2 className="text-3xl lg:text-5xl font-bold text-foreground mb-6">
            They stopped losing money.{" "}
            <span className="bg-gradient-primary bg-clip-text text-transparent">
              So can you.
            </span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Don't take our word for it. Here's what happens when exporters and banks start using TRDR Hub.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {testimonials.map((testimonial, index) => (
            <Card key={index} className="border border-gray-200/50 hover:border-primary/20 transition-all duration-300 hover:shadow-medium overflow-hidden">
              <CardContent className="p-6">
                {/* Metric highlight */}
                <div className="bg-primary/5 rounded-lg p-3 mb-4 flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
                    <testimonial.metric.icon className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <div className="text-xl font-bold text-primary">{testimonial.metric.value}</div>
                    <div className="text-xs text-muted-foreground">{testimonial.metric.label}</div>
                  </div>
                </div>
                
                {/* Stars */}
                <div className="flex gap-1 mb-4">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                  ))}
                </div>
                
                <blockquote className="text-foreground mb-6 leading-relaxed">
                  "{testimonial.quote}"
                </blockquote>
                
                {/* Author */}
                <div className="flex items-center gap-3 pt-4 border-t border-gray-200">
                  <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center text-primary font-semibold text-sm">
                    {testimonial.avatar}
                  </div>
                  <div>
                    <div className="font-semibold text-foreground text-sm">{testimonial.author}</div>
                    <div className="text-xs text-muted-foreground">{testimonial.title}</div>
                    <div className="text-xs font-medium text-primary">{testimonial.company}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Trust badges */}
        <div className="mt-16 text-center">
          <p className="text-sm text-muted-foreground mb-6">Trusted by exporters in</p>
          <div className="flex flex-wrap justify-center gap-6 text-muted-foreground">
            <span className="text-2xl">🇧🇩</span>
            <span className="text-2xl">🇮🇳</span>
            <span className="text-2xl">🇨🇳</span>
            <span className="text-2xl">🇻🇳</span>
            <span className="text-2xl">🇸🇬</span>
            <span className="text-2xl">🇦🇪</span>
            <span className="text-2xl">🇬🇧</span>
            <span className="text-2xl">🇩🇪</span>
          </div>
        </div>
      </div>
    </section>
  );
}
