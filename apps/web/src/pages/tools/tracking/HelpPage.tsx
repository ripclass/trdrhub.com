/**
 * Help Page
 * 
 * Documentation and support for tracking features.
 */

import { useState } from "react";
import { Link } from "react-router-dom";
import {
  HelpCircle,
  Book,
  MessageSquare,
  Mail,
  ExternalLink,
  ChevronRight,
  Search,
  Container,
  Ship,
  Bell,
  BarChart3,
  AlertTriangle,
  Clock,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";

const FAQ_ITEMS = [
  {
    question: "How do I track a container?",
    answer: "Enter your container number (e.g., MSCU1234567) in the search bar on the Overview page. We support tracking across 100+ carriers including MSC, Maersk, Hapag-Lloyd, OOCL, and more.",
  },
  {
    question: "What container number formats are supported?",
    answer: "We support standard BIC (Bureau International des Containers) format: 4 letters followed by 7 digits (e.g., MSCU1234567). You can also search by Bill of Lading (B/L) number or booking reference.",
  },
  {
    question: "How accurate is the ETA?",
    answer: "ETA accuracy depends on the carrier's data feed. We show a confidence percentage based on historical accuracy. Generally, ETAs become more accurate as the vessel approaches the destination port.",
  },
  {
    question: "How do I set up alerts?",
    answer: "Go to the Alerts page and click 'Create Alert'. Choose the container/vessel reference, alert type (arrival, delay, etc.), and notification channels (email/SMS). Alerts are checked every 15 minutes.",
  },
  {
    question: "Can I track multiple containers at once?",
    answer: "Yes! Use the Active Shipments page to manage your portfolio. You can add containers to your portfolio for continuous monitoring with automatic status updates.",
  },
  {
    question: "How often is tracking data updated?",
    answer: "Tracking data is updated based on carrier feeds, typically every 4-6 hours. You can manually refresh individual shipments or all shipments at once from the Active Shipments page.",
  },
  {
    question: "What does the 'Delayed' status mean?",
    answer: "A shipment is marked as 'Delayed' when its ETA has been pushed back from the original schedule. This could be due to port congestion, weather, or operational reasons. Check the timeline for specific events.",
  },
  {
    question: "How do I export my tracking data?",
    answer: "Go to History page and click 'Export CSV' to download your tracking history. This includes all shipments, their routes, ETAs, and status history.",
  },
];

const GUIDE_ITEMS = [
  {
    title: "Getting Started",
    description: "Learn the basics of container and vessel tracking",
    icon: Book,
    href: "#getting-started",
  },
  {
    title: "Setting Up Alerts",
    description: "Configure notifications for your shipments",
    icon: Bell,
    href: "/tracking/dashboard/alerts",
  },
  {
    title: "Understanding Analytics",
    description: "Make sense of your tracking metrics",
    icon: BarChart3,
    href: "/tracking/dashboard/analytics",
  },
  {
    title: "Troubleshooting",
    description: "Common issues and solutions",
    icon: AlertTriangle,
    href: "#troubleshooting",
  },
];

export default function HelpPage() {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredFaq = FAQ_ITEMS.filter(
    (item) =>
      item.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.answer.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Help & Support</h1>
        <p className="text-muted-foreground">Find answers and get assistance with tracking</p>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="p-6">
          <div className="relative max-w-xl mx-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search help articles..."
              className="pl-10 h-12"
            />
          </div>
        </CardContent>
      </Card>

      {/* Quick Guides */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        {GUIDE_ITEMS.map((guide) => {
          const Icon = guide.icon;
          const isExternal = guide.href.startsWith("#");
          
          return isExternal ? (
            <Card key={guide.title} className="cursor-pointer hover:bg-muted/50 transition-colors">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                    <Icon className="w-5 h-5 text-blue-500" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">{guide.title}</p>
                    <p className="text-xs text-muted-foreground">{guide.description}</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>
          ) : (
            <Link key={guide.title} to={guide.href}>
              <Card className="cursor-pointer hover:bg-muted/50 transition-colors h-full">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                      <Icon className="w-5 h-5 text-blue-500" />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">{guide.title}</p>
                      <p className="text-xs text-muted-foreground">{guide.description}</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                  </div>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>

      {/* FAQ */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <HelpCircle className="w-5 h-5" />
            Frequently Asked Questions
          </CardTitle>
          <CardDescription>
            {searchQuery ? `${filteredFaq.length} results for "${searchQuery}"` : "Common questions about tracking"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {filteredFaq.length === 0 ? (
            <div className="text-center py-8">
              <Search className="w-8 h-8 mx-auto mb-2 text-muted-foreground opacity-50" />
              <p className="text-muted-foreground">No results found</p>
              <Button variant="link" onClick={() => setSearchQuery("")}>
                Clear search
              </Button>
            </div>
          ) : (
            <Accordion type="single" collapsible className="w-full">
              {filteredFaq.map((item, index) => (
                <AccordionItem key={index} value={`item-${index}`}>
                  <AccordionTrigger className="text-left">
                    {item.question}
                  </AccordionTrigger>
                  <AccordionContent className="text-muted-foreground">
                    {item.answer}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          )}
        </CardContent>
      </Card>

      {/* Contact Support */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="w-5 h-5" />
              Email Support
            </CardTitle>
            <CardDescription>Get help from our support team</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Send us an email and we'll get back to you within 24 hours.
            </p>
            <Button variant="outline" asChild>
              <a href="mailto:support@trdrhub.com">
                <Mail className="w-4 h-4 mr-2" />
                support@trdrhub.com
              </a>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Documentation
            </CardTitle>
            <CardDescription>Detailed guides and API documentation</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Explore our comprehensive documentation for advanced features.
            </p>
            <Button variant="outline" asChild>
              <a href="https://docs.trdrhub.com/tracking" target="_blank" rel="noopener noreferrer">
                <ExternalLink className="w-4 h-4 mr-2" />
                View Documentation
              </a>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Tracking Tips */}
      <Card>
        <CardHeader>
          <CardTitle>Pro Tips</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Container className="w-5 h-5 text-blue-500" />
                <span className="font-medium">Container Search</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Use the full container number including the check digit for most accurate results.
              </p>
            </div>
            <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Bell className="w-5 h-5 text-emerald-500" />
                <span className="font-medium">Smart Alerts</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Set up both arrival and delay alerts to stay fully informed about your shipments.
              </p>
            </div>
            <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-5 h-5 text-amber-500" />
                <span className="font-medium">LC Integration</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Link containers to your LCs for automatic risk alerts when ETA threatens LC expiry.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

