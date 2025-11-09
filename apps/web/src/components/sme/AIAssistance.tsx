/**
 * AI Assistance Component for SME Dashboards
 * Provides AI-powered features: cover letter generation, field inference, translation
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
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface AIAssistanceProps {
  embedded?: boolean;
  lcData?: Record<string, any>;
  onFieldInferred?: (field: string, value: any) => void;
}

export function AIAssistance({ embedded = false, lcData, onFieldInferred }: AIAssistanceProps) {
  const { toast } = useToast();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = React.useState<"cover-letter" | "infer" | "translate">("cover-letter");
  
  // Cover letter state
  const [coverLetterPrompt, setCoverLetterPrompt] = React.useState("");
  const [generatedCoverLetter, setGeneratedCoverLetter] = React.useState("");
  const [generatingCoverLetter, setGeneratingCoverLetter] = React.useState(false);
  
  // Field inference state
  const [selectedField, setSelectedField] = React.useState<string>("");
  const [inferenceContext, setInferenceContext] = React.useState("");
  const [inferredValue, setInferredValue] = React.useState<any>(null);
  const [inferring, setInferring] = React.useState(false);
  
  // Translation state
  const [textToTranslate, setTextToTranslate] = React.useState("");
  const [targetLanguage, setTargetLanguage] = React.useState("bn");
  const [translatedText, setTranslatedText] = React.useState("");
  const [translating, setTranslating] = React.useState(false);

  const handleGenerateCoverLetter = async () => {
    if (!coverLetterPrompt.trim()) {
      toast({
        title: "Prompt Required",
        description: "Please provide context for the cover letter.",
        variant: "destructive",
      });
      return;
    }

    setGeneratingCoverLetter(true);
    try {
      // Mock API call - replace with real endpoint
      await new Promise((resolve) => setTimeout(resolve, 2000));
      
      const mockCoverLetter = `Dear Sir/Madam,

We hereby present the following documents for negotiation under Letter of Credit ${lcData?.lc_number || 'LC-XXXX-XXXX'}:

1. Commercial Invoice (3 copies)
2. Bill of Lading (3/3 original)
3. Packing List (2 copies)
4. Certificate of Origin (1 original)
5. Insurance Policy (1 original)

All documents have been prepared in accordance with the terms and conditions of the above-mentioned Letter of Credit.

We request you to honor the documents and credit the proceeds to our account.

Yours faithfully,
${user?.name || 'Exporter'}`;

      setGeneratedCoverLetter(mockCoverLetter);
      toast({
        title: "Cover Letter Generated",
        description: "AI has generated a professional cover letter based on your context.",
      });
    } catch (error) {
      toast({
        title: "Generation Failed",
        description: "Failed to generate cover letter. Please try again.",
        variant: "destructive",
      });
    } finally {
      setGeneratingCoverLetter(false);
    }
  };

  const handleInferField = async () => {
    if (!selectedField || !inferenceContext.trim()) {
      toast({
        title: "Context Required",
        description: "Please select a field and provide context.",
        variant: "destructive",
      });
      return;
    }

    setInferring(true);
    try {
      // Mock API call - replace with real endpoint
      await new Promise((resolve) => setTimeout(resolve, 1500));
      
      // Mock inference based on field type
      let inferred: any = null;
      if (selectedField === "beneficiary") {
        inferred = user?.name || "Your Company Name";
      } else if (selectedField === "amount") {
        inferred = "USD 50,000.00";
      } else if (selectedField === "expiry_date") {
        const futureDate = new Date();
        futureDate.setDate(futureDate.getDate() + 90);
        inferred = futureDate.toISOString().split('T')[0];
      } else if (selectedField === "port_of_loading") {
        inferred = "Chittagong Port, Bangladesh";
      } else {
        inferred = "Inferred value based on context";
      }

      setInferredValue(inferred);
      onFieldInferred?.(selectedField, inferred);
      
      toast({
        title: "Field Inferred",
        description: `AI has inferred a value for ${selectedField}.`,
      });
    } catch (error) {
      toast({
        title: "Inference Failed",
        description: "Failed to infer field value. Please try again.",
        variant: "destructive",
      });
    } finally {
      setInferring(false);
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

  return (
    <div className="flex flex-col gap-6">
      {!embedded && (
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">AI Assistance</h2>
          <p className="text-muted-foreground">
            Use AI to generate cover letters, infer field values, and translate descriptions.
          </p>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as typeof activeTab)} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="cover-letter" className="flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Cover Letter
          </TabsTrigger>
          <TabsTrigger value="infer" className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4" />
            Infer Fields
          </TabsTrigger>
          <TabsTrigger value="translate" className="flex items-center gap-2">
            <Languages className="w-4 h-4" />
            Translate
          </TabsTrigger>
        </TabsList>

        <TabsContent value="cover-letter" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Generate Cover Letter</CardTitle>
              <CardDescription>
                AI will generate a professional cover letter based on your LC details and context.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="cover-letter-prompt">Context & Instructions</Label>
                <Textarea
                  id="cover-letter-prompt"
                  placeholder="E.g., Include all documents, mention LC number LC-2024-001, request prompt payment..."
                  value={coverLetterPrompt}
                  onChange={(e) => setCoverLetterPrompt(e.target.value)}
                  rows={4}
                />
              </div>
              <Button
                onClick={handleGenerateCoverLetter}
                disabled={generatingCoverLetter || !coverLetterPrompt.trim()}
                className="w-full"
              >
                {generatingCoverLetter ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Generate Cover Letter
                  </>
                )}
              </Button>
              
              {generatedCoverLetter && (
                <div className="mt-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Generated Cover Letter</Label>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCopy(generatedCoverLetter, "Cover letter")}
                    >
                      <Copy className="h-4 w-4 mr-2" />
                      Copy
                    </Button>
                  </div>
                  <div className="border rounded-lg p-4 bg-muted/50">
                    <pre className="whitespace-pre-wrap text-sm">{generatedCoverLetter}</pre>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="infer" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Infer Field Values</CardTitle>
              <CardDescription>
                Let AI suggest field values based on your documents and context.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="field-select">Field to Infer</Label>
                <Select value={selectedField} onValueChange={setSelectedField}>
                  <SelectTrigger id="field-select">
                    <SelectValue placeholder="Select a field" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="beneficiary">Beneficiary Name</SelectItem>
                    <SelectItem value="amount">LC Amount</SelectItem>
                    <SelectItem value="expiry_date">Expiry Date</SelectItem>
                    <SelectItem value="port_of_loading">Port of Loading</SelectItem>
                    <SelectItem value="port_of_discharge">Port of Discharge</SelectItem>
                    <SelectItem value="incoterms">Incoterms</SelectItem>
                    <SelectItem value="description">Goods Description</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <Label htmlFor="inference-context">Context (Optional)</Label>
                <Textarea
                  id="inference-context"
                  placeholder="Provide additional context to help AI infer the value..."
                  value={inferenceContext}
                  onChange={(e) => setInferenceContext(e.target.value)}
                  rows={3}
                />
              </div>
              
              <Button
                onClick={handleInferField}
                disabled={inferring || !selectedField}
                className="w-full"
              >
                {inferring ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Inferring...
                  </>
                ) : (
                  <>
                    <Lightbulb className="h-4 w-4 mr-2" />
                    Infer Value
                  </>
                )}
              </Button>
              
              {inferredValue && (
                <div className="mt-4 space-y-2">
                  <Label>Inferred Value</Label>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 border rounded-lg p-3 bg-muted/50">
                      <span className="font-medium">{inferredValue}</span>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        onFieldInferred?.(selectedField, inferredValue);
                        toast({
                          title: "Value Applied",
                          description: `Inferred value applied to ${selectedField}.`,
                        });
                      }}
                    >
                      <CheckCircle2 className="h-4 w-4 mr-2" />
                      Apply
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="translate" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Translate Descriptions</CardTitle>
              <CardDescription>
                Translate LC descriptions and document text to multiple languages.
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

