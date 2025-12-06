import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  HelpCircle,
  ChevronDown,
  Shield,
  Users,
  Ship,
  Package,
  FileCheck,
  Bell,
  ExternalLink,
  MessageCircle,
} from "lucide-react";

const faqs = [
  {
    question: "Which sanctions lists do you screen against?",
    answer: "We screen against 50+ global sanctions lists including OFAC SDN (US Treasury), EU Consolidated Sanctions, UN Security Council, UK OFSI, BIS Entity List, and many more. Our lists are updated daily for OFAC and weekly for EU/UK sources.",
  },
  {
    question: "How does fuzzy matching work?",
    answer: "Our matching algorithm uses multiple techniques including Jaro-Winkler similarity, token set matching, and phonetic algorithms to catch variations in spelling, transliterations, and name order differences. We also check known aliases from the sanctions lists.",
  },
  {
    question: "What does a 'Potential Match' mean?",
    answer: "A potential match indicates that our algorithm found a similarity between your query and an entry on a sanctions list. The match score (e.g., 85%) indicates confidence. Scores above 95% are likely exact matches, while 70-85% may require manual review to confirm if it's the same entity.",
  },
  {
    question: "How long are screening certificates valid?",
    answer: "Certificates are valid for 24 hours from the time of screening. Since sanctions lists are updated frequently (daily for OFAC), we recommend re-screening before finalizing any transaction to ensure compliance with the latest data.",
  },
  {
    question: "What is the 50% Rule?",
    answer: "OFAC's 50% Rule means that any entity owned 50% or more (in aggregate) by one or more SDN-listed persons is treated as if it were on the SDN list, even if not explicitly listed. Our screening flags entities from comprehensively sanctioned countries that may be subject to this rule.",
  },
  {
    question: "Can I screen vessels for dark activity?",
    answer: "Yes, vessel screening includes flag state risk assessment (based on Paris and Tokyo MoU performance lists), ownership chain analysis, and flags of convenience detection. We recommend combining this with AIS tracking for comprehensive vessel due diligence.",
  },
  {
    question: "What's the difference between SDN and SSI lists?",
    answer: "SDN (Specially Designated Nationals) is a full block - no US person can transact with listed entities. SSI (Sectoral Sanctions Identifications) is more limited, restricting specific activities like new debt or equity with Russian entities. Trade in goods may still be permitted with SSI-listed parties.",
  },
  {
    question: "How do I set up continuous monitoring?",
    answer: "Add parties or vessels to your Watchlist, and we'll automatically re-screen them when sanctions lists are updated. You'll receive email and/or in-app alerts if any status changes. This is essential for ongoing business relationships.",
  },
];

const resources = [
  {
    title: "OFAC SDN Search",
    description: "Official US Treasury sanctions search",
    href: "https://sanctionssearch.ofac.treas.gov/",
    icon: Shield,
  },
  {
    title: "EU Sanctions Map",
    description: "European Union sanctions database",
    href: "https://www.sanctionsmap.eu/",
    icon: Shield,
  },
  {
    title: "UN Security Council",
    description: "United Nations sanctions lists",
    href: "https://www.un.org/securitycouncil/sanctions/information",
    icon: Shield,
  },
  {
    title: "UK OFSI",
    description: "UK Office of Financial Sanctions",
    href: "https://www.gov.uk/government/organisations/office-of-financial-sanctions-implementation",
    icon: Shield,
  },
];

export default function SanctionsHelp() {
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <HelpCircle className="w-6 h-6 text-red-400" />
          Help & FAQ
        </h1>
        <p className="text-slate-400 mt-1">
          Learn how to use the Sanctions Screener effectively
        </p>
      </div>

      {/* Quick Guide */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white">Quick Start Guide</CardTitle>
          <CardDescription className="text-slate-400">
            Three ways to use the Sanctions Screener
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
              <Users className="w-8 h-8 text-red-400 mb-3" />
              <h4 className="font-semibold text-white mb-2">Screen Parties</h4>
              <p className="text-sm text-slate-400">
                Enter a company or individual name to check against OFAC, EU, and UN sanctions lists.
              </p>
            </div>
            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
              <Ship className="w-8 h-8 text-orange-400 mb-3" />
              <h4 className="font-semibold text-white mb-2">Screen Vessels</h4>
              <p className="text-sm text-slate-400">
                Enter vessel name or IMO number to check ownership, flag state, and sanctions status.
              </p>
            </div>
            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
              <Package className="w-8 h-8 text-yellow-400 mb-3" />
              <h4 className="font-semibold text-white mb-2">Screen Goods</h4>
              <p className="text-sm text-slate-400">
                Describe your goods to check for dual-use indicators and export control flags.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* FAQ */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white">Frequently Asked Questions</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {faqs.map((faq, idx) => (
            <div key={idx} className="border border-slate-800 rounded-lg overflow-hidden">
              <button
                className="w-full px-4 py-3 text-left flex items-center justify-between hover:bg-slate-800/50 transition-colors"
                onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
              >
                <span className="text-white font-medium">{faq.question}</span>
                <ChevronDown
                  className={cn(
                    "w-5 h-5 text-slate-500 transition-transform",
                    openFaq === idx && "rotate-180"
                  )}
                />
              </button>
              {openFaq === idx && (
                <div className="px-4 pb-4">
                  <p className="text-slate-400 text-sm leading-relaxed">{faq.answer}</p>
                </div>
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      {/* External Resources */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white">Official Resources</CardTitle>
          <CardDescription className="text-slate-400">
            Links to official sanctions authorities
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-3">
            {resources.map((resource) => (
              <a
                key={resource.title}
                href={resource.href}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg border border-slate-700 hover:border-red-500/30 transition-colors"
              >
                <resource.icon className="w-5 h-5 text-red-400" />
                <div className="flex-1">
                  <h4 className="font-medium text-white">{resource.title}</h4>
                  <p className="text-sm text-slate-500">{resource.description}</p>
                </div>
                <ExternalLink className="w-4 h-4 text-slate-500" />
              </a>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Contact */}
      <Card className="bg-gradient-to-r from-red-500/10 to-orange-500/10 border-red-500/20">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <MessageCircle className="w-10 h-10 text-red-400" />
              <div>
                <h3 className="font-semibold text-white">Need Help?</h3>
                <p className="text-slate-400">Our compliance team is here to assist</p>
              </div>
            </div>
            <Button className="bg-red-500 hover:bg-red-600 text-white">
              Contact Support
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Disclaimer */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardContent className="p-4">
          <p className="text-xs text-slate-500 leading-relaxed">
            <strong className="text-slate-400">Disclaimer:</strong> TRDR Sanctions Screener is a screening aid, not legal advice. 
            Results should be verified with your compliance team. We update lists regularly but cannot guarantee real-time accuracy. 
            For official sanctions information, always refer to the relevant government authority (OFAC, EU, UN, UK OFSI).
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

