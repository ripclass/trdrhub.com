/**
 * LC Builder Help Page
 */

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  HelpCircle,
  FileText,
  BookOpen,
  MessageCircle,
  ExternalLink,
  PlayCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const faqs = [
  {
    question: "What is an LC (Letter of Credit)?",
    answer: "A Letter of Credit is a payment guarantee issued by a bank on behalf of a buyer, promising to pay the seller upon presentation of compliant documents. It reduces risk for both parties in international trade.",
  },
  {
    question: "What is UCP600?",
    answer: "UCP600 (Uniform Customs and Practice for Documentary Credits) is a set of international rules published by the International Chamber of Commerce (ICC) that govern letters of credit. Most LCs are subject to UCP600.",
  },
  {
    question: "What is the difference between Sight and Usance LC?",
    answer: "A Sight LC requires the issuing bank to pay immediately upon receiving compliant documents. A Usance (or deferred payment) LC allows the buyer a credit period (e.g., 60, 90, 180 days) to pay after documents are accepted.",
  },
  {
    question: "What is a Confirmed LC?",
    answer: "A Confirmed LC has a second bank (the confirming bank, usually in the seller's country) adding its guarantee of payment. This provides additional security, especially when dealing with banks in higher-risk countries.",
  },
  {
    question: "What is MT700?",
    answer: "MT700 is the SWIFT message format used by banks to issue documentary credits. Understanding MT700 fields helps ensure your LC application contains all required information in the correct format.",
  },
  {
    question: "What documents are typically required?",
    answer: "Common documents include: Commercial Invoice, Packing List, Bill of Lading (or other transport document), Certificate of Origin, Insurance Certificate (for CIF/CIP terms), and any inspection certificates required by the buyer.",
  },
  {
    question: "What is a discrepancy?",
    answer: "A discrepancy occurs when documents presented don't comply with LC terms. Common discrepancies include: late shipment, late presentation, inconsistent data between documents, missing documents, and description mismatches.",
  },
  {
    question: "What is the 5% tolerance rule?",
    answer: "Under UCP600 Article 30, a 5% tolerance in quantity is allowed (unless prohibited by the LC or exact quantity specified), provided the total amount doesn't exceed the LC value.",
  },
  {
    question: "Can I use this tool for Standby LCs?",
    answer: "Yes, the LC Builder supports both Documentary Credits and Standby Letters of Credit. Standby LCs typically have simpler document requirements as they serve as a guarantee rather than primary payment method.",
  },
  {
    question: "How do I export to MT700 format?",
    answer: "After completing your LC application, click the 'Export' button and select 'MT700 Text'. This generates a properly formatted SWIFT message that can be sent to your bank.",
  },
];

const guides = [
  {
    title: "Getting Started with LC Builder",
    description: "Learn the basics of creating your first LC application",
    duration: "5 min read",
  },
  {
    title: "Understanding the Clause Library",
    description: "How to search and use pre-approved LC clauses",
    duration: "3 min read",
  },
  {
    title: "Using Templates for Common Routes",
    description: "Speed up LC creation with trade route templates",
    duration: "4 min read",
  },
  {
    title: "MT700 Field Reference",
    description: "Complete guide to SWIFT documentary credit fields",
    duration: "10 min read",
  },
];

export default function LCBuilderHelpPage() {
  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <HelpCircle className="h-5 w-5 text-emerald-400" />
              Help & FAQ
            </h1>
            <p className="text-sm text-slate-400">
              Learn how to use LC Builder effectively
            </p>
          </div>
        </div>
      </div>

      <div className="px-6 py-6 space-y-6 max-w-4xl">
        {/* Quick Links */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="bg-slate-800/50 border-slate-700 hover:border-emerald-500/50 transition-colors cursor-pointer">
            <CardContent className="pt-6 text-center">
              <BookOpen className="h-10 w-10 text-emerald-400 mx-auto mb-3" />
              <h3 className="font-medium text-white">Clause Library</h3>
              <p className="text-sm text-slate-400 mt-1">
                Browse 428+ pre-approved clauses
              </p>
            </CardContent>
          </Card>
          
          <Card className="bg-slate-800/50 border-slate-700 hover:border-emerald-500/50 transition-colors cursor-pointer">
            <CardContent className="pt-6 text-center">
              <FileText className="h-10 w-10 text-emerald-400 mx-auto mb-3" />
              <h3 className="font-medium text-white">MT700 Reference</h3>
              <p className="text-sm text-slate-400 mt-1">
                SWIFT message field guide
              </p>
            </CardContent>
          </Card>
          
          <Card className="bg-slate-800/50 border-slate-700 hover:border-emerald-500/50 transition-colors cursor-pointer">
            <CardContent className="pt-6 text-center">
              <MessageCircle className="h-10 w-10 text-emerald-400 mx-auto mb-3" />
              <h3 className="font-medium text-white">Contact Support</h3>
              <p className="text-sm text-slate-400 mt-1">
                Get help from our team
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Video Tutorials */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <PlayCircle className="h-5 w-5 text-slate-400" />
              Video Tutorials
            </CardTitle>
            <CardDescription>
              Watch step-by-step guides
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              {guides.map((guide, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 cursor-pointer transition-colors"
                >
                  <h4 className="font-medium text-white">{guide.title}</h4>
                  <p className="text-sm text-slate-400 mt-1">{guide.description}</p>
                  <p className="text-xs text-emerald-400 mt-2">{guide.duration}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* FAQs */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">Frequently Asked Questions</CardTitle>
          </CardHeader>
          <CardContent>
            <Accordion type="multiple" className="space-y-2">
              {faqs.map((faq, idx) => (
                <AccordionItem
                  key={idx}
                  value={`faq-${idx}`}
                  className="border border-slate-700 rounded-lg bg-slate-800/30 px-4"
                >
                  <AccordionTrigger className="hover:no-underline">
                    <span className="text-left text-white">{faq.question}</span>
                  </AccordionTrigger>
                  <AccordionContent className="text-slate-300">
                    {faq.answer}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </CardContent>
        </Card>

        {/* External Resources */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">External Resources</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <a
              href="https://iccwbo.org/resources-for-business/documentary-credits-and-guarantees/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 transition-colors"
            >
              <div>
                <p className="font-medium text-white">ICC Documentary Credits</p>
                <p className="text-sm text-slate-400">Official UCP600 resources from ICC</p>
              </div>
              <ExternalLink className="h-4 w-4 text-slate-400" />
            </a>
            
            <a
              href="https://www.swift.com/standards/data-standards/message-types"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 transition-colors"
            >
              <div>
                <p className="font-medium text-white">SWIFT Message Types</p>
                <p className="text-sm text-slate-400">Official SWIFT documentation</p>
              </div>
              <ExternalLink className="h-4 w-4 text-slate-400" />
            </a>
          </CardContent>
        </Card>

        {/* Support */}
        <Card className="bg-emerald-500/10 border-emerald-500/20">
          <CardContent className="pt-6 text-center">
            <h3 className="font-medium text-white text-lg">Need More Help?</h3>
            <p className="text-slate-300 mt-2">
              Our trade finance experts are here to assist you
            </p>
            <Button className="mt-4 bg-emerald-600 hover:bg-emerald-700">
              <MessageCircle className="h-4 w-4 mr-2" />
              Contact Support
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

