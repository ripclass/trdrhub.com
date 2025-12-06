/**
 * V2 Validation Results
 * 
 * Unified results view with:
 * - Verdict banner
 * - Issues with citations
 * - Document quality metrics
 * - Extracted data preview
 * 
 * This replaces ExporterResults.tsx in V2.
 */

import { useState } from 'react';
import { 
  FileText, 
  AlertTriangle, 
  CheckCircle, 
  BarChart3, 
  Download,
  RefreshCw,
  FileSearch,
  Shield,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';

import { VerdictBannerV2, type VerdictV2 } from './VerdictBannerV2';
import { IssueCardV2, type IssueV2 } from './IssueCardV2';

// V2 Response Types
export interface DocumentResultV2 {
  id: string;
  filename: string;
  documentType: string;
  quality: {
    overall: number;
    ocrConfidence: number;
    category: string;
  };
  regions: {
    hasHandwriting: boolean;
    hasSignatures: boolean;
    hasStamps: boolean;
    handwritingCount: number;
    signatureCount: number;
    stampCount: number;
  };
  extracted: Record<string, {
    value: any;
    confidence: number;
    source: string;
    providerAgreement: number;
    needsReview: boolean;
  }>;
  processingTimeMs: number;
  pagesProcessed: number;
  status: string;
}

export interface SanctionsStatusV2 {
  screened: boolean;
  partiesScreened: number;
  matchesFound: number;
  status: 'clear' | 'potential_match' | 'match' | 'blocked';
  matches?: Array<{
    party: string;
    partyType: string;
    listName: string;
    matchScore: number;
    matchType: string;
    sanctionPrograms: string[];
  }>;
}

export interface ValidationResultsV2Data {
  sessionId: string;
  version: string;
  processingTimeSeconds: number;
  verdict: VerdictV2;
  documents: DocumentResultV2[];
  issues: IssueV2[];
  amendments: any[];
  extractedData: Record<string, Record<string, any>>;
  compliance: {
    sanctionsStatus: SanctionsStatusV2;
    ucpCompliance: number;
    isbpCompliance: number;
    overallScore: number;
  };
  quality: {
    overallConfidence: number;
    fieldsNeedingReview: string[];
    poorQualityDocuments: string[];
    handwritingDetected: boolean;
    providersUsed: string[];
  };
  audit: {
    rulesEvaluated: number;
    rulesPassed: number;
    rulesFailed: number;
    crossDocChecks: number;
    aiProvidersUsed: string[];
  };
}

interface ValidationResultsV2Props {
  data: ValidationResultsV2Data;
  onRevalidate?: () => void;
  onDownload?: () => void;
  onAmendment?: (issue: IssueV2) => void;
  onSubmit?: () => void;
}

export function ValidationResultsV2({ 
  data, 
  onRevalidate,
  onDownload,
  onAmendment,
  onSubmit,
}: ValidationResultsV2Props) {
  const [activeTab, setActiveTab] = useState('overview');
  
  const criticalIssues = data.issues.filter(i => i.severity === 'critical');
  const majorIssues = data.issues.filter(i => i.severity === 'major');
  const minorIssues = data.issues.filter(i => i.severity === 'minor');
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            Validation Results
          </h1>
          <p className="text-sm text-slate-500">
            Session: {data.sessionId} • V2 Pipeline
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          {onRevalidate && (
            <Button variant="outline" size="sm" onClick={onRevalidate}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Revalidate
            </Button>
          )}
          {onDownload && (
            <Button variant="outline" size="sm" onClick={onDownload}>
              <Download className="h-4 w-4 mr-2" />
              Export PDF
            </Button>
          )}
        </div>
      </div>
      
      {/* Verdict Banner */}
      <VerdictBannerV2 
        verdict={data.verdict}
        processingTime={data.processingTimeSeconds}
        onSubmit={data.verdict.canSubmitToBank ? onSubmit : undefined}
      />
      
      {/* Sanctions Alert */}
      {data.compliance.sanctionsStatus.status !== 'clear' && (
        <Card className="border-red-300 bg-red-50">
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <Shield className="h-6 w-6 text-red-600" />
              <div className="flex-1">
                <h3 className="font-semibold text-red-900">
                  Sanctions Alert: {data.compliance.sanctionsStatus.matchesFound} potential match(es)
                </h3>
                <p className="text-sm text-red-700">
                  Compliance review required before proceeding
                </p>
              </div>
              <Badge variant="destructive">
                {data.compliance.sanctionsStatus.status.toUpperCase()}
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid grid-cols-4 w-full max-w-lg">
          <TabsTrigger value="overview" className="gap-2">
            <BarChart3 className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="issues" className="gap-2">
            <AlertTriangle className="h-4 w-4" />
            Issues
            {data.issues.length > 0 && (
              <Badge variant="secondary" className="ml-1 h-5 w-5 p-0 text-xs">
                {data.issues.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="documents" className="gap-2">
            <FileText className="h-4 w-4" />
            Documents
          </TabsTrigger>
          <TabsTrigger value="extracted" className="gap-2">
            <FileSearch className="h-4 w-4" />
            Data
          </TabsTrigger>
        </TabsList>
        
        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Compliance Score */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">
                  UCP600 Compliance
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold text-slate-900">
                    {data.compliance.ucpCompliance}%
                  </span>
                </div>
                <Progress 
                  value={data.compliance.ucpCompliance} 
                  className="mt-2"
                />
              </CardContent>
            </Card>
            
            {/* Rules Checked */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">
                  Rules Evaluated
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold text-slate-900">
                    {data.audit.rulesEvaluated}
                  </span>
                  <span className="text-sm text-slate-500 mb-1">
                    rules
                  </span>
                </div>
                <p className="text-sm text-green-600 mt-1">
                  ✓ {data.audit.rulesPassed} passed
                </p>
              </CardContent>
            </Card>
            
            {/* AI Providers */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500 flex items-center gap-1">
                  <Sparkles className="h-4 w-4" />
                  AI Ensemble
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-1">
                  {data.quality.providersUsed.map((provider) => (
                    <Badge key={provider} variant="secondary">
                      {provider}
                    </Badge>
                  ))}
                </div>
                <p className="text-sm text-slate-600 mt-2">
                  {Math.round(data.quality.overallConfidence * 100)}% confidence
                </p>
              </CardContent>
            </Card>
          </div>
          
          {/* Quick Issue Summary */}
          {data.issues.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Issue Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {criticalIssues.length > 0 && (
                  <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                    <span className="text-red-700 font-medium">
                      Critical Issues
                    </span>
                    <Badge variant="destructive">{criticalIssues.length}</Badge>
                  </div>
                )}
                {majorIssues.length > 0 && (
                  <div className="flex items-center justify-between p-3 bg-orange-50 rounded-lg">
                    <span className="text-orange-700 font-medium">
                      Major Issues
                    </span>
                    <Badge className="bg-orange-500">{majorIssues.length}</Badge>
                  </div>
                )}
                {minorIssues.length > 0 && (
                  <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                    <span className="text-yellow-700 font-medium">
                      Minor Issues
                    </span>
                    <Badge className="bg-yellow-500">{minorIssues.length}</Badge>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>
        
        {/* Issues Tab */}
        <TabsContent value="issues" className="space-y-4">
          {data.issues.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-slate-900">
                  No Discrepancies Found
                </h3>
                <p className="text-sm text-slate-500 mt-1">
                  All documents comply with UCP600/ISBP745 requirements
                </p>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-500">
                  {data.issues.length} issue{data.issues.length !== 1 && 's'} found
                </p>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    All citations included
                  </Badge>
                </div>
              </div>
              
              {/* Critical Issues First */}
              {criticalIssues.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-red-600 uppercase tracking-wide">
                    Critical — Will Cause Rejection
                  </h3>
                  {criticalIssues.map((issue) => (
                    <IssueCardV2 
                      key={issue.id} 
                      issue={issue}
                      onAmendClick={onAmendment}
                    />
                  ))}
                </div>
              )}
              
              {/* Major Issues */}
              {majorIssues.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-orange-600 uppercase tracking-wide">
                    Major — High Risk of Rejection
                  </h3>
                  {majorIssues.map((issue) => (
                    <IssueCardV2 
                      key={issue.id} 
                      issue={issue}
                      onAmendClick={onAmendment}
                    />
                  ))}
                </div>
              )}
              
              {/* Minor Issues */}
              {minorIssues.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold text-yellow-600 uppercase tracking-wide">
                    Minor — May Cause Discrepancy
                  </h3>
                  {minorIssues.map((issue) => (
                    <IssueCardV2 
                      key={issue.id} 
                      issue={issue}
                      onAmendClick={onAmendment}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </TabsContent>
        
        {/* Documents Tab */}
        <TabsContent value="documents" className="space-y-4">
          {data.documents.map((doc) => (
            <Card key={doc.id}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-slate-400" />
                    <div>
                      <h3 className="font-semibold text-slate-900">
                        {doc.filename}
                      </h3>
                      <p className="text-sm text-slate-500">
                        {doc.documentType.replace(/_/g, ' ')} • {doc.pagesProcessed} page{doc.pagesProcessed !== 1 && 's'}
                      </p>
                    </div>
                  </div>
                  <Badge variant={doc.status === 'success' ? 'default' : 'secondary'}>
                    {doc.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Quality Metrics */}
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-xs text-slate-500 uppercase">OCR Quality</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Progress value={doc.quality.ocrConfidence * 100} className="flex-1" />
                      <span className="text-sm font-medium">
                        {Math.round(doc.quality.ocrConfidence * 100)}%
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase">Processing</p>
                    <p className="text-sm font-medium mt-1">{doc.processingTimeMs}ms</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase">Category</p>
                    <Badge variant="outline" className="mt-1">
                      {doc.quality.category}
                    </Badge>
                  </div>
                </div>
                
                {/* Special Detections */}
                {(doc.regions.hasHandwriting || doc.regions.hasSignatures || doc.regions.hasStamps) && (
                  <div className="flex items-center gap-2 flex-wrap">
                    {doc.regions.hasHandwriting && (
                      <Badge variant="secondary">
                        ✍️ Handwriting ({doc.regions.handwritingCount})
                      </Badge>
                    )}
                    {doc.regions.hasSignatures && (
                      <Badge variant="secondary">
                        ✒️ Signatures ({doc.regions.signatureCount})
                      </Badge>
                    )}
                    {doc.regions.hasStamps && (
                      <Badge variant="secondary">
                        📍 Stamps ({doc.regions.stampCount})
                      </Badge>
                    )}
                  </div>
                )}
                
                {/* Extracted Fields Preview */}
                <div className="border-t pt-4">
                  <p className="text-xs text-slate-500 uppercase mb-2">
                    Extracted Fields ({Object.keys(doc.extracted).length})
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(doc.extracted).slice(0, 6).map(([key, val]) => (
                      <div 
                        key={key}
                        className={cn(
                          'p-2 rounded text-sm',
                          val.needsReview ? 'bg-yellow-50 border border-yellow-200' : 'bg-slate-50'
                        )}
                      >
                        <span className="text-slate-500">{key}:</span>{' '}
                        <span className="font-medium">{String(val.value).slice(0, 30)}</span>
                        {val.needsReview && (
                          <Badge variant="outline" className="ml-2 text-xs">
                            Review
                          </Badge>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>
        
        {/* Extracted Data Tab */}
        <TabsContent value="extracted" className="space-y-4">
          {Object.entries(data.extractedData).map(([docType, fields]) => (
            <Card key={docType}>
              <CardHeader>
                <CardTitle className="text-lg capitalize">
                  {docType.replace(/_/g, ' ')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {Object.entries(fields).map(([fieldName, fieldData]) => (
                    <div 
                      key={fieldName}
                      className={cn(
                        'p-3 rounded-lg border',
                        fieldData.needsReview 
                          ? 'bg-yellow-50 border-yellow-200' 
                          : 'bg-slate-50 border-slate-200'
                      )}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-slate-500 uppercase">
                          {fieldName.replace(/_/g, ' ')}
                        </span>
                        <span className="text-xs text-slate-400">
                          {Math.round(fieldData.confidence * 100)}%
                        </span>
                      </div>
                      <p className="font-medium text-slate-900 break-words">
                        {typeof fieldData.value === 'object' 
                          ? JSON.stringify(fieldData.value) 
                          : String(fieldData.value)}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {fieldData.source}
                        </Badge>
                        {fieldData.providerAgreement < 1 && (
                          <span className="text-xs text-slate-400">
                            {Math.round(fieldData.providerAgreement * 100)}% agreement
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default ValidationResultsV2;

