/**
 * Help & FAQ Page
 */
import { HelpCircle, BookOpen, MessageCircle, ExternalLink } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export default function HSCodeHelp() {
  const faqs = [
    {
      question: "What is an HS code?",
      answer: "The Harmonized System (HS) is an international nomenclature for the classification of products. It uses a 6-digit code to identify goods, with additional digits added by individual countries for more specific classifications (8-10 digits in the US).",
    },
    {
      question: "How accurate is the AI classification?",
      answer: "Our AI classification achieves 90%+ accuracy for common products. For complex or unusual products, we recommend verifying with official sources or a customs broker. The confidence score indicates how certain the AI is about the classification.",
    },
    {
      question: "What are the General Rules of Interpretation (GRI)?",
      answer: "GRI are the rules that govern HS classification. GRI 1 says to classify by the terms of headings and notes. GRI 2-6 provide guidance for more complex situations like incomplete goods, mixtures, and sets.",
    },
    {
      question: "How do FTA preferential rates work?",
      answer: "Free Trade Agreements (FTAs) provide reduced or zero duty rates for products that meet specific rules of origin. To qualify, products must satisfy requirements like Change in Tariff Classification (CTC) or Regional Value Content (RVC).",
    },
    {
      question: "What is Section 301?",
      answer: "Section 301 tariffs are additional duties imposed by the US on certain Chinese products. These are added on top of the normal MFN rate and can significantly increase import costs.",
    },
    {
      question: "How do I verify a classification?",
      answer: "You can request a binding ruling from CBP (CROSS system) for an official classification determination. This ruling is legally binding and provides certainty for your imports.",
    },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <HelpCircle className="h-5 w-5 text-emerald-400" />
            Help & FAQ
          </h1>
          <p className="text-sm text-slate-400">
            Frequently asked questions and resources
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8 max-w-3xl">
        {/* Quick Links */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Card className="bg-slate-800 border-slate-700 hover:bg-slate-700 transition-colors cursor-pointer">
            <CardContent className="p-4 flex items-center gap-3">
              <BookOpen className="h-5 w-5 text-emerald-400" />
              <div>
                <p className="font-medium text-white">Documentation</p>
                <p className="text-xs text-slate-500">Learn how to use</p>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-slate-800 border-slate-700 hover:bg-slate-700 transition-colors cursor-pointer">
            <CardContent className="p-4 flex items-center gap-3">
              <MessageCircle className="h-5 w-5 text-blue-400" />
              <div>
                <p className="font-medium text-white">Contact Support</p>
                <p className="text-xs text-slate-500">Get help</p>
              </div>
            </CardContent>
          </Card>
          <a href="https://hts.usitc.gov/" target="_blank" rel="noopener noreferrer">
            <Card className="bg-slate-800 border-slate-700 hover:bg-slate-700 transition-colors cursor-pointer">
              <CardContent className="p-4 flex items-center gap-3">
                <ExternalLink className="h-5 w-5 text-purple-400" />
                <div>
                  <p className="font-medium text-white">Official HTS</p>
                  <p className="text-xs text-slate-500">USITC website</p>
                </div>
              </CardContent>
            </Card>
          </a>
        </div>

        {/* FAQ */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">Frequently Asked Questions</CardTitle>
          </CardHeader>
          <CardContent>
            <Accordion type="single" collapsible className="space-y-2">
              {faqs.map((faq, i) => (
                <AccordionItem key={i} value={`item-${i}`} className="border-slate-700">
                  <AccordionTrigger className="text-white hover:text-emerald-400">
                    {faq.question}
                  </AccordionTrigger>
                  <AccordionContent className="text-slate-400">
                    {faq.answer}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

