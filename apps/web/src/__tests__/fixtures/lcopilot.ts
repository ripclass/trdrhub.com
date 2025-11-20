import type { StructuredResultPayload, ValidationResults } from '@/types/lcopilot';

const severityBreakdown = {
  critical: 1,
  major: 1,
  medium: 1,
  minor: 0,
};

const summary = {
  total_documents: 6,
  successful_extractions: 5,
  failed_extractions: 1,
  total_issues: 3,
  severity_breakdown: severityBreakdown,
};

const documents = [
  {
    id: 'doc-lc',
    documentId: 'doc-lc',
    name: 'LC.pdf',
    filename: 'LC.pdf',
    type: 'Letter of Credit',
    typeKey: 'letter_of_credit',
    extractionStatus: 'success',
    status: 'success',
    issuesCount: 1,
    extractedFields: { amount: '50000 USD' },
  },
  {
    id: 'doc-invoice',
    documentId: 'doc-invoice',
    name: 'Invoice.pdf',
    filename: 'Invoice.pdf',
    type: 'Commercial Invoice',
    typeKey: 'commercial_invoice',
    extractionStatus: 'success',
    status: 'warning',
    issuesCount: 1,
    extractedFields: { goods_description: 'Cotton shirts' },
  },
  {
    id: 'doc-bl',
    documentId: 'doc-bl',
    name: 'BL.pdf',
    filename: 'BL.pdf',
    type: 'Bill of Lading',
    typeKey: 'bill_of_lading',
    extractionStatus: 'success',
    status: 'success',
    issuesCount: 0,
    extractedFields: { vessel: 'MV Compliance' },
  },
  {
    id: 'doc-pack',
    documentId: 'doc-pack',
    name: 'Packing.pdf',
    filename: 'Packing.pdf',
    type: 'Packing List',
    typeKey: 'packing_list',
    extractionStatus: 'partial',
    status: 'warning',
    issuesCount: 0,
    extractedFields: { quantity: '100 cartons' },
  },
  {
    id: 'doc-coo',
    documentId: 'doc-coo',
    name: 'COO.pdf',
    filename: 'COO.pdf',
    type: 'Certificate Of Origin',
    typeKey: 'certificate_of_origin',
    extractionStatus: 'success',
    status: 'success',
    issuesCount: 0,
    extractedFields: { origin_country: 'Bangladesh' },
  },
  {
    id: 'doc-insurance',
    documentId: 'doc-insurance',
    name: 'Insurance.pdf',
    filename: 'Insurance.pdf',
    type: 'Insurance Certificate',
    typeKey: 'insurance_certificate',
    extractionStatus: 'success',
    status: 'success',
    issuesCount: 1,
    extractedFields: { insured_value: '50000 USD' },
  },
];

const issues = [
  {
    id: 'issue-1',
    title: 'Amount mismatch',
    description: 'Invoice does not match LC amount',
    severity: 'critical',
    documents: ['Invoice.pdf', 'LC.pdf'],
    expected: '50000 USD',
    actual: '49000 USD',
    suggestion: 'Align invoice amount',
    ucpReference: 'UCP 600',
  },
  {
    id: 'issue-2',
    title: 'Product description mismatch',
    description: 'Invoice description is too generic',
    severity: 'major',
    documents: ['Invoice.pdf', 'LC.pdf'],
    expected: 'Cotton shirts',
    actual: 'Apparel',
    suggestion: 'Update invoice',
  },
  {
    id: 'issue-3',
    title: 'Insurance not covering full LC value',
    description: 'Policy is under-insured',
    severity: 'medium',
    documents: ['Insurance.pdf'],
    expected: '110% of LC value',
    actual: '90% of LC value',
    suggestion: 'Extend policy coverage',
  },
];

const analytics = {
  compliance_score: 82,
  issue_counts: severityBreakdown,
  document_risk: [
    { document_id: 'doc-lc', filename: 'LC.pdf', risk: 'medium' },
    { document_id: 'doc-invoice', filename: 'Invoice.pdf', risk: 'high' },
    { document_id: 'doc-insurance', filename: 'Insurance.pdf', risk: 'medium' },
  ],
};

const timeline = [
  { label: 'Upload Received', status: 'complete' },
  { label: 'OCR Complete', status: 'complete' },
  { label: 'Deterministic Rules', status: 'complete' },
  { label: 'Issue Review Ready', status: 'complete' },
];

const aiInsightsText = 'Detected misalignment in amount and insurance coverage.';

const extractedDocumentsSnapshot = {
  letter_of_credit: {
    number: 'LC-EXP-2025',
    amount: { value: '50000', currency: 'USD' },
    applicant: { name: 'Global Importers', country: 'United States' },
    beneficiary: { name: 'Dhaka Knitwear', country: 'Bangladesh' },
    ports: { loading: 'Chittagong, Bangladesh', discharge: 'New York, United States' },
    goods_description: '100% cotton knit shirts',
  },
  commercial_invoice: {
    invoice_number: 'INV-22-001',
    goods_description: 'Cotton shirts',
    invoice_amount: { value: '50000', currency: 'USD' },
  },
  bill_of_lading: {
    vessel: 'MV Compliance',
    bl_number: 'BOL-55-XYZ',
  },
};

const structuredResult: StructuredResultPayload = {
  processing_summary: summary,
  documents: documents.map((doc) => ({
    document_id: doc.documentId,
    document_type: doc.typeKey ?? doc.type,
    filename: doc.filename,
    extraction_status: doc.extractionStatus,
    extracted_fields: doc.extractedFields,
    issues_count: doc.issuesCount,
  })),
  issues: issues.map((issue) => ({
    id: issue.id,
    title: issue.title,
    severity: issue.severity,
    documents: issue.documents ?? [],
    expected: issue.expected ?? '',
    found: issue.found ?? '',
    suggested_fix: issue.suggested_fix ?? '',
    description: issue.description,
    ucp_reference: issue.ucpReference,
  })),
  analytics: {
    compliance_score: analytics.compliance_score,
    issue_counts: analytics.issue_counts,
    document_risk: analytics.document_risk,
  },
  timeline: timeline.map((entry) => ({
    title: entry.title ?? entry.label ?? 'Milestone',
    label: entry.label ?? entry.title ?? 'Milestone',
    status: entry.status,
    description: entry.description,
    timestamp: entry.timestamp,
  })),
  extracted_documents: extractedDocumentsSnapshot,
};

export const mockValidationResults: ValidationResults = {
  jobId: 'job-123',
  summary,
  documents,
  issues,
  analytics,
  timeline,
  structured_result: structuredResult,
  extracted_data: extractedDocumentsSnapshot,
  reference_issues: [],
  ai_enrichment: {
    summary: aiInsightsText,
    suggestions: ['Review invoice amount', 'Extend insurance policy'],
  },
};

export const buildValidationResults = (
  overrides: Partial<ValidationResults> = {},
): ValidationResults => {
  const clone = JSON.parse(JSON.stringify(mockValidationResults)) as ValidationResults;
  return {
    ...clone,
    ...overrides,
    documents: overrides.documents ?? clone.documents,
    issues: overrides.issues ?? clone.issues,
    analytics: overrides.analytics ?? clone.analytics,
    timeline: overrides.timeline ?? clone.timeline,
    structured_result: overrides.structured_result ?? clone.structured_result,
    summary: overrides.summary ?? clone.summary,
  };
};
