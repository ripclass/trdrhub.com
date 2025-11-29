import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, Shield, Zap, Globe, FileCheck, Upload, BarChart3, Download, Brain, Clock, DollarSign, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const roles = [
  {
    id: "exporter",
    title: "I'm an Exporter",
    description: "Validate export LCs against UCP600/ISBP745, catch discrepancies before banks do, and ship with confidence.",
    to: "/lcopilot/exporter-dashboard",
    accent: "from-blue-500 to-blue-600",
  },
  {
    id: "importer",
    title: "I'm an Importer",
    description: "Screen supplier documents, manage LC applications, and reduce costly rejections before goods ship.",
    to: "/lcopilot/importer-dashboard",
    accent: "from-emerald-500 to-emerald-600",
  },
  {
    id: "bank",
    title: "I'm a Bank",
    description: "Automate document examination, monitor compliance quality, and collaborate with clients in real time.",
    to: "/lcopilot/analytics/bank",
    accent: "from-purple-500 to-purple-600",
  },
];

const features = [
  {
    icon: Brain,
    title: "AI That Reads Like a Banker",
    description: "Our AI is trained on thousands of LC rejections. It knows exactly what banks look for - and what they reject.",
    bullets: ["Catches 99% of discrepancies", "Learns from every validation", "Explains issues in plain English"],
  },
  {
    icon: FileCheck,
    title: "3,500+ Compliance Rules",
    description: "UCP600, ISBP745, ISP98, URDG758, plus 60+ country regulations. More rules than most banks use internally.",
    bullets: ["ICC rule library included", "Country-specific checks", "Updated monthly"],
  },
  {
    icon: Globe,
    title: "Any Document, Any Format",
    description: "PDF, scan, photo from your phone - we extract the data. Supports MT700, ISO20022, and any LC format.",
    bullets: ["Multi-language OCR", "Handwriting recognition", "Photo uploads work"],
  },
];

const features2 = [
  {
    icon: Zap,
    title: "45 Seconds, Not 4 Hours",
    description: "Upload your LC and docs. Get a complete compliance report before your coffee gets cold.",
    bullets: ["Instant extraction", "Real-time validation", "Bank-ready reports"],
  },
  {
    icon: Shield,
    title: "Sanctions Screening Built-In",
    description: "Every validation includes automatic screening against OFAC, EU, UN, and UK sanctions lists.",
    bullets: ["Party name screening", "Vessel & port checks", "Real-time list updates"],
  },
  {
    icon: DollarSign,
    title: "Bank-Ready Output",
    description: "Get exactly what banks want: clear issue cards, suggested fixes, and compliance certificates.",
    bullets: ["PDF report download", "Field-by-field breakdown", "Suggested amendments"],
  },
];

const process = [
  {
    step: 1,
    title: "Upload Documents",
    description: "Drop your LC documents (Bill of Lading, Invoice, Packing List, etc.) in PDF format. Any format works.",
  },
  {
    step: 2,
    title: "AI Validates",
    description: "3,500+ rules. Checks every field. Cross-references documents. Completes in ~45 seconds.",
  },
  {
    step: 3,
    title: "Fix & Submit",
    description: "Clear issue cards tell you exactly what to fix. Download bank-ready package with confidence.",
  },
];

const stats = [
  { value: "500+", label: "Happy Customers" },
  { value: "10,000+", label: "Documents Processed" },
  { value: "₹50L+", label: "Bank Charges Saved" },
  { value: "99.2%", label: "Accuracy Rate" },
];

const testimonials = [
  {
    quote: "LCopilot saved us $1.5M in potential bank charges. The AI catches discrepancies we missed manually. Our team can always trade-ready.",
    author: "Rashida Begum",
    role: "Export Manager",
    company: "Bengal Textiles Ltd",
    rating: 5,
  },
  {
    quote: "As an importer, this tool helps me review LC terms before finalization. It flags risky clauses and ensures compliance. Essential for our operations.",
    author: "Karim Hassan",
    role: "Trade Finance Head",
    company: "Dhaka Import Co.",
    rating: 5,
  },
  {
    quote: "Processing time reduced from 2 hours to 5 minutes. The detailed discrepancy reports help us fix issues before submission. Incredible efficiency gain.",
    author: "Fatima Ahmed",
    role: "Documentation Officer",
    company: "Green Valley Exports",
    rating: 5,
  },
];

const faqs = [
  {
    question: "How accurate is the AI validation?",
    answer: "Our engine achieves 99% accuracy on discrepancy detection. We validate against 3,500+ rules from UCP600, ISBP745, and 60+ country regulations.",
  },
  {
    question: "Which document types do you support?",
    answer: "All standard trade documents: Letters of Credit (MT700, ISO20022, PDF), Bills of Lading, Commercial Invoices, Packing Lists, Insurance Certificates, and more.",
  },
  {
    question: "How long does validation take?",
    answer: "Average processing time is 45 seconds for a complete document set (6 documents). Includes OCR extraction, cross-document validation, and report generation.",
  },
  {
    question: "What's the pricing?",
    answer: "Free tier for up to 5 validations/month. Pro at $49/month for unlimited. Enterprise with custom pricing. No per-document fees on paid plans.",
  },
];

const Index = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      
      <main>
        {/* Hero Section */}
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid lg:grid-cols-2 gap-12 items-center">
              <div>
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-6">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-emerald-400 text-sm font-medium">Trusted by 500+ Exporters</span>
                </div>
                
                <h1 className="text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                  Avoid Costly LC{" "}
                  <span className="bg-gradient-to-r from-red-400 to-red-500 bg-clip-text text-transparent">Errors</span>{" "}
                  Get Bank-Ready in Minutes
                </h1>
                
                <p className="text-lg text-slate-400 mb-8 leading-relaxed">
                  AI-powered Letter of Credit compliance checking. Validate documents against UCP600/ISBP745 
                  rules with 99% accuracy. Stop paying $75 discrepancy fees.
                </p>

                <div className="flex flex-wrap gap-4 mb-8">
                  {roles.map((role) => (
                    <Button 
                      key={role.id}
                      asChild 
                      size="lg" 
                      className={`bg-gradient-to-r ${role.accent} hover:opacity-90 text-white font-semibold`}
                    >
                      <Link to={role.to}>{role.title}</Link>
                    </Button>
                  ))}
                </div>

                <div className="flex flex-wrap items-center gap-6 text-sm text-slate-400">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                    99%+ Accuracy
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                    Under 1 Minute
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                    24/7 Available
                  </div>
                </div>
              </div>

              {/* Dashboard Preview */}
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-emerald-500/20 rounded-3xl blur-3xl" />
                <div className="relative bg-slate-900/80 backdrop-blur-sm border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
                  <div className="bg-slate-800/50 px-4 py-3 border-b border-slate-700">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-500" />
                      <div className="w-3 h-3 rounded-full bg-yellow-500" />
                      <div className="w-3 h-3 rounded-full bg-emerald-500" />
                      <span className="ml-4 text-slate-400 text-sm">LC Validation Dashboard</span>
                    </div>
                  </div>
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="font-semibold text-white">LC Validation Status</h3>
                      <span className="bg-emerald-500/20 text-emerald-400 px-3 py-1 rounded-full text-xs font-medium border border-emerald-500/30">
                        Ready
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="bg-slate-800/50 rounded-lg p-4 text-center">
                        <Upload className="w-6 h-6 mx-auto mb-2 text-blue-400" />
                        <p className="text-sm font-medium text-white">5 Documents</p>
                        <p className="text-xs text-slate-500">Uploaded</p>
                      </div>
                      <div className="bg-slate-800/50 rounded-lg p-4 text-center">
                        <CheckCircle className="w-6 h-6 mx-auto mb-2 text-emerald-400" />
                        <p className="text-sm font-medium text-white">Validated</p>
                        <p className="text-xs text-slate-500">100%</p>
                      </div>
                      <div className="bg-slate-800/50 rounded-lg p-4 text-center">
                        <Download className="w-6 h-6 mx-auto mb-2 text-purple-400" />
                        <p className="text-sm font-medium text-white">Package</p>
                        <p className="text-xs text-slate-500">Ready</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="py-20 bg-slate-900 border-y border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <p className="text-emerald-400 font-semibold mb-4 tracking-wide uppercase text-sm">How It Works</p>
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                Upload. Validate. <span className="text-slate-400">Ship with confidence.</span>
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Three clicks. 45 seconds. Know exactly what banks will flag - before you submit.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              {process.map((step) => (
                <div key={step.step} className="text-center">
                  <div className="w-16 h-16 bg-emerald-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-emerald-500/30">
                    <span className="text-2xl font-bold text-emerald-400">{step.step}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{step.title}</h3>
                  <p className="text-slate-400 text-sm">{step.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid md:grid-cols-3 gap-6 mb-6">
              {features.map((feature, idx) => (
                <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 hover:border-emerald-500/30 transition-colors">
                  <div className="w-12 h-12 bg-emerald-500/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-emerald-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((bullet, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-500">
                        <CheckCircle className="w-4 h-4 text-emerald-500" />
                        {bullet}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <div className="grid md:grid-cols-3 gap-6">
              {features2.map((feature, idx) => (
                <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 hover:border-emerald-500/30 transition-colors">
                  <div className="w-12 h-12 bg-emerald-500/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-emerald-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((bullet, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-500">
                        <CheckCircle className="w-4 h-4 text-emerald-500" />
                        {bullet}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Simple Process Strip */}
        <section className="py-16 bg-slate-900 border-y border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-8">
              <h2 className="text-2xl md:text-3xl font-bold text-white">
                Simple 4-Step <span className="text-emerald-400">Validation Process</span>
              </h2>
              <p className="text-slate-400 mt-2">Our streamlined process makes LC document validation fast, accurate, and hassle-free.</p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto">
              {[
                { icon: Upload, title: "Upload Documents", desc: "Upload your LC documents (Bill of Lading, Invoice, Packing List, etc.) in PDF format." },
                { icon: Brain, title: "AI Processing", desc: "Our AI extracts and validates data against UCP600/ISBP rules automatically." },
                { icon: BarChart3, title: "Review Results", desc: "Get detailed reports highlighting any discrepancies or compliance issues." },
                { icon: Download, title: "Download Package", desc: "Receive a professional, bank-ready document package with cover sheets." },
              ].map((step, idx) => (
                <div key={idx} className="text-center">
                  <div className="w-14 h-14 bg-emerald-500/10 rounded-xl flex items-center justify-center mx-auto mb-3 border border-emerald-500/20">
                    <step.icon className="w-7 h-7 text-emerald-400" />
                  </div>
                  <h3 className="font-semibold text-white mb-1">{step.title}</h3>
                  <p className="text-slate-500 text-xs">{step.desc}</p>
                </div>
              ))}
            </div>
            <div className="text-center mt-8">
              <div className="inline-flex items-center gap-2 text-slate-400 text-sm">
                <Clock className="w-4 h-4 text-emerald-400" />
                <span><strong className="text-white">Average Processing Time:</strong> 45 seconds for 5 document LC validation</span>
              </div>
            </div>
          </div>
        </section>

        {/* Stats + Testimonials */}
        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                Trusted by Leading Exporters & Importers
              </h2>
              <p className="text-slate-400">Join hundreds of businesses who have eliminated costly LC errors with our platform.</p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto mb-16">
              {stats.map((stat, idx) => (
                <div key={idx} className="text-center">
                  <div className="text-3xl md:text-4xl font-bold text-white mb-1">{stat.value}</div>
                  <div className="text-sm text-slate-500">{stat.label}</div>
                </div>
              ))}
            </div>

            {/* Testimonials */}
            <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
              {testimonials.map((t, idx) => (
                <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                  <div className="flex gap-1 mb-4">
                    {[...Array(t.rating)].map((_, i) => (
                      <span key={i} className="text-yellow-400">★</span>
                    ))}
                  </div>
                  <p className="text-slate-300 text-sm mb-4 leading-relaxed">"{t.quote}"</p>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-slate-700 rounded-full flex items-center justify-center text-white font-semibold text-sm">
                      {t.author.split(' ').map(n => n[0]).join('')}
                    </div>
                    <div>
                      <div className="text-white font-medium text-sm">{t.author}</div>
                      <div className="text-slate-500 text-xs">{t.role}, {t.company}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-2xl mx-auto">
              <div className="text-center mb-12">
                <h2 className="text-3xl font-bold text-white mb-4">Frequently Asked Questions</h2>
              </div>
              <div className="space-y-4">
                {faqs.map((faq, idx) => (
                  <div key={idx} className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
                    <button
                      onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                      className="w-full flex items-center justify-between p-5 text-left"
                    >
                      <span className="font-medium text-white">{faq.question}</span>
                      <ChevronDown className={cn("w-5 h-5 text-slate-400 transition-transform", openFaq === idx && "rotate-180")} />
                    </button>
                    <div className={cn("grid transition-all", openFaq === idx ? "grid-rows-[1fr]" : "grid-rows-[0fr]")}>
                      <div className="overflow-hidden">
                        <p className="px-5 pb-5 text-slate-400 text-sm">{faq.answer}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
                Ready to validate your
                <br />
                <span className="bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">first LC for free?</span>
              </h2>
              <p className="text-xl text-slate-400 mb-8">
                No credit card required. Get your first 5 validations free, forever.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Button size="lg" className="bg-white text-slate-900 hover:bg-slate-100 text-lg px-8 py-6 h-auto font-semibold" asChild>
                  <Link to="/lcopilot/exporter-dashboard">
                    Start Validating Now <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button variant="outline" size="lg" className="border-slate-700 text-slate-300 hover:bg-slate-800 text-lg px-8 py-6 h-auto" asChild>
                  <Link to="/contact">Talk to Sales</Link>
                </Button>
              </div>
            </div>
          </div>
        </section>
      </main>

      <TRDRFooter />
    </div>
  );
};

export default Index;
