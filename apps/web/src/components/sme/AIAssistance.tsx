/**
 * AI Assistance Component for SME Dashboards (Exporter/Importer)
 * Role- and state-driven AI tools: Exporter = submit/cure; Importer = instruct/amend
 */
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
import { Input } from "@/components/ui/input";
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
  AlertTriangle,
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

export function AIAssistance({
  embedded = false,
  lcData,
  role: propRole,
  hasIssues = false,
  isSubmissionReady = false,
  onFieldInferred,
}: AIAssistanceProps) {
  const { toast } = useToast();
  const { user } = useAuth();
  
  // Detect role from prop or auth context
  const role = propRole || (user?.role === "exporter" ? "exporter" : "importer");
  
  const [activeTab, setActiveTab] = React.useState<"compose" | "explain" | "translate">("compose");
  
  // Compose action state
  const [activeAction, setActiveAction] = React.useState<ComposeAction | null>(null);
  const [composeInputs, setComposeInputs] = React.useState<Record<string, string>>({});
  const [generatedOutput, setGeneratedOutput] = React.useState("");
  const [generating, setGenerating] = React.useState(false);
  
  // Explain state
  const [explainContext, setExplainContext] = React.useState("");
  const [explanation, setExplanation] = React.useState("");
  const [explaining, setExplaining] = React.useState(false);
  
  // Translation state
  const [textToTranslate, setTextToTranslate] = React.useState("");
  const [targetLanguage, setTargetLanguage] = React.useState("bn");
  const [translatedText, setTranslatedText] = React.useState("");
  const [translating, setTranslating] = React.useState(false);

  // Determine recommended and other actions based on role and gating
  const getActions = () => {
    if (role === "exporter") {
      const recommended: ComposeAction[] = [];
      const others: ComposeAction[] = [];
      
      if (hasIssues) {
        recommended.push("discrepancy-response");
        others.push("bank-cover-letter", "shipping-advice", "invoice-helper", "coo-helper");
      } else if (isSubmissionReady) {
        recommended.push("bank-cover-letter");
        others.push("shipping-advice", "invoice-helper", "coo-helper");
      } else {
        recommended.push("bank-cover-letter");
        others.push("discrepancy-response", "shipping-advice", "invoice-helper", "coo-helper");
      }
      
      return { recommended, others };
    } else {
      // Importer
      const recommended: ComposeAction[] = [];
      const others: ComposeAction[] = [];
      
      if (hasIssues) {
        recommended.push("supplier-fix-email", "amendment-request");
        others.push("compliance-memo");
      } else {
        recommended.push("compliance-memo");
        others.push("supplier-fix-email", "amendment-request");
      }
      
      return { recommended, others };
    }
  };

  const { recommended, others } = getActions();

  const getActionLabel = (action: ComposeAction): string => {
    const labels: Record<ComposeAction, string> = {
      "bank-cover-letter": "Generate Bank Submission Cover Letter",
      "discrepancy-response": "Draft Discrepancy Response to Bank",
      "shipping-advice": "Create Shipping/Booking Advice Email",
      "invoice-helper": "Invoice/Packing List Wording Helper",
      "coo-helper": "COO Statement Helper",
      "supplier-fix-email": "Send Supplier Fix Pack Email",
      "amendment-request": "Draft Bank Amendment Request",
      "compliance-memo": "Generate Internal Compliance Memo",
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
      // Mock API call - replace with real endpoint
      await new Promise((resolve) => setTimeout(resolve, 2000));
      
      let output = "";
      const lcNumber = lcData?.lc_number || "LC-XXXX-XXXX";
      const userName = user?.name || (role === "exporter" ? "Exporter" : "Importer");
      
      switch (activeAction) {
        case "bank-cover-letter":
          output = `Dear Sir/Madam,

We hereby present the following documents for negotiation under Letter of Credit ${lcNumber}:

1. Commercial Invoice (3 copies)
2. Bill of Lading (3/3 original)
3. Packing List (2 copies)
4. Certificate of Origin (1 original)
5. Insurance Policy (1 original)

All documents have been prepared in accordance with the terms and conditions of the above-mentioned Letter of Credit.

We request you to honor the documents and credit the proceeds to our account.

Yours faithfully,
${userName}`;
          break;
          
        case "discrepancy-response":
          output = `Dear Sir/Madam,

RE: Letter of Credit ${lcNumber}

Thank you for your notification regarding the discrepancies in the documents presented under the above-mentioned Letter of Credit.

${composeInputs.discrepancyDetails || "We acknowledge the discrepancies and are taking immediate action to rectify them."}

We will provide corrected documents within the time limit specified in the credit.

Yours faithfully,
${userName}`;
          break;
          
        case "shipping-advice":
          output = `Dear ${composeInputs.recipientName || "Buyer"},

RE: Shipping Advice - LC ${lcNumber}

We are pleased to inform you that the goods have been shipped as per the terms of the above Letter of Credit.

${composeInputs.shippingDetails || "Please find shipping details below."}

We look forward to your confirmation.

Yours faithfully,
${userName}`;
          break;
          
        case "invoice-helper":
          output = `Suggested wording for Commercial Invoice/Packing List:

${composeInputs.invoiceContext || "Standard invoice description"}

- Ensure all quantities match the LC terms
- Include all required certifications
- Use consistent terminology throughout`;
          break;
          
        case "coo-helper":
          output = `Certificate of Origin Statement Helper:

${composeInputs.cooContext || "Standard COO statement"}

- Ensure country of origin is clearly stated
- Include all required certifications
- Match LC requirements exactly`;
          break;
          
        case "supplier-fix-email":
          output = `Dear ${composeInputs.supplierName || "Supplier"},

RE: Document Corrections Required - LC ${lcNumber}

We have reviewed the documents submitted under the above Letter of Credit and identified the following issues that require correction:

${composeInputs.issueDetails || "Please refer to the attached fix pack for detailed corrections."}

Please provide corrected documents at your earliest convenience.

Yours faithfully,
${userName}`;
          break;
          
        case "amendment-request":
          output = `Dear Sir/Madam,

RE: Request for Amendment - LC ${lcNumber}

We respectfully request an amendment to the above-mentioned Letter of Credit as follows:

${composeInputs.amendmentDetails || "Please amend the following clauses:"}

We await your confirmation of this amendment.

Yours faithfully,
${userName}`;
          break;
          
        case "compliance-memo":
          output = `Internal Compliance Memo

RE: LC ${lcNumber} - Risk Assessment

${composeInputs.memoContext || "Risk analysis summary"}

Recommendations:
- Review and approve as per company policy
- Monitor for any compliance issues`;
          break;
      }
      
      setGeneratedOutput(output);
      toast({
        title: "Content Generated",
        description: "AI has generated the requested content.",
      });
    } catch (error) {
      toast({
        title: "Generation Failed",
        description: "Failed to generate content. Please try again.",
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
      // Mock API call - replace with real endpoint
      await new Promise((resolve) => setTimeout(resolve, 2000));
      
      const explanationText = role === "exporter"
        ? `**Discrepancy Explanation:**

${explainContext}

**Why this discrepancy exists:**
The discrepancy indicates a non-compliance with UCP600 requirements. The specific document field needs correction to match the LC terms.

**How to fix:**
1. Review the LC terms carefully
2. Correct the identified field in the document
3. Ensure all related documents are consistent
4. Re-submit corrected documents

**Rules basis (in our own words):**
Documents must comply with LC terms without conflict. Any deviation requires correction before submission.`
        : `**PO ↔ LC ↔ Supplier Mismatch Explanation:**

${explainContext}

**Operational Impact:**
- Payment delays may occur if documents don't match
- Supplier may need to correct documents
- LC terms may require amendment

**Recommendations:**
1. Align PO terms with LC requirements
2. Communicate clearly with supplier
3. Consider LC amendment if necessary`;
      
      setExplanation(explanationText);
      toast({
        title: "Explanation Generated",
        description: "AI has generated an explanation based on your context.",
      });
    } catch (error) {
      toast({
        title: "Explanation Failed",
        description: "Failed to generate explanation. Please try again.",
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
      // Mock API call - replace with real endpoint
      await new Promise((resolve) => setTimeout(resolve, 1500));
      
      // Mock translation
      const translations: Record<string, string> = {
        bn: "এটি একটি নমুনা অনুবাদ।",
        ar: "هذه ترجمة نموذجية.",
        hi: "यह एक नमूना अनुवाद है।",
        ur: "یہ ایک نمونہ ترجمہ ہے۔",
        zh: "这是一个示例翻译。",
      };
      
      setTranslatedText(translations[targetLanguage] || textToTranslate);
      
      toast({
        title: "Translation Complete",
        description: "Text has been translated successfully.",
      });
    } catch (error) {
      toast({
        title: "Translation Failed",
        description: "Failed to translate text. Please try again.",
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

  const getComposeInputFields = (action: ComposeAction): Array<{ key: string; label: string; placeholder: string; required?: boolean }> => {
    switch (action) {
      case "bank-cover-letter":
        return [{ key: "additionalNotes", label: "Additional Notes", placeholder: "Any special instructions or notes..." }];
      case "discrepancy-response":
        return [{ key: "discrepancyDetails", label: "Discrepancy Details", placeholder: "Describe the discrepancies and your response..." }];
      case "shipping-advice":
        return [
          { key: "recipientName", label: "Recipient Name", placeholder: "Buyer/Consignee name" },
          { key: "shippingDetails", label: "Shipping Details", placeholder: "Vessel, ETD, ETA, etc." },
        ];
      case "invoice-helper":
        return [{ key: "invoiceContext", label: "Invoice Context", placeholder: "Describe what you need help with..." }];
      case "coo-helper":
        return [{ key: "cooContext", label: "COO Context", placeholder: "Describe your COO requirements..." }];
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
            Use AI to compose documents, explain discrepancies, and translate text.
          </p>
        </div>
      )}

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

        <TabsContent value="compose" className="mt-6">
          <div className="space-y-6">
            {/* Recommended Actions */}
            {recommended.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <Badge variant="default" className="bg-green-600">Recommended</Badge>
                  <span className="text-sm text-muted-foreground">Based on your current LC status</span>
                </div>
                <div className="grid gap-3">
                  {recommended.map((action) => (
                    <Card key={action} className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => setActiveAction(action)}>
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            {getActionIcon(action)}
                            <span className="font-medium">{getActionLabel(action)}</span>
                          </div>
                          {activeAction === action && <CheckCircle2 className="w-5 h-5 text-green-600" />}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* Other Actions */}
            {others.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <Badge variant="outline">Other Tools</Badge>
                </div>
                <div className="grid gap-3">
                  {others.map((action) => (
                    <Card key={action} className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => setActiveAction(action)}>
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            {getActionIcon(action)}
                            <span className="font-medium">{getActionLabel(action)}</span>
                          </div>
                          {activeAction === action && <CheckCircle2 className="w-5 h-5 text-green-600" />}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* Action Form */}
            {activeAction && (
              <Card className="mt-6">
                <CardHeader>
                  <CardTitle>{getActionLabel(activeAction)}</CardTitle>
                  <CardDescription>
                    Provide the required information to generate your content.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {getComposeInputFields(activeAction).map((field) => (
                    <div key={field.key}>
                      <Label htmlFor={field.key}>{field.label}</Label>
                      <Textarea
                        id={field.key}
                        placeholder={field.placeholder}
                        value={composeInputs[field.key] || ""}
                        onChange={(e) =>
                          setComposeInputs({ ...composeInputs, [field.key]: e.target.value })
                        }
                        rows={3}
                      />
                    </div>
                  ))}
                  <Button
                    onClick={handleGenerateCompose}
                    disabled={generating}
                    className="w-full"
                  >
                    {generating ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4 mr-2" />
                        Generate
                      </>
                    )}
                  </Button>
                  
                  {generatedOutput && (
                    <div className="mt-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <Label>Generated Content</Label>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCopy(generatedOutput, "Content")}
                        >
                          <Copy className="h-4 w-4 mr-2" />
                          Copy
                        </Button>
                      </div>
                      <div className="border rounded-lg p-4 bg-muted/50">
                        <pre className="whitespace-pre-wrap text-sm">{generatedOutput}</pre>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="explain" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>
                {role === "exporter"
                  ? "Explain This Discrepancy and How to Fix"
                  : "Explain PO ↔ LC ↔ Supplier Mismatch"}
              </CardTitle>
              <CardDescription>
                {role === "exporter"
                  ? "Get AI-powered explanations for discrepancies and guidance on how to fix them."
                  : "Understand mismatches between Purchase Order, Letter of Credit, and Supplier documents."}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="explain-context">Context & Question</Label>
                <Textarea
                  id="explain-context"
                  placeholder={
                    role === "exporter"
                      ? "Describe the discrepancy or ask a question about LC compliance..."
                      : "Describe the mismatch between PO, LC, and supplier documents..."
                  }
                  value={explainContext}
                  onChange={(e) => setExplainContext(e.target.value)}
                  rows={4}
                />
              </div>
              <Button
                onClick={handleExplain}
                disabled={explaining || !explainContext.trim()}
                className="w-full"
              >
                {explaining ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Explaining...
                  </>
                ) : (
                  <>
                    <Lightbulb className="h-4 w-4 mr-2" />
                    Explain
                  </>
                )}
              </Button>
              
              {explanation && (
                <div className="mt-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Explanation</Label>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCopy(explanation, "Explanation")}
                    >
                      <Copy className="h-4 w-4 mr-2" />
                      Copy
                    </Button>
                  </div>
                  <div className="border rounded-lg p-4 bg-muted/50">
                    <div className="prose prose-sm max-w-none whitespace-pre-wrap text-sm">{explanation}</div>
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
              <CardDescription>
                Translate LC descriptions, documents, and communications to multiple languages.
              </CardDescription>
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
                    <SelectItem value="bn">Bengali (বাংলা)</SelectItem>
                    <SelectItem value="ar">Arabic (العربية)</SelectItem>
                    <SelectItem value="hi">Hindi (हिन्दी)</SelectItem>
                    <SelectItem value="ur">Urdu (اردو)</SelectItem>
                    <SelectItem value="zh">Chinese (中文)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <Button
                onClick={handleTranslate}
                disabled={translating || !textToTranslate.trim()}
                className="w-full"
              >
                {translating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Translating...
                  </>
                ) : (
                  <>
                    <Languages className="h-4 w-4 mr-2" />
                    Translate
                  </>
                )}
              </Button>
              
              {translatedText && (
                <div className="mt-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Translated Text</Label>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCopy(translatedText, "Translation")}
                    >
                      <Copy className="h-4 w-4 mr-2" />
                      Copy
                    </Button>
                  </div>
                  <div className="border rounded-lg p-4 bg-muted/50">
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
