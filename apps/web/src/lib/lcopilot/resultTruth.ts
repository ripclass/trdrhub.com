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
    topLevelFinalVerdict ??
    (submissionEligibility?.can_submit === true && contractFinalVerdict === 'review'
      ? validationStatus === 'pass'
        ? 'pass'
        : null
      : contractFinalVerdict) ??
    (validationStatus === 'pass' ? 'pass' : null);
  const bankVerdict = getCanonicalBankVerdict(structuredResult);
  const bankVerdictLabel = String(bankVerdict?.verdict ?? '').trim().toUpperCase();
  const canSubmitFromValidation =
    submissionEligibility?.can_submit ??
    (structuredResult?.validation_blocked
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
    bankVerdictLabel === 'REJECT' ||
    criticalIssueCount > 0;

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
    };
  }

  if (
    finalVerdict === 'review' ||
    canSubmitFromValidation === false
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
  };
};
