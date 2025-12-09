/**
 * EmailDraftDialog Component
 * 
 * AI-powered email drafting dialog for issue resolution.
 * Generates contextual emails for carriers, banks, inspectors, etc.
 */

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Copy,
  Check,
  Mail,
  RefreshCw,
  ExternalLink,
  Sparkles,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import type { EmailDraftContext } from "./HowToFixSection";

interface EmailDraftDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: EmailDraftContext | null;
  lcNumber?: string;
  companyName?: string;
}

type EmailTone = "formal" | "professional" | "urgent";

// Email templates based on issue type
function generateEmailDraft(
  context: EmailDraftContext | null,
  lcNumber: string,
  companyName: string,
  tone: EmailTone
): { to: string; subject: string; body: string } {
  if (!context) {
    return { to: "", subject: "", body: "" };
  }
  
  const urgentPrefix = tone === "urgent" ? "URGENT: " : "";
  const toneOpening = {
    formal: "Dear Sir/Madam,",
    professional: "Hello,",
    urgent: "Dear Sir/Madam,\n\nThis is an urgent request requiring immediate attention.",
  };
  
  const toneClosing = {
    formal: "We would be grateful for your prompt attention to this matter.\n\nYours faithfully,",
    professional: "Please let us know if you need any additional information.\n\nBest regards,",
    urgent: "Given the time-sensitive nature of this LC, we kindly request expedited processing.\n\nYours faithfully,",
  };

  // B/L Amendment Request
  if (context.issueType.includes("BL") || context.issueTitle.toLowerCase().includes("b/l")) {
    return {
      to: "[Freight Forwarder / Shipping Line Email]",
      subject: `${urgentPrefix}Request for Amended Bill of Lading - LC ${lcNumber}`,
      body: `${toneOpening[tone]}

We kindly request an amended Bill of Lading for the following shipment under our Letter of Credit.

LC Number: ${lcNumber}
B/L Number: [Your B/L Number]
Shipper: ${companyName || "[Your Company Name]"}

Issue Identified:
${context.issueTitle}

${context.context ? `Details: ${context.context}\n` : ""}
Required Amendment:
Please add/correct the following information as required by our LC terms:
- [Specify required changes based on LC clause 46A]

Our LC presentation deadline is approaching, and we would appreciate your prompt assistance in issuing the amended B/L.

${toneClosing[tone]}
${companyName || "[Your Name]"}
[Your Contact Details]`,
    };
  }

  // Inspection Certificate Request
  if (context.issueType.includes("INSPECTION") || context.issueTitle.toLowerCase().includes("inspection")) {
    return {
      to: "bd.certification@sgs.com",
      subject: `${urgentPrefix}Pre-Shipment Inspection Request - LC ${lcNumber}`,
      body: `${toneOpening[tone]}

We require a Pre-Shipment Inspection Certificate for our export shipment under Letter of Credit.

LC Number: ${lcNumber}
Exporter: ${companyName || "[Your Company Name]"}

Goods Description:
[Brief description of goods - e.g., "Garments - 50,000 pieces"]

Inspection Location:
[Your warehouse/factory address]

Preferred Inspection Date: [Preferred Date]

LC Requirements:
The inspection certificate must confirm quality, quantity, and packing per LC clause 46A specifications.

Please confirm availability and provide a quotation for the inspection service.

${toneClosing[tone]}
${companyName || "[Your Name]"}
[Your Contact Details]`,
    };
  }

  // BIN/TIN related - to carrier for B/L amendment
  if (context.issueType.includes("BIN") || context.issueType.includes("TIN")) {
    return {
      to: "[Freight Forwarder / Shipping Line Email]",
      subject: `${urgentPrefix}B/L Amendment - Add Exporter BIN/TIN - LC ${lcNumber}`,
      body: `${toneOpening[tone]}

We require an amendment to our Bill of Lading to include mandatory exporter identification numbers as required by our LC and Bangladesh export regulations.

LC Number: ${lcNumber}
B/L Number: [Your B/L Number]
Shipper: ${companyName || "[Your Company Name]"}

Required Amendment:
Please add the following to the B/L:
- Exporter BIN: [Your BIN Number]
- Exporter TIN: [Your TIN Number]

This is a mandatory requirement per LC clause 47A for Bangladesh exports.

${toneClosing[tone]}
${companyName || "[Your Name]"}
[Your Contact Details]`,
    };
  }

  // Generic document amendment
  return {
    to: "[Recipient Email]",
    subject: `${urgentPrefix}Document Amendment Request - LC ${lcNumber}`,
    body: `${toneOpening[tone]}

We are writing regarding a document discrepancy identified in our LC presentation.

LC Number: ${lcNumber}
Company: ${companyName || "[Your Company Name]"}

Issue Identified:
${context.issueTitle}

${context.context ? `Details: ${context.context}\n` : ""}
Required Action:
[Please specify the required correction/amendment]

We would appreciate your assistance in resolving this matter at your earliest convenience.

${toneClosing[tone]}
${companyName || "[Your Name]"}
[Your Contact Details]`,
  };
}

export function EmailDraftDialog({
  open,
  onOpenChange,
  context,
  lcNumber = "[LC Number]",
  companyName = "[Your Company]",
}: EmailDraftDialogProps) {
  const [tone, setTone] = useState<EmailTone>("professional");
  const [email, setEmail] = useState({ to: "", subject: "", body: "" });
  const [copied, setCopied] = useState(false);
  const { toast } = useToast();

  // Generate email when context changes
  useEffect(() => {
    if (context) {
      const draft = generateEmailDraft(context, lcNumber, companyName, tone);
      setEmail(draft);
    }
  }, [context, lcNumber, companyName, tone]);

  const handleCopyAll = async () => {
    const fullEmail = `To: ${email.to}\nSubject: ${email.subject}\n\n${email.body}`;
    try {
      await navigator.clipboard.writeText(fullEmail);
      setCopied(true);
      toast({
        title: "Copied!",
        description: "Email copied to clipboard",
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

  const handleOpenInEmail = () => {
    const mailtoUrl = `mailto:${encodeURIComponent(email.to)}?subject=${encodeURIComponent(email.subject)}&body=${encodeURIComponent(email.body)}`;
    window.open(mailtoUrl, "_blank");
  };

  const handleRegenerate = () => {
    if (context) {
      const draft = generateEmailDraft(context, lcNumber, companyName, tone);
      setEmail(draft);
      toast({
        title: "Email regenerated",
        description: "New draft generated with current settings",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-blue-500" />
            Draft Email with AI
          </DialogTitle>
          <DialogDescription>
            Generated email for: {context?.issueTitle || "Document Issue"}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Tone selector */}
          <div className="flex items-center gap-4">
            <Label className="text-sm font-medium">Tone:</Label>
            <Select value={tone} onValueChange={(v) => setTone(v as EmailTone)}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="formal">Formal</SelectItem>
                <SelectItem value="professional">Professional</SelectItem>
                <SelectItem value="urgent">Urgent</SelectItem>
              </SelectContent>
            </Select>
            <Badge variant="outline" className="text-xs">
              {context?.recipient || "External Party"}
            </Badge>
          </div>

          {/* Email fields */}
          <div className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="email-to" className="text-xs text-muted-foreground">
                To:
              </Label>
              <Input
                id="email-to"
                value={email.to}
                onChange={(e) => setEmail({ ...email, to: e.target.value })}
                placeholder="recipient@example.com"
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="email-subject" className="text-xs text-muted-foreground">
                Subject:
              </Label>
              <Input
                id="email-subject"
                value={email.subject}
                onChange={(e) => setEmail({ ...email, subject: e.target.value })}
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="email-body" className="text-xs text-muted-foreground">
                Body:
              </Label>
              <Textarea
                id="email-body"
                value={email.body}
                onChange={(e) => setEmail({ ...email, body: e.target.value })}
                className="min-h-[300px] font-mono text-sm"
              />
            </div>
          </div>

          {/* Tips */}
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
            <p className="text-sm text-amber-700 dark:text-amber-300">
              <strong>💡 Tip:</strong> Replace the bracketed placeholders [like this] with your actual information before sending.
            </p>
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button variant="outline" onClick={handleRegenerate} className="gap-2">
            <RefreshCw className="w-4 h-4" />
            Regenerate
          </Button>
          <Button variant="outline" onClick={handleCopyAll} className="gap-2">
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            Copy All
          </Button>
          <Button onClick={handleOpenInEmail} className="gap-2 bg-blue-600 hover:bg-blue-700">
            <Mail className="w-4 h-4" />
            Open in Email Client
            <ExternalLink className="w-3 h-3" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default EmailDraftDialog;

