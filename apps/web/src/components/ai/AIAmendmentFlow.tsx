import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  FileEdit,
  Download,
  Copy,
  CheckCircle,
  AlertTriangle,
  Clock,
  RefreshCw,
  Sparkles
} from 'lucide-react';

interface AIAmendmentFlowProps {
  lcId: string;
  currentDiscrepancies: any[];
  onAmendmentGenerated?: (amendment: any) => void;
  className?: string;
}

interface AmendmentResponse {
  content: string;
  confidence_score: number;
  model_used: string;
  fallback_used: boolean;
  language: string;
  audit_event_id: string;
  suggested_fields: Array<{
    field_name: string;
    current_value: string;
    suggested_value: string;
    rationale: string;
  }>;
}

export default function AIAmendmentFlow({
  lcId,
  currentDiscrepancies,
  onAmendmentGenerated,
  className = ""
}: AIAmendmentFlowProps) {
  const [amendment, setAmendment] = useState<AmendmentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [amendmentType, setAmendmentType] = useState<string>('full');
  const [customInstructions, setCustomInstructions] = useState('');
  const [copied, setCopied] = useState(false);

  const generateAmendment = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/ai/amendment-draft', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          lc_id: lcId,
          discrepancies: currentDiscrepancies.map(d => ({
            discrepancy_id: d.id,
            field_name: d.field_name,
            expected_value: d.expected_value,
            actual_value: d.actual_value,
            severity: d.severity
          })),
          amendment_type: amendmentType,
          custom_instructions: customInstructions || undefined,
          language: 'en',
          include_rationale: true,
          format: 'swift_mt707'
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to generate amendment: ${response.statusText}`);
      }

      const data = await response.json();
      setAmendment(data);
      onAmendmentGenerated?.(data);
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
    const a = document.createElement('a');
    a.href = url;
    a.download = `LC_${lcId}_Amendment_${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
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
    <Card className={`${className}`}>
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
                <label className="text-sm font-medium mb-2 block">
                  Amendment Type
                </label>
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
                <label className="text-sm font-medium mb-2 block">
                  Custom Instructions (Optional)
                </label>
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

              <Button
                onClick={generateAmendment}
                disabled={loading || currentDiscrepancies.length === 0}
                className="w-full"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Generating Amendment...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Generate AI Amendment
                  </>
                )}
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="preview" className="space-y-4">
            {loading && (
              <div className="space-y-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-20 w-full" />
              </div>
            )}

            {amendment && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge className={getConfidenceColor(amendment.confidence_score)}>
                      {getConfidenceIcon(amendment.confidence_score)}
                      {Math.round(amendment.confidence_score * 100)}% confidence
                    </Badge>

                    {amendment.fallback_used && (
                      <Badge variant="outline" className="text-orange-600">
                        Rule-based fallback
                      </Badge>
                    )}

                    <Badge variant="secondary">
                      {amendment.model_used}
                    </Badge>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={copyToClipboard}
                    >
                      {copied ? (
                        <CheckCircle className="w-4 h-4 mr-1" />
                      ) : (
                        <Copy className="w-4 h-4 mr-1" />
                      )}
                      {copied ? 'Copied!' : 'Copy'}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={downloadAmendment}
                    >
                      <Download className="w-4 h-4 mr-1" />
                      Download
                    </Button>
                  </div>
                </div>

                <div className="border rounded-lg p-4 bg-gray-50">
                  <h4 className="font-medium mb-2">Generated Amendment</h4>
                  <pre className="text-xs bg-white p-3 rounded border overflow-auto max-h-64 whitespace-pre-wrap">
                    {amendment.content}
                  </pre>
                </div>

                {amendment.suggested_fields?.length > 0 && (
                  <div className="border rounded-lg p-4">
                    <h4 className="font-medium mb-3">Suggested Field Changes</h4>
                    <div className="space-y-3">
                      {amendment.suggested_fields.map((field, index) => (
                        <div key={index} className="border-l-2 border-blue-200 pl-3">
                          <div className="font-medium text-sm">{field.field_name}</div>
                          <div className="text-xs text-gray-600 mt-1">
                            <span className="line-through text-red-600">
                              {field.current_value}
                            </span>
                            <span className="mx-2">→</span>
                            <span className="text-green-600 font-medium">
                              {field.suggested_value}
                            </span>
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            {field.rationale}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="border-t pt-3">
                  <p className="text-xs text-muted-foreground">
                    Amendment ID: {amendment.audit_event_id} • Generated at {new Date().toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Please review all suggested changes before submitting to the issuing bank
                  </p>
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>

        {!amendment && !loading && !error && (
          <div className="text-center py-8 text-muted-foreground mt-4">
            <FileEdit className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">Configure options and generate your amendment</p>
            <p className="text-xs mt-1">
              AI-powered SWIFT MT707 compliant amendment drafts
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}