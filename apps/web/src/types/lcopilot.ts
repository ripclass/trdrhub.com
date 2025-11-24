import type {
  StructuredResult as SharedStructuredResultPayload,
  StructuredResultDocument as SharedStructuredResultDocument,
  StructuredResultIssue as SharedStructuredResultIssue,
  StructuredResultAnalytics as SharedStructuredResultAnalytics,
  StructuredProcessingSummary as SharedProcessingSummary,
  SeverityBreakdown as SharedSeverityBreakdown,
  TimelineEntry as SharedTimelineEntry,
  DocumentRiskEntry as SharedDocumentRiskEntry,
} from '@shared/types';

export type OptionEDocument = {
  document_id: string;
  document_type: string;
  filename: string;
  extraction_status?: string | null;
  extracted_fields?: Record<string, unknown>;
  issues_count?: number;
};

export type OptionELCStructured = {
  mt700?: {
    blocks?: Record<string, string | null>;
    raw_text?: string | null;
    version?: string;
  };
  goods?: Array<Record<string, unknown>>;
  clauses?: Array<Record<string, unknown>>;
  timeline?: Array<{
    title?: string;
    status?: string;
    description?: string | null;
    timestamp?: string | null;
  }>;
  documents_structured?: OptionEDocument[];
  analytics?: {
    compliance_score?: number | null;
    issue_counts?: { critical?: number; major?: number; medium?: number; minor?: number };
  };
};

export type OptionEStructuredResult = StructuredResultPayload & {
  version: 'structured_result_v1';
  lc_type?: string;
  lc_type_reason?: string | null;
  lc_type_confidence?: number | null;
  lc_type_source?: string | null;
  lc_structured?: OptionELCStructured | null;
  documents_structured?: OptionEDocument[];
  analytics?: StructuredResultAnalytics & {
    customs_risk?: {
      score: number;
      tier: 'low' | 'med' | 'high';
      flags: string[];
    };
  };
  reference_issues?: ReferenceIssue[];
  customs_pack?: {
    ready: boolean;
    manifest: Array<{ name?: string | null; tag?: string | null }>;
    format: string;
  };
  ai_enrichment?: {
    enabled?: boolean;
    notes?: unknown[];
  };
};

export interface IssueCard {
  id: string;
  rule?: string;
  title: string;
  description: string;
  severity: string;
  priority?: string;
  documentName?: string;
  documentType?: string;
  documents?: string[];
  expected?: string;
  actual?: string;
  suggestion?: string;
  field?: string;
  ucpReference?: string;
}

export interface ReferenceIssue {
  rule?: string;
  title?: string;
  severity?: string;
  message?: string;
  article?: string;
  ruleset_domain?: string;
}

export interface AIEnrichmentPayload {
  summary?: string;
  suggestions?: string[];
  confidence?: string;
  rule_references?: Array<{
    rule_code: string;
    title?: string;
  }>;
}

export type SeverityBreakdown = SharedSeverityBreakdown;

export type ProcessingSummaryPayload = SharedProcessingSummary;

export interface ValidationDocument {
  id: string;
  documentId: string;
  name: string;
  filename: string;
  type: string;
  typeKey?: string;
  extractionStatus: string;
  status: 'success' | 'warning' | 'error';
  issuesCount: number;
  extractedFields: Record<string, any>;
}

export type DocumentRiskEntry = SharedDocumentRiskEntry;

export type ValidationAnalytics = SharedStructuredResultAnalytics;

export type StructuredResultDocument = SharedStructuredResultDocument;

export type StructuredResultIssue = SharedStructuredResultIssue;

export type TimelineEvent = SharedTimelineEntry;

export type StructuredResultAnalytics = SharedStructuredResultAnalytics;

export type StructuredResultPayload = SharedStructuredResultPayload;

export interface ValidationResults {
  jobId: string;
  summary: ProcessingSummaryPayload;
  documents: ValidationDocument[];
  issues: IssueCard[];
  analytics: ValidationAnalytics;
  timeline: TimelineEvent[];
  structured_result: OptionEStructuredResult;
  lc_structured?: Record<string, any> | null;
  ai_enrichment?: AIEnrichmentPayload | null;
  telemetry?: Record<string, unknown>;
  reference_issues?: ReferenceIssue[];
}
