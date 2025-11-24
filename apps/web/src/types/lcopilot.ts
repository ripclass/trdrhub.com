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
  structured_result: StructuredResultPayload;
  lc_structured?: Record<string, any> | null;
  ai_enrichment?: AIEnrichmentPayload | null;
}
