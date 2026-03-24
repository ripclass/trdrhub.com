import type { StructuredResultPayload } from '@shared/types';
import type { ContractWarning, ValidationResults, IssueCard } from '@/types/lcopilot';

const DOC_LABELS: Record<string, string> = {
  letter_of_credit: 'Letter of Credit',
  commercial_invoice: 'Commercial Invoice',
  bill_of_lading: 'Bill of Lading',
  packing_list: 'Packing List',
  insurance_certificate: 'Insurance Certificate',
  certificate_of_origin: 'Certificate of Origin',
  inspection_certificate: 'Inspection Certificate',
  supporting_document: 'Supporting Document',
};

const DEFAULT_SEVERITY = {
  critical: 0,
  major: 0,
  medium: 0,
  minor: 0,
};

const createContractWarning = (
  field: string,
  message: string,
  severity: ContractWarning['severity'],
  source: string,
  suggestion?: string | null,
): ContractWarning => ({
  field,
  message,
  severity,
  source,
  suggestion: suggestion ?? null,
});

const normalizeContractWarning = (warning: any): ContractWarning => ({
  field: String(warning?.field ?? 'result_contract'),
  message: String(warning?.message ?? warning?.detail ?? 'Result contract warning'),
  severity:
    warning?.severity === 'error' || warning?.severity === 'warning' || warning?.severity === 'info'
      ? warning.severity
      : 'warning',
  source: String(warning?.source ?? 'structured_result'),
  suggestion: warning?.suggestion ? String(warning.suggestion) : null,
});

const normalizeDocType = (value?: string | null) => {
  if (!value) {
    return DOC_LABELS.supporting_document;
  }
  const normalized = value.toString().toLowerCase().replace(/\s+/g, '_');
  return DOC_LABELS[normalized] ?? value.toString().replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
};

const deriveDocumentStatus = (extractionStatus: string, issuesCount: number): 'success' | 'warning' | 'error' => {
  const status = extractionStatus?.toLowerCase();
  if (status === 'error' || issuesCount >= 3) {
    return 'error';
  }
  if (issuesCount > 0 || status === 'partial' || status === 'pending') {
    return 'warning';
  }
  return 'success';
};

const isPlaceholderText = (value?: string | null): boolean => {
  if (value === null || value === undefined) {
    return true;
  }
  const normalized = value.toString().trim();
  return normalized.length === 0 || normalized === '—';
};

const deriveRequirementStatus = ({
  missingRequiredFields,
  requiredFieldsFound,
  requiredFieldsTotal,
}: {
  missingRequiredFields: string[];
  requiredFieldsFound?: number;
  requiredFieldsTotal?: number;
}): 'matched' | 'partial' | 'missing' => {
  if (typeof requiredFieldsTotal === 'number' && requiredFieldsTotal > 0 && typeof requiredFieldsFound === 'number') {
    if (requiredFieldsFound <= 0) {
      return 'missing';
    }
    if (requiredFieldsFound < requiredFieldsTotal) {
      return 'partial';
    }
  }

  if (missingRequiredFields.length > 0) {
    return 'partial';
  }

  return 'matched';
};

const deriveReviewState = ({
  status,
  extractionStatus,
  reviewRequired,
  reviewReasons,
  issuesCount,
  extractionResolutionRequired,
}: {
  status: 'success' | 'warning' | 'error';
  extractionStatus: string;
  reviewRequired: boolean;
  reviewReasons: string[];
  issuesCount: number;
  extractionResolutionRequired?: boolean;
}): 'ready' | 'needs_review' | 'blocked' => {
  const normalizedExtractionStatus = extractionStatus.toLowerCase();
  if (status === 'error' || ['error', 'failed', 'empty'].includes(normalizedExtractionStatus)) {
    return 'blocked';
  }

  if (
    extractionResolutionRequired ||
    reviewRequired ||
    reviewReasons.length > 0 ||
    issuesCount > 0 ||
    status === 'warning' ||
    ['partial', 'pending', 'text_only', 'unknown'].includes(normalizedExtractionStatus)
  ) {
    return 'needs_review';
  }

  return 'ready';
};

const humanizeFieldLabel = (field: string): string =>
  String(field || '')
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());

const normalizeFieldKey = (value: unknown): string =>
  String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, '_');

const FACT_RESOLUTION_DOCUMENT_TYPES = new Set([
  'commercial_invoice',
  'proforma_invoice',
  'bill_of_lading',
  'ocean_bill_of_lading',
  'house_bill_of_lading',
  'master_bill_of_lading',
  'sea_waybill',
  'air_waybill',
  'multimodal_transport_document',
]);

type ResolutionQueueItemLike = {
  documentId: string;
  filename?: string;
  fieldName: string;
  label: string;
  verification: string;
  candidateValue?: unknown;
  normalizedValue?: unknown;
  evidenceSnippet?: string | null;
  evidenceSource?: string | null;
  page?: number | null;
  reason?: string;
  origin?: string | null;
};

type FactResolutionDocumentLike = {
  documentId: string;
  filename?: string;
  resolutionRequired: boolean;
  readyForValidation: boolean;
  unresolvedCount: number;
  summary: string;
  resolutionItems: ResolutionQueueItemLike[];
};

const normalizeResolutionQueueItemList = (items?: any[]): ResolutionQueueItemLike[] =>
  ensureArray(items)
    .map((item) => ({
      documentId: String(item?.document_id ?? '').trim(),
      filename: item?.filename ? String(item.filename) : undefined,
      fieldName: normalizeFieldKey(item?.field_name),
      label: String(item?.label ?? humanizeFieldLabel(item?.field_name ?? '')),
      verification: normalizeFieldKey(item?.verification_state ?? item?.verification),
      candidateValue: item?.candidate_value,
      normalizedValue: item?.normalized_value,
      evidenceSnippet: item?.evidence_snippet ? String(item.evidence_snippet) : null,
      evidenceSource: item?.evidence_source ? String(item.evidence_source) : null,
      page: typeof item?.page === 'number' ? item.page : null,
      reason: item?.reason ? String(item.reason) : undefined,
      origin: item?.origin ? String(item.origin) : null,
    }))
    .filter((item) => item.documentId && item.fieldName);

const normalizeResolutionQueueItems = (resolutionQueue?: any): ResolutionQueueItemLike[] =>
  normalizeResolutionQueueItemList(resolutionQueue?.items);

const normalizeFactResolutionDocuments = (factResolution?: any): FactResolutionDocumentLike[] =>
  ensureArray(factResolution?.documents)
    .map((document) => ({
      documentId: String(document?.document_id ?? '').trim(),
      filename: document?.filename ? String(document.filename) : undefined,
      resolutionRequired: Boolean(document?.resolution_required),
      readyForValidation: Boolean(document?.ready_for_validation),
      unresolvedCount:
        typeof document?.unresolved_count === 'number'
          ? document.unresolved_count
          : normalizeResolutionQueueItemList(document?.resolution_items).length,
      summary: String(document?.summary ?? ''),
      resolutionItems: normalizeResolutionQueueItemList(document?.resolution_items),
    }))
    .filter((document) => document.documentId);

const buildQueueBackedExtractionResolution = (
  resolutionItems: ResolutionQueueItemLike[],
  workflowStageHint?: string | null,
) => {
  const normalizedStageHint = String(workflowStageHint ?? '').trim().toLowerCase();
  if (normalizedStageHint === 'validation_results') {
    return {
      required: false,
      unresolvedCount: 0,
      summary: '',
      fields: [],
    };
  }

  if (resolutionItems.length === 0) {
    return {
      required: false,
      unresolvedCount: 0,
      summary: '',
      fields: [],
    };
  }

  const unresolvedCount = resolutionItems.length;
  return {
    required: true,
    unresolvedCount,
    summary: `${unresolvedCount} extracted field${unresolvedCount === 1 ? '' : 's'} still need confirmation before validation can be treated as final.`,
    fields: resolutionItems.map((item) => ({
      fieldName: item.fieldName,
      label: item.label,
      verification: item.verification,
      candidateValue: item.candidateValue,
      normalizedValue: item.normalizedValue,
      evidenceSnippet: item.evidenceSnippet,
      evidenceSource: item.evidenceSource,
      page: item.page,
      reason: item.reason,
      origin: item.origin,
    })),
  };
};

const buildFactResolutionExtractionResolution = (document: FactResolutionDocumentLike) => ({
  required: document.resolutionRequired,
  unresolvedCount: document.unresolvedCount,
  summary:
    document.summary ||
    (document.resolutionRequired
      ? `${document.unresolvedCount} extracted field${document.unresolvedCount === 1 ? '' : 's'} still need confirmation before validation can be treated as final.`
      : ''),
  fields: document.resolutionItems.map((item) => ({
    fieldName: item.fieldName,
    label: item.label,
    verification: item.verification,
    candidateValue: item.candidateValue,
    normalizedValue: item.normalizedValue,
    evidenceSnippet: item.evidenceSnippet,
    evidenceSource: item.evidenceSource,
    page: item.page,
    reason: item.reason,
    origin: item.origin,
  })),
});

const buildExtractionResolution = ({
  existingResolution,
  missingRequiredFields,
  fieldDetails,
  criticalFieldStates,
  parseComplete,
  workflowStageHint,
}: {
  existingResolution?: any;
  missingRequiredFields: string[];
  fieldDetails: Record<string, any>;
  criticalFieldStates: Record<string, any>;
  parseComplete?: boolean;
  workflowStageHint?: string | null;
}) => {
  const normalizedStageHint = String(workflowStageHint ?? '').trim().toLowerCase();
  if (normalizedStageHint === 'validation_results') {
    return {
      required: false,
      unresolvedCount: 0,
      summary: '',
      fields: [],
    };
  }
  const candidates = new Map<string, { fieldName: string; label: string; verification?: string }>();
  const addField = (rawField: unknown, verification?: string) => {
    const fieldName = normalizeFieldKey(rawField);
    if (!fieldName) return;
    if (!candidates.has(fieldName)) {
      candidates.set(fieldName, {
        fieldName,
        label: humanizeFieldLabel(fieldName),
        verification,
      });
    }
  };

  missingRequiredFields.forEach((field) => addField(field, 'not_found'));
  Object.entries(criticalFieldStates || {}).forEach(([fieldName, state]) => {
    const normalizedState = normalizeFieldKey(state);
    if (normalizedState === 'missing' || normalizedState === 'failed' || normalizedState === 'parse_failed') {
      addField(fieldName, normalizedState);
    }
  });
  Object.entries(fieldDetails || {}).forEach(([fieldName, detail]) => {
    const verification = normalizeFieldKey((detail as Record<string, any>)?.verification);
    if (verification && !['confirmed', 'operator_confirmed'].includes(verification)) {
      addField(fieldName, verification);
    }
  });

  const fields = Array.from(candidates.values());
  const required = fields.length > 0 || parseComplete === false;
  const unresolvedCount = fields.length;
  const summary = required
    ? unresolvedCount > 0
      ? `${unresolvedCount} extracted field${unresolvedCount === 1 ? '' : 's'} still need confirmation before validation can be treated as final.`
      : 'Extraction is still incomplete and needs confirmation before validation can be treated as final.'
    : '';

  const derived = {
    required,
    unresolvedCount,
    summary,
    fields,
  };

  if (existingResolution && typeof existingResolution === 'object') {
    const existingFields = Array.isArray(existingResolution.fields)
      ? existingResolution.fields
          .map((field: any) => ({
            fieldName: String(field?.field_name ?? field?.fieldName ?? ''),
            label: String(field?.label ?? humanizeFieldLabel(field?.field_name ?? field?.fieldName ?? '')),
            verification:
              field?.verification !== undefined && field?.verification !== null
                ? String(field.verification)
                : undefined,
          }))
          .filter((field: { fieldName: string }) => field.fieldName)
      : [];
    const existing = {
      required: Boolean(existingResolution.required),
      unresolvedCount:
        typeof existingResolution.unresolved_count === 'number'
          ? existingResolution.unresolved_count
          : typeof existingResolution.unresolvedCount === 'number'
          ? existingResolution.unresolvedCount
          : existingFields.length,
      summary: String(existingResolution.summary ?? ''),
      fields: existingFields,
    };
    if (existing.required === derived.required && existing.unresolvedCount === derived.unresolvedCount) {
      return {
        ...existing,
        fields: existing.fields.length > 0 ? existing.fields : derived.fields,
        summary: existing.summary || derived.summary,
      };
    }
  }

  return derived;
};

const deriveWorkflowStage = ({
  existingStage,
  factResolution,
  documents,
  validationStatus,
}: {
  existingStage?: any;
  factResolution?: any;
  documents: ReturnType<typeof mapDocuments>;
  validationStatus?: string | null;
}) => {
  const stageSource =
    existingStage && typeof existingStage === 'object'
      ? existingStage
      : factResolution?.workflow_stage && typeof factResolution.workflow_stage === 'object'
      ? factResolution.workflow_stage
      : null;
  if (stageSource && typeof stageSource === 'object') {
    return {
      stage: String(stageSource.stage ?? 'validation_results'),
      provisional_validation: Boolean(stageSource.provisional_validation),
      ready_for_final_validation:
        stageSource.ready_for_final_validation !== undefined
          ? Boolean(stageSource.ready_for_final_validation)
          : !Boolean(stageSource.provisional_validation),
      unresolved_documents:
        typeof stageSource.unresolved_documents === 'number'
          ? stageSource.unresolved_documents
          : typeof stageSource.unresolvedDocuments === 'number'
          ? stageSource.unresolvedDocuments
          : 0,
      unresolved_fields:
        typeof stageSource.unresolved_fields === 'number'
          ? stageSource.unresolved_fields
          : typeof stageSource.unresolvedFields === 'number'
          ? stageSource.unresolvedFields
          : 0,
      document_lane_counts:
        stageSource.document_lane_counts && typeof stageSource.document_lane_counts === 'object'
          ? stageSource.document_lane_counts
          : stageSource.documentLaneCounts && typeof stageSource.documentLaneCounts === 'object'
          ? stageSource.documentLaneCounts
          : undefined,
      summary: String(stageSource.summary ?? ''),
    };
  }

  if (documents.length === 0) {
    return {
      stage: 'upload',
      provisional_validation: true,
      ready_for_final_validation: false,
      unresolved_documents: 0,
      unresolved_fields: 0,
      summary: 'Upload the LC and supporting documents to begin extraction and validation.',
    };
  }

  const unresolvedDocuments = documents.filter((doc) => doc.extractionResolution?.required).length;
  const unresolvedFields = documents.reduce(
    (total, doc) => total + Number(doc.extractionResolution?.unresolvedCount ?? 0),
    0,
  );
  const documentLaneCounts = documents.reduce<Record<string, number>>((counts, doc) => {
    const lane = doc.extractionLane || 'unknown';
    counts[lane] = (counts[lane] ?? 0) + 1;
    return counts;
  }, {});

  if (unresolvedDocuments > 0 || unresolvedFields > 0) {
    return {
      stage: 'extraction_resolution',
      provisional_validation: true,
      ready_for_final_validation: false,
      unresolved_documents: unresolvedDocuments,
      unresolved_fields: unresolvedFields,
      document_lane_counts: documentLaneCounts,
      summary: `${unresolvedDocuments} document${unresolvedDocuments === 1 ? '' : 's'} still need${
        unresolvedDocuments === 1 ? 's' : ''
      } ${unresolvedFields} field${unresolvedFields === 1 ? '' : 's'} confirmed before validation should be treated as final.`,
    };
  }

  return {
    stage: 'validation_results',
    provisional_validation: false,
    ready_for_final_validation: true,
    unresolved_documents: 0,
    unresolved_fields: 0,
    document_lane_counts: documentLaneCounts,
    summary:
      ['blocked', 'review', 'partial'].includes(String(validationStatus ?? '').toLowerCase())
        ? 'Extraction is sufficiently resolved. Remaining items belong to documentary validation or policy review, not parser uncertainty.'
        : 'Extraction is sufficiently resolved. Validation findings reflect the current confirmed document set.',
  };
};

const formatTextValue = (value: any): string => {
  if (value === null || value === undefined) {
    return '—';
  }
  if (typeof value === 'string') {
    return value.trim() || '—';
  }
  if (Array.isArray(value)) {
    return value.map((entry) => formatTextValue(entry)).filter(Boolean).join(', ');
  }
  if (typeof value === 'object') {
    if ('value' in value) {
      return formatTextValue(value.value);
    }
    if ('text' in value) {
      return formatTextValue(value.text);
    }
    return JSON.stringify(value);
  }
  return String(value);
};

const normalizeSeverity = (
  value?: string | null,
  issue?: { rule?: string | null; ruleset_domain?: string | null },
): string => {
  const normalized = (value ?? '').toLowerCase();
  const normalizedRule = String(issue?.rule ?? '').trim().toUpperCase();
  const normalizedDomain = String(issue?.ruleset_domain ?? '').trim().toLowerCase();
  if (
    ['warn', 'warning'].includes(normalized) &&
    (normalizedRule === 'LC-TYPE-UNKNOWN' || normalizedDomain === 'system.lc_type')
  ) {
    return 'minor';
  }
  if (['critical', 'fail', 'error', 'high'].includes(normalized)) return 'critical';
  if (['major', 'warn', 'warning', 'medium'].includes(normalized)) return 'major';
  if (['minor', 'low'].includes(normalized)) return 'minor';
  if (['info', 'informational'].includes(normalized)) return 'info';
  return normalized || 'minor';
};

const humanizeText = (value?: string | null): string => {
  if (!value) return '';
  return value
    .replace(/_/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
};

const classifyBucket = (issue: any, severity: string): string => {
  const text = [
    issue?.title,
    issue?.description,
    issue?.rule,
    issue?.ruleset_domain,
    issue?.category,
    issue?.document_type,
    issue?.bucket,
    issue?.workflow_lane,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();

  if (text.includes('missing') && (text.includes('document') || text.includes('doc'))) {
    return 'Missing Required Documents';
  }
  if (
    text.includes('sanction') ||
    text.includes('aml') ||
    text.includes('compliance') ||
    text.includes('risk') ||
    text.includes('ofac') ||
    text.includes('watchlist') ||
    text.includes('screening') ||
    text.includes('compliance_review')
  ) {
    return 'Compliance / Risk Review';
  }
  if (text.includes('crossdoc') || text.includes('cross-document') || text.includes('across documents')) {
    return 'Cross-Document Conditions';
  }
  if (
    text.includes('ocr') ||
    text.includes('extraction') ||
    text.includes('manual review') ||
    text.includes('unreadable') ||
    text.includes('confidence') ||
    severity === 'info'
  ) {
    return 'Extraction / Manual Review';
  }
  return 'Document-Level Discrepancies';
};

const getSeverityDisplay = (severity: string, bucket: string): string => {
  if (bucket === 'Compliance / Risk Review') {
    if (severity === 'critical') return 'Compliance hold';
    if (severity === 'major') return 'Compliance escalation';
    if (severity === 'minor') return 'Compliance review';
    return 'Compliance note';
  }
  if (severity === 'critical') return 'High-likelihood discrepancy';
  if (severity === 'major') return 'Likely discrepancy';
  if (severity === 'minor') return 'Review required';
  return 'Informational';
};

const getFixOwner = (issue: any, bucket: string): string => {
  const text = [issue?.title, issue?.description, issue?.suggestion].filter(Boolean).join(' ').toLowerCase();
  if (text.includes('amend') || text.includes('waiver')) return 'Waiver / Amendment';
  if (bucket === 'Compliance / Risk Review') return 'Internal Compliance Review';
  if (bucket === 'Cross-Document Conditions') return 'Mixed';
  if (text.includes('carrier') || text.includes('supplier') || text.includes('insurer') || text.includes('issuer')) return 'Third Party';
  if (bucket === 'Missing Required Documents' || bucket === 'Document-Level Discrepancies') return 'Beneficiary';
  return 'Unknown';
};

const getWorkflowLane = (bucket: string): 'documentary_review' | 'compliance_review' | 'manual_review' => {
  if (bucket === 'Compliance / Risk Review') {
    return 'compliance_review';
  }
  if (bucket === 'Extraction / Manual Review') {
    return 'manual_review';
  }
  return 'documentary_review';
};

const buildNextAction = (bucket: string, suggestion: string): string => {
  if (bucket === 'Compliance / Risk Review') {
    if (
      isPlaceholderText(suggestion) ||
      /(correct|fix|amend|revalidate|resolve discrepancy|documentary|presentation|proceed with caution|monitor closely|manual review recommended|review recommended)/i.test(suggestion)
    ) {
      return 'Route to internal compliance review, document the screening disposition, and hold bank presentation until compliance clearance is recorded.';
    }
    return suggestion;
  }
  if (!isPlaceholderText(suggestion)) return suggestion;
  if (bucket === 'Missing Required Documents') return 'Obtain and upload the missing required document set.';
  if (bucket === 'Extraction / Manual Review') return 'Validate source document manually and confirm extracted values.';
  if (bucket === 'Cross-Document Conditions') return 'Reconcile conflicting values across all referenced documents.';
  return 'Correct the document field and revalidate before submission.';
};

const mapDocuments = (
  docs: any[] = [],
  workflowStageHint?: string | null,
  resolutionQueue?: any,
  factResolution?: any,
) => {
  const normalizedResolutionItems = normalizeResolutionQueueItems(resolutionQueue);
  const normalizedFactResolutionDocuments = normalizeFactResolutionDocuments(factResolution);

  return docs.map((doc, index) => {
    const documentId = String(doc?.document_id ?? doc?.id ?? index);
    const filename = doc?.filename ?? doc?.name ?? `Document ${index + 1}`;
    // Ensure typeKey is a string - handle case where backend returns object like {types: [...]}
    const rawType = doc?.document_type ?? 'supporting_document';
    const typeKey = typeof rawType === 'string' ? rawType : 'supporting_document';
    // Check multiple possible keys for issue count (backend uses discrepancyCount)
    const issuesCount = Number(doc?.discrepancyCount ?? doc?.issues_count ?? doc?.issuesCount ?? 0);
    const extractionStatus = (
      doc?.extraction_status ??
      doc?.extractionStatus ??
      doc?.extraction?.status ??
      doc?.extraction?.extraction_status ??
      'unknown'
    ).toString();
    const extractionLane = (
      doc?.extraction_lane ??
      doc?.extractionLane ??
      doc?.extraction?.lane ??
      'unknown'
    ).toString();
    const rawStatus = doc?.status;
    const normalizedStatus = typeof rawStatus === 'string' ? rawStatus.toLowerCase() : null;
    const status =
      normalizedStatus === 'success' || normalizedStatus === 'warning' || normalizedStatus === 'error'
        ? (normalizedStatus as 'success' | 'warning' | 'error')
        : deriveDocumentStatus(extractionStatus, issuesCount);
    const missingRequiredFields = Array.isArray(doc?.missing_required_fields)
      ? doc.missing_required_fields.map((field: unknown) => String(field))
      : Array.isArray(doc?.missingRequiredFields)
      ? doc.missingRequiredFields.map((field: unknown) => String(field))
      : [];
    const requiredFieldsFound =
      typeof doc?.required_fields_found === 'number'
        ? doc.required_fields_found
        : typeof doc?.requiredFieldsFound === 'number'
        ? doc.requiredFieldsFound
        : undefined;
    const requiredFieldsTotal =
      typeof doc?.required_fields_total === 'number'
        ? doc.required_fields_total
        : typeof doc?.requiredFieldsTotal === 'number'
        ? doc.requiredFieldsTotal
        : undefined;
    const reviewRequired = Boolean(doc?.review_required ?? doc?.reviewRequired);
    const reviewReasons = Array.isArray(doc?.review_reasons)
      ? doc.review_reasons.map((reason: unknown) => String(reason))
      : Array.isArray(doc?.reviewReasons)
      ? doc.reviewReasons.map((reason: unknown) => String(reason))
      : [];
    const criticalFieldStates = doc?.critical_field_states ?? doc?.criticalFieldStates ?? {};
    const fieldDetails = doc?.field_details ?? doc?.fieldDetails ?? {};
    const existingExtractionResolution = doc?.extraction_resolution ?? doc?.extractionResolution;
    const matchedFactResolution = FACT_RESOLUTION_DOCUMENT_TYPES.has(typeKey.toLowerCase())
      ? normalizedFactResolutionDocuments.find(
          (item) =>
            item.documentId === documentId ||
            (!!item.filename && item.filename.toLowerCase() === String(filename).toLowerCase()),
        )
      : undefined;
    const resolutionItems = matchedFactResolution
      ? matchedFactResolution.resolutionItems
      : FACT_RESOLUTION_DOCUMENT_TYPES.has(typeKey.toLowerCase())
      ? normalizedResolutionItems.filter(
          (item) =>
            item.documentId === documentId ||
            (!!item.filename && item.filename.toLowerCase() === String(filename).toLowerCase()),
        )
      : [];
    const fieldDiagnostics = doc?.extraction_artifacts_v1?.field_diagnostics ?? doc?.field_diagnostics ?? {};
    const rawText =
      doc?.extraction_artifacts_v1?.raw_text ??
      doc?.raw_text ??
      doc?.rawText ??
      '';
    const extractionResolution =
      FACT_RESOLUTION_DOCUMENT_TYPES.has(typeKey.toLowerCase()) && matchedFactResolution
        ? buildFactResolutionExtractionResolution(matchedFactResolution)
        : FACT_RESOLUTION_DOCUMENT_TYPES.has(typeKey.toLowerCase()) && resolutionQueue
        ? buildQueueBackedExtractionResolution(resolutionItems, workflowStageHint)
        : buildExtractionResolution({
            existingResolution: existingExtractionResolution,
            missingRequiredFields,
            fieldDetails,
            criticalFieldStates,
            workflowStageHint,
            parseComplete:
              typeof doc?.parse_complete === 'boolean' ? doc.parse_complete : doc?.parseComplete,
          });
    const requirementStatus = deriveRequirementStatus({
      missingRequiredFields,
      requiredFieldsFound,
      requiredFieldsTotal,
    });
    const reviewState = deriveReviewState({
      status,
      extractionStatus,
      reviewRequired,
      reviewReasons,
      issuesCount,
      extractionResolutionRequired: extractionResolution.required,
    });

    return {
      id: documentId,
      documentId,
      name: filename,
      filename,
      type: doc?.document_type_label ?? normalizeDocType(typeKey),
      typeKey,
      extractionStatus,
      extractionLane,
      status,
      issuesCount,
      parseComplete: typeof doc?.parse_complete === 'boolean' ? doc.parse_complete : doc?.parseComplete,
      parseCompleteness: doc?.parse_completeness ?? doc?.parseCompleteness,
      fieldDetails,
      missingRequiredFields,
      requiredFieldsFound,
      requiredFieldsTotal,
      reviewRequired,
      reviewReasons,
      criticalFieldStates,
      fieldDiagnostics,
      rawText,
      resolutionItems: matchedFactResolution ? resolutionItems : resolutionQueue ? resolutionItems : undefined,
      requirementStatus,
      reviewState,
      extractionResolution,
      extractedFields: doc?.extracted_fields ?? {},
    };
  });
};

const mapIssues = (
  issues: any[] = [],
  documents: ReturnType<typeof mapDocuments>,
  issueProvenance?: { issues?: Array<Record<string, any>> } | null,
): IssueCard[] => {
  const lookup = new Map<string, ReturnType<typeof mapDocuments>[number]>();
  documents.forEach((doc) => {
    const candidates = [doc.filename, doc.name, doc.type, doc.typeKey];
    candidates.forEach((candidate) => {
      if (candidate) {
        lookup.set(candidate.toLowerCase(), doc);
      }
    });
  });

  const provenanceLookup = new Map<string, Record<string, any>>();
  issueProvenance?.issues?.forEach((entry) => {
    if (entry?.issue_id) {
      provenanceLookup.set(String(entry.issue_id), entry);
    }
  });

  const extractProvenanceDocuments = (issue: any): string[] => {
    const provenance = issue?.provenance ?? issue?.issue_provenance ?? issue?.source_provenance ?? {};
    const provenanceEntry = provenanceLookup.get(String(issue?.id ?? '')) ?? null;
    const candidates = [
      issue?.documents,
      issue?.source_documents,
      issue?.source_document_names,
      issue?.source_document_types,
      provenance?.documents,
      provenance?.document_names,
      provenance?.document_types,
      provenance?.source_documents,
      provenance?.sources,
      provenanceEntry?.document_names,
      provenanceEntry?.document_types,
      provenanceEntry?.document_ids,
    ];

    const flattened = candidates
      .flatMap((entry) => (Array.isArray(entry) ? entry : entry ? [entry] : []))
      .filter((value) => typeof value === 'string' && value.trim().length > 0);

    if (flattened.length > 0) {
      return flattened;
    }

    const singleCandidates = [
      issue?.document_name,
      issue?.document_type,
      provenance?.document_name,
      provenance?.document_type,
      provenanceEntry?.document_names,
      provenanceEntry?.document_types,
    ];
    return singleCandidates.filter((value) => typeof value === 'string' && value.trim().length > 0) as string[];
  };

  return issues.map((issue, index) => {
    const provenanceEntry = provenanceLookup.get(String(issue?.id ?? '')) ?? null;
    const documentNames = Array.isArray(issue?.documents)
      ? issue.documents
      : issue?.documents
      ? [issue.documents]
      : extractProvenanceDocuments(issue);
    const firstDoc = documentNames[0];
    const docMeta = firstDoc ? lookup.get(firstDoc.toLowerCase()) : undefined;

    const severity = normalizeSeverity(issue?.severity ?? provenanceEntry?.severity, issue);
    const expected = formatTextValue(issue?.expected);
    const found = formatTextValue(issue?.found ?? issue?.actual);
    const suggestion = formatTextValue(issue?.suggestion ?? issue?.suggested_fix);
    const bucket = classifyBucket(issue, severity);
    const severityDisplay = getSeverityDisplay(severity, bucket);
    const lcBasis =
      issue?.ucp_reference ||
      issue?.isbp_reference ||
      issue?.rule ||
      humanizeText(issue?.ruleset_domain) ||
      'LC examination baseline';
    const fixOwner = getFixOwner(issue, bucket);
    const examinerNote = issue?.description ?? issue?.message ?? issue?.note ?? 'Review against LC terms and supporting documents.';
    const nextAction = buildNextAction(bucket, suggestion);
    const workflowLane = getWorkflowLane(bucket);
    const countClass =
      workflowLane === 'compliance_review'
        ? 'compliance_alert'
        : workflowLane === 'manual_review'
        ? 'manual_review'
        : 'documentary_discrepancy';
    const presentationImpact =
      workflowLane === 'compliance_review'
        ? severity === 'critical'
          ? 'presentation_blocked_pending_compliance'
          : 'presentation_requires_compliance_review'
        : workflowLane === 'manual_review'
        ? severity === 'critical'
          ? 'presentation_blocked_pending_manual_review'
          : 'presentation_requires_manual_review'
        : severity === 'critical'
        ? 'documentary_blocker'
        : severity === 'major'
        ? 'documentary_risk'
        : 'documentary_review';
    const confidenceRaw = issue?.extraction_confidence ?? issue?.confidence ?? issue?.match_confidence;
    const confidence = typeof confidenceRaw === 'number' ? Math.max(0, Math.min(1, confidenceRaw)) : undefined;

    return {
      id: String(issue?.id ?? issue?.rule ?? `issue-${index}`),
      rule: issue?.rule ?? provenanceEntry?.rule,
      title: issue?.title ?? humanizeText(issue?.rule) ?? 'Review Required',
      description: issue?.description ?? issue?.message ?? '',
      priority: issue?.severity,
      severity,
      severity_display: severityDisplay,
      bucket,
      lc_basis: lcBasis,
      documentName: issue?.document_name ?? issue?.documentName ?? firstDoc ?? docMeta?.name,
      documentType: issue?.document_type ?? issue?.documentType ?? docMeta?.type,
      documents: documentNames,
      expected,
      actual: found,
      found,
      examiner_note: examinerNote,
      fix_owner: fixOwner,
      remediation_owner: fixOwner,
      next_action: nextAction,
      workflow_lane: workflowLane,
      count_class: countClass,
      presentation_impact: presentationImpact,
      confidence,
      suggestion,
      field: issue?.field ?? issue?.metadata?.field,
      ruleset_domain: issue?.ruleset_domain ?? provenanceEntry?.ruleset_domain,
      ucpReference: issue?.ucp_reference && issue.ucp_reference.trim() ? issue.ucp_reference.trim() : undefined,
      ucpDescription: issue?.ucp_description ?? undefined,
      isbpReference: issue?.isbp_reference && issue.isbp_reference.trim() ? issue.isbp_reference.trim() : undefined,
      isbpDescription: issue?.isbp_description ?? undefined,
      auto_generated: issue?.auto_generated ?? false,
      extraction_confidence: confidence,
    };
  });
};

const ensureSummary = (payload: any, contractWarnings: ContractWarning[]) => {
  if (!payload) {
    contractWarnings.push(
      createContractWarning(
        'processing_summary',
        'Canonical processing summary is missing from structured_result; frontend is using zero-value defaults.',
        'error',
        'structured_result',
        'Return structured_result.processing_summary and processing_summary_v2 from /api/results/{jobId}.',
      ),
    );
  }
  const severity = payload?.severity_breakdown ?? { ...DEFAULT_SEVERITY };
  const rawStatus = payload?.document_status ?? payload?.status_counts ?? {};
  const documentStatus = {
    success: Number(rawStatus?.success ?? 0),
    warning: Number(rawStatus?.warning ?? 0),
    error: Number(rawStatus?.error ?? 0),
  };
  const statusTotal = documentStatus.success + documentStatus.warning + documentStatus.error;

  return {
    ...payload,
    total_documents: Number(payload?.total_documents ?? payload?.documents ?? statusTotal ?? 0),
    // Canonical extraction counters come from document_status/status_counts for parity across sections
    successful_extractions: Number(documentStatus.success ?? 0),
    failed_extractions: Number(documentStatus.error ?? 0),
    total_issues: Number(payload?.total_issues ?? payload?.discrepancies ?? 0),
    severity_breakdown: severity,
    // Pass through document status for SummaryStrip
    document_status: documentStatus,
    status_counts: documentStatus,
    verified: Number(documentStatus.success ?? 0),
    warnings: Number(documentStatus.warning ?? 0),
    errors: Number(documentStatus.error ?? 0),
    // Pass through other useful fields from backend
    compliance_rate: Number(payload?.compliance_rate ?? 0),
    processing_time_display: payload?.processing_time_display ?? 'N/A',
  };
};

const ensureAnalytics = (
  payload: any,
  summary: ReturnType<typeof ensureSummary>,
  contractWarnings: ContractWarning[],
) => {
  if (!payload) {
    contractWarnings.push(
      createContractWarning(
        'analytics',
        'Canonical analytics are missing from structured_result; frontend is using derived defaults.',
        'warning',
        'structured_result',
        'Return structured_result.analytics from /api/results/{jobId}.',
      ),
    );
  }
  const issueCounts = payload?.issue_counts ?? summary.severity_breakdown ?? { ...DEFAULT_SEVERITY };
  const compliance =
    typeof payload?.compliance_score === 'number'
      ? payload.compliance_score
      : typeof payload?.lc_compliance_score === 'number'
      ? payload.lc_compliance_score
      : summary.compliance_rate ?? 0;

  const documentStatusDistribution =
    payload?.document_status_distribution ?? summary.document_status ?? {
      success: 0,
      warning: 0,
      error: 0,
    };

  return {
    compliance_score: Math.max(0, Math.min(100, compliance ?? 0)),
    issue_counts: issueCounts,
    document_risk: Array.isArray(payload?.document_risk) ? payload.document_risk : [],
    // Pass through document status distribution for consistent display
    document_status_distribution: documentStatusDistribution,
    documents_processed: payload?.documents_processed ?? summary.total_documents ?? 0,
    processing_time_display: payload?.processing_time_display ?? summary.processing_time_display ?? 'N/A',
  };
};

const mapTimeline = (entries: Array<any> = []) =>
  entries
    .map((entry, index) => ({
      title: entry?.title ?? entry?.label ?? `Step ${index + 1}`,
      status: entry?.status ?? 'pending',
      description: entry?.description ?? entry?.detail,
      timestamp: entry?.timestamp ?? entry?.time,
    }))
    .filter((entry) => Boolean(entry.title));

// Ensure value is an array - returns empty array if not a proper array
const ensureArray = (value: unknown): any[] => {
  if (Array.isArray(value)) return value;
  // Don't try to convert objects - just return empty array
  // This prevents issues when backend returns unexpected shapes like {types: [...]}
  return [];
};

export const buildValidationResponse = (raw: any): ValidationResults => {
  const structured = raw?.structured_result as StructuredResultPayload | null;
  if (!structured || structured.version !== 'structured_result_v1') {
    throw new Error('structured_result_v1 payload missing');
  }

  const contractWarnings: ContractWarning[] = ensureArray((structured as any)._contract_warnings ?? []).map(
    normalizeContractWarning,
  );

  let rawDocs = (structured as any)?.document_extraction_v1?.documents;
  if (rawDocs === undefined) {
    rawDocs = (structured as any)?.documents_structured;
    if (Array.isArray(rawDocs)) {
      contractWarnings.push(
        createContractWarning(
          'documents',
          'Using legacy structured_result.documents_structured as the document source.',
          'warning',
          'results_mapper',
          'Promote document_extraction_v1.documents as the canonical document source.',
        ),
      );
    }
  }
  if (rawDocs === undefined) {
    rawDocs = structured.lc_structured?.documents_structured;
    if (Array.isArray(rawDocs)) {
      contractWarnings.push(
        createContractWarning(
          'documents',
          'Using lc_structured.documents_structured as a fallback document source.',
          'warning',
          'results_mapper',
          'Persist document_extraction_v1.documents to avoid frontend document-source drift.',
        ),
      );
    }
  }
  const optionEDocuments = ensureArray(rawDocs);
  const existingWorkflowStage = (structured as any)?.workflow_stage ?? (structured as any)?.workflowStage ?? null;
  const resolutionQueue = (structured as any)?.resolution_queue_v1 ?? null;
  const factResolution = (structured as any)?.fact_resolution_v1 ?? null;

  const documents = mapDocuments(
    optionEDocuments,
    existingWorkflowStage && typeof existingWorkflowStage === 'object'
      ? String(existingWorkflowStage.stage ?? '')
      : null,
    resolutionQueue,
    factResolution,
  );
  const workflowStage = deriveWorkflowStage({
    existingStage: existingWorkflowStage,
    factResolution,
    documents,
    validationStatus: (structured as any)?.validation_status ?? null,
  });
  
  // Safely extract issues - ensure it's always an array
  const rawIssues = structured.issues ?? [];
  const issues = mapIssues(
    ensureArray(rawIssues),
    documents,
    (structured as any)?.issue_provenance_v1 ?? null,
  );
  
  const processingSummaryPayload = (structured as any)?.processing_summary_v2 ?? structured.processing_summary;
  const summary = ensureSummary(processingSummaryPayload, contractWarnings);
  const analytics = ensureAnalytics(structured.analytics, summary, contractWarnings);
  
  // Safely extract timeline
  let rawTimeline: unknown = structured.timeline ?? [];
  if (!Array.isArray(rawTimeline) || rawTimeline.length === 0) {
    rawTimeline = structured.lc_structured?.timeline ?? [];
    if (Array.isArray(rawTimeline) && rawTimeline.length > 0) {
      contractWarnings.push(
        createContractWarning(
          'timeline',
          'Using lc_structured.timeline because structured_result.timeline is empty or missing.',
          'info',
          'results_mapper',
          'Persist the canonical timeline directly at structured_result.timeline.',
        ),
      );
    }
  }
  const timeline = mapTimeline(ensureArray(rawTimeline));

  // V2 Validation Pipeline fields
  const validationBlocked = Boolean(structured.validation_blocked);
  const validationStatus = String(
    (structured as any)?.validation_status ?? (validationBlocked ? 'blocked' : 'non_compliant'),
  );
  const gateResult = structured.gate_result ?? null;
  const extractionSummary = structured.extraction_summary ?? null;
  const lcBaseline = structured.lc_baseline ?? null;
  const complianceLevel = String((structured.analytics as any)?.compliance_level ?? validationStatus);
  const complianceCapReason = ((structured.analytics as any)?.compliance_cap_reason ?? null) as string | null;

  // Sanctions Screening fields
  const sanctionsScreening = structured.sanctions_screening ?? null;
  const sanctionsBlocked = Boolean(structured.sanctions_blocked);
  const sanctionsBlockReason = ((structured as any)?.sanctions_block_reason ?? null) as string | null;

  const contractValidation = (structured as any)._contract_validation ?? null;
  const effectiveEligibility =
    (structured as any)?.effective_submission_eligibility ??
    (structured as any)?.submission_eligibility ??
    null;
  const finalVerdict = String((structured as any)?.validation_contract_v1?.final_verdict ?? '').trim().toLowerCase();

  if (
    effectiveEligibility &&
    typeof effectiveEligibility?.can_submit === 'boolean' &&
    effectiveEligibility.can_submit === false &&
    finalVerdict === 'pass'
  ) {
    contractWarnings.push(
      createContractWarning(
        'validation_contract_v1.final_verdict',
        'Contradictory readiness state detected: final verdict is pass while effective submission eligibility blocks submission.',
        'error',
        'results_mapper',
        'Backend should keep final_verdict aligned with effective_submission_eligibility.can_submit.',
      ),
    );
  }

  return {
    jobId: raw?.jobId ?? raw?.job_id ?? '',
    job_id: raw?.job_id,
    validation_session_id: raw?.validation_session_id ?? raw?.jobId ?? raw?.job_id ?? '',
    summary,
    documents,
    issues,
    analytics,
    timeline,
    structured_result: structured as ValidationResults['structured_result'],
    lc_structured: structured.lc_structured ?? null,
    ai_enrichment: structured.ai_enrichment ?? null,
    
    // V2 Validation Pipeline additions
    validationBlocked,
    validationStatus,
    gateResult,
    extractionSummary,
    lcBaseline,
    workflowStage,
    complianceLevel,
    complianceCapReason,
    factResolution,
    resolutionQueue,
    
    // Sanctions Screening additions
    sanctionsScreening,
    sanctionsBlocked,
    sanctionsBlockReason,
    
    // Contract Validation additions (Output-First layer)
    contractWarnings,
    contractValidation:
      contractValidation ??
      {
        valid: contractWarnings.filter((warning) => warning.severity === 'error').length === 0,
        error_count: contractWarnings.filter((warning) => warning.severity === 'error').length,
        warning_count: contractWarnings.filter((warning) => warning.severity === 'warning').length,
        info_count: contractWarnings.filter((warning) => warning.severity === 'info').length,
      },
  };
};
