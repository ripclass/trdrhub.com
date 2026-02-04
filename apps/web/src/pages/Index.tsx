// Force rebuild 5
import { Link } from "react-router-dom";
import { 
  ArrowRight, 
  CheckCircle, 
  Shield, 
  Zap, 
  Globe, 
  FileCheck, 
  Upload, 
  BarChart3, 
  Download, 
  Brain, 
  Clock, 
  DollarSign, 
  ChevronDown,
  X,
  AlertTriangle,
  Play,
  Star,
  Building2,
  Users,
  TrendingUp,
  BadgeCheck
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const stats = [
  { value: "45", unit: "sec", label: "Average validation time" },
  { value: "3,500", unit: "+", label: "Compliance rules" },
  { value: "99.2", unit: "%", label: "Discrepancy detection" },
  { value: "$0", unit: "", label: "Per rejection saved" },
];

const beforeAfter = [
  { aspect: "Time to validate", before: "2-4 hours", after: "45 seconds", icon: Clock },
  { aspect: "Discrepancy fees", before: "$75-150 each", after: "$0", icon: DollarSign },
  { aspect: "First-time approval", before: "~70%", after: "99%+", icon: CheckCircle },
  { aspect: "Rules checked", before: "Manual memory", after: "3,500+ automated", icon: Brain },
  { aspect: "Cross-doc matching", before: "Error-prone", after: "AI-perfect", icon: FileCheck },
  { aspect: "Bank-ready package", before: "Hours to compile", after: "1-click download", icon: Download },
];

const features = [
  {
    icon: Brain,
    title: "AI Trained on 10,000+ Rejections",
    description: "Our AI learned from real bank rejections. It knows exactly what document examiners look for - and what makes them say no.",
    highlight: "99.2% accuracy",
  },
  {
    icon: FileCheck,
    title: "3,500+ Rules. Zero Guesswork.",
    description: "UCP600, ISBP745, ISP98, URDG758, plus country-specific regulations from 60+ jurisdictions. More comprehensive than most bank systems.",
    highlight: "Updated monthly",
  },
  {
    icon: Zap,
    title: "45 Seconds. Not 4 Hours.",
    description: "Upload your LC and supporting docs. Get a complete compliance report with specific discrepancies and fix suggestions.",
    highlight: "Bank-ready output",
  },
  {
    icon: Shield,
    title: "Sanctions Screening Included",
    description: "Every validation automatically screens parties against OFAC, EU, UN, and UK sanctions lists. No extra cost.",
    highlight: "Real-time lists",
  },
  {
    icon: Globe,
    title: "Any Document. Any Format.",
    description: "PDF, scanned image, photo from your phone. We extract data from MT700, ISO20022, or any LC format with OCR.",
    highlight: "Multi-language",
  },
  {
    icon: DollarSign,
    title: "Fix Issues Before They Cost You",
    description: "Clear issue cards tell you exactly what's wrong, which rule it violates, and how to fix it. No more guessing.",
    highlight: "Suggested fixes",
  },
];

const pricing = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Try before you buy",
    included: "2 LCs/month",
    perLc: null,
    features: [
      "2 LC validations per month",
      "Basic UCP600 rules",
      "PDF reports",
      "Email support",
    ],
    cta: "Start Free",
    href: "/lcopilot/exporter-dashboard",
    popular: false,
    badge: null,
  },
  {
    name: "Pay-as-you-go",
    price: "$12",
    period: "/LC",
    description: "No commitment required",
    included: "Pay per use",
    perLc: "$12",
    features: [
      "All 3,500+ rules",
      "Sanctions screening included",
      "Full PDF reports",
      "No monthly commitment",
    ],
    cta: "Buy Credits",
    href: "/lcopilot/exporter-dashboard",
    popular: false,
    badge: null,
  },
  {
    name: "Professional",
    price: "$79",
    period: "/month",
    description: "For regular exporters",
    included: "10 LCs included",
    perLc: "$7.90",
    features: [
      "10 LCs included ($7.90/each)",
      "Extra LCs at $8/each",
      "All 3,500+ rules",
      "Priority support",
      "API access",
    ],
    cta: "Start Professional",
    href: "/lcopilot/exporter-dashboard",
    popular: true,
    badge: "Most Popular",
  },
  {
    name: "Business",
    price: "$199",
    period: "/month",
    description: "For trading houses",
    included: "40 LCs included",
    perLc: "$4.98",
    features: [
      "40 LCs included ($4.98/each)",
      "Extra LCs at $5/each",
      "Team accounts (5 users)",
      "Custom rule sets",
      "Dedicated support",
    ],
    cta: "Start Business",
    href: "/lcopilot/exporter-dashboard",
    popular: false,
    badge: "Best Value",
  },
];

const testimonials = [
  {
    quote: "LCopilot caught a beneficiary name mismatch that would have cost us $12,000 in amendment fees. Paid for itself in one validation.",
    author: "Export Manager",
    company: "Textile Manufacturer, Bangladesh",
    metric: "$12K saved",
    rating: 5,
  },
  {
    quote: "Our document rejection rate dropped from 18% to under 2%. The ROI is insane - we process 200+ LCs per month.",
    author: "Trade Finance Head",
    company: "Trading House, Singapore",
    metric: "18% → 2%",
    rating: 5,
  },
  {
    quote: "The cross-document validation is magic. It found date inconsistencies across 6 documents that our team missed twice.",
    author: "Documentation Officer",
    company: "Agricultural Exporter, India",
    metric: "6-doc check",
    rating: 5,
  },
];

const faqs = [
  {
    question: "How accurate is the AI validation?",
    answer: "Our engine achieves 99.2% accuracy on discrepancy detection, validated against 10,000+ real bank decisions. We check against 3,500+ rules from UCP600, ISBP745, and 60+ country regulations. If we miss something a bank catches, your next month is free.",
  },
  {
    question: "Which document types do you support?",
    answer: "All standard trade documents: Letters of Credit (MT700, ISO20022, PDF), Bills of Lading, Commercial Invoices, Packing Lists, Insurance Certificates, Certificates of Origin, and more. We support PDF, scanned images, and even phone photos.",
  },
  {
    question: "How long does validation take?",
    answer: "Average processing time is 45 seconds for a complete document set (up to 6 documents). This includes OCR extraction, cross-document validation, sanctions screening, and report generation.",
  },
  {
    question: "Can I try before I buy?",
    answer: "Yes! Our Free tier gives you 5 validations per month, forever. No credit card required. Upgrade to Pro anytime for unlimited validations and full rule coverage.",
  },
  {
    question: "How is this different from manual checking?",
    answer: "Manual checking relies on human memory and takes 2-4 hours per LC set. LCopilot checks 3,500+ rules in 45 seconds, never forgets a rule, and catches cross-document inconsistencies that humans routinely miss. Plus, you get a bank-ready PDF report.",
  },
  {
    question: "Do you offer refunds?",
    answer: "Yes. If you're not satisfied within 30 days, we'll refund your payment in full. Plus, if we miss a discrepancy that a bank catches, your next month is free - that's our accuracy guarantee.",
  },
];

const Index = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  return (
    <div className="min-h-screen bg-[#00261C]">
      <TRDRHeader />
      
      <main>
        <section className="relative pt-40 md:pt-48 pb-16 lg:pb-24 overflow-hidden bg-[#00261C]">
          {/* Background effects */}
          <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-[#B2F273]/10 rounded-full blur-[120px]" />
          <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-[#B2F273]/5 rounded-full blur-[100px]" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-4xl mx-auto text-center">
              {/* Trust badge */}
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#B2F273]/10 border border-[#B2F273]/20 mb-8">
                <BadgeCheck className="w-4 h-4 text-[#B2F273]" />
                <span className="text-[#B2F273] text-sm font-medium">Saved exporters $1.2M this quarter</span>
              </div>
              
              {/* Main headline */}
              <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-bold text-white mb-6 leading-[1.1] tracking-tight font-display">
                We catch LC discrepancies
                <br />
                <span className="text-[#B2F273] text-glow-sm">before banks do.</span>
              </h1>
              
              {/* Subheadline */}
              <p className="text-xl lg:text-2xl text-[#EDF5F2]/60 mb-8 max-w-2xl mx-auto leading-relaxed">
                45 seconds. 3,500+ rules. 99% accuracy.
                <br className="hidden sm:block" />
                <span className="text-white font-medium">Stop paying $75 discrepancy fees.</span>
              </p>

              {/* CTA buttons */}
              <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
                <Button 
                  size="lg" 
                  className="bg-[#B2F273] text-[#00261C] hover:bg-[#a3e662] text-lg px-8 h-14 font-bold shadow-[0_0_20px_rgba(178,242,115,0.3)] border-none"
                  asChild
                >
                  <Link to="/lcopilot/exporter-dashboard">
                    Validate Your LC Free
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button 
                  variant="outline" 
                  size="lg" 
                  className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 text-lg px-8 h-14 bg-transparent"
                  asChild
                >
                  <Link to="#demo">
                    <Play className="w-5 h-5 mr-2" />
                    Watch Demo (60s)
                  </Link>
                </Button>
              </div>

              {/* Trust indicators */}
              <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs sm:text-sm text-[#EDF5F2]/60">
                <div className="flex items-center gap-1.5">
                  <CheckCircle className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[#B2F273]" />
                  <span>No credit card</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[#B2F273]" />
                  <span>2 free LCs</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <CheckCircle className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[#B2F273]" />
                  <span>45-second results</span>
                </div>
              </div>
            </div>

            {/* Stats bar */}
            <div className="mt-12 sm:mt-16 max-w-4xl mx-auto">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6">
                {stats.map((stat, idx) => (
                  <div key={idx} className="text-center">
                    <div className="text-2xl sm:text-3xl md:text-4xl font-bold text-white font-display">
                      {stat.value}<span className="text-[#B2F273]">{stat.unit}</span>
                    </div>
                    <div className="text-xs sm:text-sm text-[#EDF5F2]/40 mt-1 font-mono uppercase tracking-wider">{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Before/After Comparison */}
        <section className="relative py-20 bg-[#00261C] border-y border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12">
              <p className="text-[#B2F273] font-mono font-semibold mb-4 tracking-wide uppercase text-sm">The Difference</p>
              <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-4 font-display">
                Manual checking is <span className="text-[#EDF5F2]/40 line-through decoration-[#EDF5F2]/40">broken</span>
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto text-lg">
                See how LCopilot transforms your LC validation workflow
              </p>
            </div>

            <div className="max-w-4xl mx-auto">
              {/* Comparison header - hidden on mobile */}
              <div className="hidden md:grid grid-cols-3 gap-4 mb-4 text-sm font-semibold">
                <div className="text-[#EDF5F2]/40 pl-4 font-mono uppercase tracking-wider">Aspect</div>
                <div className="text-center text-[#EDF5F2]/40 font-mono uppercase tracking-wider">Without LCopilot</div>
                <div className="text-center text-[#B2F273] font-mono uppercase tracking-wider">With LCopilot</div>
              </div>

              {/* Comparison rows */}
              <div className="space-y-3">
                {beforeAfter.map((item, idx) => (
                  <div 
                    key={idx} 
                    className="bg-[#00382E]/50 rounded-xl p-4 border border-[#EDF5F2]/10"
                  >
                    {/* Mobile layout */}
                    <div className="md:hidden">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 bg-[#00261C] rounded-lg flex items-center justify-center shrink-0 border border-[#EDF5F2]/10">
                          <item.icon className="w-5 h-5 text-[#EDF5F2]/60" />
                        </div>
                        <span className="text-white font-medium text-sm">{item.aspect}</span>
                      </div>
                      <div className="flex gap-2">
                        <span className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-[#EDF5F2]/5 rounded-lg text-[#EDF5F2]/40 text-xs border border-[#EDF5F2]/10 font-mono">
                          <X className="w-3.5 h-3.5" />
                          {item.before}
                        </span>
                        <span className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-[#B2F273]/10 rounded-lg text-[#B2F273] text-xs border border-[#B2F273]/20 font-mono">
                          <CheckCircle className="w-3.5 h-3.5" />
                          {item.after}
                        </span>
                      </div>
                    </div>
                    
                    {/* Desktop layout */}
                    <div className="hidden md:grid grid-cols-3 gap-4 items-center">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-[#00261C] rounded-lg flex items-center justify-center shrink-0 border border-[#EDF5F2]/10">
                          <item.icon className="w-5 h-5 text-[#EDF5F2]/60" />
                        </div>
                        <span className="text-white font-medium text-sm">{item.aspect}</span>
                      </div>
                      <div className="text-center">
                        <span className="inline-flex items-center gap-2 px-3 py-1.5 bg-[#EDF5F2]/5 rounded-lg text-[#EDF5F2]/40 text-sm border border-[#EDF5F2]/10 font-mono">
                          <X className="w-4 h-4" />
                          {item.before}
                        </span>
                      </div>
                      <div className="text-center">
                        <span className="inline-flex items-center gap-2 px-3 py-1.5 bg-[#B2F273]/10 rounded-lg text-[#B2F273] text-sm border border-[#B2F273]/20 font-mono">
                          <CheckCircle className="w-4 h-4" />
                          {item.after}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* How It Works - Single clean version */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12 sm:mb-16">
              <p className="text-[#B2F273] font-mono font-semibold mb-3 sm:mb-4 tracking-wide uppercase text-xs sm:text-sm">How It Works</p>
              <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-3 sm:mb-4 font-display">
                Three steps. 45 seconds.
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto text-base sm:text-lg px-4">
                Know exactly what banks will flag - before you submit.
              </p>
            </div>

            <div className="max-w-5xl mx-auto">
              <div className="grid md:grid-cols-3 gap-8">
                {[
                  {
                    step: "01",
                    icon: Upload,
                    title: "Upload Documents",
                    description: "Drop your LC and supporting docs (Bill of Lading, Invoice, Packing List, etc). PDF, scan, or photo - any format works.",
                    time: "10 sec",
                  },
                  {
                    step: "02",
                    icon: Brain,
                    title: "AI Validates",
                    description: "3,500+ rules checked. Cross-document matching. Sanctions screening. All in parallel, all automated.",
                    time: "30 sec",
                  },
                  {
                    step: "03",
                    icon: Download,
                    title: "Get Bank-Ready Report",
                    description: "Clear issue cards with exact discrepancies, rule references, and fix suggestions. Download PDF and submit with confidence.",
                    time: "5 sec",
                  },
                ].map((item, idx) => (
                  <div key={idx} className="relative h-full">
                    <div className="group bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-2xl p-8 hover:border-[#B2F273]/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_10px_40px_-10px_rgba(178,242,115,0.1)] relative overflow-hidden h-full">
                      {/* Hover Glow Effect */}
                      <div className="absolute top-0 right-0 w-32 h-32 bg-[#B2F273]/10 rounded-bl-full blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
                      
                      <div className="flex items-center justify-between mb-6">
                        <span className="text-5xl font-bold text-[#EDF5F2]/10 font-display group-hover:text-[#B2F273]/20 transition-colors">{item.step}</span>
                        <div className="w-14 h-14 bg-[#B2F273]/10 rounded-xl flex items-center justify-center border border-[#B2F273]/20 group-hover:bg-[#B2F273] group-hover:text-[#00261C] transition-all duration-300 relative z-10">
                          <item.icon className="w-7 h-7 text-[#B2F273] group-hover:text-[#00261C] transition-colors" />
                        </div>
                      </div>
                      <h3 className="text-xl font-bold text-white mb-3 font-display transition-colors duration-300 group-hover:text-[#B2F273]">{item.title}</h3>
                      <p className="text-[#EDF5F2]/60 text-sm leading-relaxed mb-4">{item.description}</p>
                      <div className="inline-flex items-center gap-2 text-xs text-[#EDF5F2]/40 font-mono">
                        <Clock className="w-3 h-3" />
                        {item.time}
                      </div>

                      {/* Bottom Decorative Line */}
                      <div className="absolute bottom-0 left-0 w-0 h-[3px] bg-[#B2F273] group-hover:w-full transition-all duration-500 ease-in-out" />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* CTA under process */}
            <div className="text-center mt-12">
              <Button 
                size="lg" 
                className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] px-8 h-12 font-bold border-none"
                asChild
              >
                <Link to="/lcopilot/exporter-dashboard">
                  Try It Now - Free
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Link>
              </Button>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="relative py-20 bg-[#00261C] border-y border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12 sm:mb-16">
              <p className="text-[#B2F273] font-mono font-semibold mb-3 sm:mb-4 tracking-wide uppercase text-xs sm:text-sm">Features</p>
              <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-3 sm:mb-4 font-display">
                Built for trade professionals
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto text-base sm:text-lg px-4">
                Everything you need to validate LCs with confidence
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature, idx) => (
                <div 
                  key={idx} 
                  className="group bg-[#00261C] border border-[#EDF5F2]/10 rounded-2xl p-8 hover:border-[#B2F273]/50 transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_10px_40px_-10px_rgba(178,242,115,0.1)] overflow-hidden"
                >
                  {/* Hover Gradient Overlay */}
                  <div className="absolute inset-0 bg-gradient-to-b from-[#B2F273]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                  <div className="flex items-start justify-between mb-6">
                    <div className="w-14 h-14 bg-[#00382E] rounded-xl flex items-center justify-center group-hover:bg-[#B2F273] transition-colors duration-300 relative z-10">
                      <feature.icon className="w-7 h-7 text-[#EDF5F2]/60 group-hover:text-[#00261C] transition-colors duration-300" />
                    </div>
                    <span className="px-2.5 py-1 bg-[#B2F273]/10 rounded-full text-xs font-medium text-[#B2F273] border border-[#B2F273]/20 font-mono">
                      {feature.highlight}
                    </span>
                  </div>
                  <h3 className="text-xl font-bold text-white mb-3 font-display group-hover:text-[#B2F273] transition-colors duration-300">{feature.title}</h3>
                  <p className="text-[#EDF5F2]/60 text-sm leading-relaxed font-light">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-10 sm:mb-16">
              <p className="text-[#B2F273] font-mono font-semibold mb-3 sm:mb-4 tracking-wide uppercase text-xs sm:text-sm">Pricing</p>
              <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-3 sm:mb-4 font-display">
                Pay per LC. Save with volume.
              </h2>
              <p className="text-[#EDF5F2]/60 max-w-2xl mx-auto text-base sm:text-lg px-4">
                Start with 2 free LCs. Scale as you grow.
              </p>
            </div>

            {/* Pricing cards */}
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5 max-w-6xl mx-auto mb-8">
              {pricing.map((plan, idx) => (
                <div 
                  key={idx} 
                  className={cn(
                    "relative bg-[#00382E]/50 border rounded-2xl p-6 flex flex-col",
                    plan.popular 
                      ? "border-[#B2F273] shadow-lg shadow-[#B2F273]/10" 
                      : "border-[#EDF5F2]/10"
                  )}
                >
                  {plan.badge && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <span className={cn(
                        "px-3 py-1 rounded-full text-xs font-semibold font-mono uppercase tracking-wider",
                        "bg-[#B2F273] text-[#00261C]"
                      )}>
                        {plan.badge}
                      </span>
                    </div>
                  )}
                  
                  <div className="text-center mb-5">
                    <h3 className="text-lg font-bold text-white mb-1 font-display">{plan.name}</h3>
                    <p className="text-[#EDF5F2]/40 text-xs mb-3">{plan.description}</p>
                    <div className="flex items-baseline justify-center gap-1">
                      <span className="text-3xl font-bold text-white font-display">{plan.price}</span>
                      <span className="text-[#EDF5F2]/40 text-sm font-mono">{plan.period}</span>
                    </div>
                    {plan.perLc && (
                      <p className="text-[#B2F273] text-sm mt-1 font-medium font-mono">
                        {plan.perLc}/LC effective
                      </p>
                    )}
                  </div>

                  <div className="bg-[#00261C] rounded-lg px-3 py-2 mb-4 text-center border border-[#EDF5F2]/5">
                    <span className="text-[#EDF5F2]/80 text-sm font-medium">{plan.included}</span>
                  </div>

                  <ul className="space-y-2 mb-6 flex-1">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-[#EDF5F2]/60">
                        <CheckCircle className="w-3.5 h-3.5 text-[#B2F273] shrink-0 mt-0.5" />
                        {feature}
                      </li>
                    ))}
                  </ul>

                  <Button 
                    className={cn(
                      "w-full h-10 font-bold text-sm border-none",
                      plan.popular 
                        ? "bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C]" 
                        : "bg-[#EDF5F2]/10 hover:bg-[#EDF5F2]/20 text-white"
                    )}
                    asChild
                  >
                    <Link to={plan.href}>{plan.cta}</Link>
                  </Button>
                </div>
              ))}
            </div>

            {/* Enterprise CTA */}
            <div className="max-w-6xl mx-auto">
              <div className="bg-gradient-to-r from-[#00382E] to-[#00261C] border border-[#EDF5F2]/10 rounded-2xl p-6 md:p-8 flex flex-col md:flex-row items-center justify-between gap-6">
                <div className="text-center md:text-left">
                  <div className="flex items-center gap-2 justify-center md:justify-start mb-2">
                    <Building2 className="w-5 h-5 text-[#B2F273]" />
                    <h3 className="text-xl font-bold text-white font-display">Enterprise</h3>
                  </div>
                  <p className="text-[#EDF5F2]/60 text-sm mb-2">
                    For banks, large trading houses, and high-volume operations (100+ LCs/month)
                  </p>
                  <div className="flex flex-wrap gap-4 justify-center md:justify-start text-xs text-[#EDF5F2]/40 font-mono">
                    <span className="flex items-center gap-1">
                      <CheckCircle className="w-3 h-3 text-[#B2F273]" />
                      Unlimited LCs
                    </span>
                    <span className="flex items-center gap-1">
                      <CheckCircle className="w-3 h-3 text-[#B2F273]" />
                      White-label option
                    </span>
                    <span className="flex items-center gap-1">
                      <CheckCircle className="w-3 h-3 text-[#B2F273]" />
                      Dedicated CSM
                    </span>
                    <span className="flex items-center gap-1">
                      <CheckCircle className="w-3 h-3 text-[#B2F273]" />
                      SLA guarantee
                    </span>
                    <span className="flex items-center gap-1">
                      <CheckCircle className="w-3 h-3 text-[#B2F273]" />
                      On-premise option
                    </span>
                  </div>
                </div>
                <Button 
                  className="bg-[#B2F273] hover:bg-[#a3e662] text-[#00261C] px-8 h-12 font-bold shrink-0 border-none"
                  asChild
                >
                  <Link to="/contact">Contact Sales</Link>
                </Button>
              </div>
            </div>

            {/* Volume calculator hint */}
            <div className="mt-8 text-center">
              <p className="text-[#EDF5F2]/40 text-sm mb-4">
                Processing <strong className="text-white">50+ LCs/month</strong>? Business plan saves you <strong className="text-[#B2F273]">$350+</strong> vs pay-as-you-go.
              </p>
            </div>

            {/* Guarantee */}
            <div className="mt-8 text-center">
              <div className="inline-flex items-center gap-3 px-6 py-3 bg-[#00261C] rounded-xl border border-[#EDF5F2]/10">
                <Shield className="w-5 h-5 text-[#B2F273]" />
                <span className="text-[#EDF5F2]/60 text-sm">
                  <strong className="text-white">Accuracy Guarantee:</strong> If we miss a discrepancy a bank catches, your next month is free.
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Social Proof / Testimonials */}
        <section className="relative py-20 bg-[#00261C] border-y border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-10 sm:mb-12">
              <p className="text-[#B2F273] font-mono font-semibold mb-3 sm:mb-4 tracking-wide uppercase text-xs sm:text-sm">Trusted Worldwide</p>
              <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-3 sm:mb-4 px-4 font-display">
                Results that speak for themselves
              </h2>
            </div>

            {/* Key metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto mb-16">
              {[
                { icon: Users, value: "500+", label: "Active Users" },
                { icon: FileCheck, value: "10,000+", label: "Documents Validated" },
                { icon: TrendingUp, value: "$1.2M", label: "Saved This Quarter" },
                { icon: Star, value: "4.9/5", label: "User Rating" },
              ].map((stat, idx) => (
                <div key={idx} className="text-center">
                  <div className="w-12 h-12 bg-[#B2F273]/10 rounded-xl flex items-center justify-center mx-auto mb-3">
                    <stat.icon className="w-6 h-6 text-[#B2F273]" />
                  </div>
                  <div className="text-2xl md:text-3xl font-bold text-white font-display">{stat.value}</div>
                  <div className="text-sm text-[#EDF5F2]/60 font-mono">{stat.label}</div>
                </div>
              ))}
            </div>

            {/* Testimonials */}
            <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
              {testimonials.map((t, idx) => (
                <div key={idx} className="bg-[#00382E]/30 border border-[#EDF5F2]/10 rounded-2xl p-6">
                  {/* Metric badge */}
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-[#B2F273]/10 rounded-full mb-4 border border-[#B2F273]/20">
                    <TrendingUp className="w-4 h-4 text-[#B2F273]" />
                    <span className="text-[#B2F273] text-sm font-semibold font-mono">{t.metric}</span>
                  </div>
                  
                  {/* Stars */}
                  <div className="flex gap-1 mb-4">
                    {[...Array(t.rating)].map((_, i) => (
                      <Star key={i} className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                    ))}
                  </div>
                  
                  <p className="text-[#EDF5F2]/80 text-sm mb-6 leading-relaxed">"{t.quote}"</p>
                  
                  <div className="flex items-center gap-3 pt-4 border-t border-[#EDF5F2]/10">
                    <div className="w-10 h-10 bg-[#00261C] rounded-full flex items-center justify-center border border-[#EDF5F2]/5">
                      <Building2 className="w-5 h-5 text-[#EDF5F2]/40" />
                    </div>
                    <div>
                      <div className="text-white font-medium text-sm">{t.author}</div>
                      <div className="text-[#EDF5F2]/40 text-xs">{t.company}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="relative py-20 bg-[#00261C] overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto">
              <div className="text-center mb-12">
                <p className="text-[#B2F273] font-mono font-semibold mb-4 tracking-wide uppercase text-sm">FAQ</p>
                <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 font-display">Common Questions</h2>
              </div>
              
              <div className="space-y-3">
                {faqs.map((faq, idx) => (
                  <div 
                    key={idx} 
                    className="bg-[#00382E]/50 border border-[#EDF5F2]/10 rounded-xl overflow-hidden hover:border-[#B2F273]/30 transition-colors"
                  >
                    <button
                      onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                      className="w-full flex items-center justify-between p-5 text-left"
                    >
                      <span className="font-semibold text-white pr-8 font-display">{faq.question}</span>
                      <ChevronDown 
                        className={cn(
                          "w-5 h-5 text-[#EDF5F2]/40 transition-transform shrink-0", 
                          openFaq === idx && "rotate-180"
                        )} 
                      />
                    </button>
                    <div className={cn(
                      "grid transition-all duration-200",
                      openFaq === idx ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                    )}>
                      <div className="overflow-hidden">
                        <p className="px-5 pb-5 text-[#EDF5F2]/60 text-sm leading-relaxed">{faq.answer}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="relative py-20 bg-gradient-to-b from-[#00382E] to-[#00261C] border-t border-[#EDF5F2]/10 overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(178,242,115,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(178,242,115,0.03)_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_70%)] pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-[#B2F273]/30 to-transparent" />
          <div className="absolute top-1/4 right-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-1/4 left-0 w-96 h-96 bg-[#B2F273]/5 rounded-full blur-3xl pointer-events-none" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center">
              {/* Urgency badge */}
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[#B2F273]/20 bg-[#B2F273]/5 backdrop-blur-sm mb-8">
                <Zap className="w-4 h-4 text-[#B2F273]" />
                <span className="text-[#B2F273] font-mono text-xs tracking-wider uppercase">Takes 45 seconds to validate your first LC</span>
              </div>

              <h2 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6 leading-tight font-display">
                Ready to stop paying
                <br />
                <span className="bg-gradient-to-r from-[#B2F273] to-[#a3e662] bg-clip-text text-transparent">discrepancy fees?</span>
              </h2>
              
              <p className="text-xl text-[#EDF5F2]/60 mb-8 max-w-xl mx-auto">
                Join 500+ exporters who validate LCs with confidence. Start free, no credit card required.
              </p>

              {/* Trust checklist */}
              <div className="flex flex-wrap justify-center gap-x-8 gap-y-3 mb-8 text-sm text-[#EDF5F2]/40">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  5 free validations
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  No credit card
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  45-second results
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-[#B2F273]" />
                  Accuracy guarantee
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Button 
                  size="lg" 
                  className="bg-white text-[#00261C] hover:bg-[#EDF5F2] text-lg px-10 h-14 font-bold shadow-lg shadow-white/10 border-none"
                  asChild
                >
                  <Link to="/lcopilot/exporter-dashboard">
                    Validate Your LC Free
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button 
                  variant="outline" 
                  size="lg" 
                  className="border-[#EDF5F2]/20 text-[#EDF5F2] hover:bg-[#EDF5F2]/5 text-lg px-10 h-14 bg-transparent"
                  asChild
                >
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
