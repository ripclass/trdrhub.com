import React, { useState } from 'react';
import {
  FileEdit,
  Download,
  Copy,
  CheckCircle,
  AlertTriangle,
  Clock,
  RefreshCw,
  Sparkles,
} from 'lucide-react';

import { api } from '@/api/client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';

interface AIAmendmentFlowProps {
  lcId: string;
  currentDiscrepancies: any[];
  onAmendmentGenerated?: (amendment: NormalizedAmendment) => void;
  className?: string;
}

interface NormalizedAmendment {
  content: string;
  confidenceScore: number;
  modelUsed?: string;
  fallbackUsed: boolean;
  language?: string;
  auditEventId?: string;
  suggestedFields: Array<{
    fieldName: string;
    currentValue: string;
    suggestedValue: string;
    rationale: string;
  }>;
}

const confidenceToScore = (confidence?: string): number => {
  if (!confidence) return 0.5;
  switch (confidence.toLowerCase()) {
    case 'high':
      return 0.9;
    case 'medium':
      return 0.7;
    case 'low':
      return 0.4;
    default:
      return 0.5;
  }
};

export default function AIAmendmentFlow({
  lcId,
  currentDiscrepancies,
  onAmendmentGenerated,
  className = '',
}: AIAmendmentFlowProps) {
  const [amendment, setAmendment] = useState<NormalizedAmendment | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [amendmentType, setAmendmentType] = useState<string>('full');
  const [customInstructions, setCustomInstructions] = useState('');
  const [copied, setCopied] = useState(false);

  const generateAmendment = async () => {
    setLoading(true);
    setError(null);

    try {
      const { data } = await api.post('/api/ai/amendment-draft', {
        session_id: lcId,
        amendment_type: amendmentType,
        language: 'en',
        amendment_details: {
          discrepancies: currentDiscrepancies.map((item) => ({
            discrepancy_id: item.id,
            field_name: item.field_name,
            expected_value: item.expected_value,
            actual_value: item.actual_value,
            severity: item.severity,
          })),
          custom_instructions: customInstructions || undefined,
        },
      });

      const normalized: NormalizedAmendment = {
        content: data.content || data.output || 'No amendment draft generated.',
        confidenceScore:
          typeof data.confidence_score === 'number'
            ? data.confidence_score
            : confidenceToScore(data.confidence),
        modelUsed: data.model_used || data.model_version,
        fallbackUsed: Boolean(data.fallback_used),
        language: data.language,
        auditEventId: data.audit_event_id || data.event_id,
        suggestedFields: (data.suggested_fields || []).map((field: any) => ({
          fieldName: field.field_name,
          currentValue: field.current_value,
          suggestedValue: field.suggested_value,
          rationale: field.rationale,
        })),
      };

      setAmendment(normalized);
      onAmendmentGenerated?.(normalized);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate amendment');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async () => {
    if (!amendment) return;
    try {
      await navigator.clipboard.writeText(amendment.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const downloadAmendment = () => {
    if (!amendment) return;

    const blob = new Blob([amendment.content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `LC_${lcId}_Amendment_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'bg-green-100 text-green-800';
    if (score >= 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getConfidenceIcon = (score: number) => {
    if (score >= 0.8) return <CheckCircle className="w-4 h-4" />;
    if (score >= 0.6) return <Clock className="w-4 h-4" />;
    return <AlertTriangle className="w-4 h-4" />;
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileEdit className="w-5 h-5 text-purple-600" />
            <CardTitle className="text-lg">AI Amendment Generator</CardTitle>
          </div>
          <Badge className="bg-purple-100 text-purple-800">
            <Sparkles className="w-3 h-3 mr-1" />
            Beta
          </Badge>
        </div>
        <CardDescription>
          Generate professional amendment drafts for {currentDiscrepancies.length} discrepancies
        </CardDescription>
      </CardHeader>

      <CardContent>
        <Tabs defaultValue="generate" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="generate">Generate</TabsTrigger>
            <TabsTrigger value="preview" disabled={!amendment}>
              Preview
            </TabsTrigger>
          </TabsList>

          <TabsContent value="generate" className="space-y-4">
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Amendment Type</label>
                <Select value={amendmentType} onValueChange={setAmendmentType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="full">Full Amendment (MT707)</SelectItem>
                    <SelectItem value="partial">Partial Amendment</SelectItem>
                    <SelectItem value="cancellation">Cancellation Request</SelectItem>
                    <SelectItem value="correction">Error Correction</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">Custom Instructions (Optional)</label>
                <Textarea
                  value={customInstructions}
                  onChange={(e) => setCustomInstructions(e.target.value)}
                  placeholder="Add specific requirements, regulatory notes, or formatting preferences..."
                  rows={3}
                />
              </div>

              {error && (
                <Alert>
                  <AlertTriangle className="w-4 h-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Button onClick={generateAmendment} disabled={loading} className="w-full">
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Generating Amendment...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Generate Amendment Draft
                  </>
                )}
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="preview">
            {loading && (
              <div className="space-y-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
                <Skeleton className="h-4 w-2/3" />
              </div>
            )}

            {!loading && amendment && (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <Badge className={getConfidenceColor(amendment.confidenceScore)}>
                    {getConfidenceIcon(amendment.confidenceScore)}
                    {Math.round(amendment.confidenceScore * 100)}% confidence
                  </Badge>
                  {amendment.fallbackUsed && (
                    <Badge variant="outline" className="text-orange-600">
                      Rule-based fallback
                    </Badge>
                  )}
                  <Badge variant="secondary">{amendment.modelUsed || 'LLM'}</Badge>
                </div>

                <div className="border rounded-md p-4 bg-muted/20 space-y-3">
                  <pre className="text-sm whitespace-pre-wrap">{amendment.content}</pre>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" onClick={copyToClipboard}>
                    {copied ? (
                      <>
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4 mr-2" />
                        Copy to Clipboard
                      </>
                    )}
                  </Button>
                  <Button variant="outline" onClick={downloadAmendment}>
                    <Download className="w-4 h-4 mr-2" />
                    Download Draft
                  </Button>
                </div>

                {amendment.suggestedFields.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold mb-2">Suggested Changes</h3>
                    <div className="space-y-3">
                      {amendment.suggestedFields.map((field) => (
                        <div key={field.fieldName} className="border rounded-md p-3 text-sm space-y-1">
                          <div className="font-semibold">{field.fieldName}</div>
                          <div className="text-xs text-muted-foreground">
                            Current: {field.currentValue || 'N/A'}
                          </div>
                          <div className="text-xs text-green-700">
                            Suggested: {field.suggestedValue || 'N/A'}
                          </div>
                          <div className="text-xs text-muted-foreground italic">
                            Rationale: {field.rationale || 'Not provided'}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="text-xs text-muted-foreground">
                  Analysis ID: {amendment.auditEventId ?? 'N/A'} - Generated at {new Date().toLocaleString()}
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
