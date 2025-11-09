import * as React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle2, RefreshCw, FileText, Lightbulb, ExternalLink, Upload } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { useToast } from "@/hooks/use-toast";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Separator } from "@/components/ui/separator";

export interface DiscrepancyGuidanceProps {
  discrepancy: {
    id: string;
    title: string;
    description: string;
    severity: "critical" | "major" | "minor";
    documentName: string;
    rule: string;
    expected: string;
    actual: string;
    suggestion: string;
    documentType?: string;
    field?: string;
  };
  onRevalidate?: (discrepancyId: string) => Promise<void>;
  onUploadFixed?: (discrepancyId: string, file: File) => Promise<void>;
  validationSessionId?: string;
}

// Enhanced guidance examples based on discrepancy type
const getActionableGuidance = (discrepancy: DiscrepancyGuidanceProps["discrepancy"]) => {
  const guidance: {
    steps: string[];
    examples: { before: string; after: string; explanation: string }[];
    commonMistakes: string[];
    resources?: { title: string; url: string }[];
  } = {
    steps: [],
    examples: [],
    commonMistakes: [],
  };

  // Amount discrepancies
  if (discrepancy.field?.toLowerCase().includes("amount") || discrepancy.title.toLowerCase().includes("amount")) {
    guidance.steps = [
      "Check the LC document for the exact amount specified",
      "Verify the invoice amount matches exactly (including currency)",
      "Ensure no rounding differences exist",
      "Confirm the amount is written in both words and figures correctly",
    ];
    guidance.examples = [
      {
        before: "USD 50,000.00",
        after: "USD 50,000.00",
        explanation: "Amount must match exactly, including decimal places",
      },
      {
        before: "Fifty thousand dollars",
        after: "US Dollars Fifty Thousand Only",
        explanation: "Amount in words must match LC format exactly",
      },
    ];
    guidance.commonMistakes = [
      "Using different currency symbols ($ vs USD)",
      "Rounding differences (50,000 vs 50,000.00)",
      "Incorrect word format",
    ];
  }
  // Date discrepancies
  else if (discrepancy.field?.toLowerCase().includes("date") || discrepancy.title.toLowerCase().includes("date")) {
    guidance.steps = [
      "Verify the date format matches LC requirements (DD-MM-YYYY vs MM/DD/YYYY)",
      "Check that the date falls within the LC validity period",
      "Ensure shipment date is before expiry date",
      "Confirm all dates are consistent across documents",
    ];
    guidance.examples = [
      {
        before: "01/15/2024",
        after: "15-01-2024",
        explanation: "Use DD-MM-YYYY format as specified in LC",
      },
      {
        before: "2024-01-15",
        after: "15-Jan-2024",
        explanation: "Use the exact date format required by the LC",
      },
    ];
    guidance.commonMistakes = [
      "Using wrong date format",
      "Dates outside LC validity period",
      "Inconsistent dates across documents",
    ];
  }
  // Document discrepancies
  else if (discrepancy.title.toLowerCase().includes("document") || discrepancy.title.toLowerCase().includes("missing")) {
    guidance.steps = [
      "Review the LC document checklist to identify required documents",
      "Ensure all mandatory documents are included",
      "Verify document names match LC requirements exactly",
      "Check that documents are properly signed and stamped",
    ];
    guidance.examples = [
      {
        before: "Invoice.pdf",
        after: "Commercial Invoice.pdf",
        explanation: "Document name must match LC requirements exactly",
      },
      {
        before: "B/L",
        after: "Bill of Lading",
        explanation: "Use full document name as specified in LC",
      },
    ];
    guidance.commonMistakes = [
      "Abbreviated document names",
      "Missing required signatures or stamps",
      "Incorrect document versions",
    ];
  }
  // Default guidance
  else {
    guidance.steps = [
      "Review the LC document requirements carefully",
      "Compare your document against the expected format",
      "Make corrections based on the suggested solution",
      "Re-upload the corrected document for validation",
    ];
    guidance.examples = [
      {
        before: discrepancy.actual,
        after: discrepancy.expected,
        explanation: discrepancy.suggestion,
      },
    ];
    guidance.commonMistakes = [
      "Not following exact LC format",
      "Missing required information",
      "Incorrect field values",
    ];
  }

  return guidance;
};

export function DiscrepancyGuidance({
  discrepancy,
  onRevalidate,
  onUploadFixed,
  validationSessionId,
}: DiscrepancyGuidanceProps) {
  const { toast } = useToast();
  const [isRevalidating, setIsRevalidating] = React.useState(false);
  const [fileInputRef, setFileInputRef] = React.useState<HTMLInputElement | null>(null);
  const guidance = getActionableGuidance(discrepancy);

  const handleRevalidate = async () => {
    if (!onRevalidate) {
      toast({
        title: "Re-validation Not Available",
        description: "Re-validation functionality will be available after you upload corrected documents.",
        variant: "default",
      });
      return;
    }

    setIsRevalidating(true);
    try {
      await onRevalidate(discrepancy.id);
      toast({
        title: "Re-validation Started",
        description: "Your documents are being re-validated. Results will appear shortly.",
      });
    } catch (error) {
      toast({
        title: "Re-validation Failed",
        description: "Failed to start re-validation. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsRevalidating(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !onUploadFixed) return;

    try {
      await onUploadFixed(discrepancy.id, file);
      toast({
        title: "File Uploaded",
        description: "Your corrected document has been uploaded. Click 'Re-validate' to check again.",
      });
      // Trigger re-validation automatically after upload
      if (onRevalidate) {
        setTimeout(() => handleRevalidate(), 1000);
      }
    } catch (error) {
      toast({
        title: "Upload Failed",
        description: "Failed to upload file. Please try again.",
        variant: "destructive",
      });
    }
  };

  const severityColors = {
    critical: "destructive",
    major: "secondary",
    minor: "default",
  } as const;

  const severityIcons = {
    critical: AlertTriangle,
    major: AlertTriangle,
    minor: FileText,
  } as const;

  const SeverityIcon = severityIcons[discrepancy.severity];

  return (
    <Card className="border-l-4 border-l-warning">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1">
            <div className={`p-2 rounded-lg mt-1 bg-${severityColors[discrepancy.severity]}/10`}>
              <SeverityIcon className={`w-5 h-5 text-${severityColors[discrepancy.severity]}`} />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <CardTitle className="text-base">{discrepancy.title}</CardTitle>
                <Badge variant={severityColors[discrepancy.severity]} className="text-xs">
                  {discrepancy.severity} priority
                </Badge>
              </div>
              <CardDescription className="text-sm mb-2">
                {discrepancy.documentName} • {discrepancy.rule}
              </CardDescription>
              <p className="text-sm text-muted-foreground">{discrepancy.description}</p>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Expected vs Actual */}
        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Expected</p>
            <div className="bg-success/5 border border-success/20 rounded-lg p-3">
              <p className="text-sm font-mono text-success">{discrepancy.expected}</p>
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Found</p>
            <div className="bg-destructive/5 border border-destructive/20 rounded-lg p-3">
              <p className="text-sm font-mono text-destructive line-through">{discrepancy.actual}</p>
            </div>
          </div>
        </div>

        <Separator />

        {/* Actionable Guidance */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-primary" />
            <h4 className="font-semibold text-sm">How to Fix This Issue</h4>
          </div>

          <Accordion type="single" collapsible className="w-full">
            <AccordionItem value="steps">
              <AccordionTrigger className="text-sm">Step-by-Step Instructions</AccordionTrigger>
              <AccordionContent>
                <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
                  {guidance.steps.map((step, index) => (
                    <li key={index}>{step}</li>
                  ))}
                </ol>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="examples">
              <AccordionTrigger className="text-sm">Examples & Before/After</AccordionTrigger>
              <AccordionContent>
                <div className="space-y-3">
                  {guidance.examples.map((example, index) => (
                    <div key={index} className="border rounded-lg p-3 space-y-2">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">Before (Incorrect)</p>
                          <p className="text-sm font-mono bg-destructive/5 p-2 rounded line-through">
                            {example.before}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-muted-foreground mb-1">After (Correct)</p>
                          <p className="text-sm font-mono bg-success/5 p-2 rounded text-success">
                            {example.after}
                          </p>
                        </div>
                      </div>
                      <p className="text-xs text-muted-foreground italic">{example.explanation}</p>
                    </div>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="mistakes">
              <AccordionTrigger className="text-sm">Common Mistakes to Avoid</AccordionTrigger>
              <AccordionContent>
                <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                  {guidance.commonMistakes.map((mistake, index) => (
                    <li key={index}>{mistake}</li>
                  ))}
                </ul>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>

        <Separator />

        {/* Quick Actions */}
        <div className="flex items-center justify-between pt-2">
          <div className="flex items-center gap-2">
            <input
              ref={setFileInputRef}
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={handleFileUpload}
              className="hidden"
            />
            {onUploadFixed && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => fileInputRef?.click()}
                className="gap-2"
              >
                <Upload className="h-4 w-4" />
                Upload Fixed Document
              </Button>
            )}
          </div>
          <Button
            variant="default"
            size="sm"
            onClick={handleRevalidate}
            disabled={isRevalidating}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isRevalidating ? "animate-spin" : ""}`} />
            {isRevalidating ? "Re-validating..." : "Re-validate After Fix"}
          </Button>
        </div>

        {/* Quick Summary */}
        <div className="bg-primary/5 border border-primary/20 rounded-lg p-3">
          <p className="text-xs font-medium text-primary mb-1">💡 Quick Summary</p>
          <p className="text-sm text-muted-foreground">{discrepancy.suggestion}</p>
        </div>
      </CardContent>
    </Card>
  );
}

