/**
 * HowToFixSection Component
 * 
 * Expandable section showing actionable fix instructions for each issue type.
 * Part of Phase 0: Enhanced Issue Cards
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Mail,
  Clock,
  Phone,
  FileText,
  ExternalLink,
  Wrench,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import type { IssueCard } from "@/types/lcopilot";

interface HowToFixSectionProps {
  issue: IssueCard;
  lcNumber?: string;
  companyName?: string;
  onDraftEmail?: (context: EmailDraftContext) => void;
}

export interface EmailDraftContext {
  issueTitle: string;
  issueType: string;
  recipient: string;
  subject: string;
  context: string;
}

// Fix instruction templates based on issue patterns
interface FixInstruction {
  copyText?: string;
  steps: string[];
  timeEstimate: string;
  contactInfo?: {
    name: string;
    role: string;
    phone?: string;
    email?: string;
  };
  needsEmail?: boolean;
  emailRecipient?: string;
  docGeneratorLink?: string;
  isInternal?: boolean; // Can be fixed without external parties
}

// Get fix instructions based on issue type/rule
function getFixInstructions(issue: IssueCard, lcNumber?: string): FixInstruction | null {
  const rule = issue.rule?.toUpperCase() || "";
  const title = issue.title?.toLowerCase() || "";
  const expected = issue.expected || "";
  
  // BIN/TIN Missing
  if (rule.includes("BIN") || title.includes("bin missing")) {
    const binMatch = expected.match(/BIN[:\s]*['"]?([0-9-]+)['"]?/i);
    const binNumber = binMatch?.[1] || "[BIN from LC]";
    return {
      copyText: `Exporter BIN: ${binNumber}`,
      steps: [
        "Add the BIN number to all listed documents",
        "Place it in the header or footer area",
        "For B/L, email your carrier/freight forwarder",
      ],
      timeEstimate: "1-2 hours (docs you control) | 2-3 days (B/L)",
      needsEmail: true,
      emailRecipient: "carrier",
      isInternal: false,
    };
  }
  
  // TIN Missing
  if (rule.includes("TIN") || title.includes("tin missing")) {
    const tinMatch = expected.match(/TIN[:\s]*['"]?([0-9-]+)['"]?/i);
    const tinNumber = tinMatch?.[1] || "[TIN from LC]";
    return {
      copyText: `Exporter TIN: ${tinNumber}`,
      steps: [
        "Add the TIN number to all listed documents",
        "Place it near the BIN number if both required",
        "For B/L, include in carrier amendment request",
      ],
      timeEstimate: "1-2 hours (docs you control) | 2-3 days (B/L)",
      needsEmail: true,
      emailRecipient: "carrier",
      isInternal: false,
    };
  }
  
  // Missing Inspection Certificate
  if (rule.includes("INSPECTION") || title.includes("inspection certificate")) {
    return {
      steps: [
        "Contact SGS or Intertek to schedule pre-shipment inspection",
        "Prepare goods for inspection at your warehouse",
        "Inspection typically takes 1 day",
        "Certificate issued within 2-3 days after inspection",
      ],
      timeEstimate: "3-5 business days",
      contactInfo: {
        name: "SGS Bangladesh / Intertek",
        role: "Pre-Shipment Inspection",
        phone: "+880-2-9881234",
        email: "bd.certification@sgs.com",
      },
      needsEmail: true,
      emailRecipient: "inspector",
      isInternal: false,
    };
  }
  
  // Missing Beneficiary Certificate
  if (rule.includes("BENEFICIARY") || title.includes("beneficiary certificate")) {
    return {
      steps: [
        "Create a certificate on your company letterhead",
        "Include the required statement from LC clause 46A",
        "Sign and stamp with company seal",
        "Date should be before B/L date",
      ],
      timeEstimate: "30 minutes",
      isInternal: true,
      docGeneratorLink: "/hub/doc-generator?type=beneficiary-certificate",
    };
  }
  
  // B/L Missing Fields (Voyage, Weight, etc.)
  if (rule.includes("BL-") || rule.includes("AI-BL-") || title.includes("b/l missing")) {
    const missingField = title.replace(/b\/l missing required field:\s*/i, "").trim();
    return {
      steps: [
        `Request amended B/L from your shipping line/carrier`,
        `Specify the missing field: ${missingField}`,
        "Include your B/L number and LC number in request",
        "Ask for expedited processing if LC deadline is near",
      ],
      timeEstimate: "1-3 business days",
      needsEmail: true,
      emailRecipient: "carrier",
      isInternal: false,
    };
  }
  
  // Packing List Issues
  if (rule.includes("PL-") || rule.includes("AI-PL-") || title.includes("packing list")) {
    return {
      steps: [
        "Update your packing list with the required information",
        "Ensure carton-wise breakdown matches LC requirements",
        "Include all required fields: size, weight, dimensions",
        "Reprint and re-stamp if already issued",
      ],
      timeEstimate: "1-2 hours",
      isInternal: true,
    };
  }
  
  // Invoice Issues
  if (rule.includes("INV-") || rule.includes("AI-INV-") || title.includes("invoice")) {
    return {
      steps: [
        "Update your commercial invoice with the required information",
        "Ensure amounts match LC exactly (check unit price × quantity)",
        "Verify all mandatory fields are present",
        "Reprint and re-stamp",
      ],
      timeEstimate: "1-2 hours",
      isInternal: true,
    };
  }
  
  // Certificate of Origin Issues
  if (rule.includes("COO-") || title.includes("certificate of origin")) {
    return {
      steps: [
        "Prepare corrected C/O with all required information",
        "Submit to EPB/Chamber of Commerce for certification",
        "Ensure BIN/TIN and other required fields are included",
      ],
      timeEstimate: "1-2 business days",
      contactInfo: {
        name: "Export Promotion Bureau / Chamber",
        role: "C/O Certification",
      },
      isInternal: false,
    };
  }
  
  // Sanctions/Vessel Issues
  if (rule.includes("SANCTIONS") || title.includes("sanctions") || title.includes("vessel")) {
    return {
      steps: [
        "Review the sanctions match details carefully",
        "If false positive: Document your due diligence",
        "If genuine concern: Contact your bank's trade compliance",
        "Consider requesting a different vessel from carrier",
      ],
      timeEstimate: "Varies - consult compliance team",
      isInternal: false,
    };
  }
  
  // Amount/Date Mismatch
  if (title.includes("amount") || title.includes("mismatch") || title.includes("discrepancy")) {
    return {
      steps: [
        "Compare your document against LC terms exactly",
        "Correct the value to match LC (or request LC amendment)",
        "Ensure calculations are accurate (unit price × quantity)",
        "Check for rounding differences",
      ],
      timeEstimate: "1-2 hours (document fix) | 3-5 days (LC amendment)",
      isInternal: true,
    };
  }
  
  // Generic fallback
  return {
    steps: [
      "Review the Expected vs Found values above",
      "Correct your document to match LC requirements",
      "If document cannot be corrected, consider LC amendment",
    ],
    timeEstimate: "Varies by document type",
    isInternal: true,
  };
}

export function HowToFixSection({ 
  issue, 
  lcNumber, 
  companyName,
  onDraftEmail 
}: HowToFixSectionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const { toast } = useToast();
  
  const instructions = getFixInstructions(issue, lcNumber);
  
  if (!instructions) return null;
  
  const handleCopy = async () => {
    if (!instructions.copyText) return;
    
    try {
      await navigator.clipboard.writeText(instructions.copyText);
      setCopied(true);
      toast({
        title: "Copied!",
        description: "Text copied to clipboard",
      });
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast({
        title: "Copy failed",
        description: "Please select and copy manually",
        variant: "destructive",
      });
    }
  };
  
  const handleDraftEmail = () => {
    if (onDraftEmail) {
      const recipientMap: Record<string, string> = {
        carrier: "Shipping Line / Freight Forwarder",
        inspector: "SGS/Intertek Inspection",
        bank: "Issuing Bank",
        chamber: "Chamber of Commerce",
      };
      
      onDraftEmail({
        issueTitle: issue.title || "Document Issue",
        issueType: issue.rule || "general",
        recipient: recipientMap[instructions.emailRecipient || "carrier"] || "External Party",
        subject: `Document Amendment Request - LC ${lcNumber || "[LC Number]"}`,
        context: issue.description || "",
      });
    }
  };
  
  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="mt-3">
      <CollapsibleTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            "w-full justify-between text-sm font-medium",
            "hover:bg-emerald-500/10 hover:text-emerald-600",
            isOpen && "bg-emerald-500/10 text-emerald-600"
          )}
        >
          <span className="flex items-center gap-2">
            <Wrench className="w-4 h-4" />
            How to Fix
            {instructions.isInternal && (
              <Badge variant="outline" className="text-[10px] ml-1 bg-emerald-500/10 text-emerald-600 border-emerald-500/30">
                Self-fixable
              </Badge>
            )}
          </span>
          {isOpen ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </Button>
      </CollapsibleTrigger>
      
      <CollapsibleContent className="mt-2">
        <div className="p-4 bg-gradient-to-br from-emerald-500/5 to-emerald-500/10 rounded-lg border border-emerald-500/20 space-y-4">
          
          {/* Copy-paste text block */}
          {instructions.copyText && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-emerald-700 dark:text-emerald-300 uppercase tracking-wide">
                📋 Add this to your documents:
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 px-3 py-2 bg-white dark:bg-slate-900 rounded border border-emerald-500/30 text-sm font-mono">
                  {instructions.copyText}
                </code>
                <Button
                  size="sm"
                  variant="outline"
                  className="shrink-0 border-emerald-500/30 hover:bg-emerald-500/10"
                  onClick={handleCopy}
                >
                  {copied ? (
                    <Check className="w-4 h-4 text-emerald-600" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>
          )}
          
          {/* Steps */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-emerald-700 dark:text-emerald-300 uppercase tracking-wide">
              📝 Steps:
            </p>
            <ol className="space-y-1.5 text-sm">
              {instructions.steps.map((step, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 text-xs flex items-center justify-center font-medium">
                    {idx + 1}
                  </span>
                  <span className="text-slate-700 dark:text-slate-300">{step}</span>
                </li>
              ))}
            </ol>
          </div>
          
          {/* Time estimate */}
          <div className="flex items-center gap-2 text-sm">
            <Clock className="w-4 h-4 text-emerald-600" />
            <span className="text-slate-600 dark:text-slate-400">
              Estimated time: <span className="font-medium text-slate-800 dark:text-slate-200">{instructions.timeEstimate}</span>
            </span>
          </div>
          
          {/* Contact info */}
          {instructions.contactInfo && (
            <div className="p-3 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">
                Contact
              </p>
              <p className="font-medium text-slate-800 dark:text-slate-200">
                {instructions.contactInfo.name}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {instructions.contactInfo.role}
              </p>
              {instructions.contactInfo.phone && (
                <p className="text-sm text-slate-600 dark:text-slate-400 flex items-center gap-1 mt-1">
                  <Phone className="w-3 h-3" />
                  {instructions.contactInfo.phone}
                </p>
              )}
              {instructions.contactInfo.email && (
                <p className="text-sm text-slate-600 dark:text-slate-400 flex items-center gap-1">
                  <Mail className="w-3 h-3" />
                  {instructions.contactInfo.email}
                </p>
              )}
            </div>
          )}
          
          {/* Action buttons */}
          <div className="flex flex-wrap gap-2 pt-2">
            {instructions.needsEmail && onDraftEmail && (
              <Button
                size="sm"
                variant="outline"
                className="border-blue-500/30 text-blue-600 hover:bg-blue-500/10"
                onClick={handleDraftEmail}
              >
                <Mail className="w-4 h-4 mr-1" />
                Draft Email with AI
              </Button>
            )}
            
            {instructions.docGeneratorLink && (
              <Button
                size="sm"
                variant="outline"
                className="border-purple-500/30 text-purple-600 hover:bg-purple-500/10"
                asChild
              >
                <a href={instructions.docGeneratorLink} target="_blank" rel="noopener noreferrer">
                  <FileText className="w-4 h-4 mr-1" />
                  Generate Document
                  <ExternalLink className="w-3 h-3 ml-1" />
                </a>
              </Button>
            )}
          </div>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

export default HowToFixSection;

