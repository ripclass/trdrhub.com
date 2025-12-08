/**
 * SME Validation Response Contract
 * 
 * THE LAW: Backend MUST produce this. Frontend MUST consume this.
 * 
 * This contract defines exactly what an SME/Corporation user sees
 * after uploading their LC document set for validation.
 * 
 * @version 2.0
 * @date 2024-12-07
 */

// ============================================
// VERDICT STATUS
// ============================================
export type VerdictStatus = 
  | "PASS"           // All good, ready to submit
  | "FIX_REQUIRED"   // Has issues that need fixing
  | "LIKELY_REJECT"  // Critical issues, bank will likely reject
  | "MISSING_DOCS";  // Required documents not uploaded

export type RiskLevel = "low" | "medium" | "high";
export type Severity = "critical" | "major" | "minor";

// ============================================
// LC SUMMARY (Header Info)
// ============================================
export interface LCSummary {
  number: string;              // "EXP2026BD001"
  amount: number;              // 450000
  currency: string;            // "USD"
  beneficiary: string;         // "Bangladesh Garments Ltd"
  applicant: string;           // "Global Importers Inc"
  expiry_date: string;         // "2026-03-15" (ISO date)
  days_until_expiry: number;   // 45 (negative if expired)
  issuing_bank?: string;       // "ICBC Shanghai"
}

// ============================================
// VERDICT (The Big Answer)
// ============================================
export interface Verdict {
  status: VerdictStatus;
  
  headline: string;
  // Examples:
  // "READY TO SUBMIT"
  // "FIX 3 ISSUES BEFORE SUBMITTING"
  // "UPLOAD 2 MISSING DOCUMENTS"
  // "LIKELY TO BE REJECTED"
  
  subtext: string;
  // Examples:
  // "Your documents appear compliant with LC terms."
  // "Bank will likely REJECT your documents. Fix these issues to avoid $75+ discrepancy fee."
  // "Required documents are missing. Upload them to continue."
  
  estimated_risk: RiskLevel;
  estimated_fee_if_rejected: number;  // 75.00
  
  // Summary counts
  total_issues: number;
  critical_count: number;
  major_count: number;
  minor_count: number;
  missing_docs_count: number;
}

// ============================================
// ISSUE (Single Problem)
// ============================================
export interface SMEIssue {
  id: string;                    // "CROSSDOC-AMOUNT-1" or "ISSUE-001"
  
  // What's wrong (plain English title)
  title: string;                 // "Invoice Amount Exceeds LC"
  
  // Severity
  severity: Severity;
  
  // The actual discrepancy
  your_document: string;         // "USD 458,750.00"
  lc_requires: string;           // "USD 450,000.00"
  difference?: string;           // "Over by USD 8,750.00 (1.9%)"
  
  // Which document has the problem
  document_type: string;         // "commercial_invoice"
  document_name: string;         // "Commercial Invoice"
  affected_documents?: string[]; // ["Invoice", "B/L"] for multi-doc issues
  
  // How to fix it (actionable steps)
  how_to_fix: string[];
  // Examples:
  // ["Request corrected invoice from supplier (recommended)",
  //  "OR request LC amendment to increase amount"]
  
  // Why banks care (educational)
  why_banks_reject: string;
  // "UCP600 Article 18(c) - Invoice amount cannot exceed LC amount"
  
  // UCP/ISBP references
  ucp_article?: string;          // "18(c)"
  isbp_reference?: string;       // "C1"
  lc_clause?: string;            // "47A(6)"
  
  // Tolerance info (if applicable)
  tolerance?: {
    applicable: boolean;
    type: string;                // "5% quantity tolerance"
    within_tolerance: boolean;
    tolerance_amount?: string;   // "±5%"
  };
}

// ============================================
// DOCUMENT STATUS
// ============================================
export interface SMEDocument {
  type: string;                  // "letter_of_credit"
  name: string;                  // "Letter of Credit"
  filename?: string;             // "LC.pdf"
  status: "verified" | "has_issues";
  status_note: string;           // "All required fields present"
  issues_count: number;          // 0
  extraction_confidence?: number; // 0.95
}

export interface SMEMissingDoc {
  type: string;                  // "inspection_certificate"
  name: string;                  // "Inspection Certificate"
  required_by: string;           // "LC clause 46A-5"
  description?: string;          // "Third-party inspection certificate"
  accepted_issuers?: string[];   // ["SGS", "Intertek", "Bureau Veritas"]
}

// ============================================
// ISSUES GROUPED
// ============================================
export interface IssuesGrouped {
  must_fix: SMEIssue[];          // 🔴 critical + major - Will cause rejection
  should_fix: SMEIssue[];        // 🟡 minor - May cause rejection
  // Note: "optional" removed - if it's optional, don't show it
}

// ============================================
// DOCUMENTS GROUPED
// ============================================
export interface DocumentsGrouped {
  good: SMEDocument[];           // ✅ No issues found
  has_issues: SMEDocument[];     // ⚠️ Has fixable issues
  missing: SMEMissingDoc[];      // ❌ Required but not uploaded
}

// ============================================
// PROCESSING METADATA
// ============================================
export interface ProcessingMeta {
  session_id: string;
  processed_at: string;          // ISO timestamp
  processing_time_seconds: number;
  processing_time_display: string; // "35.6 seconds"
  documents_checked: number;
  rules_executed: number;
}

// ============================================
// THE COMPLETE RESPONSE
// ============================================
export interface SMEValidationResponse {
  // Version for future compatibility
  version: "2.0";
  
  // LC Header Info
  lc_summary: LCSummary;
  
  // The Big Answer
  verdict: Verdict;
  
  // Issues (grouped by severity)
  issues: IssuesGrouped;
  
  // Document Status (grouped)
  documents: DocumentsGrouped;
  
  // Metadata
  processing: ProcessingMeta;
}

// ============================================
// HELPER TYPE GUARDS
// ============================================
export function isPassVerdict(verdict: Verdict): boolean {
  return verdict.status === "PASS";
}

export function hasIssues(response: SMEValidationResponse): boolean {
  return response.issues.must_fix.length > 0 || response.issues.should_fix.length > 0;
}

export function hasMissingDocs(response: SMEValidationResponse): boolean {
  return response.documents.missing.length > 0;
}

export function canSubmit(response: SMEValidationResponse): boolean {
  return response.verdict.status === "PASS" || 
         (response.verdict.status === "FIX_REQUIRED" && response.verdict.critical_count === 0);
}
