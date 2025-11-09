/**
 * AI Assistance Component for Bank Dashboard
 * Provides AI-powered features: discrepancy explanations, approval/rejection letters, document summarization, translation
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
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  Copy,
  CheckCircle2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface AIAssistanceProps {
  embedded?: boolean;
  lcData?: Record<string, any>;
  discrepancyData?: Array<{ rule: string; description: string; severity: string }>;
}

export function AIAssistance({ embedded = false, lcData, discrepancyData }: AIAssistanceProps) {
  const { toast } = useToast();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = React.useState<"discrepancy" | "letter" | "summarize" | "translate">("discrepancy");
  
  // Discrepancy explanation state
  const [selectedDiscrepancy, setSelectedDiscrepancy] = React.useState("");
  const [discrepancyExplanation, setDiscrepancyExplanation] = React.useState("");
  const [generatingExplanation, setGeneratingExplanation] = React.useState(false);
  
  // Letter generation state
  const [letterType, setLetterType] = React.useState<"approval" | "rejection">("approval");
  const [clientName, setClientName] = React.useState("");
  const [lcNumber, setLcNumber] = React.useState("");
  const [letterContext, setLetterContext] = React.useState("");
  const [generatedLetter, setGeneratedLetter] = React.useState("");
  const [generatingLetter, setGeneratingLetter] = React.useState(false);
  
  // Summarization state
  const [documentText, setDocumentText] = React.useState("");
  const [summary, setSummary] = React.useState("");
  const [summarizing, setSummarizing] = React.useState(false);
  
  // Translation state
  const [textToTranslate, setTextToTranslate] = React.useState("");
  const [targetLanguage, setTargetLanguage] = React.useState("bn");
  const [translatedText, setTranslatedText] = React.useState("");
  const [translating, setTranslating] = React.useState(false);

  const handleGenerateDiscrepancyExplanation = async () => {
    if (!selectedDiscrepancy.trim()) {
      toast({
        title: "Discrepancy Required",
        description: "Please select or describe a discrepancy.",
        variant: "destructive",
      });
      return;
    }

    setGeneratingExplanation(true);
    try {
      // Mock API call - replace with real endpoint
      await new Promise((resolve) => setTimeout(resolve, 2000));
      
      const mockExplanation = `**Discrepancy Explanation:**

The discrepancy "${selectedDiscrepancy}" indicates a non-compliance with UCP600 Article 14(d), which requires that data in a document, when read in context with the credit, the document itself, and international standard banking practice, need not be identical to, but must not conflict with, data in that document, any other stipulated document, or the credit.

**Impact:**
- This may result in a rejection of documents if not corrected
- The beneficiary should be notified within 5 banking days
- Documents may need to be amended or re-presented

**Recommendation:**
Request clarification from the beneficiary or consider accepting the discrepancy if it's minor and doesn't affect the commercial transaction.`;

      setDiscrepancyExplanation(mockExplanation);
      toast({
        title: "Explanation Generated",
        description: "AI-generated discrepancy explanation is ready.",
      });
    } catch (error) {
      toast({
        title: "Generation Failed",
        description: "Failed to generate explanation. Please try again.",
        variant: "destructive",
      });
    } finally {
      setGeneratingExplanation(false);
    }
  };

  const handleGenerateLetter = async () => {
    if (!clientName.trim() || !lcNumber.trim()) {
      toast({
        title: "Required Fields",
        description: "Please provide client name and LC number.",
        variant: "destructive",
      });
      return;
    }

    setGeneratingLetter(true);
    try {
      // Mock API call - replace with real endpoint
      await new Promise((resolve) => setTimeout(resolve, 2000));
      
      const mockLetter = letterType === "approval"
        ? `Dear ${clientName},

RE: Letter of Credit ${lcNumber}

We are pleased to inform you that the documents presented under the above-mentioned Letter of Credit have been examined and found to be in compliance with the terms and conditions of the credit.

${letterContext ? `\n${letterContext}\n` : ''}

Accordingly, we have honored the documents and credited the proceeds to your account as per the credit terms.

Should you have any queries, please do not hesitate to contact us.

Yours faithfully,
${user?.name || 'Bank Officer'}
LCopilot Validation Team`
        : `Dear ${clientName},

RE: Letter of Credit ${lcNumber}

We regret to inform you that the documents presented under the above-mentioned Letter of Credit have been examined and found to contain the following discrepancies:

${letterContext || 'Please refer to the discrepancy report for details.'}

In accordance with UCP600 Article 16, we are holding the documents at your disposal pending your instructions.

We await your response within the time limit specified in the credit.

Yours faithfully,
${user?.name || 'Bank Officer'}
LCopilot Validation Team`;

      setGeneratedLetter(mockLetter);
      toast({
        title: "Letter Generated",
        description: `${letterType === "approval" ? "Approval" : "Rejection"} letter is ready.`,
      });
    } catch (error) {
      toast({
        title: "Generation Failed",
        description: "Failed to generate letter. Please try again.",
        variant: "destructive",
      });
    } finally {
      setGeneratingLetter(false);
    }
  };

  const handleSummarize = async () => {
    if (!documentText.trim()) {
      toast({
        title: "Document Text Required",
        description: "Please provide document text to summarize.",
        variant: "destructive",
      });
      return;
    }

    setSummarizing(true);
    try {
      // Mock API call - replace with real endpoint
      await new Promise((resolve) => setTimeout(resolve, 2000));
      
      const mockSummary = `**Document Summary:**

**Key Points:**
- Type: Letter of Credit
- Amount: [Extracted from document]
- Beneficiary: [Extracted from document]
- Expiry Date: [Extracted from document]
- Key Terms: [Extracted from document]

**Critical Conditions:**
- Documents required: Commercial Invoice, Bill of Lading, Certificate of Origin
- Latest shipment date: [Extracted]
- Presentation period: [Extracted]

**Risk Assessment:**
- Compliance level: High
- Potential discrepancies: [Listed if any]

**Recommendation:**
[AI-generated recommendation based on document analysis]`;

      setSummary(mockSummary);
      toast({
        title: "Summary Generated",
        description: "Document summary is ready.",
      });
    } catch (error) {
      toast({
        title: "Summarization Failed",
        description: "Failed to generate summary. Please try again.",
        variant: "destructive",
      });
    } finally {
      setSummarizing(false);
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
      
      const languageNames: Record<string, string> = {
        bn: "Bengali",
        ar: "Arabic",
        zh: "Chinese",
        es: "Spanish",
        fr: "French",
      };
      
      const mockTranslation = `[Translated to ${languageNames[targetLanguage] || targetLanguage}]: ${textToTranslate} (mock translation)`;
      
      setTranslatedText(mockTranslation);
      toast({
        title: "Translation Complete",
        description: `Text translated to ${languageNames[targetLanguage] || targetLanguage}.`,
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

  return (
    <div className="flex flex-col gap-6">
      {!embedded && (
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">AI Assistance</h2>
          <p className="text-muted-foreground">
            Leverage AI to generate discrepancy explanations, approval/rejection letters, document summaries, and translations.
          </p>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as typeof activeTab)} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="discrepancy" className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            Discrepancy Explanation
          </TabsTrigger>
          <TabsTrigger value="letter" className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Generate Letter
          </TabsTrigger>
          <TabsTrigger value="summarize" className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Summarize Document
          </TabsTrigger>
          <TabsTrigger value="translate" className="flex items-center gap-2">
            <Languages className="w-4 h-4" />
            Translate
          </TabsTrigger>
        </TabsList>

        <TabsContent value="discrepancy" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Discrepancy Explanation Generator</CardTitle>
              <CardDescription>
                Generate professional explanations for LC discrepancies to help clients understand issues.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="discrepancy">Discrepancy Description</Label>
                {discrepancyData && discrepancyData.length > 0 ? (
                  <Select value={selectedDiscrepancy} onValueChange={setSelectedDiscrepancy}>
                    <SelectTrigger id="discrepancy">
                      <SelectValue placeholder="Select a discrepancy or type custom" />
                    </SelectTrigger>
                    <SelectContent>
                      {discrepancyData.map((disc, idx) => (
                        <SelectItem key={idx} value={disc.description}>
                          {disc.description} ({disc.severity})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Textarea
                    id="discrepancy"
                    placeholder="Describe the discrepancy (e.g., 'Invoice amount differs from LC amount')"
                    value={selectedDiscrepancy}
                    onChange={(e) => setSelectedDiscrepancy(e.target.value)}
                    rows={3}
                  />
                )}
              </div>
              
              <Button
                onClick={handleGenerateDiscrepancyExplanation}
                disabled={!selectedDiscrepancy.trim() || generatingExplanation}
                className="w-full"
              >
                {generatingExplanation ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Generate Explanation
                  </>
                )}
              </Button>

              {discrepancyExplanation && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Generated Explanation</Label>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCopy(discrepancyExplanation, "Explanation")}
                    >
                      <Copy className="w-4 h-4 mr-2" />
                      Copy
                    </Button>
                  </div>
                  <div className="p-4 bg-muted rounded-md whitespace-pre-wrap text-sm">
                    {discrepancyExplanation}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="letter" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Generate Approval/Rejection Letter</CardTitle>
              <CardDescription>
                Create professional letters to communicate LC approval or rejection to clients.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="letter-type">Letter Type</Label>
                  <Select value={letterType} onValueChange={(value) => setLetterType(value as typeof letterType)}>
                    <SelectTrigger id="letter-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="approval">
                        <div className="flex items-center gap-2">
                          <CheckCircle className="w-4 h-4 text-green-500" />
                          Approval Letter
                        </div>
                      </SelectItem>
                      <SelectItem value="rejection">
                        <div className="flex items-center gap-2">
                          <XCircle className="w-4 h-4 text-red-500" />
                          Rejection Letter
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="client-name">Client Name</Label>
                  <Input
                    id="client-name"
                    placeholder="e.g., Bangladesh Exports Ltd"
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="lc-number">LC Number</Label>
                <Input
                  id="lc-number"
                  placeholder="e.g., LC-2024-001234"
                  value={lcNumber}
                  onChange={(e) => setLcNumber(e.target.value)}
                />
              </div>

              <div>
                <Label htmlFor="letter-context">Additional Context (Optional)</Label>
                <Textarea
                  id="letter-context"
                  placeholder="Add any specific details, discrepancies, or instructions..."
                  value={letterContext}
                  onChange={(e) => setLetterContext(e.target.value)}
                  rows={4}
                />
              </div>
              
              <Button
                onClick={handleGenerateLetter}
                disabled={!clientName.trim() || !lcNumber.trim() || generatingLetter}
                className="w-full"
              >
                {generatingLetter ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <FileText className="w-4 h-4 mr-2" />
                    Generate {letterType === "approval" ? "Approval" : "Rejection"} Letter
                  </>
                )}
              </Button>

              {generatedLetter && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Generated Letter</Label>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCopy(generatedLetter, "Letter")}
                    >
                      <Copy className="w-4 h-4 mr-2" />
                      Copy
                    </Button>
                  </div>
                  <div className="p-4 bg-muted rounded-md whitespace-pre-wrap text-sm font-mono">
                    {generatedLetter}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="summarize" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Document Summarization</CardTitle>
              <CardDescription>
                Extract key information and summarize complex LC documents.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="document-text">Document Text</Label>
                <Textarea
                  id="document-text"
                  placeholder="Paste LC document text here..."
                  value={documentText}
                  onChange={(e) => setDocumentText(e.target.value)}
                  rows={8}
                />
              </div>
              
              <Button
                onClick={handleSummarize}
                disabled={!documentText.trim() || summarizing}
                className="w-full"
              >
                {summarizing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Summarizing...
                  </>
                ) : (
                  <>
                    <FileText className="w-4 h-4 mr-2" />
                    Summarize Document
                  </>
                )}
              </Button>

              {summary && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Summary</Label>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCopy(summary, "Summary")}
                    >
                      <Copy className="w-4 h-4 mr-2" />
                      Copy
                    </Button>
                  </div>
                  <div className="p-4 bg-muted rounded-md whitespace-pre-wrap text-sm">
                    {summary}
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
                Translate LC terms, documents, or communications to different languages.
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
                    <SelectItem value="bn">Bengali</SelectItem>
                    <SelectItem value="ar">Arabic</SelectItem>
                    <SelectItem value="zh">Chinese</SelectItem>
                    <SelectItem value="es">Spanish</SelectItem>
                    <SelectItem value="fr">French</SelectItem>
                    <SelectItem value="de">German</SelectItem>
                    <SelectItem value="ja">Japanese</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <Button
                onClick={handleTranslate}
                disabled={!textToTranslate.trim() || translating}
                className="w-full"
              >
                {translating ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Translating...
                  </>
                ) : (
                  <>
                    <Languages className="w-4 h-4 mr-2" />
                    Translate
                  </>
                )}
              </Button>

              {translatedText && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Translated Text</Label>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCopy(translatedText, "Translation")}
                    >
                      <Copy className="w-4 h-4 mr-2" />
                      Copy
                    </Button>
                  </div>
                  <div className="p-4 bg-muted rounded-md whitespace-pre-wrap text-sm">
                    {translatedText}
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

