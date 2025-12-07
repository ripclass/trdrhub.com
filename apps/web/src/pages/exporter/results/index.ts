/**
 * Exporter Results Components
 * 
 * Split from ExporterResults.tsx for better maintainability.
 */

// Bank submission verdict
export { BankVerdictCard } from './BankVerdictCard';
export type { BankVerdict, BankVerdictActionItem } from './BankVerdictCard';

// Bank profile display
export { BankProfileBadge } from './BankProfileBadge';
export type { BankProfile } from './BankProfileBadge';

// OCR confidence warning
export { OCRConfidenceWarning } from './OCRConfidenceWarning';
export type { ExtractionConfidence } from './OCRConfidenceWarning';

// Amendment cards
export { AmendmentCard, ToleranceBadge } from './AmendmentCard';
export type { Amendment, AmendmentsAvailable, AmendmentFieldChange, ToleranceApplied } from './AmendmentCard';

// Submission history
export { SubmissionHistoryCard } from './SubmissionHistoryCard';

// Utility functions and constants
export {
  DOCUMENT_LABELS,
  humanizeLabel,
  safeString,
  formatExtractedValue,
  formatConditions,
  formatAmountValue,
  normalizeDiscrepancySeverity,
  getStatusColor,
  getStatusLabel,
} from './utils';
