import type { StructuredResultPayload } from '@shared/types';
import type { ValidationResults, IssueCard } from '@/types/lcopilot';

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
}: {
  status: 'success' | 'warning' | 'error';
  extractionStatus: string;
  reviewRequired: boolean;
  reviewReasons: string[];
  issuesCount: number;
}): 'ready' | 'needs_review' | 'blocked' => {
  const normalizedExtractionStatus = extractionStatus.toLowerCase();
  if (status === 'error' || ['error', 'failed', 'empty'].includes(normalizedExtractionStatus)) {
    return 'blocked';
  }

  if (
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

const normalizeSeverity = (value?: string | null): string => {
  const normalized = (value ?? '').toLowerCase();
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
      /(correct|fix|amend|revalidate|resolve discrepancy|documentary|presentation)/i.test(suggestion)
    ) {
      return 'Route to internal compliance review, capture the disposition, and keep submission on hold until cleared.';
    }
    return suggestion;
  }
  if (!isPlaceholderText(suggestion)) return suggestion;
  if (bucket === 'Missing Required Documents') return 'Obtain and upload the missing required document set.';
  if (bucket === 'Extraction / Manual Review') return 'Validate source document manually and confirm extracted values.';
  if (bucket === 'Cross-Document Conditions') return 'Reconcile conflicting values across all referenced documents.';
  return 'Correct the document field and revalidate before submission.';
};

const mapDocuments = (docs: any[] = []) => {
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
    });

    return {
      id: documentId,
      documentId,
      name: filename,
      filename,
      type: doc?.document_type_label ?? normalizeDocType(typeKey),
      typeKey,
      extractionStatus,
      status,
      issuesCount,
      parseComplete: typeof doc?.parse_complete === 'boolean' ? doc.parse_complete : doc?.parseComplete,
      parseCompleteness: doc?.parse_completeness ?? doc?.parseCompleteness,
      missingRequiredFields,
      requiredFieldsFound,
      requiredFieldsTotal,
      reviewRequired,
      reviewReasons,
      criticalFieldStates,
      requirementStatus,
      reviewState,
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

    const severity = normalizeSeverity(issue?.severity ?? provenanceEntry?.severity);
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

const ensureSummary = (payload: any) => {
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

const ensureAnalytics = (payload: any, summary: ReturnType<typeof ensureSummary>) => {
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

  // Safely extract documents - ensure it's always an array
  const rawDocs =
    (structured as any)?.document_extraction_v1?.documents ??
    structured.documents_structured ??
    structured.lc_structured?.documents_structured ??
    [];
  const optionEDocuments = ensureArray(rawDocs);

  const documents = mapDocuments(optionEDocuments);
  
  // Safely extract issues - ensure it's always an array
  const rawIssues = structured.issues ?? [];
  const issues = mapIssues(
    ensureArray(rawIssues),
    documents,
    (structured as any)?.issue_provenance_v1 ?? null,
  );
  
  const processingSummaryPayload = (structured as any)?.processing_summary_v2 ?? structured.processing_summary;
  const summary = ensureSummary(processingSummaryPayload);
  const analytics = ensureAnalytics(structured.analytics, summary);
  
  // Safely extract timeline
  const rawTimeline = structured.lc_structured?.timeline ?? structured.timeline ?? [];
  const timeline = mapTimeline(ensureArray(rawTimeline));

  // V2 Validation Pipeline fields
  const validationBlocked = Boolean(structured.validation_blocked);
  const validationStatus = structured.validation_status ?? (validationBlocked ? 'blocked' : 'non_compliant');
  const gateResult = structured.gate_result ?? null;
  const extractionSummary = structured.extraction_summary ?? null;
  const lcBaseline = structured.lc_baseline ?? null;
  const complianceLevel = structured.analytics?.compliance_level ?? validationStatus;
  const complianceCapReason = structured.analytics?.compliance_cap_reason ?? null;

  // Sanctions Screening fields
  const sanctionsScreening = structured.sanctions_screening ?? null;
  const sanctionsBlocked = Boolean(structured.sanctions_blocked);
  const sanctionsBlockReason = structured.sanctions_block_reason ?? null;

  // Contract Validation fields (Output-First layer)
  const contractWarnings = ensureArray((structured as any)._contract_warnings ?? []);
  const contractValidation = (structured as any)._contract_validation ?? null;

  return {
    jobId: raw?.jobId ?? raw?.job_id ?? '',
    summary,
    documents,
    issues,
    analytics,
    timeline,
    structured_result: structured,
    lc_structured: structured.lc_structured ?? null,
    ai_enrichment: structured.ai_enrichment ?? null,
    
    // V2 Validation Pipeline additions
    validationBlocked,
    validationStatus,
    gateResult,
    extractionSummary,
    lcBaseline,
    complianceLevel,
    complianceCapReason,
    
    // Sanctions Screening additions
    sanctionsScreening,
    sanctionsBlocked,
    sanctionsBlockReason,
    
    // Contract Validation additions (Output-First layer)
    contractWarnings,
    contractValidation,
  };
};
