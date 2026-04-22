/**
 * Moment configuration for <ImporterValidationPage />.
 *
 * Two routes, one component, two bundles of copy + accepted doc types.
 * The workflowType field flows through to the backend and lands on
 * ValidationSession.workflow_type; nothing else about the pipeline
 * changes between moments.
 */

export type ImporterMoment = "draft_lc" | "supplier_docs";

export type ImporterWorkflowType =
  | "importer_draft_lc"
  | "importer_supplier_docs";

export interface ImporterMomentConfig {
  moment: ImporterMoment;
  workflowType: ImporterWorkflowType;
  pageTitle: string;
  pageDescription: string;
  ctaLabel: string;
  acceptedDocTypes: { value: string; label: string }[];
  requiredDocsFraming: "informational" | "checklist";
}

const DRAFT_LC_DOC_TYPES = [
  { value: "lc", label: "Draft LC (PDF)" },
  { value: "swift", label: "SWIFT Message" },
  { value: "application", label: "LC Application Form" },
  { value: "proforma", label: "Proforma Invoice" },
  { value: "other", label: "Other Document" },
];

const SUPPLIER_DOC_TYPES = [
  { value: "lc", label: "Issued LC" },
  { value: "invoice", label: "Commercial Invoice" },
  { value: "packing", label: "Packing List" },
  { value: "bill_of_lading", label: "Bill of Lading" },
  { value: "certificate_origin", label: "Certificate of Origin" },
  { value: "insurance", label: "Insurance Certificate" },
  { value: "inspection", label: "Inspection Certificate" },
  { value: "beneficiary", label: "Beneficiary Certificate" },
  { value: "other", label: "Other Trade Document" },
];

export const IMPORTER_MOMENTS: Record<ImporterMoment, ImporterMomentConfig> = {
  draft_lc: {
    moment: "draft_lc",
    workflowType: "importer_draft_lc",
    pageTitle: "Draft LC Risk Analysis",
    pageDescription:
      "Upload the draft LC your bank has proposed. We'll surface risky clauses and unusual terms you may want to amend before issuance.",
    ctaLabel: "Analyze LC Risks",
    acceptedDocTypes: DRAFT_LC_DOC_TYPES,
    requiredDocsFraming: "informational",
  },
  supplier_docs: {
    moment: "supplier_docs",
    workflowType: "importer_supplier_docs",
    pageTitle: "Supplier Document Review",
    pageDescription:
      "Upload the issued LC plus the shipping documents your supplier presented. We'll flag discrepancies before you authorize payment.",
    ctaLabel: "Review Supplier Documents",
    acceptedDocTypes: SUPPLIER_DOC_TYPES,
    requiredDocsFraming: "checklist",
  },
};
