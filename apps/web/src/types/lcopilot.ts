export interface IssueCard {
  id: string;
  rule?: string;
  title: string;
  description: string;
  severity: string;
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

export interface SeverityBreakdown {
  critical: number;
  major: number;
  medium: number;
  minor: number;
}

export interface ProcessingSummaryPayload {
  total_documents: number;
  successful_extractions: number;
  failed_extractions: number;
  total_issues: number;
  severity_breakdown: SeverityBreakdown;
}

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

export interface DocumentRiskEntry {
  document_id?: string;
  filename?: string;
  risk?: string;
}

export interface ValidationAnalytics {
  compliance_score: number;
  issue_counts: SeverityBreakdown;
  document_risk: DocumentRiskEntry[];
}

export interface TimelineEvent {
  title?: string;
  label?: string;
  status: string;
  description?: string;
  timestamp?: string;
}

export interface ValidationResults {
  jobId: string;
  summary: ProcessingSummaryPayload;
  documents: ValidationDocument[];
  issues: IssueCard[];
  analytics: ValidationAnalytics;
  timeline: TimelineEvent[];
  results?: any[];
  discrepancies?: any[];
  lcNumber?: string;
  completedAt?: string;
  status?: string;
  reference_issues?: ReferenceIssue[];
  ai_enrichment?: AIEnrichmentPayload;
  aiEnrichment?: AIEnrichmentPayload;
  extracted_data?: Record<string, any>;
  extraction_status?: 'success' | 'partial' | 'empty' | 'error' | 'unknown';
  lc_type?: string;
  lc_type_reason?: string;
  lc_type_confidence?: number;
  lc_type_source?: string;
  overallStatus?: 'success' | 'error' | 'warning';
  packGenerated?: boolean;
  processingTime?: string;
  processing_time?: string;
  processingTimeMinutes?: string;
  processedAt?: string;
  processingCompletedAt?: string;
  processed_at?: string;
  processing_summary?: ProcessingSummaryPayload;
  issue_cards?: IssueCard[];
  overall_status?: string;
  structured_result?: {
    processing_summary?: ProcessingSummaryPayload;
    documents?: any[];
    issues?: any[];
    analytics?: any;
    timeline?: any[];
  };
}
