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
    const extractionStatus = (doc?.extraction_status ?? 'unknown').toString();

    return {
      id: documentId,
      documentId,
      name: filename,
      filename,
      type: normalizeDocType(typeKey),
      typeKey,
      extractionStatus,
      status: deriveDocumentStatus(extractionStatus, issuesCount),
      issuesCount,
      extractedFields: doc?.extracted_fields ?? {},
    };
  });
};

const mapIssues = (issues: any[] = [], documents: ReturnType<typeof mapDocuments>): IssueCard[] => {
  const lookup = new Map<string, ReturnType<typeof mapDocuments>[number]>();
  documents.forEach((doc) => {
    const candidates = [doc.filename, doc.name, doc.type, doc.typeKey];
    candidates.forEach((candidate) => {
      if (candidate) {
        lookup.set(candidate.toLowerCase(), doc);
      }
    });
  });

  return issues.map((issue, index) => {
    const documentNames = Array.isArray(issue?.documents)
      ? issue.documents
      : issue?.documents
      ? [issue.documents]
      : [];
    const firstDoc = documentNames[0];
    const docMeta = firstDoc ? lookup.get(firstDoc.toLowerCase()) : undefined;

    return {
      id: String(issue?.id ?? issue?.rule ?? `issue-${index}`),
      rule: issue?.rule,
      title: issue?.title ?? 'Review Required',
      description: issue?.description ?? issue?.message ?? '',
      priority: issue?.severity,
      severity: normalizeSeverity(issue?.severity),
      documentName: firstDoc ?? docMeta?.name,
      documentType: docMeta?.type,
      documents: documentNames,
      expected: formatTextValue(issue?.expected),
      actual: formatTextValue(issue?.found ?? issue?.actual),
      suggestion: formatTextValue(issue?.suggestion ?? issue?.suggested_fix),
      field: issue?.field ?? issue?.metadata?.field,
      // Only include references if they have actual content (not empty strings)
      ucpReference: issue?.ucp_reference && issue.ucp_reference.trim() ? issue.ucp_reference.trim() : undefined,
      ucpDescription: issue?.ucp_description ?? undefined,
      isbpReference: issue?.isbp_reference && issue.isbp_reference.trim() ? issue.isbp_reference.trim() : undefined,
      isbpDescription: issue?.isbp_description ?? undefined,
      autoGenerated: issue?.auto_generated ?? false,
    };
  });
};

const summarizeSeverity = (issues: IssueCard[]) =>
  issues.reduce(
    (acc, issue) => {
      const key = normalizeSeverity(issue.severity);
      if (key in acc) {
        acc[key as keyof typeof acc] += 1;
      } else {
        acc.minor += 1;
      }
      return acc;
    },
    { ...DEFAULT_SEVERITY },
  );

const ensureSummary = (payload: any, documents: ReturnType<typeof mapDocuments>, issues: IssueCard[]) => {
  const severity = payload?.severity_breakdown ?? summarizeSeverity(issues);
  const totalDocuments =
    typeof payload?.total_documents === 'number' ? payload.total_documents : documents.length;
  const failed =
    typeof payload?.failed_extractions === 'number'
      ? payload.failed_extractions
      : documents.filter((doc) => doc.status === 'error').length;
  const totalIssues =
    typeof payload?.total_issues === 'number' ? payload.total_issues : issues.length;

  // CANONICAL SOURCE OF TRUTH: Document status counts always derived from the
  // mapped documents array. Never use backend status_counts/document_status
  // directly — they may be stale or computed with different logic.
  // This is the single place all widgets MUST read from.
  const canonicalDocumentStatus = {
    success: documents.filter((d) => d.status === 'success').length,
    warning: documents.filter((d) => d.status === 'warning').length,
    error: documents.filter((d) => d.status === 'error').length,
  };

  const success = canonicalDocumentStatus.success;

  return {
    total_documents: totalDocuments,
    successful_extractions: success,
    failed_extractions: failed,
    total_issues: totalIssues,
    severity_breakdown: severity,
    // CANONICAL: document status distribution - computed from documents, not backend
    document_status: canonicalDocumentStatus,
    canonical_document_status: canonicalDocumentStatus,
    verified: canonicalDocumentStatus.success,
    warnings: canonicalDocumentStatus.warning,
    errors: canonicalDocumentStatus.error,
    // Pass through other useful fields from backend
    compliance_rate: payload?.compliance_rate ?? 0,
    processing_time_display: payload?.processing_time_display ?? 'N/A',
  };
};

const ensureAnalytics = (
  payload: any,
  documents: ReturnType<typeof mapDocuments>,
  issues: IssueCard[],
) => {
  const issueCounts = payload?.issue_counts ?? summarizeSeverity(issues);
  const compliance =
    typeof payload?.compliance_score === 'number'
      ? payload.compliance_score
      : Math.max(0, 100 - issueCounts.critical * 30 - issueCounts.major * 20 - issueCounts.minor * 5);
  const documentRisk = Array.isArray(payload?.document_risk)
    ? payload.document_risk
    : documents.map((doc) => ({
        document_id: doc.documentId,
        filename: doc.name,
        risk: doc.issuesCount >= 3 ? 'high' : doc.issuesCount >= 1 ? 'medium' : 'low',
      }));

  // CANONICAL SOURCE OF TRUTH: Document status distribution always derived
  // from mapped documents array — never from backend analytics field which
  // may have been computed with different thresholds or be stale.
  const canonicalDocumentStatus = {
    success: documents.filter((d) => d.status === 'success').length,
    warning: documents.filter((d) => d.status === 'warning').length,
    error: documents.filter((d) => d.status === 'error').length,
  };

  return {
    compliance_score: Math.max(0, Math.min(100, compliance)),
    issue_counts: issueCounts,
    document_risk: documentRisk,
    // CANONICAL: document status distribution — same source as summary.canonical_document_status
    document_status_distribution: canonicalDocumentStatus,
    documents_processed: payload?.documents_processed ?? documents.length,
    processing_time_display: payload?.processing_time_display ?? 'N/A',
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
  const rawDocs = structured.documents_structured 
    ?? structured.lc_structured?.documents_structured 
    ?? [];
  const optionEDocuments = ensureArray(rawDocs);

  console.log('[DOCS_MAPPER_DEBUG] rawDocs type:', typeof rawDocs, 'isArray:', Array.isArray(rawDocs), 'optionEDocuments:', optionEDocuments);

  const documents = mapDocuments(optionEDocuments);
  
  // Safely extract issues - ensure it's always an array
  const rawIssues = structured.issues ?? [];
  const issues = mapIssues(ensureArray(rawIssues), documents);
  
  const summary = ensureSummary(structured.processing_summary, documents, issues);
  const analytics = ensureAnalytics(structured.analytics, documents, issues);
  
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
