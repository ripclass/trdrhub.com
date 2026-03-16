import type { DiscrepancyInfo, ValidationSession } from '@/api/sessions';
import {
  getCanonicalResultTruth,
  type CanonicalResultTruth,
} from '@/lib/lcopilot/resultTruth';
import type {
  IssueCard,
  OptionEStructuredResult,
  ValidationResults,
} from '@/types/lcopilot';

export type ExporterSessionState = 'ready' | 'review' | 'blocked' | 'completed';

export interface ExporterSessionTruth {
  lcNumber: string;
  documentCount: number;
  issueCount: number;
  overallStatus: 'success' | 'warning' | 'error';
  statusLabel: string;
  state: ExporterSessionState;
  canSubmit: boolean;
  canonical: boolean;
  truth: CanonicalResultTruth | null;
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const coerceString = (value: unknown): string | null => {
  if (typeof value !== 'string') {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const getFallbackIssues = (discrepancies: DiscrepancyInfo[] = []): IssueCard[] =>
  discrepancies.map((discrepancy) => ({
    severity: discrepancy.severity,
    title: discrepancy.description,
    rule: discrepancy.rule_name,
  })) as IssueCard[];

export const extractSessionStructuredResult = (
  session: ValidationSession,
): OptionEStructuredResult | null => {
  const payload = session.validation_results;
  if (!isRecord(payload)) {
    return null;
  }

  if (payload.version === 'structured_result_v1') {
    return payload as OptionEStructuredResult;
  }

  const nested = payload.structured_result;
  if (isRecord(nested) && nested.version === 'structured_result_v1') {
    return nested as OptionEStructuredResult;
  }

  return null;
};

export const getSessionLcNumber = (session: ValidationSession): string => {
  const structuredResult = extractSessionStructuredResult(session);
  const candidates = [
    structuredResult?.lc_number,
    structuredResult?.number,
    structuredResult?.lc_structured?.lc_number,
    session.extracted_data?.lc_number,
  ];

  for (const candidate of candidates) {
    const value = coerceString(candidate);
    if (value) {
      return value;
    }
  }

  return session.id.slice(0, 8).toUpperCase();
};

export const getSessionDocumentCount = (session: ValidationSession): number => {
  const structuredResult = extractSessionStructuredResult(session);
  const structuredDocuments =
    structuredResult?.documents ??
    structuredResult?.documents_structured ??
    [];

  if (Array.isArray(structuredDocuments) && structuredDocuments.length > 0) {
    return structuredDocuments.length;
  }

  if (typeof session.total_documents === "number") {
    return session.total_documents;
  }

  return session.documents?.length || 0;
};

export const getSessionIssueCount = (session: ValidationSession): number => {
  const structuredResult = extractSessionStructuredResult(session);
  const structuredIssues = structuredResult?.issues;
  if (Array.isArray(structuredIssues)) {
    return structuredIssues.length;
  }

  if (typeof session.total_discrepancies === "number") {
    return session.total_discrepancies;
  }

  return session.discrepancies?.length || 0;
};

export const getExporterSessionTruth = (
  session: ValidationSession,
): ExporterSessionTruth => {
  const structuredResult = extractSessionStructuredResult(session);
  const lcNumber = getSessionLcNumber(session);
  const documentCount = getSessionDocumentCount(session);
  const issueCount = getSessionIssueCount(session);

  if (structuredResult) {
    const issues = Array.isArray(structuredResult.issues)
      ? (structuredResult.issues as IssueCard[])
      : getFallbackIssues(session.discrepancies);
    const truth = getCanonicalResultTruth({
      structured_result: structuredResult,
      issues,
    } as Pick<ValidationResults, 'issues' | 'structured_result'>);

    const readyWithCautions =
      truth.readinessLabel === 'Ready' && truth.overallStatus === 'warning';
    const statusLabel = readyWithCautions
      ? 'Ready with cautions'
      : truth.readinessLabel;
    const state: ExporterSessionState =
      truth.readinessLabel === 'Blocked'
        ? 'blocked'
        : truth.canSubmitFromValidation
        ? 'ready'
        : 'review';

    return {
      lcNumber,
      documentCount,
      issueCount,
      overallStatus: truth.overallStatus,
      statusLabel,
      state,
      canSubmit: truth.canSubmitFromValidation,
      canonical: true,
      truth,
    };
  }

  if (session.status === 'failed') {
    return {
      lcNumber,
      documentCount,
      issueCount,
      overallStatus: 'error',
      statusLabel: 'Validation failed',
      state: 'blocked',
      canSubmit: false,
      canonical: false,
      truth: null,
    };
  }

  if (issueCount === 0) {
    return {
      lcNumber,
      documentCount,
      issueCount,
      overallStatus: 'success',
      statusLabel: 'Completed',
      state: 'completed',
      canSubmit: false,
      canonical: false,
      truth: null,
    };
  }

  return {
    lcNumber,
    documentCount,
    issueCount,
    overallStatus: issueCount > 2 ? 'error' : 'warning',
    statusLabel: 'Review needed',
    state: issueCount > 2 ? 'blocked' : 'review',
    canSubmit: false,
    canonical: false,
    truth: null,
  };
};
