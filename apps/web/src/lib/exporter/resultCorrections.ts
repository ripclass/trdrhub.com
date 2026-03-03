import type { CustomsPackManifest } from '@/api/exporter';

export const parseSwiftYyMmDd = (raw: unknown): string | null => {
  const value = typeof raw === 'string' ? raw.trim() : '';
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

  const timelineIssueDate = lc?.dates?.issue;
  const swiftIssueDate = parseSwiftYyMmDd(lc?.mt700?.blocks?.['31C']);

  if (swiftIssueDate && timelineIssueDate && swiftIssueDate !== timelineIssueDate) {
    return swiftIssueDate;
  }

  return timelineIssueDate ?? swiftIssueDate ?? undefined;
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
