import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { MessageCircle, Mail, Phone, FileText, Shield, Clock, CheckCircle, AlertTriangle } from "lucide-react";

const Support = () => {
  const faqs = [
    {
      question: "What is a Letter of Credit (LC)?",
      answer: "A Letter of Credit is a financial document issued by a bank on behalf of an importer, guaranteeing payment to an exporter upon presentation of compliant documents. It's a crucial trade finance instrument that reduces risk for both parties in international trade.",
      category: "basics"
    },
    {
      question: "How does the LC compliance checking work?",
      answer: "Our AI-powered system uses advanced OCR to extract text from your documents, then applies machine learning and rule engines based on ICC UCP 600 and ISBP 745 guidelines to identify discrepancies. The entire process takes 2-3 minutes and provides detailed reports.",
      category: "process"
    },
    {
      question: "Is my data secure and confidential?",
      answer: "Yes, absolutely. We use enterprise-grade encryption (AES-256) for data at rest and in transit. Documents are automatically deleted after 30 days unless you choose to keep them longer. We're SOC 2 compliant and follow strict data protection protocols.",
      category: "security"
    },
    {
      question: "What document formats do you support?",
      answer: "We support PDF, JPEG, PNG, and TIFF formats. Our OCR can handle both English and Bengali text. For best results, ensure documents are clear, high-resolution scans or photos.",
      category: "technical"
    },
    {
      question: "How accurate is the compliance checking?",
      answer: "Our system achieves 95%+ accuracy in identifying major discrepancies. However, we always recommend having experienced trade finance professionals review critical transactions. Our AI assists but doesn't replace human expertise.",
      category: "accuracy"
    },
    {
      question: "Can I integrate this with my existing ERP system?",
      answer: "Yes, we offer API integrations for Enterprise customers. Common integrations include SAP, Oracle, and custom ERP systems. Contact our sales team to discuss your specific requirements.",
      category: "technical"
    },
    {
      question: "What happens if I find an error in the system's analysis?",
      answer: "Please report any false positives or missed discrepancies to our support team. We continuously improve our algorithms based on user feedback and will investigate any issues promptly.",
      category: "support"
    },
    {
      question: "Do you provide training for my team?",
      answer: "Yes, Enterprise customers receive comprehensive onboarding and training sessions. We also offer webinars and documentation for all users to maximize the platform's effectiveness.",
      category: "support"
    }
  ];

  const contactMethods = [
    {
      icon: MessageCircle,
      title: "Live Chat",
      description: "Get instant help during business hours",
      detail: "Available 9 AM - 6 PM (GMT+6)",
      action: "Start Chat",
      primary: true
    },
    {
      icon: Mail,
      title: "Email Support",
      description: "Send us detailed questions",
      detail: "support@lcchecker.com",
      action: "Send Email",
      primary: false
    },
    {
      icon: Phone,
      title: "Phone Support",
      description: "Speak with our experts",
      detail: "+880-1XXX-XXXXXX",
      action: "Call Now",
      primary: false
    }
  ];

  const resources = [
    {
      icon: FileText,
      title: "Documentation",
      description: "Complete guides and API docs"
    },
    {
      icon: Shield,
      title: "Security Center",
      description: "Data protection and compliance info"
    },
    {
      icon: Clock,
      title: "System Status",
      description: "Real-time platform status"
    }
  ];

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="pt-16">
        {/* Hero Section */}
        <section className="py-20 bg-gradient-hero">
          <div className="container mx-auto px-4 text-center">
            <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-6">
              How Can We Help?
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
              Get the support you need to make the most of our LC compliance platform
            </p>
          </div>
        </section>

        {/* Contact Methods */}
        <section className="py-16">
          <div className="container mx-auto px-4">
            <h2 className="text-3xl font-bold text-center text-foreground mb-12">
              Get in Touch
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto mb-16">
              {contactMethods.map((method, index) => (
                <Card key={index} className={`text-center border-gray-200 hover:shadow-medium transition-all duration-300 ${method.primary ? 'border-primary' : ''}`}>
                  <CardContent className="p-8">
                    <method.icon className={`w-12 h-12 mx-auto mb-4 ${method.primary ? 'text-primary' : 'text-muted-foreground'}`} />
                    <h3 className="text-xl font-semibold text-foreground mb-2">
                      {method.title}
                    </h3>
                    <p className="text-muted-foreground mb-2">
                      {method.description}
                    </p>
                    <p className="text-sm text-muted-foreground mb-4">
                      {method.detail}
                    </p>
                    <Button variant={method.primary ? "default" : "outline"} className="w-full">
                      {method.action}
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Contact Form */}
            <Card className="max-w-2xl mx-auto">
              <CardHeader>
                <CardTitle className="text-center">Send us a Message</CardTitle>
                <CardDescription className="text-center">
                  We'll get back to you within 24 hours
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input id="name" placeholder="Your full name" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input id="email" type="email" placeholder="your@email.com" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="company">Company</Label>
                  <Input id="company" placeholder="Your company name" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="subject">Subject</Label>
                  <Input id="subject" placeholder="How can we help?" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="message">Message</Label>
                  <Textarea id="message" placeholder="Please describe your question or issue in detail..." rows={5} />
                </div>
                <Button className="w-full bg-gradient-primary">
                  Send Message
                </Button>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* FAQ Section */}
        <section className="py-20 bg-muted/30">
          <div className="container mx-auto px-4">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-foreground mb-4">
                Frequently Asked Questions
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Find answers to common questions about LC compliance and our platform
              </p>
            </div>
            
            <div className="max-w-4xl mx-auto">
              <Accordion type="single" collapsible className="space-y-4">
                {faqs.map((faq, index) => (
                  <AccordionItem key={index} value={`item-${index}`} className="bg-card border border-gray-200 rounded-lg px-6">
                    <AccordionTrigger className="text-left hover:no-underline">
                      <div className="flex items-center gap-3">
                        <Badge variant="outline" className="text-xs">
                          {faq.category}
                        </Badge>
                        <span className="font-medium">{faq.question}</span>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent className="text-muted-foreground pt-2 pb-4">
                      {faq.answer}
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </div>
          </div>
        </section>

        {/* Resources */}
        <section className="py-20">
          <div className="container mx-auto px-4">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-foreground mb-4">
                Additional Resources
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Explore our comprehensive resources to get the most out of our platform
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              {resources.map((resource, index) => (
                <Card key={index} className="text-center border-gray-200 hover:shadow-medium transition-all duration-300 cursor-pointer">
                  <CardContent className="p-8">
                    <resource.icon className="w-12 h-12 text-primary mx-auto mb-4" />
                    <h3 className="text-xl font-semibold text-foreground mb-2">
                      {resource.title}
                    </h3>
                    <p className="text-muted-foreground">
                      {resource.description}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* Status Banner */}
        <section className="py-8 bg-success/10 border-y border-success/20">
          <div className="container mx-auto px-4">
            <div className="flex items-center justify-center gap-3 text-center">
              <CheckCircle className="w-5 h-5 text-success" />
              <span className="text-success font-medium">All systems operational</span>
              <Badge variant="outline" className="text-success border-success/20">
                99.9% uptime
              </Badge>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
};

export default Support;