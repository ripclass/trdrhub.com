import type {
  StructuredResult as SharedStructuredResultPayload,
  StructuredResultDocument as SharedStructuredResultDocument,
  StructuredResultIssue as SharedStructuredResultIssue,
  StructuredResultAnalytics as SharedStructuredResultAnalytics,
  StructuredProcessingSummary as SharedProcessingSummary,
  SeverityBreakdown as SharedSeverityBreakdown,
  TimelineEntry as SharedTimelineEntry,
  DocumentRiskEntry as SharedDocumentRiskEntry,
  // New schema-first types from shared-types
  IssueCard as SharedIssueCard,
  ReferenceIssue as SharedReferenceIssue,
  AIEnrichmentPayload as SharedAIEnrichmentPayload,
  GateResult as SharedGateResult,
  ExtractionSummary as SharedExtractionSummary,
  LCBaseline as SharedLCBaseline,
  SanctionsScreeningIssue as SharedSanctionsScreeningIssue,
  SanctionsScreeningSummary as SharedSanctionsScreeningSummary,
  ValidationDocument as SharedValidationDocument,
  ValidationResults as SharedValidationResults,
  ToleranceApplied as SharedToleranceApplied,
} from '@shared/types';

// Re-export schema-first types for use across the app
// These are now the source of truth from shared-types
export type {
  SharedIssueCard,
  SharedReferenceIssue,
  SharedAIEnrichmentPayload,
  SharedGateResult,
  SharedExtractionSummary,
  SharedLCBaseline,
  SharedSanctionsScreeningIssue,
  SharedSanctionsScreeningSummary,
  SharedValidationDocument,
  SharedValidationResults,
  SharedToleranceApplied,
};

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

// V2 Validation Pipeline Types - now using schema-first shared types
export type GateResult = SharedGateResult;
export type ExtractionSummary = SharedExtractionSummary;

export type LCBaseline = SharedLCBaseline;

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

// Use schema-first types from shared-types package
// These are now validated with Zod schemas at runtime
export type IssueCard = SharedIssueCard;
export type ReferenceIssue = SharedReferenceIssue;
export type AIEnrichmentPayload = SharedAIEnrichmentPayload;

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

// Sanctions Screening Types - now using schema-first shared types
export type SanctionsScreeningIssue = SharedSanctionsScreeningIssue;
export type SanctionsScreeningSummary = SharedSanctionsScreeningSummary;

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
