import * as React from "react";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Sparkles,
  FileText,
  Languages,
  Lightbulb,
  Loader2,
  Copy,
  CheckCircle2,
  Send,
  Mail,
  FileEdit,
  MessageSquare,
  TrendingUp,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface AIAssistanceProps {
  embedded?: boolean;
  lcData?: Record<string, any>;
  role?: "exporter" | "importer";
  hasIssues?: boolean;
  isSubmissionReady?: boolean;
  onFieldInferred?: (field: string, value: any) => void;
}

type ComposeAction =
  | "bank-cover-letter"
  | "discrepancy-response"
  | "shipping-advice"
  | "invoice-helper"
  | "coo-helper"
  | "supplier-fix-email"
  | "amendment-request"
  | "compliance-memo";

function buildComposePreview(
  action: ComposeAction,
  role: "exporter" | "importer",
  lcNumber: string,
  userName: string,
  composeInputs: Record<string, string>,
) {
  switch (action) {
    case "bank-cover-letter":
      return `Preview only

Subject: Document presentation under LC ${lcNumber}

Dear Sir/Madam,

We are preparing the document set for LC ${lcNumber}. Please review the enclosed package once the final validation pass is complete.

Additional notes:
${composeInputs.additionalNotes || "No extra notes added yet."}

Regards,
${userName}`;
    case "discrepancy-response":
      return `Preview only

Subject: Response to discrepancy notice for LC ${lcNumber}

Dear Sir/Madam,

We are reviewing the flagged issues under LC ${lcNumber}.

Response draft:
${composeInputs.discrepancyDetails || "We are checking the discrepancy details and preparing corrected documents."}

Regards,
${userName}`;
    case "shipping-advice":
      return `Preview only

Subject: Shipping advice for LC ${lcNumber}

Dear ${composeInputs.recipientName || "Buyer"},

Shipping update:
${composeInputs.shippingDetails || "Insert vessel, ETD, ETA, and dispatch notes here."}

Regards,
${userName}`;
    case "invoice-helper":
      return `Preview only

Commercial invoice wording notes:
${composeInputs.invoiceContext || "Describe the field or clause you want to tighten."}

Checklist:
- match LC terms exactly
- keep quantities and units consistent
- keep party names and addresses aligned`;
    case "coo-helper":
      return `Preview only

Certificate of origin wording notes:
${composeInputs.cooContext || "Describe the COO statement you need to prepare."}

Checklist:
- confirm origin statement wording
- confirm issuer/certifier requirement
- keep destination and consignee references aligned`;
    case "supplier-fix-email":
      return `Preview only

Subject: Supplier correction request for LC ${lcNumber}

Dear ${composeInputs.supplierName || "Supplier"},

We need corrected documents for the following points:
${composeInputs.issueDetails || "List the exact corrections required before resubmission."}

Regards,
${userName}`;
    case "amendment-request":
      return `Preview only

Subject: Amendment request for LC ${lcNumber}

Requested amendment:
${composeInputs.amendmentDetails || "Describe the clause or shipment term that needs amendment."}

Regards,
${userName}`;
    case "compliance-memo":
      return `Preview only

Internal compliance memo for LC ${lcNumber}

Summary:
${composeInputs.memoContext || "Describe the issue, risk, or decision needed."}

Suggested next step:
Confirm whether the team should request corrections, request an amendment, or proceed.`;
    default:
      return role === "exporter" ? "Exporter preview" : "Importer preview";
  }
}

export function AIAssistance({
  embedded = false,
  lcData,
  role: propRole,
  hasIssues = false,
  isSubmissionReady = false,
}: AIAssistanceProps) {
  const { toast } = useToast();
  const { user } = useAuth();
  const role = propRole || (user?.role === "exporter" ? "exporter" : "importer");

  const [activeTab, setActiveTab] = React.useState<"compose" | "explain" | "translate">("compose");
  const [activeAction, setActiveAction] = React.useState<ComposeAction | null>(null);
  const [composeInputs, setComposeInputs] = React.useState<Record<string, string>>({});
  const [generatedOutput, setGeneratedOutput] = React.useState("");
  const [generating, setGenerating] = React.useState(false);
  const [explainContext, setExplainContext] = React.useState("");
  const [explanation, setExplanation] = React.useState("");
  const [explaining, setExplaining] = React.useState(false);
  const [textToTranslate, setTextToTranslate] = React.useState("");
  const [targetLanguage, setTargetLanguage] = React.useState("bn");
  const [translatedText, setTranslatedText] = React.useState("");
  const [translating, setTranslating] = React.useState(false);

  const lcNumber = lcData?.lc_number || "current LC";
  const userName = user?.full_name || user?.username || (role === "exporter" ? "Exporter user" : "Importer user");

  const getActions = (): { recommended: ComposeAction[]; others: ComposeAction[] } => {
    if (role === "exporter") {
      const recommended: ComposeAction[] = hasIssues ? ["discrepancy-response"] : ["bank-cover-letter"];
      const others: ComposeAction[] = hasIssues
        ? ["bank-cover-letter", "shipping-advice", "invoice-helper", "coo-helper"]
        : isSubmissionReady
          ? ["shipping-advice", "invoice-helper", "coo-helper", "discrepancy-response"]
          : ["discrepancy-response", "shipping-advice", "invoice-helper", "coo-helper"];
      return { recommended, others };
    }

    return {
      recommended: (hasIssues ? ["supplier-fix-email", "amendment-request"] : ["compliance-memo"]) as ComposeAction[],
      others: (hasIssues ? ["compliance-memo"] : ["supplier-fix-email", "amendment-request"]) as ComposeAction[],
    };
  };

  const { recommended, others } = getActions();

  const getActionLabel = (action: ComposeAction) => {
    const labels: Record<ComposeAction, string> = {
      "bank-cover-letter": "Bank Cover Letter",
      "discrepancy-response": "Discrepancy Response",
      "shipping-advice": "Shipping Advice Email",
      "invoice-helper": "Invoice Wording Helper",
      "coo-helper": "COO Wording Helper",
      "supplier-fix-email": "Supplier Fix Email",
      "amendment-request": "Amendment Request",
      "compliance-memo": "Compliance Memo",
    };
    return labels[action];
  };

  const getActionIcon = (action: ComposeAction) => {
    const icons: Record<ComposeAction, React.ReactNode> = {
      "bank-cover-letter": <FileText className="w-4 h-4" />,
      "discrepancy-response": <MessageSquare className="w-4 h-4" />,
      "shipping-advice": <Mail className="w-4 h-4" />,
      "invoice-helper": <FileEdit className="w-4 h-4" />,
      "coo-helper": <FileText className="w-4 h-4" />,
      "supplier-fix-email": <Send className="w-4 h-4" />,
      "amendment-request": <FileEdit className="w-4 h-4" />,
      "compliance-memo": <TrendingUp className="w-4 h-4" />,
    };
    return icons[action];
  };

  const handleGenerateCompose = async () => {
    if (!activeAction) return;

    setGenerating(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 800));
      setGeneratedOutput(buildComposePreview(activeAction, role, lcNumber, userName, composeInputs));
      toast({
        title: "Preview Ready",
        description: "A browser-local draft preview has been prepared.",
      });
    } catch {
      toast({
        title: "Preview Failed",
        description: "The local draft preview could not be prepared. Please try again.",
        variant: "destructive",
      });
    } finally {
      setGenerating(false);
    }
  };

  const handleExplain = async () => {
    if (!explainContext.trim()) {
      toast({
        title: "Context Required",
        description: "Please provide context for explanation.",
        variant: "destructive",
      });
      return;
    }

    setExplaining(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 800));
      const nextSteps =
        role === "exporter"
          ? [
              "compare the flagged field against the LC wording",
              "correct the affected document",
              "check the rest of the pack for the same mismatch",
              "re-run validation before submission",
            ]
          : [
              "compare PO, LC, and supplier wording line by line",
              "send exact correction notes to the supplier",
              "check whether the LC needs amendment",
              "re-run validation before using the pack",
            ];

      setExplanation(`Preview only

${explainContext}

Why this may matter:
This browser-local helper is highlighting likely follow-up areas based on the context you entered.

Suggested next checks:
1. ${nextSteps[0]}
2. ${nextSteps[1]}
3. ${nextSteps[2]}
4. ${nextSteps[3]}

Beta note:
This explanation is not generated by the live LCopilot validation backend and is not saved automatically.`);

      toast({
        title: "Explanation Preview Ready",
        description: "A browser-local explanation preview has been prepared.",
      });
    } catch {
      toast({
        title: "Explanation Preview Failed",
        description: "The local explanation preview could not be prepared. Please try again.",
        variant: "destructive",
      });
    } finally {
      setExplaining(false);
    }
  };

  const handleTranslate = async () => {
    if (!textToTranslate.trim()) {
      toast({
        title: "Text Required",
        description: "Please provide text to translate.",
        variant: "destructive",
      });
      return;
    }

    setTranslating(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 600));
      const previewByLanguage: Record<string, string> = {
        bn: "[Bengali preview] " + textToTranslate,
        ar: "[Arabic preview] " + textToTranslate,
        hi: "[Hindi preview] " + textToTranslate,
        ur: "[Urdu preview] " + textToTranslate,
        zh: "[Chinese preview] " + textToTranslate,
      };
      setTranslatedText(previewByLanguage[targetLanguage] || textToTranslate);
      toast({
        title: "Translation Preview Ready",
        description: "A browser-local translation preview has been prepared.",
      });
    } catch {
      toast({
        title: "Translation Preview Failed",
        description: "The local translation preview could not be prepared. Please try again.",
        variant: "destructive",
      });
    } finally {
      setTranslating(false);
    }
  };

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: "Copied",
      description: `${label} copied to clipboard.`,
    });
  };

  const getComposeInputFields = (
    action: ComposeAction,
  ): Array<{ key: string; label: string; placeholder: string }> => {
    switch (action) {
      case "bank-cover-letter":
        return [{ key: "additionalNotes", label: "Additional Notes", placeholder: "Any special instructions or notes..." }];
      case "discrepancy-response":
        return [{ key: "discrepancyDetails", label: "Discrepancy Details", placeholder: "Describe the discrepancies and your response..." }];
      case "shipping-advice":
        return [
          { key: "recipientName", label: "Recipient Name", placeholder: "Buyer or consignee name" },
          { key: "shippingDetails", label: "Shipping Details", placeholder: "Vessel, ETD, ETA, and shipping notes" },
        ];
      case "invoice-helper":
        return [{ key: "invoiceContext", label: "Invoice Context", placeholder: "Describe the wording you want to tighten..." }];
      case "coo-helper":
        return [{ key: "cooContext", label: "COO Context", placeholder: "Describe the certificate wording you need..." }];
      case "supplier-fix-email":
        return [
          { key: "supplierName", label: "Supplier Name", placeholder: "Supplier company name" },
          { key: "issueDetails", label: "Issue Details", placeholder: "Describe the issues that need correction..." },
        ];
      case "amendment-request":
        return [{ key: "amendmentDetails", label: "Amendment Details", placeholder: "Describe the requested amendments..." }];
      case "compliance-memo":
        return [{ key: "memoContext", label: "Memo Context", placeholder: "Describe the compliance situation..." }];
      default:
        return [];
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {!embedded && (
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">AI Assistance</h2>
          <p className="text-muted-foreground">
            Use local beta writing helpers to draft content, explain issues, and preview translations.
          </p>
        </div>
      )}

      <div className="rounded-lg border border-dashed border-border/70 bg-muted/30 p-3 text-sm text-muted-foreground">
        Beta note: this panel currently runs browser-local drafting previews only. It does not call the live LCopilot validation pipeline or save outputs to your account automatically.
      </div>

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as typeof activeTab)} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="compose" className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Compose
          </TabsTrigger>
          <TabsTrigger value="explain" className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4" />
            Explain
          </TabsTrigger>
          <TabsTrigger value="translate" className="flex items-center gap-2">
            <Languages className="w-4 h-4" />
            Translate
          </TabsTrigger>
        </TabsList>

        <TabsContent value="compose" className="mt-6 space-y-6">
          {recommended.length > 0 && (
            <div>
              <div className="mb-4 flex items-center gap-2">
                <Badge className="bg-green-600">Recommended</Badge>
                <span className="text-sm text-muted-foreground">Based on your current LC status</span>
              </div>
              <div className="grid gap-3">
                {recommended.map((action) => (
                  <Card
                    key={action}
                    className="cursor-pointer transition-colors hover:bg-muted/50"
                    onClick={() => setActiveAction(action)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {getActionIcon(action)}
                          <span className="font-medium">{getActionLabel(action)}</span>
                        </div>
                        {activeAction === action && <CheckCircle2 className="h-5 w-5 text-green-600" />}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {others.length > 0 && (
            <div>
              <div className="mb-4 flex items-center gap-2">
                <Badge variant="outline">Other Tools</Badge>
              </div>
              <div className="grid gap-3">
                {others.map((action) => (
                  <Card
                    key={action}
                    className="cursor-pointer transition-colors hover:bg-muted/50"
                    onClick={() => setActiveAction(action)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {getActionIcon(action)}
                          <span className="font-medium">{getActionLabel(action)}</span>
                        </div>
                        {activeAction === action && <CheckCircle2 className="h-5 w-5 text-green-600" />}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {activeAction && (
            <Card>
              <CardHeader>
                <CardTitle>{getActionLabel(activeAction)}</CardTitle>
                <CardDescription>Provide the required information to build a local draft preview.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {getComposeInputFields(activeAction).map((field) => (
                  <div key={field.key}>
                    <Label htmlFor={field.key}>{field.label}</Label>
                    <Textarea
                      id={field.key}
                      placeholder={field.placeholder}
                      value={composeInputs[field.key] || ""}
                      onChange={(e) => setComposeInputs({ ...composeInputs, [field.key]: e.target.value })}
                      rows={3}
                    />
                  </div>
                ))}
                <Button onClick={handleGenerateCompose} disabled={generating} className="w-full">
                  {generating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-4 w-4" />
                      Generate Preview
                    </>
                  )}
                </Button>

                {generatedOutput && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Draft Preview</Label>
                      <Button variant="outline" size="sm" onClick={() => handleCopy(generatedOutput, "Draft preview")}>
                        <Copy className="mr-2 h-4 w-4" />
                        Copy
                      </Button>
                    </div>
                    <div className="rounded-lg border bg-muted/50 p-4">
                      <pre className="whitespace-pre-wrap text-sm">{generatedOutput}</pre>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="explain" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>{role === "exporter" ? "Explain This Discrepancy and How to Fix" : "Explain PO -> LC -> Supplier Mismatch"}</CardTitle>
              <CardDescription>
                {role === "exporter"
                  ? "Create a browser-local explanation preview for discrepancies and next-step guidance."
                  : "Create a browser-local explanation preview for mismatches between Purchase Order, Letter of Credit, and supplier documents."}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="explain-context">Context and Question</Label>
                <Textarea
                  id="explain-context"
                  placeholder={role === "exporter" ? "Describe the discrepancy or ask a question about LC compliance..." : "Describe the mismatch between PO, LC, and supplier documents..."}
                  value={explainContext}
                  onChange={(e) => setExplainContext(e.target.value)}
                  rows={4}
                />
              </div>
              <Button onClick={handleExplain} disabled={explaining || !explainContext.trim()} className="w-full">
                {explaining ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Explaining...
                  </>
                ) : (
                  <>
                    <Lightbulb className="mr-2 h-4 w-4" />
                    Explain Preview
                  </>
                )}
              </Button>

              {explanation && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Explanation Preview</Label>
                    <Button variant="outline" size="sm" onClick={() => handleCopy(explanation, "Explanation preview")}>
                      <Copy className="mr-2 h-4 w-4" />
                      Copy
                    </Button>
                  </div>
                  <div className="rounded-lg border bg-muted/50 p-4">
                    <div className="whitespace-pre-wrap text-sm">{explanation}</div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="translate" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Translate Text</CardTitle>
              <CardDescription>Create browser-local translation previews for LC descriptions, documents, and communications.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="text-to-translate">Text to Translate</Label>
                <Textarea
                  id="text-to-translate"
                  placeholder="Enter text to translate..."
                  value={textToTranslate}
                  onChange={(e) => setTextToTranslate(e.target.value)}
                  rows={4}
                />
              </div>

              <div>
                <Label htmlFor="target-language">Target Language</Label>
                <Select value={targetLanguage} onValueChange={setTargetLanguage}>
                  <SelectTrigger id="target-language">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bn">Bengali</SelectItem>
                    <SelectItem value="ar">Arabic</SelectItem>
                    <SelectItem value="hi">Hindi</SelectItem>
                    <SelectItem value="ur">Urdu</SelectItem>
                    <SelectItem value="zh">Chinese</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button onClick={handleTranslate} disabled={translating || !textToTranslate.trim()} className="w-full">
                {translating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Translating...
                  </>
                ) : (
                  <>
                    <Languages className="mr-2 h-4 w-4" />
                    Translate Preview
                  </>
                )}
              </Button>

              {translatedText && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Translation Preview</Label>
                    <Button variant="outline" size="sm" onClick={() => handleCopy(translatedText, "Translation preview")}>
                      <Copy className="mr-2 h-4 w-4" />
                      Copy
                    </Button>
                  </div>
                  <div className="rounded-lg border bg-muted/50 p-4">
                    <p className="text-sm">{translatedText}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
