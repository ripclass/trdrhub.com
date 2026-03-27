import type {
  IssueCard,
  OptionEStructuredResult,
  SubmissionEligibility,
  StructuredResultBankVerdict,
  ValidationContractV1,
  ValidationResults,
} from '@/types/lcopilot';

type ResultSurfaceStatus = 'success' | 'warning' | 'error';

export interface CanonicalResultTruth {
  validationContract: ValidationContractV1 | null;
  finalVerdict: 'pass' | 'review' | 'reject' | null;
  submissionEligibility: SubmissionEligibility | null;
  bankVerdict: StructuredResultBankVerdict | null;
  overallStatus: ResultSurfaceStatus;
  readinessLabel: 'Ready' | 'Review needed' | 'Blocked';
  readinessClass: 'text-success' | 'text-warning' | 'text-destructive';
  canSubmitFromValidation: boolean;
  requirementReviewNeeded: boolean;
  requirementReasonCodes: string[];
  requirementActionTitles: string[];
  requirementReadinessItems: Array<Record<string, unknown>>;
}

const isObjectRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const normalizeFinalVerdict = (
  value: unknown,
): CanonicalResultTruth['finalVerdict'] => {
  const normalized = String(value ?? '').trim().toLowerCase();
  if (normalized === 'pass' || normalized === 'review' || normalized === 'reject') {
    return normalized;
  }
  return null;
};

const normalizeValidationStatus = (value: unknown): string => {
  return String(value ?? '').trim().toLowerCase();
};

const toStringArray = (value: unknown): string[] => {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => String(item ?? '').trim())
    .filter((item) => item.length > 0);
};

const getRequirementReadinessTruth = (
  validationContract: ValidationContractV1 | null,
): Pick<
  CanonicalResultTruth,
  'requirementReviewNeeded' | 'requirementReasonCodes' | 'requirementActionTitles' | 'requirementReadinessItems'
> => {
  const rulesEvidence = isObjectRecord(validationContract?.rules_evidence)
    ? (validationContract.rules_evidence as Record<string, unknown>)
    : null;
  const evidenceSummary = isObjectRecord(validationContract?.evidence_summary)
    ? (validationContract.evidence_summary as Record<string, unknown>)
    : null;
  const requirementReadinessItems = Array.isArray(rulesEvidence?.requirement_readiness_items)
    ? (rulesEvidence?.requirement_readiness_items as unknown[]).filter(isObjectRecord)
    : [];
  const requirementReasonCodes = Array.from(
    new Set([
      ...toStringArray(rulesEvidence?.requirement_reason_codes),
      ...toStringArray(evidenceSummary?.requirement_reason_codes),
    ]),
  );
  const requirementActionTitles = Array.from(
    new Set([
      ...toStringArray(evidenceSummary?.primary_requirement_actions),
      ...requirementReadinessItems
        .map((item) => String(item.title ?? '').trim())
        .filter((item) => item.length > 0),
    ]),
  );
  const requirementReviewNeeded = Boolean(
    evidenceSummary?.requirements_review_needed ??
      rulesEvidence?.requirements_review_needed ??
      requirementReadinessItems.length > 0,
  );

  return {
    requirementReviewNeeded,
    requirementReasonCodes,
    requirementActionTitles,
    requirementReadinessItems: requirementReadinessItems.map((item) => ({ ...item })),
  };
};

const getCriticalIssueCount = (issues: IssueCard[] = []): number =>
  issues.filter((issue) => {
    const severity = String(issue?.severity ?? '').toLowerCase();
    return ['critical', 'error', 'high'].includes(severity);
  }).length;

export const getValidationContract = (
  structuredResult?: OptionEStructuredResult | null,
): ValidationContractV1 | null => {
  const contract = structuredResult?.validation_contract_v1;
  return isObjectRecord(contract) ? (contract as ValidationContractV1) : null;
};

export const getCanonicalSubmissionEligibility = (
  structuredResult?: OptionEStructuredResult | null,
): SubmissionEligibility | null => {
  const eligibility =
    structuredResult?.effective_submission_eligibility ??
    structuredResult?.submission_eligibility ??
    null;
  return isObjectRecord(eligibility) ? (eligibility as SubmissionEligibility) : null;
};

export const getCanonicalBankVerdict = (
  structuredResult?: OptionEStructuredResult | null,
): StructuredResultBankVerdict | null => {
  const verdict = structuredResult?.bank_verdict ?? null;
  return isObjectRecord(verdict) ? (verdict as StructuredResultBankVerdict) : null;
};

export const getCanonicalResultTruth = (
  resultData?: Pick<ValidationResults, 'issues' | 'structured_result'> | null,
): CanonicalResultTruth => {
  const structuredResult = resultData?.structured_result ?? null;
  const issues = resultData?.issues ?? [];
  const validationContract = getValidationContract(structuredResult);
  const validationStatus = normalizeValidationStatus(structuredResult?.validation_status);
  const submissionEligibility = getCanonicalSubmissionEligibility(structuredResult);
  const topLevelFinalVerdict = normalizeFinalVerdict(structuredResult?.final_verdict);
  const contractFinalVerdict = normalizeFinalVerdict(validationContract?.final_verdict);
  const finalVerdict =
    contractFinalVerdict ??
    topLevelFinalVerdict ??
    (validationStatus === 'pass' ? 'pass' : null);
  const bankVerdict = getCanonicalBankVerdict(structuredResult);
  const requirementReadinessTruth = getRequirementReadinessTruth(validationContract);
  const bankVerdictLabel = String(bankVerdict?.verdict ?? '').trim().toUpperCase();
  const hasContractTruth = Boolean(validationContract || submissionEligibility);
  const canSubmitFromValidation =
    submissionEligibility?.can_submit ??
    (structuredResult?.validation_blocked
      ? false
      : finalVerdict === 'review'
      ? false
      : finalVerdict === 'reject'
      ? false
      : finalVerdict === 'pass'
      ? true
      : bankVerdict?.can_submit ?? false);
  const criticalIssueCount = getCriticalIssueCount(issues);
  const isBlocked =
    structuredResult?.validation_blocked === true ||
    finalVerdict === 'reject' ||
    (!hasContractTruth && (bankVerdictLabel === 'REJECT' || criticalIssueCount > 0));

  if (isBlocked) {
    return {
      validationContract,
      finalVerdict,
      submissionEligibility,
      bankVerdict,
      overallStatus: 'error',
      readinessLabel: 'Blocked',
      readinessClass: 'text-destructive',
      canSubmitFromValidation: false,
      ...requirementReadinessTruth,
    };
  }

  if (
    finalVerdict === 'review' ||
    canSubmitFromValidation === false ||
    requirementReadinessTruth.requirementReviewNeeded
  ) {
    return {
      validationContract,
      finalVerdict,
      submissionEligibility,
      bankVerdict,
      overallStatus: 'warning',
      readinessLabel: 'Review needed',
      readinessClass: 'text-warning',
      canSubmitFromValidation: false,
      ...requirementReadinessTruth,
    };
  }

  if (
    bankVerdictLabel === 'CAUTION' ||
    bankVerdictLabel === 'HOLD' ||
    issues.length > 0
  ) {
    return {
      validationContract,
      finalVerdict,
      submissionEligibility,
      bankVerdict,
      overallStatus: 'warning',
      readinessLabel: 'Ready',
      readinessClass: 'text-success',
      canSubmitFromValidation: true,
      ...requirementReadinessTruth,
    };
  }

  return {
    validationContract,
    finalVerdict,
    submissionEligibility,
    bankVerdict,
    overallStatus: 'success',
    readinessLabel: 'Ready',
    readinessClass: 'text-success',
    canSubmitFromValidation: true,
    ...requirementReadinessTruth,
  };
};
