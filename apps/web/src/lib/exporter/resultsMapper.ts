import type { StructuredResultPayload, StructuredResultAnalytics, TimelineEntry } from '@shared/types';
import type { IssueCard, ValidationResults, TimelineEvent } from '@/types/lcopilot';

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

const mapDocuments = (docs: any[] = []): ValidationResults['documents'] => {
  return docs.map((doc, index) => {
    const documentId = String(doc?.document_id ?? doc?.id ?? index);
    const filename = doc?.filename ?? doc?.name ?? `Document ${index + 1}`;
    const typeKey = doc?.document_type ?? doc?.type ?? 'supporting_document';
    const issuesCount = Number(doc?.issues_count ?? 0);
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
      extractedFields: doc?.extracted_fields ?? doc?.extractedFields ?? {},
    };
  });
};

const buildDocumentLookup = (documents: ValidationResults['documents']) => {
  const lookup = new Map<string, ValidationResults['documents'][number]>();
  documents.forEach((doc) => {
    const candidates = [doc.filename, doc.name, doc.type, doc.typeKey];
    candidates.forEach((candidate) => {
      if (candidate) {
        lookup.set(candidate.toLowerCase(), doc);
      }
    });
  });
  return lookup;
};

const mapIssues = (issues: any[] = [], documents: ValidationResults['documents']): IssueCard[] => {
  const lookup = buildDocumentLookup(documents);

  return issues.map((issue, index) => {
    const reference = issue?.reference ?? issue?.ucp_reference;
    const priority = issue?.priority ?? issue?.severity;
    const list = issue?.documents ?? issue?.document_names ?? [];
    const normalizedList = Array.isArray(list) ? list : [list];
    const documentNames = normalizedList
      .map((name: any) => (typeof name === 'string' ? name : String(name ?? '')))
      .filter(Boolean);
    const firstDoc = documentNames[0];
    const docMeta = firstDoc ? lookup.get(firstDoc.toLowerCase()) : undefined;

    return {
      id: String(issue?.id ?? issue?.rule ?? `issue-${index}`),
      rule: issue?.rule,
      title: issue?.title ?? 'Review Required',
      description: issue?.description ?? issue?.message ?? '',
      priority,
      severity: normalizeSeverity(priority),
      documentName: firstDoc ?? docMeta?.name,
      documentType: docMeta?.type,
      documents: documentNames,
      expected: formatTextValue(issue?.expected ?? issue?.expected_value),
      actual: formatTextValue(issue?.found ?? issue?.actual ?? issue?.actual_value),
      suggestion: formatTextValue(issue?.suggested_fix ?? issue?.recommendation),
      field: issue?.field ?? issue?.field_name ?? issue?.metadata?.field,
      ucpReference: reference ? formatTextValue(reference) : undefined,
    };
  });
};

const summarizeSeverity = (issues: IssueCard[]): typeof DEFAULT_SEVERITY => {
  return issues.reduce(
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
};

const ensureSummary = (
  payload: any,
  documents: ValidationResults['documents'],
  issues: IssueCard[],
): ValidationResults['summary'] => {
  const severity = payload?.severity_breakdown ?? summarizeSeverity(issues);
  const totalDocuments =
    typeof payload?.total_documents === 'number' ? payload.total_documents : documents.length;
  const success =
    typeof payload?.successful_extractions === 'number'
      ? payload.successful_extractions
      : documents.filter((doc) => doc.status === 'success').length;
  const failed =
    typeof payload?.failed_extractions === 'number'
      ? payload.failed_extractions
      : Math.max(0, totalDocuments - success);
  const totalIssues =
    typeof payload?.total_issues === 'number' ? payload.total_issues : issues.length;

  return {
    total_documents: totalDocuments,
    successful_extractions: success,
    failed_extractions: failed,
    total_issues: totalIssues,
    severity_breakdown: severity,
  };
};

const ensureAnalytics = (
  payload: any,
  summary: ValidationResults['summary'],
  documents: ValidationResults['documents'],
): ValidationResults['analytics'] => {
  const issueCounts = payload?.issue_counts ?? summary.severity_breakdown ?? { ...DEFAULT_SEVERITY };
  const compliance =
    typeof payload?.compliance_score === 'number'
      ? payload.compliance_score
      : Math.max(
          0,
          100 - issueCounts.critical * 30 - issueCounts.major * 20 - issueCounts.minor * 5,
        );
  const documentRisk = Array.isArray(payload?.document_risk)
    ? payload.document_risk.map((entry: any) => ({
        document_id: entry?.document_id,
        filename: entry?.filename,
        risk: entry?.risk ?? 'low',
      }))
    : documents.map((doc) => ({
        document_id: doc.documentId,
        filename: doc.name,
        risk: doc.issuesCount >= 3 ? 'high' : doc.issuesCount >= 1 ? 'medium' : 'low',
      }));

  return {
    compliance_score: Math.max(0, Math.min(100, compliance)),
    issue_counts: issueCounts,
    document_risk: documentRisk,
  };
};

const mapTimeline = (entries: Array<Partial<TimelineEntry>> = []): ValidationResults['timeline'] => {
  return entries
    .map((entry, index) => ({
      title: entry?.title ?? entry?.label ?? `Step ${index + 1}`,
      status: entry?.status ?? 'pending',
      description: entry?.description ?? entry?.detail,
      timestamp: entry?.timestamp ?? entry?.time,
    }))
    .filter((entry) => Boolean(entry.title));
};

const structuredFromNormalized = (
  summary: ValidationResults['summary'],
  documents: ValidationResults['documents'],
  issues: IssueCard[],
  analytics: ValidationResults['analytics'],
  timeline: ValidationResults['timeline'],
): StructuredResultPayload => {
  return {
    processing_summary: summary,
    documents: documents.map((doc) => ({
      document_id: doc.documentId,
      document_type: doc.typeKey ?? doc.type,
      filename: doc.name,
      extraction_status: doc.extractionStatus,
      extracted_fields: doc.extractedFields ?? {},
      issues_count: doc.issuesCount ?? 0,
    })),
    issues: issues.map((issue) => ({
      id: issue.id,
      title: issue.title,
      severity: normalizeSeverity(issue.severity),
      documents: issue.documents ?? (issue.documentName ? [issue.documentName] : []),
      expected: formatTextValue(issue.expected),
      found: formatTextValue(issue.actual),
      suggested_fix: formatTextValue(issue.suggestion),
      description: issue.description ?? '',
      ucp_reference: issue.ucpReference,
    })),
    analytics,
    timeline: timeline.map((entry) => ({
      title: entry.title ?? entry.label,
      label: entry.label ?? entry.title,
      status: entry.status,
      description: entry.description,
      timestamp: entry.timestamp,
    })),
  };
};

export const buildValidationResponse = (raw: any): ValidationResults => {
  const structured = raw?.structured_result as StructuredResultPayload | undefined;

  if (structured) {
    const documents = mapDocuments(structured.documents ?? []);
    const issues = mapIssues(structured.issues ?? [], documents);
    const summary = ensureSummary(structured.processing_summary, documents, issues);
    const analytics = ensureAnalytics(structured.analytics, summary, documents);
    const timeline = mapTimeline(structured.timeline ?? []);
    const normalizedStructuredResult: StructuredResultPayload = {
      processing_summary: structured.processing_summary ?? summary,
      documents: Array.isArray(structured.documents) ? structured.documents : [],
      issues: Array.isArray(structured.issues) ? structured.issues : [],
      analytics: normalizeStructuredAnalytics(structured.analytics, analytics),
      timeline: normalizeStructuredTimeline(structured.timeline ?? timeline, timeline),
    };

    return {
      ...raw,
      jobId: raw?.jobId ?? raw?.job_id ?? raw?.request_id ?? '',
      summary,
      documents,
      issues,
      analytics,
      timeline,
      processing_summary: summary,
      issue_cards: issues,
      structured_result: normalizedStructuredResult,
    };
  }

  const structuredTimeline = raw?.structured_result?.timeline;
  const hasStructuredDocs = Array.isArray(raw?.structured_result?.documents) && raw.structured_result.documents.length > 0;
  const hasStructuredIssues = Array.isArray(raw?.structured_result?.issues) && raw.structured_result.issues.length > 0;

  const documentSource = hasStructuredDocs ? raw.structured_result.documents : raw?.documents ?? [];
  const issueSource =
    hasStructuredIssues ? raw.structured_result.issues : raw?.issue_cards ?? raw?.discrepancies ?? [];

  const documents = mapDocuments(documentSource);
  const issues = mapIssues(issueSource, documents);
  const summary = ensureSummary(raw?.processing_summary, documents, issues);
  const analytics = ensureAnalytics(raw?.analytics, summary, documents);
  const timeline = mapTimeline(structuredTimeline ?? raw?.timeline);

  const normalizedStructuredResult: StructuredResultPayload =
    raw?.structured_result && (hasStructuredDocs || hasStructuredIssues || structuredTimeline)
      ? {
          processing_summary: raw.structured_result.processing_summary ?? summary,
          documents: raw.structured_result.documents ?? [],
          issues: raw.structured_result.issues ?? [],
          analytics: normalizeStructuredAnalytics(raw.structured_result.analytics, analytics),
          timeline: normalizeStructuredTimeline(raw.structured_result.timeline, timeline),
      }
      : structuredFromNormalized(summary, documents, issues, analytics, timeline);
  return {
    ...raw,
    jobId: raw?.jobId ?? raw?.job_id ?? raw?.request_id ?? '',
    summary,
    documents,
    issues,
    analytics,
    timeline,
    processing_summary: summary,
    issue_cards: issues,
    structured_result: normalizedStructuredResult,
  };
};

const normalizeStructuredAnalytics = (
  analytics: StructuredResultAnalytics | undefined,
  fallback: ValidationResults['analytics'],
): StructuredResultAnalytics => {
  if (!analytics) {
    return {
      compliance_score: fallback.compliance_score,
      issue_counts: fallback.issue_counts,
      document_risk: fallback.document_risk,
    };
  }

  return {
    compliance_score:
      typeof analytics.compliance_score === 'number'
        ? analytics.compliance_score
        : fallback.compliance_score,
    issue_counts: analytics.issue_counts ?? fallback.issue_counts,
    document_risk:
      Array.isArray(analytics.document_risk) && analytics.document_risk.length > 0
        ? analytics.document_risk
        : fallback.document_risk,
  };
};

const normalizeStructuredTimeline = (
  timeline: any,
  fallback: TimelineEvent[],
): TimelineEvent[] => {
  if (!Array.isArray(timeline)) {
    return fallback;
  }
  return mapTimeline(timeline);
};
