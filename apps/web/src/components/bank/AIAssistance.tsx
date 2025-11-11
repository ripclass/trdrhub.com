/**
 * AI Assistance Component for Bank Dashboard
 * Provides AI-powered features: discrepancy explanations, approval/rejection letters, document summarization, translation
 * Now with state-driven UX, quota enforcement, compliance guardrails, and artifact saving
 */
import * as React from "react";
import { useToast } from "@/hooks/use-toast";
import { useBankAuth } from "@/lib/bank/auth";
import { bankAiApi, type AIUsageQuota, type AIResponse } from "@/api/bank";
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
  Save,
  Info,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

interface AIAssistanceProps {
  embedded?: boolean;
  lcData?: Record<string, any>;
  discrepancyData?: Array<{ rule: string; description: string; severity: string }>;
}

export function AIAssistance({ embedded = false, lcData, discrepancyData }: AIAssistanceProps) {
  const { toast } = useToast();
  const { user } = useBankAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = React.useState<"discrepancy" | "letter" | "summarize" | "translate">("discrepancy");
  
  // Discrepancy explanation state
  const [selectedDiscrepancy, setSelectedDiscrepancy] = React.useState("");
  const [discrepancyExplanation, setDiscrepancyExplanation] = React.useState("");
  const [discrepancyRuleBasis, setDiscrepancyRuleBasis] = React.useState<Array<{ rule_id: string; clause: string; description: string }>>([]);
  const [generatingExplanation, setGeneratingExplanation] = React.useState(false);
  
  // Letter generation state
  const [letterType, setLetterType] = React.useState<"approval" | "rejection">("approval");
  const [clientName, setClientName] = React.useState("");
  const [lcNumber, setLcNumber] = React.useState("");
  const [letterContext, setLetterContext] = React.useState("");
  const [generatedLetter, setGeneratedLetter] = React.useState("");
  const [letterRuleBasis, setLetterRuleBasis] = React.useState<Array<{ rule_id: string; clause: string; description: string }>>([]);
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

  // Quota state
  const [quotaData, setQuotaData] = React.useState<Record<string, AIUsageQuota>>({});

  // Auto-select letter type based on discrepancies
  React.useEffect(() => {
    if (discrepancyData && discrepancyData.length > 0) {
      setLetterType("rejection");
      // Prefill discrepancy list in letter context
      if (!letterContext) {
        const discList = discrepancyData.map(d => `- ${d.description} (${d.severity})`).join('\n');
        setLetterContext(`The following discrepancies were identified:\n\n${discList}`);
      }
    } else {
      setLetterType("approval");
    }
  }, [discrepancyData]);

  // Prefill fields from lcData
  React.useEffect(() => {
    if (lcData) {
      if (lcData.lc_number && !lcNumber) {
        setLcNumber(lcData.lc_number);
      }
      if (lcData.client_name && !clientName) {
        setClientName(lcData.client_name);
      }
      if (lcData.beneficiary && !clientName) {
        setClientName(lcData.beneficiary);
      }
    }
  }, [lcData, lcNumber, clientName]);

  // Prefill selected discrepancy
  React.useEffect(() => {
    if (discrepancyData && discrepancyData.length > 0 && !selectedDiscrepancy) {
      setSelectedDiscrepancy(discrepancyData[0].description);
    }
  }, [discrepancyData, selectedDiscrepancy]);

  // Fetch quota for active tab
  const quotaFeatureMap: Record<string, string> = {
    discrepancy: "discrepancy",
    letter: "letter",
    summarize: "summarize",
    translate: "translate",
  };

  const { data: quota } = useQuery({
    queryKey: ['bank-ai-quota', quotaFeatureMap[activeTab]],
    queryFn: () => bankAiApi.getQuota(quotaFeatureMap[activeTab]),
    enabled: !!quotaFeatureMap[activeTab],
    refetchInterval: 60000, // Refetch every minute
  });

  const explainMutation = useMutation({
    mutationFn: bankAiApi.explainDiscrepancy,
    onSuccess: (data) => {
      setDiscrepancyExplanation(data.content);
      setDiscrepancyRuleBasis(data.rule_basis || []);
      if (data.usage_remaining !== undefined) {
        queryClient.invalidateQueries({ queryKey: ['bank-ai-quota'] });
      }
      toast({
        title: "Explanation Generated",
        description: "AI-generated discrepancy explanation is ready.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Generation Failed",
        description: error?.response?.data?.detail || "Failed to generate explanation. Please try again.",
        variant: "destructive",
      });
    },
  });

  const letterMutation = useMutation({
    mutationFn: bankAiApi.generateLetter,
    onSuccess: (data) => {
      setGeneratedLetter(data.content);
      setLetterRuleBasis(data.rule_basis || []);
      if (data.usage_remaining !== undefined) {
        queryClient.invalidateQueries({ queryKey: ['bank-ai-quota'] });
      }
      toast({
        title: "Letter Generated",
        description: `${letterType === "approval" ? "Approval" : "Rejection"} letter is ready.`,
      });
    },
    onError: (error: any) => {
      toast({
        title: "Generation Failed",
        description: error?.response?.data?.detail || "Failed to generate letter. Please try again.",
        variant: "destructive",
      });
    },
  });

  const summarizeMutation = useMutation({
    mutationFn: bankAiApi.summarizeDocument,
    onSuccess: (data) => {
      setSummary(data.content);
      if (data.usage_remaining !== undefined) {
        queryClient.invalidateQueries({ queryKey: ['bank-ai-quota'] });
      }
      toast({
        title: "Summary Generated",
        description: "Document summary is ready.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Summarization Failed",
        description: error?.response?.data?.detail || "Failed to generate summary. Please try again.",
        variant: "destructive",
      });
    },
  });

  const translateMutation = useMutation({
    mutationFn: bankAiApi.translateText,
    onSuccess: (data) => {
      setTranslatedText(data.content);
      if (data.usage_remaining !== undefined) {
        queryClient.invalidateQueries({ queryKey: ['bank-ai-quota'] });
      }
      toast({
        title: "Translation Complete",
        description: `Text translated to ${targetLanguage}.`,
      });
    },
    onError: (error: any) => {
      toast({
        title: "Translation Failed",
        description: error?.response?.data?.detail || "Failed to translate text. Please try again.",
        variant: "destructive",
      });
    },
  });

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
      await explainMutation.mutateAsync({
        discrepancy: selectedDiscrepancy,
        lc_number: lcNumber || lcData?.lc_number,
        validation_session_id: lcData?.validation_session_id,
        language: "en",
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
      await letterMutation.mutateAsync({
        letter_type: letterType,
        client_name: clientName,
        lc_number: lcNumber,
        context: letterContext,
        discrepancy_list: discrepancyData,
        language: "en",
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
      await summarizeMutation.mutateAsync({
        document_text: documentText,
        lc_number: lcNumber || lcData?.lc_number,
        language: "en",
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
      await translateMutation.mutateAsync({
        text: textToTranslate,
        target_language: targetLanguage,
        source_language: "en",
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

  const handleSaveToEvidencePack = async (content: string, contentType: string) => {
    // TODO: Wire to evidence pack API
    toast({
      title: "Save to Evidence Pack",
      description: `Feature coming soon. Content will be saved to evidence pack.`,
    });
  };

  const isQuotaExceeded = quota && quota.remaining <= 0;
  const quotaWarning = quota && quota.remaining < 10;

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

      {/* Quota Display */}
      {quota && (
        <Card className="bg-muted/50">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">
                  AI Usage: {quota.used} / {quota.limit} ({quota.remaining} remaining)
                </span>
              </div>
              {quotaWarning && (
                <Badge variant={isQuotaExceeded ? "destructive" : "outline"}>
                  {isQuotaExceeded ? "Quota Exceeded" : "Low Quota"}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>
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
                disabled={!selectedDiscrepancy.trim() || generatingExplanation || isQuotaExceeded}
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
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopy(discrepancyExplanation, "Explanation")}
                      >
                        <Copy className="w-4 h-4 mr-2" />
                        Copy
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleSaveToEvidencePack(discrepancyExplanation, "discrepancy_explanation")}
                      >
                        <Save className="w-4 h-4 mr-2" />
                        Save
                      </Button>
                    </div>
                  </div>
                  <div className="p-4 bg-muted rounded-md whitespace-pre-wrap text-sm">
                    {discrepancyExplanation}
                  </div>
                  {discrepancyRuleBasis.length > 0 && (
                    <div className="mt-2 p-3 bg-blue-50 dark:bg-blue-950 rounded-md">
                      <Label className="text-xs font-semibold mb-2 block">Rule Basis (Internal IDs):</Label>
                      <ul className="text-xs space-y-1">
                        {discrepancyRuleBasis.map((rule, idx) => (
                          <li key={idx}>
                            <span className="font-mono">{rule.rule_id}</span>: {rule.clause} - {rule.description}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
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
                disabled={!clientName.trim() || !lcNumber.trim() || generatingLetter || isQuotaExceeded}
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
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopy(generatedLetter, "Letter")}
                      >
                        <Copy className="w-4 h-4 mr-2" />
                        Copy
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleSaveToEvidencePack(generatedLetter, "letter")}
                      >
                        <Save className="w-4 h-4 mr-2" />
                        Save
                      </Button>
                    </div>
                  </div>
                  <div className="p-4 bg-muted rounded-md whitespace-pre-wrap text-sm font-mono">
                    {generatedLetter}
                  </div>
                  {letterRuleBasis.length > 0 && (
                    <div className="mt-2 p-3 bg-blue-50 dark:bg-blue-950 rounded-md">
                      <Label className="text-xs font-semibold mb-2 block">Rule Basis (Internal IDs):</Label>
                      <ul className="text-xs space-y-1">
                        {letterRuleBasis.map((rule, idx) => (
                          <li key={idx}>
                            <span className="font-mono">{rule.rule_id}</span>: {rule.clause} - {rule.description}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
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
                disabled={!documentText.trim() || summarizing || isQuotaExceeded}
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
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopy(summary, "Summary")}
                      >
                        <Copy className="w-4 h-4 mr-2" />
                        Copy
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleSaveToEvidencePack(summary, "document_summary")}
                      >
                        <Save className="w-4 h-4 mr-2" />
                        Save
                      </Button>
                    </div>
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
                disabled={!textToTranslate.trim() || translating || isQuotaExceeded}
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
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopy(translatedText, "Translation")}
                      >
                        <Copy className="w-4 h-4 mr-2" />
                        Copy
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleSaveToEvidencePack(translatedText, "translation")}
                      >
                        <Save className="w-4 h-4 mr-2" />
                        Save
                      </Button>
                    </div>
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
