import { normalizeDocumentType } from '@shared/types';

export interface UploadDocumentRequirement {
  key: string;
  type: string;
  label: string;
  exactRequirement: string;
}

export interface UploadAdditionalRequirement {
  key: string;
  label: string;
  detail: string;
  category: 'identifier';
}

export interface UploadRequirementsModel {
  documentRequirements: UploadDocumentRequirement[];
  additionalRequirements: UploadAdditionalRequirement[];
}

const IDENTIFIER_REQUIREMENT_PATTERNS: Array<{ key: string; label: string; patterns: RegExp[] }> = [
  {
    key: 'exporter_bin',
    label: 'Exporter BIN',
    patterns: [/\bBIN\b/i, /business\s+identification\s+number/i],
  },
  {
    key: 'exporter_tin',
    label: 'Exporter TIN',
    patterns: [/\bTIN\b/i, /tax\s+identification\s+number/i],
  },
];

export function getUploadRequirementsModel(input: {
  requiredDocumentTypes?: string[] | null;
  documentsRequired?: string[] | null;
  specialConditions?: string[] | null;
  resolveLabel: (docType: string) => string;
}): UploadRequirementsModel {
  const requiredDocumentTypes = input.requiredDocumentTypes || [];
  const documentsRequired = input.documentsRequired || [];
  const specialConditions = input.specialConditions || [];

  const documentRequirements = requiredDocumentTypes.map((docType, index) => {
    const normalizedType = normalizeDocumentType(docType);
    const label = input.resolveLabel(normalizedType) || docType;
    const exactRequirement = String(documentsRequired[index] || '').trim();
    return {
      key: `${normalizedType}-${index}`,
      type: normalizedType,
      label,
      exactRequirement,
    };
  });

  const combinedTexts = [...documentsRequired, ...specialConditions]
    .map((value) => String(value || '').trim())
    .filter((value, index, all) => value.length > 0 && all.indexOf(value) === index);

  const additionalRequirements: UploadAdditionalRequirement[] = [];
  const seen = new Set<string>();

  for (const text of combinedTexts) {
    for (const identifier of IDENTIFIER_REQUIREMENT_PATTERNS) {
      if (seen.has(identifier.key)) continue;
      if (identifier.patterns.some((pattern) => pattern.test(text))) {
        seen.add(identifier.key);
        additionalRequirements.push({
          key: identifier.key,
          label: identifier.label,
          detail: text,
          category: 'identifier',
        });
      }
    }
  }

  return {
    documentRequirements,
    additionalRequirements,
  };
}
