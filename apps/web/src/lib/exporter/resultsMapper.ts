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
    const typeKey = doc?.document_type ?? 'supporting_document';
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
      suggestion: formatTextValue(issue?.suggested_fix),
      field: issue?.field ?? issue?.metadata?.field,
      ucpReference: formatTextValue(issue?.ucp_reference) ?? undefined,
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

  return {
    compliance_score: Math.max(0, Math.min(100, compliance)),
    issue_counts: issueCounts,
    document_risk: documentRisk,
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

export const buildValidationResponse = (raw: any): ValidationResults => {
  const structured = raw?.structured_result as StructuredResultPayload | null;
  if (!structured || structured.version !== 'structured_result_v1') {
    throw new Error('structured_result_v1 payload missing');
  }

  console.log('[DOCS_MAPPER_DEBUG]', structured.documents_structured ?? []);
  const documents = mapDocuments(structured.documents_structured ?? []);
  const issues = mapIssues(structured.issues ?? [], documents);
  const summary = ensureSummary(structured.processing_summary, documents, issues);
  const analytics = ensureAnalytics(structured.analytics, documents, issues);
  const timeline = mapTimeline(structured.lc_structured?.timeline ?? []);

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
  };
};
