import type {
  StructuredResult as SharedStructuredResultPayload,
  StructuredResultDocument as SharedStructuredResultDocument,
  StructuredResultIssue as SharedStructuredResultIssue,
  StructuredResultAnalytics as SharedStructuredResultAnalytics,
  StructuredProcessingSummary as SharedProcessingSummary,
  ProcessingSummaryV2 as SharedProcessingSummaryV2,
  DocumentExtractionV1 as SharedDocumentExtractionV1,
  IssueProvenanceV1 as SharedIssueProvenanceV1,
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
  ValidationContractV1 as SharedValidationContractV1,
  SubmissionEligibility as SharedSubmissionEligibility,
  BankVerdict as SharedBankVerdict,
  BankProfile as SharedBankProfile,
  AmendmentsAvailable as SharedAmendmentsAvailable,
  ContractWarning as SharedContractWarning,
  ContractValidation as SharedContractValidation,
  ExtractionFieldDetail as SharedExtractionFieldDetail,
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
  SharedValidationContractV1,
  SharedSubmissionEligibility,
  SharedBankVerdict,
  SharedBankProfile,
  SharedAmendmentsAvailable,
  SharedContractWarning,
  SharedContractValidation,
};

export type OptionEDocument = {
  document_id: string;
  document_type: string;
  filename: string;
  extraction_status?: string | null;
  extracted_fields?: Record<string, unknown>;
  field_details?: Record<string, SharedExtractionFieldDetail>;
  fieldDetails?: Record<string, SharedExtractionFieldDetail>;
  issues_count?: number;
};

export type LcClassificationRequiredDocument = {
  code: string;
  display_name?: string;
  category?: string;
  raw_text?: string;
  aliases_matched?: string[];
  originals?: number | null;
  copies?: number | null;
  signed?: boolean | null;
  negotiable?: boolean | null;
  issuer?: string | null;
  exact_wording?: string | null;
  legalized?: boolean | null;
  transport_mode?: string | null;
  detection_source?: string;
  confidence?: number;
  evidence?: string[];
};

export type LcClassificationAttributes = {
  revocability?: string;
  availability?: string;
  available_with_scope?: string;
  confirmation?: string;
  transferability?: string;
  assignment_of_proceeds?: string;
  revolving?: string;
  revolving_mode?: string | null;
  red_clause?: string;
  green_clause?: string;
  back_to_back?: string;
  documentation_basis?: string;
  partial_shipments?: string;
  transshipment?: string;
  latest_shipment_date?: string | null;
  expiry_date?: string | null;
  expiry_place?: string | null;
  presentation_period_days?: number | null;
  tenor_kind?: string;
  tenor_days?: number | null;
  tolerance_min_pct?: number | null;
  tolerance_max_pct?: number | null;
  reimbursement_present?: string;
};

export type LcClassification = {
  format_family?: string;
  format_variant?: string;
  embedded_variant?: string | null;
  instrument_type?: string;
  workflow_orientation?: string;
  applicable_rules?: string;
  attributes?: LcClassificationAttributes;
  required_documents?: LcClassificationRequiredDocument[];
  requirement_conditions?: string[];
  unmapped_requirements?: string[];
};

export type OptionELCStructured = {
  mt700?: {
    blocks?: Record<string, string | null>;
    raw_text?: string | null;
    version?: string;
  };
  goods?: Array<Record<string, unknown>>;
  clauses?: Array<Record<string, unknown>>;
  documents_required?: string[] | string;
  required_document_types?: string[];
  required_documents_detailed?: LcClassificationRequiredDocument[];
  requirement_conditions?: string[];
  unmapped_requirements?: string[];
  additional_conditions?: string[] | string;
  lc_type?: string | null;
  lc_type_reason?: string | null;
  lc_type_confidence?: number | null;
  lc_type_source?: string | null;
  lc_classification?: LcClassification | null;
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

  // Phase A contracts (canonical metrics)
  processing_summary_v2?: ProcessingSummaryV2 | null;
  document_extraction_v1?: DocumentExtractionV1 | null;
  issue_provenance_v1?: IssueProvenanceV1 | null;
  
  // V2 Validation Pipeline fields
  validation_blocked?: boolean;
  validation_status?: 'pass' | 'blocked' | 'non_compliant' | 'partial' | 'mostly_compliant' | 'compliant';
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
  validation_contract_v1?: ValidationContractV1 | null;
  submission_eligibility?: SubmissionEligibility | null;
  raw_submission_eligibility?: SubmissionEligibility | null;
  effective_submission_eligibility?: SubmissionEligibility | null;
  bank_verdict?: StructuredResultBankVerdict | null;
  bank_profile?: StructuredResultBankProfile | null;
  amendments_available?: StructuredResultAmendmentsAvailable | null;
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
export type ProcessingSummaryV2 = SharedProcessingSummaryV2;
export type DocumentExtractionV1 = SharedDocumentExtractionV1;
export type IssueProvenanceV1 = SharedIssueProvenanceV1;

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
  fieldDetails?: Record<string, SharedExtractionFieldDetail>;
  missingRequiredFields?: string[];
  requiredFieldsFound?: number;
  requiredFieldsTotal?: number;
  requirementStatus?: 'matched' | 'partial' | 'missing';
  reviewRequired?: boolean;
  reviewState?: 'ready' | 'needs_review' | 'blocked';
  reviewReasons?: string[];
  criticalFieldStates?: Record<string, string>;
  extractionResolution?: {
    required: boolean;
    unresolvedCount: number;
    summary: string;
    fields: Array<{
      fieldName: string;
      label: string;
      verification?: string;
    }>;
  };
}

export type DocumentRiskEntry = SharedDocumentRiskEntry;

export type ValidationAnalytics = SharedStructuredResultAnalytics;

export type StructuredResultDocument = SharedStructuredResultDocument;

export type StructuredResultIssue = SharedStructuredResultIssue;

export type TimelineEvent = SharedTimelineEntry;

export type StructuredResultAnalytics = SharedStructuredResultAnalytics;

export type StructuredResultPayload = SharedStructuredResultPayload;
export type ValidationContractV1 = SharedValidationContractV1;
export type SubmissionEligibility = SharedSubmissionEligibility;
export type StructuredResultBankVerdict = SharedBankVerdict;
export type StructuredResultBankProfile = SharedBankProfile;
export type StructuredResultAmendmentsAvailable = SharedAmendmentsAvailable;

// Sanctions Screening Types - now using schema-first shared types
export type SanctionsScreeningIssue = SharedSanctionsScreeningIssue;
export type SanctionsScreeningSummary = SharedSanctionsScreeningSummary;

// Contract Validation Types (Output-First layer)
export type ContractWarningSeverity = 'error' | 'warning' | 'info';

export type ContractWarning = SharedContractWarning & {
  severity: ContractWarningSeverity;
};

export type ContractValidation = SharedContractValidation;

export interface ValidationResults {
  jobId: string;
  job_id?: string;
  validation_session_id?: string;
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
  
  // Contract Validation additions (Output-First layer)
  contractWarnings?: ContractWarning[];
  contractValidation?: ContractValidation | null;
}
