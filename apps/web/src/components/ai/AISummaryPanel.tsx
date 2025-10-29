import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Brain, AlertTriangle, CheckCircle, Clock, RefreshCw } from 'lucide-react';

interface AISummaryPanelProps {
  lcId: string;
  discrepancies: any[];
  onRefresh?: () => void;
  className?: string;
}

interface AIResponse {
  content: string;
  confidence_score: number;
  model_used: string;
  fallback_used: boolean;
  language: string;
  audit_event_id: string;
}

export default function AISummaryPanel({
  lcId,
  discrepancies,
  onRefresh,
  className = ""
}: AISummaryPanelProps) {
  const [summary, setSummary] = useState<AIResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateSummary = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/ai/discrepancies', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          lc_id: lcId,
          discrepancies: discrepancies.map(d => ({
            discrepancy_id: d.id,
            field_name: d.field_name,
            expected_value: d.expected_value,
            actual_value: d.actual_value,
            severity: d.severity
          })),
          language: 'en',
          include_recommendations: true,
          analysis_depth: 'detailed'
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to generate summary: ${response.statusText}`);
      }

      const data = await response.json();
      setSummary(data);
      onRefresh?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate summary');
    } finally {
      setLoading(false);
    }
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
            <Brain className="w-5 h-5 text-blue-600" />
            <CardTitle className="text-lg">AI Discrepancy Summary</CardTitle>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={generateSummary}
            disabled={loading}
          >
            {loading ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            {loading ? 'Analyzing...' : 'Generate'}
          </Button>
        </div>
        <CardDescription>
          AI-powered analysis of {discrepancies.length} discrepancies
        </CardDescription>
      </CardHeader>

      <CardContent>
        {error && (
          <Alert className="mb-4">
            <AlertTriangle className="w-4 h-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {loading && (
          <div className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        )}

        {summary && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-3">
              <Badge className={getConfidenceColor(summary.confidence_score)}>
                {getConfidenceIcon(summary.confidence_score)}
                {Math.round(summary.confidence_score * 100)}% confidence
              </Badge>

              {summary.fallback_used && (
                <Badge variant="outline" className="text-orange-600">
                  Rule-based fallback
                </Badge>
              )}

              <Badge variant="secondary">
                {summary.model_used}
              </Badge>
            </div>

            <div className="prose prose-sm max-w-none">
              <div
                className="text-sm leading-relaxed"
                dangerouslySetInnerHTML={{
                  __html: summary.content.replace(/\n/g, '<br />')
                }}
              />
            </div>

            <div className="border-t pt-3">
              <p className="text-xs text-muted-foreground">
                Analysis ID: {summary.audit_event_id} • Generated at {new Date().toLocaleString()}
              </p>
            </div>
          </div>
        )}

        {!summary && !loading && !error && (
          <div className="text-center py-8 text-muted-foreground">
            <Brain className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">Click "Generate" to get AI-powered insights</p>
            <p className="text-xs mt-1">
              Analyze discrepancies with confidence scoring and recommendations
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}