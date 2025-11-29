import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle, FileEdit, Clock, Zap, Shield, BookOpen, ChevronDown, AlertTriangle, FileText, MessageSquare, Download, Eye, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TRDRHeader } from "@/components/layout/trdr-header";
import { TRDRFooter } from "@/components/layout/trdr-footer";
import { useState } from "react";
import { cn } from "@/lib/utils";

const features = [
  {
    icon: FileEdit,
    title: "Guided LC Drafting",
    description: "Step-by-step wizard walks you through every field. Smart defaults based on your trade type.",
    bullets: ["Field-by-field guidance", "Context-sensitive help", "Smart auto-suggestions", "Progress tracking"],
  },
  {
    icon: BookOpen,
    title: "Clause Library",
    description: "Pre-approved clauses for common scenarios. Each clause explained in plain English.",
    bullets: ["500+ standard clauses", "Bank-accepted language", "Plain English explanations", "Risk indicators"],
  },
  {
    icon: Shield,
    title: "Real-Time Validation",
    description: "Instant error detection as you type. Catch problems before you submit to the bank.",
    bullets: ["UCP600 compliance check", "Logical consistency", "Date validation", "Amount verification"],
  },
  {
    icon: AlertTriangle,
    title: "Risk Scoring",
    description: "See the risk profile of your LC before submission. Understand which clauses benefit you or the bank.",
    bullets: ["Clause-by-clause risk", "Red/amber/green flags", "Beneficiary vs applicant bias", "Negotiation tips"],
  },
  {
    icon: Eye,
    title: "MT700 Preview",
    description: "See exactly how your LC will look in SWIFT format. No surprises when the bank issues.",
    bullets: ["SWIFT field mapping", "Character count check", "Format validation", "Bank preview mode"],
  },
  {
    icon: Download,
    title: "Export Options",
    description: "Download in the format your bank accepts. PDF, Word, or structured data for API submission.",
    bullets: ["Bank-ready PDF", "Editable Word doc", "MT700 text format", "API/JSON export"],
  },
];

const process = [
  {
    step: "1",
    title: "Start with Basics",
    description: "Enter parties, amounts, goods description, and key dates in our guided wizard",
  },
  {
    step: "2",
    title: "Select Clauses",
    description: "Browse our clause library or let AI suggest clauses based on your trade scenario",
  },
  {
    step: "3",
    title: "Review & Export",
    description: "Preview the MT700, fix any warnings, and export in your bank's preferred format",
  },
];

const stats = [
  { value: "80%", label: "Fewer Rejections" },
  { value: "500+", label: "Clause Library" },
  { value: "30min", label: "Avg Draft Time" },
  { value: "100%", label: "UCP600 Compliant" },
];

const clauseCategories = [
  { name: "Shipment Terms", count: 85, example: "Latest shipment date, partial shipments, transhipment" },
  { name: "Document Requirements", count: 120, example: "B/L requirements, certificate formats, inspection" },
  { name: "Payment Terms", count: 65, example: "Sight, deferred, acceptance, mixed payment" },
  { name: "Special Conditions", count: 95, example: "Insurance, origin, quality certificates" },
  { name: "Amendments", count: 45, example: "Pre-approved amendment language" },
  { name: "Red Clause / Green Clause", count: 25, example: "Advance payment provisions" },
];

const faqs = [
  {
    q: "Can I use this for import or export LCs?",
    a: "Yes! LC Builder works for both import (LC application to your bank) and export (reviewing LCs received from buyers). The guided wizard adapts to your perspective.",
  },
  {
    q: "How does the clause library work?",
    a: "Our library contains 500+ pre-approved clauses covering shipment, documents, payment, and special conditions. Each clause includes plain English explanations, risk indicators, and bank acceptance history.",
  },
  {
    q: "Will this work with my bank's format?",
    a: "We support export formats for major trade banks worldwide. If your bank has specific requirements, our Enterprise plan includes custom template development.",
  },
  {
    q: "How does risk scoring work?",
    a: "Each clause is analyzed for favorability (who benefits: applicant, beneficiary, or neutral) and risk level. The overall LC gets a score so you can see potential issues before submission.",
  },
  {
    q: "Can I save draft LCs for later?",
    a: "Yes, all plans include draft saving. Professional and Enterprise plans add version history, team sharing, and LC templates for repeat transactions.",
  },
];

const pricing = [
  { tier: "Starter", lcs: "5 LCs/mo", price: "$39/mo", description: "For occasional traders", features: ["Guided wizard", "Basic clause library", "PDF export"] },
  { tier: "Professional", lcs: "25 LCs/mo", price: "$99/mo", description: "For active traders", features: ["Full clause library", "Risk scoring", "MT700 preview", "Version history"], popular: true },
  { tier: "Enterprise", lcs: "Unlimited", price: "$299/mo", description: "For banks & corporates", features: ["Everything in Pro", "Custom templates", "Team access", "API integration"] },
];

const LCBuilderLanding = () => {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-slate-950">
      <TRDRHeader />
      
      <main>
        {/* Hero Section */}
        <section className="relative pt-24 pb-20 lg:pt-32 lg:pb-32 overflow-hidden">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px]" />

          <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="max-w-3xl mx-auto text-center mb-12">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 mb-6">
                <Clock className="w-4 h-4 text-amber-400" />
                <span className="text-amber-400 text-sm font-medium">Coming Q1 2025</span>
              </div>
              
              <h1 className="text-4xl lg:text-6xl font-bold text-white mb-6 leading-tight">
                Draft{" "}
                <span className="bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">Error-Free LCs</span>{" "}
                in 30 Minutes
              </h1>
              
              <p className="text-lg text-slate-400 mb-8 leading-relaxed max-w-2xl mx-auto">
                Guided LC application builder with smart clause suggestions, real-time validation, 
                and risk scoring. Reduce application rejections by 80%.
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
                <Button size="lg" className="bg-emerald-500 hover:bg-emerald-600 text-white font-semibold" asChild>
                  <Link to="/waitlist?tool=lc-builder">
                    Join Waitlist <ArrowRight className="w-5 h-5 ml-2" />
                  </Link>
                </Button>
                <Button variant="outline" size="lg" className="border-slate-700 text-slate-300 hover:bg-slate-800" asChild>
                  <Link to="/contact">Request Demo</Link>
                </Button>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-slate-400">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  UCP600 Compliant
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  500+ Clause Library
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  MT700 Preview
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Stats */}
        <section className="py-12 bg-slate-900 border-y border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto">
              {stats.map((stat, idx) => (
                <div key={idx} className="text-center">
                  <div className="text-3xl md:text-4xl font-bold text-white mb-1">{stat.value}</div>
                  <div className="text-sm text-slate-500">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Problem Statement */}
        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-3xl md:text-4xl font-bold text-white text-center mb-12">
                LC Applications Get{" "}
                <span className="text-emerald-400">Rejected</span>. A Lot.
              </h2>
              
              <div className="grid md:grid-cols-2 gap-8">
                <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">Common Problems</h3>
                  <ul className="space-y-3 text-slate-400">
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Missing required fields or clauses
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Conflicting dates or terms
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Non-standard clause language
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-red-400">✗</span>
                      Hidden risks in accepted clauses
                    </li>
                  </ul>
                </div>
                <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-white mb-4">With LC Builder</h3>
                  <ul className="space-y-3 text-slate-400">
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Guided wizard ensures completeness
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Real-time date/term validation
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Pre-approved clause library
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-emerald-400">✓</span>
                      Risk scoring before submission
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Clause Library Preview */}
        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                500+ Bank-Approved Clauses
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Stop writing clauses from scratch. Use our library of pre-approved, bank-accepted language.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-5xl mx-auto">
              {clauseCategories.map((cat, idx) => (
                <div key={idx} className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-white font-medium">{cat.name}</h3>
                    <span className="text-emerald-400 text-sm">{cat.count} clauses</span>
                  </div>
                  <p className="text-slate-500 text-sm">{cat.example}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                From Blank Page to Bank-Ready in 30 Minutes
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Our guided wizard makes LC drafting straightforward.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              {process.map((step, idx) => (
                <div key={idx} className="text-center">
                  <div className="w-12 h-12 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-emerald-500/20">
                    <span className="text-emerald-400 font-bold">{step.step}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{step.title}</h3>
                  <p className="text-slate-400 text-sm">{step.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                Everything for Professional LC Drafting
              </h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Smart suggestions, validation, and export in the format your bank accepts.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {features.map((feature, idx) => (
                <div key={idx} className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 hover:border-emerald-500/30 transition-colors">
                  <div className="w-12 h-12 bg-emerald-500/10 rounded-lg flex items-center justify-center mb-4">
                    <feature.icon className="w-6 h-6 text-emerald-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm mb-4">{feature.description}</p>
                  <ul className="space-y-2">
                    {feature.bullets.map((bullet, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-500">
                        <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />
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
        <section className="py-20 bg-slate-950">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                Simple Pricing
              </h2>
              <p className="text-slate-400">
                Pay per LC. No hidden fees.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {pricing.map((plan, idx) => (
                <div key={idx} className={cn(
                  "bg-slate-900/50 border rounded-xl p-6",
                  plan.popular ? "border-emerald-500/50 bg-emerald-500/5" : "border-slate-800"
                )}>
                  {plan.popular && (
                    <span className="text-xs text-emerald-400 font-medium">MOST POPULAR</span>
                  )}
                  <h3 className="text-lg font-semibold text-white mt-2">{plan.tier}</h3>
                  <div className="text-3xl font-bold text-white my-4">{plan.price}</div>
                  <p className="text-slate-400 text-sm mb-4">{plan.lcs}</p>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm text-slate-400">
                        <CheckCircle className="w-4 h-4 text-emerald-500" />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <Button className={cn(
                    "w-full",
                    plan.popular ? "bg-emerald-500 hover:bg-emerald-600" : "bg-slate-700 hover:bg-slate-600"
                  )} asChild>
                    <Link to="/waitlist?tool=lc-builder">Join Waitlist</Link>
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="py-20 bg-slate-900 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
              <h2 className="text-3xl md:text-4xl font-bold text-white text-center mb-12">
                Frequently Asked Questions
              </h2>

              <div className="space-y-4">
                {faqs.map((faq, idx) => (
                  <div key={idx} className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
                    <button
                      className="w-full px-6 py-4 text-left flex items-center justify-between"
                      onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                    >
                      <span className="text-white font-medium">{faq.q}</span>
                      <ChevronDown className={cn(
                        "w-5 h-5 text-slate-400 transition-transform shrink-0 ml-4",
                        openFaq === idx && "rotate-180"
                      )} />
                    </button>
                    {openFaq === idx && (
                      <div className="px-6 pb-4">
                        <p className="text-slate-400 text-sm leading-relaxed">{faq.a}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 bg-slate-950 border-t border-slate-800">
          <div className="container mx-auto px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto text-center">
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
                Stop Getting LC Applications Rejected
              </h2>
              <p className="text-lg text-slate-400 mb-8">
                Join the waitlist for early access and launch pricing.
              </p>
              <Button size="lg" className="bg-emerald-500 hover:bg-emerald-600 text-white font-semibold" asChild>
                <Link to="/waitlist?tool=lc-builder">
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

export default LCBuilderLanding;

