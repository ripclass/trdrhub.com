import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Mail, Phone, MapPin, Send, MessageSquare, HelpCircle, Building2 } from "lucide-react";
import { useState } from "react";

const ContactPage = () => {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    subject: "",
    message: ""
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Contact form submitted:", formData);
    alert("Thank you for your message! We'll get back to you soon.");
    setFormData({ name: "", email: "", subject: "", message: "" });
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      <main className="pt-32 md:pt-48 pb-24 relative min-h-screen">
        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none fixed" />

        {/* Background decoration */}
        <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
        <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          
          {/* Hero Section */}
          <div className="text-center mb-24">
            <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full border border-[#B2F273]/20 bg-[#B2F273]/5 backdrop-blur-sm mb-6">
              <span className="text-[#B2F273] font-mono text-xs tracking-wider uppercase">Contact Us</span>
            </div>
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-white mb-8 leading-tight font-display">
              Let's Talk
              <br />
              <span className="text-[#B2F273] text-glow-sm">Trade.</span>
            </h1>
            <p className="text-lg text-[#EDF5F2]/60 max-w-2xl mx-auto font-light leading-relaxed">
              Whether you're an enterprise looking for a custom solution or a developer with a technical question, we're here to help.
            </p>
          </div>

          <div className="max-w-6xl mx-auto">
            <div className="grid lg:grid-cols-2 gap-12">
              
              {/* Contact Form */}
              <Card className="bg-[#00382E]/30 border border-[#EDF5F2]/10 backdrop-blur-sm">
                <CardHeader>
                  <CardTitle className="text-2xl font-bold text-white font-display">Send us a message</CardTitle>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <Label htmlFor="name" className="text-[#EDF5F2]/80">Full Name</Label>
                        <Input
                          id="name"
                          name="name"
                          value={formData.name}
                          onChange={handleChange}
                          required
                          className="bg-[#00261C] border-[#EDF5F2]/10 text-white placeholder:text-[#EDF5F2]/20 focus:border-[#B2F273]/50"
                          placeholder="John Doe"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="email" className="text-[#EDF5F2]/80">Email Address</Label>
                        <Input
                          id="email"
                          name="email"
                          type="email"
                          value={formData.email}
                          onChange={handleChange}
                          required
                          className="bg-[#00261C] border-[#EDF5F2]/10 text-white placeholder:text-[#EDF5F2]/20 focus:border-[#B2F273]/50"
                          placeholder="john@company.com"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="subject" className="text-[#EDF5F2]/80">Subject</Label>
                      <Input
                        id="subject"
                        name="subject"
                        value={formData.subject}
                        onChange={handleChange}
                        required
                        className="bg-[#00261C] border-[#EDF5F2]/10 text-white placeholder:text-[#EDF5F2]/20 focus:border-[#B2F273]/50"
                        placeholder="How can we help?"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="message" className="text-[#EDF5F2]/80">Message</Label>
                      <Textarea
                        id="message"
                        name="message"
                        value={formData.message}
                        onChange={handleChange}
                        required
                        className="min-h-[150px] bg-[#00261C] border-[#EDF5F2]/10 text-white placeholder:text-[#EDF5F2]/20 focus:border-[#B2F273]/50"
                        placeholder="Tell us about your project..."
                      />
                    </div>

                    <Button
                      type="submit"
                      size="lg"
                      className="w-full bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] font-bold"
                    >
                      <Send className="w-4 h-4 mr-2" />
                      Send Message
                    </Button>
                  </form>
                </CardContent>
              </Card>

              {/* Contact Info & Channels */}
              <div className="space-y-8">
                <div className="grid gap-6">
                  <div className="group bg-[#00261C] border border-[#EDF5F2]/10 rounded-2xl p-6 hover:border-[#B2F273]/30 transition-all duration-300">
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 bg-[#00382E] rounded-xl flex items-center justify-center shrink-0 group-hover:bg-[#B2F273]/20 transition-colors">
                        <MessageSquare className="w-6 h-6 text-[#B2F273]" />
                      </div>
                      <div>
                        <h3 className="font-bold text-white text-lg mb-1 font-display">Sales Inquiry</h3>
                        <p className="text-[#EDF5F2]/60 text-sm mb-3">
                          Interested in Enterprise plans or custom integrations?
                        </p>
                        <a href="mailto:sales@trdrhub.com" className="text-[#B2F273] hover:underline font-medium">
                          sales@trdrhub.com
                        </a>
                      </div>
                    </div>
                  </div>

                  <div className="group bg-[#00261C] border border-[#EDF5F2]/10 rounded-2xl p-6 hover:border-[#B2F273]/30 transition-all duration-300">
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 bg-[#00382E] rounded-xl flex items-center justify-center shrink-0 group-hover:bg-[#B2F273]/20 transition-colors">
                        <HelpCircle className="w-6 h-6 text-[#B2F273]" />
                      </div>
                      <div>
                        <h3 className="font-bold text-white text-lg mb-1 font-display">Technical Support</h3>
                        <p className="text-[#EDF5F2]/60 text-sm mb-3">
                          Need help with the API or platform features?
                        </p>
                        <a href="mailto:support@trdrhub.com" className="text-[#B2F273] hover:underline font-medium">
                          support@trdrhub.com
                        </a>
                      </div>
                    </div>
                  </div>

                  <div className="group bg-[#00261C] border border-[#EDF5F2]/10 rounded-2xl p-6 hover:border-[#B2F273]/30 transition-all duration-300">
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 bg-[#00382E] rounded-xl flex items-center justify-center shrink-0 group-hover:bg-[#B2F273]/20 transition-colors">
                        <Building2 className="w-6 h-6 text-[#B2F273]" />
                      </div>
                      <div>
                        <h3 className="font-bold text-white text-lg mb-1 font-display">Global HQ</h3>
                        <p className="text-[#EDF5F2]/60 text-sm mb-3">
                          71 Ayer Rajah Crescent, #05-14<br />
                          Singapore 139951
                        </p>
                        <div className="flex gap-4 text-sm">
                          <span className="text-[#EDF5F2]/40">Reg: 202312345K</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Map Placeholder (Visual Element) */}
                <div className="relative h-48 bg-[#00382E]/30 rounded-2xl border border-[#EDF5F2]/10 overflow-hidden flex items-center justify-center">
                  <div className="absolute inset-0 opacity-20 bg-[url('https://upload.wikimedia.org/wikipedia/commons/e/ec/World_map_blank_without_borders.svg')] bg-cover bg-center" />
                  <div className="relative z-10 flex items-center gap-2">
                    <div className="w-2 h-2 bg-[#B2F273] rounded-full animate-ping" />
                    <span className="text-[#B2F273] font-mono text-sm tracking-widest uppercase">Operating Globally</span>
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
