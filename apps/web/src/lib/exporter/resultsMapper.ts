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
  if (['critical', 'fail', 'error', 'high'].includes(normalized)) {
    return 'critical';
  }
  if (['major', 'warn', 'warning', 'medium'].includes(normalized)) {
    return 'major';
  }
  if (['minor', 'low'].includes(normalized)) {
    return 'minor';
  }
  return normalized || 'minor';
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

    return {
      id: documentId,
      documentId,
      name: filename,
      filename,
      type: normalizeDocType(typeKey),
      typeKey,
      extractionStatus,
      status,
      issuesCount,
      parseComplete: typeof doc?.parse_complete === 'boolean' ? doc.parse_complete : doc?.parseComplete,
      parseCompleteness: doc?.parse_completeness ?? doc?.parseCompleteness,
      missingRequiredFields: doc?.missing_required_fields ?? [],
      requiredFieldsFound: doc?.required_fields_found,
      requiredFieldsTotal: doc?.required_fields_total,
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

    return {
      id: String(issue?.id ?? issue?.rule ?? `issue-${index}`),
      rule: issue?.rule ?? provenanceEntry?.rule,
      title: issue?.title ?? 'Review Required',
      description: issue?.description ?? issue?.message ?? '',
      priority: issue?.severity,
      severity: normalizeSeverity(issue?.severity ?? provenanceEntry?.severity),
      documentName: issue?.document_name ?? issue?.documentName ?? firstDoc ?? docMeta?.name,
      documentType: issue?.document_type ?? issue?.documentType ?? docMeta?.type,
      documents: documentNames,
      expected: formatTextValue(issue?.expected),
      actual: formatTextValue(issue?.found ?? issue?.actual),
      suggestion: formatTextValue(issue?.suggestion ?? issue?.suggested_fix),
      field: issue?.field ?? issue?.metadata?.field,
      ruleset_domain: issue?.ruleset_domain ?? provenanceEntry?.ruleset_domain,
      // Only include references if they have actual content (not empty strings)
      ucpReference: issue?.ucp_reference && issue.ucp_reference.trim() ? issue.ucp_reference.trim() : undefined,
      ucpDescription: issue?.ucp_description ?? undefined,
      isbpReference: issue?.isbp_reference && issue.isbp_reference.trim() ? issue.isbp_reference.trim() : undefined,
      isbpDescription: issue?.isbp_description ?? undefined,
      autoGenerated: issue?.auto_generated ?? false,
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

  console.log('[DOCS_MAPPER_DEBUG] rawDocs type:', typeof rawDocs, 'isArray:', Array.isArray(rawDocs), 'optionEDocuments:', optionEDocuments);

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
