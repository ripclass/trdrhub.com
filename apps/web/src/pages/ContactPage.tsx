import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Mail, Phone, MapPin, Send } from "lucide-react";
import { useState } from "react";

const ContactPage = () => {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    message: ""
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Contact form submitted:", formData);
    alert("Thank you for your message! We'll get back to you soon.");
    setFormData({ name: "", email: "", message: "" });
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="min-h-screen bg-background">
      <TRDRHeader />
      <main>
        {/* Hero Section */}
        <div className="py-20 bg-gradient-hero">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h1 className="text-4xl lg:text-6xl font-bold text-white mb-6">
              Contact Us
            </h1>
            <p className="text-xl text-white/90 max-w-3xl mx-auto">
              Get in touch with our team. We're here to help you streamline your trade operations.
            </p>
          </div>
        </div>

        {/* Contact Section */}
        <div className="py-20">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-6xl mx-auto">
              <div className="grid lg:grid-cols-2 gap-12">
                {/* Contact Form */}
                <Card className="border border-gray-200/50">
                  <CardHeader>
                    <CardTitle className="text-2xl font-bold">Send us a message</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-6">
                      <div>
                        <Label htmlFor="name">Full Name</Label>
                        <Input
                          id="name"
                          name="name"
                          type="text"
                          value={formData.name}
                          onChange={handleChange}
                          required
                          className="mt-1"
                          placeholder="Enter your full name"
                        />
                      </div>

                      <div>
                        <Label htmlFor="email">Email Address</Label>
                        <Input
                          id="email"
                          name="email"
                          type="email"
                          value={formData.email}
                          onChange={handleChange}
                          required
                          className="mt-1"
                          placeholder="Enter your email address"
                        />
                      </div>

                      <div>
                        <Label htmlFor="message">Message</Label>
                        <Textarea
                          id="message"
                          name="message"
                          value={formData.message}
                          onChange={handleChange}
                          required
                          className="mt-1 min-h-[120px]"
                          placeholder="Tell us how we can help you..."
                        />
                      </div>

                      <Button
                        type="submit"
                        className="w-full bg-gradient-primary hover:opacity-90"
                      >
                        <Send className="w-4 h-4 mr-2" />
                        Send Message
                      </Button>
                    </form>
                  </CardContent>
                </Card>

                {/* Contact Information */}
                <div className="space-y-8">
                  <div>
                    <h2 className="text-3xl font-bold text-foreground mb-6">Get in Touch</h2>
                    <p className="text-lg text-muted-foreground mb-8">
                      Have questions about our platform? Need help with trade documentation?
                      Our expert team is ready to assist you.
                    </p>
                  </div>

                  <div className="space-y-6">
                    <Card className="border border-gray-200/50 hover:border-primary/20 transition-all duration-300">
                      <CardContent className="p-6">
                        <div className="flex items-start gap-4">
                          <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                            <Mail className="w-5 h-5 text-primary" />
                          </div>
                          <div>
                            <h3 className="font-semibold mb-1">Email Us</h3>
                            <p className="text-muted-foreground text-sm mb-2">
                              Send us an email and we'll respond within 24 hours
                            </p>
                            <a
                              href="mailto:support@trdrhub.com"
                              className="text-primary hover:underline"
                            >
                              support@trdrhub.com
                            </a>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="border border-gray-200/50 hover:border-primary/20 transition-all duration-300">
                      <CardContent className="p-6">
                        <div className="flex items-start gap-4">
                          <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                            <Phone className="w-5 h-5 text-primary" />
                          </div>
                          <div>
                            <h3 className="font-semibold mb-1">Call Us</h3>
                            <p className="text-muted-foreground text-sm mb-2">
                              Speak with our support team
                            </p>
                            <p className="text-primary">+1 (555) 123-4567</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="border border-gray-200/50 hover:border-primary/20 transition-all duration-300">
                      <CardContent className="p-6">
                        <div className="flex items-start gap-4">
                          <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                            <MapPin className="w-5 h-5 text-primary" />
                          </div>
                          <div>
                            <h3 className="font-semibold mb-1">Visit Us</h3>
                            <p className="text-muted-foreground text-sm mb-2">
                              Our headquarters
                            </p>
                            <p className="text-muted-foreground text-sm">
                              123 Trade Center<br />
                              Business District<br />
                              New York, NY 10001
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>

                  <div className="bg-muted/30 rounded-lg p-6">
                    <h3 className="font-semibold mb-2">Need immediate help?</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      Check out our comprehensive documentation and FAQs for quick answers.
                    </p>
                    <Button variant="outline" className="w-full">
                      View Documentation
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      <TRDRFooter />
    </div>
  );
};

export default ContactPage;