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

// V2 Validation Pipeline Types
export interface GateResult {
  status: 'passed' | 'blocked' | 'warning';
  can_proceed: boolean;
  block_reason?: string | null;
  completeness: number; // 0-100 percentage
  critical_completeness: number; // 0-100 percentage
  missing_critical: string[];
  missing_required?: string[];
  blocking_issues?: Array<Record<string, unknown>>;
  warning_issues?: Array<Record<string, unknown>>;
}

export interface ExtractionSummary {
  completeness: number; // 0-100 percentage
  critical_completeness: number; // 0-100 percentage
  missing_critical: string[];
  missing_required?: string[];
  total_fields?: number;
  extracted_fields?: number;
}

export interface LCBaseline {
  lc_number?: string | null;
  lc_type?: string | null;
  applicant?: string | null;
  beneficiary?: string | null;
  issuing_bank?: string | null;
  advising_bank?: string | null;
  amount?: string | null;
  currency?: string | null;
  expiry_date?: string | null;
  issue_date?: string | null;
  latest_shipment?: string | null;
  port_of_loading?: string | null;
  port_of_discharge?: string | null;
  goods_description?: string | null;
  incoterm?: string | null;
  extraction_completeness: number;
  critical_completeness: number;
}

export type OptionEStructuredResult = StructuredResultPayload & {
  version: 'structured_result_v1';
  
  // V2 Validation Pipeline fields
  validation_blocked?: boolean;
  validation_status?: 'blocked' | 'non_compliant' | 'partial' | 'mostly_compliant' | 'compliant';
  gate_result?: GateResult | null;
  extraction_summary?: ExtractionSummary | null;
  lc_baseline?: LCBaseline | null;
  
  // LC Type detection
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
    compliance_level?: string;
    compliance_cap_reason?: string | null;
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
  
  // Audit
  audit_trail_id?: string | null;
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
  ruleset_domain?: string;
  auto_generated?: boolean;
  isbpReference?: string;
  // Tolerance and confidence metadata
  tolerance_applied?: {
    tolerance_percent: number;
    source: string;
    explicit: boolean;
  };
  extraction_confidence?: number;
  amendment_available?: boolean;
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

// Sanctions Screening Types
export interface SanctionsScreeningIssue {
  party: string | null;
  type: string | null;
  status: 'match' | 'potential_match' | 'clear';
  score: number | null;
}

export interface SanctionsScreeningSummary {
  screened: boolean;
  parties_screened: number;
  matches: number;
  potential_matches: number;
  clear: number;
  should_block: boolean;
  screened_at: string;
  issues: SanctionsScreeningIssue[];
  error?: string;
}

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
  
  // V2 Validation Pipeline additions
  validationBlocked?: boolean;
  validationStatus?: string;
  gateResult?: GateResult | null;
  extractionSummary?: ExtractionSummary | null;
  lcBaseline?: LCBaseline | null;
  complianceLevel?: string;
  complianceCapReason?: string | null;
  
  // Sanctions Screening additions
  sanctionsScreening?: SanctionsScreeningSummary | null;
  sanctionsBlocked?: boolean;
  sanctionsBlockReason?: string | null;
}
