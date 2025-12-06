/**
 * LCopilot V2 - Shared Types
 * 
 * Source of truth for all V2 API contracts.
 * Both backend (Python) and frontend (TypeScript) use these types.
 * 
 * Target: <30 seconds, 99% accuracy
 */

import { z } from 'zod';

// ============================================================================
// DOCUMENT TYPES
// ============================================================================

export const DocumentTypeSchema = z.enum([
  'letter_of_credit',
  'mt700',
  'commercial_invoice',
  'bill_of_lading',
  'packing_list',
  'insurance_certificate',
  'certificate_of_origin',
  'inspection_certificate',
  'weight_certificate',
  'fumigation_certificate',
  'phytosanitary_certificate',
  'beneficiary_certificate',
  'draft',
  'unknown',
]);
export type DocumentType = z.infer<typeof DocumentTypeSchema>;

export const DocumentQualitySchema = z.enum(['excellent', 'good', 'medium', 'poor', 'very_poor']);
export type DocumentQuality = z.infer<typeof DocumentQualitySchema>;

// ============================================================================
// PAGE REGIONS (For handwriting, stamps, signatures)
// ============================================================================

export const RegionTypeSchema = z.enum([
  'text',
  'table',
  'handwriting',
  'signature',
  'stamp',
  'logo',
  'barcode',
  'qr_code',
]);
export type RegionType = z.infer<typeof RegionTypeSchema>;

export const PageRegionSchema = z.object({
  type: RegionTypeSchema,
  bounds: z.object({
    x: z.number(),
    y: z.number(),
    width: z.number(),
    height: z.number(),
  }),
  content: z.string().nullable(),
  confidence: z.number().min(0).max(1),
  pageNumber: z.number(),
});
export type PageRegion = z.infer<typeof PageRegionSchema>;

// ============================================================================
// EXTRACTED FIELDS
// ============================================================================

export const FieldConfidenceSchema = z.object({
  value: z.any(),
  confidence: z.number().min(0).max(1),
  source: z.string(), // 'ensemble', 'gpt', 'claude', 'gemini'
  providerAgreement: z.number().min(0).max(1), // 0.33, 0.66, 1.0
  needsReview: z.boolean(),
  alternatives: z.array(z.any()).optional(),
  reviewReason: z.string().optional(),
});
export type FieldConfidence = z.infer<typeof FieldConfidenceSchema>;

export const ExtractedFieldsSchema = z.record(z.string(), FieldConfidenceSchema);
export type ExtractedFields = z.infer<typeof ExtractedFieldsSchema>;

// ============================================================================
// CITATIONS (The key differentiator)
// ============================================================================

export const CitationsSchema = z.object({
  ucp600: z.array(z.string()).optional(), // ["Article 14(a)", "Article 14(d)"]
  isbp745: z.array(z.string()).optional(), // ["Paragraph 72", "Paragraph 73(a)"]
  urc522: z.array(z.string()).optional(),
  urr725: z.array(z.string()).optional(),
  swift: z.array(z.string()).optional(), // ["MT700 Field 45A"]
});
export type Citations = z.infer<typeof CitationsSchema>;

// ============================================================================
// ISSUES
// ============================================================================

export const IssueSeveritySchema = z.enum(['critical', 'major', 'minor', 'info']);
export type IssueSeverity = z.infer<typeof IssueSeveritySchema>;

export const IssueSchema = z.object({
  id: z.string(),
  ruleId: z.string(),
  title: z.string(),
  severity: IssueSeveritySchema,
  
  // REQUIRED - Always include citations
  citations: CitationsSchema,
  
  // Bank-readable message
  bankMessage: z.string(),
  
  // User-friendly explanation
  explanation: z.string(),
  
  // Structured discrepancy
  expected: z.string(),
  found: z.string(),
  suggestion: z.string(),
  
  // Source documents
  documents: z.array(z.string()),
  documentIds: z.array(z.string()),
  
  // Amendment info
  canAmend: z.boolean(),
  amendmentCost: z.number().optional(),
  amendmentDays: z.number().optional(),
  
  // Confidence
  confidence: z.number().min(0).max(1),
});
export type Issue = z.infer<typeof IssueSchema>;

// ============================================================================
// VERDICT
// ============================================================================

export const VerdictStatusSchema = z.enum(['SUBMIT', 'CAUTION', 'HOLD', 'REJECT']);
export type VerdictStatus = z.infer<typeof VerdictStatusSchema>;

export const VerdictSchema = z.object({
  status: VerdictStatusSchema,
  message: z.string(),
  recommendation: z.string(),
  confidence: z.number().min(0).max(1),
  canSubmitToBank: z.boolean(),
  willBeRejected: z.boolean(),
  estimatedDiscrepancyFee: z.number(),
  
  issueSummary: z.object({
    critical: z.number(),
    major: z.number(),
    minor: z.number(),
    info: z.number(),
    total: z.number(),
  }),
  
  actionItems: z.array(z.object({
    priority: z.enum(['critical', 'high', 'medium', 'low']),
    issue: z.string(),
    action: z.string(),
  })),
});
export type Verdict = z.infer<typeof VerdictSchema>;

// ============================================================================
// AMENDMENTS
// ============================================================================

export const AmendmentSchema = z.object({
  id: z.string(),
  issueId: z.string(),
  field: z.object({
    tag: z.string(),
    name: z.string(),
    current: z.string(),
    proposed: z.string(),
  }),
  
  // SWIFT formats
  mt707Text: z.string(),
  iso20022Xml: z.string().optional(),
  
  narrative: z.string(),
  estimatedFeeUsd: z.number(),
  processingDays: z.number(),
  formatsAvailable: z.array(z.string()),
});
export type Amendment = z.infer<typeof AmendmentSchema>;

// ============================================================================
// DOCUMENT RESULT
// ============================================================================

export const DocumentResultSchema = z.object({
  id: z.string(),
  filename: z.string(),
  documentType: DocumentTypeSchema,
  
  // Quality metrics
  quality: z.object({
    overall: z.number().min(0).max(1),
    ocrConfidence: z.number().min(0).max(1),
    category: DocumentQualitySchema,
  }),
  
  // Detected regions
  regions: z.object({
    hasHandwriting: z.boolean(),
    hasSignatures: z.boolean(),
    hasStamps: z.boolean(),
    handwritingCount: z.number(),
    signatureCount: z.number(),
    stampCount: z.number(),
    details: z.array(PageRegionSchema).optional(),
  }),
  
  // Extraction result
  extracted: ExtractedFieldsSchema,
  
  // Processing metrics
  processingTimeMs: z.number(),
  pagesProcessed: z.number(),
  
  // Status
  status: z.enum(['success', 'partial', 'failed']),
  errors: z.array(z.string()).optional(),
});
export type DocumentResult = z.infer<typeof DocumentResultSchema>;

// ============================================================================
// SANCTIONS STATUS
// ============================================================================

export const SanctionsStatusSchema = z.object({
  screened: z.boolean(),
  partiesScreened: z.number(),
  matchesFound: z.number(),
  status: z.enum(['clear', 'potential_match', 'match', 'blocked']),
  
  matches: z.array(z.object({
    party: z.string(),
    partyType: z.string(),
    listName: z.string(),
    matchScore: z.number(),
    matchType: z.enum(['exact', 'fuzzy', 'alias']),
    sanctionPrograms: z.array(z.string()),
  })).optional(),
});
export type SanctionsStatus = z.infer<typeof SanctionsStatusSchema>;

// ============================================================================
// MAIN RESPONSE
// ============================================================================

export const LCopilotV2ResponseSchema = z.object({
  // Session info
  sessionId: z.string(),
  version: z.literal('v2'),
  processingTimeSeconds: z.number(),
  
  // Main verdict
  verdict: VerdictSchema,
  
  // Documents
  documents: z.array(DocumentResultSchema),
  
  // Issues with citations (THE KEY FEATURE)
  issues: z.array(IssueSchema),
  
  // Amendments
  amendments: z.array(AmendmentSchema),
  
  // Extracted data (unified)
  extractedData: z.object({
    lc: ExtractedFieldsSchema.optional(),
    invoice: ExtractedFieldsSchema.optional(),
    billOfLading: ExtractedFieldsSchema.optional(),
    packingList: ExtractedFieldsSchema.optional(),
    insurance: ExtractedFieldsSchema.optional(),
    certificateOfOrigin: ExtractedFieldsSchema.optional(),
  }),
  
  // Compliance
  compliance: z.object({
    sanctionsStatus: SanctionsStatusSchema,
    ucpCompliance: z.number().min(0).max(100),
    isbpCompliance: z.number().min(0).max(100),
    overallScore: z.number().min(0).max(100),
  }),
  
  // Quality metrics
  quality: z.object({
    overallConfidence: z.number().min(0).max(1),
    fieldsNeedingReview: z.array(z.string()),
    poorQualityDocuments: z.array(z.string()),
    handwritingDetected: z.boolean(),
    providersUsed: z.array(z.string()),
  }),
  
  // Audit
  audit: z.object({
    rulesEvaluated: z.number(),
    rulesPassed: z.number(),
    rulesFailed: z.number(),
    crossDocChecks: z.number(),
    aiProvidersUsed: z.array(z.string()),
  }),
});
export type LCopilotV2Response = z.infer<typeof LCopilotV2ResponseSchema>;

// ============================================================================
// REQUEST
// ============================================================================

export const LCopilotV2RequestSchema = z.object({
  // Files are sent as multipart, this is for metadata
  documentTags: z.record(z.string(), DocumentTypeSchema).optional(),
  lcNumber: z.string().optional(),
  userType: z.enum(['exporter', 'importer', 'bank']).optional(),
  
  // Options
  options: z.object({
    ensembleMode: z.enum(['full', 'smart', 'fast']).optional(),
    includeAmendments: z.boolean().optional(),
    strictMode: z.boolean().optional(),
    bankProfile: z.string().optional(),
  }).optional(),
});
export type LCopilotV2Request = z.infer<typeof LCopilotV2RequestSchema>;

// ============================================================================
// HELPERS
// ============================================================================

export function formatCitation(citations: Citations): string {
  const parts: string[] = [];
  
  if (citations.ucp600?.length) {
    parts.push(`UCP600 ${citations.ucp600.join(', ')}`);
  }
  if (citations.isbp745?.length) {
    parts.push(`ISBP745 ${citations.isbp745.join(', ')}`);
  }
  if (citations.urc522?.length) {
    parts.push(`URC522 ${citations.urc522.join(', ')}`);
  }
  if (citations.swift?.length) {
    parts.push(`SWIFT ${citations.swift.join(', ')}`);
  }
  
  return parts.join('; ');
}

export function formatBankMessage(issue: Issue): string {
  const citationStr = formatCitation(issue.citations);
  if (citationStr) {
    return `${issue.title}. Per ${citationStr}.`;
  }
  return issue.title;
}

export const DEFAULT_CITATIONS: Citations = {
  ucp600: [],
  isbp745: [],
};

