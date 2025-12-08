/**
 * ExporterResultsV2 - SME-Focused Results Page (Output-First)
 * 
 * This page consumes the SMEValidationResponse contract.
 * Clean, simple, focused on what SME users need to see.
 * 
 * @version 2.0
 * @date 2024-12-07
 */

import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  AlertCircle,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Clock,
  DollarSign,
  ChevronRight,
  RefreshCw,
  Download,
  Send,
  Home,
  Loader2,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

// ============================================
// TYPES (from shared-types contract)
// ============================================

type VerdictStatus = "PASS" | "FIX_REQUIRED" | "LIKELY_REJECT" | "MISSING_DOCS";
type Severity = "critical" | "major" | "minor";
type RiskLevel = "low" | "medium" | "high";

interface LCSummary {
  number: string;
  amount: number;
  currency: string;
  beneficiary: string;
  applicant: string;
  expiry_date: string;
  days_until_expiry: number;
  issuing_bank?: string;
}

interface Verdict {
  status: VerdictStatus;
  headline: string;
  subtext: string;
  estimated_risk: RiskLevel;
  estimated_fee_if_rejected: number;
  total_issues: number;
  critical_count: number;
  major_count: number;
  minor_count: number;
  missing_docs_count: number;
}

interface SMEIssue {
  id: string;
  title: string;
  severity: Severity;
  your_document: string;
  lc_requires: string;
  difference?: string;
  document_type: string;
  document_name: string;
  affected_documents?: string[];
  how_to_fix: string[];
  why_banks_reject: string;
  ucp_article?: string;
  isbp_reference?: string;
  lc_clause?: string;
}

interface SMEDocument {
  type: string;
  name: string;
  filename?: string;
  status: "verified" | "has_issues";
  status_note: string;
  issues_count: number;
}

interface SMEMissingDoc {
  type: string;
  name: string;
  required_by: string;
  description?: string;
  accepted_issuers?: string[];
}

interface SMEValidationResponse {
  version: string;
  lc_summary: LCSummary;
  verdict: Verdict;
  issues: {
    must_fix: SMEIssue[];
    should_fix: SMEIssue[];
  };
  documents: {
    good: SMEDocument[];
    has_issues: SMEDocument[];
    missing: SMEMissingDoc[];
  };
  processing: {
    session_id: string;
    processed_at: string;
    processing_time_seconds: number;
    processing_time_display: string;
    documents_checked: number;
    rules_executed: number;
  };
}

// ============================================
// API FETCH
// ============================================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://trdrhub-api.onrender.com';

async function fetchValidationResultV2(sessionId: string): Promise<SMEValidationResponse> {
  const response = await fetch(`${API_BASE_URL}/api/validate/v2/session/${sessionId}`, {
    credentials: 'include',
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch results: ${response.statusText}`);
  }
  
  const json = await response.json();
  return json.data;
}

// ============================================
// VERDICT CARD
// ============================================

function VerdictCard({ verdict }: { verdict: Verdict }) {
  const getVerdictStyle = () => {
    switch (verdict.status) {
      case "PASS":
        return {
          bg: "bg-green-50 border-green-200",
          icon: <CheckCircle2 className="h-8 w-8 text-green-600" />,
          textColor: "text-green-800",
        };
      case "FIX_REQUIRED":
        return {
          bg: "bg-yellow-50 border-yellow-200",
          icon: <AlertTriangle className="h-8 w-8 text-yellow-600" />,
          textColor: "text-yellow-800",
        };
      case "LIKELY_REJECT":
        return {
          bg: "bg-red-50 border-red-200",
          icon: <XCircle className="h-8 w-8 text-red-600" />,
          textColor: "text-red-800",
        };
      case "MISSING_DOCS":
        return {
          bg: "bg-orange-50 border-orange-200",
          icon: <FileText className="h-8 w-8 text-orange-600" />,
          textColor: "text-orange-800",
        };
      default:
        return {
          bg: "bg-gray-50 border-gray-200",
          icon: <AlertCircle className="h-8 w-8 text-gray-600" />,
          textColor: "text-gray-800",
        };
    }
  };

  const style = getVerdictStyle();

  return (
    <Card className={`${style.bg} border-2`}>
      <CardContent className="pt-6">
        <div className="flex items-start gap-4">
          {style.icon}
          <div className="flex-1">
            <h2 className={`text-2xl font-bold ${style.textColor}`}>
              {verdict.headline}
            </h2>
            <p className={`mt-1 ${style.textColor} opacity-80`}>
              {verdict.subtext}
            </p>
            
            {verdict.estimated_fee_if_rejected > 0 && (
              <div className="mt-3 flex items-center gap-2 text-sm">
                <DollarSign className="h-4 w-4" />
                <span>Estimated discrepancy fee if rejected: ${verdict.estimated_fee_if_rejected.toFixed(2)}</span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================
// ISSUE CARD
// ============================================

function IssueCard({ issue, index }: { issue: SMEIssue; index: number }) {
  const getSeverityBadge = () => {
    switch (issue.severity) {
      case "critical":
        return <Badge variant="destructive">Critical</Badge>;
      case "major":
        return <Badge className="bg-orange-500">Major</Badge>;
      case "minor":
        return <Badge variant="secondary">Minor</Badge>;
    }
  };

  return (
    <Card className="mb-4">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-sm font-medium">
              {index + 1}
            </span>
            <div>
              <CardTitle className="text-lg">{issue.title}</CardTitle>
              <div className="mt-1 flex items-center gap-2">
                {getSeverityBadge()}
                <Badge variant="outline">📄 {issue.document_name}</Badge>
              </div>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* The Discrepancy */}
        <div className="mb-4 rounded-lg bg-gray-50 p-4">
          <div className="grid gap-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Your document:</span>
              <span className="font-medium">{issue.your_document}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">LC requires:</span>
              <span className="font-medium">{issue.lc_requires}</span>
            </div>
            {issue.difference && (
              <div className="flex justify-between text-red-600">
                <span>Difference:</span>
                <span className="font-medium">{issue.difference}</span>
              </div>
            )}
          </div>
        </div>

        {/* How to Fix */}
        <div className="mb-4">
          <h4 className="mb-2 flex items-center gap-2 font-medium text-green-700">
            💡 HOW TO FIX:
          </h4>
          <ul className="space-y-1 text-sm">
            {issue.how_to_fix.map((fix, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-green-600">•</span>
                <span>{fix}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Why Banks Reject */}
        <div className="text-sm text-gray-600">
          <span className="font-medium">📖 Why banks reject this: </span>
          {issue.why_banks_reject}
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================
// DOCUMENT STATUS SECTION
// ============================================

function DocumentSection({ documents }: { documents: SMEValidationResponse['documents'] }) {
  return (
    <div className="space-y-6">
      {/* Good Documents */}
      {documents.good.length > 0 && (
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-lg font-semibold text-green-700">
            <CheckCircle2 className="h-5 w-5" />
            DOCUMENTS THAT LOOK GOOD
          </h3>
          <div className="space-y-2">
            {documents.good.map((doc) => (
              <div
                key={doc.type}
                className="flex items-center justify-between rounded-lg border border-green-200 bg-green-50 p-3"
              >
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  <span className="font-medium">{doc.name}</span>
                </div>
                <span className="text-sm text-green-600">{doc.status_note}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Documents with Issues */}
      {documents.has_issues.length > 0 && (
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-lg font-semibold text-yellow-700">
            <AlertTriangle className="h-5 w-5" />
            DOCUMENTS WITH ISSUES
          </h3>
          <div className="space-y-2">
            {documents.has_issues.map((doc) => (
              <div
                key={doc.type}
                className="flex items-center justify-between rounded-lg border border-yellow-200 bg-yellow-50 p-3"
              >
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-yellow-600" />
                  <span className="font-medium">{doc.name}</span>
                </div>
                <Badge variant="secondary">{doc.issues_count} issue(s)</Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Missing Documents */}
      {documents.missing.length > 0 && (
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-lg font-semibold text-red-700">
            <XCircle className="h-5 w-5" />
            MISSING DOCUMENTS
          </h3>
          <div className="space-y-2">
            {documents.missing.map((doc) => (
              <div
                key={doc.type}
                className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 p-3"
              >
                <div className="flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-red-600" />
                  <span className="font-medium">{doc.name}</span>
                </div>
                <span className="text-sm text-red-600">Required by {doc.required_by}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================
// MAIN PAGE
// ============================================

export default function ExporterResultsV2() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['validation-v2', sessionId],
    queryFn: () => fetchValidationResultV2(sessionId!),
    enabled: !!sessionId,
  });

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-12 w-12 animate-spin text-blue-600" />
          <p className="mt-4 text-gray-600">Loading validation results...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="container mx-auto max-w-4xl p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error loading results</AlertTitle>
          <AlertDescription>
            {error instanceof Error ? error.message : 'Failed to load validation results'}
          </AlertDescription>
        </Alert>
        <Button onClick={() => navigate('/lcopilot/upload')} className="mt-4">
          <Home className="mr-2 h-4 w-4" />
          Back to Upload
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-4xl p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">LC Document Check</h1>
          <div className="mt-1 flex items-center gap-4 text-sm text-gray-600">
            <span>LC: {data.lc_summary.number}</span>
            <span>•</span>
            <span>{data.lc_summary.currency} {data.lc_summary.amount.toLocaleString()}</span>
            <span>•</span>
            <span>{data.lc_summary.beneficiary}</span>
          </div>
        </div>
        <Button variant="outline" onClick={() => navigate('/lcopilot/dashboard')}>
          <Home className="mr-2 h-4 w-4" />
          Home
        </Button>
      </div>

      {/* Verdict Card */}
      <VerdictCard verdict={data.verdict} />

      {/* Issues - Must Fix */}
      {data.issues.must_fix.length > 0 && (
        <div className="mt-8">
          <h3 className="mb-4 text-xl font-bold text-red-700">
            🔴 MUST FIX ({data.issues.must_fix.length})
          </h3>
          <p className="mb-4 text-sm text-gray-600">
            These issues will cause rejection. Fix them before submitting.
          </p>
          {data.issues.must_fix.map((issue, index) => (
            <IssueCard key={issue.id} issue={issue} index={index} />
          ))}
        </div>
      )}

      {/* Issues - Should Fix */}
      {data.issues.should_fix.length > 0 && (
        <div className="mt-8">
          <h3 className="mb-4 text-xl font-bold text-yellow-700">
            🟡 SHOULD FIX ({data.issues.should_fix.length})
          </h3>
          <p className="mb-4 text-sm text-gray-600">
            Minor issues that may cause problems. Recommended to fix.
          </p>
          {data.issues.should_fix.map((issue, index) => (
            <IssueCard key={issue.id} issue={issue} index={data.issues.must_fix.length + index} />
          ))}
        </div>
      )}

      {/* Document Status */}
      <div className="mt-8">
        <Separator className="mb-6" />
        <DocumentSection documents={data.documents} />
      </div>

      {/* Action Buttons */}
      <div className="mt-8 flex gap-4">
        <Button variant="outline" onClick={() => refetch()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Re-check After Fixes
        </Button>
        <Button variant="outline">
          <Download className="mr-2 h-4 w-4" />
          Download Report
        </Button>
        <Button 
          disabled={data.verdict.status === "LIKELY_REJECT" || data.verdict.status === "MISSING_DOCS"}
        >
          <Send className="mr-2 h-4 w-4" />
          Submit to Bank
        </Button>
      </div>

      {/* Processing Info */}
      <div className="mt-8 rounded-lg bg-gray-50 p-4 text-sm text-gray-600">
        <div className="flex items-center gap-4">
          <Clock className="h-4 w-4" />
          <span>Processed in {data.processing.processing_time_display}</span>
          <span>•</span>
          <span>{data.processing.documents_checked} documents checked</span>
          <span>•</span>
          <span>{data.processing.rules_executed} rules evaluated</span>
        </div>
      </div>
    </div>
  );
}
