import type { IssueCard, ValidationResults } from '@/hooks/use-lcopilot';

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

const STATUS_ORDER: Record<string, number> = {
  error: 3,
  warning: 2,
  success: 1,
};

const humanizeDocType = (value?: string | null) => {
  if (!value) return DOC_LABELS.supporting_document;
  const normalized = value.toString().toLowerCase().replace(/\s+/g, '_');
  return DOC_LABELS[normalized] ?? value.toString().replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
};

export const formatExpectedFound = (value: any): string => {
  if (value === null || value === undefined) {
    return '—';
  }
  if (typeof value === 'string') {
    return value.trim() || '—';
  }
  if (Array.isArray(value)) {
    return value.map((item) => formatExpectedFound(item)).filter(Boolean).join(', ');
  }
  if (typeof value === 'object') {
    if ('value' in value) {
      return formatExpectedFound(value.value);
    }
    if ('text' in value) {
      return formatExpectedFound(value.text);
    }
    if ('message' in value) {
      return formatExpectedFound(value.message);
    }
    return JSON.stringify(value);
  }
  return String(value);
};

const normalizeDocumentStatuses = (documents: ValidationResults['documents'] = []) => {
  return documents.reduce<Record<string, number>>((acc, doc) => {
    const status = (doc.status || 'success').toLowerCase();
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, { success: 0, warning: 0, error: 0 });
};

const buildDefaultTimeline = (documentCount: number) => {
  const now = new Date();
  const entries = [
    { title: 'Documents Uploaded', status: 'success', description: `${documentCount} document(s) received` },
    { title: 'LC Terms Extracted', status: 'success', description: 'Structured LC context generated' },
    { title: 'Document Cross-Check', status: 'success', description: 'Compared trade docs against LC terms' },
    { title: 'Customs Pack Generated', status: 'success', description: 'Bundle prepared for submission' },
  ];
  return entries.map((event, index) => {
    const timestamp = new Date(now.getTime() - (entries.length - index) * 45 * 1000);
    return { ...event, timestamp: timestamp.toISOString() };
  });
};

const buildDefaultAnalytics = (
  documents: ValidationResults['documents'],
  statusCounts: Record<string, number>,
  processingSummary: ValidationResults['processing_summary'],
) => {
  return {
    extraction_accuracy: 100 - (statusCounts.warning ?? 0) * 2 - (statusCounts.error ?? 0) * 5,
    lc_compliance_score: processingSummary?.compliance_rate ?? 0,
    customs_ready_score: Math.max(0, (processingSummary?.compliance_rate ?? 0) - (statusCounts.warning ?? 0) * 2),
    documents_processed: documents?.length ?? 0,
    document_status_distribution: statusCounts,
    document_processing: (documents || []).map((doc, index) => ({
      name: doc.name,
      type: doc.type,
      status: doc.status,
      processing_time_seconds: Number((0.2 + index * 0.05).toFixed(2)),
      accuracy_score: doc.ocrConfidence ? Math.round(doc.ocrConfidence * 100) : 95,
      compliance_level: doc.status === 'success' ? 'High' : doc.status === 'warning' ? 'Medium' : 'Low',
      risk_level: doc.status === 'success' ? 'Low Risk' : doc.status === 'warning' ? 'Medium Risk' : 'High Risk',
    })),
    performance_insights: [
      `${documents?.length ?? 0} document(s) processed`,
      `${statusCounts.success ?? 0} verified without issues`,
      `Runtime: ${processingSummary?.processing_time_display ?? 'n/a'}`,
    ],
    processing_time_display: processingSummary?.processing_time_display,
  };
};

export const mapDiscrepanciesToUI = (
  rawItems: any[] = [],
  documents: ValidationResults['documents'] = [],
): IssueCard[] => {
  const docStatusMap = new Map<string, { status?: string; type?: string }>();
  documents.forEach((doc) => {
    if (doc.name) {
      docStatusMap.set(doc.name, { status: doc.status, type: doc.type });
    }
  });

  return rawItems.map((item, index) => {
    const documentNames: string[] = [];
    const anyValue = item as any;
    if (Array.isArray(anyValue.document_names)) {
      documentNames.push(...anyValue.document_names);
    }
    if (Array.isArray(anyValue.documents)) {
      documentNames.push(...anyValue.documents);
    }
    if (anyValue.documentName) {
      documentNames.push(anyValue.documentName);
    }

    const documentName = documentNames.find(Boolean);
    const linkedDoc = documentName ? docStatusMap.get(documentName) : undefined;

    return {
      id: String(item.id ?? item.rule ?? `issue-${index}`),
      rule: item.rule,
      title: item.title ?? item.rule ?? 'Review Required',
      description: item.description ?? item.message ?? '',
      severity: item.severity ?? 'minor',
      documentName: documentName,
      documentType:
        item.documentType ??
        linkedDoc?.type ??
        (item.document_type ? humanizeDocType(item.document_type) : undefined),
      expected: formatExpectedFound(item.expected ?? item.expected_value ?? item.expectedValue),
      actual: formatExpectedFound(item.actual ?? item.actual_value ?? item.actualValue ?? item.found),
      suggestion:
        item.suggestion ??
        item.recommendation ??
        item.suggested_fix ??
        item.expected_outcome?.invalid ??
        item.expected_outcome?.message,
      field: item.field ?? item.field_name ?? item.metadata?.field,
    };
  });
};

export const buildValidationResponse = (raw: any): ValidationResults => {
  const normalizedDocuments = Array.isArray(raw?.documents)
    ? raw.documents.map((doc: any, index: number) => {
        const canonicalType =
          doc.documentType ??
          (typeof doc.type === 'string' ? doc.type.replace(/\s+/g, '_').toLowerCase() : undefined);
        return {
          ...doc,
          id: doc.id ?? doc.document_id ?? `${index}`,
          name: doc.name ?? doc.filename ?? `Document ${index + 1}`,
          type: humanizeDocType(canonicalType ?? doc.type),
          documentType: canonicalType ?? doc.type ?? 'supporting_document',
          status: doc.status ?? 'success',
          discrepancyCount: doc.discrepancyCount ?? doc.discrepancies ?? 0,
          extractedFields: doc.extractedFields ?? doc.extracted_fields ?? {},
          ocrConfidence: doc.ocrConfidence ?? doc.ocr_confidence,
          extractionStatus: doc.extractionStatus ?? doc.extraction_status,
        };
      })
    : [];

  const issueCards = mapDiscrepanciesToUI(raw?.issue_cards ?? raw?.discrepancies ?? [], normalizedDocuments);
  const documentStatus = raw?.document_status ?? normalizeDocumentStatuses(normalizedDocuments);
  const totalDocuments = raw?.total_documents ?? normalizedDocuments.length;
  const totalDiscrepancies =
    raw?.total_discrepancies ?? (Array.isArray(raw?.discrepancies) ? raw.discrepancies.length : issueCards.length);
  const processingSummary =
    raw?.processing_summary ??
    ({
      documents: totalDocuments,
      verified: documentStatus.success ?? 0,
      warnings: documentStatus.warning ?? 0,
      errors: documentStatus.error ?? 0,
      compliance_rate: totalDocuments
        ? Math.round(((documentStatus.success ?? 0) / totalDocuments) * 100)
        : 0,
      processing_time_display: raw?.processingTime ?? raw?.processing_time ?? raw?.processingTimeMinutes,
    } satisfies ValidationResults['processing_summary']);

  const analytics =
    raw?.analytics ?? buildDefaultAnalytics(normalizedDocuments, documentStatus, processingSummary ?? {});
  const timeline = raw?.timeline ?? buildDefaultTimeline(totalDocuments);
  const overallStatus =
    raw?.overall_status ??
    (documentStatus.error
      ? 'error'
      : documentStatus.warning
      ? 'warning'
      : raw?.status ?? raw?.overallStatus ?? 'success');

  return {
    ...raw,
    jobId: raw?.jobId ?? raw?.job_id ?? raw?.request_id ?? '',
    job_id: raw?.job_id ?? raw?.jobId ?? raw?.request_id,
    results: raw?.results ?? [],
    discrepancies: raw?.discrepancies ?? [],
    documents: normalizedDocuments,
    issue_cards: issueCards,
    totalDocuments,
    totalDiscrepancies,
    document_status: documentStatus,
    processing_summary: processingSummary,
    analytics,
    timeline,
    overall_status: overallStatus,
  };
};
