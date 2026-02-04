import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, FileText, Clock, Zap, Shield, Globe, Download, ChevronDown, FileCheck, Package, Receipt, ScrollText, Award, ClipboardCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const documentTypes = [
  { name: "Commercial Invoice", icon: Receipt, description: "Pre-filled from LC, bank-compliant format" },
  { name: "Packing List", icon: Package, description: "Detailed carton breakdown with weights" },
  { name: "Certificate of Origin", icon: Award, description: "Multiple formats: Form A, EUR.1, RCEP" },
  { name: "Bill of Lading Draft", icon: ScrollText, description: "Standard layout for carrier/shipper review" },
  { name: "Weight Certificate", icon: FileText, description: "Auto-calculated from packing details" },
  { name: "Beneficiary Certificate", icon: FileCheck, description: "LC-compliant attestation documents" },
  { name: "Insurance Certificate", icon: Shield, description: "Marine cargo policy certificates" },
  { name: "Inspection Certificate", icon: FileCheck, description: "Pre-shipment inspection reports" },
];

const features = [
  {
    icon: Zap,
    title: "Pre-Filled from LC Data",
    description: "Upload your LC once. All documents auto-populate with correct buyer, seller, goods description, and terms.",
    bullets: ["Auto-extract LC terms", "Consistent data across docs", "No manual re-entry", "Reduces typo errors by 95%"],
  },
  {
    icon: Shield,
    title: "Bank-Compliant Formats",
    description: "Templates designed to pass bank examination. Formatting, fonts, and layouts that banks expect to see.",
    bullets: ["UCP600 compliant", "ISBP745 aligned", "Bank-specific templates", "Proper document dating"],
  },
  {
    icon: Globe,
    title: "Country-Specific Templates",
    description: "Certificate of Origin formats for every FTA. Know exactly which form your destination requires.",
    bullets: ["Form A (GSP)", "EUR.1, EUR-MED", "RCEP, CPTPP forms", "US-specific formats"],
  },
  {
    icon: FileCheck,
    title: "Consistency Checker",
    description: "Automatic cross-check between documents. Catch weight mismatches, description differences, and value discrepancies.",
    bullets: ["Cross-doc validation", "Weight reconciliation", "Value matching", "Description consistency"],
  },
  {
    icon: Download,
    title: "Multiple Export Formats",
    description: "Download as PDF for submission, Word for editing, or Excel for data manipulation.",
    bullets: ["Bank-ready PDFs", "Editable Word docs", "Excel data export", "Batch download"],
  },
  {
    icon: Clock,
    title: "10x Faster Preparation",
    description: "What takes hours manually takes minutes with Doc Generator. Focus on your business, not paperwork.",
    bullets: ["Minutes not hours", "Template library", "Reuse previous docs", "Bulk generation"],
  },
];

const process = [
  {
    step: "1",
    title: "Upload Your LC",
    description: "Upload your Letter of Credit or enter shipment details manually",
  },
  {
    step: "2",
    title: "Select Documents",
    description: "Choose which documents you need - invoice, packing list, COO, etc.",
  },
  {
    step: "3",
    title: "Review & Download",
    description: "Preview each document, make adjustments, and download bank-ready PDFs",
  },
];

const stats = [
  { value: "95%", label: "Error Reduction" },
  { value: "10x", label: "Faster Prep" },
  { value: "15+", label: "Doc Types" },
  { value: "6", label: "Banks Supported" },
];

const pricing = [
  { tier: "Starter", docs: "10 doc sets/mo", price: "$29/mo", description: "For occasional exporters", features: ["Basic templates", "PDF export", "Email support"] },
  { tier: "Professional", docs: "50 doc sets/mo", price: "$79/mo", description: "For regular exporters", features: ["All templates", "Word/Excel export", "LC integration", "Priority support"], popular: true },
  { tier: "Enterprise", docs: "Unlimited", price: "$199/mo", description: "For freight & banks", features: ["Everything in Pro", "Custom templates", "API access", "White-label option"] },
];

const faqs = [
  {
    q: "What documents can I generate?",
    a: "We support 15+ trade document types including Commercial Invoice, Packing List, Certificate of Origin (Form A, EUR.1, RCEP), Bill of Lading draft, Weight Certificate, Beneficiary Certificate, Bill of Exchange, Inspection Certificate, Insurance Certificate, and Shipping Instructions.",
  },
  {
    q: "Can I customize the templates?",
    a: "Yes! Professional and Enterprise plans allow you to customize templates with your logo, letterhead, and specific formatting. Enterprise plans include fully custom template design.",
  },
  {
    q: "How does LC integration work?",
    a: "Upload your LC PDF and our AI extracts key fields - buyer/seller details, goods description, amounts, shipping terms, and document requirements. These auto-populate into every document you generate.",
  },
  {
    q: "Are the documents compliant with UCP600?",
    a: "Yes, all templates are designed to meet UCP600 and ISBP745 requirements. We follow ICC guidelines for document formatting, dating, and content structure.",
  },
  {
    q: "Can I edit documents after generation?",
    a: "Absolutely. Download in Word format for editing, or use our built-in editor to make changes before downloading the final PDF.",
  },
];

const DocGeneratorLanding = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      
      <main>
        {/* Hero Section */}
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden bg-[#00261C]">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-[#B2F273]/10 rounded-full blur-[120px]" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-[100px]" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center mb-12">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#B2F273]/10 border border-[#B2F273]/20 mb-6">
                <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                <span className="text-[#B2F273] text-sm font-medium">Now Available</span>
              </div>
              
              <h1 className="text-3xl sm:text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight font-display">
                Generate Trade Docs in{" "}
                <span className="text-[#B2F273] text-glow-sm">Minutes, Not Hours</span>
              </h1>
              
              <p className="text-lg text-[#EDF5F2]/60 mb-8 leading-relaxed max-w-2xl mx-auto">
                Bank-compliant commercial invoices, packing lists, and certificates of origin - 
                all pre-filled from your LC data. No more manual entry, no more typos.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
                <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
                  <Link to="/doc-generator/dashboard">
                    Start Generating <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button variant="outline" size="lg" className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 bg-transparent" asChild>
                  <Link to="/doc-generator/dashboard/new">Create First Document</Link>
                </Button>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-[#EDF5F2]/60">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  UCP600 Compliant
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  Pre-filled from LC
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  20+ Document Types
                </div>
              </div>
            </div>

            {/* Document Types Grid */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 max-w-4xl mx-auto">
              {documentTypes.map((doc, idx) => (
                <div key={idx} className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-4 hover:border-[#B2F273]/30 transition-colors backdrop-blur-sm group">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 bg-[#B2F273]/10 rounded-lg flex items-center justify-center shrink-0 border border-[#B2F273]/20 group-hover:bg-[#B2F273] transition-colors">
                      <doc.icon className="w-5 h-5 text-[#B2F273] group-hover:text-[#00261C] transition-colors" />
                    </div>
                    <div>
                      <h3 className="text-white font-bold text-sm font-display">{doc.name}</h3>
                      <p className="text-[#EDF5F2]/60 text-xs mt-1">{doc.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Stats */}
        <section className="relative py-12 bg-[#00261C] border-y border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto">
              {stats.map((stat, idx) => (
                <div key={idx} className="text-center">
                  <div className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-1 font-display">{stat.value}</div>
                  <div className="text-sm text-[#EDF5F2]/60 font-mono uppercase tracking-wider">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Problem Statement */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          
          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white text-center mb-12 font-display">
                Document Prep is a{" "}
                <span className="text-[#B2F273]">Time Sink</span>
              </h2>
              
              <div className="grid md:grid-cols-2 gap-8">
                <div className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 backdrop-blur-sm">
                  <h3 className="text-lg font-bold text-white mb-4 font-display">The Old Way</h3>
                  <ul className="space-y-3 text-[#EDF5F2]/60">
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Hours copying data between Word docs
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Typos and inconsistencies across documents
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Wrong COO format for the destination
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Bank rejects for formatting issues
                    </li>
                  </ul>
                </div>
                <div className="bg-[#B2F273]/5 border border-[#B2F273]/20 rounded-xl p-6 backdrop-blur-sm">
                  <h3 className="text-lg font-bold text-white mb-4 font-display">With Doc Generator</h3>
                  <ul className="space-y-3 text-[#EDF5F2]/60">
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Upload LC once, generate all docs
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Auto-consistency across every document
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Smart COO format selection
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[#B2F273]">✓</span>
                      Bank-tested templates
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="relative py-20 bg-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
                From LC to Documents in Three Steps
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                Upload your LC, select documents, download. That's it.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              {process.map((step, idx) => (
                <div key={idx} className="text-center group">
                  <div className="w-12 h-12 bg-[#B2F273]/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-[#B2F273]/20 group-hover:bg-[#B2F273] transition-colors duration-300">
                    <span className="text-[#B2F273] font-bold font-display group-hover:text-[#00261C] transition-colors">{step.step}</span>
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2 font-display">{step.title}</h3>
                  <p className="text-[#EDF5F2]/60 text-sm">{step.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
                Everything You Need for Document Prep
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto">
                Professional templates, smart auto-fill, and cross-document validation.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature, idx) => (
                <div key={idx} className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl p-6 hover:border-[#B2F273]/30 transition-colors group backdrop-blur-sm">
                  <div className="w-12 h-12 bg-[#B2F273]/10 rounded-lg flex items-center justify-center mb-4 border border-[#B2F273]/20 group-hover:bg-[#B2F273] transition-colors">
                    <feature.icon className="w-6 h-6 text-[#B2F273] group-hover:text-[#00261C] transition-colors" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2 font-display">{feature.title}</h3>
                  <p className="text-[#EDF5F2]/60 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((bullet, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-[#EDF5F2]/50">
                        <CheckCircle className="w-4 h-4 text-[#B2F273] shrink-0" />
                        {bullet}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing */}
        <section className="relative py-20 bg-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4 font-display">
                Simple Pricing
              </h2>
              <p className="text-[#EDF5F2]/60">
                Pay for what you use. No long-term contracts.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {pricing.map((plan, idx) => (
                <div key={idx} className={cn(
                  "bg-[#00382E]/50 border rounded-xl p-6 backdrop-blur-sm",
                  plan.popular ? "border-[#B2F273] shadow-[0_0_20px_rgba(178,242,115,0.1)]" : "border-[#EDF5F2]/10"
                )}>
                  {plan.popular && (
                    <span className="text-xs text-[#B2F273] font-mono uppercase tracking-wider font-medium">MOST POPULAR</span>
                  )}
                  <h3 className="text-lg font-bold text-white mt-2 font-display">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4 font-display">{plan.price}</div>
                  <p className="text-[#EDF5F2]/60 text-sm mb-4">{plan.docs}</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-[#EDF5F2]/50">
                        <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Button className={cn(
                    "w-full font-bold border-none",
                    plan.popular ? "bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C]" : "bg-[#EDF5F2]/10 hover:bg-[#EDF5F2]/20 text-white"
                  )} asChild>
                    <Link to="/waitlist?tool=doc-generator">Join Waitlist</Link>
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white text-center mb-12 font-display">
                Frequently Asked Questions
              </h2>

              <div className="space-y-4">
                {faqs.map((faq, idx) => (
                  <div key={idx} className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl overflow-hidden backdrop-blur-sm">
                    <button
                      className="w-full px-6 py-4 text-left flex items-center justify-between"
                      onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                    >
                      <span className="text-white font-medium font-display">{faq.q}</span>
                      <ChevronDown className={cn(
                        "w-5 h-5 text-[#EDF5F2]/40 transition-transform shrink-0 ml-4",
                        openFaq === idx && "rotate-180"
                      )} />
                    </button>
                    {openFaq === idx && (
                      <div className="px-6 pb-4">
                        <p className="text-[#EDF5F2]/60 text-sm leading-relaxed">{faq.a}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="relative py-20 bg-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-6 font-display">
                Be First to Know When We Launch
              </h2>
              <p className="text-lg text-[#EDF5F2]/60 mb-8">
                Join the waitlist for early access and launch pricing.
              </p>
              <Button size="lg" className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] font-bold border-none" asChild>
                <Link to="/waitlist?tool=doc-generator">
                  Join Waitlist <ArrowRight className="w-5 h-5 ml-2" />
                </Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      <TRDRFooter />
    </div>
  );
};

export default DocGeneratorLanding;

