import type { CustomsPackManifest } from '@/api/exporter';

const readDateString = (value: unknown): string | undefined => {
  if (typeof value === 'string' && value.trim().length > 0) {
    return value.trim();
  }
  if (value && typeof value === 'object' && 'value' in (value as Record<string, unknown>)) {
    const nested = (value as Record<string, unknown>).value;
    if (typeof nested === 'string' && nested.trim().length > 0) {
      return nested.trim();
    }
  }
  return undefined;
};

const parseIsoDate = (value: string | undefined): Date | null => {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const dt = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(dt.getTime()) ? null : dt;
};

const maybeRecoverSwappedIsoDate = (
  explicitIssueDate: string | undefined,
  expiryDate: string | undefined,
): string | undefined => {
  if (!explicitIssueDate) return undefined;

  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(explicitIssueDate);
  if (!match) return undefined;

  const [, yyyy, mm, dd] = match;
  const swapped = `20${dd}-${mm}-${yyyy.slice(2)}`;

  const explicitDt = parseIsoDate(explicitIssueDate);
  const swappedDt = parseIsoDate(swapped);
  const expiryDt = parseIsoDate(expiryDate);
  if (!explicitDt || !swappedDt || !expiryDt) return undefined;

  const explicitYear = explicitDt.getUTCFullYear();
  const swappedYear = swappedDt.getUTCFullYear();
  const expiryYear = expiryDt.getUTCFullYear();

  // Conservative guardrail: recover only when explicit year is unrealistically stale
  // for this LC horizon and swapped candidate lands near expiry window.
  if (explicitYear <= expiryYear - 5 && swappedYear >= expiryYear - 2 && swappedDt <= expiryDt) {
    return swapped;
  }

  return undefined;
};

export const parseSwiftYyMmDd = (raw: unknown): string | null => {
  const value = readDateString(raw) ?? '';
  if (!/^\d{6}$/.test(value)) return null;

  const yy = Number(value.slice(0, 2));
  const mm = Number(value.slice(2, 4));
  const dd = Number(value.slice(4, 6));
  if (mm < 1 || mm > 12 || dd < 1 || dd > 31) return null;

  const year = yy <= 69 ? 2000 + yy : 1900 + yy;
  return `${year.toString().padStart(4, '0')}-${value.slice(2, 4)}-${value.slice(4, 6)}`;
};

export const resolveIssueDateFromLc = (lc: Record<string, any> | null): string | undefined => {
  if (!lc) return undefined;

  const explicitIssueDate = readDateString(lc?.issue_date);
  const timelineIssueDate = readDateString(lc?.dates?.issue);

  const mt700FieldIssueDate =
    readDateString(lc?.mt700?.fields?.date_of_issue)
    ?? readDateString(lc?.mt700?.date_of_issue)
    ?? readDateString(lc?.mt700_raw?.fields?.date_of_issue)
    ?? readDateString(lc?.mt700_raw?.date_of_issue);

  const swiftIssueDate =
    parseSwiftYyMmDd(lc?.mt700?.blocks?.['31C'])
    ?? parseSwiftYyMmDd(lc?.mt700?.['31C'])
    ?? parseSwiftYyMmDd(lc?.mt700?.fields?.['31C'])
    ?? parseSwiftYyMmDd(lc?.mt700_raw?.blocks?.['31C'])
    ?? parseSwiftYyMmDd(lc?.mt700_raw?.['31C'])
    ?? parseSwiftYyMmDd(lc?.mt700_raw?.fields?.['31C']);

  if (swiftIssueDate) {
    return swiftIssueDate;
  }

  if (mt700FieldIssueDate) {
    return mt700FieldIssueDate;
  }

  const recoveredIssueDate = maybeRecoverSwappedIsoDate(explicitIssueDate, readDateString(lc?.dates?.expiry));
  if (recoveredIssueDate) {
    return recoveredIssueDate;
  }

  return explicitIssueDate ?? timelineIssueDate ?? undefined;
};

export const hydrateManifestFromCustomsPack = (
  customsPack: { manifest?: Array<{ name?: string | null; tag?: string | null }>; format?: string } | null | undefined,
  lcNumber: string | undefined,
  validationSessionId: string | null,
): CustomsPackManifest | null => {
  if (!customsPack || !Array.isArray(customsPack.manifest) || customsPack.manifest.length === 0) {
    return null;
  }

  return {
    lc_number: lcNumber || 'Unknown',
    validation_session_id: validationSessionId || '',
    generated_at: new Date().toISOString(),
    documents: customsPack.manifest.map((item, index) => ({
      name: item?.name || `Document ${index + 1}`,
      type: item?.tag || 'supporting_document',
      sha256: '',
      size_bytes: 0,
    })),
    generator_version: customsPack.format || 'zip-manifest-v1',
  };
};
