import type { StructuredResultPayload, ExtractionStatus, ComplianceStatus } from '@shared/types';
import { mapExtractionToUiStatus, CanonicalSemanticsSchema } from '@shared/types';
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

const normalizeLookupKey = (value: unknown) => {
  if (value === null || value === undefined) {
    return '';
  }
  return String(value)
    .toLowerCase()
    .trim()
    .replace(/\.[^/.]+$/u, '') // drop file extension
    .replace(/[^a-z0-9]/gu, '');
};

const normalizeDocType = (value?: string | null) => {
  if (!value) {
    return DOC_LABELS.supporting_document;
  }
  const normalized = value.toString().toLowerCase().replace(/\s+/g, '_');
  return DOC_LABELS[normalized] ?? value.toString().replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
};

const normalizeExtractionStatus = (value: unknown): ExtractionStatus => {
  const token = String(value ?? '').toLowerCase();
  if (token === 'success') return 'success';
  if (token === 'failed' || token === 'error' || token === 'empty') return 'failed';
  return 'partial';
};

const deriveDocumentStatus = (extractionStatus: ExtractionStatus): 'success' | 'warning' | 'error' =>
  mapExtractionToUiStatus(extractionStatus);

const deriveComplianceStatus = (doc: any): ComplianceStatus => {
  const token = String(doc?.compliance_status ?? '').toLowerCase();
  if (token === 'reject') return 'reject';
  if (token === 'warning') return 'warning';
  return 'clean';
};

const PLACEHOLDER_TOKENS = new Set(['', '—', '-', '--', 'n/a', 'na', 'none', 'null', 'undefined', 'unknown']);

const isPlaceholderText = (value: unknown): boolean => {
  if (value === null || value === undefined) return true;
  const normalized = String(value).trim().toLowerCase();
  return PLACEHOLDER_TOKENS.has(normalized);
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

const isRecord = (value: unknown): value is Record<string, unknown> =>
  Boolean(value) && typeof value === 'object' && !Array.isArray(value);

const isNonEmptyRecord = (value: unknown): value is Record<string, unknown> =>
  isRecord(value) && Object.keys(value).length > 0;

const resolveStructuredDocPayload = (
  structured: StructuredResultPayload | null | undefined,
  typeKey: string | null | undefined,
) => {
  if (!structured || !typeKey) return undefined;
  const extractedDocuments =
    structured.extracted_documents
    ?? (structured as any).extractedDocuments
    ?? (structured as any).extracted_data
    ?? (structured as any).extractedData;

  const lcStructured = structured.lc_structured ?? (structured as any).lcStructured;
  const extractedDoc = isRecord(extractedDocuments) ? extractedDocuments[typeKey] : undefined;
  const lcDoc = isRecord(lcStructured) ? lcStructured[typeKey] : undefined;

  if (isNonEmptyRecord(extractedDoc)) return extractedDoc;
  if (isNonEmptyRecord(lcDoc)) return lcDoc;
  if (isRecord(extractedDoc)) return extractedDoc;
  if (isRecord(lcDoc)) return lcDoc;
  return undefined;
};

const getNestedValue = (source: any, path: string) => {
  if (!source || !path) return undefined;
  const parts = path.split('.');
  let cursor: any = source;
  for (const part of parts) {
    if (!cursor || typeof cursor !== 'object') return undefined;
    cursor = cursor[part];
  }
  return cursor;
};

const normalizeAmountValue = (value: any) => {
  if (!value) return undefined;
  if (typeof value === 'object') {
    const amount = value.value ?? value.amount ?? value.total;
    const currency = value.currency ?? value.ccy;
    if (amount && currency) return `${amount} ${currency}`;
    if (amount) return String(amount);
  }
  return value;
};

const setIfMeaningful = (target: Record<string, unknown>, key: string, value: any) => {
  if (value === null || value === undefined) return;
  const formatted = formatTextValue(value);
  if (isPlaceholderText(formatted)) return;
  if (target[key] === undefined || target[key] === null || isPlaceholderText(formatTextValue(target[key]))) {
    target[key] = value;
  }
};

const normalizeDocumentFields = (fields: Record<string, unknown>, typeKey?: string) => {
  if (!typeKey) return {};
  const canonical: Record<string, unknown> = {};

  const pick = (paths: string[]) => {
    for (const path of paths) {
      const candidate = getNestedValue(fields, path);
      if (candidate !== undefined && candidate !== null) return candidate;
    }
    return undefined;
  };

  switch (typeKey) {
    case 'letter_of_credit': {
      setIfMeaningful(canonical, 'lc_number', pick(['lc_number', 'number', 'lc_no', 'lcNo', 'lcNumber']));
      setIfMeaningful(canonical, 'lc_type', pick(['lc_type', 'type', 'lcType']));
      setIfMeaningful(canonical, 'applicant', pick(['applicant', 'applicant_name']));
      setIfMeaningful(canonical, 'beneficiary', pick(['beneficiary', 'beneficiary_name']));
      setIfMeaningful(canonical, 'issuing_bank', pick(['issuing_bank', 'issuingBank', 'issuing_bank_name']));
      setIfMeaningful(canonical, 'advising_bank', pick(['advising_bank', 'advisingBank', 'advising_bank_name']));
      const amount = normalizeAmountValue(pick(['amount', 'lc_amount', 'amounts', 'lc_amounts']));
      setIfMeaningful(canonical, 'total_amount', amount);
      setIfMeaningful(canonical, 'currency', pick(['currency', 'amount.currency', 'lc_amount.currency']));
      setIfMeaningful(canonical, 'issue_date', pick(['issue_date', 'issueDate', 'dates.issue']));
      setIfMeaningful(canonical, 'expiry_date', pick(['expiry_date', 'expiryDate', 'dates.expiry']));
      setIfMeaningful(canonical, 'latest_shipment', pick(['latest_shipment', 'latestShipment', 'dates.latest_shipment']));
      setIfMeaningful(canonical, 'port_of_loading', pick(['port_of_loading', 'ports.loading', 'loading_port']));
      setIfMeaningful(canonical, 'port_of_discharge', pick(['port_of_discharge', 'ports.discharge', 'discharge_port']));
      setIfMeaningful(canonical, 'goods_description', pick(['goods_description', 'goods', 'description']));
      setIfMeaningful(canonical, 'incoterm', pick(['incoterm', 'incoterms']));
      setIfMeaningful(canonical, 'ucp_reference', pick(['ucp_reference', 'ucp', 'ucp_rules']));
      setIfMeaningful(canonical, 'additional_conditions', pick(['additional_conditions', 'conditions', 'clauses', 'terms']));
      break;
    }
    case 'commercial_invoice': {
      setIfMeaningful(canonical, 'invoice_number', pick(['invoice_number', 'invoiceNo', 'invoice_no', 'number']));
      setIfMeaningful(canonical, 'invoice_date', pick(['invoice_date', 'invoiceDate', 'date']));
      setIfMeaningful(canonical, 'goods_description', pick(['goods_description', 'goods', 'description', 'item_description']));
      const amount = normalizeAmountValue(pick(['invoice_amount', 'total_amount', 'amount', 'invoice_total', 'total']));
      setIfMeaningful(canonical, 'total_amount', amount);
      setIfMeaningful(canonical, 'currency', pick(['currency', 'invoice_amount.currency', 'amount.currency']));
      setIfMeaningful(canonical, 'shipper', pick(['shipper', 'seller', 'exporter', 'beneficiary']));
      setIfMeaningful(canonical, 'consignee', pick(['consignee', 'buyer', 'applicant']));
      break;
    }
    case 'bill_of_lading': {
      setIfMeaningful(canonical, 'bl_number', pick(['bl_number', 'bol_number', 'bill_of_lading_number', 'number']));
      setIfMeaningful(canonical, 'bl_date', pick(['bl_date', 'date', 'issue_date']));
      setIfMeaningful(canonical, 'on_board_date', pick(['on_board_date', 'shipped_on_board_date', 'onBoardDate']));
      setIfMeaningful(canonical, 'vessel_name', pick(['vessel_name', 'vessel', 'ship_name']));
      setIfMeaningful(canonical, 'voyage_number', pick(['voyage_number', 'voyage']));
      setIfMeaningful(canonical, 'port_of_loading', pick(['port_of_loading', 'ports.loading', 'loading_port', 'port_loading']));
      setIfMeaningful(canonical, 'port_of_discharge', pick(['port_of_discharge', 'ports.discharge', 'discharge_port', 'port_discharge']));
      setIfMeaningful(canonical, 'shipper', pick(['shipper']));
      setIfMeaningful(canonical, 'consignee', pick(['consignee']));
      setIfMeaningful(canonical, 'notify_party', pick(['notify_party', 'notify']));
      setIfMeaningful(canonical, 'container_number', pick(['container_number', 'container_no', 'container']));
      setIfMeaningful(canonical, 'seal_number', pick(['seal_number', 'seal_no', 'seal']));
      setIfMeaningful(canonical, 'marks_and_numbers', pick(['marks_and_numbers', 'marks']));
      setIfMeaningful(canonical, 'gross_weight', pick(['gross_weight', 'weight_gross']));
      setIfMeaningful(canonical, 'net_weight', pick(['net_weight', 'weight_net']));
      setIfMeaningful(canonical, 'measurement', pick(['measurement', 'measurements']));
      setIfMeaningful(canonical, 'number_of_packages', pick(['number_of_packages', 'packages', 'package_count']));
      setIfMeaningful(canonical, 'package_type', pick(['package_type', 'packages_type']));
      setIfMeaningful(canonical, 'freight_prepaid', pick(['freight_prepaid', 'freight', 'freight_terms']));
      break;
    }
    case 'packing_list': {
      setIfMeaningful(canonical, 'number_of_packages', pick(['number_of_packages', 'packages', 'package_count']));
      setIfMeaningful(canonical, 'gross_weight', pick(['gross_weight', 'weight_gross']));
      setIfMeaningful(canonical, 'net_weight', pick(['net_weight', 'weight_net']));
      setIfMeaningful(canonical, 'measurement', pick(['measurement', 'measurements']));
      setIfMeaningful(canonical, 'marks_and_numbers', pick(['marks_and_numbers', 'marks']));
      setIfMeaningful(canonical, 'package_type', pick(['package_type', 'packages_type']));
      setIfMeaningful(canonical, 'goods_description', pick(['goods_description', 'goods', 'description']));
      break;
    }
    case 'certificate_of_origin': {
      setIfMeaningful(canonical, 'origin_country', pick(['origin_country', 'country_of_origin', 'origin']));
      setIfMeaningful(canonical, 'goods_description', pick(['goods_description', 'goods', 'description']));
      setIfMeaningful(canonical, 'issuer', pick(['issuer', 'issued_by']));
      break;
    }
    case 'insurance_certificate': {
      setIfMeaningful(canonical, 'policy_number', pick(['policy_number', 'insurance_policy_number']));
      const amount = normalizeAmountValue(pick(['insured_value', 'coverage_amount', 'amount']));
      setIfMeaningful(canonical, 'total_amount', amount);
      setIfMeaningful(canonical, 'currency', pick(['currency', 'insured_value.currency', 'amount.currency']));
      break;
    }
    default:
      break;
  }

  return canonical;
};

const resolveExtractedFields = (
  doc: any,
  structured?: StructuredResultPayload | null,
  typeKey?: string,
): Record<string, unknown> => {
  const candidates = [
    doc?.extracted_fields,
    doc?.extractedFields,
    doc?.structured_fields,
    doc?.structuredFields,
    doc?.fields,
    doc?.field_values,
    doc?.extracted_data,
    doc?.extractedData,
    doc?.structured_result,
    doc?.structuredResult,
  ];

  const unwrapCandidate = (value: unknown): Record<string, unknown> | null => {
    if (!isRecord(value)) return null;
    const nested =
      value.structured_fields ??
      value.structuredFields ??
      value.extracted_fields ??
      value.extractedFields ??
      value.fields ??
      value.field_values ??
      value.extracted_data ??
      value.extractedData;

    if (isRecord(nested)) {
      return nested as Record<string, unknown>;
    }

    return null;
  };

  const normalizedCandidates = candidates.flatMap((candidate) => {
    const unwrapped = unwrapCandidate(candidate);
    return unwrapped ? [unwrapped, candidate] : [candidate];
  });

  const nonEmpty = normalizedCandidates.find(isNonEmptyRecord);
  const baseRecord = nonEmpty ?? normalizedCandidates.find(isRecord) ?? {};
  const structuredDoc = resolveStructuredDocPayload(structured, typeKey);
  const structuredFallback = isNonEmptyRecord(structuredDoc)
    ? structuredDoc
    : isRecord(structuredDoc)
    ? structuredDoc
    : undefined;

  const base = (isNonEmptyRecord(baseRecord)
    ? baseRecord
    : structuredFallback ?? baseRecord) as Record<string, unknown>;

  const resolved = { ...(base ?? {}) } as Record<string, unknown>;
  const normalized = normalizeDocumentFields(resolved, typeKey);
  Object.assign(resolved, normalized);

  const hasStructuredKeys = Object.keys(resolved).some(
    (key) => !key.startsWith('_') && key !== 'raw_text_preview' && key !== 'raw_text',
  );

  const previewText =
    doc?.raw_text_preview
    ?? doc?.rawTextPreview
    ?? doc?.text_preview
    ?? doc?.textPreview
    ?? doc?.preview_text
    ?? doc?.previewText
    ?? doc?.raw_text
    ?? doc?.rawText
    ?? doc?.extracted_text
    ?? doc?.extractedText
    ?? doc?.text;

  if (!hasStructuredKeys && typeof previewText === 'string' && previewText.trim()) {
    const metadata = Object.fromEntries(
      Object.entries(resolved).filter(([key]) => key.startsWith('_')),
    );
    return { ...metadata, raw_text_preview: previewText.trim() };
  }

  return resolved;
};

const mapDocuments = (docs: any[] = [], structured?: StructuredResultPayload | null) => {
  return docs.map((doc, index) => {
    const documentId = String(doc?.document_id ?? doc?.id ?? index);
    const filename = doc?.filename ?? doc?.name ?? `Document ${index + 1}`;
    // Ensure typeKey is a string - handle case where backend returns object like {types: [...]}
    const rawType = doc?.document_type ?? 'supporting_document';
    const typeKey = typeof rawType === 'string' ? rawType : 'supporting_document';
    // Check multiple possible keys for issue count (backend uses discrepancyCount)
    const issuesCount = Number(doc?.discrepancyCount ?? doc?.issues_count ?? doc?.issuesCount ?? 0);
    const extractionStatus = normalizeExtractionStatus(doc?.extraction_status ?? doc?.extractionStatus);
    const complianceStatus = deriveComplianceStatus(doc);
    const failedReason = doc?.failed_reason ?? doc?.failedReason ?? null;
    if (CanonicalSemanticsSchema && typeof CanonicalSemanticsSchema.parse === 'function') {
      CanonicalSemanticsSchema.parse({
        extraction_status: extractionStatus,
        compliance_status: complianceStatus,
        pipeline_verification_status: 'VERIFIED',
        failed_reason: failedReason,
      });
    }

    const status = deriveDocumentStatus(extractionStatus);

    return {
      id: documentId,
      documentId,
      name: filename,
      filename,
      type: normalizeDocType(typeKey),
      typeKey,
      extractionStatus,
      complianceStatus,
      failedReason,
      status,
      issuesCount,
      extractedFields: resolveExtractedFields(doc, structured, typeKey),
    };
  });
};

const pickFirstMeaningful = (...candidates: any[]): string => {
  for (const candidate of candidates) {
    const formatted = formatTextValue(candidate);
    if (!isPlaceholderText(formatted)) {
      return formatted;
    }
  }
  return '—';
};

const mapIssues = (issues: any[] = [], documents: ReturnType<typeof mapDocuments>): IssueCard[] => {
  const lookup = new Map<string, ReturnType<typeof mapDocuments>[number]>();
  documents.forEach((doc) => {
    const candidates = [doc.filename, doc.name, doc.type, doc.typeKey];
    candidates.forEach((candidate) => {
      const key = normalizeLookupKey(candidate);
      if (key) {
        lookup.set(key, doc);
      }
    });
  });

  return issues.map((issue, index) => {
    const documentNames = Array.isArray(issue?.documents)
      ? issue.documents
      : issue?.documents
      ? [issue.documents]
      : [];
    const normalizedDocumentNames = documentNames
      .map((name: unknown) => normalizeLookupKey(name))
      .filter(Boolean);

    const firstDoc = documentNames[0];
    const firstDocLookup = normalizedDocumentNames[0]
      ? lookup.get(normalizedDocumentNames[0])
      : undefined;
    const docType = issue?.document_type ? String(issue.document_type) : undefined;
    const docMeta =
      firstDocLookup
      ?? (docType ? lookup.get(normalizeLookupKey(docType)) : undefined);

    const expected = pickFirstMeaningful(
      issue?.expected,
      issue?.evaluated_expected,
      issue?.metadata?.expected,
      issue?.context?.expected,
      issue?.lc_value,
      issue?.baseline_value,
    );
    const actual = pickFirstMeaningful(
      issue?.found,
      issue?.actual,
      issue?.evaluated_found,
      issue?.metadata?.found,
      issue?.context?.found,
      issue?.document_value,
      issue?.observed_value,
    );

    // Drop low-value issue cards with no concrete evidence for user-facing Issues tab.
    if (isPlaceholderText(expected) && isPlaceholderText(actual)) {
      return null;
    }

    return {
      id: String(issue?.id ?? issue?.rule ?? `issue-${index}`),
      rule: issue?.rule,
      title: issue?.title ?? 'Review Required',
      description: issue?.description ?? issue?.message ?? '',
      priority: issue?.severity,
      severity: normalizeSeverity(issue?.severity),
      documentName: docMeta?.name ?? firstDoc,
      documentType: docMeta?.type,
      documents: documentNames,
      expected,
      actual,
      suggestion: formatTextValue(issue?.suggestion ?? issue?.suggested_fix),
      field: issue?.field ?? issue?.metadata?.field,
      // Only include references if they have actual content (not empty strings)
      ucpReference: issue?.ucp_reference && issue.ucp_reference.trim() ? issue.ucp_reference.trim() : undefined,
      ucpDescription: issue?.ucp_description ?? undefined,
      isbpReference: issue?.isbp_reference && issue.isbp_reference.trim() ? issue.isbp_reference.trim() : undefined,
      isbpDescription: issue?.isbp_description ?? undefined,
      autoGenerated: issue?.auto_generated ?? false,
    };
  }).filter(Boolean) as IssueCard[];
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

const reconcileDocumentIssueCounts = (
  documents: ReturnType<typeof mapDocuments>,
  issues: IssueCard[],
): ReturnType<typeof mapDocuments> => {
  const lookup = new Map<string, string>();
  const counts = new Map<string, number>();

  documents.forEach((doc) => {
    counts.set(doc.id, 0);
    [doc.filename, doc.name, doc.type, doc.typeKey].forEach((candidate) => {
      const key = normalizeLookupKey(candidate);
      if (key) lookup.set(key, doc.id);
    });
  });

  const fallbackDocId =
    documents.find((doc) => String(doc.typeKey).toLowerCase() === 'letter_of_credit')?.id
    ?? documents[0]?.id
    ?? null;

  issues.forEach((issue) => {
    const rawCandidates: unknown[] = [
      ...(Array.isArray(issue.documents) ? issue.documents : []),
      issue.documentName,
      issue.documentType,
    ];

    const matched = new Set<string>();
    rawCandidates.forEach((candidate) => {
      const key = normalizeLookupKey(candidate);
      const docId = key ? lookup.get(key) : undefined;
      if (docId) matched.add(docId);
    });

    if (matched.size === 0 && fallbackDocId) {
      matched.add(fallbackDocId);
    }

    matched.forEach((docId) => {
      counts.set(docId, (counts.get(docId) ?? 0) + 1);
    });
  });

  return documents.map((doc) => ({
    ...doc,
    issuesCount: counts.get(doc.id) ?? 0,
  }));
};

const ensureSummary = (payload: any, documents: ReturnType<typeof mapDocuments>, issues: IssueCard[]) => {
  const severity = summarizeSeverity(issues);
  const totalDocuments =
    typeof payload?.total_documents === 'number' ? payload.total_documents : documents.length;
  const totalIssues = documents.reduce((acc, doc) => acc + (Number(doc?.issuesCount) || 0), 0);

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
  const failed = canonicalDocumentStatus.error;

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
  // P0 invariant: issue counts in analytics must always come from visible mapped issues.
  // Never trust backend issue_counts directly, as stale values cause UI/API contradiction.
  const canonicalIssueCounts = summarizeSeverity(issues);

  const payloadCompliance =
    typeof payload?.compliance_score === 'number' ? payload.compliance_score : null;
  const derivedCompliance = Math.max(
    0,
    100 - canonicalIssueCounts.critical * 30 - canonicalIssueCounts.major * 20 - canonicalIssueCounts.minor * 5,
  );

  // P0 invariant: if critical issues exist, compliance cannot be emitted as a passing score.
  const compliance =
    canonicalIssueCounts.critical > 0
      ? 0
      : payloadCompliance !== null
      ? payloadCompliance
      : derivedCompliance;

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
    issue_counts: canonicalIssueCounts,
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
    ?? (structured as any).documents
    ?? structured.lc_structured?.documents_structured 
    ?? [];
  const optionEDocuments = ensureArray(rawDocs);

  console.log('[DOCS_MAPPER_DEBUG] rawDocs type:', typeof rawDocs, 'isArray:', Array.isArray(rawDocs), 'optionEDocuments:', optionEDocuments);

  const normalizedRawDocs = optionEDocuments.map((doc: any) => {
    const rawType = doc?.document_type ?? doc?.type ?? 'supporting_document';
    const typeKey = typeof rawType === 'string' ? rawType : 'supporting_document';
    const normalizedFields = resolveExtractedFields(doc, structured, typeKey);
    return {
      ...doc,
      extracted_fields: normalizedFields,
    };
  });

  const structuredResult = {
    ...structured,
    documents_structured: normalizedRawDocs,
    lc_structured: structured.lc_structured && typeof structured.lc_structured === 'object'
      ? { ...structured.lc_structured, documents_structured: normalizedRawDocs }
      : structured.lc_structured ?? null,
  } as StructuredResultPayload;

  const documents = mapDocuments(normalizedRawDocs, structuredResult);
  
  // Safely extract issues - ensure it's always an array
  const rawIssues = structuredResult.issues ?? [];
  const issues = mapIssues(ensureArray(rawIssues), documents);

  // Canonical issue count source for document rows must align with visible issue cards.
  // This prevents Documents-tab badge totals from drifting from Issues-tab totals.
  const reconciledDocuments = reconcileDocumentIssueCounts(documents, issues);

  const summary = ensureSummary(structuredResult.processing_summary, reconciledDocuments, issues);
  const analytics = ensureAnalytics(structuredResult.analytics, reconciledDocuments, issues);
  
  // Safely extract timeline
  const rawTimeline = structuredResult.lc_structured?.timeline ?? structuredResult.timeline ?? [];
  const timeline = mapTimeline(ensureArray(rawTimeline));

  // V2 Validation Pipeline fields
  const validationBlocked = Boolean(structuredResult.validation_blocked);
  const validationStatus = structuredResult.validation_status ?? (validationBlocked ? 'blocked' : 'non_compliant');
  const gateResult = structuredResult.gate_result ?? null;
  const extractionSummary = structuredResult.extraction_summary ?? null;
  const lcBaseline = structuredResult.lc_baseline ?? null;
  const complianceLevel = structuredResult.analytics?.compliance_level ?? validationStatus;
  const complianceCapReason = structuredResult.analytics?.compliance_cap_reason ?? null;

  // Sanctions Screening fields
  const sanctionsScreening = structuredResult.sanctions_screening ?? null;
  const sanctionsBlocked = Boolean(structuredResult.sanctions_blocked);
  const sanctionsBlockReason = structuredResult.sanctions_block_reason ?? null;

  // Contract Validation fields (Output-First layer)
  const contractWarnings = ensureArray((structuredResult as any)._contract_warnings ?? []);
  const contractValidation = (structuredResult as any)._contract_validation ?? null;

  return {
    jobId: raw?.jobId ?? raw?.job_id ?? '',
    summary,
    documents: reconciledDocuments,
    issues,
    analytics,
    timeline,
    structured_result: structuredResult,
    lc_structured: structuredResult.lc_structured ?? null,
    ai_enrichment: structuredResult.ai_enrichment ?? null,
    
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
