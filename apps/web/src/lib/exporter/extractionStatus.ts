import type { ValidationDocument } from '@/types/lcopilot';

export const NORMALIZED_EXTRACTION_REASONS = [
  'OCR timeout',
  'Low text quality',
  'Low extraction confidence',
  'Missing required fields',
  'Ambiguous field mapping',
  'Unsupported format',
] as const;

export type NormalizedExtractionReason = (typeof NORMALIZED_EXTRACTION_REASONS)[number];
export type ConfidenceBand = 'High' | 'Medium' | 'Low';

const FAILURE_CONFIDENCE_THRESHOLD = 0.6;

const reasonMatchers: Array<{ reason: NormalizedExtractionReason; test: (value: string) => boolean }> = [
  { reason: 'OCR timeout', test: (value) => value.includes('timeout') || value.includes('timed out') || value.includes('ocr timeout') },
  { reason: 'Low text quality', test: (value) => value.includes('low text') || value.includes('poor scan') || value.includes('illegible') || value.includes('blurry') || value.includes('quality') },
  { reason: 'Low extraction confidence', test: (value) => value.includes('low confidence') || value.includes('confidence') },
  { reason: 'Missing required fields', test: (value) => value.includes('missing required') || value.includes('required field') || value.includes('missing fields') },
  { reason: 'Ambiguous field mapping', test: (value) => value.includes('ambiguous') || value.includes('mapping') },
  { reason: 'Unsupported format', test: (value) => value.includes('unsupported') || value.includes('format') || value.includes('file type') },
];

export function normalizeExtractionReason(reason: unknown): NormalizedExtractionReason {
  const normalized = String(reason ?? '').trim().toLowerCase();
  if (!normalized) return 'Low extraction confidence';
  const hit = reasonMatchers.find((matcher) => matcher.test(normalized));
  return hit?.reason ?? 'Low extraction confidence';
}

export function toConfidenceScore(value: unknown): number {
  const parsed = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(parsed)) return 0;
  return Math.min(1, Math.max(0, parsed));
}

export function confidenceBand(score: number): ConfidenceBand {
  if (score >= 0.8) return 'High';
  if (score >= 0.6) return 'Medium';
  return 'Low';
}

export function formatConfidence(score: number): string {
  const clamped = toConfidenceScore(score);
  return `${clamped.toFixed(2)} (${confidenceBand(clamped)})`;
}

function hasUsableExtractedFields(doc: ValidationDocument): boolean {
  const fields = doc.extractedFields;
  if (!fields || typeof fields !== 'object') return false;
  const keys = Object.keys(fields).filter((key) => !key.startsWith('_'));
  return keys.length > 0;
}

export function isFailedDocumentGuardrailCompliant(doc: ValidationDocument): boolean {
  if ((doc.status ?? '').toLowerCase() !== 'error') return true;
  if (!doc.failedReason) return false;
  const confidence = toConfidenceScore((doc.extractedFields as any)?._extraction_confidence);
  if (hasUsableExtractedFields(doc) && confidence >= FAILURE_CONFIDENCE_THRESHOLD) {
    return false;
  }
  return true;
}
